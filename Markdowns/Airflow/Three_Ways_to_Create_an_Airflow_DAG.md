# Three Ways to Create an Airflow DAG: Examples, Pros, and Cons

For this project's **Airflow 2.9.2** setup.

A DAG defines a workflow: its tasks, their dependencies, and its schedule. You can create one using a **context manager**, a **decorator**, or the **direct constructor**. These are alternative ways to organize the definition; choosing one does not make tasks execute faster.

**My recommendation for your current project: use `with DAG(...)`.** It matches the lesson and keeps settings and task wiring easy to read. Use `@dag` when wrapping the workflow in a function helps organize or reuse it. The direct constructor is useful when explicit task assignment is helpful.

## 1. Context manager: `with DAG(...)`

Tasks created inside the block automatically belong to that DAG.

```python
import pendulum
from airflow import DAG
from airflow.operators.empty import EmptyOperator

with DAG(
    dag_id="example_context",
    start_date=pendulum.datetime(2025, 1, 1, tz="Africa/Cairo"),
    schedule="0 14 * * *",
    catchup=False,
) as dag:
    extract = EmptyOperator(task_id="extract")
    save = EmptyOperator(task_id="save")

    extract >> save
```

- `with DAG(...)` establishes the DAG context for task creation.
- `as dag` gives the DAG object a Python variable name; `dag_id` is its Airflow identifier.
- `extract >> save` makes `save` wait for `extract` to succeed under the default trigger rule.

**Pros:** clear grouping, little boilerplate, and no repeated `dag=` on each task.

**Cons:** task ownership relies on the surrounding context; a long block can become difficult to navigate.

The block defines the workflow when Airflow parses the file. It does **not** immediately run its tasks.

Reference: [Airflow fundamentals](https://airflow.apache.org/docs/apache-airflow/2.9.2/tutorial/fundamentals.html).

## 2. Decorator: `@dag(...)`

The decorator turns a Python function into a DAG factory. Calling the function builds the DAG.

```python
import pendulum
from airflow.decorators import dag
from airflow.operators.empty import EmptyOperator

@dag(
    dag_id="example_decorator",
    start_date=pendulum.datetime(2025, 1, 1, tz="Africa/Cairo"),
    schedule="0 14 * * *",
    catchup=False,
)
def build_pipeline():
    extract = EmptyOperator(task_id="extract")
    save = EmptyOperator(task_id="save")

    extract >> save

pipeline = build_pipeline()
```

- `@dag(...)` supplies the workflow settings.
- `build_pipeline()` groups the task definitions inside a function.
- The final call creates the DAG object; defining the function alone is insufficient.

**Pros:** keeps the workflow contained in a function and works naturally with TaskFlow tasks. A factory can create related DAGs with distinct `dag_id` values.

**Cons:** adds a function and invocation to understand; forgetting the final call leaves no DAG instance.

Reference: [declaring DAGs](https://airflow.apache.org/docs/apache-airflow/2.9.2/core-concepts/dags.html#declaring-a-dag).

## 3. Direct constructor: `DAG(...)`

Create the DAG object first, then explicitly assign tasks using `dag=pipeline`.

```python
import pendulum
from airflow import DAG
from airflow.operators.empty import EmptyOperator

pipeline = DAG(
    dag_id="example_constructor",
    start_date=pendulum.datetime(2025, 1, 1, tz="Africa/Cairo"),
    schedule="0 14 * * *",
    catchup=False,
)

extract = EmptyOperator(task_id="extract", dag=pipeline)
save = EmptyOperator(task_id="save", dag=pipeline)

extract >> save
```

**Pros:** task ownership is visible on each operator; useful when constructing tasks outside a single block.

**Cons:** repeats `dag=pipeline`, and forgetting assignment can leave a task unattached. For a straightforward pipeline, the context manager is usually easier to scan.

Reference: [DAG declaration and assignment](https://airflow.apache.org/docs/apache-airflow/2.9.2/core-concepts/dags.html#dag-assignment).

## Important distinction: `@dag` versus `@task`

`@dag` creates a **workflow factory**. `@task` turns a Python function into an **Airflow task definition**. You can use `@task` with either `with DAG(...)` or `@dag`; the context manager does not require abandoning TaskFlow.

For example, this replaces the placeholder operators inside a `with DAG(...)` block or a decorated DAG function. Add `from airflow.decorators import task` to the imports:

```python
@task
def extract():
    return ["video_1", "video_2"]

@task
def save(video_ids):
    print(video_ids)

save(extract())
```

During DAG construction, these calls create task instances and connect them. Airflow executes the function bodies later. Passing `extract()` into `save(...)` automatically establishes their dependency and transfers the returned value through XCom.

Reference: [TaskFlow tutorial](https://airflow.apache.org/docs/apache-airflow/2.9.2/tutorial/taskflow.html).

## Which should you choose?

| Your situation | Suggested approach | Why |
| --- | --- | --- |
| Your current YT_ELT lesson | **Context manager** | Clear settings followed by your imported task calls. |
| You prefer a function containing the workflow | **Decorator** | Encapsulates the definition and supports reuse. |
| You need explicit assignment outside a block | **Direct constructor** | Shows the DAG on each operator. |

This is a readability recommendation, not an Airflow requirement. All three are supported.

Each full example is independent and can be saved under `dags/`. `EmptyOperator` is a placeholder that performs no extraction or saving; it makes the structure easy to compare. The daily schedule is 14:00 Cairo time, with historical catchup disabled. Replace the placeholders with your real tasks when applying the pattern.
