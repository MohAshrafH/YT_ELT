# Soda Data Quality Testing: Overview, Examples, and Commands

Soda checks whether data meets expectations: are IDs present and unique, are counts valid, and did the pipeline load usable data? This guide explains the tool first, then shows examples adapted to YT_ELT.

**Version scope:** the tutorial uses **Soda Core v3 and SodaCL**. Soda Core v4 uses data contracts and a different CLI; do not mix its examples with the commands below. The [official v3 README](https://github.com/sodadata/soda-core/blob/v3/README.md) documents the older workflow and recommends pinning a v3 version when staying with it.

## 1. What Soda does

You describe expectations in YAML. Soda connects to the database, calculates metrics, compares them with thresholds, and reports the results. For PostgreSQL, it runs SQL against the tables; it does not need a CSV export.

```text
configuration.yml                    checks.yml
Where is the data?                   What should be true?
         \                              /
          +-------- Soda scan ---------+
                         |
                SQL queries in PostgreSQL
                         |
                Metrics vs. thresholds
                         |
               Results + process exit code
                         |
               Airflow/CI decides what follows
```

| Term | Meaning | Example |
|---|---|---|
| Soda Core | Open-source Python library and CLI used in this guide | Installed through the PostgreSQL connector package |
| Connector | Database-specific support | `soda-core-postgres` for v3 |
| SodaCL | Soda Checks Language, written in YAML | `row_count > 0` |
| Metric | A measured value | Number of missing IDs |
| Check | A metric plus an expectation | Missing IDs must equal zero |
| Scan | One execution of a set of checks | Scan `core.yt_api` after loading |
| Soda Cloud | Hosted collaboration, result history, and alerting | Optional for these local Core examples |

Soda **detects** issues. Correcting data, retrying a load, and stopping downstream tasks require your pipeline logic. [Soda Core overview](https://github.com/sodadata/soda-core/blob/v3/README.md).

## 2. What can be checked?

| Quality question | Example rule | Meaning |
|---|---|---|
| Did anything load? | `row_count > 0` | Table must contain data |
| Are required values present? | `missing_count("Video_ID") = 0` | No NULL IDs |
| Are identifiers unique? | `duplicate_count("Video_ID") = 0` | No duplicate IDs |
| Are numbers plausible? | `min("Video_Views") >= 0` | No negative non-NULL view counts |
| Are fields available? | Schema check | Expected columns and types exist |
| Is data recent enough? | `freshness(loaded_at) < 1d` | Latest ingestion timestamp is under one day old |
| Do relationships hold? | Reference check or custom SQL | IDs exist in a parent table; values agree across columns |

The freshness example is general: this project's tables do not currently have `loaded_at`. `Upload_Date` measures a video's publication time, so old videos do not prove the pipeline is stale. Built-in examples appear in the [v3 README](https://github.com/sodadata/soda-core/blob/v3/README.md).

**NULL is the default meaning of missing.** Empty strings or placeholders such as `N/A` need explicit missing-value configuration. Numeric comparisons also do not establish that a value is present; add missing checks when required. [Missing metrics](https://docs.soda.io/soda-v3/sodacl-reference/missing-metrics).

Soda complements **pytest**: Soda checks datasets, while pytest is useful for testing Python functions, transformations, and application behavior. PostgreSQL constraints enforce rules at write time. For example, this project's primary key already rejects NULL and duplicate IDs; Soda makes those expectations visible alongside broader quality checks.

## 3. Where the files belong in this project

```text
YT_ELT/
├── Markdowns/Testing/
│   └── Soda_Data_Quality_Overview_and_Commands.md  # This guide
├── include/soda/                                 # Suggested future runtime files
│   ├── configuration.yml                        # Connection settings
│   └── checks.yml                               # Data expectations
└── tests/                                       # Future pytest tests
```

Only the documentation folder/file is introduced here. The runtime YAML below is illustrative and has not been installed or executed. The existing Compose file already mounts `include/` at `/opt/airflow/include` and `tests/` at `/opt/airflow/tests`.

Examples target this repository's `staging.yt_api` and `core.yt_api`, defined in [data_utils.py](../../dags/datawarehouse/data_utils.py). PostgreSQL requires double quotes around the project's mixed-case column names. The related Astro project at `C:\Astro\Airflow\learning-airflow` is a separate runtime; these paths and commands target YT_ELT's Compose stack.

## 4. Installation and command essentials

For this course workflow, a future `requirements.txt` entry can constrain the connector to v3:

```text
soda-core-postgres>=3.5,<4
```

Resolve compatibility with the Airflow image and pin the exact working version before adopting it. Rebuilding the image installs the dependency persistently; installing interactively in a running container is temporary. The repository's requirements currently contain no Soda dependency. See the existing [image build guide](../Docker/Podman_Build_and_Push_Steps.md) for the build/push process. Publishing to Docker Hub is only needed when the runtime will pull the image from there.

After a rebuilt image is running, open its worker shell from **PowerShell in the YT_ELT root**:

```powershell
podman compose exec airflow-worker bash
```

Use `docker compose` instead if Docker Engine hosts your YT_ELT stack. The commands that follow run **inside that Linux container**:

```bash
cd /opt/airflow
python -m pip show soda-core-postgres
soda --version
soda --help
soda test-connection --help
soda scan --help
```

`pip show` confirms the installed package; `--help` confirms the options available in that version. The [v3 installation overview](https://github.com/sodadata/soda-core/blob/v3/README.md) identifies the PostgreSQL package.

| Command or option | Purpose |
|---|---|
| `soda test-connection` | Verify database connectivity; does not run quality checks |
| `soda scan` | Execute the checks in the supplied YAML file(s) |
| `-d pg_data_source` | Select the named data source from the configuration |
| `-c PATH` | Supply the connection configuration file |
| `-v SODA_SCHEMA=core` | Supply a scan variable; lowercase `v` |
| `-V` | Show verbose output, including scan SQL; uppercase `V` |
| `-srf PATH` | Write scan results to a JSON file |
| Final positional path(s) | Identify the checks YAML file(s) |

The scan syntax is documented in [Run a Soda Core scan](https://github.com/sodadata/soda-core/blob/v3/docs/scan-core.md). Flags belong to their subcommand; consult its help before reusing them elsewhere.

## 5. Example connection configuration

If implementing later, save this as `include/soda/configuration.yml`:

```yaml
data_source pg_data_source:
  type: postgres
  host: ${POSTGRES_CONN_HOST}
  port: ${POSTGRES_CONN_PORT}
  username: ${ELT_DATABASE_USERNAME}
  password: ${ELT_DATABASE_PASSWORD}
  database: ${ELT_DATABASE_NAME}
  schema: ${SODA_SCHEMA}
```

`pg_data_source` is a Soda alias, not the database name. These connection variables are already passed into YT_ELT's Airflow containers by Compose; `SODA_SCHEMA` is the additional value supplied below. A `.env` file is not automatically a Soda environment loader.

From the worker, the database address is `postgres:5432`; Windows clients use `localhost:5433` with the current Compose defaults. Never put real passwords in example YAML. [PostgreSQL connection fields](https://docs.soda.io/soda-v3/data-source-reference/connect-postgres).

Test from the same container shell:

```bash
export SODA_SCHEMA=core
soda test-connection -d pg_data_source -c include/soda/configuration.yml -V
```

A successful connection verifies access to PostgreSQL. It does not establish that tables exist, checks pass, or permissions cover every query. [Test-connection reference](https://docs.soda.io/soda-v3/data-source-reference/connect-postgres).

## 6. Example checks: built-in metrics and custom SQL

Example `include/soda/checks.yml`:

```yaml
checks for yt_api:
  - row_count > 0
  - missing_count("Video_ID") = 0
  - duplicate_count("Video_ID") = 0
  - min("Video_Views") >= 0
  - likes_exceed_views = 0:
      name: No videos with more likes than views
      likes_exceed_views query: |
        SELECT COUNT(*)
        FROM ${SODA_SCHEMA}.yt_api
        WHERE "Likes_Count" > "Video_Views"
```

Read the custom check as: **count rows where likes exceed views, then require that count to equal zero**. The SQL returns one row containing a number; zero means zero violations, not zero SQL result rows. `likes_exceed_views query` must match the custom metric name. Indentation and the colon before nested properties matter. [User-defined checks](https://docs.soda.io/soda-v3/sodacl-reference/user-defined).

| Views | Likes | Contribution to `likes_exceed_views` |
|---:|---:|---|
| 1,000 | 80 | 0: comparison is false |
| 50 | 70 | 1: comparison is true |
| 100 | NULL | 0: SQL comparison is unknown; use a separate missing check if required |

For these three illustrative rows, the metric is **1**, so `= 0` fails. These are learning rules, not proof that all upstream YouTube statistics must always agree.

The transcript briefly reverses the inequality: its intended rule is **likes ≤ views**. Its analogous comments rule is especially worth reconsidering: viewers can leave multiple comments, so comments ≤ views is not a universal invariant. Choose checks from the actual data contract rather than adopting every tutorial assumption.

To reuse the YAML across layers, run these separately in the worker shell:

```bash
soda scan -d pg_data_source -c include/soda/configuration.yml -v SODA_SCHEMA=core -V include/soda/checks.yml
soda scan -d pg_data_source -c include/soda/configuration.yml -v SODA_SCHEMA=staging -V include/soda/checks.yml
```

The variable controls both the configured schema and the custom SQL's table reference. Keep it to trusted schema names such as `core` and `staging`: substitution is not SQL parameter binding. [Variables](https://docs.soda.io/soda-v3/sodacl-reference/filters).

## 7. Results, troubleshooting, and pipeline use

| Outcome | Interpretation | Typical next step |
|---|---|---|
| Pass | Measured data meets the rule | Continue |
| Warn | A configured warning threshold was reached | Investigate according to policy |
| Fail | Scan ran, but data violates the rule | Inspect data and upstream logic |
| Error | Soda could not evaluate reliably | Fix YAML, SQL, credentials, or permissions |

Warning thresholds must be explicitly configured; a failed check does not automatically become a warning. [Check configurations](https://docs.soda.io/soda-v3/sodacl-reference/optional-config).

For automation, v3 scan exit codes are **0** for success, **1** for warnings, **2** for failed checks, and **3/4** for runtime errors (distinguished by result submission status). Treat runtime errors as an incomplete evaluation. Airflow/CI must explicitly apply your desired warning/failure policy. [Exit-code reference](https://docs.soda.io/soda-v3/quick-start-sip/programmatic).

To save machine-readable output:

```bash
soda scan -d pg_data_source -c include/soda/configuration.yml -v SODA_SCHEMA=core -srf /tmp/soda-core-results.json include/soda/checks.yml
scan_status=$?
echo "Soda exit code: $scan_status"
```

Capture `$?` immediately after the scan in Bash; `/tmp` is inside the container. The JSON option is documented in [Run a Soda Core scan](https://github.com/sodadata/soda-core/blob/v3/docs/scan-core.md).

| Symptom | Check first |
|---|---|
| `soda: command not found` | Correct container, rebuilt image, installed connector |
| Unresolved variable | Container environment or the scan's `-v` value |
| Connection refused | Engine/network, `postgres:5432` inside the worker |
| Missing relation/column | Selected schema, `yt_api` name, quoted mixed-case columns |
| YAML or custom-metric error | Indentation, spelling, colon, matching metric/query key |
| Counts pass despite no data | Include `row_count > 0`; zero violations can describe an empty table |

A useful future Airflow sequence is `load staging → scan staging → transform/load core → scan core → downstream consumers`. Run each scan after the relevant database transaction commits. A failing scan should affect task state through the exit code or explicit Python result handling; logging the result alone does not create a quality gate.

Tutorial context: [Udemy lecture 52043831](https://www.udemy.com/course/start-your-data-engineering-journey-project-based-learning/learn/lecture/52043831#notes), using the supplied transcript. Examples here adapt the lecture to this repository and correct its ambiguous assumptions.
