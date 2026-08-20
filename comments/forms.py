from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator

from comments.models import Comment


class CommentForm(forms.ModelForm):
    text = forms.CharField(
        max_length=5000,
        validators=[MaxLengthValidator(500)],
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

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.title = kwargs.pop('title', None)
        super().__init__(*args, **kwargs)

    def clean_parent(self):
        parent_id = self.cleaned_data['parent']
        title = self.title
        if parent_id and title:
            try:
                return Comment.objects.get(id=parent_id, title=title)
            except Comment.DoesNotExist:
                raise ValidationError('Отправлен ответ для несуществующего комментария!')

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.user = self.request.user
        instance.title = self.title
        if commit:
            instance.save()
        return instance

    class Meta:
        model = Comment
        fields = ('text', 'parent')
