from django.contrib import admin

from .models import Event


@admin.register(Event)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title",)
    search_fields = ("title", "description")
    list_filter = ("user_dst", "user_src", "access_type", "event_date")
