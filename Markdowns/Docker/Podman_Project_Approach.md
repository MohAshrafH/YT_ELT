# Our Podman approach for YT_ELT

## 1. Overview — what we will use

We will follow the course's Airflow container approach using **Podman as the container engine**. We keep the Dockerfile, image versions, Python requirements, and later Compose service definitions. Podman builds and runs them using Linux supplied by WSL2 on Windows.

```text
Windows: VS Code, project files, PowerShell, Podman CLI
                         ↓ commands
WSL2: existing astro-machine → Podman Linux engine
                         ↓ builds / runs
Custom Airflow image → Airflow containers + PostgreSQL + Redis
```

WSL2 supplies the Linux environment; Podman manages containers; Compose coordinates multiple services. Podman Desktop is an optional graphical interface. No separate VirtualBox/VMware Linux installation is part of this approach.

Our earlier notes recorded a working WSL-backed machine named `astro-machine`, kept in **rootful** mode, and a successful container test. Reuse that machine. Its name does not restrict it to Astro: it can also build and run this project's containers. Those are historical observations; the checks below establish its present state.

**Where Astro fits:** the previous Airflow project used Astro CLI configured for Podman. This course uses an ordinary Dockerfile and Compose file, so we will use Podman directly here. We do not need to convert YT_ELT into an Astro project or run `astro dev start` in this folder. This changes the management commands, while retaining Podman and WSL2 underneath.

## 2. What maps from the tutorial?

| In the tutorial | In our approach |
|---|---|
| Docker Desktop / Docker Engine | Podman engine in the WSL2 machine |
| Dockerfile instructions | Same syntax; keep `ARG`, `FROM`, `ENV`, `COPY`, `RUN` |
| `apache/airflow:2.9.2-python3.10` | Same image, explicitly addressed as `docker.io/apache/airflow:2.9.2-python3.10` |
| Docker Hub | Same registry; its images can be used by Podman |
| `requirements.txt` | Same package list; installed inside the image |
| `docker build ...` | `podman build ...` |
| `docker run`, `docker ps`, `docker logs` | `podman run`, `podman ps`, `podman logs` |
| `docker compose ...` | `podman compose ...`, using an external Compose provider |
| Windows Python `venv` | Remains separate from the container's Python environment |

Podman supports Dockerfile builds, but compatibility still needs project testing, particularly for Compose and Windows folder mounts. [Podman build reference](https://docs.podman.io/en/stable/markdown/podman-build.1.html).

## 3. Start and verify the existing engine

**Where:** a Windows PowerShell terminal, including VS Code's integrated terminal. These machine commands work from any folder. Normal use should not need an administrator terminal.

```powershell
podman --version
wsl --list --verbose
podman machine list
```

**Why:** confirm the client exists, WSL2 is registered, and `astro-machine` is available. The WSL distribution may be named `podman-astro-machine`; the Podman machine command uses `astro-machine`.

If it is stopped, start it; if running, skip the start command:

```powershell
podman machine start astro-machine
podman version
podman info
podman ps --all
```

**Expected:** client and server information, no connection error, and any preserved containers listed. An empty container list alone is not a failure. If the machine is missing or connection fails, inspect `podman system connection list` before changing anything. Keep the existing rootful connection; switching modes changes which stored objects you see. Machine startup runs the Linux environment containing the engine. [Machine start reference](https://docs.podman.io/en/stable/markdown/podman-machine-start.1.html).

For an initial end-to-end test:

```powershell
podman run --rm docker.io/library/alpine:latest echo "Podman is working"
```

Expect that message. `--rm` removes the disposable test container after it exits; the image remains cached.

## 4. Prepare this lecture's files

**Where:** open the YT_ELT folder in VS Code. In PowerShell, enter its project root:

```powershell
Set-Location "F:\Data Engineering\Training\Data Engineering Automation\Data Engineering Project SQL, Python, Airflow, Docker, CICD - Udemy\Project Directory\YT_ELT"
```

Create the following files using VS Code's **New File** action. These are project-root files, separate from this documentation under `Markdowns/Docker`.

```text
YT_ELT/
├── Dockerfile
├── requirements.txt
├── .dockerignore
├── .env                 existing local configuration
├── venv/                existing Windows Python environment
└── Markdowns/Docker/    these guides
```

**Dockerfile:** use the lecture's recipe with a fully qualified registry name and an explicit in-stage argument declaration:

```dockerfile
ARG AIRFLOW_VERSION=2.9.2
ARG PYTHON_VERSION=3.10

FROM docker.io/apache/airflow:${AIRFLOW_VERSION}-python${PYTHON_VERSION}
ARG AIRFLOW_VERSION

ENV AIRFLOW_HOME=/opt/airflow
COPY requirements.txt /
RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" -r /requirements.txt
```

`docker.io` makes the registry unambiguous. The second `ARG AIRFLOW_VERSION` makes the selected build argument available after `FROM`. The versions follow the lecture, not a claim about today's latest releases. See the [line-by-line explanation](Dockerfile_Lecture_Explained.md).

**requirements.txt:** leave it empty for this lecture. Later, add packages your DAGs need and pin versions once tested. Do not copy the downloaded course's final dependency list just to complete this early lesson.

**.dockerignore:** add:

```text
.git/
venv/
.venv/
.env
__pycache__/
Markdowns/
data/
logs/
```

This keeps local secrets and unnecessary files out of the build context. `.gitignore` controls Git; it does not control image builds. Podman accepts `.dockerignore`; if `.containerignore` also exists, Podman gives that file precedence. These exclusions do not prevent later runtime volume mounts.

## 5. Build and check the image

**Where:** PowerShell in the YT_ELT project root, with the machine running.

```powershell
podman build -f Dockerfile -t localhost/yt-elt-airflow:lecture .
```

**Why and how:** `-f` selects the recipe; `-t` assigns a local image name and tag; the final `.` supplies this directory as the build context. `localhost/` labels our locally built image; it does not start a web server or upload to a registry. The first build may download a large base image.

Verify the result:

```powershell
podman images localhost/yt-elt-airflow
podman run --rm localhost/yt-elt-airflow:lecture airflow version
podman run --rm localhost/yt-elt-airflow:lecture python --version
```

**Expected:** the image exists, Airflow reports `2.9.2`, and Python reports `3.10.x`. These commands test the image; they do not start the Airflow web interface or a database.

After a later requirements change, repeat the build. For example, after adding a tested `requests` requirement, verify its installation with:

```powershell
podman run --rm localhost/yt-elt-airflow:lecture python -c "import requests; print(requests.__version__)"
```

## 6. Later — start the course's multi-service environment

This is the next phase, after the course introduces Compose, DAGs, database setup, and environment values. A successful image build completes the current Dockerfile exercise.

**First check the Compose provider**, from any PowerShell folder:

```powershell
podman compose version
```

`podman compose` delegates to another executable. Our earlier setup detected Docker Desktop's bundled Compose v2.20.2, so the Podman engine worked while retaining that file dependency. A provider called `docker-compose.exe` can talk to Podman; its name does not mean Docker Engine is running. [Compose provider reference](https://docs.podman.io/en/stable/markdown/podman-compose.1.html).

If no provider is installed, open **Podman Desktop → Settings → Resources → Compose → Setup**, follow the prompts, reopen PowerShell, and rerun the version check. If Setup is absent because a provider was detected, inspect `Get-Command docker-compose -All`. A location under Docker Desktop indicates the recorded dependency remains. Complete independence needs a standalone provider and a successful project test before removing Docker Desktop. [Compose installation options](https://podman-desktop.io/docs/compose/setting-up-compose).

**Then prepare the course project configuration.** The downloaded reference is under `Course Downloads/Code/YT_ELT-main`, two directories above this project's root. Its Compose file expects a published Docker Hub image, many environment values, DAG/support folders, and a PostgreSQL initialization script. It cannot be treated as a ready-to-run replacement for the current early-stage project.

When those files have been introduced and adapted in YT_ELT:

1. In `docker-compose.yaml`, change the shared `x-airflow-common` image to `localhost/yt-elt-airflow:lecture`. PostgreSQL and Redis keep their own images; qualify them as `docker.io/library/postgres:13` and `docker.io/library/redis:7.2-bookworm` if needed.
2. Populate the required `.env` settings, preserving existing API values. Container-to-container database connections normally use the service name `postgres` and its internal port `5432`, rather than Windows `localhost`.
3. Check the declared folders and initialization script exist, and use LF line endings for the Linux shell script. Check port `8080` and published database port `5432` are free; the older Astro environment may already use them.

**Where:** PowerShell in the configured YT_ELT root. Use the same command prefix throughout:

```powershell
podman compose -p yt-elt -f docker-compose.yaml config --quiet
podman compose -p yt-elt -f docker-compose.yaml run --rm airflow-init
podman compose -p yt-elt -f docker-compose.yaml up -d
podman compose -p yt-elt -f docker-compose.yaml ps
```

These validate configuration, initialize the metadata database and Airflow user, start services, and show status. Resolve missing-variable warnings and initialization failures before continuing. The project name groups Compose resources; the course file's explicit `container_name` entries can still clash with other workloads.

After healthy startup, visit `http://localhost:8080` and use the credentials configured for this project. If it fails:

```powershell
podman compose -p yt-elt -f docker-compose.yaml logs --tail 100 airflow-webserver airflow-scheduler
```

For a normal pause, use `podman compose -p yt-elt -f docker-compose.yaml stop`; resume with `up -d`. After all workloads in the machine are stopped, `podman machine stop astro-machine` stops the Linux environment while preserving it. Avoid `down -v`, machine removal, or WSL unregister during routine use because they can delete stored state.

**Completion for this stage:** the custom image builds and reports the expected Airflow/Python versions. **Completion for the later Compose stage:** initialization succeeds, services remain healthy, and the Airflow page opens. The commands here are instructions to execute; this guide does not claim they have been run for YT_ELT.
