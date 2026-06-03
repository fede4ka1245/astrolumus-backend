from django.contrib import admin

from .models import Consultation


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "contact", "topic", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("name", "contact", "message")
    list_editable = ("status",)
    readonly_fields = ("created_at", "user")
