# Generated migration - Add tariff field to Order model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tariffs', '0010_tariff_pricing'),
        ('payments', '0004_order_comment_order_payment_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='tariff',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='orders', to='tariffs.tariff'),
        ),
    ]

