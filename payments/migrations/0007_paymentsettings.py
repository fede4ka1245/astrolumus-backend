# Generated migration - Add PaymentSettings model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0006_order_currency'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('platform', models.CharField(
                    choices=[('ios', 'iOS'), ('android', 'Android'), ('web', 'Web')],
                    help_text='Платформа для которой настраиваются платежи',
                    max_length=50,
                    unique=True,
                    verbose_name='Платформа'
                )),
                ('enabled', models.BooleanField(
                    default=True,
                    help_text='Включить или выключить платежи для данной платформы',
                    verbose_name='Платежи включены'
                )),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Дата обновления')),
            ],
            options={
                'verbose_name': 'Настройка платежей',
                'verbose_name_plural': 'Настройки платежей',
                'db_table': 'payment_settings',
            },
        ),
    ]

