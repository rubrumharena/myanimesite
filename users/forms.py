import uuid
from datetime import timedelta

from django.contrib.auth.forms import UserChangeForm, PasswordChangeForm
from django import forms
from django.core.validators import FileExtensionValidator
from django.utils.timezone import now
from django.core.exceptions import ValidationError

from accounts.models import EmailVerification
from common.utils.validators import validate_image_size
from users.models import User


class ProfileUpdateForm(UserChangeForm):
    username = forms.CharField(widget=forms.TextInput(
        attrs={'class': 'input-field',
               'placeholder': 'Введите ваше имя пользователя'}), required=True)
    name = forms.CharField(widget=forms.TextInput(
        attrs={'class': 'input-field',
               'placeholder': 'Введите ваше отображаемое имя'}), required=False)
    bio = forms.CharField(widget=forms.Textarea(
        attrs={'class': 'input-field !border-[0.09rem] min-h-40 p-4 rounded-3xl bg-transparent resize-none',
               'placeholder': 'Напишите что-нибудь...'}), required=False)

    class Meta:
        model = User
        fields = ('username', 'name', 'bio')


class PasswordUpdateForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['old_password'].widget.attrs = {'class': 'input-field', 'placeholder': 'Введите ваш пароль',
                                                    'autocomplete': 'new-password'}
        self.fields['new_password1'].widget.attrs.update(
            {'class': 'input-field', 'placeholder': 'Введите ваш новый пароль'})
        self.fields['new_password2'].widget.attrs.update(
            {'class': 'input-field', 'placeholder': 'Введите пароль ещё раз'})


class EmailUpdateForm(UserChangeForm):
    email = forms.CharField(widget=forms.EmailInput(
        attrs={'class': 'input-field',
               'placeholder': 'Введите ваш email'}), required=True)

    def clean_email(self):
        email = (self.cleaned_data.get("email") or '').lower()

        is_email_prev = (self.instance.email or '').lower() == email
        if is_email_prev:
            raise ValidationError('Новый email не отличается от предыдущего.')

        is_email_taken = User.objects.filter(email__iexact=email).exclude(id=self.instance.id).exists()
        if is_email_taken:
            raise ValidationError('Пользователь с таким email уже существует.')

        return email

    def save(self, commit=True):
        user = super().save(commit=False)

        if commit:
            user.is_verified = False
            user.save()
            record = EmailVerification.objects.create(code=uuid.uuid4(), user=user,
                                                      expiration=now() + timedelta(hours=1),
                                                      type=EmailVerification.VERIFY_ACCOUNT)
            record.send_verification_email()
        return user

    class Meta:
        model = User
        fields = ('email',)


class AvatarUpdateForm(UserChangeForm):
    avatar = forms.ImageField(widget=forms.FileInput(
        attrs={'class': 'hidden',
               'accept': '.jpg, .jpeg, .png'}), required=False,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png']),
                    validate_image_size(max_size_mb=User.MAX_AVATAR_SIZE,
                                        min_width=User.MIN_AVATAR_WIDTH,
                                        min_height=User.MIN_AVATAR_HEIGHT)])

    class Meta:
        model = User
        fields = ('avatar',)


class HistoryVisibilityForm(UserChangeForm):
    is_history_public = forms.ChoiceField(widget=forms.CheckboxInput(
        attrs={'class': 'sr-only peer'}), required=False)

    class Meta:
        model = User
        fields = ('is_history_public',)
