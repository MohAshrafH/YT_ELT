from airflow.providers.postgres.hooks.postgres import PostgresHook  # Airflow's PostgreSQL hook.
from psycopg2.extras import RealDictCursor  # Return rows keyed by column name.


def get_conn_cursor():
    # Use Airflow's connection settings to access elt_db.
    hook = PostgresHook(postgres_conn_id="postgres_db_yt_elt", database="elt_db")
    conn = hook.get_conn()  # Open the database session.
    cur = conn.cursor(cursor_factory=RealDictCursor)  # Execute SQL; fetch dictionary rows.
    return conn, cur


def close_conn_cursor(conn, cur):
    cur.close()  # Release the cursor.
    conn.close()  # Close the session; does not commit pending writes.