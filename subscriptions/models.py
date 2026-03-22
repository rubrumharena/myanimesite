from django.conf import settings
from django.core.mail import send_mail
from django.db import models

from users.models import User

# Create your models here.


class Subscription(models.Model):
    price = models.DecimalField(max_digits=10, decimal_places=2)
    name = models.CharField(max_length=20)
    plan = models.SmallIntegerField()
    stripe_price_id = models.CharField(max_length=30)


class UserSubscription(models.Model):
    ACTIVE = 'active'
    PAST_DUE = 'past_due'
    CANCELLED = 'cancelled'

    STATUS_CHOICES = ((ACTIVE, 'Активная'), (PAST_DUE, 'Просрочена'), (CANCELLED, 'Отменена'))

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, blank=True)
    stripe_subscription_id = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PAST_DUE)
    ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def send_email(self) -> None:
        if self.status == self.ACTIVE:
            subject = 'Подписка успешно подключена'
            message = f"""
            Здравствуйте!

            Оплата вашей подписки "{self.subscription.name}" на MYANIMESITE успешно подтверждена.
            Квитанция по оплате сформирована, а подписка уже подключена к вашей учётной записи.

            Теперь вы можете пользоваться всеми возможностями подписки.
            
            Следующая квитанция будет отправлена {self.ends_at.strftime('%d.%m.%Y')}

            Если у вас возникнут вопросы, пожалуйста, свяжитесь с нами.
            
            С уважением,
            Команда MYANIMESITE
            """

        elif self.status == self.PAST_DUE:
            subject = 'Не удалось списать оплату за подписку'
            message = f"""
                Здравствуйте!

                Нам не удалось списать оплату за подписку "{self.subscription.name}" на MYANIMESITE.

                Из-за этого подписка не будет действовать на вашем аккаунте.
                Пожалуйста, проверьте способ оплаты и при необходимости обновите платёжные данные.

                Если у вас возникнут вопросы, пожалуйста, свяжитесь с нами.

                С уважением,
                Команда MYANIMESITE
                """

        elif self.status == self.CANCELLED:
            subject = 'Подписка отключена'
            message = f"""
                Здравствуйте!

                Ваша подписка "{self.subscription.name}" на MYANIMESITE была отключена.

                Доступ к возможностям подписки больше недоступен.
                Вы можете подключить подписку снова в любое удобное время.

                Если у вас возникнут вопросы, пожалуйста, свяжитесь с нами.

                С уважением,
                Команда MYANIMESITE
                """
        else:
            raise ValueError('Status is invalid')

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[self.user.email],
        )
