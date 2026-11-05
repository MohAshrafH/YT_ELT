# DWH / ELT: Reading today's JSON file

## Conceptual and functional overview

`dags/datawarehouse/data_loading.py` defines a helper that finds today's dated JSON file, reads it, converts its contents into Python objects, and returns those objects to its caller.

Conceptually, the file on disk is stored text. `open()` provides access to that text; `json.load()` interprets its JSON structure. For example, JSON objects become Python dictionaries and JSON arrays become Python lists. Later pipeline code can use these objects to prepare database inserts.

Despite the filename `data_loading.py`, this code only loads data into Python memory. It does not insert anything into a warehouse, call the YouTube API, or create an Airflow task. Defining the function does not run it: another part of the program must call `load_path()`.

The function has three main outcomes:

1. **Valid file:** read and parse the JSON, close the file, and return the parsed value.
2. **Missing file:** log an error and pass the original exception to the caller.
3. **Malformed JSON:** close the file, log an error, and pass the original parsing exception to the caller.

Other exceptions, such as permission errors, also propagate to the caller, but these two handlers do not log them.

## Code being explained

This is the current file's executable code, with comments omitted here so each statement can be discussed below.

```python
import json
from datetime import date
import logging

logger = logging.getLogger(__name__)


def load_path():
    file_path = f"./data/YT_data_{date.today()}.json"

    try:
        logger.info(f"Processing file: YT_data_{date.today()}")

        with open(file_path, "r", encoding="utf-8") as raw_data:
            data = json.load(raw_data)

        return data
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in file: {file_path}")
        raise
```

## Line-by-line explanation: function and syntax

### 1. `import json`

Imports Python's built-in JSON module and binds it to the name `json`. A **module** is a unit of Python code that groups related functions, classes, and other names.

The `import` keyword makes that module available. Later, `json.load(...)` uses a dot to access its `load` function. No separate package installation is needed for this standard-library module.

### 2. `from datetime import date`

Imports the `date` class from the standard-library `datetime` module. The syntax `from module import name` lets you use the imported name directly: `date.today()` instead of `datetime.date.today()`.

`date` represents a calendar date without a time of day. Its `today()` class method returns the current local date of the machine or container running Python; this may differ from your own timezone.

### 3. `import logging`

Imports Python's standard-library logging module. Logging records events with severity levels such as `DEBUG`, `INFO`, `WARNING`, `ERROR`, and `CRITICAL`.

Unlike plain `print()`, logging supports named sources, severity filtering, timestamps, formatting, and destinations such as console output or files. Configuration determines which of these features are active.

### 4. `logger = logging.getLogger(__name__)`

This obtains a named logger object and stores a reference to it in the variable `logger`.

The terminology matters: **`logging` is a module; `logger` is an object**, an instance of `logging.Logger`. The variable name `logger` is a convention, not a special Python keyword. A logger provides methods such as `.info()` and `.error()` for reporting events.

Breakdown:

| Part | Meaning |
|---|---|
| `logger` | The variable that will refer to the logger object. |
| `=` | Assignment: evaluate the expression on the right and bind its result to the name on the left. |
| `logging` | The imported module. |
| `.` | Access an attribute belonging to an object or module. |
| `getLogger` | A function that retrieves an existing logger with this name, or creates it if needed. |
| `(...)` | Call the function, passing the values inside the parentheses. |
| `__name__` | A Python-provided string identifying the current module. It is the argument passed to `getLogger`. |

`__name__` is a variable, not the literal text `"__name__"`. Python supplies its value according to how the file is loaded. For example, if imported as `datawarehouse.data_loading`, its value is `"datawarehouse.data_loading"`. If the file is executed directly as a script, its value is `"__main__"`. The exact import name depends on how your project is run.

Using the module name helps distinguish messages from different files and supports hierarchical configuration: `datawarehouse.data_loading` can inherit logging settings from `datawarehouse` and the root logger. Repeated calls to `getLogger` with the same name return the same logger object within the process.

This line runs when the module is imported, outside the function. It does not read the JSON file, emit a message, or configure an output file. It prepares the logger that `load_path()` will use.

Also, calling `.info()` does not guarantee a visible message. The logger's effective level and handler configuration control output. In a standalone program with default logging settings, `INFO` messages are normally filtered out; Airflow typically supplies its own logging configuration.

### 5. `def load_path():`

Defines a function named `load_path`. `def` introduces a function definition, `()` contains its parameters (none here), and `:` starts its indented body.

The body runs only when someone calls `load_path()`. It needs no arguments because it calculates the date and file path internally. Despite its name, it returns the parsed contents, not the path itself.

Python uses indentation to group statements. The function's body is indented one level; nested blocks such as `try` and `with` add further levels. Blank lines improve readability without changing execution.

### 6. `file_path = f"./data/YT_data_{date.today()}.json"`

Builds a filename using today's date, then assigns the resulting string to the local variable `file_path`.

- `f` before the quote creates an **f-string**, which inserts evaluated expressions into text.
- `{date.today()}` calls `today()` and inserts its result, normally formatted as `YYYY-MM-DD`.
- `./data/` means the `data` directory beneath the process's current working directory.
- `YT_data_` is a fixed prefix and `.json` is the filename extension.

For example, on November 5, 2026, the string is `./data/YT_data_2026-11-05.json`.

The relative path is resolved from the working directory, **not automatically from the directory containing this Python file**. Running Python from another folder or from a container can therefore change where it looks. The assignment only builds a string; it does not check whether the file exists.

### 7. `try:`

Starts a block whose exceptions can be handled by the associated `except` clauses. Python runs the statements inside in order. If one raises an exception, Python skips the remaining statements in that block and looks for a matching handler.

The colon introduces an indented block. Only errors raised during execution of this block are considered by these handlers; the preceding path assignment is outside it.

### 8. `logger.info(f"Processing file: YT_data_{date.today()}")`

Reports a normal progress event at `INFO` severity. The f-string inserts the current local date into the message. `.info(...)` is a method call on the logger object; the string is the message argument.

This records an attempt to process a file, not proof of success. It occurs before opening or parsing. The date is calculated again here, so a call crossing midnight could theoretically log a different date from the path built just beforehand. The message also omits the directory and `.json` extension.

### 9. `with open(file_path, "r", encoding="utf-8") as raw_data:`

Opens the file and manages its lifetime through a **context manager**.

| Part | Meaning |
|---|---|
| `with` | Enter a managed block and perform its cleanup when leaving it. |
| `open(...)` | Python's built-in function for opening a file; returns a file object. |
| `file_path` | First positional argument: the file to open. |
| `"r"` | Second positional argument: read mode. With no `b`, this is text mode; the file must already exist. It is not created or overwritten. |
| `encoding="utf-8"` | Keyword argument specifying how file bytes are decoded into Python text. UTF-8 supports characters from many languages. |
| `as raw_data` | Bind the opened file object to the local name `raw_data`. This is a readable stream, not the parsed contents. |
| `:` | Start the indented block that uses the open file. |

The file is closed automatically when execution leaves the block, including if parsing raises an exception. If opening itself fails, there is no successfully opened file to close. An encoding mismatch can raise `UnicodeDecodeError`, which this function does not explicitly catch.

### 10. `data = json.load(raw_data)`

Reads JSON from the open file object, parses it, and assigns the resulting Python value to `data`.

`json.load()` accepts a readable file-like object. By comparison, `json.loads()` parses a JSON string that is already in memory. The `s` in `loads` helps distinguish the string-based function.

Typical conversions are:

| JSON value | Python value |
|---|---|
| Object: `{"id": "abc"}` | Dictionary: `{"id": "abc"}` |
| Array: `[1, 2]` | List: `[1, 2]` |
| String | `str` |
| Integer / fractional number | Usually `int` / `float` |
| `true` / `false` | `True` / `False` |
| `null` | `None` |

The top-level value need not be a dictionary or list. Valid JSON can also contain a single number, string, boolean, or `null`. Parsing verifies JSON syntax; it does not verify that required video fields or expected data types are present.

### 11. `return data`

Ends the function successfully and gives `data` to the caller. This statement is outside the `with` block but inside the `try` block, so the file has already closed before the result is returned.

For example, `videos = load_path()` assigns the parsed result to `videos` if loading succeeds. If opening or parsing fails, this return statement is never reached.

### 12. `except FileNotFoundError:`

Handles a matching exception raised in the `try` block. `FileNotFoundError` is a built-in exception class, commonly raised here when the requested file or a directory in its path does not exist.

`except` identifies the handler, the class names the kind of error to match, and the colon starts its body. You could use `except FileNotFoundError as exc:` to bind the exception object to a variable, but this code does not need such a variable.

### 13. `logger.error(f"File not found: {file_path}")`

Reports an `ERROR` message containing the attempted path. It describes the failure for someone inspecting logs. Logging alone does not stop the function or pass the exception onward; the next statement does that.

This call records a message, not automatically the full exception traceback. `logger.exception(...)` inside an exception handler is an alternative when the traceback should also be logged there.

### 14. `raise`

A bare `raise` inside this handler re-raises the exception currently being handled, preserving its original traceback. Execution leaves the function, and the caller must handle the exception or allow it to propagate further.

No new exception is created, and no normal result is returned. A bare `raise` requires an active exception; using it without one raises `RuntimeError`.

### 15. `except json.JSONDecodeError:`

Handles malformed JSON, such as an empty file, missing double quotes around keys, or a trailing comma. `JSONDecodeError` is an exception class accessed through the imported `json` module.

This handler is an alternative to the preceding handler, not a step executed afterward. Python selects the first matching handler; a re-raised missing-file exception does not flow into this sibling handler.

### 16. `logger.error(f"Invalid JSON in file: {file_path}")`

Reports which file could not be parsed. At this point, opening succeeded but JSON parsing failed, and the `with` block has already closed the file while unwinding the exception.

### 17. `raise`

Re-raises the original `JSONDecodeError`. The caller receives the parsing failure, including its error details, rather than a normal data result.

## `raise` versus `return`

Both can end the current function's execution, but they communicate different outcomes.

| Statement | Meaning | Effect at the caller |
|---|---|---|
| `return data` | Successful completion with a result. | The call evaluates to `data`; execution continues normally. |
| `return None` or bare `return` | Normal completion with no useful result. | The call evaluates to `None`; no exception is signaled. |
| `raise` | Re-throw the active exception. | Normal execution stops; Python searches for an exception handler. |
| `raise ValueError("Bad input")` | Create and throw an explicit exception. | The caller receives a `ValueError` unless it is handled. |
| `return error` | Return whatever object the variable `error` refers to. | Even an exception object is just a normal return value here; returning it does not throw it. |

`raise error` is valid if `error` refers to an exception instance or exception class. In an `except ... as error:` handler, prefer bare `raise` when the intention is to propagate the original error; explicitly raising the variable adds a re-raise location to the traceback.

For this loader, replacing `raise` with `return None` would turn a missing or invalid file into a normal return. Downstream code would need to distinguish that result from real data. This is especially ambiguous because a valid JSON file containing `null` also parses to `None`.

If an Airflow task calls this function and the exception escapes the task callable, Airflow can treat the attempt as failed and apply configured retries. Returning normally does not by itself signal task failure. Logging an error without raising it does not by itself fail a task either.

### Example: caller behavior

```python
try:
    videos = load_path()  # Assign a value only if the function returns normally.
except FileNotFoundError:
    print("Today's input file is missing.")  # Handle the propagated failure here.
except json.JSONDecodeError:
    print("Today's input file contains invalid JSON.")
else:
    print("File loaded successfully.")  # Runs only when no exception occurred.
```

These example handlers print messages and finish normally, so they consume the errors. In a task that should fail on either condition, omit these handlers or re-raise after any additional handling.

## Practical boundaries of this implementation

- The filename uses the runtime's local date, not an Airflow logical date. Rerunning an older scheduled interval still selects today's file.
- The `./data/` directory must resolve correctly in the process or container running the function.
- `json.load()` builds the parsed result in memory; it is not a streaming record-by-record warehouse load.
- Only missing-file and JSON syntax errors receive custom log messages here. Other failures still propagate.
- Importing the module prepares its imports, logger, and function definition. It does not call `load_path()`.
