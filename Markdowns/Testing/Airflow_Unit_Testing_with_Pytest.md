# Airflow Unit Testing with pytest

[Udemy lecture 52043863](https://www.udemy.com/course/start-your-data-engineering-journey-project-based-learning/learn/lecture/52043863#notes) covers testing Python code in isolation, mocking Airflow settings, and checking DAG structure before running the ELT pipeline.

| Test level | What it checks | YT_ELT example |
| --- | --- | --- |
| Unit | One function or behavior in isolation, with fake inputs or mocked dependencies | Read a fake API key from an Airflow Variable |
| Integration | Components working together, with mocked or live dependencies depending on the test | Use real test credentials to connect to PostgreSQL and query a test table |
| End-to-end | The full workflow with valid credentials for the services it uses | Run the ELT workflow from YouTube extraction through PostgreSQL loading and verify the resulting rows |

## Fixtures and test discovery

Put reusable setup in `tests/conftest.py`. Decorate each fixture with `@pytest.fixture`, then request it by name in a test function’s arguments. By default, pytest discovers `test_*.py` and `*_test.py` files and functions beginning with `test_`. The lecture uses `tests/unit_test.py`. [pytest discovery rules](https://docs.pytest.org/en/stable/explanation/goodpractices.html)

## Mock Airflow Variables and the PostgreSQL connection

In `tests/conftest.py`, `mock.patch.dict` temporarily changes `os.environ`. `yield` keeps the patch active while the test runs, and exiting the `with` block restores the environment. Airflow looks up Variables through `AIRFLOW_VAR_<KEY>` and Connections through `AIRFLOW_CONN_<CONN_ID>`, using uppercase environment names. `Connection.get_uri()` serializes the fake settings for Airflow’s secrets lookup. For this PostgreSQL connection, `schema` holds the database name. [Airflow mocking examples](https://airflow.apache.org/docs/apache-airflow/2.10.2/best-practices.html#mocking-variables-and-connections)

```python
# tests/conftest.py
import os
from unittest import mock

import pytest
from airflow.models import Connection, DagBag, Variable


@pytest.fixture
def api_key():
    with mock.patch.dict(os.environ, AIRFLOW_VAR_API_KEY="mock_key1234"):
        yield Variable.get("API_KEY")


@pytest.fixture
def channel_handle():
    with mock.patch.dict(os.environ, AIRFLOW_VAR_CHANNEL_HANDLE="@MrCheese"):
        yield Variable.get("CHANNEL_HANDLE")


@pytest.fixture
def mock_postgres_conn():
    conn = Connection(
        conn_type="postgres", host="mock-postgres", port=5432,
        login="test_user", password="test_password", schema="elt_db",
    )
    with mock.patch.dict(os.environ, AIRFLOW_CONN_POSTGRES_DB_YT_ELT=conn.get_uri()):
        yield Connection.get_connection_from_secrets("postgres_db_yt_elt")


@pytest.fixture
def dagbag(api_key, channel_handle):
    return DagBag(dag_folder="dags/main.py", include_examples=False)
```

The fake channel replaces the lecture’s MrBeast example. The fixture uses this checkout’s `postgres_db_yt_elt` connection ID. The lecture uses `postgres_db_youtube_elt`. The connection test verifies the resolved settings without opening a database session. [Project connection code](../../dags/datawarehouse/data_utils.py)

```python
# tests/unit_test.py
def test_api_key(api_key):
    assert api_key == "mock_key1234"


def test_channel_handle(channel_handle):
    assert channel_handle == "@MrCheese"


def test_postgres_conn(mock_postgres_conn):
    conn = mock_postgres_conn
    assert conn.conn_type == "postgres"
    assert (conn.host, conn.port) == ("mock-postgres", 5432)
    assert (conn.login, conn.password, conn.schema) == ("test_user", "test_password", "elt_db")
```

## Check DAG integrity

`DagBag` parses DAG definitions and exposes loaded DAGs and import errors. This fixture requests the two Variable fixtures because `video_stats.py` reads them during import. The four checks cover import errors, expected IDs, total DAG count, and task count per DAG. This checkout defines `update_db` with six tasks and `data_quality` with two. [Current DAG definitions](../../dags/main.py)

```python
# Append to tests/unit_test.py
def test_dag_integrity(dagbag):
    assert dagbag.import_errors == {}, f"DAG import errors: {dagbag.import_errors}"

    expected_counts = {"update_db": 6, "data_quality": 2}
    print(f"Loaded {len(dagbag.dags)} DAGs: {sorted(dagbag.dags)}")
    for dag_id in expected_counts:
        assert dag_id in dagbag.dags, f"Missing DAG: {dag_id}"
    assert len(dagbag.dags) == len(expected_counts)

    for dag_id, expected in expected_counts.items():
        actual = len(dagbag.dags[dag_id].tasks)
        print(f"{dag_id}: {actual} tasks")
        assert actual == expected, f"{dag_id}: expected {expected} tasks, found {actual}"
```

The lecture loads three DAGs and expects four tasks in `produce_json`. Changing its expected count to `3` deliberately fails the assertion, with a message such as `produce_json: expected 3 tasks, found 4`. Restore the expected count to `4` after the demonstration.

## Run in the Airflow worker

After adding the examples to the test files, run these commands inside the YT_ELT Airflow worker. The directory is `tests/` (plural).

```bash
cd /opt/airflow
pytest -v tests/unit_test.py
pytest -v tests/unit_test.py -k test_channel_handle
pytest -v -s tests/unit_test.py -k test_dag_integrity
```

`-v` shows each test and its result. `-k` filters by name expression and reports other collected tests as deselected. `-s` turns off output capture so the DAG debug prints appear during the run. The lecture runs the tests successfully, demonstrates the deliberate failure, then moves on to integration testing. [pytest invocation](https://docs.pytest.org/en/stable/how-to/usage.html) · [Output capture](https://docs.pytest.org/en/stable/how-to/capture-stdout-stderr.html)
