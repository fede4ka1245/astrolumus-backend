from django.db import migrations, models
from django.db.models import Count, Q


def dedupe_payment_records(apps, schema_editor):
    PaymentRecord = apps.get_model("payments", "PaymentRecord")
    duplicates = (
        PaymentRecord.objects.exclude(payment_id__isnull=True)
        .exclude(payment_id="")
        .values("payment_system", "payment_id")
        .annotate(cnt=Count("id"))
        .filter(cnt__gt=1)
    )

    for dup in duplicates.iterator():
        records = (
            PaymentRecord.objects.filter(
                payment_system=dup["payment_system"],
                payment_id=dup["payment_id"],
            )
            .order_by("created_at", "id")
            .values_list("id", flat=True)
        )
        ids = list(records)
        if len(ids) > 1:
            PaymentRecord.objects.filter(id__in=ids[1:]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0010_paymentrecord_is_recurring"),
    ]

    operations = [
        migrations.RunPython(dedupe_payment_records, reverse_code=migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="paymentrecord",
            constraint=models.UniqueConstraint(
                fields=("payment_system", "payment_id"),
                condition=Q(payment_id__isnull=False) & ~Q(payment_id=""),
                name="uniq_payment_records_system_payment_id",
            ),
        ),
    ]
