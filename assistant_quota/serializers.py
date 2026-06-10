from rest_framework import serializers

from utils.multilinguality import LocalizedFieldsSerializerMixin
from .models import RequestPack, SubscriptionPlan


class RequestPackSerializer(LocalizedFieldsSerializerMixin, serializers.ModelSerializer):
    localized_fields = ("title", "description")

    class Meta:
        model = RequestPack
        fields = (
            "code",
            "title",
            "description",
            "requests_count",
            "price_rub",
            "price_byn",
            "price_usd",
            "price_eur",
            "discount_percent",
            "is_popular",
            "sort_order",
        )


class SubscriptionPlanSerializer(LocalizedFieldsSerializerMixin, serializers.ModelSerializer):
    localized_fields = ("title", "description")

    class Meta:
        model = SubscriptionPlan
        fields = (
            "code",
            "months",
            "title",
            "description",
            "price_rub",
            "price_byn",
            "price_usd",
            "price_eur",
            "is_popular",
            "sort_order",
        )
