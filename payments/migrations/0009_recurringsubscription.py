# Generated manually - Add RecurringSubscription model for recurring payments

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tariffs', '0010_tariff_pricing'),
        ('payments', '0008_paymentrecord'),
    ]

    operations = [
        migrations.CreateModel(
            name='RecurringSubscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payment_system', models.CharField(choices=[('stripe', 'Stripe'), ('bepaid', 'BePaid')], max_length=20, verbose_name='Платежная система')),
                ('subscription_id', models.CharField(max_length=255, unique=True, verbose_name='ID подписки')),
                ('customer_id', models.CharField(blank=True, max_length=255, null=True, verbose_name='ID клиента')),
                ('status', models.CharField(choices=[('active', 'Активна'), ('canceled', 'Отменена'), ('past_due', 'Просрочена'), ('unpaid', 'Не оплачена'), ('trialing', 'Пробный период'), ('incomplete', 'Не завершена'), ('incomplete_expired', 'Не завершена (истекла)')], default='incomplete', max_length=30, verbose_name='Статус подписки')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Сумма подписки')),
                ('currency', models.CharField(default='USD', max_length=3, verbose_name='Валюта')),
                ('current_period_start', models.DateTimeField(blank=True, null=True, verbose_name='Начало текущего периода')),
                ('current_period_end', models.DateTimeField(blank=True, null=True, verbose_name='Конец текущего периода')),
                ('cancel_at_period_end', models.BooleanField(default=False, verbose_name='Отменить в конце периода')),
                ('canceled_at', models.DateTimeField(blank=True, null=True, verbose_name='Дата отмены')),
                ('metadata', models.JSONField(blank=True, default=dict, verbose_name='Метаданные')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Дата обновления')),
                ('order', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='recurring_subscriptions', to='payments.order', verbose_name='Заказ')),
                ('tariff', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recurring_subscriptions', to='tariffs.tariff', verbose_name='Тариф')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recurring_subscriptions', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'Рекурентная подписка',
                'verbose_name_plural': 'Рекурентные подписки',
                'db_table': 'recurring_subscriptions',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='recurringsubscription',
            index=models.Index(fields=['user', 'status'], name='recurring_s_user_id_status_idx'),
        ),
        migrations.AddIndex(
            model_name='recurringsubscription',
            index=models.Index(fields=['subscription_id'], name='recurring_s_subscri_idx'),
        ),
        migrations.AddIndex(
            model_name='recurringsubscription',
            index=models.Index(fields=['customer_id'], name='recurring_s_custome_idx'),
        ),
    ]
