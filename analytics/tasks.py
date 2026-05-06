"""
Periodic task to sync production data into the analytics (cold) database.
Runs every hour via Celery Beat.
"""
from celery import shared_task
from django.db import connections


# Tables to sync from main DB to analytics DB.
# Each entry: (source_table, columns_to_copy)
SYNC_TABLES = [
    (
        "users_user",
        "id, email, first_name, last_name, date_joined, last_seen, language, consent_marketing",
    ),
    (
        "payment_records",
        "id, user_id, user_email, tariff_name, payment_system, amount, currency, "
        "status, is_recurring, payment_id, created_at",
    ),
    (
        "recurring_subscriptions",
        "id, user_id, tariff_id, payment_system, subscription_id, customer_id, "
        "status, amount, currency, current_period_start, current_period_end, "
        "cancel_at_period_end, canceled_at, created_at, updated_at",
    ),
    (
        "tariffs_tariff",
        "id, code, public, validity_days, price_rub, price_usd, price_eur, price_byn, "
        "can_work_with_another, tariff_renew_wait",
    ),
    (
        "tariffs_activationtariff",
        "id, user_id, tariff_id, created_at",
    ),
    (
        "orders",
        "id, user_id, status, amount, currency, pay_system, created_at, tariff_id, course_id",
    ),
    (
        "expenses",
        "id, category_id, description, amount, currency, period, is_recurring, created_at, updated_at",
    ),
    (
        "expense_categories",
        "id, name, description",
    ),
    (
        "currency_rates",
        "id, currency, rate_to_usd, updated_at",
    ),
]


@shared_task(name="analytics.sync_to_analytics_db")
def sync_to_analytics_db():
    """
    Copy data from the main (default) database to the analytics database.
    Uses DELETE + INSERT (full refresh) for simplicity and data consistency.
    """
    src = connections["default"]
    dst = connections["analytics"]

    synced = []

    for table, columns in SYNC_TABLES:
        try:
            with src.cursor() as cur:
                cur.execute(f"SELECT {columns} FROM {table}")
                rows = cur.fetchall()
                col_list = [c.strip() for c in columns.split(",")]

            with dst.cursor() as cur:
                cur.execute(f"DROP TABLE IF EXISTS {table}")
                # Build CREATE TABLE from source schema
                with src.cursor() as src_cur:
                    src_cur.execute(f"""
                        SELECT column_name, data_type, character_maximum_length
                        FROM information_schema.columns
                        WHERE table_name = %s AND column_name IN %s
                        ORDER BY ordinal_position
                    """, [table, tuple(col_list)])
                    schema_rows = src_cur.fetchall()

                col_defs = []
                for col_name, data_type, max_len in schema_rows:
                    if data_type == "character varying" and max_len:
                        col_defs.append(f'"{col_name}" varchar({max_len})')
                    elif data_type == "character varying":
                        col_defs.append(f'"{col_name}" varchar(255)')
                    elif data_type in ("integer", "bigint", "smallint"):
                        col_defs.append(f'"{col_name}" {data_type}')
                    elif data_type == "numeric":
                        col_defs.append(f'"{col_name}" numeric(12,2)')
                    elif data_type == "boolean":
                        col_defs.append(f'"{col_name}" boolean')
                    elif data_type in ("timestamp with time zone", "timestamp without time zone"):
                        col_defs.append(f'"{col_name}" timestamp with time zone')
                    elif data_type == "date":
                        col_defs.append(f'"{col_name}" date')
                    elif data_type == "uuid":
                        col_defs.append(f'"{col_name}" uuid')
                    elif data_type == "text":
                        col_defs.append(f'"{col_name}" text')
                    elif data_type == "jsonb":
                        col_defs.append(f'"{col_name}" jsonb')
                    else:
                        col_defs.append(f'"{col_name}" text')

                create_sql = f'CREATE TABLE {table} ({", ".join(col_defs)})'
                cur.execute(create_sql)

                # Insert data
                if rows:
                    placeholders = ", ".join(["%s"] * len(col_list))
                    quoted_cols = ", ".join([f'"{c}"' for c in col_list])
                    insert_sql = f"INSERT INTO {table} ({quoted_cols}) VALUES ({placeholders})"
                    cur.executemany(insert_sql, rows)

            synced.append(f"{table}: {len(rows)} rows")

        except Exception as e:
            synced.append(f"{table}: ERROR - {e}")

    return "; ".join(synced)
