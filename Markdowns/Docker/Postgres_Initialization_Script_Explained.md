# PostgreSQL initialization: three databases from one script

The script at [`docker/postgres/init-multiple-databases.sh`](../../docker/postgres/init-multiple-databases.sh) prepares the course's database destinations. It creates **three application roles and three databases inside one PostgreSQL container**. It does not start Airflow, create a DAG, or load YouTube records.

Based on your supplied transcript and the [instructor's script](https://github.com/MattTheDataEngineer/YT_ELT/blob/main/docker/postgres/init-multiple-databases.sh). Our version keeps the same function and three calls, with input validation and safer SQL quoting. See the [Compose guide](Docker_Compose_Lecture_Explained.md) for how it is mounted.

## 1. What it creates in your project

| Database | Application user | What eventually goes there |
|---|---|---|
| `airflow_metadata_db` | `airflow_meta_user` | Airflow's DAG runs, task states, users, and other operational tables. |
| `celery_results_db` | `celery_user` | Celery execution result/status records. |
| `elt_db` | `yt_api_user` | Loaded and transformed YouTube data. |

Names come from `.env`; passwords also come from there and are not written in this guide. The bootstrap role is `postgres`, configured through `POSTGRES_USER` by Compose. It has permission to create the other roles/databases.

Three logical databases are lighter than running three separate servers. They share CPU, memory, storage, and failure lifecycle. Separate application users are useful access organization, but this script is not a complete security-isolation policy: PostgreSQL's default public connection permissions are not revoked here.

## 2. Who runs the script, and when?

```text
Windows file: YT_ELT/docker/postgres/init-multiple-databases.sh
                         | read-only bind mount
PostgreSQL container: /docker-entrypoint-initdb.d/init-multiple-databases.sh
                         |
Official image entrypoint, when its database storage is empty
                         |
Temporary PostgreSQL server → psql → CREATE USER / CREATE DATABASE
                         |
Normal PostgreSQL server starts
```

The official image recognizes `/docker-entrypoint-initdb.d/`. A mount alone does not make an arbitrary program execute a script; this directory has meaning because the image's entrypoint explicitly processes it. It supplies a temporary database server so `psql` can execute SQL before normal startup. [Official PostgreSQL image initialization](https://hub.docker.com/_/postgres).

On later starts with the same populated named volume, this directory is **skipped**. Editing the script or changing `.env` then does not rerun user/database creation or reset passwords.

## 3. The Bash setup

```bash
#!/bin/bash
set -e
set -u
```

The shebang selects Bash when executed directly. `set -e` stops this simple script when a command fails; it is not a transaction or a universal guarantee for every Bash construct. `set -u` treats unset variable references as errors.

Our added lines such as:

```bash
: "${METADATA_DATABASE_PASSWORD:?METADATA_DATABASE_PASSWORD is required}"
```

also reject **empty** values. `:` is a no-op command; expanding the expression performs the check. All required inputs are checked before the first database is created, reducing partially completed initialization caused by a missing later setting.

These values must exist **inside the PostgreSQL container**. Compose passes them explicitly; Bash does not read the Windows `.env` file by itself.

## 4. The function and its three arguments

```bash
function create_user_and_database() {
    local database="$1"
    local username="$2"
    local password="$3"
    # psql runs the SQL here
}
```

`$1`, `$2`, and `$3` are the first, second, and third arguments. `local` limits each variable to this function. For the metadata call, their values come from:

```bash
create_user_and_database "$METADATA_DATABASE_NAME" "$METADATA_DATABASE_USERNAME" "$METADATA_DATABASE_PASSWORD"
```

The same function is called for the Celery and ELT settings. Quoting each argument keeps one value together even if it contains spaces or shell wildcard characters. There is no actual password in the source file.

## 5. How Bash sends SQL to PostgreSQL

Our function invokes:

```bash
psql --no-psqlrc -v ON_ERROR_STOP=1 \
    --username "$POSTGRES_USER" --dbname "${POSTGRES_DB:-postgres}" \
    --set=db_name="$database" --set=db_user="$username" \
    --set=db_password="$password" <<'EOSQL'
CREATE USER :"db_user" WITH PASSWORD :'db_password';
CREATE DATABASE :"db_name" OWNER :"db_user";
EOSQL
```

| Part | Purpose |
|---|---|
| `psql` | PostgreSQL's command-line SQL client, included in this container image. |
| `--no-psqlrc` | Ignore personal client startup customizations. |
| `-v ON_ERROR_STOP=1` | Make an SQL error stop the client with failure, so Bash can stop too. |
| `--username` | Connect as the bootstrap database role. |
| `--dbname` | Connect to the existing bootstrap database, normally `postgres`. |
| `--set=...` | Pass function values as psql variables. |
| `<<'EOSQL' ... EOSQL` | A here-document: feed several lines of SQL to the client. |
| `:"db_user"` | Substitute a safely quoted SQL identifier, such as a role name. |
| `:'db_password'` | Substitute a safely quoted SQL string value. |

The quoted opening delimiter prevents Bash from expanding the SQL body. psql performs its own variable substitution. The closing `EOSQL` must stand alone without spaces in front. The instructor's `<<-EOSQL` form can remove leading **tabs**, not ordinary spaces. [psql variables and quoting](https://www.postgresql.org/docs/13/app-psql.html).

`CREATE USER` creates a login role. `CREATE DATABASE ... OWNER ...` creates a database owned by that role, allowing the application to manage its schemas/tables. The instructor instead creates the database as the bootstrap role, then runs `GRANT ALL PRIVILEGES ON DATABASE ... TO ...`. Database privileges do not mean all privileges on every schema/table. Ownership makes the intended application permissions explicit and also avoids the common newer-PostgreSQL `public`-schema creation issue. [Database ownership](https://www.postgresql.org/docs/13/sql-createdatabase.html).

SQL quoting in this script does not solve connection-URL encoding elsewhere. Our existing generated alphanumeric passwords already work in the Compose URLs. If you choose punctuation later, consider both Compose `$` interpolation and URI percent-encoding.

## 6. Database initialization versus Airflow initialization

| Stage | What it creates |
|---|---|
| PostgreSQL image's own initialization | Server system catalogs and bootstrap user/database. |
| Our mounted `.sh` script | The three application users and their databases. |
| Compose `airflow-init` service | Airflow's metadata tables/migrations and initial UI admin. |
| Later DAGs/libraries | ELT business tables/data and Celery result tables when needed. |

For example, `airflow_metadata_db` can exist before it contains any Airflow tables. Airflow migrations connect to that database as `airflow_meta_user` and create the required structure. Your browser admin is an Airflow application account, separate from PostgreSQL login roles.

## 7. Windows details: LF matters; PowerShell chmod is unnecessary

This script lives in Windows but runs in Linux. It is saved as **UTF-8 without BOM, with LF line endings**. `.gitattributes` contains `*.sh text eol=lf` to preserve that after Git checkout. In VS Code, confirm **LF** in the status bar; CRLF can cause errors such as `/bin/bash^M` or `$'\r': command not found`.

Our Compose mount uses the `/home/user/yt-elt-project` Linux alias because Podman's mount parser rejected the commas in this repository's Windows path. The [command guide](Docker_and_Podman_Commands_Guide.md) explains the small PowerShell preparation helper. This changes the path used to reach the same file, not its contents or storage location.

Do not paste the escaped `\`, HTML entities such as `&#x20;`, or extra Markdown formatting from the lecture notes. The supplied project script already contains clean Bash.

On Windows, skip the lecture's `chmod +x` command. The official image executes executable `.sh` files and **sources non-executable `.sh` files**, so a non-executable mount can still work with this image. Execution permissions matter in other contexts, and Linux/macOS users can use the lecture's command where needed. This does not remove the need for valid content, readable mounts, and LF endings. [Entrypoint's script handling](https://github.com/docker-library/postgres/blob/master/docker-entrypoint.sh).

## 8. Failures, retries, and password changes

This is a first-initialization script, **not an idempotent migration**. A manual rerun against existing roles fails at `CREATE USER`. Creation is not one all-or-nothing transaction: if the second database fails, the first may remain. PostgreSQL's image can then see initialized storage on a restart and skip the directory, leaving incomplete application setup.

First inspect PostgreSQL logs and list the actual databases. Do not assume restarting fixed an earlier script failure. The [command guide](Docker_and_Podman_Commands_Guide.md) includes inspection and login checks.

Changing `.env` does not update a password stored in an existing database. For retained data, change the database role password deliberately (for example with interactive psql `\password role_name`), update the matching local setting, and recreate consumers. Initial Airflow UI settings likewise are not an existing-user password reset. Keep the Fernet key stable.

For a genuinely disposable course database, deleting this project's named volume allows clean initialization but erases **all three databases**. The command guide keeps that destructive reset separate from ordinary shutdown. Existing Astro storage must remain outside any reset.
