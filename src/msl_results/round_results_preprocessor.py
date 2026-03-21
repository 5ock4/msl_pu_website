import numpy as np
import pandas as pd
from django.core.files.uploadedfile import InMemoryUploadedFile

from msl_results.models import Result
from msl_about.models import SeasonParameters, SeasonParametersPenalizations, Team
from .models import SeasonRounds
from util.models import CategoryChoices


class RoundResultsPreprocessor:
    def __init__(self, round_obj: SeasonRounds, results_file: InMemoryUploadedFile):
        self.round_obj = round_obj
        self.results_df = self.file_to_dataframe(results_file)

    def file_to_dataframe(self, results_file: InMemoryUploadedFile) -> pd.DataFrame:
        results = pd.read_excel(
                results_file,
                header=2,
                usecols=['LIGOVÉ BODY', 'SDH', 'TEAM', 'LIGA -1   NELIGOVÝ - 0', 'PŮJČENÝ ZÁVODNÍK M-1, Ž-1,2, SG-1',
                        '1-M,  2-Ž, 3-35', 'LEVÝ PROUD', 'PRAVÝ PROUD']
            ) \
            .dropna(subset=['SDH']) \
            .rename(columns={
                'LIGOVÉ BODY': 'points_excel',
                'SDH': 'sdh',
                'TEAM': 'team_excel',
                'LIGA -1   NELIGOVÝ - 0': 'msl',
                'PŮJČENÝ ZÁVODNÍK M-1, Ž-1,2, SG-1': 'competitors_borrowed',
                '1-M,  2-Ž, 3-35': 'category_excel',
                'LEVÝ PROUD': 'lp',
                'PRAVÝ PROUD': 'pp'
            })
        results['team_excel'] = np.where(
            (results['team_excel'].notna()) & (results['team_excel'] != 'A'), 
            results['sdh'] + ' ' + results['team_excel'], 
            results['sdh']
        )
        results = results.drop(columns=['sdh'])
        
        # Map category numeric values to readable text
        category_mapping = {
            1: CategoryChoices.MUZI.value,
            2: CategoryChoices.ZENY.value,
            3: CategoryChoices.VETERANI.value
        }
        results['category_excel'] = results['category_excel'].map(category_mapping)
        results['competitors_borrowed'] = pd.to_numeric(results['competitors_borrowed'], errors='coerce').fillna(0).astype(int)
        # Select only teams part of MSL
        results = results[results['msl'] == 1]

        results = self.postprocess(results)

        return results

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
            # TODO: Minus 5 points for NU and D should not be hardcoded here!
            if row['ranking_def'] in ['NU', 'D']:
                penalty -= 5
            return penalty

        results_df['penalty_points'] = results_df.apply(_compute_penalty, axis=1)

        # Order by max_lp_pp within each category_excel, but keep 0.0 at the end
        results_df = (
            results_df.sort_values(
                by=['category_excel', 'ranking_def', 'max_lp_pp',],
                ascending=[True, False, True],  # False (non-zero) first, True (zero) last
                kind='mergesort',  # stable sort
            )
        )

        # Assign ranking numbers within each category, replacing only 'U' with the rank number
        results_df['_rank_within_category'] = results_df.groupby('category_excel').cumcount() + 1
        results_df['ranking_def'] = results_df.apply(
            lambda row: str(row['_rank_within_category']) if row['ranking_def'] == 'U' else row['ranking_def'],
            axis=1,
        )
        results_df = results_df.drop(columns=['_rank_within_category'])

        results_df['points'] = results_df.apply(
            lambda row: SeasonParameters.get_points(
                season_year=self.round_obj.season_year, category=row['category_excel'], ranking_def=row['ranking_def']
            ) - row['penalty_points'],
            axis=1,
        )
        results_df['prize_money'] = results_df.apply(
            lambda row: SeasonParameters.get_finances(
                season_year=self.round_obj.season_year, category=row['category_excel'], ranking_def=row['ranking_def']
            ),
            axis=1,
        )
        return results_df

    def store_to_results_model(self):
        """
        Store results DataFrame to Result model in database
        """
        for _, row in self.results_df.iterrows():
            try:
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

            except Exception as e:
                print(f'Error saving result for team {row["team"]} in category {row["category_excel"]}: {str(e)}')
                continue
