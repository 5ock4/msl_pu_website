import os
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from msl_results.round_results_preprocessor import RoundResultsPreprocessor


EXCEL_PATH = os.path.join(os.path.dirname(__file__), 'test_results_jistebnik_2025.xlsx')


class TestFileToDataframeFromActualFile(unittest.TestCase):

    def setUp(self):
        round_obj = MagicMock()
        round_obj.season_year = 2024

        with patch('msl_results.round_results_preprocessor.Team') as MockTeam, \
             patch('msl_results.round_results_preprocessor.Result') as MockResult, \
             patch('msl_results.round_results_preprocessor.SeasonParametersPenalizations') as MockPenal:

            MockTeam.get_team.return_value = MagicMock(name='team_instance')
            MockResult.penalties_allowed.return_value = False
            MockPenal.objects.filter.return_value \
                .values_list.return_value.first.return_value = None

            preprocessor = RoundResultsPreprocessor.__new__(RoundResultsPreprocessor)
            preprocessor.round_obj = round_obj

            with open(EXCEL_PATH, 'rb') as f:
                self.df = preprocessor.file_to_dataframe(f)

    def test_returns_dataframe(self):
        self.assertIsInstance(self.df, pd.DataFrame)

    def test_not_empty(self):
        self.assertFalse(self.df.empty)

    def test_all_rows_are_msl(self):
        self.assertTrue((self.df['msl'] == 1).all())

    def test_expected_columns_present(self):
        expected = {'team_excel', 'category_excel', 'lp', 'pp', 'ranking_def', 'calc_penalty_points'}
        self.assertTrue(expected.issubset(set(self.df.columns)))


if __name__ == '__main__':
    unittest.main()