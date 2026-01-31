from django.contrib.auth.views import LogoutView
from django.urls import path

from accounts.views import (
    DeleteAccountView,
    EmailVerificationView,
    PasswordResetView,
    RecoveryView,
    RegistrationView,
    UserLoginView,
    VerificationMessageView,
    WelcomeView,
)

app_name = 'accounts'

urlpatterns = [
    path('', WelcomeView.as_view(), name='welcome'),
    path('register/', RegistrationView.as_view(), name='register'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('delete_account/', DeleteAccountView.as_view(), name='delete_account'),
    path('verify/<str:user_id>/<str:code>/', EmailVerificationView.as_view(), name='account_verification'),
    path('recovery/', RecoveryView.as_view(), name='recovery'),
    path('reset/<str:user_id>/<str:code>/', PasswordResetView.as_view(), name='password_reset'),
    path(
        'message/<str:user_id>/<str:code>/<str:status>/', VerificationMessageView.as_view(), name='verification_message'
    ),
]
