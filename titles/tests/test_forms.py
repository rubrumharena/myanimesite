
from  http import HTTPStatus
from unittest.mock import patch

from titles.forms import TitleForm
from users.models import User
from django.shortcuts import reverse
from django.test import TestCase

from titles.models import TitleCreationHistory
from lists.models import Collection


class TitleFormTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        Collection.objects.create(slug='fantasy', name='Фэнтези', type=Collection.GENRE)

    def test_title_form_accepts_valid_input_data(self):
        test_cases = [{'page': 1, 'limit': 1, 'rating': '1-10', 'is_series': '', 'year': '', 'genre': '', 'sequels': False},
                      {'page': 2, 'limit': 1, 'rating': 7, 'is_series': True, 'year': '2020-2025', 'genre': 'fantasy', 'sequels': True},
                      {'page': 3, 'limit': 1, 'rating': 7.6, 'is_series': False, 'year': 2020, 'genre': '', 'sequels': False},
                      {'page': 3, 'limit': 1, 'rating': '7.6-10', 'is_series': False, 'year': '2020 - 2025', 'genre': '', 'sequels': False},
                      {'page': 3, 'limit': 1, 'rating': '7.6 - 10', 'is_series': False, 'year': 2020, 'genre': '', 'sequels': False}]
        for case in test_cases:
            with self.subTest(case=case):
                form = TitleForm(data=case)
                self.assertTrue(form.is_valid())

    def test_custom_validators_for_rating_and_years(self):
        base_data = {
            'page': 1,
            'limit': 1,
            'is_series': False,
            'genre': '',
            'sequels': False,
        }

        test_cases = [
            {'rating': 15, 'year': '', 'error': '15.0 is out of range! The range is 1-10'},
            {'rating': '7-15', 'year': '', 'error': '15.0 is out of range! The range is 1-10'},
            {'rating': -9, 'year': '', 'error': '-9.0 is out of range! The range is 1-10'},
            {'rating': '7-3', 'year': '', 'error': 'Incorrect range'},
            {'rating': 'test', 'year': '', 'error': 'test is unsupported value! The range is 1-10'},
            {'rating': '-2-9', 'year': '', 'error': 'Could not read the range! The range must look like 1-10'},
            {'rating': '', 'year': '2022-2020', 'error': 'Incorrect range'},
            {'rating': '', 'year': 2080, 'error': '2080 is out of range! The range is 1874-2050'},
            {'rating': '', 'year': 1100, 'error': '1100 is out of range! The range is 1874-2050'},
            {'rating': '', 'year': -1100, 'error': '-1100 is unsupported value! The range is 1874-2050'},
            {'rating': '', 'year': 2020.9, 'error': '2020.9 is unsupported value! The range is 1874-2050'},
            {'rating': '', 'year': 'test', 'error': 'test is unsupported value! The range is 1874-2050'},
        ]

        for case in test_cases:
            test_rating = case['rating']
            test_year = case['year']
            with self.subTest(rating=test_rating, year=test_year):
                data = base_data.copy()
                data.update({'rating': test_rating, 'year': test_year})
                form = TitleForm(data=data)
                self.assertFalse(form.is_valid())
                errors = sum(form.errors.values(), [])
                self.assertIn(case['error'], errors)