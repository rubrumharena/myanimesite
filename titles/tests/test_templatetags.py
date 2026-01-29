from django.http import QueryDict
from django.test import TestCase

from titles.templatetags.utils import humanize_number, get_firm_num_ending, get_soft_num_ending, exclude_params



class HumanizeNumbersTagTestCase(TestCase):

    def test_if_number_less_than_thousand(self):
        self.assertEqual('100', humanize_number(100))

    def test_if_number_is_thousands(self):
        self.assertEqual('2,0 тыс.', humanize_number(2_000))

    def test_if_number_more_than_million(self):
        self.assertEqual('3,2 мил.', humanize_number(3_200_000))

    def test_if_invalid_input(self):
        self.assertEqual('—', humanize_number('test'))

class ExcludeParams(TestCase):

    def setUp(self):
        self.query_dict = QueryDict('a=1&b=2&c=3&c=4', mutable=True)

    def test_happy_path(self):
        url = exclude_params(self.query_dict, 'b')
        self.assertEqual('?a=1&c=3&c=4', url)

    def test_when_parameter_is_multiple(self):
        url = exclude_params(self.query_dict, 'c')
        self.assertEqual('?a=1&b=2', url)

    def test_when_no_parameter(self):
        url = exclude_params(self.query_dict, 'd')
        self.assertEqual('?a=1&b=2&c=3&c=4', url)

    def test_params_are_empty(self):
        url = exclude_params(QueryDict(), 'a')
        self.assertEqual('', url)