from django.db import migrations, models


_INFO_LINK_FIELDS = [
    "whatsapp", "telegram_direct", "telegram", "viber", "youtube_alpha", "youtube_deep_sky",
]

_CONVERT_SQL = "\n".join(
    f"""
    ALTER TABLE info_{table}
        ALTER COLUMN {col} TYPE jsonb
        USING CASE
            WHEN {col} IS NULL OR {col} = '' THEN NULL
            ELSE json_build_object('ru', {col})::jsonb
        END;
    """
    for table, col in (
        [("info", f) for f in _INFO_LINK_FIELDS]
        + [("mobileappsversion", "link"), ("apppartinfo", "link")]
    )
)

_REVERT_SQL = "\n".join(
    f"ALTER TABLE info_{table} ALTER COLUMN {col} TYPE varchar(255) USING ({col}->>'ru');"
    for table, col in (
        [("info", f) for f in _INFO_LINK_FIELDS]
        + [("mobileappsversion", "link"), ("apppartinfo", "link")]
    )
)


class Migration(migrations.Migration):

    dependencies = [
        ('info', '0010_update_contacts'),
    ]

    operations = [
        migrations.RunSQL(sql=_CONVERT_SQL, reverse_sql=_REVERT_SQL),

        # Update Django state for Info fields
        *[
            migrations.SeparateDatabaseAndState(
                state_operations=[
                    migrations.AlterField(
                        model_name='info',
                        name=col,
                        field=models.JSONField(verbose_name=col, blank=True, null=True, default=None),
                    )
                ],
                database_operations=[],
            )
            for col in _INFO_LINK_FIELDS
        ],

        # Update Django state for MobileAppsVersion.link
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name='mobileappsversion',
                    name='link',
                    field=models.JSONField(verbose_name='Ссылка', blank=True, null=True, default=None),
                )
            ],
            database_operations=[],
        ),

        # Update Django state for AppPartInfo.link
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name='apppartinfo',
                    name='link',
                    field=models.JSONField(verbose_name='Ссылка', blank=True, null=True, default=None),
                )
            ],
            database_operations=[],
        ),
    ]
