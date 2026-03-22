import os
import unittest
from unittest.mock import MagicMock

from msl_results.round_results_preprocessor import RoundResultsPreprocessor


EXCEL_PATH = os.path.join(os.path.dirname(__file__), 'test_results_jistebnik_2025.xlsx')


class TestFileToDataframeFromActualFile(unittest.TestCase):

    def setUp(self):
        round_obj = MagicMock()
        round_obj.season_year = 2025

        preprocessor = RoundResultsPreprocessor.__new__(RoundResultsPreprocessor)
        preprocessor.round_obj = round_obj

        with open(EXCEL_PATH, 'rb') as f:
            self.df = preprocessor.file_to_dataframe(f)

    def test_expected_structure_and_data(self):
        expected = {'team_excel', 'category_excel', 'lp', 'pp', 'ranking_def', 'penalty_points', 'points', 'prize_money'}
        self.assertTrue(expected.issubset(set(self.df.columns)))
        self.assertEqual(len(self.df), 31)

if __name__ == '__main__':
    unittest.main()