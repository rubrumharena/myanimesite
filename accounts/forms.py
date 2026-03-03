from django import forms
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.db import transaction

from accounts.models import EmailVerification
from accounts.tasks import send_email
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
        user = super().save(commit=commit)
        if commit:
            transaction.on_commit(lambda: send_email.delay(user.id, EmailVerification.REGISTER))

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
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise ValidationError('Нет пользователя с таким email.')

        send_email.delay(user.id, EmailVerification.RESET_PASSWORD)

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
