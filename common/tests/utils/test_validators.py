import math
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.core.exceptions import ValidationError

from common.utils.testing_components import create_image
from common.utils.validators import validate_rating, validate_years, validate_image_size


class TitleValidatorTestCase(TestCase):

    def test_rating_validator__valid_cases(self):
        test_cases = [{'rating': '1-10'}, {'rating': 7}, {'rating': 7.6}, {'rating': '7.6-10'}, {'rating': '7.6 - 10'}]
        for case in test_cases:
            test_rating = case['rating']
            with self.subTest(rating=test_rating):
                self.assertIsNone(validate_rating(test_rating))

    def test_years_validator__valid_cases(self):
        test_cases = [{'year': '2020-2025'}, {'year': 2020}, {'year': '2020 - 2025'}]
        for case in test_cases:
            test_year = case['year']
            with self.subTest(year=test_year):
                self.assertIsNone(validate_years(test_year))

    def test_rating_validator__invalid_cases(self):
        test_cases = [
            {'rating': 15, 'error': '15.0 is out of range! The range is 1-10'},
            {'rating': '7-15', 'error': '15.0 is out of range! The range is 1-10'},
            {'rating': -9, 'error': '-9.0 is out of range! The range is 1-10'},
            {'rating': '7-3', 'error': 'Incorrect range'},
            {'rating': 'test', 'error': 'test is unsupported value! The range is 1-10'},
            {'rating': '-2-9', 'error': 'Could not read the range! The range must look like 1-10'},
        ]

        for case in test_cases:
            test_rating = case['rating']
            with self.subTest(rating=test_rating):
                with self.assertRaises(ValidationError) as error:
                    validate_rating(test_rating)
                    self.assertEqual(error.exception.messages, case['error'])

    def test_year_validator__invalid_cases(self):
        test_cases = [
            {'year': '2022-2020', 'error': 'Incorrect range'},
            {'year': 2080, 'error': '2080 is out of range! The range is 1874-2050'},
            {'year': 1100, 'error': '1100 is out of range! The range is 1874-2050'},
            {'year': -1100, 'error': '-1100 is unsupported value! The range is 1874-2050'},
            {'year': 2020.9, 'error': '2020.9 is unsupported value! The range is 1874-2050'},
            {'year': 'test', 'error': 'test is unsupported value! The range is 1874-2050'},
        ]

        for case in test_cases:
            test_year = case['year']
            with self.subTest(year=test_year):
                with self.assertRaises(ValidationError) as error:
                    validate_years(test_year)
                    self.assertEqual(error.exception.messages, case['error'])


class ImageValidatorTestCase(TestCase):

    def setUp(self):
        self.base_params = {'max_size_mb': 0.05, 'min_width': 10, 'min_height': 10}
        self.validator = validate_image_size(**self.base_params)

    @patch('common.utils.validators.get_image_dimensions')
    def test_when_image_has_invalid_resolution(self, mock_get_image_dimensions):
        mock_get_image_dimensions.return_value = (1, 1)
        test_image = MagicMock(size=10)

        with self.assertRaises(ValidationError) as error:
            self.validator(test_image)
        self.assertEqual(error.exception.messages, [f'Слишком маленькое разрешение.'
                                                    f' Минимальное разрешение - {self.base_params["min_width"]}х{self.base_params["min_height"]}'])

    @patch('common.utils.validators.get_image_dimensions')
    def test_when_image_has_invalid_size(self, mock_get_image_dimensions):
        mock_get_image_dimensions.return_value = (15, 15)
        test_image = MagicMock(size=100000)

        with self.assertRaises(ValidationError) as error:
            self.validator(test_image)
        self.assertEqual(error.exception.messages,
                         [f'Слишком большое изображение. Максимальный размер - {self.base_params["max_size_mb"]}мб'])

    @patch('common.utils.validators.get_image_dimensions')
    def test_when_image_has_all_issues_in_one_time(self, mock_get_image_dimensions):
        mock_get_image_dimensions.return_value = (1, 1)
        test_image = MagicMock(size=100000)

        with self.assertRaises(ValidationError) as error:
            self.validator(test_image)
        self.assertCountEqual(
            error.exception.messages,
            [
                f'Слишком маленькое разрешение. Минимальное разрешение - {self.base_params["min_width"]}х{self.base_params["min_height"]}',
                f'Слишком большое изображение. Максимальный размер - {self.base_params["max_size_mb"]}мб',
            ]
        )

    @patch('common.utils.validators.get_image_dimensions')
    def test_happy_path(self, mock_get_image_dimensions):
        mock_get_image_dimensions.return_value = (15, 15)
        test_image = MagicMock(size=10)

        self.assertIsNone(self.validator(test_image))
