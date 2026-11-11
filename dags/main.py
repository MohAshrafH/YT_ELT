# DAG groups tasks; Pendulum supplies timezone rules; datetime/timedelta set timing.
from airflow import DAG
import pendulum
from datetime import datetime, timedelta
from datawarehouse.dwh import staging_table, core_table  # Import the functions that create the DAG's tasks. 
from airflow.decorators import task  # Turn decorated functions into Airflow tasks.

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

with DAG(  # Create the workflow; tasks defined inside this block belong to it.
    dag_id="update_db",  # Unique workflow ID shown in Airflow's UI and CLI.
    default_args=default_args,  # Apply shared task settings from the existing dictionary.
    description="DAG to process JSON file and insert data into both staging and core schemas",  # UI summary.
    schedule="0 15 * * *",  # Run daily at 15:00 in the DAG's timezone, after its data interval ends.
    catchup=False,  # Skip historical scheduled intervals when the DAG is enabled.
) as dag:  # Store the DAG object in the variable dag.

    # Define tasks: these calls create tasks; workers execute their bodies later.
    playlist_id = get_playlist_id()  # Find the channel's uploads playlist.
    video_ids = get_video_id(playlist_id)  # Use that playlist to collect video IDs.
    extract_data = extract_video_data(video_ids)  # Fetch metadata and statistics.
    save_to_json_task = save_to_json(extract_data)  # Write the extracted records to JSON.
    update_staging = staging_table()  # Read the JSON and synchronize staging.
    update_core = core_table()  # Transform staging records and synchronize core.

    # Start staging only after JSON saving succeeds; then update core.
    save_to_json_task >> update_staging >> update_core

    with DAG(  # Create a DAG; tasks defined inside this block belong to it.
    dag_id="data_quality",  # Name identifying this workflow in Airflow.
    default_args=default_args,  # Apply task defaults from the previously defined dictionary.
    description="DAG to check the data quality on both layers in the db",  # Describe the workflow in Airflow.
    schedule="0 16 * * *",  # Run daily at 16:00 in the DAG's timezone (minute, hour, day, month, weekday).
    catchup=False,  # Skip creating runs for missed historical schedule intervals.
    ) as dag_update:  # Store the DAG object in dag_update.

        # Define tasks
        soda_validate_staging = yt_elt_data_quality(staging_schema)  # Create a Soda task using the staging schema value.
        soda_validate_core = yt_elt_data_quality(core_schema)  # Create a Soda task using the core schema value.

        # Define dependencies
        soda_validate_staging >> soda_validate_core  # Run the core task after the staging task succeeds by default.