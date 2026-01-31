from http import HTTPStatus

from django.shortcuts import reverse
from django.test import TestCase

from common.utils.testing_components import TestHistorySetUpMixin
from titles.models import SeasonsInfo, Title
from video_player.models import VideoResource, ViewingHistory


class HistoryManagementTestCase(TestHistorySetUpMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.path_delete = reverse('users:delete_from_history_ajax')
        self.path_toggle = reverse('users:toggle_viewing_completed_ajax')

    def test_delete__happy_path(self):
        self.client.login(username=self.username, password=self.password)
        to_delete = ViewingHistory.objects.first().id
        data = {'record_id': to_delete}
        response = self.client.post(self.path_delete, data=data)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertFalse(ViewingHistory.objects.filter(id=to_delete).exists())

    def test_delete__when_there_are_several_records_for_title(self):
        self.client.login(username=self.username, password=self.password)

        title = Title.objects.create(name='Title 999', type=Title.SERIES, id=999)
        info1 = SeasonsInfo.objects.create(title=title, season=1, episode=1, id=999)
        info2 = SeasonsInfo.objects.create(title=title, season=1, episode=2, id=888)
        resource1 = VideoResource.objects.create(iframe='http://video_999', content_unit=info1, id=999)
        resource2 = VideoResource.objects.create(iframe='http://video_999', content_unit=info2, id=888)

        ViewingHistory.objects.create(user=self.user, position=1, resource=resource1, id=999)
        to_delete = ViewingHistory.objects.create(user=self.user, position=1, resource=resource2, id=888)

        data = {'record_id': to_delete.id}
        response = self.client.post(self.path_delete, data=data)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertFalse(ViewingHistory.objects.filter(resource__content_unit__title=title).exists())

    def test_delete__when_record_does_not_exist(self):
        count_before = ViewingHistory.objects.count()
        self.client.login(username=self.username, password=self.password)
        to_delete = 9999
        data = {'record_id': to_delete}
        response = self.client.post(self.path_delete, data=data)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertEqual(ViewingHistory.objects.count(), count_before)

    def test_toggle__false(self):
        self.client.login(username=self.username, password=self.password)
        to_delete = ViewingHistory.objects.first()
        data = {'record_id': to_delete.id}
        response = self.client.post(self.path_toggle, data=data)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTrue(ViewingHistory.objects.get(id=to_delete.id).completed)

    def test_toggle__true(self):
        self.client.login(username=self.username, password=self.password)
        to_delete = ViewingHistory.objects.first()
        to_delete.completed = True
        to_delete.save()
        data = {'record_id': to_delete.id}
        response = self.client.post(self.path_toggle, data=data)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertFalse(ViewingHistory.objects.get(id=to_delete.id).completed)

    def test_toggle__when_record_does_not_exist(self):
        self.client.login(username=self.username, password=self.password)
        to_delete = 9999
        data = {'record_id': to_delete}
        response = self.client.post(self.path_toggle, data=data)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
