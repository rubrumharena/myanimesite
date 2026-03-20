from django.urls import path

from subscriptions.views import (
    SubscriptionCanceledTemplateView,
    SubscriptionCreateView,
    SubscriptionSuccessTemplateView,
    SubscriptionTemplateView,
)

app_name = 'subscriptions'

urlpatterns = [
    path('issue_order/', SubscriptionTemplateView.as_view(), name='issue_order'),
    path('checkout_order/', SubscriptionCreateView.as_view(), name='checkout_order'),
    path('order_success/', SubscriptionSuccessTemplateView.as_view(), name='order_success'),
    path('order_canceled/', SubscriptionCanceledTemplateView.as_view(), name='order_canceled'),
]
