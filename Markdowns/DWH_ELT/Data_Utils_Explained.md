# DWH / ELT: PostgreSQL connection helpers

## Quick overview: connection, cursor, and Spark

The **connection represents the PostgreSQL session**. A **cursor is a tool within that session** for executing SQL and fetching results; it is not a separate session. Multiple cursors can share one connection and its transaction.

```python
conn = hook.get_conn()  # Open the database session.
cur = conn.cursor()  # Create a tool for executing SQL.
cur.execute("SELECT * FROM videos")
rows = cur.fetchall()  # Retrieve the query results.
```

As a loose analogy, a `SparkSession` is closer to the connection as an entry point for working with data. A cursor handles the SQL execution/result-retrieval role associated with `spark.sql(...)`, though Spark returns a DataFrame and works differently. The objects are not direct equivalents.

## Purpose and place in the pipeline

**DWH (data warehouse)** stores data organized for analysis and reporting. **ELT** means Extract from a source, Load into a database, then Transform inside that database. ETL instead transforms before loading.

For this project, the intended flow is YouTube API → raw JSON → PostgreSQL staging tables → SQL transformations → reporting tables. The current `produce_json` DAG stops at JSON; the screenshot's helpers prepare database access for later loading and transformation. They do not load data or create tasks by themselves.

## Screenshot code, with concise comments

This preserves the screenshot's logic and identifiers; whitespace is formatted for readability. The code is intended for `dags/datawarehouse/data_utils.py`.

```python
from airflow.providers.postgres.hooks.postgres import PostgresHook  # Airflow's PostgreSQL adapter.
from psycopg2.extras import RealDictCursor  # Fetch rows using column names as keys.


def get_conn_cursor():
    # Read Airflow connection settings; target the elt_db database.
    hook = PostgresHook(postgres_conn_id="postgres_db_yt_elt", database="elt_db")
    conn = hook.get_conn()  # Open a live PostgreSQL session.
    cur = conn.cursor(cursor_factory=RealDictCursor)  # Create a SQL execution/result interface.
    return conn, cur  # Give both objects to the caller.


def close_conn_cursor(conn, cur):
    cur.close()  # Release the cursor.
    conn.close()  # End the session; this does not commit pending writes.
```

## Imports and what a hook is

`from package.module import Class` imports a named class so you can use its short name. Imports make the classes available; these two imports do not open a database connection.

| Import | Meaning and reason |
|---|---|
| `airflow.providers.postgres.hooks.postgres` | The Python module containing Airflow's PostgreSQL hook, supplied by the `apache-airflow-providers-postgres` package. |
| `PostgresHook` | An Airflow integration class that uses an Airflow connection ID to obtain settings and provides PostgreSQL operations, including opening a connection. |
| `psycopg2` | The Python PostgreSQL driver used by this example; it communicates with PostgreSQL. |
| `psycopg2.extras` | Extra driver utilities, including alternative cursor classes. |
| `RealDictCursor` | A cursor class that returns each fetched row as a dictionary-like `RealDictRow`, keyed by column name. |

A **hook** is Airflow's reusable interface to an external system, such as PostgreSQL, S3, or an API. Here, `hook` is an instance of `PostgresHook`. It bridges stored configuration and the database driver; `hook.get_conn()` opens the actual database session. It is neither a database nor a scheduled task. [Airflow PostgresHook reference](https://airflow.apache.org/docs/apache-airflow-providers-postgres/stable/_api/airflow/providers/postgres/hooks/postgres/index.html).

## Connection versus cursor

| Object | Responsibility | Typical operations |
|---|---|---|
| Airflow connection configuration | Saved host, port, login, password, database, and extra settings, identified by `postgres_db_yt_elt`. Configuration is distinct from a live session. | Looked up by the hook. |
| `hook` | Integrates Airflow with PostgreSQL and creates the live connection. | `get_conn()` |
| `conn` | Represents the live database session and controls its transaction. | `cursor()`, `commit()`, `rollback()`, `close()` |
| `cur` | Uses that session to execute SQL and retrieve query results. | `execute()`, `fetchone()`, `fetchall()`, `close()` |

Think of `conn` as an open conversation with PostgreSQL and `cur` as the tool for asking questions and reading answers. One connection can have several cursors; those cursors share its transaction. Closing a cursor leaves the connection open. Closing the connection makes its cursors unusable. [Psycopg connections](https://www.psycopg.org/docs/connection.html), [cursors](https://www.psycopg.org/docs/cursor.html).

## Why `RealDictCursor`?

It makes query results clearer when working with named fields in JSON-like records:

```python
# For: SELECT video_id, view_count FROM some_table
# Default cursor: ("demo_001", 1200) -> row[1]
# RealDictCursor: {"video_id": "demo_001", "view_count": 1200}
views = row["view_count"]
```

`row["view_count"]` explains itself and survives reordering selected columns. `RealDictCursor` changes the **Python result format**, not the SQL, table, or stored data. It is optional: use a default tuple cursor if positional access is sufficient. Dictionary rows add overhead and do not support `row[0]`; `DictCursor` supports both names and positions. In joins, give duplicate column names unique aliases so each result key is unambiguous. [Psycopg dictionary cursors](https://www.psycopg.org/docs/extras.html#real-dictionary-cursor).

## Line-by-line explanation

Line numbers below refer to the original screenshot, before adding comments.

| Line | Code | Explanation |
|---|---|---|
| 1 | `from ... import PostgresHook` | Import Airflow's PostgreSQL integration class. |
| 2 | `from psycopg2.extras import RealDictCursor` | Import the dictionary-result cursor class. |
| 3, 9–10 | Blank lines | Separate imports and functions; no runtime action. |
| 4 | `def get_conn_cursor():` | Define a helper; its body runs only when called. |
| 5 | `hook = PostgresHook(...)` | Create the hook using connection ID `postgres_db_yt_elt`; `database="elt_db"` selects the destination database. The ID is a configuration lookup key, not the database name. |
| 6 | `conn = hook.get_conn()` | Resolve connection settings and open a PostgreSQL session; errors such as invalid credentials surface here. |
| 7 | `cur = conn.cursor(cursor_factory=RealDictCursor)` | Create a cursor on that session. `cursor_factory` receives the class, without `()`, so the driver can instantiate it. No SQL has run yet. |
| 8 | `return conn, cur` | Return a two-item tuple, usually unpacked with `conn, cur = get_conn_cursor()`. |
| 11 | `def close_conn_cursor(conn, cur):` | Define a cleanup helper receiving the previously opened objects. |
| 12 | `cur.close()` | Close the cursor and release its resources. |
| 13 | `conn.close()` | Close the session. Under normal psycopg2 transaction behavior, uncommitted changes are discarded. |

## Apply it: load two videos and calculate total views

**Setup:** copy the helper code above into `dags/datawarehouse/data_utils.py` before trying this example. Run inside the project's Airflow container, where the PostgreSQL provider, psycopg2, and connection configuration must be available. Compose already supplies `AIRFLOW_CONN_POSTGRES_DB_YT_ELT`, which maps to `postgres_db_yt_elt`; the database and user must exist and the user needs table-creation/write permissions. See the [database initialization guide](../Docker/Postgres_Initialization_Script_Explained.md).

The example assumes a psycopg2-backed hook, matching the screenshot. Newer provider environments can use psycopg 3, whose dictionary-row API differs; do not mix that connection with psycopg2's `RealDictCursor`. Check dependencies in the running Airflow environment before changing versions.

Save this example as a separate script under `dags/` and run it there inside the Airflow container. In a DAG, call it inside a task body, so database work happens when the task runs.

```python
from datawarehouse.data_utils import get_conn_cursor, close_conn_cursor

videos = [("demo_001", 1200), ("demo_002", 800)]
conn, cur = get_conn_cursor()
try:
    # Temporary staging table: automatically removed when this session closes.
    cur.execute("""
        CREATE TEMP TABLE demo_video_stage (
            video_id TEXT PRIMARY KEY,
            view_count BIGINT NOT NULL
        )
    """)

    # Load: pass values separately so the driver handles quoting safely.
    cur.executemany(
        "INSERT INTO demo_video_stage (video_id, view_count) VALUES (%s, %s)",
        videos,
    )

    # Transform in PostgreSQL: calculate an aggregate from loaded rows.
    cur.execute("SELECT SUM(view_count) AS total_views FROM demo_video_stage")
    row = cur.fetchone()  # One dictionary-like result row.
    print(row["total_views"])  # Expected: 2000
    conn.commit()  # Complete the transaction successfully.
except Exception:
    conn.rollback()  # Undo this transaction if a database operation fails.
    raise  # Let Airflow detect the failure if running inside a task.
finally:
    close_conn_cursor(conn, cur)  # Clean up on success or failure.
```

This demonstrates loading and SQL transformation using sample extracted records. It does not call YouTube or persist a reporting table. For permanent tables, `commit()` saves writes; `close()` does not replace it. Use `%s` parameters for values instead of f-strings. In an Airflow task, return data if needed, never `conn` or `cur` through XCom.

The screenshot's helpers are deliberately minimal: if cursor creation fails after connecting, the caller never receives the connection; if `cur.close()` raises, `conn.close()` is skipped. Production cleanup should handle those cases with context managers or nested `try/finally`. For psycopg2, `with conn:` manages commit/rollback but does **not** close the connection. [Transaction and context-manager behavior](https://www.psycopg.org/docs/connection.html).
