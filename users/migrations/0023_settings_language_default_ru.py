from django.db import migrations, models


def flip_en_to_ru(apps, schema_editor):
    """Продукт русскоязычный: старый дефолт 'en' лежал у пользователей не по
    их выбору — один раз переводим en → ru (выбор в настройках сохраняется)."""
    Settings = apps.get_model("users", "Settings")
    Settings.objects.filter(language="en").update(language="ru")


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0022_applanguage_user_app_language"),
    ]

    operations = [
        migrations.AlterField(
            model_name="settings",
            name="language",
            field=models.CharField(default="ru", max_length=10),
        ),
        migrations.RunPython(flip_en_to_ru, migrations.RunPython.noop),
    ]
