from django import forms
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext, gettext_lazy as _

from accounts.models import EmailVerification
from accounts.tasks import send_email
from users.models import User


class UserLoginForm(AuthenticationForm):
    """
    A form for authenticating users using email or username and password.
    """

    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'Введите ваш логин или email'}),
        required=True,
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'input-field', 'placeholder': 'Введите ваш текущий пароль'}),
        required=True,
    )

    def clean_username(self):
        """
        Allow authentication using either username or email.

        If the input contains '@', it is treated as an email.
        The corresponding username is retrieved and returned,
        so that authentication proceeds using the standard username field.

        If no user with the given email exists, the original value is returned.
        """
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
    """
    A form for registration users.
    """

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

    def save(self, commit=True):
        """
        Save user instance and trigger email verification asynchronously.

        If commit is True, schedules a Celery task to send a confirmation email
        after the database transaction is successfully committed.

        Using transaction.on_commit ensures that the email is only sent if the
        user is fully saved in the database, preventing inconsistencies where
        an email is sent but the user record does not exist.
        """
        user = super().save(commit=commit)
        if commit:
            transaction.on_commit(lambda: send_email.delay(user.id, EmailVerification.REGISTER))

        return user

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')


class EmailForm(forms.Form):
    """
    A form that lets user recover password using email address.
    """

    email = forms.CharField(
        widget=forms.EmailInput(attrs={'class': 'input-field', 'placeholder': _('Введите ваш email')}), required=True
    )

    def clean_email(self):
        """
        Integrate additional verification to ensure the corresponding email exists.

        If email exists in the DB, the email to reset password is sent.

        Otherwise, ValidationError is raised.
        """
        email = self.cleaned_data['email']
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise ValidationError(gettext('Нет пользователя с таким email.'))

        send_email.delay(user.id, EmailVerification.RESET_PASSWORD)

        return email


class PasswordResetForm(SetPasswordForm):
    """
    A form that lets user reset password.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['new_password1'].widget.attrs.update(
            {'class': 'input-field', 'placeholder': _('Введите ваш новый пароль')}
        )

        self.fields['new_password2'].widget.attrs.update(
            {'class': 'input-field', 'placeholder': _('Введите пароль ещё раз')}
        )
