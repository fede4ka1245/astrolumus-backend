# Generated migration for adding pricing in multiple currencies

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tariffs', '0009_alter_tariff_description_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='tariff',
            name='price_rub',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Цена в российских рублях', max_digits=10, verbose_name='Цена (RUB)'),
        ),
        migrations.AddField(
            model_name='tariff',
            name='price_byn',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Цена в белорусских рублях', max_digits=10, verbose_name='Цена (BYN)'),
        ),
        migrations.AddField(
            model_name='tariff',
            name='price_usd',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Цена в американских долларах', max_digits=10, verbose_name='Цена (USD)'),
        ),
        migrations.AddField(
            model_name='tariff',
            name='price_eur',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Цена в евро', max_digits=10, verbose_name='Цена (EUR)'),
        ),
    ]









