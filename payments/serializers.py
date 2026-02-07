from rest_framework import serializers

from .models import Order, PaymentSettings


class PaymentSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentSettings
        fields = ["platform", "enabled", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class OrderSerializer(serializers.ModelSerializer):
    payment_url = serializers.SerializerMethodField()

    def get_payment_url(self, obj):
        return obj.payload.get("confirmation_url")

    class Meta:
        model = Order
        fields = "__all__"
        read_only_fields = ["user", "status", "created_at", "payment_id", "payload"]
