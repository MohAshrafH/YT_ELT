import logging  # Python's built-in tools for recording errors and other messages.
from airflow.operators.bash import BashOperator  # Defines an Airflow task that runs a shell command.

logger = logging.getLogger(__name__)  # Get a logger named after this module; __name__ holds its module name.

SODA_PATH = "/opt/airflow/include/soda"  # Folder inside Airflow containing the Soda configuration and checks.
DATASOURCE = "pg_datasource"  # Data source name defined in Soda's configuration file.


def yt_elt_data_quality(schema):  # Accept the database schema name used for this check.
    try:  # Catch errors raised while creating and returning the task.
        task = BashOperator(  # Create a task definition; Airflow runs its command later.
            task_id=f"soda_test_{schema}",  # Insert the schema into the task's identifier using an f-string.
            # Run Soda checks: -d selects the data source; -c selects its configuration file.
            # -v supplies the SCHEMA variable to the checks; the final path selects the checks file.
            bash_command=f"soda scan -d {DATASOURCE} -c {SODA_PATH}/configuration.yml -v SCHEMA={schema} {SODA_PATH}/checks.yml",
        )
        return task  # Give the caller the configured BashOperator task, not the scan results.
    except Exception as e:  # Catch ordinary errors from this block and store the exception in e.
        logger.error(f"Error running data quality check for schema: {schema}")  # Log which schema was involved.
        raise e  # Pass the caught exception to the caller so the failure remains visible.