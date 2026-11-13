# DAG groups tasks; Pendulum supplies timezone rules; datetime/timedelta set timing.
from airflow import DAG
import pendulum
from datetime import datetime, timedelta
from datawarehouse.dwh import staging_table, core_table  # Import the functions that create the DAG's tasks. 
from airflow.decorators import task  # Turn decorated functions into Airflow tasks.
from airflow.operators.trigger_dagrun import TriggerDagRunOperator  # Trigger another DAG from this one.

# Import decorated TaskFlow functions used to build the extraction pipeline.
from api.video_stats import get_playlist_id, get_video_id,extract_video_data, save_to_json

from dataquality.soda import yt_elt_data_quality

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

staging_schema = "staging"  # Database schema for staging tables.
core_schema = "core"  # Database schema for core tables.

# Register this workflow; tasks created in the with block belong to this DAG.
with DAG(
    dag_id="produce_json",  # Unique workflow ID used by the UI and CLI.
    default_args=default_args,  # Apply the shared task settings above.
    description="Extract YouTube video statistics and save raw JSON.",  # UI summary.
    schedule="0 14 * * *",  # Daily at 14:00 Cairo; scheduled runs follow interval end.
    catchup=False,  # Skip the backlog of historical scheduled intervals.
    max_active_runs=1,  # Allow only one active run of this DAG at a time.
    dagrun_timeout=timedelta(hours=1),  # Limit scheduled DAG runs to one hour.
) as dag_produce:
    # These calls build tasks now; their bodies run later on an Airflow worker.
    # Returned XComArgs reference task outputs, resolved through XCom at runtime.
    playlist_id = get_playlist_id()  # Resolve the channel's uploads playlist ID.
    video_ids = get_video_id(playlist_id)  # Collect video IDs across playlist pages.
    extract_data = extract_video_data(video_ids)  # Fetch video metadata and statistics.
    save_to_json_task = save_to_json(extract_data)  # Write records to a dated JSON file.

    trigger_update_db = TriggerDagRunOperator(
        task_id="trigger_update_db",  # Unique task ID within this DAG.
        trigger_dag_id="update_db",  # Name of the DAG to trigger after this one.
    )

    # Explicit upstream-to-downstream order; output arguments already imply this chain.
    playlist_id >> video_ids >> extract_data >> save_to_json_task

with DAG(  # Create the workflow; tasks defined inside this block belong to it.
    dag_id="update_db",  # Unique workflow ID shown in Airflow's UI and CLI.
    default_args=default_args,  # Apply shared task settings from the existing dictionary.
    description="DAG to process JSON file and insert data into both staging and core schemas",  # UI summary.
    schedule=None, # This DAG is triggered by the produce_json DAG; no independent schedule.
    catchup=False,  # Skip historical scheduled intervals when the DAG is enabled.
) as dag_update:  # Store the DAG object in the variable dag.

    # Define tasks: these calls create tasks; workers execute their bodies later.
    playlist_id = get_playlist_id()  # Find the channel's uploads playlist.
    video_ids = get_video_id(playlist_id)  # Use that playlist to collect video IDs.
    extract_data = extract_video_data(video_ids)  # Fetch metadata and statistics.
    save_to_json_task = save_to_json(extract_data)  # Write the extracted records to JSON.
    update_staging = staging_table()  # Read the JSON and synchronize staging.
    update_core = core_table()  # Transform staging records and synchronize core.

    trigger_update_db = TriggerDagRunOperator(
        task_id="trigger_data_quality",  # Unique task ID within this DAG.
        trigger_dag_id="data_quality",  # Name of the DAG to trigger after this one.
    )

    # Start staging only after JSON saving succeeds; then update core.
    save_to_json_task >> update_staging >> update_core

with DAG(  # Create a DAG; tasks defined inside this block belong to it.
    dag_id="data_quality",  # Name identifying this workflow in Airflow.
    default_args=default_args,  # Apply task defaults from the previously defined dictionary.
    description="DAG to check the data quality on both layers in the db",  # Describe the workflow in Airflow.
    schedule=None, # This DAG is triggered by the update_db DAG; no independent schedule.
    catchup=False,  # Skip creating runs for missed historical schedule intervals.
) as dag_quality:  # Store the DAG object in dag_data_quality.

    # Define tasks
    soda_validate_staging = yt_elt_data_quality(staging_schema)  # Create a Soda task using the staging schema value.
    soda_validate_core = yt_elt_data_quality(core_schema)  # Create a Soda task using the core schema value.

    # Define dependencies
    soda_validate_staging >> soda_validate_core  # Run the core task after the staging task succeeds by default.
