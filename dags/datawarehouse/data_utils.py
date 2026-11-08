from airflow.providers.postgres.hooks.postgres import PostgresHook  # Airflow's PostgreSQL hook.
from psycopg2.extras import RealDictCursor  # Return rows keyed by column name.

table = "yt_api"  # Table name used by create_table() and get_video_ids().

def get_conn_cursor():
    # Use Airflow's connection settings to access elt_db.
    hook = PostgresHook(postgres_conn_id="postgres_db_yt_elt", database="elt_db")
    conn = hook.get_conn()  # Open the database session.
    cur = conn.cursor(cursor_factory=RealDictCursor)  # Execute SQL; fetch dictionary rows.
    return conn, cur


def close_conn_cursor(conn, cur):
    cur.close()  # Release the cursor.
    conn.close()  # Close the session; does not commit pending writes.

def create_schema(schema):  # Define a function to create a schema.
    conn, cur = get_conn_cursor()  # Get the connection and cursor.

    schema_sql = f"CREATE SCHEMA IF NOT EXISTS {schema};"  # Build the SQL.

    cur.execute(schema_sql)  # Execute the SQL.

    conn.commit()  # Save the changes.

    close_conn_cursor(conn, cur)  # Close the connection and cursor.

def create_table(schema):  # Create a table in the given schema.
    conn, cur = get_conn_cursor()  # Get the connection and cursor.

    if schema == 'staging':  # Use staging column types.
        table_sql = f"""
            CREATE TABLE IF NOT EXISTS {schema}.{table} (
                "Video_ID" VARCHAR(11) PRIMARY KEY NOT NULL, -- Unique video ID.
                "Video_Title" TEXT NOT NULL, -- Video title.
                "Upload_Date" TIMESTAMP NOT NULL, -- Upload date and time.
                "Duration" VARCHAR(20) NOT NULL, -- Duration as text.
                "Video_Views" INT, -- View count.
                "Likes_Count" INT, -- Like count.
                "Comments_Count" INT -- Comment count.
            );
        """
    else:  # Use warehouse column types.
        table_sql = f"""
            CREATE TABLE IF NOT EXISTS {schema}.{table} (
                "Video_ID" VARCHAR(11) PRIMARY KEY NOT NULL, -- Unique video ID.
                "Video_Title" TEXT NOT NULL, -- Video title.
                "Upload_Date" TIMESTAMP NOT NULL, -- Upload date and time.
                "Duration" TIME NOT NULL, -- Duration as time.
                "Video_Type" VARCHAR(10) NOT NULL, -- Video category.
                "Video_Views" INT, -- View count.
                "Likes_Count" INT, -- Like count.
                "Comments_Count" INT -- Comment count.
            );
        """

    cur.execute(table_sql)  # Execute the SQL.
    conn.commit()  # Save the changes.
    close_conn_cursor(conn, cur)  # Close the connection and cursor.

def get_video_ids(cur, schema):  # Get video IDs from the given schema.
    cur.execute(f"""SELECT "Video_ID" FROM {schema}.{table};""")  # Query video IDs.
    ids = cur.fetchall()  # Fetch all matching rows.

    video_ids = [row["Video_ID"] for row in ids]  # Extract IDs from the rows.

    return video_ids  # Return the list of IDs.