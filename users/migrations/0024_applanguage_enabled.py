from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0023_user_consent_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='applanguage',
            name='enabled',
            field=models.BooleanField(default=True, verbose_name='enabled'),
        ),
    ]
