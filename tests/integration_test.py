import os

import requests # Imports the requests library, which provides functions for making HTTP requests.
import pytest # Imports pytest, which provides the testing framework and fixtures.
import psycopg2

# Check that the YouTube API returns HTTP 200 for the configured channel.
# Pytest finds functions whose names start with test_ and passes in fixtures by parameter name.
def test_youtube_api_response(airflow_variable):
    api_key = airflow_variable("api_key")  # Call the fixture's helper and store the API key.
    channel_handle = airflow_variable("channel_handle")  # Call the same helper for the channel handle.

    # The f-string fills in the {channel_handle} and {api_key} placeholders with their values.
    # The ? starts the URL's query parameters, and & separates them.
    url = f"https://www.googleapis.com/youtube/v3/channels?part=contentDetails&forHandle={channel_handle}&key={api_key}"

    try:  # Run this block and let the except clause handle matching errors.
        response = requests.get(url)  # Send an HTTP GET request to the URL and store the response.
        assert response.status_code == 200  # == checks for HTTP 200 (OK). assert fails the test if the check is false.
    except requests.RequestException as e:  # Catch a Requests error and give it the name e.
        pytest.fail(f"Request to YouTube API failed: {e}")  # Fail the test and insert the error details into the message.

# Check that the PostgreSQL connection can run a simple query and return the expected value.
def test_real_postgres_connection(real_postgres_connection):  # Pytest passes in the connection from the fixture with the same name.
    cursor = None  # Start with no cursor so cleanup can tell if one was created.

    try:  # Run the query and let the except block handle database driver errors.
        cursor = real_postgres_connection.cursor()  # Create a cursor to run SQL and read results.
        cursor.execute("SELECT 1;")  # Run a SQL statement that returns the number 1 in a single row.
        result = cursor.fetchone()  # Read the next row as a tuple, or get None if there is no row.

        assert result[0] == 1  # [0] gets the first column. The test fails if its value differs from 1.

    except psycopg2.Error as e:  # Catch a PostgreSQL driver error and give it the name e.
        pytest.fail(f"Database query failed: {e}")  # Insert the error into the message and fail the test.

    finally:  # Run cleanup whether the test passes or fails.
        if cursor is not None:  # Check that a cursor was created before trying to close it.
            cursor.close()  # Release the cursor's resources.

