from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('info', '0011_convert_link_fields_to_jsonfield'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE info_mobileappsversion
                    ALTER COLUMN description TYPE jsonb
                    USING CASE
                        WHEN description IS NULL OR description = '' THEN NULL
                        ELSE json_build_object('ru', description)::jsonb
                    END;
            """,
            reverse_sql="ALTER TABLE info_mobileappsversion ALTER COLUMN description TYPE text USING (description->>'ru');",
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name='mobileappsversion',
                    name='description',
                    field=models.JSONField(blank=True, default=None, null=True, verbose_name='Описание'),
                )
            ],
            database_operations=[],
        ),
    ]
