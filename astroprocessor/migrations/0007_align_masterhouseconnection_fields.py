from django.db import migrations, models


class Migration(migrations.Migration):
    """Align main's MasterHouseConnection model with the staging-schema DB.

    The deployed prod DB (cloned from the staging schema) already has the
    columns ``master_house`` / ``at_house`` instead of the old ``planet`` /
    ``house`` that main's model declared. This migration only realigns Django's
    model *state* — it performs NO database operations (the columns already
    exist) so it is safe to run against the existing prod schema.
    """

    dependencies = [
        ('astroprocessor', '0006_alter_masterhouseconnection_description_and_more'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RemoveField(
                    model_name='masterhouseconnection',
                    name='planet',
                ),
                migrations.RemoveField(
                    model_name='masterhouseconnection',
                    name='house',
                ),
                migrations.AddField(
                    model_name='masterhouseconnection',
                    name='master_house',
                    field=models.IntegerField(default=1, verbose_name='Управитель дома'),
                    preserve_default=False,
                ),
                migrations.AddField(
                    model_name='masterhouseconnection',
                    name='at_house',
                    field=models.IntegerField(default=1, verbose_name='В доме'),
                    preserve_default=False,
                ),
            ],
        ),
    ]
