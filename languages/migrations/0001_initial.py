from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0024_applanguage_enabled'),
    ]

    operations = [
        migrations.CreateModel(
            name='AppLanguageProxy',
            fields=[
            ],
            options={
                'verbose_name': 'Язык',
                'verbose_name_plural': 'Языки приложения',
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('users.applanguage',),
        ),
    ]
