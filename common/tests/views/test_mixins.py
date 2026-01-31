from http import HTTPStatus
from unittest import TestCase
from unittest.mock import Mock

from django.test import RequestFactory
from django.views.generic import ListView, TemplateView

from common.views.mixins import PaginatorMixin


class PaginatorMixinTestCase(TestCase):
    class DummyView(PaginatorMixin, ListView):
        paginate_by = 1
        template_name = 'test.html'

        def get_queryset(self):
            return [Mock() for _ in range(10)]

    def setUp(self):
        self.factory = RequestFactory()

    def test_happy_path(self):
        request = self.factory.get('/?page=2')
        view = self.DummyView
        response = view.as_view()(request)
        context = response.context_data

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIn('paginator', context)
        self.assertIn('page_obj', context)
        self.assertIn('page_range', context)
        self.assertIn('page_error', context)

        page_obj = context['page_obj']
        self.assertEqual(page_obj.number, 2)
        self.assertEqual(len(page_obj.object_list), view.paginate_by)
        self.assertEqual(len(page_obj.paginator.object_list), len(view().get_queryset()))
        self.assertFalse(context['page_error'])

    def test_when_mixin_used_without_list_view(self):
        with self.assertRaises(TypeError):

            class InvalidDummyView(PaginatorMixin, TemplateView):
                template_name = 'test.html'

    def test_when_invalid_page_parameter(self):
        request = self.factory.get('/?page=999')
        view = self.DummyView
        response = view.as_view()(request)
        context = response.context_data

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIn('paginator', context)
        self.assertIn('page_obj', context)
        self.assertIn('page_range', context)
        self.assertIn('page_error', context)

        page_obj = context['page_obj']
        self.assertEqual(page_obj.number, 1)
        self.assertEqual(len(page_obj.object_list), view.paginate_by)
        self.assertEqual(len(page_obj.paginator.object_list), len(view().get_queryset()))
        self.assertTrue(context['page_error'])
