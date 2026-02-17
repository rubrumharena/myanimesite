from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

from common.models.bases import BaseListModel
from common.utils.validators import validate_image_size
from lists.models import Folder
from titles.models import Title

# from watchlists.models import Folder


class FolderForm(forms.ModelForm):
    title = forms.ModelChoiceField(queryset=Title.objects.all(), widget=forms.HiddenInput(), required=False)

    name = forms.CharField(
        widget=forms.TextInput(
            attrs={
                'class': 'input-field p-4  h-full !border-[0.09rem] rounded-[15px]',
                'placeholder': 'Добавь своё название',
            }
        ),
        required=True,
        max_length=40,
    )
    description = forms.CharField(
        widget=forms.Textarea(
            attrs={
                'class': 'input-field p-4 resize-none h-full !border-[0.09rem] rounded-[15px]',
                'placeholder': 'Напишите что-нибудь...',
            }
        ),
        required=False,
    )

    image = forms.ImageField(
        widget=forms.FileInput(attrs={'class': 'hidden z-100 w-full h-full', 'accept': '.jpg, .jpeg, .png'}),
        required=False,
        validators=[
            FileExtensionValidator(['jpg', 'jpeg', 'png']),
            validate_image_size(
                max_size_mb=BaseListModel.MAX_SIZE,
                min_width=BaseListModel.MIN_WIDTH,
                min_height=BaseListModel.MIN_HEIGHT,
            ),
        ],
    )

    is_hidden = forms.BooleanField(widget=forms.CheckboxInput(attrs={'class': 'hidden peer'}), required=False)
    is_pinned = forms.BooleanField(widget=forms.CheckboxInput(attrs={'class': 'hidden peer'}), required=False)

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request

    def clean(self):
        if self.instance:
            if self.instance.type == Folder.SYSTEM:
                raise ValidationError('Превышение пользовательских прав')
        return super().clean()

    def save(self, commit=True):
        folder = super().save(commit=False)

        title = self.cleaned_data.get('title')
        folder.user = self.request.user

        if commit:
            folder.save()
            if title:
                folder.titles.add(title)

        return folder

    def clean_name(self):
        folder_name = self.cleaned_data.get('name')
        user = self.request.user

        base_q = Folder.objects.filter(name__iexact=folder_name.lower(), user=user)
        queryset = base_q.exclude(id=self.instance.id) if self.instance.id else base_q

        if queryset.exists():
            raise ValidationError('Такое название для папки уже существует')

        return folder_name

    def clean_image(self):
        image = self.cleaned_data.get('image')

        if self.instance.image:
            if self.instance.image != image:
                self.instance.image.delete(save=False)

        return image

    class Meta:
        model = Folder
        fields = ('name', 'description', 'image', 'is_hidden', 'is_pinned')
