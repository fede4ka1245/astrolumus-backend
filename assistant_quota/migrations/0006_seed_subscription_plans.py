from django.db import migrations


# Prices are PLACEHOLDERS — edit them in the Django admin (Тарифы подписки).
DEFAULT_PLANS = [
    {
        "code": "sub-3m",
        "months": 3,
        "title": {"ru": "3 месяца", "en": "3 months"},
        "price_rub": "990.00",
        "is_popular": False,
        "sort_order": 1,
    },
    {
        "code": "sub-6m",
        "months": 6,
        "title": {"ru": "6 месяцев", "en": "6 months"},
        "price_rub": "1690.00",
        "is_popular": True,
        "sort_order": 2,
    },
    {
        "code": "sub-12m",
        "months": 12,
        "title": {"ru": "12 месяцев", "en": "12 months"},
        "price_rub": "2990.00",
        "is_popular": False,
        "sort_order": 3,
    },
]


def seed_plans(apps, schema_editor):
    SubscriptionPlan = apps.get_model("assistant_quota", "SubscriptionPlan")
    # Idempotent: get_or_create per plan so re-running never duplicates rows
    # and never overwrites admin-edited prices.
    for data in DEFAULT_PLANS:
        SubscriptionPlan.objects.get_or_create(
            code=data["code"],
            defaults={
                "months": data["months"],
                "title": data["title"],
                "description": {},
                "price_rub": data["price_rub"],
                "is_popular": data["is_popular"],
                "is_active": True,
                "sort_order": data["sort_order"],
            },
        )


def unseed_plans(apps, schema_editor):
    # Reverse is a no-op: plans may be referenced by subscriptions/payments
    # (SubscriptionPlan is PROTECT-ed) or edited in admin.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("assistant_quota", "0005_subscription_subscriptionplan_subscriptionpayment_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_plans, unseed_plans),
    ]
