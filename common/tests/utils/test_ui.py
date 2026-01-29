import unittest
from datetime import datetime
from unittest.mock import patch, PropertyMock

from django.test import TestCase
from django.utils import timezone

from common.utils.ui import generate_years_and_decades, get_partial_fill


class CalendarGeneratorTestCase(TestCase):

    def setUp(self):
        self.expected_years_and_decades = ['2028', '2027', '2026', '2025', '2024', '2023', '2022', '2021', '2020',
                                           '2020-2028', '2010-2019', '2000-2009', '1990-1999', '1980-1989', '1970-1979',
                                           '1960-1969']

    @patch('common.utils.ui.datetime')
    def test_generate_years_and_decades__happy_path(self, mock_datetime):
        mock_datetime.now.return_value = datetime(2025, 1, 1)
        self.assertEqual(self.expected_years_and_decades, generate_years_and_decades())

    @patch('common.utils.ui.datetime')
    def test_generate_years_and_decades__structure(self, mock_datetime):
        mock_datetime.now.return_value = datetime(2025, 1, 1)
        result = generate_years_and_decades()
        for i, value in enumerate(self.expected_years_and_decades):
            with self.subTest(value=value):
                self.assertEqual(value, result[i])

    @patch('common.utils.ui.datetime')
    def test_generate_years_and_decades__with_expand_until_and_current(self, mock_datetime):
        mock_datetime.now.return_value = datetime(2025, 1, 1)
        expected = ['2025', '2024', '2023', '2022', '2021', '2020', '2019', '2018', '2017', '2016', '2015', '2020-2028',
                    '2010-2019', '2000-2009', '1990-1999', '1980-1989', '1970-1979', '1960-1969']
        self.assertEqual(expected, generate_years_and_decades(10, True))


class StarFillingTestCase(unittest.TestCase):

    def test_partial_star_logic_success(self):
        self.assertEqual(get_partial_fill(7.5),
                         {1: 100, 2: 100, 3: 100, 4: 100, 5: 100, 6: 100, 7: 100, 8: 50, 9: 0, 10: 0})
        self.assertEqual(get_partial_fill(7.0),
                         {1: 100, 2: 100, 3: 100, 4: 100, 5: 100, 6: 100, 7: 100, 8: 0, 9: 0, 10: 0})
        self.assertEqual(get_partial_fill(1.34), {1: 100, 2: 34, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9: 0, 10: 0})
        self.assertEqual(get_partial_fill(0.7), {1: 70, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9: 0, 10: 0})
        self.assertEqual(get_partial_fill(0), {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9: 0, 10: 0})
        self.assertEqual(get_partial_fill('7.5'),
                         {1: 100, 2: 100, 3: 100, 4: 100, 5: 100, 6: 100, 7: 100, 8: 50, 9: 0, 10: 0})

    def test_partial_star_logic_error(self):
        with self.assertRaises(ValueError):
            self.assertEqual(get_partial_fill(-1), ValueError)
            self.assertEqual(get_partial_fill('a'), ValueError)
            self.assertEqual(get_partial_fill(rating=13, stars=12), ValueError)




