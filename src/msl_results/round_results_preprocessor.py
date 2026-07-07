import pandas as pd
from django.core.files.uploadedfile import InMemoryUploadedFile

from msl_results.models import Result
from msl_about.models import SeasonParameters, SeasonParametersPenalizations, Team
from .models import SeasonRounds


class RoundResultsPreprocessor:
    def __init__(self, round_obj: SeasonRounds, new_results_file: InMemoryUploadedFile):
        self.round_obj = round_obj
        self.results_df = self.file_to_dataframe(new_results_file)

    def file_to_dataframe(self, results_file: InMemoryUploadedFile) -> pd.DataFrame:
        sheet_names = ["Pořadí muži", "Pořadí ženy", "Pořadí 35+"]
        # N=13, Q=16, S=18, T=19, U=20 (0-indexed)
        col_indices = [13, 16, 18, 19, 20]
        col_names = ['team_excel', 'category_excel', 'competitors_borrowed', 'lp', 'pp']

        all_sheets = pd.read_excel(
            results_file,
            sheet_name=sheet_names,
            header=None,
            skiprows=3,   # rows 1-3 skipped, data starts at row 4
            nrows=27,     # rows 4-30 inclusive
            usecols=col_indices,
        )

        dfs = []
        for df in all_sheets.values():
            df.columns = col_names
            dfs.append(df)

        results = pd.concat(dfs, ignore_index=True).dropna(subset=['team_excel'])
        results = results.apply(lambda col: col.str.strip() if pd.api.types.is_string_dtype(col) else col)
        return self.postprocess(results)

    def postprocess(self, results_df: pd.DataFrame) -> pd.DataFrame:
        """Calculates extra columns for the results DataFrame"""

        def _extract_ranking_def(val):
            if pd.isna(val):
                return None
            try:
                float(val)
                return None
            except (ValueError, TypeError):
                return str(val)[:2]

        # ranking_def from lp / pp
        results_df['ranking_def'] = results_df.apply(
            lambda row: (
                _extract_ranking_def(row['lp'])
                or _extract_ranking_def(row['pp'])
                or 'U'  # default
            ),
            axis=1,
        )
        results_df['lp'] = pd.to_numeric(results_df['lp'], errors='coerce').fillna(0.0)
        results_df['pp'] = pd.to_numeric(results_df['pp'], errors='coerce').fillna(0.0)
        results_df['max_lp_pp'] = results_df.apply(
            lambda row: 0.0 if (row['lp'] == 0 or row['pp'] == 0) else max(row['lp'], row['pp']),
            axis=1
        )
        results_df['sum_lp_pp'] = results_df['lp'] + results_df['pp']

        results_df['team'] = results_df.apply(
            lambda row: Team.get_team(row['team_excel'], row['category_excel']),
            axis=1,
        )
        results_df['penalties_allowed'] = results_df.apply(
            lambda row: Result.penalties_allowed(team=row['team'], round=self.round_obj),
            axis=1,
        )

        def _compute_penalty(row):
            penalty = 0
            if row['penalties_allowed'] and row['competitors_borrowed'] > 0:
                penal_points = (
                    SeasonParametersPenalizations.objects
                    .filter(
                        season_year=self.round_obj.season_year,
                        category=row['category_excel'],
                        competitors_borrowed=row['competitors_borrowed'],
                    )
                    .values_list('penalization_points', flat=True)
                    .first()
                )
                if penal_points is not None:
                    penalty += penal_points
            return penalty

        results_df['penalty_points'] = results_df.apply(_compute_penalty, axis=1)

        # Order by max_lp_pp within each category_excel, but keep ranking_def=N (max_lp_pp=0.0) at the end
        results_df = (
            results_df.sort_values(
                by=['category_excel', 'ranking_def', 'max_lp_pp', 'sum_lp_pp'],
                ascending=[True, False, True, True],  # False (non-zero) first, True (zero) last; lower sum ranks better
                kind='mergesort',  # stable sort
            )
        )

        # Assign ranking numbers within each category, replacing only 'U' with the rank number
        results_df['_rank_within_category'] = results_df.groupby('category_excel').cumcount() + 1
        # This ranking is for mapping to ranking_def in SeasonParameters (includes also integers as positions)
        results_df['ranking'] = results_df.apply(
            lambda row: str(row['_rank_within_category']) if row['ranking_def'] == 'U' else row['ranking_def'],
            axis=1,
        )
        results_df = results_df.drop(columns=['_rank_within_category'])

        results_df['points'] = results_df.apply(
            lambda row: SeasonParameters.get_points(
                season_year=self.round_obj.season_year, category=row['category_excel'], ranking_def=row['ranking']
            ) - row['penalty_points'],
            axis=1,
        )
        results_df['prize_money'] = results_df.apply(
            lambda row: SeasonParameters.get_finances(
                season_year=self.round_obj.season_year, category=row['category_excel'], ranking_def=row['ranking']
            ),
            axis=1,
        )
        return results_df

    def store_to_results_model(self):
        """
        Store results DataFrame to Result model in database
        """
        for _, row in self.results_df.iterrows():
            # Create or update the result
            result, created = Result.objects.get_or_create(
                team_excel=row['team_excel'],
                round=self.round_obj,
                category_excel=row['category_excel'],
                defaults={
                    'team': row['team'],
                    'competitors_borrowed': int(row['competitors_borrowed']) if pd.notna(row['competitors_borrowed']) else 0,
                    'lp': row['lp'],
                    'pp': row['pp'],
                    'ranking_def': row['ranking_def'],
                    'penalty_points': int(row['penalty_points']) if pd.notna(row['penalty_points']) else 0,
                    'points': int(row['points']) if pd.notna(row['points']) else 0,
                    'prize_money': int(row['prize_money']) if pd.notna(row['prize_money']) else 0,
                }
            )

            # If the result already exists, update it
            if not created:
                result.team = row['team']
                result.competitors_borrowed = int(row['competitors_borrowed']) if pd.notna(row['competitors_borrowed']) else 0
                result.lp = row['lp']
                result.pp = row['pp']
                result.ranking_def = row['ranking_def']
                result.penalty_points = int(row['penalty_points']) if pd.notna(row['penalty_points']) else 0
                result.points = int(row['points']) if pd.notna(row['points']) else 0
                result.prize_money = int(row['prize_money']) if pd.notna(row['prize_money']) else 0
                result.save()
