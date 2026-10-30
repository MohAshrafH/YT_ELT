# The .env lecture, applied to your YT_ELT project

This guide uses the supplied instructor transcript, the downloaded course Compose and PostgreSQL initialization files, your working YT_ELT project, and the older projects under `C:\Astro\Airflow`. It follows **Airflow 2.9.2**, the version selected by this project's Dockerfile. Inspection and preparation date: **2026-10-28**.

## 1. What .env means here

`.env` is a plain text configuration file containing `NAME=value` settings. It gives the application and its deployment configuration a place to read values that may differ between computers or environments. Some values are secret, such as passwords; others are ordinary settings, such as a channel handle or image tag. The file itself is not encrypted.

It is different from `venv/`: **`.env` stores configuration; `venv/` stores a Python interpreter environment and installed packages.**

For example, `CHANNEL_HANDLE=MrBeast` means “when the code asks for CHANNEL_HANDLE, use MrBeast.” A line beginning with `#` is a comment; a blank line separates groups. Quotes can surround a value but are normally removed by the reader. Use the actual filename `.env`, without `.txt`, and omit the numbered list and Markdown escapes from the course slide.

In this project the file has two readers:

1. The existing Python scripts call `load_dotenv(dotenv_path="./.env")`, then use `os.getenv(...)`. Run them from the YT_ELT root because that path is relative to the terminal's current directory. Existing process environment variables take precedence under the scripts' default `load_dotenv` behavior.
2. At the next lecture, Compose substitutes values such as `${METADATA_DATABASE_NAME}` into its service definitions. Compose then explicitly passes the needed values into each container through its `environment` entries.

Merely putting a value in `.env` does **not** automatically set it globally in Windows, create a database, configure every container, or start Airflow. Compose's substitution and the environment inside a container are related but separate steps. [Docker's explanation of .env and interpolation](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/).

## 2. Why databases are involved

Airflow needs durable operational memory. If a worker or scheduler restarts, Airflow must still know which workflows were scheduled, which task instances succeeded or failed, and which work remains. That is the metadata database's job.

The course also needs somewhere to store extracted YouTube records for SQL transformations, updates, and data-quality checks. JSON files are useful extraction outputs, but a relational database provides tables, SQL queries and joins, constraints, and transactions for the ELT stages.

The course uses Celery workers as its execution model. Its Celery result backend stores execution status/result records for that mechanism. This is separate from both the YouTube business data and the metadata tables Airflow uses to orchestrate workflows. It is also separate from Redis, which carries queued execution messages. Do not treat the result backend as a store of all task logs or all business return values; Airflow also has its own metadata and XCom mechanisms.

The resulting arrangement is:

```text
One PostgreSQL service/container: postgres:5432
├── airflow_metadata_db  — Airflow's operational records
├── celery_results_db    — Celery execution result/status records
└── elt_db               — your extracted/loaded YouTube data

Redis service             — queued messages between Celery components
```

These are three logical databases on **one PostgreSQL server**, not a requirement to install three database servers. Within a database, schemas organize tables. Giving each database a separate application user keeps their access distinct.

PostgreSQL is an open-source relational database server with support in Airflow, Celery's SQL result backend, and the course's database tools. Reusing it reduces the number of technologies needed here. It is not the only possible choice: Airflow 2.9.2 also supports MySQL as a metadata backend, while SQLite is limited to development and the SequentialExecutor. Following PostgreSQL here matches the course's SQL, drivers, and initialization script. [Airflow 2.9.2 database backend documentation](https://airflow.apache.org/docs/apache-airflow/2.9.2/howto/set-up-database.html).

## 3. Every setting in the instructor's file

Variable names are an interface between files. Keep the course's names unless you also update every consumer. Most of these are **course-defined names**, not settings automatically recognized by PostgreSQL or Airflow.

| Setting | Meaning and consumer | Your configuration |
|---|---|---|
| `DOCKERHUB_NAMESPACE` | Docker Hub user or organization that owns the image repository. Compose uses it to assemble the image reference. It is not a login password. | `mohammadashraf97` |
| `DOCKERHUB_REPOSITORY` | Image repository within that namespace. | `yt_api_elt` |
| `IMAGE_TAG` | Image version label; independent of the Airflow version. Has an effect only when the consuming Compose file references it. | `1.0.0` |
| `POSTGRES_CONN_USERNAME` | Server bootstrap/admin role, mapped by course Compose to the PostgreSQL image's `POSTGRES_USER`. Used by the initialization script to create application users/databases. | `postgres` |
| `POSTGRES_CONN_PASSWORD` | Password for that bootstrap role, mapped to `POSTGRES_PASSWORD`. Not the Airflow browser password. | Generated locally |
| `POSTGRES_CONN_HOST` | Network address used by containers to reach PostgreSQL. | `postgres`, matching the future Compose service name |
| `POSTGRES_CONN_PORT` | Port PostgreSQL listens on inside that container network. | `5432` |
| `METADATA_DATABASE_NAME` | Name of the database holding Airflow's operational state. | `airflow_metadata_db` |
| `METADATA_DATABASE_USERNAME` | Database role that Airflow uses for metadata access. | `airflow_meta_user` |
| `METADATA_DATABASE_PASSWORD` | Password for that role. Compose includes it in Airflow's metadata connection URL. | Generated locally |
| `CELERY_BACKEND_NAME` | Name of the database selected as Celery's SQL result backend. | `celery_results_db` |
| `CELERY_BACKEND_USERNAME` | Role used to access the Celery results database. | `celery_user` |
| `CELERY_BACKEND_PASSWORD` | Password for that role, used in the result backend URL. | Generated locally |
| `ELT_DATABASE_NAME` | Destination database for YouTube data; the workflow later creates/uses its schemas and tables. | `elt_db` |
| `ELT_DATABASE_USERNAME` | Application role used by loading/transformation tasks and database tests. | `yt_api_user` |
| `ELT_DATABASE_PASSWORD` | Password for that role. Compose builds an Airflow Connection from it. | Generated locally |
| `AIRFLOW_UID` | Numeric Linux user ID for ordinary Airflow containers. Compose applies it through `user: "${AIRFLOW_UID}:0"`; the second number is the group ID. | `50000`; not your Windows login or Airflow website username |
| `AIRFLOW_WWW_USER_USERNAME` | Initial Airflow 2 browser admin account name. The course maps it to the image entrypoint's `_AIRFLOW_WWW_USER_USERNAME`. | `airflow` |
| `AIRFLOW_WWW_USER_PASSWORD` | Initial browser admin password; unrelated to database roles. | Generated locally; read it from your local `.env` when login is needed |
| `FERNET_KEY` | Symmetric encryption key Airflow uses for sensitive Connection/Variable fields stored in its metadata database. Course Compose maps it to `AIRFLOW__CORE__FERNET_KEY`. | Generated locally and kept stable |
| `API_KEY` | Your Google/YouTube Data API credential. Existing scripts read it directly; course Compose later maps it to `AIRFLOW_VAR_API_KEY`. | Your pre-existing value preserved exactly |
| `CHANNEL_HANDLE` | Channel to query, not an authentication credential. Existing scripts now read it from `.env`; course Compose later maps it to `AIRFLOW_VAR_CHANNEL_HANDLE`. | `MrBeast`, change if you want a different channel |

The bootstrap role does not eliminate database creation: the course's script still creates all three named databases and their users. Keeping `POSTGRES_CONN_USERNAME=postgres` follows that script and the image defaults; it does not make the other names automatic.

For the network address, **inside an Airflow container**, `localhost` means that Airflow container. `postgres` means the PostgreSQL service on the shared Compose network. From a Windows database client, you would normally use `localhost` and the port published on Windows. If later we map `5433:5432` to avoid a conflict, Windows clients use `5433`, but the Airflow-to-PostgreSQL settings remain `postgres:5432`.

## 4. How the settings reach Airflow

The downloaded course Compose file explicitly performs these mappings:

```text
METADATA_DATABASE_* + POSTGRES_CONN_HOST/PORT
  → AIRFLOW__DATABASE__SQL_ALCHEMY_CONN
  → Airflow metadata database connection

CELERY_BACKEND_* + POSTGRES_CONN_HOST/PORT
  → AIRFLOW__CELERY__RESULT_BACKEND
  → Celery SQL result backend

ELT_DATABASE_* + POSTGRES_CONN_HOST/PORT
  → AIRFLOW_CONN_POSTGRES_DB_YT_ELT
  → Connection ID postgres_db_yt_elt used by DAG database tasks

API_KEY        → AIRFLOW_VAR_API_KEY        → Variable.get("api_key")
CHANNEL_HANDLE → AIRFLOW_VAR_CHANNEL_HANDLE → Variable.get("channel_handle")
```

The double underscores in `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN` delimit an Airflow configuration section and option. The single underscore conventions in `AIRFLOW_CONN_...` and `AIRFLOW_VAR_...` define Connections and Variables. The shorter course names are inputs to those settings.

An illustrative connection URL, with a placeholder password, is:

```text
postgresql+psycopg2://airflow_meta_user:PASSWORD@postgres:5432/airflow_metadata_db
```

Read it as database engine/driver, login/password, server/port, then database name. Do not print a resolved real connection URL when sharing diagnostics because it contains credentials.

## 5. What your older Airflow directories contribute

I inspected the main project at `C:\Astro\Airflow\learning-airflow` and its nested `learning-airflow` project. Both Dockerfiles select `astrocrpublic.azurecr.io/runtime:3.1-9`; `.astro/config.yaml` identifies `learning-airflow` as the project name. The nested project is largely the starter scaffold; the outer project contains your practice DAGs and provider requirements.

The outer project's `.env` has only:

- `AIRFLOW_CONN_SNOWFLAKE`: a connection definition, whose value was not displayed or copied. The associated example DAG describes the Snowflake setup as educational/placeholders rather than a verified real account.
- `AIRFLOW_VAR_MY_VAR`: a JSON-valued Airflow Variable used for practice. It is not a YouTube API key.

Its `airflow_settings.yaml` also declares a filesystem connection, `fs_default`. That file is another configuration channel supplied by Astro. Its generated README documents local PostgreSQL and Airflow service startup through Astro, although those boilerplate version/UI details should not be assumed to describe the current Runtime exactly.

This explains the small `.env`: **a short file can sit on top of extensive generated/default configuration**. The earlier setup already used a metadata database; you did not have to list all its bootstrap settings yourself. The current course spells out a custom Compose stack and adds separate ELT and Celery databases. The inspected project files do not explicitly configure a Celery backend; I did not verify the old runtime's effective executor because the engine is stopped.

Useful material to reuse is the concept of `AIRFLOW_CONN_...`, `AIRFLOW_VAR_...`, TaskFlow dependencies, and your existing Podman/WSL infrastructure. Do not copy Snowflake credentials, unrelated AWS/Snowflake provider pins, or whole runtime configuration into this course. Several old DAGs import `airflow.sdk`, an Airflow 3 interface; this project is pinned to Airflow 2.9.2, so those imports need adaptation before reuse. The course's Airflow 2 examples use imports such as `from airflow.models import Variable`.

## 6. What was already present and what was prepared

Before this step:

- YT_ELT had a root `.env` containing only `API_KEY`.
- Three standalone extraction scripts already read that key using `python-dotenv`, but hardcoded `MrBeast`.
- Dockerfile selected Airflow 2.9.2 and Python 3.10. The image requirements list contained comments only.
- The Airflow project folders existed, but there was no working-root Compose file or PostgreSQL initialization script.
- `.gitignore` ignored `.env`, and `.dockerignore` excluded it from image build input. Git did not track `.env`.
- Podman and Astro CLIs were installed. The WSL-backed Podman machine `astro-machine` existed but was **stopped**. Saved image/container/database existence could not be verified without starting it.

Prepared for this lesson:

- Expanded `.env` to the 22 settings above with your confirmed Docker Hub repository.
- Preserved the exact existing API key line. Its presence is confirmed, but no API call was made to validate its authorization or quota.
- Generated independent 24-character alphanumeric passwords for the PostgreSQL bootstrap role, three database users, and Airflow browser login.
- Generated a local Fernet key from 32 cryptographically random bytes, encoded as URL-safe Base64; no key generation website or additional Python dependency was needed. This matches the [Fernet key format](https://cryptography.io/en/latest/fernet/).
- Added `.env.example` with placeholders instead of real secrets, as a shareable record of required variable names.
- Changed only the channel setting in each extraction script to `os.getenv("CHANNEL_HANDLE", "MrBeast")`.

The instructor's published API key is not yours to use; the transcript explicitly says it will be disabled. You do not need a new key solely because this lesson adds configuration if your existing one still works. The database and UI passwords are values you choose for accounts created locally later; they are not credentials you need to obtain from a website. Docker Hub credentials remain a separate `podman login` concern.

## 7. Remaining work belongs to the Compose lesson

Writing `.env` completes configuration preparation, not deployment. Next we must adapt the course Compose file, bring in the PostgreSQL initialization script with Linux line endings, confirm the image/dependencies and volume mounts, then initialize and start the services. No separate native Windows PostgreSQL install is needed for that container approach.

The downloaded reference has a concrete inconsistency: its shared Airflow image line ends in `:latest`, ignoring `IMAGE_TAG`. When we introduce Compose, use a reference such as:

```yaml
image: docker.io/${DOCKERHUB_NAMESPACE}/${DOCKERHUB_REPOSITORY}:${IMAGE_TAG}
```

That would select `docker.io/mohammadashraf97/yt_api_elt:1.0.0`; the existence of that tag has not been verified here. A locally built image is also an option if chosen consistently with our earlier Podman guide.

The PostgreSQL image and mounted initialization script create the database roles/databases on first initialization of an empty data directory. Airflow initialization then creates/migrates its metadata tables and creates the initial UI user. The workflow later creates/loads the ELT tables. These are separate steps. Editing `.env` after a database volume already exists does not automatically change stored database passwords; use a deliberate password change instead. Similarly, changing an initial UI credential setting is not a general reset command for an existing user.

Keep the Fernet key stable after encrypted metadata exists; replacing it outright can make that data unreadable. Fernet encrypts selected database fields, **not** your `.env` file, all metadata, or environment-supplied values that never enter the database. [Airflow's Fernet explanation and rotation procedure](https://airflow.apache.org/docs/apache-airflow/2.2.2/security/secrets/fernet.html).

The transcript's caution about password punctuation is a course integration issue, not a PostgreSQL prohibition. `$` can trigger Compose substitution; `@`, `:`, and `/` need care inside URLs; the supplied shell/SQL initialization script also interpolates passwords directly. The generated long alphanumeric passwords avoid these particular integration problems. PostgreSQL itself supports more than alphanumeric passwords.

During the next lesson, verify available memory and host ports before starting the full stack. The stopped machine's configuration reports 2 GiB, while Airflow's 2.9.2 Compose guide calls for at least 4 GB and ideally 8 GB; the effective memory available inside this WSL-backed engine still needs to be checked. Reusing the same engine does not require reusing the old Astro databases or service names. [Airflow 2.9.2 Compose requirements and initialization](https://airflow.apache.org/docs/apache-airflow/2.9.2/howto/docker-compose/index.html).

## 8. Verification scope

The local checks for this step parse `.env` with your existing `python-dotenv`, compare its variable set to `.env.example`, check nonempty entries and duplicate names, validate the Fernet key encoding and password format, confirm `.env` remains ignored/untracked, and parse the Python scripts without running their extraction code. The channel setting can be evaluated in isolation to verify it respects the environment without making YouTube requests.

There is no running-service, database-login, Docker Hub tag, or YouTube API validation in this preparation step. Those checks require the relevant service/API and should be done at their course stage.
