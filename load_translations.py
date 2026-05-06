#!/usr/bin/env python3
"""
Load English translations from XLS files into the astroprocessor database.

XLS files structure:
- First rows (1-4): info/comments about orange cells
- Row 5 (or row 1 for some files): column headers
- Data rows follow

All translations go into JSONField columns as {"ru": "...", "en": "..."} format.
"""

import openpyxl
import psycopg2
import json
import sys

DB_CONFIG = {
    'host': '64.226.83.59',
    'port': 5432,
    'dbname': 'alpha',
    'user': 'alpha',
    'password': 'ahpla123',
}


def read_xlsx_data(filepath, header_row, data_start_row, columns):
    """
    Read XLSX file and return list of dicts.
    columns: list of column names matching header, e.g. ['id', 'internal_id', 'name_en', 'description_en']
    """
    wb = openpyxl.load_workbook(filepath)
    ws = wb.active
    rows = []
    for row in ws.iter_rows(min_row=data_start_row, values_only=True):
        if row[0] is None:  # skip empty rows
            continue
        record = {}
        for i, col_name in enumerate(columns):
            if col_name is None:
                continue
            val = row[i] if i < len(row) else None
            record[col_name] = val
        rows.append(record)
    wb.close()
    return rows


def read_houses_xlsx(filepath):
    """Special reader for houses - has extra column E for text to append."""
    wb = openpyxl.load_workbook(filepath)
    ws = wb.active
    rows = []
    for row in ws.iter_rows(min_row=6, values_only=True):
        if row[0] is None:
            continue
        record = {
            'id': row[0],
            'internal_id': row[1],
            'name_en': row[2],
            'description_en': row[3],
            'description_append': row[4] if len(row) > 4 else None,
        }
        rows.append(record)
    wb.close()
    return rows


def update_astroprocessor_data(cur, record_id, name_en, description_en):
    """Update name and description JSON fields for astroprocessor_astroprocessordata."""
    updates = []
    params = []

    if name_en is not None:
        updates.append("name = jsonb_set(COALESCE(name, '{}'::jsonb), '{en}', %s::jsonb)")
        params.append(json.dumps(name_en))

    if description_en is not None:
        updates.append("description = jsonb_set(COALESCE(description, '{}'::jsonb), '{en}', %s::jsonb)")
        params.append(json.dumps(description_en))

    if not updates:
        return 0

    params.append(int(record_id))
    sql = f"UPDATE astroprocessor_astroprocessordata SET {', '.join(updates)} WHERE id = %s"
    cur.execute(sql, params)
    return cur.rowcount


def update_connection_table(cur, table_name, record_id, name_en, description_en):
    """Update name and description JSON fields for connection tables."""
    updates = []
    params = []

    if name_en is not None:
        updates.append("name = jsonb_set(COALESCE(name, '{}'::jsonb), '{en}', %s::jsonb)")
        params.append(json.dumps(name_en))

    if description_en is not None:
        updates.append("description = jsonb_set(COALESCE(description, '{}'::jsonb), '{en}', %s::jsonb)")
        params.append(json.dumps(description_en))

    if not updates:
        return 0

    params.append(int(record_id))
    sql = f"UPDATE {table_name} SET {', '.join(updates)} WHERE id = %s"
    cur.execute(sql, params)
    return cur.rowcount


def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    xls_dir = "/root/projects/horo-me/xls"
    total_updated = 0
    total_skipped = 0

    # 1. Zodiac Signs (type_id=1) - header at row 1, data from row 2
    print("=" * 60)
    print("Loading Zodiac Signs...")
    data = read_xlsx_data(
        f"{xls_dir}/export_zodiac_signs_en.xlsx",
        header_row=1, data_start_row=2,
        columns=['id', 'internal_id', 'name_en', 'description_en']
    )
    updated = 0
    for row in data:
        cnt = update_astroprocessor_data(cur, row['id'], row['name_en'], row['description_en'])
        updated += cnt
        if cnt == 0:
            print(f"  WARNING: No row found for id={row['id']}")
            total_skipped += 1
    print(f"  Updated {updated}/{len(data)} rows")
    total_updated += updated

    # 2. Nakshatras (type_id=2) - header at row 5, data from row 6
    print("=" * 60)
    print("Loading Nakshatras...")
    data = read_xlsx_data(
        f"{xls_dir}/export_nakshatras_en.xlsx",
        header_row=5, data_start_row=6,
        columns=['id', 'internal_id', 'name_en', 'description_en']
    )
    updated = 0
    for row in data:
        cnt = update_astroprocessor_data(cur, row['id'], row['name_en'], row['description_en'])
        updated += cnt
        if cnt == 0:
            print(f"  WARNING: No row found for id={row['id']}")
            total_skipped += 1
    print(f"  Updated {updated}/{len(data)} rows")
    total_updated += updated

    # 3. Planets (type_id=3) - header at row 5, data from row 6
    print("=" * 60)
    print("Loading Planets...")
    data = read_xlsx_data(
        f"{xls_dir}/export_planets_en.xlsx",
        header_row=5, data_start_row=6,
        columns=['id', 'internal_id', 'name_en', 'description_en']
    )
    updated = 0
    for row in data:
        cnt = update_astroprocessor_data(cur, row['id'], row['name_en'], row['description_en'])
        updated += cnt
        if cnt == 0:
            print(f"  WARNING: No row found for id={row['id']}")
            total_skipped += 1
    print(f"  Updated {updated}/{len(data)} rows")
    total_updated += updated

    # 4. Karakas (type_id=4) - header at row 5, data from row 6
    print("=" * 60)
    print("Loading Karakas...")
    data = read_xlsx_data(
        f"{xls_dir}/export_karakas_en.xlsx",
        header_row=5, data_start_row=6,
        columns=['id', 'internal_id', 'name_en', 'description_en']
    )
    updated = 0
    for row in data:
        cnt = update_astroprocessor_data(cur, row['id'], row['name_en'], row['description_en'])
        updated += cnt
        if cnt == 0:
            print(f"  WARNING: No row found for id={row['id']}")
            total_skipped += 1
    print(f"  Updated {updated}/{len(data)} rows")
    total_updated += updated

    # 5. Arudhas (type_id=5) - header at row 5, data from row 6
    print("=" * 60)
    print("Loading Arudhas...")
    data = read_xlsx_data(
        f"{xls_dir}/export_arudhas_en.xlsx",
        header_row=5, data_start_row=6,
        columns=['id', 'internal_id', 'name_en', 'description_en']
    )
    updated = 0
    for row in data:
        cnt = update_astroprocessor_data(cur, row['id'], row['name_en'], row['description_en'])
        updated += cnt
        if cnt == 0:
            print(f"  WARNING: No row found for id={row['id']}")
            total_skipped += 1
    print(f"  Updated {updated}/{len(data)} rows")
    total_updated += updated

    # 6. Houses (type_id=6) - header at row 5, data from row 6, with append column
    print("=" * 60)
    print("Loading Houses...")
    data = read_houses_xlsx(f"{xls_dir}/export_houses_en.xlsx")
    updated = 0
    for row in data:
        description = row['description_en'] or ''
        if row['description_append']:
            description = description + '\n' + row['description_append']
        description = description if description else None
        cnt = update_astroprocessor_data(cur, row['id'], row['name_en'], description)
        updated += cnt
        if cnt == 0:
            print(f"  WARNING: No row found for id={row['id']}")
            total_skipped += 1
        elif row['description_append']:
            print(f"  id={int(row['id'])}: appended extra text from column E")
    print(f"  Updated {updated}/{len(data)} rows")
    total_updated += updated

    # 7. SignPlanetConnection - header at row 5, data from row 6
    print("=" * 60)
    print("Loading SignPlanetConnection...")
    data = read_xlsx_data(
        f"{xls_dir}/export_signplanetconnection_en.xlsx",
        header_row=5, data_start_row=6,
        columns=['id', 'planet', 'sign', 'name_en', 'description_en']
    )
    updated = 0
    for row in data:
        cnt = update_connection_table(
            cur, 'astroprocessor_signplanetconnection',
            row['id'], row['name_en'], row['description_en']
        )
        updated += cnt
        if cnt == 0:
            print(f"  WARNING: No row found for id={row['id']}")
            total_skipped += 1
    print(f"  Updated {updated}/{len(data)} rows")
    total_updated += updated

    # 8. PlanetHouseConnection - header at row 1, data from row 2
    print("=" * 60)
    print("Loading PlanetHouseConnection...")
    data = read_xlsx_data(
        f"{xls_dir}/export_planethouseconnection_en.xlsx",
        header_row=1, data_start_row=2,
        columns=['id', 'planet', 'house', 'name_en', 'description_en']
    )
    updated = 0
    for row in data:
        # name_en is None for all rows in this file, only update description
        name = row['name_en'] if row['name_en'] is not None else None
        cnt = update_connection_table(
            cur, 'astroprocessor_planethouseconnection',
            row['id'], name, row['description_en']
        )
        updated += cnt
        if cnt == 0:
            print(f"  WARNING: No row found for id={row['id']}")
            total_skipped += 1
    print(f"  Updated {updated}/{len(data)} rows")
    total_updated += updated

    # 9. MasterHouseConnection - header at row 5, data from row 6
    print("=" * 60)
    print("Loading MasterHouseConnection...")
    data = read_xlsx_data(
        f"{xls_dir}/export_masterhouseconnection_en.xlsx",
        header_row=5, data_start_row=6,
        columns=['id', 'master_house', 'at_house', 'name_en', 'description_en']
    )
    updated = 0
    for row in data:
        cnt = update_connection_table(
            cur, 'astroprocessor_masterhouseconnection',
            row['id'], row['name_en'], row['description_en']
        )
        updated += cnt
        if cnt == 0:
            print(f"  WARNING: No row found for id={row['id']}")
            total_skipped += 1
    print(f"  Updated {updated}/{len(data)} rows")
    total_updated += updated

    # Summary
    print("=" * 60)
    print(f"TOTAL: Updated {total_updated} rows, Skipped {total_skipped}")

    if total_skipped > 0:
        print("\nWARNING: Some rows were not found in the database!")
        response = input("Commit changes? [y/N]: ").strip().lower()
        if response != 'y':
            conn.rollback()
            print("ROLLED BACK")
            sys.exit(1)

    conn.commit()
    print("COMMITTED successfully!")

    # Verify a few records
    print("\n--- Verification ---")
    cur.execute("SELECT id, name->'en', substring((description->'en')::text, 1, 80) FROM astroprocessor_astroprocessordata WHERE type_id=1 LIMIT 3")
    print("Zodiac Signs (en):")
    for r in cur.fetchall():
        print(f"  id={r[0]}: name={r[1]}, desc={r[2]}")

    cur.execute("SELECT id, name->'en', substring((description->'en')::text, 1, 80) FROM astroprocessor_signplanetconnection LIMIT 3")
    print("SignPlanetConnection (en):")
    for r in cur.fetchall():
        print(f"  id={r[0]}: name={r[1]}, desc={r[2]}")

    cur.execute("SELECT id, name->'en', substring((description->'en')::text, 1, 80) FROM astroprocessor_masterhouseconnection LIMIT 3")
    print("MasterHouseConnection (en):")
    for r in cur.fetchall():
        print(f"  id={r[0]}: name={r[1]}, desc={r[2]}")

    conn.close()


if __name__ == '__main__':
    main()
