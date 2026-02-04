from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator

from comments.models import Comment


class CommentForm(forms.ModelForm):
    text = forms.CharField(
        max_length=500,
        validators=[MaxLengthValidator(500)],
        widget=forms.Textarea(
            attrs={
                'class': 'min-h-16 h-16 p-2.5 rounded-[5px] bg-secondary border-[0.09rem] border-[#2b2c2d] w-full text-text-gray focus:border-primary',
                'placeholder': 'Напишите отзыв...',
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
