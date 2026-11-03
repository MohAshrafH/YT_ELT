# Default arguments and Cairo timezone

This follows the screenshot's structure and dates. The owner is adapted to this project, Cairo replaces Malta, and the email is a placeholder. Paste below your existing imports of `pendulum`, `datetime`, and `timedelta`.

```python
# Define the local timezone
local_tz = pendulum.timezone("Africa/Cairo")

# Default Args
default_args = {
    "owner": "yt_elt",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "email": "your_email@example.com",
    # 'retries': 1,
    # 'retry_delay': timedelta(minutes=5),
    "max_active_runs": 1,
    "dagrun_timeout": timedelta(hours=1),
    "start_date": datetime(2025, 1, 1, tzinfo=local_tz),
    # 'end_date': datetime(2030, 12, 31, tzinfo=local_tz),
}
```

## Line by line

| Line | Meaning |
| --- | --- |
| `# Define the local timezone` | Comment introducing the timezone. |
| `local_tz = pendulum.timezone("Africa/Cairo")` | Creates Cairo's timezone object using the installed timezone database. |
| `# Default Args` | Comment introducing shared defaults. |
| `default_args = {` | Starts the dictionary supplied later through `DAG(default_args=default_args, ...)`. |
| `owner` | Task owner label; it does not create an Airflow login. |
| `depends_on_past=False` | A task does not require its previous run to succeed. Current-run dependencies still apply. |
| `email_on_failure=False` | Disables built-in task failure emails. |
| `email_on_retry=False` | Disables built-in task retry emails. |
| `email` | Placeholder recipient. Replace with your address if enabling alerts; email delivery also needs configuration. |
| `# 'retries': 1` | Inactive comment. Uncommenting allows one retry: two attempts total. |
| `# 'retry_delay': ...` | Inactive comment. Uncommenting sets a five-minute retry delay. |
| `max_active_runs=1` | Intended limit of one active DAG run at a time; see placement note below. |
| `dagrun_timeout` | Intended one-hour timeout for scheduled DAG runs; see placement note below. |
| `start_date` | Earliest interval boundary: 1 January 2025 at midnight in Cairo. |
| `# 'end_date': ...` | Inactive comment. If enabled, bounds eligible logical dates; it is not an exact wall-clock shutdown command. |
| `}` | Ends the dictionary. |

**Placement note:** This transcription preserves the screenshot. In Airflow 2.9.2, `max_active_runs` and `dagrun_timeout` must be passed directly to `DAG(...)` to configure those DAG limits. Move those two entries there when building the DAG. Commented-out retry settings leave environment defaults in effect; they do not explicitly set retries to zero.

References: [DAG arguments](https://airflow.apache.org/docs/apache-airflow/2.9.2/_api/airflow/models/dag/index.html), [task arguments](https://airflow.apache.org/docs/apache-airflow/2.9.2/_api/airflow/models/baseoperator/index.html).

## Why start_date does not mean immediate execution

With Airflow 2.9.2's normal cron scheduling, a run represents a **data interval**. Airflow waits for that interval to finish before scheduling its run. The **logical date** labels the interval's start, rather than the actual execution time.

Assume the DAG is enabled beforehand and the scheduler is running. All times are Cairo time:

| Schedule | Start date | First interval | First run eligible |
| --- | --- | --- | --- |
| `@daily` | 1 Jan 2025, 00:00 | 1 Jan 00:00 → 2 Jan 00:00 | 2 Jan 00:00 |
| `@hourly` | 1 Jan 2025, 00:00 | 1 Jan 00:00 → 01:00 | 1 Jan 01:00 |

Think of a daily report: the reporting day must finish before its complete report can be produced. Scheduler and worker availability can delay execution further.

Reference: [data intervals](https://airflow.apache.org/docs/apache-airflow/2.9.2/core-concepts/dag-run.html#data-interval).

## The lesson's daily 2 p.m. schedule

This dictionary alone does not set a schedule. Later, `schedule="0 14 * * *"` on `DAG(...)` creates daily boundaries at 14:00.

With the screenshot's midnight start date, the first full interval is **1 January 2025 at 14:00 → 2 January at 14:00**. Its run becomes eligible after **2 January at 14:00**. There is no partial midnight-to-14:00 interval.

Keep `start_date` fixed. `datetime.now()` would move the boundary whenever Airflow parses the file.

Reference: [start-date FAQ](https://airflow.apache.org/docs/apache-airflow/2.9.2/faq.html#what-s-the-deal-with-start-date).

## Enabling a DAG with an old start date

Suppose you first unpause this new DAG at 16:00 on 3 November 2026, using the 14:00 schedule:

- `catchup=False`: the latest completed interval is 2 November 14:00 → 3 November 14:00. A run can start shortly after unpausing.
- `catchup=True`: earlier missing intervals since the start date are also eligible.

`catchup` belongs on `DAG(...)` and is absent from this screenshot. Manual triggers do not wait for the next cron boundary.

Reference: [catchup](https://airflow.apache.org/docs/apache-airflow/2.9.2/core-concepts/dag-run.html#catchup).

## Cairo timezone and extraction

`Africa/Cairo` uses local timezone rules rather than a fixed UTC offset. A timezone-aware cron schedule follows Cairo wall-clock time, including daylight-saving rules supported by the installed database. Airflow stores dates in UTC; the UI display timezone is separate.

A data interval does not automatically filter YouTube API results. Your functions must explicitly use interval boundaries if historical filtering is required; an old interval can otherwise fetch current video statistics.

Reference: [timezones](https://airflow.apache.org/docs/apache-airflow/2.9.2/authoring-and-scheduling/timezone.html).
