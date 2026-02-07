from django.db import migrations, models


def reconcile_recurring_subscription_indexes(apps, schema_editor):
    """
    Make index naming resilient across databases with different index history.

    Some DBs don't have the legacy explicit names from 0009 anymore, so a plain
    RenameIndex migration fails with:
      psycopg2.errors.UndefinedTable: relation "..." does not exist
    """

    RecurringSubscription = apps.get_model("payments", "RecurringSubscription")
    table_name = RecurringSubscription._meta.db_table

    connection = schema_editor.connection
    quote = schema_editor.quote_name

    def get_table_namespace(table: str):
        # Resolve schema for the table to avoid false positives when an index
        # with the same name exists in another schema.
        # Works for both plain `recurring_subscriptions` and `schema.table`.
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
        # Prefer schema-qualified operations to be robust to search_path.
        if table_schema:
            return f"{quote(table_schema)}.{quote(index_name)}"
        return quote(index_name)

    def index_exists(index_name: str) -> bool:
        # Do not rely solely on introspection here: in some real-world DB states
        # (e.g., partially-created/invalid indexes, schema/search_path quirks),
        # `get_constraints()` can miss objects that still exist as relations.
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

    def desired_index_name(column_names):
        return schema_editor._create_index_name(table_name, column_names, suffix="_idx")

    def drop_index(index_name: str) -> None:
        schema_editor.execute(f"DROP INDEX IF EXISTS {q_index(index_name)}")

    def rename_index(old_name: str, new_name: str) -> None:
        schema_editor.execute(
            f"ALTER INDEX {q_index(old_name)} RENAME TO {quote(new_name)}"
        )

    def create_index(field_names, index_name: str) -> None:
        schema_editor.add_index(
            RecurringSubscription,
            models.Index(fields=field_names, name=index_name),
        )

    index_specs = [
        # (legacy_name, model_fields, db_columns)
        ("recurring_s_user_id_status_idx", ["user", "status"], ["user_id", "status"]),
        ("recurring_s_subscri_idx", ["subscription_id"], ["subscription_id"]),
        ("recurring_s_custome_idx", ["customer_id"], ["customer_id"]),
    ]

    for legacy_name, field_names, column_names in index_specs:
        desired_name = desired_index_name(column_names)

        legacy_exists = index_exists(legacy_name)
        desired_exists = index_exists(desired_name)

        if legacy_exists and desired_exists and legacy_name != desired_name:
            drop_index(legacy_name)
            continue

        if legacy_exists and not desired_exists:
            rename_index(legacy_name, desired_name)
            continue

        if not legacy_exists and not desired_exists:
            create_index(field_names, desired_name)


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0011_paymentrecord_unique_payment_id"),
    ]

    operations = [
        migrations.RunPython(
            reconcile_recurring_subscription_indexes,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
