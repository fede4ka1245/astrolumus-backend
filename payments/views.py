import json
import os
import hashlib
from abc import ABC, abstractmethod

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import View
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
import stripe
import logging
from datetime import timedelta, datetime
from django.utils import timezone

from bootcamp.models import Curriculum
from tariffs.models import Tariff, ActivationTariff
from utils.multilinguality import get_language_value

from .models import Order, PaymentSettings, PaymentRecord, RecurringSubscription
from .serializers import OrderSerializer, PaymentSettingsSerializer
from .tasks import activate_user_tariff

logger = logging.getLogger(__name__)

def _is_test_env() -> bool:
    return os.getenv("ENV") != "production"


class PaySystem(ABC):
    @abstractmethod
    def make_payment(
        self, amount: float, order_id: str, return_url: str, description: str, currency: str = 'USD'
    ) -> dict:
        pass

    @abstractmethod
    def get_payment(self, order_id: str) -> dict:
        pass


class Stripe(PaySystem):
    def make_payment(
        self, amount: float, order_id: str, return_url: str, description: str, currency: str = 'USD',
        user_email: str = None, is_recurring: bool = True
    ) -> dict:
        """Create recurring subscription using Stripe Subscriptions API"""
        stripe_key = settings.STRIPE_SECRET_KEY
        if not stripe_key:
            raise Exception("STRIPE_SECRET_KEY is not configured in environment variables")
        stripe.api_key = stripe_key

        amount_cents = int(float(amount) * 100)

        try:
            if is_recurring:
                # Create recurring subscription
                # First, create or get customer
                customer = None
                if user_email:
                    # Try to find existing customer
                    customers = stripe.Customer.list(email=user_email, limit=1)
                    if customers.data:
                        customer = customers.data[0]
                    else:
                        # Create new customer
                        customer = stripe.Customer.create(email=user_email)

                # Create checkout session for subscription
                session = stripe.checkout.Session.create(
                    payment_method_types=["card"],
                    mode="subscription",
                    success_url=settings.STRIPE_SUCCESS_URL,
                    cancel_url=settings.STRIPE_CANCEL_URL,
                    customer=customer.id if customer else None,
                    customer_email=user_email if not customer else None,
                    line_items=[
                        {
                            "price_data": {
                                "currency": currency.lower(),
                                "unit_amount": amount_cents,
                                "product_data": {
                                    "name": description,
                                },
                                "recurring": {
                                    "interval": "year",  # Yearly subscription
                                },
                            },
                            "quantity": 1,
                        }
                    ],
                    metadata={"order_id": order_id},
                    subscription_data={
                        "metadata": {"order_id": order_id},
                    },
                )

                r = {
                    "payment_id": session.id,
                    "subscription_id": session.subscription,
                    "customer_id": customer.id if customer else None,
                    "client_secret": session.id,
                    "amount": str(amount),
                    "currency": currency,
                    "created_at": session.created,
                    "confirmation_url": session.url,
                    "data": session,
                    "is_recurring": True,
                }
                return r
            else:
                # Fallback to one-time payment for backward compatibility
                session = stripe.checkout.Session.create(
                    payment_method_types=["card"],
                    mode="payment",
                    success_url=settings.STRIPE_SUCCESS_URL,
                    cancel_url=settings.STRIPE_CANCEL_URL,
                    line_items=[
                        {
                            "price_data": {
                                "currency": currency.lower(),
                                "unit_amount": amount_cents,
                                "product_data": {
                                    "name": description,
                                },
                            },
                            "quantity": 1,
                        }
                    ],
                    metadata={"order_id": order_id},
                )

                r = {
                    "payment_id": session.id,
                    "client_secret": session.id,
                    "amount": str(amount),
                    "currency": currency,
                    "created_at": session.created,
                    "confirmation_url": session.url,
                    "data": session,
                    "is_recurring": False,
                }
                return r
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe payment error: {str(e)}")

    def get_payment(self, order_id: str) -> dict:
        """Check payment status"""
        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            payment_intents = stripe.PaymentIntent.list(
                limit=1,
                metadata={"order_id": order_id}
            )
            if payment_intents.data:
                return {"status": payment_intents.data[0].status}
            return {"status": "not_found"}
        except stripe.error.StripeError:
            return {"status": "error"}


class Bepaid(PaySystem):
    def make_payment(
        self,
        amount: float,
        order_id: str,
        return_url: str,
        description: str,
        currency: str = "RUB",
        user_email: str = None,
        is_recurring: bool = True,
    ) -> dict:
        print(f"🔵 BePaid.make_payment() called with currency: {currency}, is_recurring: {is_recurring}")
        is_test = _is_test_env()

        notification_url = f"{settings.BEPAID_WEBHOOK_BASE_URL}{reverse_lazy('payments:bepaid-callback', kwargs={'pk': order_id, })}"

        if is_recurring:
            # Create recurring subscription using BePaid subscriptions API
            # Create subscription via checkout
            checkout_data = {
                "checkout": {
                    "transaction_type": "payment",
                    "test": is_test,
                    "order": {
                        "amount": int(amount * 100),
                        "currency": currency,
                        "description": description,
                    },
                    "settings": {
                        "success_url": return_url or f"{settings.BEPAID_WEBHOOK_BASE_URL}/payment-success",
                        "decline_url": f"{settings.BEPAID_WEBHOOK_BASE_URL}/payment-cancel",
                        "fail_url": f"{settings.BEPAID_WEBHOOK_BASE_URL}/payment-cancel",
                        "notification_url": notification_url,
                        "language": "ru",
                        "customer_fields": {
                            "visible": ["email"],
                            "read_only": [],
                        },
                    },
                    "recurring": {
                        "type": "recurring",
                    },
                },
            }

            pr = requests.post(
                "https://checkout.bepaid.by/ctp/api/checkouts",
                json=checkout_data,
                auth=(settings.BEPAID_SHOP_ID, settings.BEPAID_SECRET_KEY),
            )

            print(f"🔵 BePaid API response status: {pr.status_code}")
            try:
                pr_json = pr.json()
            except ValueError:
                pr_json = {"raw": pr.text}
            print(f"🔵 BePaid API response: {pr_json}")

            if pr.status_code != 201:
                raise Exception(f"BePaid API error: {pr.text}")

            checkout_id = pr_json.get("checkout", {}).get("token")

            r = {
                "payment_id": checkout_id,
                "subscription_id": checkout_id,  # BePaid uses checkout token for subscriptions
                "amount": str(amount),
                "currency": currency,
                "created_at": pr_json.get("checkout", {}).get("created_at"),
                "confirmation_url": pr_json.get("checkout", {}).get("redirect_url"),
                "data": pr_json,
                "is_recurring": True,
            }

            print(
                f"🔵 Returning from BePaid.make_payment() with currency: {r['currency']}, subscription_id: {r['subscription_id']}"
            )
            return r

        # Fallback to one-time payment for backward compatibility
        product = {
            "name": description,
            "description": description,
            "currency": currency,
            "amount": int(amount * 100),
            "infinite": True,
            "visible_fields": None,
            "test": is_test,
            "immortal": True,
            "notification_url": notification_url,
            "shop_id": settings.BEPAID_SHOP_ID,
            "language": "ru",
            "transaction_type": "payment",
        }

        print(f"🔵 Sending to BePaid API - Currency in request: {product['currency']}, Amount: {product['amount']}")

        pr = requests.post(
            "https://api.bepaid.by/products",
            json=product,
            auth=(settings.BEPAID_SHOP_ID, settings.BEPAID_SECRET_KEY),
        )

        print(f"🔵 BePaid API response status: {pr.status_code}")
        try:
            pr_json = pr.json()
        except ValueError:
            pr_json = {"raw": pr.text}
        print(f"🔵 BePaid API response: {pr_json}")

        payment_id = pr_json.get("id")
        payment_amount = pr_json.get("amount")
        response_currency = pr_json.get("currency")

        print(f"🔵 BePaid response - Requested currency: {currency}, Response currency: {response_currency}")
        created_at = pr_json.get("created_at")

        pay_url = f"https://api.bepaid.by/products/{payment_id}/pay"
        r = requests.post(pay_url, allow_redirects=False)

        soup = BeautifulSoup(r.text, "html.parser")
        a = soup.find("a")
        confirmation_url = a.attrs.get("href") if a else None

        r = {
            "payment_id": payment_id,
            "amount": str(payment_amount),
            "currency": currency,
            "created_at": created_at,
            "confirmation_url": confirmation_url,
            "data": pr_json,
            "is_recurring": False,
        }

        print(f"🔵 Returning from BePaid.make_payment() with currency: {r['currency']}")
        return r

    def get_payment(self, order_id: str) -> dict:
        check_payment_url = f"https://checkout.bepaid.by/ctp/api/checkouts/{order_id}"
        r = requests.get(
            check_payment_url,
            auth=(settings.BEPAID_SHOP_ID, settings.BEPAID_SECRET_KEY),
        )
        return True if r.json().get("checkout").get("status") == "successful" else False


class Payer:
    pay_systems = {"stripe": Stripe, "bepaid": Bepaid}

    def __init__(self, pay_system_name):
        self.pay_system = self.pay_systems.get(pay_system_name)()

    def make_payment(
        self, amount: float, order_id: str, return_url: str, description: str, currency: str = 'USD',
        user_email: str = None, is_recurring: bool = True
    ):
        print(f"🔷 Payer.make_payment() called with currency: {currency}, is_recurring: {is_recurring}")
        result = self.pay_system.make_payment(
            amount, order_id, return_url, description, currency, user_email, is_recurring
        )
        print(f"🔷 Payer.make_payment() returning currency: {result.get('currency')}, is_recurring: {result.get('is_recurring')}")
        return result


class OrderViewset(viewsets.ModelViewSet):
    permission_classes = (AllowAny,)
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def perform_create(self, serializer):
        """
        Handle order creation with tariff activation flow
        Validates:
        1. User must exist (no auto-creation)
        2. User doesn't already have an active tariff
        """
        email = self.request.data.get('email')
        tariff_code = self.request.data.get('tariff_code')
        pay_system = self.request.data.get('pay_system')
        currency = self.request.data.get('currency')
        if not currency:
            currency = 'RUB' if pay_system == "bepaid" else 'USD'
        currency = str(currency).upper()
        if pay_system == "bepaid" and currency not in {"RUB", "BYN"}:
            raise ValidationError({
                "error": "invalid_currency",
                "message": "BePaid supports only RUB/BYN currencies.",
            })

        print(f"📥 OrderViewset.perform_create() - Received currency: {currency}")
        print(f"📥 Full request data: {self.request.data}")

        # Check 1: User must exist
        user = None
        if email:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                raise ValidationError({
                    'error': 'unknown_user',
                    'message': 'User not found. Please check your email.'
                })

        # Get tariff if tariff_code provided
        tariff = None
        if tariff_code:
            try:
                tariff = Tariff.objects.get(code=tariff_code)
            except Tariff.DoesNotExist:
                raise ValidationError({
                    'error': 'unknown_error',
                    'message': 'Tariff not found.'
                })

        # Check 2: User doesn't already have an active tariff
        if user and tariff:
            existing_activation = ActivationTariff.objects.filter(
                user=user,
                tariff=tariff
            ).order_by('-created_at').first()

            if existing_activation:
                # Check if tariff is still active (not expired)
                if tariff.validity_days > 0:
                    expiration_date = existing_activation.created_at + timedelta(days=tariff.validity_days)
                    if timezone.now() < expiration_date:
                        raise ValidationError({
                            'error': 'already_paid',
                            'message': 'This tariff is already active.',
                            'expiration_date': expiration_date.isoformat()
                        })
                else:
                    # Lifetime tariff - always active
                    raise ValidationError({
                        'error': 'already_paid',
                        'message': 'This tariff is already active (lifetime).'
                    })

        # Save order with user, tariff, and currency
        try:
            super().perform_create(serializer)
            order = serializer.instance

            if user:
                order.user = user
            if tariff:
                order.tariff = tariff

            # Save currency
            order.currency = currency

            # Create payment with Payer
            payer = Payer(pay_system_name=pay_system)

            # Get tariff title in Russian (default)
            tariff_title = "Unknown"
            if tariff and tariff.title:
                tariff_title = get_language_value(tariff.title, 'ru')

            # Get price based on currency
            if tariff:
                if currency == 'USD':
                    amount_for_payment = tariff.price_usd
                elif currency == 'RUB':
                    amount_for_payment = tariff.price_rub
                elif currency == 'BYN':
                    amount_for_payment = tariff.price_byn
                elif currency == 'EUR':
                    amount_for_payment = tariff.price_eur
                else:
                    amount_for_payment = tariff.price_usd  # Default to USD
            else:
                amount_for_payment = float(order.amount)

            print(f"💳 Calling payer.make_payment() with currency: {currency}, user_email: {email}")

            # Create recurring subscription by default
            result = payer.make_payment(
                amount_for_payment,
                str(order.pk),
                "",  # No return_url for now
                f"Subscription: {tariff_title}",
                currency,
                user_email=email,
                is_recurring=True  # Enable recurring payments
            )

            print(f"💳 payer.make_payment() returned currency: {result.get('currency')}, is_recurring: {result.get('is_recurring')}")

            order.payload = result
            order.payment_id = result.get("payment_id")
            order.save()

        except ValidationError:
            # Re-raise validation errors
            raise
        except Exception as e:
            logger.error(f"❌ Error creating payment: {str(e)}")
            if 'order' in locals():
                order.delete()  # Clean up if payment creation fails
            raise ValidationError({
                'error': 'unknown_error',
                'message': f'An error occurred: {str(e)}'
            })


class PaymentSettingsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for payment settings.
    Provides endpoint to check if payments are enabled for a specific platform.
    """
    permission_classes = (AllowAny,)
    queryset = PaymentSettings.objects.all()
    serializer_class = PaymentSettingsSerializer

    @action(detail=False, methods=['get'], url_path='platform/(?P<platform_name>[^/.]+)')
    def by_platform(self, request, platform_name=None):
        """
        Get payment settings for a specific platform.
        Usage: GET /api/payments/settings/platform/{ios|android|web}
        """
        try:
            settings = PaymentSettings.objects.get(platform=platform_name.lower())
            serializer = self.get_serializer(settings)
            return Response(serializer.data)
        except PaymentSettings.DoesNotExist:
            # If settings don't exist for platform, return default (enabled=True)
            return Response({
                'platform': platform_name.lower(),
                'enabled': True,
                'created_at': None,
                'updated_at': None
            })


class StripeCallbackView(View):
    def _map_stripe_subscription_status(self, stripe_status: str) -> str:
        """Map Stripe subscription status to our RecurringSubscription status"""
        status_map = {
            "active": RecurringSubscription.SubscriptionStatuses.ACTIVE,
            "canceled": RecurringSubscription.SubscriptionStatuses.CANCELED,
            "past_due": RecurringSubscription.SubscriptionStatuses.PAST_DUE,
            "unpaid": RecurringSubscription.SubscriptionStatuses.UNPAID,
            "trialing": RecurringSubscription.SubscriptionStatuses.TRIALING,
            "incomplete": RecurringSubscription.SubscriptionStatuses.INCOMPLETE,
            "incomplete_expired": RecurringSubscription.SubscriptionStatuses.INCOMPLETE_EXPIRED,
        }
        return status_map.get(stripe_status, RecurringSubscription.SubscriptionStatuses.INCOMPLETE)

    def _update_recurring_subscription(self, subscription_obj):
        """Update or create RecurringSubscription from Stripe subscription object"""
        subscription_id = subscription_obj.get("id")
        customer_id = subscription_obj.get("customer")

        try:
            # Try to find existing subscription by subscription_id
            recurring_sub = RecurringSubscription.objects.get(subscription_id=subscription_id)
            order = recurring_sub.order
            user = recurring_sub.user
            tariff = recurring_sub.tariff
        except RecurringSubscription.DoesNotExist:
            # Try to find by customer_id and get latest order
            try:
                customer = stripe.Customer.retrieve(customer_id)
                customer_email = customer.email
                if customer_email:
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    try:
                        user = User.objects.get(email=customer_email)
                        # Get latest order for this user
                        order = Order.objects.filter(user=user).order_by("-created_at").first()
                        tariff = order.tariff if order else None
                    except User.DoesNotExist:
                        logger.warning(f"⚠️ User not found for customer email: {customer_email}")
                        return
            except Exception as e:
                logger.error(f"❌ Error retrieving customer: {str(e)}")
                return

        if not user or not tariff:
            logger.warning(f"⚠️ Cannot create RecurringSubscription: missing user or tariff")
            return

        RecurringSubscription.objects.update_or_create(
            subscription_id=subscription_id,
            defaults={
                "user": user,
                "tariff": tariff,
                "order": order,
                "payment_system": RecurringSubscription.PaymentSystems.STRIPE,
                "customer_id": customer_id,
                "status": self._map_stripe_subscription_status(subscription_obj.get("status")),
                "amount": float(subscription_obj.get("items", {}).get("data", [{}])[0].get("price", {}).get("unit_amount", 0)) / 100.0,
                "currency": subscription_obj.get("currency", "usd").upper(),
                "current_period_start": datetime.fromtimestamp(
                    subscription_obj.get("current_period_start"), tz=timezone.utc
                ) if subscription_obj.get("current_period_start") else None,
                "current_period_end": datetime.fromtimestamp(
                    subscription_obj.get("current_period_end"), tz=timezone.utc
                ) if subscription_obj.get("current_period_end") else None,
                "cancel_at_period_end": subscription_obj.get("cancel_at_period_end", False),
                "canceled_at": datetime.fromtimestamp(
                    subscription_obj.get("canceled_at"), tz=timezone.utc
                ) if subscription_obj.get("canceled_at") else None,
                "metadata": dict(subscription_obj.get("metadata", {})),
            }
        )
        print(f"✅ Updated RecurringSubscription {subscription_id}")

    def post(self, *args, **kwargs):
        """Handle Stripe webhook events and activate tariffs on payment success"""
        print("=" * 80)
        print("🔔 STRIPE WEBHOOK RECEIVED!")
        print(f"📍 Request path: {self.request.path}")
        print(f"📍 Request method: {self.request.method}")
        print(f"📍 Headers: {dict(self.request.META)}")

        payload = self.request.body
        sig_header = self.request.META.get("HTTP_STRIPE_SIGNATURE")
        endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

        print(f"🔑 Signature: {sig_header[:20] if sig_header else 'NO SIGNATURE'}")
        print(f"📦 Payload length: {len(payload)} bytes")
        print("=" * 80)

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
            print(f"✅ Webhook verified, event type: {event.get('type')}")
        except ValueError as e:
            logger.warning(f"❌ Invalid Stripe webhook payload: {str(e)}")
            return HttpResponse(status=400)
        except stripe.error.SignatureVerificationError as e:
            logger.warning(f"❌ Invalid Stripe webhook signature: {str(e)}")
            return HttpResponse(status=400)

        event_type = event["type"]
        print(f"📋 Processing event type: {event_type}")

        # Handle checkout.session.completed (initial subscription creation)
        if event_type == "checkout.session.completed":
            session = event["data"]["object"]
            session_id = session.get("id")
            payment_status = session.get("payment_status")
            order_id = session.get("metadata", {}).get("order_id")
            subscription_id = session.get("subscription")
            customer_id = session.get("customer")
            mode = session.get("mode")  # "subscription" or "payment"

            # Получаем данные клиента из Stripe
            customer_email = session.get("customer_email") or session.get("customer_details", {}).get("email")
            customer_name = session.get("customer_details", {}).get("name", "")
            customer_first_name = ""
            customer_last_name = ""
            if customer_name:
                name_parts = customer_name.split(" ", 1)
                customer_first_name = name_parts[0] if name_parts else ""
                customer_last_name = name_parts[1] if len(name_parts) > 1 else ""

            print(f"💰 Checkout session completed - Session ID: {session_id}, Mode: {mode}, Payment status: {payment_status}, Order ID: {order_id}, Subscription ID: {subscription_id}")

            if order_id and payment_status == "paid":
                try:
                    with transaction.atomic():
                        order = Order.objects.select_for_update().get(pk=order_id)
                        print(f"📦 Found order {order_id}, current status: {order.status}")

                        if order.status == Order.PaymentStatuses.PENDING:
                            order.status = Order.PaymentStatuses.SUCCEEDED
                            order.payment_id = session_id
                            order.save(update_fields=["status", "payment_id"])
                            print(f"✅ Updated order {order_id} status to SUCCEEDED")
                        else:
                            logger.warning(f"⚠️ Order {order_id} already has status {order.status}, skipping status update")

                        # For subscriptions: only create RecurringSubscription here.
                        # PaymentRecord + tariff activation are handled by invoice.paid
                        # (which fires right after for the first period and on every renewal).
                        # Creating them here too would cause duplicates.
                        if mode == "subscription" and subscription_id and order.tariff and order.user:
                            subscription_obj = stripe.Subscription.retrieve(subscription_id)

                            RecurringSubscription.objects.update_or_create(
                                subscription_id=subscription_id,
                                defaults={
                                    "user": order.user,
                                    "tariff": order.tariff,
                                    "order": order,
                                    "payment_system": RecurringSubscription.PaymentSystems.STRIPE,
                                    "customer_id": customer_id,
                                    "status": self._map_stripe_subscription_status(subscription_obj.status),
                                    "amount": order.amount,
                                    "currency": order.currency,
                                    "current_period_start": datetime.fromtimestamp(
                                        subscription_obj.current_period_start, tz=timezone.utc
                                    ) if subscription_obj.current_period_start else None,
                                    "current_period_end": datetime.fromtimestamp(
                                        subscription_obj.current_period_end, tz=timezone.utc
                                    ) if subscription_obj.current_period_end else None,
                                    "cancel_at_period_end": subscription_obj.cancel_at_period_end,
                                    "canceled_at": datetime.fromtimestamp(
                                        subscription_obj.canceled_at, tz=timezone.utc
                                    ) if subscription_obj.canceled_at else None,
                                    "metadata": dict(subscription_obj.metadata) if subscription_obj.metadata else {},
                                }
                            )
                            print(f"📝 Created/Updated RecurringSubscription {subscription_id} for order {order_id}")

                        # For one-time payments only: create PaymentRecord and activate tariff
                        if mode == "payment":
                            from django.utils.html import strip_tags
                            tariff_name = None
                            if order.tariff and order.tariff.title:
                                tariff_name = strip_tags(get_language_value(order.tariff.title, 'ru') or "").strip() or None

                            payment_record, created = PaymentRecord.objects.get_or_create(
                                payment_system=PaymentRecord.PaymentSystems.STRIPE,
                                payment_id=session_id,
                                defaults={
                                    "user": order.user,
                                    "order": order,
                                    "user_first_name": order.user.first_name if order.user else None,
                                    "user_last_name": order.user.last_name if order.user else None,
                                    "user_email": order.user.email if order.user else None,
                                    "merchant_first_name": customer_first_name,
                                    "merchant_last_name": customer_last_name,
                                    "merchant_email": customer_email,
                                    "tariff_name": tariff_name,
                                    "amount": order.amount,
                                    "currency": order.currency,
                                    "status": PaymentRecord.PaymentStatuses.SUCCESS,
                                    "raw_data": dict(session),
                                    "is_recurring": False,
                                },
                            )
                            if created:
                                print(f"📝 Created PaymentRecord for order {order_id} (one-time)")
                                if order.tariff and order.user:
                                    print(f"🎯 Activating tariff {order.tariff.code} for user {order.user.email}")
                                    activate_user_tariff.delay(order.user.id, order.tariff.code, str(order.id))
                            else:
                                logger.warning(f"⚠️ PaymentRecord already exists for Stripe session {session_id}, skipping")

                        if order.course:
                            Curriculum.objects.get_or_create(user=order.user, course=order.course)
                except Order.DoesNotExist:
                    logger.error(f"❌ Order not found: {order_id}")

        # Handle customer.subscription.created
        elif event_type == "customer.subscription.created":
            subscription = event["data"]["object"]
            subscription_id = subscription.get("id")
            customer_id = subscription.get("customer")
            print(f"🆕 Subscription created - Subscription ID: {subscription_id}, Customer ID: {customer_id}")
            self._update_recurring_subscription(subscription)

        # Handle customer.subscription.updated
        elif event_type == "customer.subscription.updated":
            subscription = event["data"]["object"]
            subscription_id = subscription.get("id")
            print(f"🔄 Subscription updated - Subscription ID: {subscription_id}")
            self._update_recurring_subscription(subscription)

        # Handle customer.subscription.deleted
        elif event_type == "customer.subscription.deleted":
            subscription = event["data"]["object"]
            subscription_id = subscription.get("id")
            print(f"🗑️ Subscription deleted - Subscription ID: {subscription_id}")
            try:
                recurring_sub = RecurringSubscription.objects.get(subscription_id=subscription_id)
                recurring_sub.status = RecurringSubscription.SubscriptionStatuses.CANCELED
                recurring_sub.canceled_at = timezone.now()
                recurring_sub.save()
                print(f"✅ Updated RecurringSubscription {subscription_id} to CANCELED")
            except RecurringSubscription.DoesNotExist:
                logger.warning(f"⚠️ RecurringSubscription not found: {subscription_id}")

        # Handle invoice.paid (recurring payment)
        elif event_type == "invoice.paid":
            invoice = event["data"]["object"]
            subscription_id = invoice.get("subscription")
            customer_id = invoice.get("customer")
            amount_paid = invoice.get("amount_paid", 0) / 100.0  # Convert from cents
            currency = invoice.get("currency", "usd").upper()

            print(f"💳 Invoice paid - Subscription ID: {subscription_id}, Amount: {amount_paid} {currency}")

            if subscription_id:
                try:
                    recurring_sub = RecurringSubscription.objects.get(subscription_id=subscription_id)

                    # Create PaymentRecord for recurring payment
                    tariff_name = None
                    if recurring_sub.tariff and recurring_sub.tariff.title:
                        from utils.multilinguality import get_language_value
                        from django.utils.html import strip_tags
                        tariff_name = strip_tags(get_language_value(recurring_sub.tariff.title, 'ru') or "").strip() or None

                    invoice_id = invoice.get("id")
                    if not invoice_id:
                        logger.error("❌ Stripe invoice.paid received without invoice id, skipping")
                        return HttpResponse(status=200)
                    payment_record, created = PaymentRecord.objects.get_or_create(
                        payment_system=PaymentRecord.PaymentSystems.STRIPE,
                        payment_id=invoice_id,
                        defaults={
                            "user": recurring_sub.user,
                            "order": recurring_sub.order,
                            "user_first_name": recurring_sub.user.first_name if recurring_sub.user else None,
                            "user_last_name": recurring_sub.user.last_name if recurring_sub.user else None,
                            "user_email": recurring_sub.user.email if recurring_sub.user else None,
                            "tariff_name": tariff_name,
                            "amount": amount_paid,
                            "currency": currency,
                            "status": PaymentRecord.PaymentStatuses.SUCCESS,
                            "raw_data": dict(invoice),
                            "is_recurring": True,
                        },
                    )
                    if created:
                        # Get customer email from Stripe only once per invoice
                        customer_obj = stripe.Customer.retrieve(customer_id) if customer_id else None
                        customer_email = customer_obj.email if customer_obj else None
                        if customer_email:
                            PaymentRecord.objects.filter(pk=payment_record.pk).update(merchant_email=customer_email)

                        print(f"📝 Created PaymentRecord for recurring payment (invoice: {invoice_id})")

                        # Activate tariff for the new billing period
                        if recurring_sub.tariff and recurring_sub.user:
                            print(f"🎯 Activating tariff {recurring_sub.tariff.code} for user {recurring_sub.user.email} (recurring payment)")
                            activate_user_tariff.delay(recurring_sub.user.id, recurring_sub.tariff.code, str(recurring_sub.order.id) if recurring_sub.order else None)

                        # Update subscription period
                        subscription_obj = stripe.Subscription.retrieve(subscription_id)
                        recurring_sub.current_period_start = datetime.fromtimestamp(
                            subscription_obj.current_period_start, tz=timezone.utc
                        ) if subscription_obj.current_period_start else None
                        recurring_sub.current_period_end = datetime.fromtimestamp(
                            subscription_obj.current_period_end, tz=timezone.utc
                        ) if subscription_obj.current_period_end else None
                        recurring_sub.save()
                        print(f"✅ Updated RecurringSubscription {subscription_id} period")
                    else:
                        logger.warning(f"⚠️ PaymentRecord already exists for Stripe invoice {invoice_id}, skipping")
                except RecurringSubscription.DoesNotExist:
                    logger.warning(f"⚠️ RecurringSubscription not found: {subscription_id}")
        else:
            logger.debug(f"ℹ️ Ignoring event type: {event_type}")

        return HttpResponse(status=200)


class BepaidCallBackView(View):
    @staticmethod
    def _stable_payment_id(order_id: str, json_data: dict) -> str:
        last_transaction = json_data.get("last_transaction") or {}
        checkout = json_data.get("checkout") or {}
        transaction_obj = json_data.get("transaction") or {}

        candidates = [
            last_transaction.get("uid"),
            last_transaction.get("id"),
            transaction_obj.get("uid"),
            transaction_obj.get("id"),
            json_data.get("uid"),
            json_data.get("id"),
            checkout.get("token"),
            checkout.get("id"),
            json_data.get("token"),
        ]
        for candidate in candidates:
            if candidate:
                return str(candidate)

        normalized = json.dumps(
            json_data, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        digest = hashlib.sha256(normalized).hexdigest()
        return f"payload_sha256:{order_id}:{digest}"

    def post(self, *args, **kwargs):
        """Handle BePaid webhook events and activate tariffs on payment success"""
        print("=" * 80)
        print("🔔 BEPAID WEBHOOK RECEIVED!")
        print(f"📍 Request path: {self.request.path}")
        print(f"📍 Request method: {self.request.method}")

        order_id = kwargs.get("pk")
        print(f"📦 Order ID from URL: {order_id}")
        print("=" * 80)

        try:
            body_text = self.request.body.decode("utf-8") if self.request.body else ""
            print(f"📄 Raw body length: {len(body_text)} chars")
            print(f"📄 Raw body: '{body_text}'")

            if not body_text or body_text.strip() == "":
                print("⚠️ BODY IS EMPTY!")
                json_data = {}
            else:
                json_data = json.loads(body_text)
                print(f"📋 Parsed JSON keys: {list(json_data.keys())}")
                print(f"📋 Full JSON: {json.dumps(json_data, indent=2)}")

            # BePaid может присылать разные форматы:
            # - state + last_transaction.status
            # - status в корне checkout payload (successful/expired/failed/...)
            checkout_obj = json_data.get("checkout") or {}
            transaction_obj = json_data.get("transaction") or checkout_obj.get("transaction") or {}

            payment_state = json_data.get("state") or checkout_obj.get("state")
            root_status = json_data.get("status") or checkout_obj.get("status")

            last_transaction = json_data.get("last_transaction", {}) or {}
            if not last_transaction and transaction_obj:
                last_transaction = transaction_obj

            tx_status = (
                last_transaction.get("status")
                or transaction_obj.get("status")
                or (transaction_obj.get("payment") or {}).get("status")
            )

            credit_card = last_transaction.get("credit_card", {}) or {}
            merchant_first_name = credit_card.get("first_name", "")
            merchant_last_name = credit_card.get("last_name", "")
            customer_obj = json_data.get("customer") or {}
            last_tx_customer_obj = last_transaction.get("customer") or {}
            tx_customer_obj = transaction_obj.get("customer") or {}
            merchant_email = (
                customer_obj.get("email")
                or last_tx_customer_obj.get("email")
                or tx_customer_obj.get("email")
                or ""
            )
            tx_amount = (
                last_transaction.get("amount")
                if last_transaction.get("amount") is not None
                else transaction_obj.get("amount", 0)
            )
            tx_currency = (
                last_transaction.get("currency")
                or transaction_obj.get("currency")
                or "RUB"
            )

            effective_status = payment_state or tx_status or root_status
            print(f"💳 Payment state: {payment_state}")
            print(f"💳 Last transaction: {last_transaction}")
            print(f"💳 Transaction status: {tx_status}")
            print(f"💳 Root status: {root_status}")
            print(f"💳 Merchant info: {merchant_first_name} {merchant_last_name}, {merchant_email}")

            if effective_status == "successful":
                with transaction.atomic():
                    order = Order.objects.select_for_update().get(pk=order_id)
                    print(f"📦 Found order {order_id}, current status: {order.status}")

                    if order.status != Order.PaymentStatuses.SUCCEEDED:
                        order.status = Order.PaymentStatuses.SUCCEEDED
                        order.save(update_fields=["status"])
                        print(f"✅ Updated order {order_id} status to SUCCEEDED")
                    else:
                        logger.warning(f"⚠️ Order {order_id} already succeeded")

                    amount_decimal = tx_amount / 100 if tx_amount else order.amount

                    tariff_name = None
                    if order.tariff and order.tariff.title:
                        from django.utils.html import strip_tags
                        from utils.multilinguality import get_language_value

                        tariff_name = strip_tags(get_language_value(order.tariff.title, "ru") or "").strip() or None

                    checkout_token = checkout_obj.get("token") or json_data.get("token")
                    is_recurring = (
                        (json_data.get("recurring") or {}).get("type") == "recurring"
                        or bool(checkout_token)
                        or bool(last_transaction.get("recurring_type") or transaction_obj.get("recurring_type"))
                    )

                    payment_id = self._stable_payment_id(str(order_id), json_data)

                    _, created = PaymentRecord.objects.get_or_create(
                        payment_system=PaymentRecord.PaymentSystems.BEPAID,
                        payment_id=payment_id,
                        defaults={
                            "user": order.user,
                            "order": order,
                            "user_first_name": order.user.first_name if order.user else None,
                            "user_last_name": order.user.last_name if order.user else None,
                            "user_email": order.user.email if order.user else None,
                            "merchant_first_name": merchant_first_name,
                            "merchant_last_name": merchant_last_name,
                            "merchant_email": merchant_email,
                            "tariff_name": tariff_name,
                            "amount": amount_decimal,
                            "currency": tx_currency or order.currency,
                            "status": PaymentRecord.PaymentStatuses.SUCCESS,
                            "raw_data": json_data,
                            "is_recurring": is_recurring,
                        },
                    )
                    if created:
                        print(f"📝 Created PaymentRecord for order {order_id} (recurring: {is_recurring})")
                    else:
                        logger.warning(f"⚠️ PaymentRecord already exists for BePaid payment {payment_id}, skipping")

                    if created and is_recurring and order.tariff and order.user:
                        subscription_id = checkout_token or payment_id

                        from datetime import timedelta

                        period_start = timezone.now()
                        period_end = period_start + timedelta(days=365)

                        RecurringSubscription.objects.update_or_create(
                            subscription_id=subscription_id,
                            defaults={
                                "user": order.user,
                                "tariff": order.tariff,
                                "order": order,
                                "payment_system": RecurringSubscription.PaymentSystems.BEPAID,
                                "status": RecurringSubscription.SubscriptionStatuses.ACTIVE,
                                "amount": amount_decimal,
                                "currency": tx_currency or order.currency,
                                "current_period_start": period_start,
                                "current_period_end": period_end,
                                "metadata": json_data,
                            },
                        )
                        print(f"📝 Created/Updated RecurringSubscription {subscription_id} for order {order_id}")

                    if created and order.tariff and order.user:
                        print(f"🎯 Activating tariff {order.tariff.code} for user {order.user.email}")
                        activate_user_tariff.delay(order.user.id, order.tariff.code, str(order.id))

                    if order.course and last_transaction.get("amount") >= order.course.price:
                        Curriculum.objects.get_or_create(user=order.user, course=order.course)
            else:
                print(f"⚠️ Payment not successful - state: {payment_state}, tx_status: {tx_status}, status: {root_status}")
                logger.warning(f"⚠️ Payment not successful - state: {payment_state}, tx_status: {tx_status}, status: {root_status}")

                # Не падаем на неуспешных статусах, но фиксируем итоговый статус заказа
                if effective_status in {"expired", "failed", "declined"}:
                    try:
                        with transaction.atomic():
                            order = Order.objects.select_for_update().get(pk=order_id)
                            if order.status == Order.PaymentStatuses.PENDING:
                                order.status = Order.PaymentStatuses.FAILED
                                order.save(update_fields=["status"])
                    except Order.DoesNotExist:
                        pass

        except Order.DoesNotExist:
            print(f"❌ Order not found: {order_id}")
            logger.error(f"❌ Order not found: {order_id}")
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error: {str(e)}")
            print(f"❌ Body was: {self.request.body}")
            logger.error(f"❌ JSON decode error: {str(e)}")
        except Exception as e:
            print(f"❌ Error processing BePaid callback: {str(e)}")
            print(f"❌ Exception type: {type(e)}")
            import traceback

            print(f"❌ Traceback: {traceback.format_exc()}")
            logger.error(f"❌ Error processing BePaid callback: {str(e)}")

        return HttpResponse("Callback page", content_type="text/plain")
