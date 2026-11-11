# PostgreSQL commands and interactions

This guide collects the project's PostgreSQL connection, inspection, and troubleshooting commands in the order you normally use them. Run container commands in **Windows PowerShell** and database commands inside **psql**. The example outputs below are from your supplied session; they are snapshots, not live checks.

| Setting | Project value |
|---|---|
| Compose service | `postgres` |
| Confirmed container name | `yt-elt-postgres-1` |
| PostgreSQL image | `docker.io/library/postgres:13` |
| ELT database | `elt_db` |
| ELT role | `yt_api_user` |
| Bootstrap administrator | `postgres` |
| Windows connection | `localhost:5433` |
| Container network connection | `postgres:5432` |

## 1. Open the project directory

```powershell
Set-Location "F:\Data Engineering\Training\Data Engineering Automation\Data Engineering Project SQL, Python, Airflow, Docker, CICD - Udemy\Project Directory\YT_ELT"
```

Activating the Windows Python virtual environment is not required for these commands.

## 2. Check or start PostgreSQL

```powershell
# Check the service and actual container name.
docker compose ps postgres

# Include stopped containers when diagnosing a missing service.
docker compose ps -a postgres

# Run only if PostgreSQL needs starting.
docker compose up -d postgres

# Inspect recent PostgreSQL logs if startup or connection fails.
docker compose logs --tail 100 postgres
```

Your confirmed running container is `yt-elt-postgres-1`, with `127.0.0.1:5433->5432/tcp` published for Windows clients.

## 3. Connect to the ELT database

Use the Compose service name from the project directory:

```powershell
docker compose exec postgres psql -U yt_api_user -d elt_db
```

Alternatively, use the actual container name:

```powershell
docker exec -it yt-elt-postgres-1 psql -U yt_api_user -d elt_db
```

Choose one connection command. `-U` selects the PostgreSQL role; `-d` selects the database. For `docker exec`, `-i` keeps input open and `-t` allocates an interactive terminal. Compose `exec` provides an interactive terminal by default.

`docker exec -it postgres ...` fails because `postgres` is the service name, while this container is named `yt-elt-postgres-1`. `docker compose exec postgres ...` resolves the service to its container. Recheck `docker compose ps postgres` if the generated name changes.

After connecting, the prompt is `elt_db=>`. Enter the following commands there, without typing the prompt itself. SQL statements need a final `;`; psql backslash commands do not.

## 4. List PostgreSQL roles: `\du`

```text
elt_db=> \du
                                      List of roles
     Role name     |                         Attributes                         | Member of
-------------------+------------------------------------------------------------+-----------
 airflow_meta_user |                                                            | {}
 celery_user       |                                                            | {}
 postgres          | Superuser, Create role, Create DB, Replication, Bypass RLS | {}
 yt_api_user       |                                                            | {}
```

Roles are PostgreSQL identities. The `postgres` role is the administrator; the other roles belong to the Airflow metadata, Celery results, and ELT databases. `{}` indicates no role memberships in this output.

## 5. List databases and owners: `\l`

```text
elt_db=> \l
                                         List of databases
        Name         |       Owner       | Encoding |  Collate   |   Ctype    |   Access privileges
---------------------+-------------------+----------+------------+------------+-----------------------
 airflow_metadata_db | airflow_meta_user | UTF8     | en_US.utf8 | en_US.utf8 |
 celery_results_db   | celery_user       | UTF8     | en_US.utf8 | en_US.utf8 |
 elt_db              | yt_api_user       | UTF8     | en_US.utf8 | en_US.utf8 |
 postgres            | postgres          | UTF8     | en_US.utf8 | en_US.utf8 |
 template0           | postgres          | UTF8     | en_US.utf8 | en_US.utf8 | =c/postgres          +
                     |                   |          |            |            | postgres=CTc/postgres
 template1           | postgres          | UTF8     | en_US.utf8 | en_US.utf8 | =c/postgres          +
                     |                   |          |            |            | postgres=CTc/postgres
(6 rows)
```

`elt_db` is owned by `yt_api_user`. `template0` and `template1` are PostgreSQL template databases. Listing databases does not change the database you are connected to.

## 6. List schemas in the current database: `\dn`

```text
elt_db=> \dn
    List of schemas
  Name   |    Owner
---------+-------------
 core    | yt_api_user
 public  | postgres
 staging | yt_api_user
(3 rows)
```

Schemas group objects within a database. Your ELT database contains the `staging` and `core` schemas, both owned by `yt_api_user`.

## 7. List tables and inspect their structure

List the tables in `core`:

```text
elt_db=> \dt core.*
           List of relations
 Schema |  Name  | Type  |    Owner
--------+--------+-------+-------------
 core   | yt_api | table | yt_api_user
(1 row)
```

Other useful inspection commands, entered inside psql:

```sql
-- List staging tables.
\dt staging.*

-- List tables across all schemas, including system schemas.
\dt *.*

-- Inspect columns, types, and constraints on the core table.
\d core.yt_api
```

## 8. Query the ELT data

```sql
-- Read the core table shown in the course screenshot.
SELECT * FROM core.yt_api;

-- Preview a smaller number of rows.
SELECT * FROM core.yt_api LIMIT 10;

-- Confirm the connected role and database.
SELECT current_user, current_database();
```

If `core.yt_api` does not exist, inspect the schemas and tables above, then check the ELT pipeline. Connecting to PostgreSQL alone does not create application tables or load data. If output opens in a pager showing `(END)`, press `q` to return to the psql prompt.

## 9. Exit psql

```text
elt_db=> \q
```

This returns to PowerShell and leaves PostgreSQL running.

## 10. Run database checks directly from PowerShell

The `-c` option executes a command and exits, so these commands do not open an interactive psql session.

List non-template databases and their owners using the bootstrap administrator:

```powershell
docker compose exec postgres psql -U postgres -d postgres -c 'SELECT datname, pg_get_userbyid(datdba) AS owner FROM pg_database WHERE datistemplate = false;'
```

The expected project databases are `postgres`, `airflow_metadata_db`, `celery_results_db`, and `elt_db`.

Check a password login over the container network and enter `ELT_DATABASE_PASSWORD` from your local `.env` at the hidden prompt:

```powershell
docker compose exec postgres psql -h postgres -U yt_api_user -d elt_db -W -c 'SELECT current_user, current_database();'
```

`-h postgres` selects the service's network address; `-W` forces a password prompt. A prompt by itself does not prove password validation: socket and container-loopback connections in this image may use trust authentication. Repeat the network check with the metadata or Celery role and database when needed.

For Windows clients such as DBeaver, use host `localhost`, port `5433`, database `elt_db`, role `yt_api_user`, and the matching local password.

## 11. Equivalent commands for the Podman setup

Use these alternatives when the project containers are managed through Podman. Run them in PowerShell from the project directory.

```powershell
podman compose -p yt-elt -f docker-compose.yaml ps postgres
podman compose -p yt-elt -f docker-compose.yaml ps -a postgres
# Only if PostgreSQL needs starting:
podman compose -p yt-elt -f docker-compose.yaml up -d postgres
podman compose -p yt-elt -f docker-compose.yaml logs --tail 100 postgres

# Interactive connection using the service name:
podman compose -p yt-elt -f docker-compose.yaml exec postgres psql -U yt_api_user -d elt_db
# Alternative using the container name:
podman exec -it yt-elt-postgres-1 psql -U yt_api_user -d elt_db

# Non-template database owners:
podman compose -p yt-elt -f docker-compose.yaml exec postgres psql -U postgres -d postgres -c 'SELECT datname, pg_get_userbyid(datdba) AS owner FROM pg_database WHERE datistemplate = false;'

# Network password login:
podman compose -p yt-elt -f docker-compose.yaml exec postgres psql -h postgres -U yt_api_user -d elt_db -W -c 'SELECT current_user, current_database();'
```

The commands inside psql (`\du`, `\l`, `\dn`, `\dt`, SQL queries, and `\q`) are the same with either engine.

## 12. Deliberately change an existing role password

Changing `.env` does not update a role password already stored in PostgreSQL. Only when you intend to change a password, connect as the administrator:

```powershell
docker compose exec postgres psql -U postgres -d postgres
```

Then use the interactive command, which prompts for the new password:

```text
\password yt_api_user
\q
```

For Podman, use the same administrator connection with `podman compose -p yt-elt -f docker-compose.yaml exec postgres psql -U postgres -d postgres`. After changing the password, update the matching local `.env` setting and recreate the affected consumers so they use it. See the [initialization script explanation](Postgres_Initialization_Script_Explained.md) for how initial roles and databases are created.

For full-stack lifecycle and volume commands, see the [Docker and Podman command guide](Docker_and_Podman_Commands_Guide.md).
