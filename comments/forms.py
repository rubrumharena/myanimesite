from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator
from django.shortcuts import reverse

from comments.models import Comment


class FilterRadioSelect(forms.RadioSelect):
    def __init__(self, *args, title_id=None, **kwargs):
        self.title_id = title_id
        super().__init__(*args, **kwargs)

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        option['attrs']['class'] = f'sr-only peer/{value}'

        if self.title_id is not None:
            option['attrs']['data-url'] = (
                reverse(
                    'comments:comments',
                    kwargs={
                        'title_id': self.title_id,
                    },
                )
                + f'?filter_by={value}'
            )
        return option


class CommentForm(forms.ModelForm):
    ALL = 'all'
    REVIEWS = 'reviews'
    FEEDBACKS = 'feedbacks'

    BASE_CLASSES = 'check-button'
    FILTER_BY_LABEL_CLASSES = {
        FEEDBACKS: f'{BASE_CLASSES} peer-checked/feedbacks:border-cyan-400 peer-checked/feedbacks:!text-cyan-400 peer-checked/feedbacks:bg-cyan-400/10',
        REVIEWS: f'{BASE_CLASSES} peer-checked/reviews:border-cyan-400 peer-checked/reviews:!text-cyan-400 peer-checked/reviews:bg-cyan-400/10',
        ALL: f'{BASE_CLASSES} peer-checked/all:border-cyan-400 peer-checked/all:!text-cyan-400 peer-checked/all:bg-cyan-400/10',
    }
    FILTER_CHOICES = [
        (ALL, 'Все'),
        (REVIEWS, 'Рецензии'),
        (FEEDBACKS, 'Комментарии'),
    ]

    text = forms.CharField(
        max_length=5000,
        validators=[MaxLengthValidator(5000)],
        widget=forms.Textarea(
            attrs={
                'class': 'min-h-25 max-h-100 p-2.5 w-full text-neutral-400 text-base resize-none overflow-y-auto',
                'placeholder': 'Напишите отзыв...',
                'rows': 1,
                'data-autogrow': '',
            }
        ),
    )
    parent = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    rating = forms.FloatField(widget=forms.HiddenInput(), required=False, max_value=10)
    is_review = forms.BooleanField(widget=forms.HiddenInput(), required=False)

    filter_by = forms.ChoiceField(widget=FilterRadioSelect(), choices=FILTER_CHOICES, required=False)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.title = kwargs.pop('title', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        parent = cleaned_data['parent']
        is_review = cleaned_data.get('is_review')
        print(is_review)
        if parent is not None and is_review:
            raise ValidationError('Невозможно написать рецензию под чужим отзывом')

    def clean_is_review(self):
        is_review = self.cleaned_data['is_review']
        if is_review:
            review = Comment.objects.filter(user=self.request.user, title=self.title, is_review=True).first()
            if review:
                self.add_error(None, f'Вы уже написали рецензию для "{self.title.name}". Измените или удалите её')
        return is_review

    def clean_parent(self):
        parent_id = self.cleaned_data['parent']
        title = self.title
        if parent_id and title:
            try:
                return Comment.objects.get(id=parent_id, title=title)
            except Comment.DoesNotExist:
                raise ValidationError('Отправлен ответ для несуществующего комментария!')
        return None

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.user = self.request.user
        instance.title = self.title
        if commit:
            instance.save()
        return instance

    class Meta:
        model = Comment
        fields = ('text', 'parent', 'rating', 'is_review')
