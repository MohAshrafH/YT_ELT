import os  # Provides os.environ, the mapping of environment variable names to values.
import pytest  # Provides @pytest.fixture, which registers setup code that tests can request.
from unittest import mock  # Imports mock, whose patch.dict temporarily changes a mapping.
import psycopg2  # Imports the PostgreSQL driver, which provides the connect() function.
# The comma-separated names import three Airflow classes directly.
# Variable reads configuration values, Connection represents connection settings,
# and DagBag loads DAG definitions so tests can inspect them.
from airflow.models import Variable, Connection, DagBag

@pytest.fixture  # The @ decorator registers the function below as a pytest fixture.
def api_key():  # def defines the function. Tests request the fixture by its name.
    # patch.dict resolves "os.environ" by name. NAME=value sets that environment entry.
    # The with block restores the original environment when the fixture exits.
    with mock.patch.dict("os.environ", AIRFLOW_VAR_API_KEY="MOCK_KEY1234"):
        # get() looks up the quoted Airflow variable name. yield gives its value
        # to the test and pauses the fixture until pytest resumes it for cleanup.
        yield Variable.get("API_KEY")

@pytest.fixture  # The @ applies pytest's fixture decorator to the function below.
def channel_handle():  # def defines the function. Tests request it with a channel_handle parameter.
    # patch.dict resolves "os.environ" to the process's environment variables.
    # The NAME=value argument temporarily sets AIRFLOW_VAR_CHANNEL_HANDLE to "MRCHEESE".
    # The with block keeps the patch active during the test and restores it on exit.
    with mock.patch.dict("os.environ", AIRFLOW_VAR_CHANNEL_HANDLE="MRCHEESE"):
        # Variable.get() looks up the Airflow variable named by the quoted argument.
        # yield supplies the value to the test and pauses here until pytest resumes cleanup.
        yield Variable.get("CHANNEL_HANDLE")

@pytest.fixture  # The @ applies pytest's fixture decorator to the function below.
def mock_postgres_conn_vars():  # A test requests this fixture by using its name as a parameter.
    conn = Connection(  # Calling the class creates an Airflow connection object with fake settings.
        login="mock_username",  # The name=value syntax passes the database username by name.
        password="mock_password",  # Supplies the fake password as a string.
        host="mock_host",  # Supplies the fake hostname, which normally identifies the server.
        port=1234,  # The unquoted number passes the server port as an integer.
        schema="mock_db_name",  # schema is the db name
    )
    conn_uri = conn.get_uri()  # The dot accesses a method on conn. Calling it produces a URI string.

    # patch.dict resolves "os.environ" by name and temporarily stores the URI under this key.
    # The with block keeps that entry in place until pytest resumes the fixture for cleanup.
    with mock.patch.dict("os.environ", AIRFLOW_CONN_POSTGRES_DB_YT_ELT=conn_uri):
        # conn_id= names the Airflow connection to look up. AIRFLOW_CONN_ is the environment prefix.
        # yield gives the retrieved Connection object to the test and pauses here.
        yield Connection.get_connection_from_secrets(conn_id="POSTGRES_DB_YT_ELT")

@pytest.fixture()  # @ applies the decorator. Empty parentheses use pytest's default fixture settings.
def dagbag():  # def defines the fixture. A test requests it with a parameter named dagbag.
    # DagBag() loads Airflow DAG definitions using the default settings.
    # yield gives the DagBag object to the test and pauses until pytest finishes the test.
    yield DagBag()

@pytest.fixture()  # The @ decorator registers the function below as a pytest fixture.
def airflow_variable():  # Tests can request this fixture by using its name as a parameter.
    def get_airflow_variable(variable_name):  # Define a helper that takes a variable name as a string.
        # The f-string inserts the result of .upper() after the AIRFLOW_VAR_ prefix.
        env_var = f"AIRFLOW_VAR_{variable_name.upper()}"
        # Pass the full name to os.getenv and return its value as a string, or None if it is unset.
        return os.getenv(env_var)

    return get_airflow_variable  # Give the test the helper itself. Add parentheses to call it.

# Read the PostgreSQL connection settings from environment variables.
@pytest.fixture  # The @ decorator registers this function as a fixture that tests can request by name.
def real_postgres_connection():  # Empty parentheses mean the fixture takes no arguments.
    # os.getenv looks up the name in quotes and returns its value as text, or None if it is unset.
    dbname = os.getenv("ELT_DATABASE_NAME")  # Store the database name.
    user = os.getenv("ELT_DATABASE_USERNAME")  # Store the login username.
    password = os.getenv("ELT_DATABASE_PASSWORD")  # Store the login password.
    host = os.getenv("POSTGRES_CONN_HOST")  # Store the server hostname or IP address.
    port = os.getenv("POSTGRES_CONN_PORT")  # Store the port as text, even if it contains only digits.

    conn = None  # Start with no connection so cleanup can tell if opening it failed.

    try:  # Run this block and handle matching errors in except.
        conn = psycopg2.connect(  # Open the connection and store it in conn.
            # In each name=value pair, the left side names the argument and the right side supplies its value.
            dbname=dbname, user=user, password=password, host=host, port=port
        )

        yield conn  # Give the open connection to the test and pause here until the test finishes.

    except psycopg2.Error as e:  # Catch errors from the PostgreSQL driver and refer to the error as e.
        pytest.fail(f"Failed to connect to the database: {e}")  # Fail the test with the error inserted into the message.

    finally:  # Run cleanup after the test finishes or if setup fails.
        if conn:  # Skip cleanup if conn is still None.
            conn.close()  # Close the connection and release its resources.