-- Runs once when the postgres container's data volume is first created.
-- Table creation is owned by Alembic migrations (services/memory/migrations);
-- this file only exists for bootstrap-time extensions/roles if ever needed.
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
