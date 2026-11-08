# Import helpers to open/close database resources, create database objects, and retrieve stored video IDs.
from datawarehouse.data_utils import get_conn_cursor, close_conn_cursor, create_schema, create_table, get_video_ids

# Import the function used to load input data for processing.
from datawarehouse.data_loading import load_data

# Import functions that insert, update, and delete video records in the database.
from datawarehouse.data_modification import insert_rows, update_rows, delete_rows

# Import the function that converts a row's duration and assigns its video type.
from datawarehouse.data_transformation import transform_data

import logging

logger = logging.getLogger(__name__)  # Use this module's name to identify its log messages.
table = "yt_api"  # Store the table name; this variable is not directly used in the function shown.


@task  # Airflow decorator: calling this function creates a task in a DAG.
def staging_table():  # Synchronize the staging table with the loaded video records.
    schema = 'staging'  # Name the database schema passed to the helper functions.

    conn, cur = None, None  # Start without a database connection or cursor; a cursor executes SQL.

    try:  # Attempt the database work; handle failures and cleanup below.
        conn, cur = get_conn_cursor()  # Unpack the helper's connection and cursor into two variables.

        YT_data = load_data()  # Get the records parsed from today's JSON file.

        create_schema(schema)  # Create the schema if missing; keep an existing one unchanged.
        create_table(schema)  # Create the table in this schema if missing; keep existing columns and data.

        table_ids = get_video_ids(cur, schema)  # Fetch existing video IDs using the cursor and schema.

        for row in YT_data:  # Process each loaded video record.
            if len(table_ids) == 0:  # Run when the fetched collection contains no existing IDs.
                insert_rows(cur, conn, schema, row)  # Pass the cursor, connection, schema, and record to the insert helper.

            else:  # Run when at least one existing ID was fetched.
                if row['video_id'] in table_ids:  # Read the record's video_id key and check whether it already exists.
                    update_rows(cur, conn, schema, row)  # Pass this record and database details to the update helper.
                else:  # Run when this video's ID was not among the fetched IDs.
                    insert_rows(cur, conn, schema, row)  # Insert the new record using the supplied database details.

        ids_in_json = {row['video_id'] for row in YT_data}  # Set comprehension: collect unique IDs from the loaded records.

        ids_to_delete = set(table_ids) - ids_in_json  # Set difference: find database IDs absent from the loaded data.

        if ids_to_delete:  # Run only when the set contains at least one ID.
            delete_rows(cur, conn, schema, ids_to_delete)  # Pass the missing IDs and database details to the delete helper.

        logger.info(f"{schema} table update completed")  # Log success, inserting the schema name into the message.

    except Exception as e:  # Catch failures derived from Exception and store the exception in e.
        logger.error(f"An error occurred during the update of {schema} table: {e}")  # Log the schema and error details.
        raise e  # Pass the caught exception to the caller; this raise also adds a traceback entry.

    finally:  # Run cleanup whether the work succeeds or raises an exception.
        if conn and cur:  # Clean up only when both objects evaluate as true.
            close_conn_cursor(conn, cur)  # Ask the helper to close the connection and cursor.

    # Without an explicit return, successful completion gives the caller None.

def core_table():  # Synchronize the core table with transformed staging records.
    schema = 'core'  # Target database schema for inserts, updates, and deletions.

    conn, cur = None, None  # Initialize the connection and SQL cursor before attempting to connect.

    try:  # Attempt the database work; catch failures in the except block.
        conn, cur = get_conn_cursor()  # Unpack the helper's database connection and cursor.

        create_schema(schema)  # Create the core schema if missing; keep an existing one unchanged.
        create_table(schema)  # Create its table if missing; preserve existing columns and data.

        table_ids = get_video_ids(cur, schema)  # Fetch the video IDs already stored in core.

        current_video_ids = set()  # Start an empty set to collect unique staging video IDs.

        cur.execute(f"SELECT * FROM staging.{table};")  # Read all columns; insert the table name into the SQL string.
        rows = cur.fetchall()  # Retrieve all query results for processing.

        for row in rows:  # Process each staging record.
            current_video_ids.add(row["Video_ID"])  # Track this ID; adding a duplicate leaves the set unchanged.

            if len(table_ids) == 0:  # Run if core had no video IDs when they were fetched.
                transformed_row = transform_data(row)  # Convert the staging record into the format expected by core.
                insert_rows(cur, conn, schema, transformed_row)  # Insert the converted record using the database helpers.

            else:  # Run if core already contained video IDs.
                transformed_row = transform_data(row)  # Prepare this staging record for storage in core.

                if transformed_row["Video_ID"] in table_ids:  # Check whether the converted record's ID already exists.
                    update_rows(cur, conn, schema, transformed_row)  # Update the matching core record.

                else:  # Run when the converted record's ID was absent from the fetched core IDs.
                    insert_rows(cur, conn, schema, transformed_row)  # Add the new video record to core.

        ids_to_delete = set(table_ids) - current_video_ids  # Find core IDs that were absent from staging.

        if ids_to_delete:  # Run only when at least one ID needs removal.
            delete_rows(cur, conn, schema, ids_to_delete)  # Delete core records matching these IDs.

        logger.info(f"{schema} table update completed")  # Log success; the f-string inserts the schema name.

    except Exception as e:  # Catch failures derived from Exception and name the caught error e.
        # Log any exceptions that occur
        logger.error(f"An error occurred during the update of {schema} table: {e}")  # Record the target schema and error.
        raise e  # Pass the caught error to the caller; this raise adds a traceback entry.

    # Successful completion implicitly returns None.