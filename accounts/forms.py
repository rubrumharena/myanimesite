import uuid
from datetime import timedelta

from django import forms
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.utils.timezone import now

from accounts.models import EmailVerification
from users.models import User


class UserLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'Введите ваш логин или email'}),
        required=True,
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'input-field', 'placeholder': 'Введите ваш текущий пароль'}),
        required=True,
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')

        if '@' in username:
            try:
                user = User.objects.get(email=username)
                username = user.username
            except User.DoesNotExist:
                pass

        return username

    class Meta:
        model = User
        fields = ('username', 'password')


class UserRegisterForm(UserCreationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'Введите ваш логин'}), required=True
    )
    email = forms.CharField(
        widget=forms.EmailInput(attrs={'class': 'input-field', 'placeholder': 'Введите ваш email'}), required=True
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'input-field', 'placeholder': 'Введите ваш пароль'}), required=True
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'input-field', 'placeholder': 'Введите пароль ещё раз'}),
        required=True,
    )

    # We need to modify save here (no in the model), because we cannot manipulate user without commit
    def save(self, commit=True):
        if commit:
            user = super().save()
            verification_record = EmailVerification.objects.create(
                code=uuid.uuid4(),
                user=user,
                expiration=now() + timedelta(hours=1),
                type=EmailVerification.REGISTER,
            )
            verification_record.send_verification_email()
            return user

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')


class EmailForm(forms.Form):
    email = forms.CharField(
        widget=forms.EmailInput(attrs={'class': 'input-field', 'placeholder': 'Введите ваш email'}), required=True
    )

    def clean_email(self):
        email = self.cleaned_data['email']
        user = User.objects.filter(email__iexact=email)
        if not user.exists():
            raise ValidationError('Нет пользователя с таким email.')

        verification_record = EmailVerification.objects.create(
            code=uuid.uuid4(),
            user=user.first(),
            expiration=now() + timedelta(hours=1),
            type=EmailVerification.RESET_PASSWORD,
        )
        verification_record.send_verification_email()

        return email


class PasswordResetForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['new_password1'].widget.attrs.update(
            {'class': 'input-field', 'placeholder': 'Введите ваш новый пароль'}
        )

        self.fields['new_password2'].widget.attrs.update(
            {'class': 'input-field', 'placeholder': 'Введите пароль ещё раз'}
        )
