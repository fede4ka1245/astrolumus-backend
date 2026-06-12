from django.contrib import admin

from .models import BusinessLead


@admin.register(BusinessLead)
class BusinessLeadAdmin(admin.ModelAdmin):
    list_display = ("name", "contact", "comment", "source", "created_at", "is_processed")
    list_filter = ("is_processed", "source")
    list_editable = ("is_processed",)
    search_fields = ("name", "contact", "comment")
    readonly_fields = ("created_at",)
