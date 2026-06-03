from rest_framework import serializers

from .models import MyHoroscope, HoroscopeCache


class HoroscopeCacheSerializer(serializers.ModelSerializer):
    class Meta:
        model = HoroscopeCache
        fields = "__all__"


class HoroscopeCacheListSerializer(serializers.ModelSerializer):
    class Meta:
        model = HoroscopeCache
        exclude = ["data"]


class MyHoroscopeListSerializer(serializers.ModelSerializer):
    horoscope_id = serializers.PrimaryKeyRelatedField(source="horoscope", queryset=HoroscopeCache.objects.all(),
                                                      write_only=True)
    horoscope = HoroscopeCacheListSerializer(read_only=True)
    user = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )

    class Meta:
        model = MyHoroscope
        fields = ["id", "name", "city", "user", "horoscope_id", "horoscope", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class MyHoroscopeSerializer(serializers.ModelSerializer):
    horoscope_id = serializers.PrimaryKeyRelatedField(source="horoscope", queryset=HoroscopeCache.objects.all(),
                                                      write_only=True)
    horoscope = HoroscopeCacheSerializer(read_only=True)
    user = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )

    class Meta:
        model = MyHoroscope
        fields = ["id", "name", "city", "user", "horoscope_id", "horoscope", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]
        # Drop the auto-generated UniqueTogetherValidator for [horoscope, user]:
        # auto-save re-sends the same build, and the idempotency is handled in
        # MyHoroscopeViewSet.create (returns the existing row with 200). The DB
        # unique_together constraint still guarantees integrity.
        validators = []


class SettingsSerializer(serializers.Serializer):
    LANGUAGE_CHOICES = (
        ("ru", "Русский"),
        ("en", "English"),
        ("sa_en", "Санскрипт (eng)"),
        ("sa_ru", "Санскрипт (ru)"),
    )

    ARUDHA_CHOICES = (
        (0, "Согласно К.Н. Рао"),
        (1, "Согласно С. Ратху"),
        (2, "Согласно И. Рангачарьи"),
        (3, "Согласно Шри Джйотиш Акубенсу"),
    )

    language = serializers.ChoiceField(
        choices=LANGUAGE_CHOICES, required=False
    )
    arudha = serializers.ChoiceField(
        choices=ARUDHA_CHOICES, required=False
    )
