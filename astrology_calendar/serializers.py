from rest_framework import serializers

from .models import Event


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = (
            "user_src",
            "title",
            "description",
            "image",
            "access_type",
            "event_date",
        )
