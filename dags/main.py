# DAG groups tasks; Pendulum supplies timezone rules; datetime/timedelta set timing.
from airflow import DAG
import pendulum
from datetime import datetime, timedelta

# Import decorated TaskFlow functions used to build the extraction pipeline.
from api.video_stats import get_playlist_id, get_video_id,extract_video_data, save_to_json

# Keep the start date and scheduled runs aligned with Cairo's timezone rules.
local_tz = pendulum.timezone("Africa/Cairo")

# Defaults inherited by the DAG's tasks unless a task overrides them.
default_args = {
    "owner": "yt_elt",  # Task ownership label shown in Airflow.
    "depends_on_past": False,  # Do not require the previous run's task to succeed.
    "email_on_failure": False,  # Disable task-failure emails.
    "email_on_retry": False,  # Disable task-retry emails; this does not set retries.
    "email": "your_email@example.com",  # Placeholder recipient; alerts above are disabled.
    "start_date": datetime(2025, 1, 1, tzinfo=local_tz),  # Earliest data-interval boundary.
}

# Register this workflow; tasks created in the with block belong to this DAG.
with DAG(
    dag_id="produce_json",  # Unique workflow ID used by the UI and CLI.
    default_args=default_args,  # Apply the shared task settings above.
    description="Extract YouTube video statistics and save raw JSON.",  # UI summary.
    schedule="0 14 * * *",  # Daily at 14:00 Cairo; scheduled runs follow interval end.
    catchup=False,  # Skip the backlog of historical scheduled intervals.
    max_active_runs=1,  # Allow only one active run of this DAG at a time.
    dagrun_timeout=timedelta(hours=1),  # Limit scheduled DAG runs to one hour.
) as dag:
    # These calls build tasks now; their bodies run later on an Airflow worker.
    # Returned XComArgs reference task outputs, resolved through XCom at runtime.
    playlist_id = get_playlist_id()  # Resolve the channel's uploads playlist ID.
    video_ids = get_video_id(playlist_id)  # Collect video IDs across playlist pages.
    extract_data = extract_video_data(video_ids)  # Fetch video metadata and statistics.
    save_to_json_task = save_to_json(extract_data)  # Write records to a dated JSON file.

    # Explicit upstream-to-downstream order; output arguments already imply this chain.
    playlist_id >> video_ids >> extract_data >> save_to_json_task
