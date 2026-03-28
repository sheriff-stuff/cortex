"""
Database migration script.

Compares the live database schema against the expected schema defined in
api/db.py and applies ALTER TABLE statements to bring it up to date.
Preserves all existing data.

Usage:
    python migration/migrate.py [database_path]

    database_path defaults to meeting-notes.db
"""

import sqlite3
import sys
from pathlib import Path

# Add project root to path so we can import api.db
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.db import metadata


# Map SQLAlchemy types to SQLite type strings
def sa_type_to_sqlite(col):
    """Convert a SQLAlchemy column type to its SQLite type affinity."""
    type_name = type(col.type).__name__
    mapping = {
        "String": f"VARCHAR({col.type.length})" if hasattr(col.type, "length") and col.type.length else "VARCHAR",
        "Text": "TEXT",
        "Integer": "INTEGER",
        "Float": "FLOAT",
    }
    return mapping.get(type_name, "TEXT")


def get_live_columns(cursor, table_name):
    """Return {col_name: col_info} for a live table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    rows = cursor.fetchall()
    return {row[1]: {"type": row[2], "notnull": row[3], "default": row[4]} for row in rows}


def migrate(db_path: str = "meeting-notes.db"):
    """Run migration: add any missing columns to existing tables."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get existing tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = {row[0] for row in cursor.fetchall()}

    changes = []

    for table in metadata.sorted_tables:
        if table.name not in existing_tables:
            # Table doesn't exist yet — metadata.create_all() will handle it
            changes.append(f"  NEW TABLE: {table.name} (will be created on next server start)")
            continue

        live_cols = get_live_columns(cursor, table.name)
        expected_cols = {col.name: col for col in table.columns}

        # Find missing columns
        for col_name, col in expected_cols.items():
            if col_name not in live_cols:
                sqlite_type = sa_type_to_sqlite(col)
                default_clause = ""
                if col.default is not None:
                    default_val = col.default.arg
                    if isinstance(default_val, str):
                        default_clause = f" DEFAULT '{default_val}'"
                    elif isinstance(default_val, (int, float)):
                        default_clause = f" DEFAULT {default_val}"

                sql = f"ALTER TABLE {table.name} ADD COLUMN {col_name} {sqlite_type}{default_clause}"
                print(f"  ALTER: {sql}")
                cursor.execute(sql)
                changes.append(sql)

        # Report columns in DB but not in code (informational only — not dropped)
        for col_name in live_cols:
            if col_name not in expected_cols:
                note = f"  NOTE: {table.name}.{col_name} exists in DB but not in code (left as-is)"
                print(note)
                changes.append(note)

    conn.commit()
    conn.close()

    if changes:
        print(f"\nMigration complete — {len(changes)} change(s).")
    else:
        print("Schema is up to date. No changes needed.")

    return changes


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "meeting-notes.db"
    print(f"Migrating: {db_path}\n")
    migrate(db_path)
