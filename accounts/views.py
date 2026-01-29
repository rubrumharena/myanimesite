from django.contrib.auth import authenticate, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.db import transaction
from django.http import HttpResponseRedirect, Http404
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic.base import TemplateView
from django.views.generic.edit import CreateView, FormView, DeleteView
from django.contrib import messages

from common.views.mixins import PageTitleMixin

from accounts.forms import UserLoginForm, UserRegisterForm, EmailForm, PasswordResetForm
from users.models import User
from accounts.models import EmailVerification


class WelcomeView(PageTitleMixin, TemplateView):
    template_name = 'accounts/welcome.html'
    page_title = 'Добро пожаловать! | MYANIMESITE'


class RegistrationView(PageTitleMixin, CreateView):
    template_name = 'accounts/register.html'
    page_title = 'Регистрация | MYANIMESITE'
    model = User
    form_class = UserRegisterForm
    success_url = reverse_lazy('index')

    # The logic for direct login after registration
    def form_valid(self, form):
        response = super().form_valid(form)

        user = authenticate(username=form.cleaned_data['username'], password=form.cleaned_data['password1'])

        if user:
            login(self.request, user)

        return response


class UserLoginView(PageTitleMixin, LoginView):
    template_name = 'accounts/login.html'
    page_title = 'Авторизация | MYANIMESITE'
    form_class = UserLoginForm


class RecoveryView(PageTitleMixin, FormView):
    page_title = 'Восстановление пароля | MYANIMESITE'
    form_class = EmailForm
    template_name = 'accounts/recovery.html'
    success_url = reverse_lazy('accounts:recovery')

    def form_valid(self, form):
        messages.success(self.request, message=form.cleaned_data['email'], extra_tags='email-sent')
        return super().form_valid(form)


class EmailVerificationView(PageTitleMixin, TemplateView):
    page_title = 'Верификация аккаунта | MYANIMESITE'
    template_name = 'accounts/email_verification.html'

    def get(self, request, *args, **kwargs):
        code = kwargs['code']
        user_id = kwargs['user_id']

        record = get_object_or_404(EmailVerification, code=code, user_id=user_id)

        if record.is_expired():
            return HttpResponseRedirect(reverse('accounts:verification_message',
                                                kwargs={'code': code, 'user_id': record.user_id,
                                                        'status': EmailVerification.EXPIRED}))

        user = User.objects.get(id=user_id)

        with transaction.atomic():
            print('dfdfdf')
            user.is_verified, record.used = True, True
            user.save(), record.save()

        return super().get(request, *args, **kwargs)


class VerificationMessageView(PageTitleMixin, TemplateView):
    page_title = 'Сообщение о верификации | MYANIMESITE'
    template_name = 'accounts/verification_message.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        status = kwargs['status']
        record = get_object_or_404(EmailVerification, code=kwargs['code'], user_id=kwargs['user_id'])
        expired, used = EmailVerification.EXPIRED, EmailVerification.USED

        if ((status == expired and not record.is_expired()) or
                (status == used and not record.used) or status not in [expired, used]):
            raise Http404
        return {**context, 'status': status, 'type': record.type}


class PasswordResetView(PageTitleMixin, FormView):
    page_title = 'Сброс пароля | MYANIMESITE'
    form_class = PasswordResetForm
    template_name = 'accounts/password_reset.html'

    def get_success_url(self):
        return reverse('accounts:verification_message',
                       kwargs={'user_id': self.kwargs['user_id'], 'code': self.kwargs['code'],
                               'status': EmailVerification.USED})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = get_object_or_404(User, id=self.kwargs['user_id'])
        return kwargs

    def form_valid(self, form):
        kwargs = self.kwargs
        record = EmailVerification.objects.get(code=kwargs['code'], user_id=kwargs['user_id'])
        record.used = True
        record.save()
        return super().form_valid(form)

    def get(self, request, *args, **kwargs):
        code = kwargs['code']
        user_id = kwargs['user_id']

        record = get_object_or_404(EmailVerification, code=code, user_id=user_id)

        if record.is_expired():
            return HttpResponseRedirect(reverse('accounts:verification_message',
                                                kwargs={'code': code, 'user_id': record.user_id,
                                                        'status': EmailVerification.EXPIRED}))
        elif record.used:
            return HttpResponseRedirect(reverse('accounts:verification_message',
                                                    kwargs={'code': code, 'user_id': record.user_id,
                                                            'status': EmailVerification.USED}))

        return super().get(request, *args, **kwargs)


class DeleteAccountView(LoginRequiredMixin, DeleteView):
    model = User
    success_url = reverse_lazy('index')

    def get_object(self, queryset=None):
        return self.request.user