# Safe migration: convert VARCHAR UUID columns to Postgres UUID

This repository includes an additive Alembic revision that converts
previously-created `character varying` columns (used to store UUID
strings) into proper Postgres `uuid` typed columns.

File created: `backend/alembic/versions/c4d2e6f0a9b1_convert_varchar_to_uuid_event_fks.py`

What this migration does
- Enables the Postgres extension `uuid-ossp` (used for UUID helpers).
- Validates that existing values in the affected columns are valid UUID strings.
- Drops foreign key constraints that would block the type change.
- Alters the following columns to `uuid` using a safe `USING col::uuid` cast:
  - `event.id`, `event.owner_id`
  - `event_participant.id`, `event_participant.event_id`, `event_participant.user_id`
- Recreates foreign keys with `ON DELETE CASCADE`.

Safety notes (read before running)
- ALWAYS run this on a recent backup or a staging copy first.
- The migration will abort if any value in the validated columns is not a valid
  UUID string — this prevents silent corruption.
- If your production DB already has FK constraint names you rely on, update
  the migration to recreate those exact names.

How to run (recommended)
1. Take a logical backup (pg_dump) or snapshot of your database.

   PowerShell example:
   ```powershell
   pg_dump -h <host> -p <port> -U <user> -Fc -f backup_pre_uuid_migration.dump <database>
   ```

2. If you don't have a staging environment, create one and restore the dump
   there to test the migration end-to-end.

3. From the backend runtime environment where Alembic is configured, run:

   ```powershell
   alembic upgrade head
   ```

   - The migration will create the `uuid-ossp` extension if missing.
   - It will validate UUID formats and fail early if any invalid strings are found.

4. Verify integrity in the target DB (row counts, sample queries, foreign keys).

Rollback / Downgrade
- The revision implements a downgrade that casts the UUID columns back to
  `varchar(36)` and recreates FK constraints (also with `ON DELETE CASCADE`).
  Use `alembic downgrade -1` to step back, but only after ensuring no application
  code has inserted UUID values that would be incompatible with the expected text
  format.

Notes / customization
- If you prefer the `pgcrypto` extension (gen_random_uuid) instead of
  `uuid-ossp`, edit the top of the migration and replace `uuid-ossp` with
  `pgcrypto`.
- The migration recreates FKs with `ON DELETE CASCADE`. If you need different
  cascade behavior or specific constraint names, update the SQL in the
  migration file accordingly before running.

Questions or help
- If you'd like I can:
  - Update the migration to preserve specific constraint names.
  - Add tests or a dry-run script that scans the DB for invalid UUID values
    before running Alembic.
