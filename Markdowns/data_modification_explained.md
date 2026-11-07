# Understanding `data_modification.py`

## 1. Overview

[`data_modification.py`](../dags/datawarehouse/data_modification.py) changes video records in a database table named `yt_api`:

| Function | Database action | How it selects records |
|---|---|---|
| `insert_rows` | Adds one video record per call | Uses all supplied insert values |
| `update_rows` | Changes title, views, likes, and comments | Matches video ID **and** upload date |
| `delete_rows` | Removes matching video records | Matches any supplied video ID |

Each function executes SQL, commits the connection's pending transaction, and logs success. On failure, it attempts to log the error and raises an exception to the caller. Successful calls return **`None`** because there is no `return` statement; the main output is the database change.

The module does not open a connection, create tables, fetch videos, or call these functions itself. The caller supplies an existing connection and its cursor.

> This guide describes the current file, including its limitations. Line numbers refer to the source as documented and exclude no lines; blank lines and comment-only lines need no execution explanation.

## 2. Inputs and syntax used throughout

| Input | Meaning | Example |
|---|---|---|
| `cur` | Cursor that sends SQL through a database connection | A cursor obtained from `conn` |
| `conn` | Connection whose transaction is committed | An already-open database connection |
| `schema` | Database namespace containing `yt_api` | `'staging'` or `'core'` |
| `row` | Dictionary mapping expected keys to one video's values | `{'Video_ID': 'v101', ...}` |
| `ids_to_delete` | Iterable of IDs; use a list of strings in these examples | `['v101', 'v102']` |

`cur` should belong to `conn`: otherwise the commit may not save the cursor's changes. The SQL expects a driver supporting `%(name)s` named parameters, such as psycopg2.

| Syntax | How to read it |
|---|---|
| `def name(...):` | Define a function; its indented body runs when called |
| `=` versus `==` | Store a value versus test whether two values are equal |
| `obj.method(...)` | Call an operation on an object, such as `conn.commit()` |
| `f"...{value}..."` | Build a string by evaluating expressions inside braces |
| `"""..."""` | A string that can span several lines |
| `row[video_id]` | Look up the dictionary key stored in `video_id` |
| `%(title)s` | Driver placeholder for `row['title']`; `s` does not mean the value must be a string |
| SQL `"Video_ID"` | A quoted column identifier; spelling and capitalization matter |

There are two substitution steps in insert/update: Python fills `{schema}`, `{table}`, and any key-name expressions; then the database driver binds the dictionary values. Schema/table names are inserted directly, not bound as values.

## 3. Module setup — line by line

| Line | Code | Purpose |
|---|---|---|
| 1 | `import logging` | Load Python's built-in message logging tools |
| 3 | `logger = logging.getLogger(__name__)` | Obtain a logger named after this module. `__name__` is its import name, or `'__main__'` when run directly |
| 4 | `table = "yt_api"` | Define the shared destination table name used by all three functions |

Logging configuration comes from the surrounding application; `info()` messages are only displayed or saved if that configuration enables them. Defining the functions does not execute SQL.

## 4. `insert_rows` — add a video

### Line-by-line explanation

| Line(s) | Code or operation | Purpose and syntax |
|---|---|---|
| 6 | `def insert_rows(cur, conn, schema, row):` | Define a function accepting the four inputs described above |
| 8 | `try:` | Start the block whose exceptions are handled at line 42 |
| 10 | `if schema == 'staging':` | Select the staging format only for this exact schema string |
| 12 | `video_id = 'video_id'` | Store the dictionary key used later in success/error messages |
| 16 | `cur.execute(` | Begin a SQL call with SQL text and a separate values dictionary |
| 19 | `INSERT INTO ... (columns)` | Choose `schema.yt_api` and the seven staging destination columns |
| 20 | `VALUES (...)` | Match seven named dictionary values to those columns by position |
| 21–23 | End SQL string; pass `row`; close call | Let the driver bind values and execute the insert |
| 25 | `else:` | Use the other insert format for **every** non-staging schema |
| 26 | `video_id = "Video_ID"` | Select the non-staging dictionary key for logging |
| 29–30 | `cur.execute(f"""` | Start the alternative multiline SQL statement |
| 31 | `INSERT INTO ... (columns)` | Select eight underscore-named columns, including `Video_Type` |
| 32 | `VALUES (...)` | Map the eight non-staging dictionary keys to the columns in order |
| 33–35 | End SQL string; pass `row`; close call | Bind the values and execute this insert |
| 37 | `conn.commit()` | Commit all pending changes on this connection |
| 40 | `logger.info(f"...{row[video_id]}")` | Retrieve the selected ID and log successful execution |
| 42 | `except Exception as e:` | Catch an `Exception` from the try block and store it as `e` |
| 43 | `logger.error(...)` | Log the video ID; this message does not include the error text |
| 44 | `raise e` | Raise the caught exception again so the caller sees failure |

### Field mapping: input → placeholder → destination

The middle column applies to the staging insert; the last applies to the non-staging insert. Each key becomes a placeholder of the form `%(key)s`.

| Value | Staging key → SQL column | Non-staging key → SQL column |
|---|---|---|
| ID | `video_id` → `"Video ID"` | `Video_ID` → `"Video_ID"` |
| Title | `title` → `"Video Title"` | `Video_Title` → `"Video_Title"` |
| Upload date | `publishedAt` → `"Upload Date"` | `Upload_Date` → `"Upload_Date"` |
| Duration | `duration` → `"Duration"` | `Duration` → `"Duration"` |
| Type | Not inserted | `Video_Type` → `"Video_Type"` |
| Views | `viewCount` → `"Video Views"` | `Video_Views` → `"Video_Views"` |
| Likes | `likeCount` → `"Likes Count"` | `Likes_Count` → `"Likes_Count"` |
| Comments | `commentCount` → `"Comments Count"` | `Comments_Count` → `"Comments_Count"` |

### Worked trace

Assume `core.yt_api` exists, accepts these values, and initially contains no rows. These examples are illustrative, not executed database results.

```python
row = {
    'Video_ID': 'v101', 'Video_Title': 'Python Basics',
    'Upload_Date': '2026-11-01', 'Duration': 'PT5M',
    'Video_Type': 'video', 'Video_Views': 100,
    'Likes_Count': 10, 'Comments_Count': 2,
}
insert_rows(cur, conn, 'core', row)
```

1. `'core' != 'staging'`, so line 25 selects the non-staging branch; `video_id` becomes `'Video_ID'`.
2. `{schema}.{table}` becomes `core.yt_api`. For example, `%(Video_Title)s` receives `'Python Basics'`; the mapping table explains every other value.
3. `execute()` inserts the record; `commit()` saves the transaction.
4. The logger receives `Inserted row with Video ID: v101`. The caller receives `None`.

**Database after the call** (the duration shown is the supplied value, not a claim about its database storage type):

| Video_ID | Video_Title | Upload_Date | Duration | Video_Type | Video_Views | Likes_Count | Comments_Count |
|---|---|---|---|---|---:|---:|---:|
| v101 | Python Basics | 2026-11-01 | PT5M | video | 100 | 10 | 2 |

## 5. `update_rows` — refresh an existing video

### Line-by-line explanation

| Line(s) | Code or operation | Purpose and syntax |
|---|---|---|
| 46 | `def update_rows(cur,conn,schema,row):` | Accept one video's replacement values plus cursor, connection, and schema |
| 47 | `try:` | Start the protected update/commit/logging block |
| 48 | `if schema == 'staging':` | Choose staging dictionary keys |
| 49 | `video_id = 'video_id'` | Select the ID key for matching and logging |
| 50 | `upload_date = 'publishedAt'` | Select the date key for matching |
| 51 | `video_title = 'title'` | Select the replacement title key |
| 52 | `video_views = 'viewCount'` | Select the replacement views key |
| 53 | `likes_count = 'likeCount'` | Select the replacement likes key |
| 54 | `comments_count = 'commentCount'` | Select the replacement comments key |
| 57 | `else:` | Choose non-staging keys for every other schema |
| 58 | `video_id = 'Video_ID'` | Select the non-staging ID key |
| 59 | `upload_date = 'Upload_Date'` | Select the non-staging date key |
| 60 | `video_title = 'Video_Title'` | Select the non-staging title key |
| 61 | `video_views = 'Video_Views'` | Select the non-staging views key |
| 62 | `likes_count = 'Likes_Count'` | Select the non-staging likes key |
| 63 | `comments_count = 'Comments_Count'` | Select the non-staging comments key |
| 70–71 | `cur.execute(f"""` | Start a call containing dynamically constructed SQL |
| 72 | `UPDATE {schema}.{table}` | Choose the table to modify |
| 73 | `SET "Video_Title" = %({video_title})s,` | Construct a title placeholder, then bind its replacement value |
| 74 | `"Video_Views" = %({video_views})s,` | Assign the supplied view count |
| 75 | `"Likes_Count" = %({likes_count})s,` | Assign the supplied like count |
| 76 | `"Comments_Count" = %({comments_count})s` | Assign the supplied comment count; no comma follows the last assignment |
| 77 | `WHERE ... AND ...` | Modify only records matching both ID and date |
| 78–79 | End SQL; pass `row`; close call | Bind the dictionary values and execute the update |
| 81 | `conn.commit()` | Save the pending transaction |
| 84 | `logger.info(...)` | Log the selected ID after successful execution |
| 86 | `except Exception as e:` | Catch a failure and name it `e` |
| 87 | `logger.error(f"...{e}")` | Log the ID and the exception's readable message |
| 88 | `raise e` | Pass the failure to the caller |

### Worked trace: continue from the inserted record

```python
updated_row = {
    'Video_ID': 'v101', 'Upload_Date': '2026-11-01',
    'Video_Title': 'Python Basics Updated', 'Video_Views': 150,
    'Likes_Count': 15, 'Comments_Count': 4,
}
update_rows(cur, conn, 'core', updated_row)
```

| Input value | Selected variable | Generated placeholder | SQL role |
|---|---|---|---|
| `v101` | `video_id = 'Video_ID'` | `%(Video_ID)s` | Match `"Video_ID"` |
| `2026-11-01` | `upload_date = 'Upload_Date'` | `%(Upload_Date)s` | Match `"Upload_Date"` |
| `Python Basics Updated` | `video_title = 'Video_Title'` | `%(Video_Title)s` | Set title |
| `150` | `video_views = 'Video_Views'` | `%(Video_Views)s` | Set views |
| `15` | `likes_count = 'Likes_Count'` | `%(Likes_Count)s` | Set likes |
| `4` | `comments_count = 'Comments_Count'` | `%(Comments_Count)s` | Set comments |

`execute()` targets `core.yt_api` and matches the existing ID/date pair. After `commit()`, the result is:

| Field | Before | After |
|---|---|---|
| Video_ID | v101 | v101 |
| Upload_Date | 2026-11-01 | 2026-11-01 |
| Video_Title | Python Basics | Python Basics Updated |
| Video_Views | 100 | 150 |
| Likes_Count | 10 | 15 |
| Comments_Count | 2 | 4 |
| Duration | PT5M | PT5M |
| Video_Type | video | video |

The logger receives `Updated row with Video_ID: v101`; the caller receives `None`. Duration/type are unchanged because they are absent from `SET`. If no ID/date pair matches, no record changes, but the function still commits and logs success. Multiple matching records would all be updated.

## 6. `delete_rows` — remove videos by ID

### Line-by-line explanation

| Line(s) | Code or operation | Purpose and syntax |
|---|---|---|
| 91 | `def delete_rows(cur, conn, schema, ids_to_delete):` | Accept an iterable of IDs instead of a row dictionary |
| 92 | `try:` | Start the protected deletion block |
| 94 | `ids_to_delete = f"""({', '.join(f"'{id}'" for id in ids_to_delete)})"""` | Iterate over IDs, quote each, join with comma-space, and add parentheses; replace the local input variable with that string |
| 98–99 | `cur.execute(f"""` | Start SQL execution with one string argument; no separate parameter mapping is supplied |
| 100 | `DELETE FROM {schema}.{table}` | Select the table whose records will be removed |
| 101 | `WHERE "Video_ID" IN {ids_to_delete};` | Match every record whose ID belongs to the constructed list |
| 102–103 | End string and call | Send the completed SQL for execution |
| 105 | `conn.commit()` | Save the deletion transaction |
| 106 | `logger.info(...)` | Log the formatted ID list |
| 108 | `except Exception as e:` | Catch a failure and keep it in `e` |
| 109 | `logger.error(...)` | Log the ID list and exception message |
| 110 | `raise e` | Raise the failure to the caller |

### Worked trace

Continue with the updated `v101` record. Assume `v102` and `v103` also exist:

| Video_ID | Video_Title | Present before? |
|---|---|---|
| v101 | Python Basics Updated | Yes |
| v102 | SQL Basics | Yes |
| v103 | Airflow Basics | Yes |

```python
ids = ['v101', 'v102']
delete_rows(cur, conn, 'core', ids)
```

| Step | Value or action |
|---|---|
| Function input | `ids_to_delete` initially refers to `['v101', 'v102']` |
| `for id in ids_to_delete` | Visit `v101`, then `v102`; `id` is a local loop name |
| `f"'{id}'"` | Produce the strings `'v101'` and `'v102'`, including SQL quote characters |
| `', '.join(...)` | Produce `'v101', 'v102'` |
| Outer f-string | Produce `('v101', 'v102')` and assign it to local `ids_to_delete` |
| SQL sent | `DELETE FROM core.yt_api WHERE "Video_ID" IN ('v101', 'v102');` |
| Commit | Save removal of every record with either ID, regardless of upload date |
| Log message | `Deleted rows with Video_IDs: ('v101', 'v102')` |
| Python result | `None`; the caller's `ids` list remains unchanged |

**Database after deletion:**

| Video_ID | Video_Title |
|---|---|
| v103 | Airflow Basics |

## 7. Failure behavior and current limitations

These points explain the code's actual behavior; no source changes are proposed here.

| Detail | Practical effect |
|---|---|
| **Staging column mismatch** | Insert uses `"Video ID"`, `"Video Title"`, etc.; update/delete use `"Video_ID"`, `"Video_Title"`, etc. These are different SQL identifiers. A table containing only the spaced names will reject update/delete statements referencing underscore names |
| **Different row formats** | Staging expects API-style keys; other schemas expect underscore names. `else` does not specifically validate `'core'` |
| **Delete values are interpolated** | Unlike insert/update values, IDs are not driver-bound. Embedded quotes can break SQL or allow SQL injection; an empty list generates invalid `IN ()` SQL |
| **Schema is interpolated in all functions** | It must come from a trusted, valid source; value placeholders do not protect SQL identifiers |
| **No rollback in these functions** | After a transaction error, the caller must manage rollback/recovery as required by the driver |
| **Commit applies to the connection** | Other pending work on the same connection is also committed; each function commits separately |
| **Logs do not count affected rows** | An update/delete affecting zero records can still log success; no count is returned |
| **Error logging can fail** | In insert/update, a missing ID key can make `row[video_id]` raise another error inside the handler, masking the original failure |
| **Commit comes before success logging** | If subsequent logging fails, an exception may escape even though the database change is already saved |

For example, if the database rejects an insert because a required column is missing, control jumps to `except`; the function attempts to log the ID and `raise e` sends the exception to the caller. That call does **not** return `None` normally. `raise e` also adds the re-raise location to the traceback; a bare `raise` would preserve the original traceback more directly.

Some existing inline comments are stale: staging's `video_id` **is** used for logging; `table` and `logger` are defined at this module's top; and the complete `try` blocks already have `except` handlers. The explanations above follow the executable code.
