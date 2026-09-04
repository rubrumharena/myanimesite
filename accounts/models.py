from django.conf import settings
from django.core.mail import send_mail
from django.db import models
from django.shortcuts import reverse
from django.utils.timezone import now
from django.utils.translation import gettext_lazy, gettext as _

# Create your models here.


class EmailVerification(models.Model):
    RESET_PASSWORD = 'reset'
    VERIFY_EMAIL = 'emai_verification'
    REGISTER = 'registration'
    EXPIRED = 'expired'
    USED = 'used'

    TYPE_CHOICES = (
        (RESET_PASSWORD, gettext_lazy('Сброс пароля')),
        (VERIFY_EMAIL, gettext_lazy('Подтверждение учетной записи')),
        (REGISTER, gettext_lazy('Завершение регистрации')),
    )

    code = models.UUIDField(editable=False, unique=True)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    expiration = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    type = models.CharField(max_length=40, choices=TYPE_CHOICES, default=None)
    used = models.BooleanField(default=False)

    def send_verification_email(self) -> None:
        if self.type == self.RESET_PASSWORD:
            link = settings.DOMAIN_NAME + reverse(
                'accounts:password_reset', kwargs={'code': self.code, 'user_id': self.user.id}
            )
            subject = _('Сброс пароля')
            message = _(
                'Вы запросили сброс пароля для вашей учётной записи на MYANIMESITE.\n'
                'Чтобы установить новый пароль, пожалуйста, перейдите по следующей ссылке:\n'
                '%(link)s\n\n'
                'Если вы не запрашивали сброс пароля, просто проигнорируйте это письмо.\n'
                'Ваш текущий пароль останется без изменений.\n'
                'С уважением,\n'
                'Команда MYANIMESITE\n'
                ) % {'link': link}

        elif self.type == self.REGISTER:
            link = settings.DOMAIN_NAME + reverse(
                'accounts:account_verification', kwargs={'code': self.code, 'user_id': self.user.id}
            )
            subject = _('Завершите регистрацию')
            message = _(
                'Благодарим вас за регистрацию на MYANIMESITE!\n'
                'Для завершения регистрации нам необходимо подтвердить ваш адрес электронной почты.\n'
                'Пожалуйста, перейдите по ссылке ниже, чтобы подтвердить свой адрес электронной почты:\n'
                '%(link)s\n\n'
                'Если вы не имеете никакого отношения к MYANIMESITE, пожалуйста, проигнорируйте это письмо.\n'
                'С уважением,\n'
                'Команда MYANIMESITE\n'
            ) % {'link': link}

        elif self.type == self.VERIFY_EMAIL:
            link = settings.DOMAIN_NAME + reverse(
                'accounts:account_verification', kwargs={'code': self.code, 'user_id': self.user.id}
            )
            subject = _('Подтвердите ваш email')
            message = _(
                'Мы получили запрос на смену адреса электронной почты для вашей учётной записи на MYANIMESITE.\n'
                'Для подтверждения вашего адреса электронной почты, пожалуйста, перейдите по следующей ссылке:\n'
                '%(link)s\n\n'
                'Если вы не имеете отношения к MYANIMESITE, просто проигнорируйте это письмо.\n'
                'С уважением,\n'
                'Команда MYANIMESITE\n'
                ) % {'link': link}
        else:
            raise ValueError('Message type is invalid')

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[self.user.email],
        )

    def is_expired(self) -> bool:
        return self.expiration < now()
