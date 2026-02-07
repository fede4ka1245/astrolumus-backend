# Generated manually

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('payments', '0007_paymentsettings'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_first_name', models.CharField(blank=True, max_length=150, null=True, verbose_name='Имя в приложении')),
                ('user_last_name', models.CharField(blank=True, max_length=150, null=True, verbose_name='Фамилия в приложении')),
                ('user_email', models.EmailField(blank=True, max_length=254, null=True, verbose_name='Email в приложении')),
                ('merchant_first_name', models.CharField(blank=True, max_length=150, null=True, verbose_name='Имя при оплате')),
                ('merchant_last_name', models.CharField(blank=True, max_length=150, null=True, verbose_name='Фамилия при оплате')),
                ('merchant_email', models.EmailField(blank=True, max_length=254, null=True, verbose_name='Email при оплате')),
                ('tariff_name', models.CharField(blank=True, max_length=255, null=True, verbose_name='Название тарифа')),
                ('payment_system', models.CharField(choices=[('stripe', 'Stripe'), ('bepaid', 'BePaid')], max_length=20, verbose_name='Платежная система')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Сумма оплаты')),
                ('currency', models.CharField(default='USD', max_length=3, verbose_name='Валюта')),
                ('status', models.CharField(choices=[('success', 'Успешно'), ('failed', 'Неуспешно'), ('pending', 'Ожидание')], default='success', max_length=20, verbose_name='Статус')),
                ('payment_id', models.CharField(blank=True, max_length=255, null=True, verbose_name='ID платежа')),
                ('raw_data', models.JSONField(blank=True, default=dict, verbose_name='Сырые данные платежа')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('order', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='payment_records', to='payments.order', verbose_name='Заказ')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='payment_records', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'Запись об оплате',
                'verbose_name_plural': 'Записи об оплатах',
                'db_table': 'payment_records',
                'ordering': ['-created_at'],
            },
        ),
    ]
