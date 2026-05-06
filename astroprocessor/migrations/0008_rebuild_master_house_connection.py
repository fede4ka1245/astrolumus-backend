from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('astroprocessor', '0007_rename_planet_to_sign_in_master_house'),
    ]

    operations = [
        # Populate sign from planet for rows where sign is NULL (data migration)
        migrations.RunSQL(
            "UPDATE astroprocessor_masterhouseconnection SET sign = planet WHERE sign IS NULL",
            migrations.RunSQL.noop,
        ),
        # Remove old planet field
        migrations.RemoveField(
            model_name='masterhouseconnection',
            name='planet',
        ),
        # Rename sign -> master_house
        migrations.RenameField(
            model_name='masterhouseconnection',
            old_name='sign',
            new_name='master_house',
        ),
        # Rename house -> at_house
        migrations.RenameField(
            model_name='masterhouseconnection',
            old_name='house',
            new_name='at_house',
        ),
        # Make master_house not nullable
        migrations.AlterField(
            model_name='masterhouseconnection',
            name='master_house',
            field=models.IntegerField(verbose_name='Управитель дома'),
        ),
    ]
