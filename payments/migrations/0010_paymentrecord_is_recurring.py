# Generated manually - Add is_recurring field to PaymentRecord model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0009_recurringsubscription'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentrecord',
            name='is_recurring',
            field=models.BooleanField(
                default=False,
                help_text='Является ли этот платеж частью рекурентной подписки',
                verbose_name='Рекурентный платеж'
            ),
        ),
    ]
