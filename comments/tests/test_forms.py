from comments.forms import CommentForm
from comments.models import Comment
from users.models import User
from django.test import TestCase, RequestFactory

from titles.models import Title


class CommentFormTestCase(TestCase):

    def setUp(self):
        self.username = 'test_user'
        self.password = '12345'
        self.user = User.objects.create_user(username=self.username, password=self.password)
        self.title = Title.objects.create(name='Test Title', type=Title.MOVIE)
        self.request = RequestFactory().get('/')
        self.request.user = self.user

    def test_form_connects_user_from_request(self):
        data = {'text': 'Tralalelo', 'title': self.title.id}
        form = CommentForm(request=self.request, data=data)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(Comment.objects.first().user, self.user)
        self.assertEqual(Comment.objects.first().title, self.title)

    def test_form_finds_parent(self):
        parent = Comment.objects.create(user=self.user, title=self.title, text='Tralalelo')
        data = {'text': 'Tralalelo', 'title': self.title.id, 'parent': parent.id}
        form = CommentForm(request=self.request, data=data)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(Comment.objects.last().user, self.user)
        self.assertEqual(Comment.objects.last().title, self.title)
        self.assertEqual(Comment.objects.last().parent, parent)

    def test_form_raises_error_if_title_does_not_exist(self):
        data = {'text': 'Tralalelo', 'title': 999}
        form = CommentForm(request=self.request, data=data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['title'], ['Тайтл не существует'])

    def test_form_raises_error_parent_does_not_exist(self):
        parent = Comment.objects.create(user=self.user, title=self.title, text='Tralalelo')
        title = Title.objects.create(name='Test Title 2', type=Title.MOVIE)
        test_cases = [{'text': 'Tralalelo', 'title': self.title.id, 'parent': 999},
                      {'text': 'Tralalelo', 'title': title.id, 'parent': parent.id}]
        for case in test_cases:
            with self.subTest(case=case):
                form = CommentForm(request=self.request, data=case)
                self.assertFalse(form.is_valid())
                self.assertEqual(form.errors['parent'], ['Ответ для несуществующего комментария'])

    def test_form_raises_error_if_request_is_invalid_when_try_to_save_form(self):
        data = {'text': 'Tralalelo', 'title': self.title}
        with self.assertRaises(TypeError):
            CommentForm(data=data)

    def test_form_does_not_raise_error_for_view(self):
        self.assertTrue(CommentForm())