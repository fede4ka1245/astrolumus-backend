# Generated migration - Add currency field to Order model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0005_order_tariff'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='currency',
            field=models.CharField(
                default='USD',
                help_text='Currency code (USD, RUB, BYN, EUR)',
                max_length=3,
                verbose_name='Валюта'
            ),
        ),
    ]

