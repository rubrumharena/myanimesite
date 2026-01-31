import json
from http import HTTPStatus
from unittest.mock import patch

from django.shortcuts import reverse
from django.test import TestCase

from comments.models import Comment, CommentLikeHistory
from titles.models import Title
from users.models import User


class CommentAjaxViewTestCase(TestCase):
    def setUp(self):
        self.page_data = {
            'page_obj': {
                'has_previous': False,
                'has_next': True,
                'previous_page_number': None,
                'next_page_number': 2,
                'number': 1,
                'object_list': [1, 2, 3],
            },
            'page_range': [1, 2, 3],
            'page_error': False,
            'ellipsis': '...',
        }
        self.date_time = 'оставлен сегодня'
        self.username = 'testuser'
        self.password = '12345'
        self.title = Title.objects.create(name='Title', type=Title.MOVIE)
        self.get_path = reverse('comments:comment_get_ajax', kwargs={'title_id': self.title.id})
        self.post_path = reverse('comments:comment_post_ajax')
        self.user = User.objects.create_user(username=self.username, password=self.password)
        self.user_url = reverse('users:profile', kwargs={'username': self.username})

        comments = [Comment(title=self.title, user=self.user, text='Test comment') for _ in range(40)]
        Comment.objects.bulk_create(comments)

        self.title_comments = list(
            Comment.objects.filter(title=self.title)
            .order_by('-created_at')
            .values(
                'id', 'user__username', 'user__name', 'user__avatar', 'like_count', 'text', 'parent_id', 'created_at'
            )
        )
        for comment in self.title_comments:
            comment['created_at'] = self.date_time
            comment['user_url'] = self.user_url
            comment['user__avatar'] = None

    def _common_tests(self, actual_data, comment_tree, liked_comments):
        self.assertEqual(actual_data['liked_comments'], liked_comments)
        self.assertEqual(actual_data['comment_tree'], comment_tree)
        self.assertEqual(actual_data['page_obj'], self.page_data['page_obj'])
        self.assertEqual(actual_data['page_range'], self.page_data['page_range'])
        self.assertEqual(actual_data['page_error'], self.page_data['page_error'])
        self.assertEqual(actual_data['ellipsis'], self.page_data['ellipsis'])

    @patch('comments.views.humanize_date_time')
    @patch('comments.views.CommentAjaxView._serialize_page_data')
    def test_get__when_no_parents_in_comments(self, mock_page_data, mock_date_time):
        mock_page_data.return_value = self.page_data
        mock_date_time.return_value = self.date_time
        self.client.login(username=self.username, password=self.password)
        comment_tree = {str(comment['id']): [] for comment in self.title_comments}

        response = self.client.get(self.get_path)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self._common_tests(json.loads(response.content.decode()), comment_tree, [])

    def test_get__when_title_does_no_exist(self):
        self.client.login(username=self.username, password=self.password)
        path = reverse('comments:comment_get_ajax', kwargs={'title_id': 999})
        response = self.client.get(path)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    @patch('comments.views.humanize_date_time')
    @patch('comments.views.CommentAjaxView._serialize_page_data')
    def test_get__when_user_is_not_authenticated(self, mock_page_data, mock_date_time):
        mock_page_data.return_value = self.page_data
        mock_date_time.return_value = self.date_time
        self.client.login(username=self.username, password=self.password)
        comment_tree = {str(comment['id']): [] for comment in self.title_comments}

        response = self.client.get(self.get_path)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self._common_tests(json.loads(response.content.decode()), comment_tree, [])

    @patch('comments.views.humanize_date_time')
    @patch('comments.views.CommentAjaxView._serialize_page_data')
    def test_get__when_comments_have_parents(self, mock_page_data, mock_date_time):
        mock_page_data.return_value = self.page_data
        mock_date_time.return_value = self.date_time
        self.client.login(username=self.username, password=self.password)

        Comment.objects.all().delete()

        comments = [Comment(title=self.title, user=self.user, text='Test comment', id=i) for i in range(1, 4)]
        Comment.objects.bulk_create(comments)
        for i in range(2, 4):
            comment = Comment.objects.get(id=i)
            comment.parent_id = i - 1
            comment.save()
        title_comments = list(
            Comment.objects.filter(title=self.title)
            .order_by('-created_at')
            .values('id', 'user__username', 'user__name', 'like_count', 'text', 'parent_id', 'created_at')
        )
        comment_tree = {'1': [title_comments[1]], '2': [title_comments[0]], '3': []}

        for comment in title_comments:
            comment['created_at'] = self.date_time
            comment['user_url'] = self.user_url
            comment['user__avatar'] = None

        response = self.client.get(self.get_path)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self._common_tests(json.loads(response.content.decode()), comment_tree, [])

    @patch('comments.views.humanize_date_time')
    def test_serialize_page_data__if_no_page_in_request(self, mock_date_time):
        mock_date_time.return_value = self.date_time
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(self.get_path)
        data = json.loads(response.content.decode())
        expected_page_obj = {
            'has_previous': False,
            'has_next': True,
            'previous_page_number': None,
            'next_page_number': 2,
            'number': 1,
            'object_list': self.title_comments[:24],
        }

        self.assertEqual(data['page_obj'], expected_page_obj)
        self.assertEqual(data['page_range'], [1, 2])
        self.assertEqual(data['ellipsis'], '…')

    @patch('comments.views.humanize_date_time')
    def test_serialize_page_data__if_page_in_request(self, mock_date_time):
        mock_date_time.return_value = self.date_time
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(self.get_path + '?page=2')
        data = json.loads(response.content.decode())
        expected_page_obj = {
            'has_previous': True,
            'has_next': False,
            'previous_page_number': 1,
            'next_page_number': None,
            'number': 2,
            'object_list': self.title_comments[24:],
        }

        self.assertEqual(data['page_obj'], expected_page_obj)
        self.assertEqual(data['page_range'], [1, 2])
        self.assertEqual(data['ellipsis'], '…')

    @patch('comments.views.humanize_date_time')
    def test_serialize_page_data__with_invalid_cases(self, mock_date_time):
        mock_date_time.return_value = self.date_time
        self.client.login(username=self.username, password=self.password)

        test_cases = [999, 8.9, -1, 'test', None]

        for case in test_cases:
            with self.subTest(case=case):
                response = self.client.get(self.get_path + f'?page={case}')
                self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_post__happy_path(self):
        self.client.login(username=self.username, password=self.password)
        data = {'text': 'Tralalelo', 'title': self.title.id}
        response = self.client.post(self.post_path, data)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Comment.objects.last().text, data['text'])

    def test_post__invalid_form(self):
        self.client.login(username=self.username, password=self.password)
        data = {'text': 'Tralalelo', 'title': 999}
        response = self.client.post(self.post_path, data)
        response_data = json.loads(response.content.decode())
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(response_data['errors']['title'], ['Тайтл не существует'])

    def test_post__when_user_is_not_authenticated(self):
        data = {'text': 'Tralalelo', 'title': 999}
        response = self.client.post(self.post_path, data)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)


class LikeCommentTestCase(TestCase):
    def setUp(self):
        self.username = 'testuser'
        self.password = '12345'
        self.user = User.objects.create_user(username=self.username, password=self.password)
        self.title = Title.objects.create(name='Title 1', type=Title.SERIES)
        self.comment = Comment.objects.create(text='BlaBlaBla', user=self.user, title=self.title)
        self.path = reverse('comments:like_comment_ajax')

    def test_if_like_no_record(self):
        self.client.login(username=self.username, password=self.password)
        data = {'comment_id': self.comment.id}
        response = self.client.post(self.path, data=data)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Comment.objects.last().like_count, 1)
        self.assertTrue(CommentLikeHistory.objects.filter(user=self.user, comment=self.comment).exists())

    def test_if_like_record(self):
        self.client.login(username=self.username, password=self.password)
        data = {'comment_id': self.comment.id}
        self.comment.like_count = 20
        self.comment.save()
        CommentLikeHistory.objects.create(user=self.user, comment=self.comment)

        response = self.client.post(self.path, data=data)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Comment.objects.last().like_count, 19)
        self.assertFalse(CommentLikeHistory.objects.filter(user=self.user, comment=self.comment).exists())

    def test_invalid_comment_id(self):
        self.client.login(username=self.username, password=self.password)
        test_cases_400 = [8.9, 'test', '']
        for case in test_cases_400:
            with self.subTest(case=case):
                response = self.client.post(self.path, data={'comment_id': case})
                self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        response = self.client.post(self.path, data={'comment_id': 999})
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_if_user_is_not_authenticated(self):
        response = self.client.post(self.path, data={'comment_id': self.comment.id})
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
