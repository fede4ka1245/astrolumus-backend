from django.contrib.auth import get_user_model
from rest_framework import serializers

from astroprocessor.models import AstroprocessorData, SignPlanetConnection, PlanetHouseConnection, MasterHouseConnection

from utils.multilinguality import get_language_value, LocalizedFieldsSerializerMixin

User = get_user_model()


class AstroprocessorDataSerializer(
    LocalizedFieldsSerializerMixin,
    serializers.ModelSerializer
):
    tolgee_namespace = "astroprocessor_data"
    tolgee_key_prefix = "data"
    type_name = serializers.SerializerMethodField('get_type_name')
    type_id = serializers.SerializerMethodField()
    localized_fields = ("name", "description")

    def get_type_name(self, obj):
        return get_language_value(
            obj.type.name,
            self.context.get("language_code")
        )

    @staticmethod
    def get_type_id(obj):
        return obj.type.id

    class Meta:
        model = AstroprocessorData
        fields = ["id", "name", "internal_id", "type_name", "type_id", "description"]


class SignPlanetConnectionSerializer(
    LocalizedFieldsSerializerMixin,
    serializers.ModelSerializer
):
    tolgee_namespace = "sign_planet"
    tolgee_key_prefix = "sp"
    localized_fields = ("name", "description")

    class Meta:
        model = SignPlanetConnection
        fields = '__all__'


class PlanetHouseConnectionSerializer(
    LocalizedFieldsSerializerMixin,
    serializers.ModelSerializer
):
    tolgee_namespace = "planet_house"
    tolgee_key_prefix = "ph"
    localized_fields = ("name", "description")

    class Meta:
        model = PlanetHouseConnection
        fields = '__all__'


class MasterHouseConnectionSerializer(
    LocalizedFieldsSerializerMixin,
    serializers.ModelSerializer
):
    tolgee_namespace = "master_house"
    tolgee_key_prefix = "mh"
    localized_fields = ("name", "description")

    class Meta:
        model = MasterHouseConnection
        fields = '__all__'
