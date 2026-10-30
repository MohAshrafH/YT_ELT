# Docker Compose: the lecture applied to YT_ELT

Compose describes **how several containers work together**: which images to run, their commands, configuration, storage, networking, and startup dependencies. Our Dockerfile builds the Airflow image; the new root [`docker-compose.yaml`](../../docker-compose.yaml) runs that image as several Airflow services alongside PostgreSQL and Redis.

This guide follows your supplied lecture, Compose attachment, and the [Airflow 2.9.2 Compose guide](https://airflow.apache.org/docs/apache-airflow/2.9.2/howto/docker-compose/index.html), using **Airflow 2.9.2 / Python 3.10**. Read this first, then the [initialization-script guide](Postgres_Initialization_Script_Explained.md) and [command guide](Docker_and_Podman_Commands_Guide.md). Prepared for your Windows/Podman environment on **2026-10-30**.

## 1. Where everything runs

```text
Windows: YT_ELT files + PowerShell + Podman CLI
                         |
              podman compose + Compose provider
                         |
WSL2 astro-machine: Podman engine
  yt-elt network:
    webserver ---- metadata database <---- scheduler
    scheduler ---- Redis task queue ----> worker
    worker ------- Celery results database
    worker ------- ELT database + mounted data files

  One postgres container hosts all three databases.
```

The executor is configured inside Airflow; it is not another service. The scheduler selects runnable tasks, Celery delivers execution messages through Redis, and the worker executes them. For example, a future DAG could run `extract videos → load elt_db → transform → check quality`. Metadata records progress; task logs go to `logs/`; extracted JSON goes to `data/`.

Your existing `astro-machine` is reusable Linux infrastructure. Its name does not require Astro CLI for this project. The older Astro project at `C:\Astro\Airflow\learning-airflow` has separate containers/storage and a different Runtime. Use ordinary Compose commands in YT_ELT; use `astro dev ...` only when working on that Astro project.

## 2. The files and vocabulary

```text
YT_ELT/
├── docker-compose.yaml       service definitions; run commands here
├── Dockerfile                Airflow image build recipe
├── requirements.txt          packages installed when rebuilding the image
├── .env                      local values/secrets, ignored by Git
├── .env.example              shareable template; placeholders are not credentials
├── .gitattributes            preserves LF for Linux shell scripts
├── docker/prepare-podman-mount.ps1  prepares this machine's mount alias
├── docker/postgres/init-multiple-databases.sh
├── dags/  data/  logs/  config/  plugins/  include/  tests/
└── Markdowns/Docker/          these explanations
```

| YAML item | How to read it |
|---|---|
| `name: yt-elt` | Group this stack's containers, network, and volume under one project. |
| `services:` | Declare runnable components, such as `postgres` and `airflow-worker`. |
| `image:` | Select the already built/published software environment. |
| `command:` | Choose the process inside that image, such as `scheduler`. |
| `environment:` | Supply settings to that container. |
| `ports:` | Publish a container port through Windows. |
| `volumes:` | Attach a host file/folder or engine-managed storage. |
| `depends_on:` | Declare startup prerequisites. |
| `healthcheck:` | Define a recurring readiness/health probe. |
| `profiles:` | Keep optional services off until explicitly enabled. |

Indentation expresses nesting; use spaces. A service is a definition; a container is a running or stopped instance. Compose is the tool, while YAML is the file format.

## 3. Shared Airflow configuration and YAML anchors

The `x-airflow-common` block collects settings repeated across Airflow services. The `x-` prefix marks an extension block, so it does not create a container.

```yaml
x-airflow-common: &airflow-common
  # shared image, environment, mounts, user, dependencies ...

services:
  airflow-scheduler:
    <<: *airflow-common
    command: scheduler
```

`&airflow-common` names a reusable YAML anchor; `*airflow-common` references it; `<<:` merges its mapping. Scheduler, worker, and webserver therefore use the same image/settings while running different processes. PostgreSQL and Redis have their own definitions.

Merging is not automatically recursive. A service that defines its own `environment` must merge `*airflow-common-env` inside that mapping too. Our worker does this before adding `DUMB_INIT_SETSID`. Likewise, its dependencies merge the shared database/broker prerequisites before adding `airflow-init`.

The Airflow image resolves from your existing `.env` to:

```text
docker.io/mohammadashraf97/yt_api_elt:1.0.0
```

`1.0.0` is your image tag; its Dockerfile selects Airflow `2.9.2`. The image was found locally in the rootful Podman connection during inspection. Compose does not rebuild it automatically because this file has `image`, not `build`. Editing requirements requires a rebuild before recreating services.

## 4. How .env reaches each application

The lecture combines two different mechanisms:

1. Compose reads root `.env` to replace expressions such as `${IMAGE_TAG}` in YAML.
2. A service's `environment` entries pass the resulting settings into its container. A service-level `env_file: .env` would instead inject that file's entries into that service.

Our file uses explicit `environment` mappings, so it needs no service-level `env_file`. This also avoids passing the YouTube API key to PostgreSQL or the bootstrap database password to ordinary Airflow services. Shell environment values can override interpolation inputs. `${NAME:?message}` stops configuration when a required setting is missing/empty; `${NAME:-default}` supplies a default. See [Compose interpolation](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/).

| Container setting | Purpose |
|---|---|
| `AIRFLOW__CORE__EXECUTOR=CeleryExecutor` | Select the worker/queue execution model. |
| `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN` | Connect Airflow to `airflow_metadata_db`. |
| `AIRFLOW__CELERY__RESULT_BACKEND` | Store Celery execution results in `celery_results_db`. |
| `AIRFLOW__CELERY__BROKER_URL` | Reach Redis at `redis:6379/0`; `/0` selects its logical Redis database. |
| `AIRFLOW__CORE__FERNET_KEY` | Encrypt sensitive values stored in Airflow metadata; keep it stable. |
| `AIRFLOW_CONN_POSTGRES_DB_YT_ELT` | Supply Connection ID `postgres_db_yt_elt`, pointing to `elt_db`. |
| `AIRFLOW_VAR_API_KEY`, `AIRFLOW_VAR_CHANNEL_HANDLE` | Supply Variables `api_key` and `channel_handle` to DAG code. |
| `ELT_DATABASE_*`, `POSTGRES_CONN_*` | Ordinary variables used by later database tests. |

Double underscores in `AIRFLOW__SECTION__OPTION` configure Airflow. Single underscores in `AIRFLOW_CONN_...` and `AIRFLOW_VAR_...` expose Connections/Variables. Environment-supplied Connections/Variables can be retrieved by code without appearing as stored records in the UI. Your standalone Python scripts still read `API_KEY` and `CHANNEL_HANDLE` directly.

The file pauses new DAGs, hides example DAGs, enables the scheduler's health endpoint, and retains the course's Airflow 2 API authentication settings. It limits Celery concurrency and webserver processes to two each for this small workload. Concurrency counts task execution slots, not worker containers.

## 5. Networking: Windows and containers use different addresses

| Caller | Destination | Address in our setup |
|---|---|---|
| Browser on Windows | Airflow UI | `http://localhost:8081` |
| Database client on Windows | PostgreSQL | `localhost:5433` |
| Airflow container | PostgreSQL | `postgres:5432` |
| Airflow container | Redis | `redis:6379` |
| Browser, if Flower is enabled | Flower | `http://localhost:5556` |

For `127.0.0.1:5433:5432`, the parts are **host interface : host port : container port**. Binding to loopback keeps these learning services local. Changing the Windows port does not change PostgreSQL's internal port; keep `.env` values `POSTGRES_CONN_HOST=postgres` and `POSTGRES_CONN_PORT=5432`.

Compose creates a shared network and service-name DNS. Inside the worker, `localhost` means the worker itself. Redis does not need `ports` or even `expose` for services on that network to reach its listening port. Our different host ports leave `8080`/`5432` available for the older Astro project, although running both stacks still consumes shared memory/CPU.

## 6. Storage: bind mounts versus a named volume

```yaml
volumes:
  - ${CONTAINER_PROJECT_ROOT:-.}/data:/opt/airflow/data
```

This **bind mount** makes your Windows `YT_ELT/data` visible inside Airflow. A worker writing `/opt/airflow/data/videos.json` writes a file you can inspect in the project's `data/` folder. Editing DAG files also becomes visible without rebuilding the image. Existing folder purposes are covered in the [Airflow directories guide](../Airflow/Airflow_Directories_Explained.md).

**A fix specific to your actual path:** the live Podman test rejected the commas in `...SQL, Python, Airflow, Docker, CICD...` with `Python: invalid mount option`. The helper [`docker/prepare-podman-mount.ps1`](../../docker/prepare-podman-mount.ps1) creates the Linux symlink `/home/user/yt-elt-project` pointing to this repository under `/mnt/f/...`. The added local `.env` setting `CONTAINER_PROJECT_ROOT=/home/user/yt-elt-project` makes every bind mount use that alias. Files stay in their original Windows location; there is no second copy. Run the helper again after recreating the Podman machine. It refuses to replace an existing alias pointing elsewhere. On other hosts, omitting this setting falls back to ordinary `./` mounts.

PostgreSQL uses a **named volume**:

```yaml
volumes:
  - postgres-db-volume:/var/lib/postgresql/data
```

The top-level `volumes:` declaration defines this storage resource. With project name `yt-elt`, its engine name is `yt-elt_postgres-db-volume`. Podman manages it inside the Linux environment; it is not a new Windows project folder. It holds all three databases and survives container removal and normal `compose down`.

The second PostgreSQL mount puts our `.sh` file under `/docker-entrypoint-initdb.d/`, read-only. That special path is processed by the official image when initializing **empty** database storage. `create_host_path: false` makes a missing script fail instead of silently creating a directory at its filename.

## 7. Each service and the startup sequence

| Service | Role and expected lifecycle |
|---|---|
| `postgres` | One PostgreSQL 13 server; creates three application users/databases on first initialization. |
| `redis` | Celery message broker; stays running. |
| `airflow-init` | Prepares log permissions, migrates metadata tables, and creates the first browser admin; exits successfully. |
| `airflow-webserver` | Serves the Airflow 2 UI; stays running. |
| `airflow-scheduler` | Parses/schedules DAGs and queues tasks; stays running. |
| `airflow-worker` | Executes queued tasks; stays running. |
| `airflow-cli` | Optional `debug` profile for one-off commands. |
| `airflow-triggerer` | Optional `triggerer` profile for deferrable tasks. |
| `flower` | Optional `flower` profile for Celery monitoring. |

```text
Empty PostgreSQL volume
  → PostgreSQL initializes itself and runs our .sh script
  → PostgreSQL and Redis become healthy
  → airflow-init migrates metadata and creates the browser account
  → airflow-init exits 0
  → webserver, scheduler, worker start
```

`service_healthy` waits for a healthcheck; `service_completed_successfully` waits for exit code zero. These are startup gates, not ongoing dependency supervision. An unhealthy status alone does not make `restart` restart a still-running process. PostgreSQL's TCP readiness probe checks server availability, not every password/table; actual initialization and database-login checks provide stronger evidence. See [Compose service behavior](https://docs.docker.com/reference/compose-file/services/).

Ordinary services run as Linux UID `50000`, group `0`, from `AIRFLOW_UID`; this is unrelated to your Windows username. Only `airflow-init` uses root for the mounted log folder before invoking the image entrypoint. The entrypoint reads `_AIRFLOW_DB_MIGRATE` and `_AIRFLOW_WWW_USER_CREATE`. The script creating PostgreSQL databases and this Airflow initializer have different jobs.

## 8. Tailoring and limits

Compared with the supplied file, we use fully qualified registry names and your `IMAGE_TAG`; project-scoped container names; ports `8081`, `5433`, and optional `5556`; explicit variable mappings; optional profiles; a shorter initializer that changes only log-folder ownership; and `unless-stopped` for ordinary services. Removing hardcoded `container_name` also allows worker scaling without manually duplicating service definitions.

All existing `.env` values, including credentials/API key, are preserved; only the nonsecret mount-alias setting was appended. Optional port/concurrency defaults and the alias are documented in `.env.example`; port/concurrency entries are not required in your current `.env`. `.gitattributes` protects the shell script's Linux line endings. The adapted script quotes SQL safely and gives each application ownership of its database, as explained in its companion guide.

The configuration deliberately follows historical course versions for local learning. PostgreSQL 13 is now outside upstream support; this is not a current production deployment template. A later PostgreSQL major upgrade requires a planned data migration, not just changing the tag against the same volume. [PostgreSQL version policy](https://www.postgresql.org/support/versioning/).

Inspection found the WSL engine running with **15.6 GiB effective RAM** and the old Astro containers stopped. The machine listing's 2 GiB field did not reflect effective Linux memory. The available Compose provider is **v2.20.2-desktop.1**, bundled with Docker Desktop. `podman compose` uses that executable to control Podman; Docker Engine need not be started. Retain that provider until a replacement is installed and tested. [Podman Compose behavior](https://docs.podman.io/en/stable/markdown/podman-compose.1.html).

For the exact preparation and startup commands, continue to the [command guide](Docker_and_Podman_Commands_Guide.md). A working UI alone will not produce YouTube data: the DAG and its dependencies still belong to later lessons.

## 9. What was actually verified

Compose validation passed with your installed provider. Your image reported Airflow **2.9.2**, Python **3.10.14**, and working Celery/PostgreSQL imports. A disposable PostgreSQL 13 instance ran the mounted script, created all three databases with correct owners, accepted each application's password, and permitted table creation. It rejected a wrong password; a missing input stopped the script before SQL. A quoted password and hyphenated role name also passed. All seven shared Airflow directory mounts passed in a separate disposable container; rerunning the alias helper was safe.

Test containers, networks, and test-only storage were removed. The downloaded PostgreSQL 13 image remains cached. Existing Astro containers/storage were left intact. The **full YT_ELT stack, Airflow migrations/UI login, and YouTube DAG execution have not been started or validated**; those are the next lecture's startup checks.
