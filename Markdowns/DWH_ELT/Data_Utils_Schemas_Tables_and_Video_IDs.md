# Data utils: schemas, tables, and video IDs

Companion to [the connection helpers guide](Data_Utils_Explained.md). This explains the additions in `dags/datawarehouse/data_utils.py`: `create_schema`, `create_table`, and `get_video_ids`.

## Brief conceptual and functional overview

Within the `elt_db` database, a **schema** is a namespace that groups tables. A **table** defines columns and stores rows. A qualified name such as `staging.video_stats` identifies both the schema and the table.

```text
elt_db
├── staging
│   └── video_stats    ← raw video records
└── core
    └── video_stats    ← cleaned video records
```

The table name `video_stats` is an example, not a value currently configured in the utilities file.

| Function | What it does | What it returns |
|---|---|---|
| `create_schema(schema)` | Creates a namespace if absent. | `None` implicitly. |
| `create_table(schema)` | Creates the table and its column definitions if absent. | `None` implicitly. |
| `get_video_ids(cur, schema)` | Reads IDs already stored in a table. | A Python list of ID strings. |

The creation functions prepare storage; they do not insert videos, transform durations, or move records from staging to core. `get_video_ids` queries PostgreSQL, unlike `get_video_id` in `dags/api/video_stats.py`, which discovers IDs through YouTube's API.

## 1. Creating a schema, line by line

```python
def create_schema(schema):  # Receive the schema name.
    conn, cur = get_conn_cursor()  # Open a session and cursor.
    schema_sql = f"CREATE SCHEMA IF NOT EXISTS {schema};"  # Build SQL.
    cur.execute(schema_sql)  # Ask PostgreSQL to create it.
    conn.commit()  # Save the database change.
    close_conn_cursor(conn, cur)  # Release both resources.
```

1. `def create_schema(schema):` defines the function. Calling `create_schema('staging')` assigns `'staging'` to the local parameter `schema`.
2. `conn, cur = get_conn_cursor()` unpacks the helper's two returned objects. `conn` controls the session/transaction; `cur` executes SQL.
3. `schema_sql = f"..."` substitutes `{schema}` into a Python string. With `'staging'`, it becomes `CREATE SCHEMA IF NOT EXISTS staging;`. Building the string alone does not execute SQL.
4. `cur.execute(schema_sql)` sends that command to PostgreSQL. `IF NOT EXISTS` avoids an error solely because the schema already exists; other errors can still occur.
5. `conn.commit()` commits the transaction so the creation is saved.
6. `close_conn_cursor(conn, cur)` closes the cursor, then the connection. This does not delete the schema.

Create the schema before creating a table within it. Creating `staging.video_stats` does not automatically create `staging`.

## 2. Creating a table, line by line

This preserves the current function's logic, including its unresolved `table` variable.

```python
def create_table(schema):  # Receive the schema name.
    conn, cur = get_conn_cursor()  # Open a session and cursor.

    if schema == 'staging':  # Choose the staging definition.
        table_sql = f"""
            CREATE TABLE IF NOT EXISTS {schema}.{table} (
                "Video_ID" VARCHAR(11) PRIMARY KEY NOT NULL, -- Unique ID.
                "Video_Title" TEXT NOT NULL, -- Required title.
                "Upload_Date" TIMESTAMP NOT NULL, -- Required timestamp.
                "Duration" VARCHAR(20) NOT NULL, -- Raw duration text.
                "Video_Views" INT, -- Optional view count.
                "Likes_Count" INT, -- Optional like count.
                "Comments_Count" INT -- Optional comment count.
            );
        """
    else:  # Choose the other schema definition.
        table_sql = f"""
            CREATE TABLE IF NOT EXISTS {schema}.{table} (
                "Video_ID" VARCHAR(11) PRIMARY KEY NOT NULL, -- Unique ID.
                "Video_Title" TEXT NOT NULL, -- Required title.
                "Upload_Date" TIMESTAMP NOT NULL, -- Required timestamp.
                "Duration" TIME NOT NULL, -- Time-formatted value.
                "Video_Type" VARCHAR(10) NOT NULL, -- Required category.
                "Video_Views" INT, -- Optional view count.
                "Likes_Count" INT, -- Optional like count.
                "Comments_Count" INT -- Optional comment count.
            );
        """

    cur.execute(table_sql)  # Execute the selected definition.
    conn.commit()  # Save the creation.
    close_conn_cursor(conn, cur)  # Release both resources.
```

| Line or expression | Explanation |
|---|---|
| `def create_table(schema):` | Defines a function with one parameter. It currently receives no table-name parameter. |
| `conn, cur = get_conn_cursor()` | Opens the resources owned by this function call. |
| `if schema == 'staging':` | Compares the schema string to `'staging'`; the comparison is case sensitive. |
| `table_sql = f"""` | Starts a multiline formatted Python string containing SQL. |
| `CREATE TABLE IF NOT EXISTS {schema}.{table} (` | Names the destination and begins its column definitions. For example: `staging.video_stats`. |
| `"Video_ID" VARCHAR(11) PRIMARY KEY NOT NULL` | Stores up to 11 characters. The primary key enforces uniqueness and also implies non-nullability, so explicit `NOT NULL` is redundant here. |
| `"Video_Title" TEXT NOT NULL` | Requires a non-null text title; an empty string is still allowed. |
| `"Upload_Date" TIMESTAMP NOT NULL` | Requires date/time data. Plain PostgreSQL `TIMESTAMP` has no time zone. |
| `"Duration" VARCHAR(20) NOT NULL` | Staging requires duration text of at most 20 characters. |
| `"Video_Views" INT` | Stores an integer view count; null is allowed. |
| `"Likes_Count" INT` | Stores an integer like count; null is allowed. |
| `"Comments_Count" INT` | Stores an integer comment count; no comma follows the final column. |
| `);` | Ends the SQL column list and statement. |
| Closing `"""` | Ends the Python SQL string. |
| `else:` | Runs for every schema other than exactly `'staging'`, including `'core'` and accidental misspellings. It does not validate that the name is `'core'`. |
| Core `"Duration" TIME NOT NULL` | Replaces duration text with a time-of-day column. See the limitation below. |
| `"Video_Type" VARCHAR(10) NOT NULL` | Adds a required text category of at most 10 characters. The function does not calculate that category. |
| Other core column lines | Have the same meanings as the corresponding staging columns. |
| `cur.execute(table_sql)` | Executes only the definition selected by the branch. |
| `conn.commit()` | Saves the table creation. |
| `close_conn_cursor(conn, cur)` | Closes the cursor and its session after success. |

SQL comments use `--` inside the string; Python comments use `#` outside it. The double quotes around column names preserve their exact capitalization: use `"Video_ID"` in later SQL as well.

`IF NOT EXISTS` does not update or check an existing table's columns. Editing this function's definition will not migrate a table that already exists.

## 3. Where does `table` get its value?

**Currently, it does not have a value in this module.** The file neither defines nor imports `table`, and neither affected function accepts it as an argument. Both `create_table` and `get_video_ids` will raise `NameError` when evaluating their f-strings unless the module's namespace is supplied with that name externally.

Python does not derive the name from the filename, the schema, or PostgreSQL. A variable named `table` in a calling script is not automatically visible inside an imported function.

Two possible designs are:

```python
# Option A: define a module-level name in data_utils.py.
table = 'video_stats'  # Both functions use this shared name.
```

```python
# Option B: explicitly pass the name; clearer and reusable.
def create_table(schema, table):  # Add table to the existing signature.
    # Existing function body goes here.
    ...

def get_video_ids(cur, schema, table):  # Add table here too.
    cur.execute(f'SELECT "Video_ID" FROM {schema}.{table};')
    ids = cur.fetchall()
    return [row['Video_ID'] for row in ids]

# After updating the signatures and retaining the creation body:
create_schema('staging')
create_table('staging', 'video_stats')
```

These are suggested changes, not changes made to the Python file by this guide. The `...` is a placeholder, not a working creation implementation.

For example, `schema = 'core'` and `table = 'video_stats'` produce `core.video_stats`. The same table name can exist independently in two schemas.

The screenshot uses direct f-string interpolation. For dynamic identifiers, use `psycopg2.sql.Identifier` to handle SQL identifier quoting; `%s` parameters are for data values, not table/schema names. See [Psycopg SQL composition](https://www.psycopg.org/docs/sql.html).

## 4. Why change the duration type?

The likely design intention is **preserve the source representation in staging, then store a cleaned representation in core**. The API extraction file stores `contentDetails['duration']` unchanged.

| Layer | Current column type | Example representation |
|---|---|---|
| Staging | `VARCHAR(20)` | `PT5M30S`: duration text meaning 5 minutes, 30 seconds. |
| Core | `TIME` | `00:05:30`: the intended converted representation. |

That is an inferred intention, not a transformation implemented by `create_table`. Separate loading/transformation code must parse the source value before writing the target value. Creating a different column type does not move or convert existing staging rows.

There is a modeling issue: PostgreSQL `TIME` represents **time of day**, whereas `INTERVAL` represents a duration. I would use `INTERVAL` or integer seconds (`330` for this example) in core. Both fit elapsed time more naturally, including durations beyond 24 hours. [PostgreSQL date/time types](https://www.postgresql.org/docs/current/datatype-datetime.html).

The other schema difference is `Video_Type`, which exists only in core. Its derivation rules are not present in this function.

## 5. Why close the connection and cursor each time?

**Close resources when the code that owns them finishes using them.** You do not need a new connection for every small function.

| Function | Opens its own connection? | Who should close it? |
|---|---|---|
| `create_schema` | Yes | The function itself. |
| `create_table` | Yes | The function itself. |
| `get_video_ids` | No; receives `cur` | The caller that opened the session/cursor. |

The creation helpers each do one independent job, commit it, and clean up. This is simple, although repeated connection setup has overhead. Several helpers can instead share a caller-owned connection when their interfaces and transaction boundaries are designed for that.

`cur.close()` releases cursor resources. `conn.close()` ends the session and makes its cursors unusable. Closing does not delete committed tables or rows, and it does not replace `commit()`. Uncommitted changes are discarded on connection close. [Psycopg connection behavior](https://www.psycopg.org/docs/connection.html).

If resources remain open, repeated calls can accumulate sessions and consume connection capacity. Unfinished transactions can also retain locks. A later process exit may release resources, but explicit cleanup makes their lifetime predictable.

The current functions only reach their close calls on success. An exception in `execute()` or `commit()` skips cleanup; the undefined `table` also causes failure after opening a connection. A better ownership pattern is:

```python
conn, cur = get_conn_cursor()  # This caller owns both objects.
try:
    video_ids = get_video_ids(cur, 'staging')  # Borrow the cursor.
    conn.commit()  # End the read transaction successfully.
except Exception:
    conn.rollback()  # End a failed transaction.
    raise  # Preserve the error.
finally:
    close_conn_cursor(conn, cur)  # Clean up on either path.
```

This example assumes `table` has first been defined in `data_utils.py`. If using the suggested parameter version, call `get_video_ids(cur, 'staging', 'video_stats')` instead. A `SELECT` needs no commit to save data; the commit here ends its transaction. The returned Python list remains usable after closing.

## 6. `get_video_ids`, line by line

```python
def get_video_ids(cur, schema):  # Receive a cursor and schema.
    cur.execute(f'''SELECT "Video_ID" FROM {schema}.{table};''')  # Run query.
    ids = cur.fetchall()  # Read all remaining result rows.
    video_ids = [row['Video_ID'] for row in ids]  # Extract each ID.
    return video_ids  # Return a list of strings.
```

1. `def get_video_ids(cur, schema):` receives an already-created cursor and a schema string. It does not open a connection.
2. `cur.execute(...)` runs a query selecting only `"Video_ID"`, regardless of how many columns the table has. `execute()` itself does not return the rows; the cursor exposes the result for fetching.
3. `ids = cur.fetchall()` reads **all remaining rows from that query result** into a Python list. Here, nothing has been fetched yet, so it gets all result rows. It does not return every column from the original table.
4. `video_ids = [...]` builds a new list containing just the ID value from each row. It does not modify `ids` or the database.
5. `return video_ids` gives that new list to the caller.

`fetchall()` returns `[]` when no rows remain. After it consumes this result, calling it again without re-executing returns `[]`. Large results occupy Python memory; batching is preferable when that becomes significant. See [Psycopg fetching methods](https://www.psycopg.org/docs/cursor.html#cursor.fetchall).

### Concrete example: table → query rows → strings

Suppose `staging.video_stats` contains:

| Video_ID | Video_Title | Duration |
|---|---|---|
| `AbCdEfGhI01` | Python basics | `PT5M30S` |
| `JkLmNoPqR02` | SQL joins | `PT12M` |

The executed SQL is:

```sql
SELECT "Video_ID" FROM staging.video_stats;
```

Because `get_conn_cursor()` uses `RealDictCursor`, each fetched row is dictionary-like, keyed by the selected column name. Displayed as ordinary dictionaries for clarity, `ids` looks like:

```python
ids = [
    {'Video_ID': 'AbCdEfGhI01'},  # First result row.
    {'Video_ID': 'JkLmNoPqR02'},  # Second result row.
]
```

The actual row objects are `RealDictRow` objects. A default cursor would give tuple rows instead, requiring `row[0]`. The dictionary cursor is what permits `row['Video_ID']`. See [Psycopg RealDictCursor](https://www.psycopg.org/docs/extras.html#real-dictionary-cursor).

Read the comprehension as: **for each row in `ids`, take its `Video_ID` value and put that value in the new list**.

```python
video_ids = [row['Video_ID'] for row in ids]

# Equivalent expanded loop:
video_ids = []  # Start an empty result list.
for row in ids:  # Visit one dictionary-like row at a time.
    video_id = row['Video_ID']  # Look up this row's ID string.
    video_ids.append(video_id)  # Add the string to the result.
```

| Iteration | `row` | `row['Video_ID']` | New list so far |
|---|---|---|---|
| 1 | `{'Video_ID': 'AbCdEfGhI01'}` | `'AbCdEfGhI01'` | `['AbCdEfGhI01']` |
| 2 | `{'Video_ID': 'JkLmNoPqR02'}` | `'JkLmNoPqR02'` | `['AbCdEfGhI01', 'JkLmNoPqR02']` |

`row` is a temporary loop variable chosen by the programmer; it is not a special keyword. `ids` is a list of row objects, while `video_ids` is a list of strings:

```python
ids[0]                 # {'Video_ID': 'AbCdEfGhI01'}
ids[0]['Video_ID']     # 'AbCdEfGhI01'
video_ids[0]           # 'AbCdEfGhI01'
```

If `ids` is empty, the loop has zero iterations and the returned list is `[]`. The query has no `ORDER BY`, so the example row order is illustrative, not guaranteed.

These IDs can then be compared with API-discovered IDs to identify videos already loaded. This helper only retrieves stored IDs; it does not perform that comparison itself.
