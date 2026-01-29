import uuid

from django.test import TestCase
from unittest.mock import patch
from django.utils.timezone import now
from datetime import timedelta
from django.shortcuts import reverse
from django.conf import settings

from accounts.models import EmailVerification
from users.models import User


class EmailVerificationModelTestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='test_user', email='test@email.com', password='123456')
        self.email_data = {'from_email': settings.EMAIL_HOST_USER, 'recipient_list': [self.user.email]}

    @staticmethod
    def _build_message_text(link, email_type):
        if email_type == EmailVerification.RESET_PASSWORD:
            return ('Вы запросили сброс пароля для вашей учётной записи на MYANIMESITE.\n\n'
                       'Чтобы установить новый пароль, пожалуйста, перейдите по следующей ссылке:\n\n'
                       f'{link}\n\n'
                       'Если вы не запрашивали сброс пароля, просто проигнорируйте это письмо. '
                       'Ваш текущий пароль останется без изменений.\n\n'
                       'С уважением,\n'
                       'Команда MYANIMESITE')
        elif email_type == EmailVerification.VERIFY_ACCOUNT:
            return ('Благодарим вас за регистрацию в MYANIMESITE!\n\n'
                    'Для завершения регистрации нам необходимо подтвердить ваш адрес электронной почты.\n\n'
                    'Пожалуйста, перейдите по ссылке ниже, чтобы подтвердить свой адрес электронной почты:\n\n'
                    f'{link}\n\n'
                    'Если вы не имеете никакого отношения к MYANIMESITE, пожалуйста, проигнорируйте это письмо.\n\n'
                    'С уважением,\n'
                    'Команда MYANIMESITE')


    @patch('accounts.models.send_mail')
    def test_when_account_verification(self, mock_send_mail):
        code = uuid.uuid4()
        record = EmailVerification.objects.create(user=self.user, code=code,
                                                  expiration=now() + timedelta(hours=1), type=EmailVerification.VERIFY_ACCOUNT)
        link = settings.DOMAIN_NAME + reverse('accounts:account_verification', kwargs={'code': code, 'user_id': self.user.id})
        self.email_data['message'] = self._build_message_text(link, EmailVerification.VERIFY_ACCOUNT)
        self.email_data['subject'] = 'Подтвердите ваш email'

        record.send_verification_email()
        mock_send_mail.assert_called_with(**self.email_data)


    @patch('accounts.models.send_mail')
    def test_when_recovery(self, mock_send_mail):
        code = uuid.uuid4()
        record = EmailVerification.objects.create(user=self.user, code=code,
                                                  expiration=now() + timedelta(hours=1), type=EmailVerification.RESET_PASSWORD)
        link = settings.DOMAIN_NAME + reverse('accounts:password_reset', kwargs={'code': code, 'user_id': self.user.id})
        self.email_data['message'] = self._build_message_text(link, EmailVerification.RESET_PASSWORD)
        self.email_data['subject'] = 'Сброс пароля'

        record.send_verification_email()
        mock_send_mail.assert_called_with(**self.email_data)

    def test_email_type_is_invalid(self):
        code = uuid.uuid4()
        record = EmailVerification.objects.create(user=self.user, code=code,
                                                  expiration=now() + timedelta(hours=1), type='test')

        with self.assertRaises(ValueError):
            record.send_verification_email()

