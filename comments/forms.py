from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from comments.models import Comment
from common.utils.forms import StatusRadioSelect
from titles.models import LibraryEntry


class BaseCommentForm(forms.ModelForm):
    STATUS_LABEL_CLASSES = {
        'not_watched': 'peer-checked/not-watched:border-neutral-400 peer-checked/not-watched:!text-white peer-checked/not-watched:bg-neutral-400/10',
        'current': 'peer-checked/current:border-cyan-400 peer-checked/current:!text-cyan-400 peer-checked/current:bg-cyan-400/10',
        'planned': 'peer-checked/planned:border-pink-500 peer-checked/planned:!text-pink-500 peer-checked/planned:bg-pink-500/10',
        'watched': 'peer-checked/watched:border-green-500 peer-checked/watched:!text-green-500 peer-checked/watched:bg-green-500/10',
        'skipped': 'peer-checked/skipped:border-red-500 peer-checked/skipped:!text-red-500 peer-checked/skipped:bg-red-500/10',
    }
    text = forms.CharField(
        max_length=5000,
        widget=forms.Textarea(
            attrs={
                'class': 'min-h-25 max-h-100 p-2.5 w-full text-base resize-none overflow-y-auto',
                'placeholder': 'Напишите отзыв...',
                'rows': 1,
                'data-autogrow': '',
            }
        ),
    )
    status = forms.ChoiceField(
        choices=LibraryEntry.STATUS_CHOICES,
        widget=StatusRadioSelect(),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        self.user_id = kwargs.pop('user_id', None)
        self.title_id = kwargs.pop('title_id', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        comment = super().save(commit=False)
        if not self.instance.pk:
            comment.user_id = self.user_id
            comment.title_id = self.title_id

        if commit:
            comment.save()

        return comment

    def connect_entry(self, comment):
        status = self.cleaned_data.get('status') or LibraryEntry.NOT_WATCHED
        rating = self.cleaned_data.get('rating', 0)
        entry, _ = LibraryEntry.objects.update_or_create(
            title_id=comment.title_id, user_id=comment.user_id, defaults={'status': status, 'rating': rating}
        )
        comment.review = entry

    class Meta:
        model = Comment
        fields = ('text',)


class ReviewForm(BaseCommentForm):
    rating = forms.FloatField(
        widget=forms.HiddenInput(attrs={'data-rating-input': True}),
        required=False,
        min_value=0,
        max_value=10,
    )

    def save(self, commit=True):
        comment = super().save(commit=False)

        self.connect_entry(comment)

        if commit:
            comment.save()
        return comment


class CommentForm(BaseCommentForm):
    parent_id = forms.IntegerField(
        widget=forms.HiddenInput(attrs={'id': 'reply-parent'}),
        required=False,
    )
    comment_id = forms.IntegerField(
        widget=forms.HiddenInput(attrs={'id': 'edit-id'}),
        required=False,
    )
    rating = forms.FloatField(
        widget=forms.HiddenInput(attrs={'data-rating-input': ''}),
        required=False,
        min_value=0,
        max_value=10,
    )
    is_review = forms.BooleanField(
        widget=forms.HiddenInput(attrs={'data-review-flag': '', 'value': '0'}), required=False
    )

    def clean(self):
        cleaned = super().clean()
        if self.instance.pk:
            return cleaned

        parent_id = cleaned.get('parent_id')
        is_review = cleaned.get('is_review')

        if parent_id and is_review:
            raise ValidationError(_('Рецензию нельзя написать в ответ на комментарий'))

        if is_review:
            exists = Comment.objects.filter(
                user_id=self.user_id,
                title_id=self.title_id,
                review__isnull=False,
            ).exists()
            if exists:
                raise ValidationError(_('Вы уже написали рецензию. Измените или удалите её'))

        return cleaned

    def save(self, commit=True):
        comment = super().save(commit=False)
        if not self.instance.pk:
            comment.parent_id = self.cleaned_data.get('parent_id')

        if self.cleaned_data.get('is_review'):
            self.connect_entry(comment)

        if commit:
            comment.save()

        return comment
