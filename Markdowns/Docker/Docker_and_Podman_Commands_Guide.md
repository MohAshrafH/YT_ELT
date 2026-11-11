# Docker commands, translated to your Podman setup

Use this as the practical companion to the [Compose explanation](Docker_Compose_Lecture_Explained.md) and [PostgreSQL script explanation](Postgres_Initialization_Script_Explained.md). Commands below run in **Windows PowerShell**. Most examples document the project's Podman setup; the PostgreSQL connection section also includes the Docker commands confirmed in your current session. Use the engine that contains your project containers.

## 1. The command layers

| Layer | Course command | Your command and purpose |
|---|---|---|
| Linux host | Managed by Docker Desktop | `podman machine ...` manages `astro-machine`. |
| Engine | `docker images`, `docker ps` | `podman images`, `podman ps`: inspect images/containers. |
| Image building | `docker build` | `podman build`: turn a Dockerfile into an image. |
| Registry | `docker login/pull/push` | `podman login/pull/push`: authenticate/download/upload. |
| Multi-service app | `docker compose ...` | `podman compose ...`: apply this project's YAML. |
| Airflow application | `airflow ...` inside a container | Run through Compose `exec` or `run`. |
| Older Astro project | `astro dev ...` | Only in `C:\Astro\Airflow\learning-airflow`. |

`podman compose` delegates to a Compose provider. Yours is Docker Desktop's `docker-compose.exe`, **v2.20.2-desktop.1**, but it connects to the Podman engine. Its filename does not require starting Docker Engine. Keep it installed until you have tested another provider. [Podman reference](https://docs.podman.io/en/stable/markdown/podman-compose.1.html).

## 2. Check the engine and enter the correct directory

From any PowerShell directory:

```powershell
podman machine list
podman system connection list
podman version
podman ps -a
podman compose version
```

If `astro-machine` is stopped, run `podman machine start astro-machine`, then repeat `podman version`. Expect client/server information. Retain the existing default **`astro-machine-root`** connection; rootful/rootless stores are separate. If another connection became default, use `podman system connection default astro-machine-root` before continuing. Changing that default is a deliberate setting change, not a repair for every container issue.

During inspection on 2026-10-30, the machine was running, effective Linux memory was about 15.6 GiB, and old Astro containers were stopped. To check current effective memory:

```powershell
podman machine ssh astro-machine free -m
```

For project commands, change to this exact root (quotes are necessary because the path contains spaces):

```powershell
Set-Location "F:\Data Engineering\Training\Data Engineering Automation\Data Engineering Project SQL, Python, Airflow, Docker, CICD - Udemy\Project Directory\YT_ELT"
Get-Item docker-compose.yaml, Dockerfile, .env, docker/postgres/init-multiple-databases.sh
```

The existing folders `config`, `dags`, `data`, `include`, `logs`, `plugins`, and `tests` are already present. No Windows virtual-environment activation, native Windows PostgreSQL install, or `astro dev start` is required for these container commands.

**Prepare the mount alias once for this machine** (already performed during setup; safe to repeat):

```powershell
& .\docker\prepare-podman-mount.ps1
```

Podman rejected the commas in your long Windows path. This helper creates `/home/user/yt-elt-project` inside WSL as a symlink to the existing repository. The local `.env` now contains `CONTAINER_PROJECT_ROOT=/home/user/yt-elt-project`; all earlier values are preserved. The helper copies no files and refuses to overwrite a different existing path. Repeat it after recreating the machine. A missing alias or a different connection can make mounts fail even when YAML validation succeeds.

## 3. Validate configuration and inspect the image

```powershell
podman compose -p yt-elt -f docker-compose.yaml config --quiet
podman compose -p yt-elt -f docker-compose.yaml config --services
podman image inspect docker.io/mohammadashraf97/yt_api_elt:1.0.0 --format '{{.Id}}'
```

`-p` selects the project; `-f` selects the file; `config --quiet` validates without printing resolved credentials. Expect exit code zero and no error. `config --services` lists the default services. Plain `config` or broad container inspection can print secrets, so do not share their full output. Configuration validation does not prove database logins, image availability, mounts, or application health.

That custom image is already present locally in the inspected rootful store. If it is absent later, either pull your published tag or rebuild from the local Dockerfile:

```powershell
# Download only if the published tag exists and your account can access it.
podman pull docker.io/mohammadashraf97/yt_api_elt:1.0.0

# Alternative: build locally; no registry push is needed to run locally.
podman build -f Dockerfile -t docker.io/mohammadashraf97/yt_api_elt:1.0.0 .
```

`-t` assigns the image name/tag; final `.` is the build context. Do not run both alternatives unnecessarily. For registry authentication/token steps, see the existing [build and push guide](Podman_Build_and_Push_Steps.md). A successful local build does not prove a successful push.

Optional disposable image checks:

```powershell
podman run --rm docker.io/mohammadashraf97/yt_api_elt:1.0.0 airflow version
podman run --rm docker.io/mohammadashraf97/yt_api_elt:1.0.0 python --version
```

Expect `2.9.2` and Python `3.10.x`. `run` creates a new container; `--rm` removes that temporary container after exit. It does not delete the image or start the full stack.

### Rebuild and publish after adding dependencies: 1.0.0 to 1.0.1

This is the Soda lecture's image-update workflow, tailored to your Docker Hub repository **`mohammadashraf97/yt_api_elt`**. Run commands from the YT_ELT root in PowerShell. Choose the Docker or Podman sequence for the engine holding your project; their local image stores are separate. These examples document a future update; creating this guide does not build, publish, or restart anything.

First save the required packages in `requirements.txt`. For the tutorial's Soda Core v3 workflow, use a v3 constraint such as `soda-core-postgres>=3.5,<4`, and add `pytest` when implementing the functional tests. Resolve compatibility and pin the working versions when implementing. See [Soda overview and commands](../Testing/Soda_Data_Quality_Overview_and_Commands.md) for the version distinction.

**Docker Engine — build, log in, and push:**

```powershell
docker build -f Dockerfile -t docker.io/mohammadashraf97/yt_api_elt:1.0.1 .
docker images docker.io/mohammadashraf97/yt_api_elt
docker login --username mohammadashraf97 docker.io
docker push docker.io/mohammadashraf97/yt_api_elt:1.0.1
```

**Podman — equivalent sequence:**

```powershell
podman build -f Dockerfile -t docker.io/mohammadashraf97/yt_api_elt:1.0.1 .
podman images docker.io/mohammadashraf97/yt_api_elt
podman login --username mohammadashraf97 docker.io
podman push docker.io/mohammadashraf97/yt_api_elt:1.0.1
```

Run each next step only after the previous command succeeds. At the hidden password prompt, enter your Docker Hub access token with repository read/write permission; see the [token setup steps](Podman_Build_and_Push_Steps.md#generate-the-access-token). The tag `1.0.1` versions your custom image; Airflow remains `2.9.2`. Changing the requirements file causes the Dockerfile's dependency-install layer to rebuild. [Docker build reference](https://docs.docker.com/reference/cli/docker/buildx/build/), [push reference](https://docs.docker.com/reference/cli/docker/image/push/).

| Action | Docker example | Podman equivalent | What it changes |
|---|---|---|---|
| Build new contents | `docker build -t docker.io/mohammadashraf97/yt_api_elt:1.0.1 .` | Replace `docker` with `podman` | Creates a local image from the Dockerfile |
| Assign another tag | `docker tag docker.io/mohammadashraf97/yt_api_elt:1.0.1 docker.io/mohammadashraf97/yt_api_elt:soda-v3` | Replace `docker` with `podman` | Adds a name for the same image; does not install packages |
| Upload one tag | `docker push docker.io/mohammadashraf97/yt_api_elt:1.0.1` | Replace `docker` with `podman` | Publishes that tag to Docker Hub |
| Download one tag | `docker pull docker.io/mohammadashraf97/yt_api_elt:1.0.1` | Replace `docker` with `podman` | Downloads the image; leaves running containers as they are |

The extra `soda-v3` tag is optional and is not used by the remaining examples. Confirm `1.0.1` appears in your repository's **Tags** tab after the push.

### Select the new tag, pull, and recreate the containers

Before pulling or recreating, edit the existing `.env` entry to:

```dotenv
IMAGE_TAG=1.0.1
```

Keep `DOCKERHUB_NAMESPACE=mohammadashraf97` and `DOCKERHUB_REPOSITORY=yt_api_elt`. This is essential: Compose reads `${IMAGE_TAG}` from the environment/configuration; building or pushing `1.0.1` does not change the existing `1.0.0` selection. A PowerShell `$env:IMAGE_TAG` value takes precedence over `.env` if you have set one.

**Docker Engine — the tutorial's pull/recreate/verify sequence:**

```powershell
docker compose -p yt-elt -f docker-compose.yaml config --quiet
docker compose -p yt-elt -f docker-compose.yaml pull
docker compose -p yt-elt -f docker-compose.yaml up -d --force-recreate
docker compose -p yt-elt -f docker-compose.yaml ps -a
docker ps --filter label=com.docker.compose.project=yt-elt --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
docker inspect yt-elt-airflow-worker-1 --format '{{.Config.Image}}'
```

**Podman — equivalent sequence:**

```powershell
podman compose -p yt-elt -f docker-compose.yaml config --quiet
podman compose -p yt-elt -f docker-compose.yaml pull
podman compose -p yt-elt -f docker-compose.yaml up -d --force-recreate
podman compose -p yt-elt -f docker-compose.yaml ps -a
podman ps --filter label=com.docker.compose.project=yt-elt --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
podman inspect yt-elt-airflow-worker-1 --format '{{.Config.Image}}'
```

Expect the worker's image reference to end in **`:1.0.1`**, and the application services to become healthy. Check `airflow-init` logs as in section 4. The full-stack recreation replaces service containers and briefly interrupts the application; named database storage remains attached. `airflow-init` completing with exit code zero is normal.

`compose pull` downloads the configured service images, including PostgreSQL and Redis for this full-stack sequence. To download only the custom Airflow image, use `docker compose -p yt-elt -f docker-compose.yaml pull airflow-worker` (or `podman compose ...`); the Airflow services share that image. Pulling does not start containers. [Compose pull reference](https://docs.docker.com/reference/cli/docker/compose/pull/).

`up -d --force-recreate` replaces containers using the selected image; **it does not itself rebuild this project's Dockerfile**. This Compose file has `image:` entries and no `build:` section, so `compose build` or `up --build` does not replace the explicit build step above. `restart` also does not adopt a newly selected image. [Compose up reference](https://docs.docker.com/reference/cli/docker/compose/up/).

For a local-only update on the same engine, skip login/push/pull after building, select `IMAGE_TAG=1.0.1`, and recreate using the local image. For the published-image workflow, complete the push before pulling. If the worker still shows `1.0.0`, check the selected tag, shell overrides, engine, and Compose project before recreating again; closing VS Code is not an image-update step.

## 4. Start the stack and verify initialization

The tailored file already includes initialization dependencies, so the normal startup is:

```powershell
podman compose -p yt-elt -f docker-compose.yaml up -d
podman compose -p yt-elt -f docker-compose.yaml ps -a
podman compose -p yt-elt -f docker-compose.yaml logs --tail 100 airflow-init
```

`up` creates/reconciles services, network, and volume; `-d` leaves long-running services in the background. First startup may download PostgreSQL and Redis. PostgreSQL initializes empty storage and runs our mounted script; Airflow initialization then migrates tables and creates the browser user. The application services wait for those steps.

Expected: `airflow-init` exits **0**; PostgreSQL, Redis, webserver, scheduler, and worker remain running and become healthy. An exited initializer is normal; a repeatedly exiting worker or scheduler is not. Optional triggerer, Flower, and CLI services remain off.

If you want to diagnose initialization separately before normal startup, `podman compose -p yt-elt -f docker-compose.yaml run --rm airflow-init` runs a temporary initializer and returns its result. A later `up` still manages the regular initializer service; repeating migrations is expected, but initial UI settings do not reset existing users.

Open [Airflow UI](http://localhost:8081). Use `AIRFLOW_WWW_USER_USERNAME` and `AIRFLOW_WWW_USER_PASSWORD` from your local `.env`; do not assume the password is `airflow`. An empty DAG list is expected at this stage: your root extraction scripts have not yet become DAGs.

## 5. Inspect a running application

```powershell
podman compose -p yt-elt -f docker-compose.yaml logs --tail 100 postgres
podman compose -p yt-elt -f docker-compose.yaml logs --tail 100 airflow-scheduler airflow-worker
podman compose -p yt-elt -f docker-compose.yaml logs -f --tail 50 airflow-webserver
```

`logs` reads output; `--tail` limits old lines; `-f` follows new output. **Ctrl+C** ends a log-follow command without stopping detached services. Review logs locally before sharing them because applications can log sensitive values.

`exec` runs a command inside an **existing running** service container:

```powershell
podman compose -p yt-elt -f docker-compose.yaml exec airflow-scheduler airflow dags list
podman compose -p yt-elt -f docker-compose.yaml exec airflow-worker python --version
podman compose -p yt-elt -f docker-compose.yaml exec airflow-worker ls -la /opt/airflow/data
```

These commands demonstrate the container's Airflow, Python, and mounted Linux paths. Packages installed only in Windows `venv` are not automatically available here.

### Enter the worker and run a Python script

The project's worker container is **`yt-elt-airflow-worker-1`** (Compose service: `airflow-worker`). This container executes Airflow tasks and has the project's container dependencies and connection settings. Use it for the [DWH/ELT example](../DWH_ELT/Data_Utils_Explained.md).

From Windows PowerShell, open an interactive Bash shell:

```powershell
podman exec -it yt-elt-airflow-worker-1 bash
```

Then run these commands **inside the container**:

```bash
cd /opt/airflow/dags
python your_script.py
exit
```

Replace `your_script.py` with the filename of your saved example under `dags/`. `exit` returns to PowerShell. The Windows `dags/` folder is mounted at `/opt/airflow/dags` inside the container. Running `datawarehouse/data_utils.py` alone only defines its helpers; use an example script that calls them to execute SQL.

Alternatively, execute the script directly from PowerShell:

```powershell
podman exec -it yt-elt-airflow-worker-1 python /opt/airflow/dags/your_script.py
```

Or address the Compose service from the project directory, without depending on its generated container name:

```powershell
podman compose -p yt-elt -f docker-compose.yaml exec airflow-worker bash
podman compose -p yt-elt -f docker-compose.yaml exec airflow-worker python /opt/airflow/dags/your_script.py
```

These are alternatives: the first opens a shell; the second runs Python directly. `-i` keeps input open and `-t` allocates an interactive terminal. To check container names, run `podman ps` in PowerShell. With Docker Engine, the equivalent commands use `docker exec` or `docker compose` against containers running in Docker.

Executing a script this way runs ordinary Python immediately; it does not schedule or trigger an Airflow DAG.

### Verify Soda and pytest in the rebuilt worker

After the dependency update and recreation in section 3, the tutorial enters the worker with `docker exec`. Your Docker commands from PowerShell are:

```powershell
docker exec -it yt-elt-airflow-worker-1 bash
```

Inside that **Linux container**, check the installed packages and CLI:

```bash
python -m pip show soda-core-postgres
python -m pip show pytest
soda --help
exit
```

The first command confirms the **Soda PostgreSQL connector**, not installation of the PostgreSQL database server. Expect pytest only if you included it in the rebuilt requirements. `exit` returns to PowerShell.

You can run the same checks directly through Compose, without opening Bash:

```powershell
docker compose -p yt-elt -f docker-compose.yaml exec airflow-worker python -m pip show soda-core-postgres
docker compose -p yt-elt -f docker-compose.yaml exec airflow-worker python -m pip show pytest
docker compose -p yt-elt -f docker-compose.yaml exec airflow-worker soda --help
```

For Podman, use `podman exec -it yt-elt-airflow-worker-1 bash`, or replace `docker compose` with `podman compose` in the direct checks. If the package is absent, confirm the worker image tag and the requirements used to build it. The [Soda guide](../Testing/Soda_Data_Quality_Overview_and_Commands.md) covers connection tests and data scans after these installation checks.

### Connect to PostgreSQL and query the ELT database

For the complete PostgreSQL-only walkthrough, including roles, databases, schemas, tables, and example psql output, see [PostgreSQL commands and interactions](Postgres_Commands_and_Interactions.md).

Your `docker compose ps postgres` output on 2026-11-08 confirmed the running container name **`yt-elt-postgres-1`**, Compose service **`postgres`**, and Windows port **5433** mapped to container port **5432**.

Run these commands from the YT_ELT project directory in PowerShell:

```powershell
# Check the PostgreSQL service and its actual container name.
docker compose ps postgres

# Only if the service needs starting:
docker compose up -d postgres

# Open psql using the Compose service name.
docker compose exec postgres psql -U yt_api_user -d elt_db
```

Alternatively, connect directly using the confirmed container name:

```powershell
docker exec -it yt-elt-postgres-1 psql -U yt_api_user -d elt_db
```

Choose either connection command. `docker exec` expects a container name or ID, so `docker exec -it postgres ...` fails with `no container with name or ID "postgres" found`. `docker compose exec` resolves the service name `postgres` to its container. Compose generates names from the project, service, and instance number; recheck `docker compose ps postgres` if the name changes.

At the `elt_db=>` prompt, run SQL and psql commands:

```sql
-- List tables in the core schema.
\dt core.*

-- Query the table shown in the course screenshot, if it exists.
SELECT * FROM core.yt_api;

-- Leave psql and return to PowerShell.
\q
```

SQL statements end with `;`. The psql commands `\dt` and `\q` do not need one. If the table is missing, use `\dt *.*` to inspect existing tables; connecting to PostgreSQL does not create the application's tables or run the ELT pipeline.

For containers managed through Podman, the equivalent connection commands are:

```powershell
podman compose -p yt-elt -f docker-compose.yaml exec postgres psql -U yt_api_user -d elt_db
# Alternative using the container name:
podman exec -it yt-elt-postgres-1 psql -U yt_api_user -d elt_db
```

### Check database owners and password authentication

Check the actual databases and owners (the configured bootstrap user is `postgres`):

```powershell
podman compose -p yt-elt -f docker-compose.yaml exec postgres psql -U postgres -d postgres -c 'SELECT datname, pg_get_userbyid(datdba) AS owner FROM pg_database WHERE datistemplate = false;'
```

Expect `postgres` plus `airflow_metadata_db`, `celery_results_db`, and `elt_db`, with their application owners. To verify a password login, connect through the service's network address and enter the corresponding local password at the hidden prompt:

```powershell
podman compose -p yt-elt -f docker-compose.yaml exec postgres psql -h postgres -U yt_api_user -d elt_db -W -c 'SELECT current_user, current_database();'
```

Repeat with the metadata/Celery user and database when needed. In the official PostgreSQL 13 image, socket and container-loopback connections may use trust authentication; even `-W` merely forces a prompt and does not prove the server checked that password. Using service name `postgres` reaches its network address. Windows tools such as DBeaver use host `localhost`, port **5433**, and the same chosen database/user/password.

## 6. Normal stopping, resuming, and changing files

| Intent | Command after the usual Compose prefix | Effect |
|---|---|---|
| Pause this project | `stop` | Stop its containers, keep containers/storage. |
| Resume/reconcile | `up -d` | Start stopped containers and apply configuration changes as needed. |
| Remove this project's containers/network | `down` | Preserve the named PostgreSQL volume and Windows bind-mounted files. |
| Recreate after `.env`/service changes | `up -d --force-recreate` | Replace containers with current settings; keep named storage. |
| Restart unchanged containers | `restart` | Restart processes; does not apply new environment/image configuration. |

For example:

```powershell
podman compose -p yt-elt -f docker-compose.yaml stop
# Later:
podman compose -p yt-elt -f docker-compose.yaml up -d
```

Editing a mounted DAG/SQL/data file usually needs no image rebuild. Editing `requirements.txt` or Dockerfile does: rebuild the selected image, then recreate affected services. Changing `.env` requires recreation, but changing a database password additionally requires updating the stored role password. See the script guide before doing that.

For the complete dependency-update example, follow [rebuild and publish](#rebuild-and-publish-after-adding-dependencies-100-to-101), then [select, pull, and recreate](#select-the-new-tag-pull-and-recreate-the-containers). Those steps use `1.0.1`; the initial-start examples earlier in this guide use `1.0.0`.

When every workload in this shared machine is stopped, `podman machine stop astro-machine` shuts down Linux while preserving it. This affects all projects in that machine, so first inspect `podman ps`. Keep the old Astro containers and volumes intact.

## 7. Optional services and scaling

```powershell
podman compose -p yt-elt -f docker-compose.yaml --profile flower up -d
podman compose -p yt-elt -f docker-compose.yaml --profile triggerer up -d
podman compose -p yt-elt -f docker-compose.yaml run --rm airflow-cli airflow version
podman compose -p yt-elt -f docker-compose.yaml up -d --scale airflow-worker=2
```

These are alternatives for later exploration, not required startup steps. Flower opens on `localhost:5556`; the triggerer supports deferrable tasks. Explicitly targeting `airflow-cli` enables that profiled service for the one-off run. Two workers with default concurrency two can provide up to four execution slots, subject to Airflow limits/resources. Use `--scale airflow-worker=1` to return to one worker.

## 8. Volume inspection and the destructive reset

The lecture's `docker volume ls` / `docker volume rm` map to `podman volume ls` / `podman volume rm`. Inspect first:

```powershell
podman volume ls
podman volume inspect yt-elt_postgres-db-volume
```

**Only for an intentionally disposable YT_ELT database:** the following erases all three databases, including Airflow users/history and YouTube tables. Prefer repairing credentials if data matters. Do not substitute an Astro volume name.

```powershell
# DESTRUCTIVE: deliberately discard this project's database storage.
podman compose -p yt-elt -f docker-compose.yaml down
podman volume rm yt-elt_postgres-db-volume
# Recreate empty storage and rerun first initialization:
podman compose -p yt-elt -f docker-compose.yaml up -d
```

`down -v` is a shorter destructive alternative that removes this Compose project's declared volumes. Neither reset belongs in normal shutdown. Avoid machine removal, WSL unregister, and broad prune commands for this lesson.

## 9. Common symptoms

| Symptom | Next useful check |
|---|---|
| Cannot connect to Podman | Machine state, `podman version`, default rootful connection. |
| Missing Compose provider | Existing `docker-compose.exe`; see [provider setup](https://podman-desktop.io/docs/compose/setting-up-compose). |
| `no container with name or ID "postgres" found` | Use `docker compose exec postgres psql -U yt_api_user -d elt_db`, or `docker exec -it yt-elt-postgres-1 psql -U yt_api_user -d elt_db`; confirm the name with `docker compose ps postgres`. |
| Required variable missing | Actual `.env` filename/value and any overriding PowerShell environment setting. |
| Worker still uses `1.0.0` after building `1.0.1` | Set `IMAGE_TAG=1.0.1`, check shell overrides and engine, then pull if using the registry and recreate; `restart` does not adopt a new image. |
| Push denied or tag cannot be pulled | Correct Docker Hub account/repository, access-token permissions, successful push, and identical tag spelling. |
| Soda missing after an image update | Confirm `requirements.txt` included the connector, the image build succeeded, and the worker was recreated from that image. |
| Invalid mount or script is a directory | File exists, correct root, alias prepared; inspect `podman machine ssh astro-machine ls /home/user/yt-elt-project/docker/postgres`. |
| `Python: invalid mount option` | Ensure `CONTAINER_PROJECT_ROOT` uses the comma-free Linux alias, then rerun the helper. |
| `^M` / carriage-return errors | Save `.sh` with LF and UTF-8 without BOM. |
| Password authentication failed after editing `.env` | Existing volume still stores the earlier password; initialization is not a password reset. |
| `airflow-init` fails | Its logs, PostgreSQL script logs, database ownership, connection settings. |
| Port already allocated | Check Windows listeners and adjust host-port overrides, keeping container ports unchanged. |
| UI works but no data appears | DAG code, dependencies, scheduling/unpause, then task logs; Compose alone does not run the old scripts. |

Podman Desktop can show these same containers, logs, images, and volumes. Look for the **yt-elt** project and generated names such as `yt-elt-postgres-1`; the older `learning-airflow_b0e091` group is a different application.
