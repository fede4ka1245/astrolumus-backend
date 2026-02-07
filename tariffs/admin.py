from datetime import timedelta

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.contrib.auth import get_user_model
from django.forms import ModelForm, ChoiceField, CharField
from django.utils import timezone
from django.db.models import Q, F

from rangefilter.filters import DateTimeRangeFilter, NumericRangeFilter

from .models import SitePayments, Tariff, ActivationTariff, TariffGroup

from utils.multilinguality import LocalizedModelAdmin

User = get_user_model()


class SitePaymentsAdminForm(ModelForm):
    # tariff = ChoiceField(choices=(*Tariff.objects.values_list('id', 'title'),))
    tariff = ChoiceField()
    tariff_code = CharField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tariff'].choices = Tariff.objects.values_list('id', 'title')
        if self.instance:
            try:
                self.initial['tariff'] = Tariff.objects.get(code=self.instance.tariff_code).id
            except Tariff.DoesNotExist:
                pass

    def clean_tariff_code(self):
        try:
            tariff = Tariff.objects.get(code=self.cleaned_data["tariff_code"])
        except Tariff.DoesNotExist:
            try:
                tariff = Tariff.objects.get(pk=int(self.data["tariff"]))  # assume that data is ok from admin part
            except Tariff.DoesNotExist:
                raise ValidationError("Tariff with this code not found")

        return tariff.code

    def clean_email(self):
        try:
            User.objects.get(email=self.cleaned_data["email"])
        except User.DoesNotExist:
            raise ValidationError("User with this email not found")

        return self.cleaned_data["email"]


@admin.register(SitePayments)
class SitePaymentsAdmin(admin.ModelAdmin):
    form = SitePaymentsAdminForm

    @transaction.atomic
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        # FIXME same code as tariffs/views/payment_from_site
        # try to find user
        user = None
        try:
            user = User.objects.get(email=obj.email)
        except User.DoesNotExist:
            pass

        tariff_paid = None
        try:
            tariff_paid = Tariff.objects.get(code=obj.tariff_code)
        except Tariff.DoesNotExist:
            raise ValidationError("Tariff with this code not found")

        # activate tariff
        if user and tariff_paid:
            # create default tariff
            Tariff.objects.get_user_tariffs(user=user)

            # try to find last activate tariff or already activate tariff from group
            last_activations = ActivationTariff.objects.filter(user=user).filter(
                Q(Q(tariff__validity_days__gt=0)
                  & Q(created_at__gt=timezone.now() - timedelta(days=1) *
                                     F("tariff__validity_days"))) |
                Q(tariff__validity_days=0)
            ).order_by("-created_at")

            tariff_group_last_activation = last_activations.filter(
                Q(tariff=tariff_paid) | Q(tariff__tariff_group_id=tariff_paid.tariff_group)).first()
            if tariff_group_last_activation:
                # if we have non ended activation
                tariff_of_last_activation = tariff_group_last_activation.tariff

                at = ActivationTariff.objects.create(
                    tariff=tariff_paid, user=user)
                at.created_at = tariff_group_last_activation.created_at + timedelta(
                    tariff_of_last_activation.validity_days)
                at.save()
            else:
                # activate now if there is no old group tariff
                ActivationTariff.objects.create(tariff=tariff_paid, user=user)

    list_display = ("id", "email", "datetime", "tariff_code", "currency", "amount")
    list_filter = ["tariff_code", ('datetime', DateTimeRangeFilter), "currency", ("amount", NumericRangeFilter)]
    search_fields = ("email", )


@admin.register(TariffGroup)
class TariffGroupAdmin(admin.ModelAdmin):
    pass


@admin.register(Tariff)
class TariffAdmin(LocalizedModelAdmin):
    localized_fields = ("title", "description", "public_description")
    list_display = ("id", "default_localized_title", "code", "tariff_group", "created_at", "start_datetime",
                    "end_datetime", "validity_days", "priority_for_default", "tariff_renew_wait")


@admin.register(ActivationTariff)
class ActivationTariffAdmin(admin.ModelAdmin):
    autocomplete_fields = ['user']
    list_filter = ["tariff", ('created_at', DateTimeRangeFilter),]

    def user__email(self, obj):
        return obj.user.email

    def validity_days(self, obj):
        if obj.tariff is None:
            return '-'
        return obj.tariff.validity_days

    list_display = ("id", "user", "user__email", "tariff", "created_at", "validity_days")
    search_fields = ("user__email", )
    readonly_fields = ["user__email", ]
