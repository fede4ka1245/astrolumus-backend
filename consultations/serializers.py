from rest_framework import serializers

from .models import Consultation


class ConsultationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consultation
        fields = ("id", "name", "contact", "topic", "message", "preferred_time", "status", "created_at", "user")
        read_only_fields = ("id", "status", "created_at", "user")
