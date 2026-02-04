from datetime import datetime
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from common.utils.humanizers import define_firm_ending, define_soft_ending, humanize_date_time


class EndingTagsTestCase(TestCase):
    def _firm_num_ending_tests(self, test_cases, ending):
        for case in test_cases:
            with self.subTest(case=case):
                self.assertEqual(ending, define_firm_ending(case))

    def _soft_num_ending_tests(self, test_cases, ending):
        for case in test_cases:
            with self.subTest(case=case):
                self.assertEqual(ending, define_soft_ending(case))

    def test_get_firm_num_ending_to_get_ov(self):
        test_cases = [11, 10, 40, 59, 65, 4589, 890]
        self._firm_num_ending_tests(test_cases, 'ов')

    def test_get_firm_num_ending_to_get_empty(self):
        test_cases = [1, 21, 101, 1001]

        self._firm_num_ending_tests(test_cases, '')

    def test_get_firm_num_ending_to_get_a(self):
        test_cases = [2, 4, 102, 23, 5643]

        self._firm_num_ending_tests(test_cases, 'а')

    def test_get_firm_num_ending_if_invalid_input(self):
        test_cases = ['test', 12.5]

        self._firm_num_ending_tests(test_cases, '')

    def test_get_soft_num_ending_to_get_iy(self):
        test_cases = [11, 10, 40, 59, 65, 4589, 890]
        self._soft_num_ending_tests(test_cases, 'й')

    def test_get_soft_num_ending_to_get_ya(self):
        test_cases = [1, 21, 101, 1001]

        self._soft_num_ending_tests(test_cases, 'я')

    def test_get_soft_num_ending_to_get_i(self):
        test_cases = [2, 4, 102, 23, 5643]

        self._soft_num_ending_tests(test_cases, 'и')

    def test_get_soft_num_ending_if_invalid_input(self):
        test_cases = ['test', 12.5]

        self._soft_num_ending_tests(test_cases, '')


class HumanizeDateTime(TestCase):
    def setUp(self):
        self.today = timezone.datetime(2025, 9, 13, 14, 30)

    @patch('common.utils.humanizers.timezone.now')
    def test_when_some_minutes_ago(self, mock_now):
        mock_now.return_value = self.today
        test_date = datetime(2025, 9, 13, 14, 10)

        actual_date = humanize_date_time(test_date)
        self.assertEqual(actual_date, '20 минут назад')

    @patch('common.utils.humanizers.timezone.now')
    def test_when_some_seconds_ago(self, mock_now):
        mock_now.return_value = self.today
        test_cases = [datetime(2025, 9, 13, 14, 29), datetime(2025, 9, 13, 14, 30)]

        for case in test_cases:
            with self.subTest(case=case):
                actual_date = humanize_date_time(case)
                self.assertEqual(actual_date, 'несколько секунд назад')

    @patch('common.utils.humanizers.timezone.now')
    def test_when_today(self, mock_now):
        mock_now.return_value = self.today
        test_date = datetime(2025, 9, 13, 10, 10)

        actual_date = humanize_date_time(test_date)
        self.assertEqual(actual_date, 'сегодня в 10:10')

    @patch('common.utils.humanizers.timezone.now')
    def test_when_yesterday(self, mock_now):
        mock_now.return_value = self.today
        test_date = datetime(2025, 9, 12, 10, 10)

        actual_date = humanize_date_time(test_date)
        self.assertEqual(actual_date, 'вчера в 10:10')

    @patch('common.utils.humanizers.timezone.now')
    def test_when_long_ago(self, mock_now):
        mock_now.return_value = self.today
        test_date = datetime(2025, 9, 10, 10, 10)

        actual_date = humanize_date_time(test_date)
        self.assertEqual(actual_date, '10 сентября 2025 в 10:10')
