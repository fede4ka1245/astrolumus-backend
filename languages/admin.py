from django.contrib import admin

from languages.models import AppLanguageProxy


@admin.register(AppLanguageProxy)
class AppLanguageProxyAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "enabled")
    list_editable = ("enabled",)
    ordering = ("name",)
