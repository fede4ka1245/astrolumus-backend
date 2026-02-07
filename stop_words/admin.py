from django.contrib import admin

from .models import Word


@admin.register(Word)
class WordAdmin(admin.ModelAdmin):
    search_fields = ("word",)
    list_display = ("word",)
