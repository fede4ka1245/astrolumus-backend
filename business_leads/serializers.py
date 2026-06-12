from rest_framework import serializers

from .models import BusinessLead


class BusinessLeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessLead
        fields = ("name", "contact", "comment", "source")
        extra_kwargs = {
            "comment": {"required": False, "allow_blank": True},
            "source": {"required": False, "allow_blank": True},
        }
