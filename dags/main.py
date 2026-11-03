# DAG defines the workflow; Pendulum and datetime provide dates and durations.
from airflow import DAG
import pendulum
from datetime import datetime, timedelta
# Import TaskFlow functions: calling them below creates tasks, not API requests.
from api.video_stats import get_playlist_id, get_video_id,extract_video_data, save_to_json

# Use Cairo's timezone rules for the start date and daily cron schedule.
local_tz = pendulum.timezone("Africa/Cairo")

# Shared task settings: independent of previous runs, with email alerts disabled.
# Retry and end-date options remain inactive until uncommented.
default_args = {
    "owner": "yt_elt",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "email": "your_email@example.com",
    # 'retries': 1,
    # 'retry_delay': timedelta(minutes=5),
    # Earliest interval boundary, not a command to execute at this instant.
    "start_date": datetime(2025, 1, 1, tzinfo=local_tz),
    # 'end_date': datetime(2030, 12, 31, tzinfo=local_tz),
}

# Tasks created in this context belong to produce_json, scheduled at 14:00 Cairo.
# Skip historical catchup; allow one active run and a one-hour scheduled-run limit.
with DAG(
    dag_id="produce_json",
    default_args=default_args,
    description="Extract YouTube video statistics and save raw JSON.",
    schedule="0 14 * * *",
    catchup=False,
    max_active_runs=1,
    dagrun_timeout=timedelta(hours=1),
) as dag:
    # Resolve the channel's uploads playlist; this variable holds an XComArg now.
    playlist_id = get_playlist_id()
    # At runtime, receive the playlist ID and collect video IDs across all pages.
    video_ids = get_video_id(playlist_id)
    # Fetch metadata and statistics in batches, returning a list of video records.
    extract_data = extract_video_data(video_ids)
    # Write those records to a dated JSON file in the worker's mounted data folder.
    save_to_json_task = save_to_json(extract_data)

    # State the execution order explicitly; output arguments already create it.
    # Airflow runs function bodies later and resolves their inputs through XCom.
    playlist_id >> video_ids >> extract_data >> save_to_json_task
