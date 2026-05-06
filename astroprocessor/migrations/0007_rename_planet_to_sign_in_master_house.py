from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('astroprocessor', '0006_alter_masterhouseconnection_description_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='masterhouseconnection',
            name='sign',
            field=models.IntegerField(verbose_name='Знак', null=True, blank=True),
        ),
    ]
