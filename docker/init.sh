#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$DB_NAME" <<EOF
DO \$\$ BEGIN
  CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
EXCEPTION WHEN duplicate_object THEN NULL;
END \$\$;

GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;

CREATE TABLE conversations (
            id SERIAL PRIMARY KEY,
            phone_number VARCHAR(20) NOT NULL,
            role VARCHAR(10) NOT NULL CHECK (role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

CREATE INDEX idx_conversations_phone_created ON conversations (phone_number, created_at);

CREATE TABLE reservations (
        id SERIAL PRIMARY KEY,
        phone_number VARCHAR(20) NOT NULL,
        space_type VARCHAR(20) NOT NULL CHECK (space_type IN
        ('hot_desk','private_office', 'meeting_room')),
        start_time TIMESTAMPTZ NOT NULL,
        end_time TIMESTAMPTZ NOT NULL CHECK (end_time > start_time),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

CREATE TABLE reminders (
        id SERIAL PRIMARY KEY,
        reservation_id INTEGER REFERENCES reservations (id) ON DELETE CASCADE,
        reminder_type VARCHAR(20) NOT NULL CHECK(reminder_type IN ('24h', '1h')),
        sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

ALTER TABLE reminders ADD CONSTRAINT reminder_unique UNIQUE(reservation_id, reminder_type);


GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $DB_USER;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $DB_USER;

EOF

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" -tc "SELECT 1 FROM pg_database WHERE datname = '$AIRFLOW_DB_NAME'" | grep -q 1 || psql --username "$POSTGRES_USER" -c "CREATE DATABASE $AIRFLOW_DB_NAME"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<EOF
DO \$\$ BEGIN
  CREATE USER $AIRFLOW_DB_USER WITH PASSWORD '$AIRFLOW_DB_PASSWORD';
EXCEPTION WHEN duplicate_object THEN NULL;
END \$\$;

GRANT ALL PRIVILEGES ON DATABASE $AIRFLOW_DB_NAME TO $AIRFLOW_DB_USER;

EOF

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$AIRFLOW_DB_NAME" <<EOF
GRANT ALL ON SCHEMA public TO $AIRFLOW_DB_USER;

EOF

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$DB_NAME" -tc "SELECT 1 FROM pg_namespace WHERE nspname = '$STAGING_DB_NAME'" | grep -q 1 || psql --username "$POSTGRES_USER" --dbname "$DB_NAME" -c "CREATE SCHEMA $STAGING_DB_NAME"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$DB_NAME" -tc "SELECT 1 FROM pg_namespace WHERE nspname = '$MARTS_DB_NAME'" | grep -q 1 || psql --username "$POSTGRES_USER" --dbname "$DB_NAME" -c "CREATE SCHEMA $MARTS_DB_NAME"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$DB_NAME"<<EOF
DO \$\$ BEGIN
  CREATE USER $DBT_DB_USER WITH PASSWORD '$DBT_DB_PASSWORD';
EXCEPTION WHEN duplicate_object THEN NULL;
END \$\$;

GRANT USAGE ON SCHEMA public TO $DBT_DB_USER;
GRANT SELECT ON reservations, reminders TO $DBT_DB_USER;
GRANT CREATE, USAGE ON SCHEMA $STAGING_DB_NAME TO $DBT_DB_USER;
GRANT CREATE, USAGE ON SCHEMA $MARTS_DB_NAME TO $DBT_DB_USER;
GRANT CONNECT ON DATABASE $DB_NAME TO $DBT_DB_USER;
GRANT CREATE ON DATABASE $DB_NAME TO $DBT_DB_USER;
EOF

