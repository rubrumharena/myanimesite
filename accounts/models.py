import uuid
from datetime import timedelta

from django.shortcuts import reverse
from django.contrib.auth.models import AbstractUser
from django.core.mail import send_mail
from django.db import models
from django.utils.timezone import now
from django.conf import settings



from titles.models import Title
from lists.models import Folder

# Create your models here.


class EmailVerification(models.Model):
    RESET_PASSWORD = 'reset'
    VERIFY_ACCOUNT = 'verification'
    EXPIRED = 'expired'
    USED = 'used'


    TYPE_CHOICES = (
        (RESET_PASSWORD, 'Сброс пароля'),
        (VERIFY_ACCOUNT, 'Подтверждение учетной записи'),
    )

    code = models.UUIDField(editable=False, unique=True)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    expiration = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    type = models.CharField(max_length=40, choices=TYPE_CHOICES, default=None)
    used = models.BooleanField(default=False)

    def send_verification_email(self):
        if self.type == self.RESET_PASSWORD:
            link = settings.DOMAIN_NAME + reverse('accounts:password_reset', kwargs={'code': self.code, 'user_id': self.user.id})
            subject = 'Сброс пароля'
            message = ('Вы запросили сброс пароля для вашей учётной записи на MYANIMESITE.\n\n'
                       'Чтобы установить новый пароль, пожалуйста, перейдите по следующей ссылке:\n\n'
                       f'{link}\n\n'
                       'Если вы не запрашивали сброс пароля, просто проигнорируйте это письмо. '
                       'Ваш текущий пароль останется без изменений.\n\n'
                       'С уважением,\n'
                       'Команда MYANIMESITE')

        elif self.type == self.VERIFY_ACCOUNT:
            link = settings.DOMAIN_NAME + reverse('accounts:account_verification', kwargs={'code': self.code, 'user_id': self.user.id})
            subject = 'Подтвердите ваш email'
            message = ('Благодарим вас за регистрацию в MYANIMESITE!\n\n'
                'Для завершения регистрации нам необходимо подтвердить ваш адрес электронной почты.\n\n'
                'Пожалуйста, перейдите по ссылке ниже, чтобы подтвердить свой адрес электронной почты:\n\n'
                f'{link}\n\n'
                'Если вы не имеете никакого отношения к MYANIMESITE, пожалуйста, проигнорируйте это письмо.\n\n'
                'С уважением,\n'
                'Команда MYANIMESITE')
        else:
            link = None
        
        if link: 
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[self.user.email],
            )
        else: 
            raise ValueError('Message type is invalid')

    def is_expired(self):
        return self.expiration < now()