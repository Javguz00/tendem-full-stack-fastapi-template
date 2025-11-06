"""Pre-check script for UUID migration

Usage:
  - From the project / backend container where SQLAlchemy is available:
      python backend/scripts/precheck_uuid_migration.py
  - Optionally pass a DATABASE_URL:
      python backend/scripts/precheck_uuid_migration.py --database-url postgresql://user:pass@host:5432/db

This script connects to the database (via SQLALCHEMY_DATABASE_URI env or
--database-url) and checks the following columns for non-UUID text values:
  - event.id
  - event.owner_id
  - event_participant.id
  - event_participant.event_id
  - event_participant.user_id

It prints counts and example offending rows (up to N) to help you triage.
"""
import argparse
import os
import sys

try:
    from sqlalchemy import create_engine, text
except Exception as e:
    print("ERROR: sqlalchemy is required to run this script. Run inside the project container or install dependencies.")
    raise


DEFAULT_SAMPLE = 10


def check_column(engine, table, column, sample=DEFAULT_SAMPLE):
    q_count = text(f"SELECT COUNT(*) AS bad_count FROM {table} WHERE {column} IS NOT NULL AND {column} !~ :uuid_regex")
    q_sample = text(f"SELECT {column} FROM {table} WHERE {column} IS NOT NULL AND {column} !~ :uuid_regex LIMIT :limit")
    uuid_regex = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'

    from sqlalchemy.exc import ProgrammingError

    with engine.connect() as conn:
        try:
            r = conn.execute(q_count, {"uuid_regex": uuid_regex})
            bad_count = r.scalar() or 0
            print(f"{table}.{column}: {bad_count} non-UUID rows")
            if bad_count > 0:
                rs = conn.execute(q_sample, {"uuid_regex": uuid_regex, "limit": sample})
                rows = [row[0] for row in rs]
                print("Examples:")
                for val in rows:
                    print("  ", val)
            return bad_count
        except ProgrammingError as e:
            # Likely the table doesn't exist in the target DB (e.g. migrations
            # haven't been applied or wrong DATABASE_URL). Report and continue.
            msg = str(e)
            if 'does not exist' in msg or 'relation "' in msg:
                print(f"SKIP: Table or column not found for {table}.{column}: {msg}")
                return 0
            raise


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--database-url", dest="database_url", help="Database URL to use (overrides env)")
    p.add_argument("--sample", dest="sample", type=int, default=DEFAULT_SAMPLE, help="Sample rows to show per column")
    args = p.parse_args()

    database_url = args.database_url or os.environ.get("DATABASE_URL") or os.environ.get("SQLALCHEMY_DATABASE_URI")
    if not database_url:
        print("ERROR: No database URL provided. Set DATABASE_URL or pass --database-url")
        sys.exit(2)

    engine = create_engine(database_url)

    checks = [
        ("event", "id"),
        ("event", "owner_id"),
        ("event_participant", "id"),
        ("event_participant", "event_id"),
        ("event_participant", "user_id"),
    ]

    total_bad = 0
    for table, column in checks:
        bad = check_column(engine, table, column, sample=args.sample)
        total_bad += bad

    print("\nPre-check complete.")
    if total_bad == 0:
        print("No invalid UUID strings found. You can proceed with the migration after backing up your DB.")
        sys.exit(0)
    else:
        print(f"Found {total_bad} total offending rows. Fix them or investigate before running migration.")
        sys.exit(1)


if __name__ == '__main__':
    main()
