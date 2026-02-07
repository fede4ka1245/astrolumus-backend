from django.db import migrations, models


def stabilize_recurring_subscription_index_names(apps, schema_editor):
    """
    Stabilize RecurringSubscription index names.

    Historically we created explicit index names in 0009:
      - recurring_s_user_id_status_idx
      - recurring_s_subscri_idx
      - recurring_s_custome_idx

    Later, some environments ended up with Django auto-generated names (hash
    suffixes). This migration reconciles the DB to the explicit names so
    future `makemigrations` won't generate endless RenameIndex migrations.
    """

    RecurringSubscription = apps.get_model("payments", "RecurringSubscription")
    table_name = RecurringSubscription._meta.db_table

    connection = schema_editor.connection
    quote = schema_editor.quote_name

    def get_table_namespace(table: str):
        if "." in table:
            schema, rel = table.split(".", 1)
            schema = schema.strip('"')
            rel = rel.strip('"')
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT n.oid, n.nspname
                    FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE c.relname = %s
                      AND n.nspname = %s
                      AND c.relkind IN ('r','p')
                    LIMIT 1
                    """,
                    [rel, schema],
                )
                return cursor.fetchone()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT n.oid, n.nspname
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relname = %s
                  AND c.relkind IN ('r','p')
                ORDER BY n.nspname = 'public' DESC, n.nspname ASC
                LIMIT 1
                """,
                [table],
            )
            return cursor.fetchone()

    table_ns = get_table_namespace(table_name)
    table_namespace_oid = table_ns[0] if table_ns else None
    table_schema = table_ns[1] if table_ns else None

    def q_index(index_name: str) -> str:
        if table_schema:
            return f"{quote(table_schema)}.{quote(index_name)}"
        return quote(index_name)

    def index_exists(index_name: str) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 1
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relkind = 'i'
                  AND c.relname = %s
                  AND (%s IS NULL OR c.relnamespace = %s)
                LIMIT 1
                """,
                [index_name, table_namespace_oid, table_namespace_oid],
            )
            return cursor.fetchone() is not None

    def drop_index(index_name: str) -> None:
        schema_editor.execute(f"DROP INDEX IF EXISTS {q_index(index_name)}")

    def rename_index(old_name: str, new_name: str) -> None:
        schema_editor.execute(f"ALTER INDEX {q_index(old_name)} RENAME TO {quote(new_name)}")

    def create_index(field_names, index_name: str) -> None:
        schema_editor.add_index(
            RecurringSubscription,
            models.Index(fields=field_names, name=index_name),
        )

    def auto_index_name(column_names):
        return schema_editor._create_index_name(table_name, column_names, suffix="_idx")

    # (canonical_name, model_fields, db_columns)
    index_specs = [
        ("recurring_s_user_id_status_idx", ["user", "status"], ["user_id", "status"]),
        ("recurring_s_subscri_idx", ["subscription_id"], ["subscription_id"]),
        ("recurring_s_custome_idx", ["customer_id"], ["customer_id"]),
    ]

    for canonical_name, field_names, column_names in index_specs:
        auto_name = auto_index_name(column_names)

        canonical_exists = index_exists(canonical_name)
        auto_exists = auto_name != canonical_name and index_exists(auto_name)

        if canonical_exists and auto_exists:
            drop_index(auto_name)
            continue

        if not canonical_exists and auto_exists:
            rename_index(auto_name, canonical_name)
            continue

        if not canonical_exists and not auto_exists:
            create_index(field_names, canonical_name)


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0013_rename_recurring_s_user_id_status_idx_recurring_s_user_id_42b2db_idx_and_more"),
    ]

    operations = [
        migrations.RunPython(
            stabilize_recurring_subscription_index_names,
            reverse_code=migrations.RunPython.noop,
        ),
    ]


