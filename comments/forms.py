from django import forms
from django.core.exceptions import ValidationError
from django.http import HttpRequest

from comments.models import Comment
from titles.models import Title


class CommentForm(forms.ModelForm):
    text = forms.CharField(
        widget=forms.Textarea(
            attrs={
                'class': 'min-h-16 h-16 p-2.5 rounded-[5px] bg-secondary border-[0.09rem] border-[#2b2c2d] w-full text-text-gray focus:border-primary',
                'placeholder': 'Напишите отзыв...',
            }
        )
    )
    title = forms.IntegerField(widget=forms.HiddenInput())
    parent = forms.IntegerField(widget=forms.HiddenInput(), required=False)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if not isinstance(self.request, HttpRequest) and self.data:
            raise TypeError(
                'Request is a required parameter to link User and Comment. It must be a Django HttpRequest instance'
            )

    def clean_title(self):
        try:
            return Title.objects.get(id=self.cleaned_data['title'])
        except Title.DoesNotExist:
            raise ValidationError('Тайтл не существует')

    def clean_parent(self):
        parent_id = self.cleaned_data['parent']
        title = self.cleaned_data.get('title')
        if parent_id and title:
            try:
                return Comment.objects.get(id=parent_id, title=title)
            except Comment.DoesNotExist:
                raise ValidationError('Ответ для несуществующего комментария')

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.user = self.request.user
        if commit:
            instance.save()
        return instance

    class Meta:
        model = Comment
        fields = ('text', 'title', 'parent')
