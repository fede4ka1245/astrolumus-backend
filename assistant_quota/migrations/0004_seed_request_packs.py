from django.db import migrations


DEFAULT_PACKS = [
    {
        "code": "p10",
        "title": {"ru": "10 запросов", "en": "10 requests"},
        "requests_count": 10,
        "price_rub": "199.00",
        "discount_percent": None,
        "is_popular": False,
        "sort_order": 1,
    },
    {
        "code": "p30",
        "title": {"ru": "30 запросов", "en": "30 requests"},
        "requests_count": 30,
        "price_rub": "499.00",
        "discount_percent": 16,
        "is_popular": True,
        "sort_order": 2,
    },
    {
        "code": "p100",
        "title": {"ru": "100 запросов", "en": "100 requests"},
        "requests_count": 100,
        "price_rub": "1290.00",
        "discount_percent": 35,
        "is_popular": False,
        "sort_order": 3,
    },
]


def seed_packs(apps, schema_editor):
    RequestPack = apps.get_model("assistant_quota", "RequestPack")
    # Idempotent: only seed when there are no packs at all.
    if RequestPack.objects.exists():
        return
    for data in DEFAULT_PACKS:
        RequestPack.objects.create(
            code=data["code"],
            title=data["title"],
            description={},
            requests_count=data["requests_count"],
            price_rub=data["price_rub"],
            discount_percent=data["discount_percent"],
            is_popular=data["is_popular"],
            is_active=True,
            sort_order=data["sort_order"],
        )


def unseed_packs(apps, schema_editor):
    # Reverse is a no-op: we don't want to delete packs that may have been
    # edited or referenced by purchases (RequestPack is PROTECT-ed).
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("assistant_quota", "0003_requestpack_discount_percent_requestpack_is_popular_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_packs, unseed_packs),
    ]
