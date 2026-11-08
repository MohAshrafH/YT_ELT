# Understanding `dwh.py`

## 1. Overview

`dags/datawarehouse/dwh.py` coordinates two database synchronization steps:

```text
Today's JSON file → staging.yt_api → transformation → core.yt_api
                    staging_table()                  core_table()
```

- **Staging** keeps incoming YouTube records, including duration text such as `PT45S`.
- **Core** receives transformed records: duration becomes a clock-time value, and `Video_Type` is added.
- Both functions insert new IDs, update existing IDs, and delete target IDs missing from their source.

These functions take **no explicit arguments**. Their inputs come from files, database queries, and module settings. Their useful outputs are **database changes and logs**; successful execution returns `None`.

**Current execution status:** the file and helpers contain blockers listed in section 7. The worked examples show the intended successful flow after those blockers are corrected, not a verified database run. This guide does not modify Python code.

## 2. Names, inputs, and helper contracts

| Name | Meaning / example |
|---|---|
| `schema` | Database namespace: `'staging'` or `'core'`. |
| `table` | Table name `'yt_api'`; `schema.table` identifies a table. |
| `conn` | Database connection; manages the session and transaction. |
| `cur` | Cursor; executes SQL and fetches results. |
| `row` | One dictionary-like video record. Its keys depend on the source. |
| `table_ids` | List of target IDs fetched **before** the loop; not refreshed after inserts. |

The imported helpers supply the following behavior:

| Helper and input | Return value | Effect / important detail |
|---|---|---|
| `get_conn_cursor()` | `(conn, cur)` | Opens `elt_db` through Airflow connection `postgres_db_yt_elt`; uses `RealDictCursor` for named fields. |
| `close_conn_cursor(conn, cur)` | `None` | Closes cursor, then connection; does not commit. |
| `load_data()` | Parsed JSON, expected here to be a list of dictionaries | Reads `./data/YT_data_<today>.json` as UTF-8; path is relative to the process working directory. |
| `create_schema(schema)` | `None` | Executes `CREATE SCHEMA IF NOT EXISTS`; commits using its own connection. |
| `create_table(schema)` | `None` | Creates the schema's table if absent; commits using its own connection. Existing columns are not migrated. |
| `get_video_ids(cur, schema)` | List such as `['A0000000001', 'C0000000003']` | Selects `Video_ID` from the target table. |
| `insert_rows(cur, conn, schema, row)` | `None` | Inserts one record and commits. Dictionary keys supply SQL parameter values. |
| `update_rows(cur, conn, schema, row)` | `None` | Updates title and counts where **ID and upload date** match; commits. Does not update duration or type. |
| `delete_rows(cur, conn, schema, ids)` | `None` | Deletes matching IDs and commits. |
| `transform_data(row)` | The **same dictionary**, modified | Parses duration, replaces `Duration`, and adds `Video_Type`: `Shorts` for ≤60 seconds, otherwise `Normal`. |

`None` means “no explicit result.” A function can still write to a database even when its return value is `None`.

## 3. Module setup, line by line

Line numbers refer to the current `dwh.py`. Blank lines and existing explanatory comments are omitted. Each row below covers an executable line.

| Line | Code / name | Purpose and syntax |
|---|---|---|
| 2 | `from datawarehouse.data_utils import ...` | Imports five named helpers from that module so they can be called directly. |
| 5 | `from datawarehouse.data_loading import load_data` | Imports the JSON loader. |
| 8 | `from datawarehouse.data_modification import ...` | Imports the insert, update, and delete helpers. |
| 11 | `from datawarehouse.data_transformation import transform_data` | Imports the staging-to-core row converter. |
| 13 | `import logging` | Makes Python's logging module available. |
| 15 | `logger = logging.getLogger(__name__)` | Gets a logger named for this module. `__name__` is normally `datawarehouse.dwh`, or `'__main__'` when executed directly. |
| 16 | `table = "yt_api"` | Stores the table name used by the core query on line 79. This name does not automatically become visible inside imported helpers. |

Python indentation defines blocks. A trailing `:` starts a function or control-flow block; indented lines belong to it.

## 4. `staging_table()`, line by line

**Input:** today's JSON records plus existing staging rows. **Output:** synchronized staging data, logs, and `None` on success.

### Setup and source loading

| Line | Code | Explanation |
|---|---|---|
| 19 | `@task` | Intended Airflow TaskFlow decorator. Calling a decorated function while building a DAG creates a task reference; Airflow later executes its body. Currently `task` is not imported. |
| 20 | `def staging_table():` | Defines a function with no parameters. |
| 21 | `schema = 'staging'` | Selects staging as the target namespace. |
| 23 | `conn, cur = None, None` | Initializes both names before connection attempts; avoids undefined names in cleanup. |
| 25 | `try:` | Starts work whose failures will be caught below. |
| 26 | `conn, cur = get_conn_cursor()` | Unpacks the returned pair into connection and cursor. |
| 28 | `YT_data = load_data()` | Stores the parsed JSON; expects iterable records with keys such as `video_id`. |
| 30 | `create_schema(schema)` | Creates staging if absent; preserves an existing schema. |
| 31 | `create_table(schema)` | Creates its table if absent; leaves existing structure and data unchanged. |
| 33 | `table_ids = get_video_ids(cur, schema)` | Saves the initial staging ID list for membership checks and later deletion. |

### Insert, update, and delete decisions

| Line | Code | Explanation |
|---|---|---|
| 35 | `for row in YT_data:` | Assigns each incoming dictionary to `row`, one at a time. |
| 36 | `if len(table_ids) == 0:` | Tests whether the initial ID list is empty; `len` counts its elements and `==` compares values. |
| 37 | `insert_rows(cur, conn, schema, row)` | Inserts the current source record; the four positional arguments supply cursor, connection, target schema, and values. |
| 39 | `else:` | Runs when the initial target was not empty. |
| 40 | `if row['video_id'] in table_ids:` | Reads a dictionary key with `[]`; `in` checks whether that ID was already stored. |
| 41 | `update_rows(cur, conn, schema, row)` | Sends an existing record to the update helper. |
| 42 | `else:` | Handles an ID absent from the initial target list. |
| 43 | `insert_rows(cur, conn, schema, row)` | Sends a new record to the insert helper. |
| 45 | `ids_in_json = {row['video_id'] for row in YT_data}` | Set comprehension: collects distinct source IDs. This is a second pass over the loaded list. |
| 47 | `ids_to_delete = set(table_ids) - ids_in_json` | Converts target IDs to a set; subtraction keeps only IDs absent from the source. |
| 49 | `if ids_to_delete:` | A nonempty set is true; an empty set skips deletion. |
| 50 | `delete_rows(cur, conn, schema, ids_to_delete)` | Deletes target records matching the computed IDs. |

### Completion, errors, and cleanup

| Line | Code | Explanation |
|---|---|---|
| 52 | `logger.info(f"{schema} table update completed")` | Records completion; an `f`-string substitutes the value inside `{}`. |
| 54 | `except Exception as e:` | Catches failures derived from `Exception` in the try block; `e` holds the error object. |
| 55 | `logger.error(...)` | Records the schema and error text; logging alone does not propagate the failure. |
| 56 | `raise e` | Raises the caught error to the caller/task runner, adding this raise location to the traceback. |
| 58 | `finally:` | Runs after the try/except path, including when an error is raised. |
| 59 | `if conn and cur:` | Calls cleanup only when both values evaluate as true. |
| 60 | `close_conn_cursor(conn, cur)` | Releases the cursor and connection. |

There is no explicit `return`: the body returns `None` on success. A normal failure propagates after cleanup; a cleanup failure can itself become the raised error.

## 5. `core_table()`, line by line

**Input:** staging rows plus existing core rows. **Output:** transformed core data, logs, and `None` on success.

### Read staging and prepare the target

| Line | Code | Explanation |
|---|---|---|
| 64 | `def core_table():` | Defines an ordinary Python function with no parameters; no `@task` decorator is present here. |
| 65 | `schema = 'core'` | Selects core as the destination. |
| 67 | `conn, cur = None, None` | Initializes database-resource names. |
| 69 | `try:` | Starts work covered by the error handler. |
| 70 | `conn, cur = get_conn_cursor()` | Opens a connection and dictionary-row cursor. |
| 72 | `create_schema(schema)` | Creates core only if missing. |
| 73 | `create_table(schema)` | Creates the core table only if missing. |
| 75 | `table_ids = get_video_ids(cur, schema)` | Gets the initial **core** IDs. |
| 77 | `current_video_ids = set()` | Creates an empty set for IDs observed in staging. `{}` would create an empty dictionary instead. |
| 79 | `cur.execute(f"SELECT * FROM staging.{table};")` | Sends `SELECT * FROM staging.yt_api;` to the database; `*` selects all columns. Source schema remains staging even though the target is core. |
| 80 | `rows = cur.fetchall()` | Fetches the query results as a list of dictionary-like rows. |

### Transform and synchronize

| Line | Code | Explanation |
|---|---|---|
| 82 | `for row in rows:` | Processes each fetched staging row. |
| 83 | `current_video_ids.add(row["Video_ID"])` | Adds its ID to the source-ID set; repeated IDs do not create duplicate set elements. |
| 85 | `if len(table_ids) == 0:` | Checks whether core was initially empty. |
| 86 | `transformed_row = transform_data(row)` | Converts duration and adds type; the returned object is the same modified row. |
| 87 | `insert_rows(cur, conn, schema, transformed_row)` | Inserts converted values into core. |
| 89 | `else:` | Handles a core table that initially contained IDs. |
| 90 | `transformed_row = transform_data(row)` | Applies the same conversion before choosing update or insert. |
| 92 | `if transformed_row["Video_ID"] in table_ids:` | Tests the converted record's ID against the initial core ID list. |
| 93 | `update_rows(cur, conn, schema, transformed_row)` | Updates matching core title/counts; the helper does not write the transformed duration/type. |
| 95 | `else:` | Handles IDs not initially present in core. |
| 96 | `insert_rows(cur, conn, schema, transformed_row)` | Inserts the complete new core record, including duration/type. |
| 98 | `ids_to_delete = set(table_ids) - current_video_ids` | Finds initial core IDs absent from staging. |
| 100 | `if ids_to_delete:` | Skips deletion if the difference set is empty. |
| 101 | `delete_rows(cur, conn, schema, ids_to_delete)` | Deletes obsolete core records. |
| 103 | `logger.info(...)` | Records `core table update completed`. |
| 105 | `except Exception as e:` | Captures a failure from the try block. |
| 107 | `logger.error(...)` | Records the core schema and error description. |
| 108 | `raise e` | Propagates the failure to the caller. |

Success implicitly returns `None`. Unlike staging, this function has **no `finally` cleanup**. Neither function is called or connected into a DAG inside this file.

## 6. Worked database trace

Use three valid-length example IDs throughout:

```text
A = A0000000001    B = B0000000002    C = C0000000003
```

Tables below abbreviate IDs as A/B/C. All records share upload date `2026-11-01 12:00:00`; this ensures the update helper's date condition matches. Likes/comments are valid values carried through but omitted for readability. These are illustrative values, not production data.

### A. `staging_table()`: JSON → staging

**Input file**, shown as a table of JSON dictionary fields:

| `video_id` | `title` | `publishedAt` | `duration` | `viewCount` |
|---|---|---|---|---|
| A | Intro revised | 2026-11-01T12:00:00 | PT45S | 120 |
| B | SQL lesson | 2026-11-01T12:00:00 | PT5M | 80 |

**Staging before:**

| `Video_ID` | `Video_Title` | `Duration` | `Video_Views` |
|---|---|---|---|
| A | Intro | PT45S | 100 |
| C | Removed video | PT2M | 20 |

| Step | Values passed / produced | Database effect |
|---|---|---|
| Connect and load | `get_conn_cursor()` → `(conn, cur)`; `load_data()` → `[A_record, B_record]` | Reads source file. |
| Prepare | `create_schema('staging')`; `create_table('staging')` | Existing objects remain. |
| Fetch IDs | `get_video_ids(cur, 'staging')` → `[A, C]` | Reads initial staging IDs. |
| Process A | `A in [A, C]` → `True`; `update_rows(cur, conn, 'staging', A_record)` | Updates A's title and counts; commits. |
| Process B | `B in [A, C]` → `False`; `insert_rows(cur, conn, 'staging', B_record)` | Inserts B; commits. |
| Compare IDs | `ids_in_json = {A, B}`; `{A, C} - {A, B} = {C}` | Computes obsolete IDs in memory. |
| Delete | `delete_rows(cur, conn, 'staging', {C})` | Deletes C; commits. |
| Finish | Log success; `close_conn_cursor(conn, cur)` | Releases resources; body returns `None`. |

**Staging after, and the input to the core function:**

| `Video_ID` | `Video_Title` | `Duration` | `Video_Views` |
|---|---|---|---|
| A | Intro revised | PT45S | 120 |
| B | SQL lesson | PT5M | 80 |

The staging insert maps JSON keys to database columns, for example `video_id` → `Video_ID`, `title` → `Video_Title`, and `viewCount` → `Video_Views` (subject to the column-name blocker below).

### B. `core_table()`: staging → core

**Core before:**

| `Video_ID` | `Video_Title` | `Duration` | `Video_Type` | `Video_Views` |
|---|---|---|---|---|
| A | Intro | 00:00:45 | Shorts | 90 |
| C | Removed video | 00:02:00 | Normal | 15 |

| Step | Values passed / produced | Database effect |
|---|---|---|
| Prepare | Connect; create core schema/table if missing | Existing objects remain. |
| Fetch IDs | `get_video_ids(cur, 'core')` → `[A, C]` | Reads initial core IDs. |
| Read source | `SELECT * FROM staging.yt_api;` → rows A and B | Uses staging output above. |
| Process A | Add A to set; `transform_data(A_row)` → duration `00:00:45`, type `Shorts` | Transformation changes the in-memory dictionary. |
| Write A | `A in [A, C]` → `True`; `update_rows(cur, conn, 'core', transformed_row)` | Updates title/counts; commits. |
| Process B | Add B to set; `transform_data(B_row)` → duration `00:05:00`, type `Normal` | Prepares a new core record. |
| Write B | `B in [A, C]` → `False`; `insert_rows(cur, conn, 'core', transformed_row)` | Inserts B including duration/type; commits. |
| Compare IDs | `current_video_ids = {A, B}`; `{A, C} - {A, B} = {C}` | Identifies obsolete core row C. |
| Delete and finish | `delete_rows(cur, conn, 'core', {C})`; log success | Deletes C; commits; returns `None` without explicit cleanup. |

Inside `transform_data`, B passes through these values:

```text
row['Duration'] = 'PT5M'
  → parse_duration('PT5M') → timedelta(minutes=5)
  → (datetime.min + duration_td).time() → time(0, 5)
  → duration_td.total_seconds() = 300
  → 300 <= 60 is False → row['Video_Type'] = 'Normal'
  → return the modified row
```

**Core after:**

| `Video_ID` | `Video_Title` | `Duration` | `Video_Type` | `Video_Views` |
|---|---|---|---|---|
| A | Intro revised | 00:00:45 | Shorts | 120 |
| B | SQL lesson | 00:05:00 | Normal | 80 |

### C. Other branches and failures

| Situation | Trace / result |
|---|---|
| Target initially empty | `table_ids = []` → `len(...) == 0` stays true for every source row → insert each row; nothing to delete. |
| Source successfully loads zero records | Source-ID set is empty → every initial target ID enters `ids_to_delete` → all target rows are deleted. The code treats the source as a complete snapshot. |
| File missing or invalid JSON | `load_data()` logs and raises → staging handler logs and raises → `finally` closes acquired resources. No row writes have occurred yet. |
| A later write fails | Earlier helper commits remain saved. The function raises; the entire synchronization is not one atomic transaction. Core has no explicit cleanup. |
| Existing ID has a different upload date | Update branch is selected by ID, but SQL's ID-and-date condition may match zero rows; the helper still commits and logs success. |

## 7. Current blockers and limits

These findings come from the checked-in helper implementations, not from executing the examples against a database.

| Location | Current behavior / consequence |
|---|---|
| `dwh.py`: `@task` | `task` is not imported. Module loading stops with `NameError` before either function can run normally. |
| `data_utils.py`: `create_table`, `get_video_ids` | Both reference `table`, but this module does not define/import it. `dwh.py`'s variable does not fill that gap. |
| `data_modification.py`: staging insert | SQL uses spaced column names such as `"Video ID"`; table creation uses `"Video_ID"`. Against the declared schema, insertion fails. |
| `data_transformation.py`: `parse_duration` | `timedelta(..., secondsays=...)` uses an invalid keyword; duration conversion raises `TypeError`. The intended keyword is `seconds`. |
| `core_table()` | No decorator, DAG dependency, invocation, or connection cleanup is supplied here. Running staging before core needs orchestration elsewhere. |
| `update_rows()` | Only title and counts are updated. Existing duration/type remain unchanged even when a transformed row contains new values. |
| Duration representation | Core stores `TIME`, a time of day; `.time()` drops elapsed days. Durations of 24 hours or more lose that information. |
| Initial ID snapshot | Newly inserted IDs are not appended to `table_ids`. Duplicate new IDs in a source can attempt duplicate inserts and fail the primary key constraint. |

The `Shorts` threshold is the rule implemented in this project. Schema creation preserves existing objects; it does not fix any incompatible table definition already present.

## 8. Source map

- [`dwh.py`](../dags/datawarehouse/dwh.py): orchestration explained here.
- [`data_loading.py`](../dags/datawarehouse/data_loading.py): dated JSON loading.
- [`data_utils.py`](../dags/datawarehouse/data_utils.py): connections, creation, and ID lookup.
- [`data_modification.py`](../dags/datawarehouse/data_modification.py): SQL writes and commits.
- [`data_transformation.py`](../dags/datawarehouse/data_transformation.py): duration conversion and classification.
