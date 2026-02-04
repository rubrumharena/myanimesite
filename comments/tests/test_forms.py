from django.test import RequestFactory, TestCase

from comments.forms import CommentForm
from comments.models import Comment
from titles.models import Title
from users.models import User


class CommentFormTestCase(TestCase):
    def setUp(self):
        self.username = 'test_user'
        self.password = '12345'
        self.user = User.objects.create_user(username=self.username, password=self.password)
        self.title = Title.objects.create(name='Test Title', type=Title.MOVIE)
        self.request = RequestFactory().get('/')
        self.request.user = self.user

    def test_form_connects_user_from_request(self):
        data = {'text': 'New comment'}
        form = CommentForm(request=self.request, data=data, title=self.title)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(Comment.objects.first().user, self.user)
        self.assertEqual(Comment.objects.first().title, self.title)

    def test_form_finds_parent(self):
        parent = Comment.objects.create(user=self.user, title=self.title, text='New comment')
        data = {'text': 'New comment', 'parent': parent.id}
        form = CommentForm(request=self.request, data=data, title=self.title)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(Comment.objects.last().user, self.user)
        self.assertEqual(Comment.objects.last().title, self.title)
        self.assertEqual(Comment.objects.last().parent, parent)

    def test_form_raises_error_parent_does_not_exist(self):
        title = Title.objects.create(name='Test Title 2', type=Title.MOVIE)
        parent = Comment.objects.create(user=self.user, title=title, text='New comment')
        test_cases = [
            {'text': 'New comment', 'parent': 999},
            {'text': 'New comment', 'parent': parent.id},
        ]
        for case in test_cases:
            with self.subTest(case=case):
                form = CommentForm(request=self.request, data=case, title=self.title)
                self.assertFalse(form.is_valid())
                self.assertEqual(form.errors['parent'], ['Отправлен ответ для несуществующего комментария!'])

    def test_form_raises_error_if_request_is_invalid_when_try_to_save_form(self):
        data = {'text': 'New comment'}
        CommentForm(data=data)
        self.assertEqual(Comment.objects.all().count(), 0)

    def test_form_does_not_raise_error_for_view(self):
        self.assertTrue(CommentForm())
