from django.conf import settings
from django.core.mail import send_mail
from django.db import models
from django.shortcuts import reverse
from django.utils.timezone import now

# Create your models here.


class EmailVerification(models.Model):
    RESET_PASSWORD = 'reset'
    VERIFY_EMAIL = 'emai_verification'
    REGISTER = 'registration'
    EXPIRED = 'expired'
    USED = 'used'

    TYPE_CHOICES = (
        (RESET_PASSWORD, 'Сброс пароля'),
        (VERIFY_EMAIL, 'Подтверждение учетной записи'),
        (REGISTER, 'Завершение регистрации'),
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
            subject = 'Сброс пароля'
            message = f"""
                Вы запросили сброс пароля для вашей учётной записи на MYANIMESITE.
                Чтобы установить новый пароль, пожалуйста, перейдите по следующей ссылке:
                {link}
                Если вы не запрашивали сброс пароля, просто проигнорируйте это письмо. 
                Ваш текущий пароль останется без изменений.
                С уважением,
                Команда MYANIMESITE
                """

        elif self.type == self.REGISTER:
            link = settings.DOMAIN_NAME + reverse(
                'accounts:account_verification', kwargs={'code': self.code, 'user_id': self.user.id}
            )
            subject = 'Завершите регистрацию'
            message = f"""
                Благодарим вас за регистрацию на MYANIMESITE!
                Для завершения регистрации нам необходимо подтвердить ваш адрес электронной почты.
                Пожалуйста, перейдите по ссылке ниже, чтобы подтвердить свой адрес электронной почты:
                {link}\n\n'
                Если вы не имеете никакого отношения к MYANIMESITE, пожалуйста, проигнорируйте это письмо.
                С уважением,
                Команда MYANIMESITE
                """
        elif self.type == self.VERIFY_EMAIL:
            link = settings.DOMAIN_NAME + reverse(
                'accounts:account_verification', kwargs={'code': self.code, 'user_id': self.user.id}
            )
            subject = 'Подтвердите ваш email'
            message = f"""
                Мы получили запрос на смену адреса электронной почты для вашей учётной записи на MYANIMESITE.
                Для подтверждения вашего адреса электронной почты, пожалуйста, перейдите по следующей ссылке:
                {link}
                Если вы не имеете отношения к MYANIMESITE, просто проигнорируйте это письмо.
                С уважением,
                Команда MYANIMESITE
                """
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
