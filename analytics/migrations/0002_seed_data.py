from django.db import migrations


def seed_categories(apps, schema_editor):
    ExpenseCategory = apps.get_model("analytics", "ExpenseCategory")
    categories = [
        ("Серверы и хостинг", "Coolify, DigitalOcean, домены, SSL"),
        ("Реклама", "Таргетированная реклама, контекст, блогеры"),
        ("Зарплаты", "Оплата труда команды"),
        ("Платёжные комиссии", "Комиссии Stripe, BePaid"),
        ("Инструменты и SaaS", "Sentry, Tolgee, Firebase, GitHub, и др."),
        ("Контент", "Создание астрологического контента, переводы"),
        ("Юридические", "Бухгалтерия, лицензии, юр. услуги"),
        ("Прочее", "Другие расходы"),
    ]
    for name, desc in categories:
        ExpenseCategory.objects.get_or_create(name=name, defaults={"description": desc})


def seed_rates(apps, schema_editor):
    CurrencyRate = apps.get_model("analytics", "CurrencyRate")
    rates = [
        ("USD", "1.000000"),
        ("EUR", "1.080000"),  # 1 EUR ≈ 1.08 USD
        ("RUB", "0.011000"),  # 1 RUB ≈ 0.011 USD
        ("BYN", "0.310000"),  # 1 BYN ≈ 0.31 USD
    ]
    for currency, rate in rates:
        CurrencyRate.objects.get_or_create(
            currency=currency, defaults={"rate_to_usd": rate}
        )


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_categories, migrations.RunPython.noop),
        migrations.RunPython(seed_rates, migrations.RunPython.noop),
    ]
