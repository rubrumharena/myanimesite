from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.http import HttpRequest

from common.models.bases import BaseListModel
from common.utils.validators import validate_image_size
from titles.models import Title
from lists.models import Folder


# from watchlists.models import Folder


class FolderForm(forms.ModelForm):
    title_id = forms.IntegerField(widget=forms.HiddenInput(), required=False)

    name = forms.CharField(widget=forms.TextInput(
        attrs={'class': 'input-field p-4  h-full !border-[0.09rem] rounded-[15px]',
               'placeholder': 'Добавь своё название'}), required=True, max_length=40)
    description = forms.CharField(widget=forms.Textarea(
        attrs={'class': 'input-field p-4 resize-none h-full !border-[0.09rem] rounded-[15px]',
               'placeholder': 'Напишите что-нибудь...'}), required=False)

    image = forms.ImageField(widget=forms.FileInput(
        attrs={'class': 'hidden z-100 w-full h-full',
               'accept': '.jpg, .jpeg, .png'}), required=False,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png']), validate_image_size(max_size_mb=BaseListModel.MAX_SIZE,
                                                                                        min_width=BaseListModel.MIN_WIDTH,
                                                                                        min_height=BaseListModel.MIN_HEIGHT)])
    is_hidden = forms.BooleanField(widget=forms.CheckboxInput(attrs={'class': 'hidden peer'}), required=False)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)

        super().__init__(*args, **kwargs)

        if not isinstance(self.request, HttpRequest) and self.data:
            raise TypeError(
                'Request is a required parameter to link User and Folder. It must be a Django HttpRequest instance')

        for field in ('name', 'description', 'image', 'is_hidden'):
            value = getattr(self.instance, field)
            value = value.url if value and field == 'image' else value
            value = str(value) if field == 'is_hidden' else value
            self.fields[field].widget.attrs.update({'data-initial': value})

    def save(self, commit=True):
        folder = super().save(commit=False)
        title_id = self.cleaned_data.get('title_id')
        folder.user = self.request.user

        if commit:
            folder.save()
            if title_id:
                folder.titles.add(title_id)

        return folder

    def clean_name(self):
        folder_name = self.cleaned_data.get('name')
        user = self.request.user

        base_q = Folder.objects.filter(name__iexact=folder_name.lower(), user=user)
        queryset = base_q.exclude(id=self.instance.id) if self.instance.id else base_q

        if queryset.exists():
            raise ValidationError('Такое название для папки уже существует')

        return folder_name

    def clean_title_id(self):
        title_id = self.cleaned_data.get('title_id')
        if title_id is not None:
            try:
                title_id = int(title_id)
                Title.objects.get(id=title_id)
            except (ValueError, TypeError, Title.DoesNotExist):
                raise ValidationError('Неизвестный тайтл')

        return title_id

    def clean_image(self):
        image = self.cleaned_data.get('image')

        if self.instance.image:
            if self.instance.image != image:
                self.instance.image.delete(save=False)

        return image

    class Meta:
        model = Folder
        fields = ('name', 'description', 'image', 'is_hidden')
