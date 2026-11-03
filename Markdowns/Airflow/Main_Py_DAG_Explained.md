# Understanding main.py: Airflow Imports, Task Decorators, and Execution Flow

`dags/main.py` defines **when** the YouTube extraction runs and **how** its four tasks connect. The API requests and file-writing logic live in `dags/api/video_stats.py`.

## 1. Imports and configuration

| Code | Purpose |
| --- | --- |
| `from airflow import DAG` | Imports the workflow class. |
| `import pendulum` | Provides Cairo's timezone object. |
| `datetime, timedelta` | Represent fixed dates and durations. |
| `from api.video_stats import ...` | Imports four functions already decorated with `@task`. |
| `local_tz = pendulum.timezone("Africa/Cairo")` | Gives the start date Cairo timezone information. |

The function name is **`get_video_id`**, singular, although it returns a list of IDs. The local variable `video_ids` correctly describes that list.

Importing `video_stats.py` also reads `API_KEY` and `CHANNEL_HANDLE` through `Variable.get(...)`. Your Compose configuration supplies them as `AIRFLOW_VAR_API_KEY` and `AIRFLOW_VAR_CHANNEL_HANDLE`. Missing values can prevent the DAG from loading. The module's `if __name__ == "__main__":` block is skipped during import.

### The added Airflow imports: which file uses what?

| Import | Location | Why it is there |
| --- | --- | --- |
| `from airflow import DAG` | `main.py` | Creates the workflow container, schedule, and run-level settings. |
| `from airflow.decorators import task, dag` | `api/video_stats.py` | `task` wraps the four functions as TaskFlow tasks. The imported `dag` decorator is currently unused; `main.py` uses `with DAG(...)` instead. |
| `from airflow.models import Variable` | `api/video_stats.py` | Retrieves configuration through Airflow instead of directly loading a local `.env` file. |

`DAG` is the workflow class, `@dag` is an alternative way to define a workflow through a function, and `@task` defines an individual task. They have different jobs. **Using `@task` does not require using `@dag`.**

For your configuration, `Variable.get("API_KEY")` resolves the key named `API_KEY`, supplied through `AIRFLOW_VAR_API_KEY`. Environment-backed variables need not appear in the UI's Variables list. With no fallback supplied, a missing variable raises an error rather than returning `None`.

The old dotenv-related comments in the helper file describe its earlier standalone version. The active code now uses `Variable.get`, not `load_dotenv` or `os.getenv`.

Reference: [managing Airflow Variables](https://airflow.apache.org/docs/apache-airflow/2.9.2/howto/variable.html).

## 2. What default_args controls

The dictionary supplies shared defaults to the tasks through `DAG(default_args=default_args)`.

| Setting | Effect in this code |
| --- | --- |
| `owner="yt_elt"` | Labels task ownership. |
| `depends_on_past=False` | A task does not depend on its previous run succeeding. |
| Email flags set to `False` | Built-in failure and retry emails are disabled. |
| `email="your_email@example.com"` | An unused placeholder while those alerts are disabled. |
| Commented `retries` / `retry_delay` | Inactive; environment defaults apply. The current container resolves retries to **0**. |
| `start_date` | Tasks inherit 1 January 2025 at midnight in Cairo as their earliest scheduling boundary. |
| Commented `end_date` | Inactive; no end-date cutoff is configured. |

Reference: [task arguments](https://airflow.apache.org/docs/apache-airflow/2.9.2/_api/airflow/models/baseoperator/index.html).

## 3. Creating the DAG

`with DAG(...) as dag:` creates the workflow object and makes it the context for task creation. Tasks instantiated inside this block belong to it.

| DAG argument | Meaning |
| --- | --- |
| `dag_id="produce_json"` | Workflow identifier shown in Airflow. |
| `description=...` | Explains the workflow's purpose in the UI. |
| `schedule="0 14 * * *"` | Daily at 14:00 Cairo time. |
| `catchup=False` | Avoids scheduling every missing historical interval. |
| `max_active_runs=1` | Limits this DAG to one active run at a time. |
| `dagrun_timeout=timedelta(hours=1)` | Sets a one-hour timeout for scheduled DAG runs in Airflow 2.9.2. |

The last two settings belong directly on `DAG(...)`; they are not task defaults. `max_active_runs` limits workflow runs, not the number of tasks.

Reference: [DAG arguments](https://airflow.apache.org/docs/apache-airflow/2.9.2/_api/airflow/models/dag/index.html).

## 4. Definition time versus execution time

### Why use the task decorator?

The original extraction functions perform ordinary Python work. Adding `@task` lets Airflow manage each step separately: scheduling it on a worker, recording its status and logs, applying task retry settings, and transferring returned values to downstream tasks.

```python
# Simplified illustration from the helper module:
from airflow.decorators import task

@task
def get_playlist_id():
    # The real function calls YouTube and returns the uploads playlist ID.
    return "example_playlist_id"
```

Without `@task`, calling this function would immediately execute its body. Calling all four plain functions in `main.py` would do extraction during file parsing, rather than create four scheduled tasks. Another valid approach is wrapping plain functions in `PythonOperator`; `@task` avoids that additional wiring here.

### What happens when Airflow reads main.py?

Airflow first parses the file to **build the workflow**. During this phase:

1. Imports run and configuration is read.
2. The DAG object is created.
3. Calls to the decorated functions create tasks and return **XComArg output references**.
4. Airflow records their dependencies.

For example, `playlist_id = get_playlist_id()` does not fetch the playlist during parsing. At this point, `playlist_id` is a reference to the future task result. When the task executes, its returned playlist ID becomes available through XCom.

TaskFlow resolves these references into actual values when downstream tasks execute. Ordinary undecorated functions would behave differently: calling them would immediately execute their bodies.

| Expression | During DAG construction | During task execution |
| --- | --- | --- |
| `get_playlist_id()` | Creates a task and an output reference | Calls YouTube and returns a string |
| `get_video_id(playlist_id)` | Connects the upstream output reference | Receives the string and returns a list of IDs |
| `extract_video_data(video_ids)` | Adds the extraction task | Receives IDs and returns video records |
| `save_to_json(extract_data)` | Adds the save task | Receives records and writes JSON |

The Python variable names are references during construction. The actual UI task IDs come from the decorated function names: `get_playlist_id`, `get_video_id`, `extract_video_data`, and `save_to_json`.

Reference: [TaskFlow](https://airflow.apache.org/docs/apache-airflow/2.9.2/tutorial/taskflow.html).

## 5. Exact runtime flow

```text
Configured channel handle
        ↓
get_playlist_id
        ↓ uploads playlist ID: string
get_video_id
        ↓ video IDs: list of strings
extract_video_data
        ↓ video records: list of dictionaries
save_to_json
        ↓
/opt/airflow/data/YT_data_<worker-date>.json
```

1. **Resolve the uploads playlist.** `get_playlist_id()` calls YouTube's channels endpoint using the configured handle and returns the channel's uploads playlist ID.
2. **Collect video IDs.** `get_video_id(playlist_id)` reads playlist pages of up to 50 entries, following `nextPageToken` until no pages remain.
3. **Extract records.** `extract_video_data(video_ids)` requests video details in batches of up to 50 IDs. Each record contains `video_id`, `title`, `publishedAt`, `duration`, `viewCount`, `likeCount`, and `commentCount`.
4. **Write JSON.** `save_to_json(extract_data)` writes the records as UTF-8 JSON. It returns `None`; the useful result is the file.

The worker's current directory is `/opt/airflow`, so `./data/...` resolves to `/opt/airflow/data/...`. Compose mounts that directory to your configured project data folder.

## 6. How dependencies work

```python
playlist_id >> video_ids >> extract_data >> save_to_json_task
```

This explicitly states the task order. Passing each task's output into the next call already establishes the same chain, so the final line is redundant but valid and useful for reading the sequence.

With the default trigger rule, each task waits for its upstream task to succeed. An extraction failure prevents the save task from running. With the current zero-retry setting, a failed task receives no automatic additional attempt.

## 7. Scheduling and output details

For the normal cron timetable in this Airflow version, runs become eligible after their data intervals finish. The first full interval after the configured midnight start date is **1 January 2025 at 14:00 → 2 January at 14:00**.

Because `catchup=False`, enabling this new DAG later can schedule the latest completed interval shortly afterward. Automatic scheduling requires the DAG to be unpaused and Airflow services running.

Reference: [data intervals and catchup](https://airflow.apache.org/docs/apache-airflow/2.9.2/core-concepts/dag-run.html).

The current helper code also means:

- Requests fetch current API results; interval dates do not automatically filter YouTube data.
- Output filenames use the worker's `datetime.date.today()`, not the DAG's logical date or an explicitly selected Cairo date.
- Runs on the same worker date overwrite the same JSON file.
- Counts remain strings; absent counts become JSON `null`.
- The full extracted list passes through XCom before saving, which can become expensive for large channels.

## Verification

Verified in the running scheduler container: **zero DAG import errors**, four tasks, the expected three dependency edges, `Africa/Cairo` timezone, one active run, and a one-hour timeout. Both Python files passed syntax checks, and the worker's data directory exists. No live extraction was triggered during this review.
