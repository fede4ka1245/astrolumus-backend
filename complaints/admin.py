from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline

from .models import Complaint, Feedback


# for use in external component
class ComplaintInline(GenericTabularInline):
    autocomplete_fields = ["user", "assigned_employee"]
    model = Complaint
    extra = 1
    can_delete = True


admin.site.register(Complaint)
admin.site.register(Feedback)
