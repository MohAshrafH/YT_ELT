# Docker commands, translated to your Podman setup

Use this as the practical companion to the [Compose explanation](Docker_Compose_Lecture_Explained.md) and [PostgreSQL script explanation](Postgres_Initialization_Script_Explained.md). Commands below run in **Windows PowerShell**. Use Podman for YT_ELT; Docker examples explain the lecture's vocabulary.

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
| Required variable missing | Actual `.env` filename/value and any overriding PowerShell environment setting. |
| Invalid mount or script is a directory | File exists, correct root, alias prepared; inspect `podman machine ssh astro-machine ls /home/user/yt-elt-project/docker/postgres`. |
| `Python: invalid mount option` | Ensure `CONTAINER_PROJECT_ROOT` uses the comma-free Linux alias, then rerun the helper. |
| `^M` / carriage-return errors | Save `.sh` with LF and UTF-8 without BOM. |
| Password authentication failed after editing `.env` | Existing volume still stores the earlier password; initialization is not a password reset. |
| `airflow-init` fails | Its logs, PostgreSQL script logs, database ownership, connection settings. |
| Port already allocated | Check Windows listeners and adjust host-port overrides, keeping container ports unchanged. |
| UI works but no data appears | DAG code, dependencies, scheduling/unpause, then task logs; Compose alone does not run the old scripts. |

Podman Desktop can show these same containers, logs, images, and volumes. Look for the **yt-elt** project and generated names such as `yt-elt-postgres-1`; the older `learning-airflow_b0e091` group is a different application.
