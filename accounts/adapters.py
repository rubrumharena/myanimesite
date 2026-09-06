from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model

User = get_user_model()


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)

        # If an email is not provided by social, it returns unverified user
        if 'email' not in sociallogin.account.extra_data or sociallogin.account.extra_data['email'] is None:
            return user

        # Otherwise the account considered as verified
        user.is_verified = True
        user.save()
        return user

    def pre_social_login(self, request, sociallogin):
        """
        Invoked just after a user successfully authenticates via a
        social provider, but before the login is actually processed
        (and before the pre_social_login signal is emitted).

        We're trying to solve different use cases:
        - social account already exists, just go on
        - social account has no email or email is unknown, just go on
        - social account's email exists, link social account to existing user
        """

        # Ignore existing social accounts, just do this stuff for new ones
        if sociallogin.is_existing:
            return

        # some social logins don't have an email address, e.g. facebook accounts
        # with mobile numbers only, but allauth takes care of this case so just
        # ignore it
        if 'email' not in sociallogin.account.extra_data or sociallogin.account.extra_data['email'] is None:
            return

        # Check if a user with this email already exists. We match against
        # User.email (not allauth's EmailAddress) because allauth's own
        # uniqueness check (assess_unique_email) also matches against
        # User.email, and accounts can exist without an EmailAddress row
        # (e.g. superusers created via createsuperuser). Matching only
        # against EmailAddress left those accounts unreachable via social
        # login: allauth would refuse to auto-signup a duplicate email, but
        # this adapter would never link it either, so the user got stuck on
        # the manual signup form with no way to complete it.
        # Note: __iexact is used to ignore cases
        try:
            email = sociallogin.account.extra_data['email']
            user = User.objects.get(email__iexact=email)

        # if it does not, let allauth take care of this new social account
        except User.DoesNotExist:
            return

        # if it does, connect this new social login to the existing user
        sociallogin.connect(request, user)
