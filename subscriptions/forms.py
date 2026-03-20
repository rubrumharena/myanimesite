from django import forms
from django.forms import ModelChoiceField, RadioSelect

from subscriptions.models import Subscription, UserSubscription


class SubscriptionForm(forms.ModelForm):
    subscription = ModelChoiceField(
        queryset=Subscription.objects.none(),
        widget=RadioSelect(),
    )

    class Meta:
        model = UserSubscription
        fields = ('subscription',)

    def __init__(self, *args, **kwargs):
        subscriptions_qs = kwargs.pop('subscriptions_qs', None)
        super().__init__(*args, **kwargs)

        if subscriptions_qs is None:
            subscriptions_qs = Subscription.objects.order_by('plan')

        self.fields['subscription'].queryset = subscriptions_qs
        self.fields['subscription'].initial = subscriptions_qs.first()
