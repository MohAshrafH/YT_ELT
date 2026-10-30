#!/bin/bash
# Adapted from MattTheDataEngineer/YT_ELT for this project's first initialization.
# Run by the official PostgreSQL image inside Linux, not by PowerShell.
set -e
set -u

# Check every input before creating anything; empty values are errors too.
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${METADATA_DATABASE_NAME:?METADATA_DATABASE_NAME is required}"
: "${METADATA_DATABASE_USERNAME:?METADATA_DATABASE_USERNAME is required}"
: "${METADATA_DATABASE_PASSWORD:?METADATA_DATABASE_PASSWORD is required}"
: "${CELERY_BACKEND_NAME:?CELERY_BACKEND_NAME is required}"
: "${CELERY_BACKEND_USERNAME:?CELERY_BACKEND_USERNAME is required}"
: "${CELERY_BACKEND_PASSWORD:?CELERY_BACKEND_PASSWORD is required}"
: "${ELT_DATABASE_NAME:?ELT_DATABASE_NAME is required}"
: "${ELT_DATABASE_USERNAME:?ELT_DATABASE_USERNAME is required}"
: "${ELT_DATABASE_PASSWORD:?ELT_DATABASE_PASSWORD is required}"

function create_user_and_database() {
    local database="$1"
    local username="$2"
    local password="$3"
    echo "Creating user '$username' and database '$database'"

    # psql quotes identifiers (:"name") and string values (:'name') safely.
    # Ownership lets each application create its own schemas/tables.
    psql --no-psqlrc -v ON_ERROR_STOP=1 \
        --username "$POSTGRES_USER" --dbname "${POSTGRES_DB:-postgres}" \
        --set=db_name="$database" --set=db_user="$username" \
        --set=db_password="$password" <<'EOSQL'
CREATE USER :"db_user" WITH PASSWORD :'db_password';
CREATE DATABASE :"db_name" OWNER :"db_user";
EOSQL
    echo "  User '$username' and database '$database' created successfully"
}

# Three logical databases in one PostgreSQL server/container.
create_user_and_database "$METADATA_DATABASE_NAME" "$METADATA_DATABASE_USERNAME" "$METADATA_DATABASE_PASSWORD"
create_user_and_database "$CELERY_BACKEND_NAME" "$CELERY_BACKEND_USERNAME" "$CELERY_BACKEND_PASSWORD"
create_user_and_database "$ELT_DATABASE_NAME" "$ELT_DATABASE_USERNAME" "$ELT_DATABASE_PASSWORD"

echo "All databases and users created successfully"
