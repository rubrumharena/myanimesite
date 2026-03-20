from http import HTTPStatus

import stripe
from django.conf import settings
from django.db.models import F
from django.db.models.functions import Round
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import reverse
from django.template.loader import render_to_string
from django.views.generic import CreateView, TemplateView

from subscriptions.forms import SubscriptionForm
from subscriptions.models import Subscription

# Create your views here.

stripe.api_key = settings.STRIPE_SECRET_KEY


class SubscriptionSuccessTemplateView(TemplateView):
    template_name = 'subscriptions/success.html'


class SubscriptionCanceledTemplateView(TemplateView):
    template_name = 'subscriptions/cancel.html'


class SubscriptionCreateView(CreateView):
    form_class = SubscriptionForm

    def form_valid(self, form):
        # form.instance.user = self.request.user
        # form.instance.ends_at = timezone.now() + timedelta(days=30 * form.instance.subscription.plan)
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    'price': 'price_1TClVGPMfdDlaO98Bxs5Q9nO',
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=f'{settings.DOMAIN_NAME}/{reverse("subscriptions:order_success")}',
            cancel_url=f'{settings.DOMAIN_NAME}/{reverse("subscriptions:order_canceled")}',
        )
        return HttpResponseRedirect(checkout_session.url, status=HTTPStatus.SEE_OTHER)


class SubscriptionTemplateView(TemplateView):
    template_name = 'subscriptions/premium_popup.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        min_plan = Subscription.objects.order_by('plan').first()
        subscriptions = Subscription.objects.order_by('plan')

        context['form'] = SubscriptionForm(subscriptions_qs=subscriptions)
        subscriptions = subscriptions.annotate(
            economy=Round(100 - ((F('price') * 100) / (min_plan.price * F('plan')))),
            real_price=Round(F('price') / F('plan'), 2),
        )

        context['plans'] = zip(subscriptions, context['form']['subscription'])

        return context

    def get(self, request, *args, **kwargs):
        html = render_to_string(self.template_name, self.get_context_data(), request)
        return JsonResponse(data={'html': html}, status=HTTPStatus.OK)
