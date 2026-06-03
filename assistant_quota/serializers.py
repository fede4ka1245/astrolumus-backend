from rest_framework import serializers

from utils.multilinguality import LocalizedFieldsSerializerMixin
from .models import RequestPack


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
            "sort_order",
        )
