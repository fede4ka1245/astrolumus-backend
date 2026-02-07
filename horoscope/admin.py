from django.contrib import admin

from .models import HoroscopeCache, MyHoroscope


@admin.register(HoroscopeCache)
class HoroscopeCacheAdmin(admin.ModelAdmin):
    search_fields = ["id", "latitude", "longitude"]


@admin.register(MyHoroscope)
class MyHoroscopeAdmin(admin.ModelAdmin):
    autocomplete_fields = ["horoscope", "user"]

