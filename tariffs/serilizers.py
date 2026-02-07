from rest_framework import serializers

from .models import SitePayments, Tariff, ActivationTariff

from utils.multilinguality import LocalizedFieldsSerializerMixin


class SitePaymentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SitePayments
        fields = "__all__"


class TariffSerializer(serializers.ModelSerializer):
    current_user_activated = serializers.SerializerMethodField()
    current_user_activates = serializers.SerializerMethodField()

    def get_current_user_activated(self, obj):
        if "request" in self.context and self.context["request"].user:
            last_activation = ActivationTariff.objects.filter(tariff=obj, user=self.context["request"].user).order_by(
                "-created_at").first()
            if last_activation:
                return last_activation.created_at
        return None

    def get_current_user_activates(self, obj):
        if "request" in self.context and self.context["request"].user:
            last_activations = ActivationTariff.objects.filter(tariff=obj, user=self.context["request"].user).order_by(
                "-created_at")
            if last_activations:
                return last_activations.values_list("created_at", flat=True)
        return None

    class Meta:
        model = Tariff
        # fields = "__all__"
        fields = ['id', 'code', 'title', 'description', 'restriction_forum', 'restriction_astroprocessor',
                  'restriction_number_of_topic',
                  'restriction_number_of_horoscopes', 'restriction_astroprocessor_validity_days', 'validity_days',
                  'current_user_activated', 'current_user_activates', 'tariff_group']


class PublicTariffSerializer(
    LocalizedFieldsSerializerMixin,
    serializers.ModelSerializer
):
    localized_fields = ("title", "public_description")
    prices = serializers.SerializerMethodField()
    price_rub = serializers.SerializerMethodField()
    price_byn = serializers.SerializerMethodField()
    price_usd = serializers.SerializerMethodField()
    price_eur = serializers.SerializerMethodField()

    def get_prices(self, obj):
        """Return prices in all currencies"""
        return {
            "RUB": float(obj.price_rub),
            "BYN": float(obj.price_byn),
            "USD": float(obj.price_usd),
            "EUR": float(obj.price_eur),
        }

    def get_price_rub(self, obj):
        return float(obj.price_rub)

    def get_price_byn(self, obj):
        return float(obj.price_byn)

    def get_price_usd(self, obj):
        return float(obj.price_usd)

    def get_price_eur(self, obj):
        return float(obj.price_eur)

    class Meta:
        model = Tariff
        fields = ['id', 'code', 'title', 'public_description', 'validity_days', 'tariff_link', 'prices', 'price_rub', 'price_byn', 'price_usd', 'price_eur']


class FullTariffSerializer(serializers.ModelSerializer):
    """Full tariff serializer with all language translations"""
    prices = serializers.SerializerMethodField()
    price_rub = serializers.SerializerMethodField()
    price_byn = serializers.SerializerMethodField()
    price_usd = serializers.SerializerMethodField()
    price_eur = serializers.SerializerMethodField()

    def get_prices(self, obj):
        """Return prices in all currencies"""
        return {
            "RUB": float(obj.price_rub),
            "BYN": float(obj.price_byn),
            "USD": float(obj.price_usd),
            "EUR": float(obj.price_eur),
        }

    def get_price_rub(self, obj):
        return float(obj.price_rub)

    def get_price_byn(self, obj):
        return float(obj.price_byn)

    def get_price_usd(self, obj):
        return float(obj.price_usd)

    def get_price_eur(self, obj):
        return float(obj.price_eur)

    class Meta:
        model = Tariff
        fields = ['id', 'code', 'title', 'public_description', 'validity_days', 'tariff_link', 'prices', 'price_rub', 'price_byn', 'price_usd', 'price_eur']
