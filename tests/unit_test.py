# pytest discovers functions starting with test_ and fills api_key from the fixture of the same name.
def test_api_key(api_key):
    # == compares the two values. assert fails the test if they differ.
    assert api_key == "MOCK_KEY1234"

# def defines the test function. The test_ prefix tells pytest it's a test.
# The channel_handle parameter asks pytest to supply the fixture's yielded value.
def test_channel_handle(channel_handle):
    # == compares the fixture value with the expected string. assert fails if they differ.
    assert channel_handle == "MRCHEESE"

# The test_ prefix marks this as a pytest test. The parameter name asks pytest
# to run the matching fixture and pass in the Airflow Connection object it yields.
def test_postgres_conn(mock_postgres_conn_vars):
    conn = mock_postgres_conn_vars  # Gives the same connection object a shorter local name.
    # The dot reads an attribute, == compares values, and assert fails if they differ.
    assert conn.login == "mock_username"  # The login attribute holds the database username.
    assert conn.password == "mock_password"  # Checks that the fake password survived the URI round trip.
    assert conn.host == "mock_host"  # Checks the hostname Airflow read from the connection URI.
    assert conn.port == 1234  # The unquoted number checks the port as an integer.
    assert conn.schema == "mock_db_name"  # For this connection, schema holds the database name.

# pytest discovers the test_ function and supplies the matching dagbag fixture.
def test_dags_integrity(dagbag):
    # 1.
    # {} is an empty dictionary. If there are import errors, the f-string
    # inserts the error dictionary into the assertion failure message.
    assert dagbag.import_errors == {}, f"Import errors found: {dagbag.import_errors}"
    print("-----------")  # Separates this check's output from the next one.
    print(dagbag.import_errors)  # Prints the error dictionary if the assertion passes.

    # 2.
    expected_dag_ids = ["produce_json", "update_db", "data_quality"]  # Lists the required DAG IDs.
    loaded_dag_ids = list(dagbag.dags.keys())  # keys() gives the loaded IDs. list() collects them.
    print("-----------")  # Starts the output for the DAG ID check.
    print(dagbag.dags.keys())  # Prints the dictionary's view of the loaded IDs.

    for dag_id in expected_dag_ids:  # Loops through the required IDs one at a time.
        assert dag_id in loaded_dag_ids, f"DAG {dag_id} is missing."  # in checks list membership.

    # 3.
    assert dagbag.size() == 3  # size() counts the loaded DAGs. == checks for exactly three.
    print("-----------")  # Starts the output for the DAG count check.
    print(dagbag.size())  # Prints the count after the assertion passes.

    # 4.
    expected_task_counts = {  # Each key: value pair maps a DAG ID to its expected task count.
        "produce_json": 5,  # Includes trigger_update_db.
        "update_db": 7,  # Includes trigger_data_quality.
        "data_quality": 2,  # Expects two tasks in data_quality.
    }
    print("-----------")  # Starts the output for the per-DAG task counts.
    for dag_id, dag in dagbag.dags.items():  # items() gives pairs, unpacked into an ID and a DAG.
        expected_count = expected_task_counts[dag_id]  # Square brackets look up the count by ID.
        actual_count = len(dag.tasks)  # len() counts the tasks on this DAG.
        # Parentheses let the comparison span lines. The f-string reports both counts on failure.
        assert (
            expected_count == actual_count
        ), f"DAG {dag_id} has {actual_count} tasks, expected {expected_count}."
        print(dag_id, len(dag.tasks))  # Prints the ID and task count separated by a space.
