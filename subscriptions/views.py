from datetime import timedelta, datetime
from http import HTTPStatus

import stripe
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F
from django.db.models.functions import Round
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import reverse
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import CreateView, TemplateView
from django.utils import timezone

from subscriptions.forms import SubscriptionForm
from subscriptions.models import Subscription, UserSubscription
from subscriptions.webhook_handlers import fulfill_subscription, handle_payment_failed, handle_subscription_canceled

# Create your views here.

stripe.api_key = settings.STRIPE_SECRET_KEY


class SubscriptionSuccessTemplateView(TemplateView):
    template_name = 'subscriptions/success.html'


class SubscriptionCanceledTemplateView(TemplateView):
    template_name = 'subscriptions/cancel.html'


class SubscriptionTemplateView(TemplateView):
    template_name = 'subscriptions/premium_popup.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        subscriptions = Subscription.objects.order_by('plan')
        min_plan = subscriptions.first()

        if not min_plan:
            return context

        context['form'] = SubscriptionForm(subscriptions_qs=subscriptions)
        subscriptions = subscriptions.annotate(
            economy=Round(100 - ((F('price') * 100) / (min_plan.price * F('plan')))),
            real_price=Round(F('price') / F('plan'), 2),
        )

        context['plans'] = list(zip(subscriptions, context['form']['subscription']))
        return context

    def get(self, request, *args, **kwargs):
        html = render_to_string(self.template_name, self.get_context_data(), request)
        return JsonResponse(data={'html': html}, status=HTTPStatus.OK)


class SubscriptionCreateView(LoginRequiredMixin, CreateView):
    form_class = SubscriptionForm

    def form_valid(self, form):
        sub = form.cleaned_data['subscription']
        meta = {'subscription_id': sub.id, 'user_id': self.request.user.id}

        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    'price': sub.stripe_price_id,
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=settings.DOMAIN_NAME + reverse('subscriptions:order_success'),
            cancel_url=settings.DOMAIN_NAME + reverse('subscriptions:order_canceled'),
            customer_email=self.request.user.email,
            subscription_data = {'metadata': meta},
        )
        return HttpResponseRedirect(checkout_session.url, status=HTTPStatus.SEE_OTHER)


@csrf_exempt
def stripe_webhook_view(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return HttpResponse(status=HTTPStatus.BAD_REQUEST)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=HTTPStatus.BAD_REQUEST)

    data = event['data']['object']
    if event['type'] == 'invoice.paid':
        fulfill_subscription(data['subscription'])
    elif event['type'] == 'invoice.payment_failed':
        handle_payment_failed(data['subscription'])
    elif event['type'] == 'customer.subscription.deleted':
        handle_subscription_canceled(data['subscription'])

    return HttpResponse(status=HTTPStatus.OK)

