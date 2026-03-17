from datetime import datetime, timedelta
from http import HTTPStatus
from unittest.mock import patch

from django.shortcuts import reverse
from django.test import TestCase
from django.urls import NoReverseMatch

from comments.forms import CommentForm
from comments.models import Comment, CommentLikeHistory
from titles.models import Title
from users.models import User


class CommentAjaxViewTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.username = 'testuser'
        cls.password = '12345'
        cls.user = User.objects.create_user(username=cls.username, password=cls.password)
        cls.title = Title.objects.create(name='Title', type=Title.MOVIE)

    def set_up_comments(self):
        now = datetime.now()
        comments = [
            Comment(
                title=self.title,
                user=self.user,
                text=f'Test comment {i}',
                created_at=now + timedelta(minutes=i),
            )
            for i in range(30)
        ]
        Comment.objects.bulk_create(comments)

        self.comments = Comment.objects.filter(title=self.title).select_related('user')
        self.root_comments = (
            Comment.objects.filter(title=self.title, parent__isnull=True).order_by('-created_at').select_related('user')
        )
        self.comment_tree = {comment.id: [] for comment in self.comments}

    def setUp(self):
        self.get_path = reverse('comments:comments', kwargs={'title_id': self.title.id})
        self.post_path = reverse('comments:publicate_comment', kwargs={'title_id': self.title.id})
        self.set_up_comments()

    def _common_tests(self, response, tree, liked_comments, root):
        context = response.context
        self.assertTemplateUsed(response, 'comments/comment_tree.html')
        self.assertEqual(
            [c.id for c in context['root']],
            [c.id for c in root],
        )
        self.assertEqual(context['tree'], tree)
        self.assertEqual(list(context['liked_comments']), list(liked_comments))
        self.assertIsInstance(context['form'], CommentForm)

    @patch('video_player.models.cache.set')
    @patch('video_player.models.cache.get', return_value=None)
    def test_get__when_no_parents_in_comments(self, mock_cache_get, mock_cache_set):
        self.client.login(username=self.username, password=self.password)
        likes = []
        for comment in self.comments[:5]:
            CommentLikeHistory.objects.create(user=self.user, comment=comment)
            likes.append(comment.id)

        response = self.client.get(self.get_path)
        self._common_tests(response, self.comment_tree, likes, self.root_comments[:24])
        self.assertEqual(response.status_code, HTTPStatus.OK)

    @patch('video_player.models.cache.set')
    @patch('video_player.models.cache.get', return_value=None)
    def test_get__when_user_is_not_authenticated(self, mock_cache_get, mock_cache_set):
        response = self.client.get(self.get_path)
        self._common_tests(response, self.comment_tree, [], self.root_comments[:24])
        self.assertEqual(response.status_code, HTTPStatus.OK)

    @patch('video_player.models.cache.set')
    @patch('video_player.models.cache.get', return_value=None)
    def test_get__when_title_does_not_exist(self, mock_cache_get, mock_cache_set):
        self.client.login(username=self.username, password=self.password)
        path = reverse('comments:comments', kwargs={'title_id': 999})

        response = self.client.get(path)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    @patch('video_player.models.cache.set')
    @patch('video_player.models.cache.get', return_value=None)
    def test_get__when_comments_have_parents(self, mock_cache_get, mock_cache_set):
        self.client.login(username=self.username, password=self.password)

        rc1 = self.comments[0]
        rc2 = self.comments[1]

        bc1 = self.comments[2]
        bc2 = self.comments[3]
        bc3 = self.comments[4]
        bc4 = self.comments[5]

        bc1.parent = rc1
        bc2.parent = rc1
        bc3.parent = bc1
        bc4.parent = rc2

        bc1.save()
        bc2.save()
        bc3.save()
        bc4.save()

        comment_tree = {comment.id: [] for comment in self.comments}
        comment_tree[rc1.id] = [bc2, bc1]
        comment_tree[rc2.id] = [bc4]
        comment_tree[bc1.id] = [bc3]

        response = self.client.get(self.get_path)
        self._common_tests(response, comment_tree, [], self.root_comments[:24])
        self.assertEqual(response.status_code, HTTPStatus.OK)

    @patch('video_player.models.cache.set')
    @patch('video_player.models.cache.get', return_value=None)
    def test_get__pagination_works(self, mock_cache_get, mock_cache_set):
        comment_tree = {comment.id: [] for comment in self.comments}

        response = self.client.get(self.get_path + '?page=2')
        self._common_tests(response, comment_tree, [], self.root_comments[24:])
        self.assertEqual(response.status_code, HTTPStatus.OK)

    @patch('video_player.models.cache.set')
    @patch('video_player.models.cache.get', return_value=None)
    def test_post__happy_path(self, mock_cache_get, mock_cache_set):
        self.client.login(username=self.username, password=self.password)
        data = {'text': 'New comment'}
        response = self.client.post(self.post_path, data)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Comment.objects.last().text, data['text'])

    @patch('video_player.models.cache.set')
    @patch('video_player.models.cache.get', return_value=None)
    def test_post__invalid_form(self, mock_cache_get, mock_cache_set):
        self.client.login(username=self.username, password=self.password)
        data = {'text': 'New comment', 'parent': 9999}
        response = self.client.post(self.post_path, data)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            response.context['form'].errors['parent'][0], 'Отправлен ответ для несуществующего комментария!'
        )
        self._common_tests(response, {}, [], [])

    @patch('video_player.models.cache.set')
    @patch('video_player.models.cache.get', return_value=None)
    def test_post__when_user_is_not_authenticated(self, mock_cache_get, mock_cache_set):
        data = {'text': 'New comment', 'title': 999}
        response = self.client.post(self.post_path, data)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)


class LikeCommentTestCase(TestCase):
    def setUp(self):
        self.username = 'testuser'
        self.password = '12345'
        self.user = User.objects.create_user(username=self.username, password=self.password)
        self.title = Title.objects.create(name='Title 1', type=Title.SERIES)
        self.comment = Comment.objects.create(text='BlaBlaBla', user=self.user, title=self.title)
        self.path = reverse('comments:like_comment', args=[self.comment.id])

    def test_if_like_no_record(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.post(self.path)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Comment.objects.last().like_count, 1)
        self.assertTrue(CommentLikeHistory.objects.filter(user=self.user, comment=self.comment).exists())

    def test_if_like_record(self):
        self.client.login(username=self.username, password=self.password)
        self.comment.like_count = 20
        self.comment.save()
        CommentLikeHistory.objects.create(user=self.user, comment=self.comment)

        response = self.client.post(self.path)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Comment.objects.last().like_count, 19)
        self.assertFalse(CommentLikeHistory.objects.filter(user=self.user, comment=self.comment).exists())

    def test_invalid_comment_id(self):
        self.client.login(username=self.username, password=self.password)
        test_cases_404 = [8.9, 'test', '']
        for case in test_cases_404:
            with self.subTest(case=case):
                with self.assertRaises(NoReverseMatch):
                    self.client.post(reverse('comments:like_comment', args=[case]))
        response = self.client.post(reverse('comments:like_comment', args=[999]))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_if_user_is_not_authenticated(self):
        response = self.client.post(self.path)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
