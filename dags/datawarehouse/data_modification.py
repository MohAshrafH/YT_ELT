import logging  # Import Python's tools for recording messages, warnings, and errors.

logger = logging.getLogger(__name__)  # Get a logger named after this module; __name__ is "__main__" when run directly.
table = "yt_api"  # Store the destination table name used in the SQL statement.

def insert_rows(cur, conn, schema, row):  # Accept a database cursor, connection, schema name, and row values.

    try:  # Attempt this block; an except or finally block must follow in the remaining code.

        if schema == 'staging':  # Run this insert only when the supplied schema is 'staging'.

            video_id = 'video_id'  # Store a field name; this variable is not used in the visible code.

        # Build the SQL with schema/table names; %(name)s placeholders get values from the row mapping.
        # cur is the database cursor used to send SQL commands to the database.
            cur.execute(
                # f substitutes {schema} and {table}; triple quotes allow SQL across multiple lines.
                # The listed columns receive the VALUES below in the same order.
                f"""INSERT INTO {schema}.{table}("Video ID", "Video Title", "Upload Date", "Duration", "Video Views", "Likes Count", "Comments Count")
                VALUES (%(video_id)s, %(title)s, %(publishedAt)s, %(duration)s, %(viewCount)s, %(likeCount)s, %(commentCount)s);
                """,
                row  # Dictionary supplying values: %(title)s uses row["title"], and so on.
            )  # The driver safely handles value quoting; the 's' does not require string values. 
        
        else:  # Run when schema is not 'staging'.
            video_id = "Video_ID"  # Key used to read the video's ID from row for logging.

            # Insert into the supplied schema and table; columns match VALUES by position.
            cur.execute(
                f"""
                INSERT INTO {schema}.{table}("Video_ID", "Video_Title", "Upload_Date", "Duration", "Video_Type", "Video_Views", "Likes_Count", "Comments_Count")
                VALUES (%(Video_ID)s, %(Video_Title)s, %(Upload_Date)s, %(Duration)s, %(Video_Type)s, %(Video_Views)s, %(Likes_Count)s, %(Comments_Count)s)
                """,
                row,  # Supply dictionary values: %(Video_ID)s uses row["Video_ID"]; 's' does not require strings.
            )

        conn.commit()  # Save the transaction's pending database changes after either insert branch.

        # Record success; row[video_id] reads the ID using the key chosen in the relevant branch.
        logger.info(f"Inserted row with Video ID: {row[video_id]}")

    except Exception as e:  # Catch an error from the try block and store the exception in e.
        logger.error(f"Error inserting row with Video_ID: {row[video_id]}")  # Log which video's insert failed.
        raise e  # Pass the caught exception to the caller so the failure is not silently ignored.

def update_rows(cur,conn,schema,row):  # Receive a database cursor, connection, schema name, and row dictionary.
    try:  # Attempt the update, commit, and logging; failures go to the except block.
        if schema == 'staging':  # Select dictionary keys matching the staging data format.
            video_id = 'video_id'  # Key used to retrieve the video's ID from row.
            upload_date = 'publishedAt'  # Key used to retrieve the publication date.
            video_title = 'title'  # Key used to retrieve the video's title.
            video_views = 'viewCount'  # Key used to retrieve the view count.
            likes_count = 'likeCount'  # Key used to retrieve the like count.
            comments_count = 'commentCount'  # Key used to retrieve the comment count.

        # core
        else:  # Select these keys for every schema other than staging.
            video_id = 'Video_ID'  # ID key in the non-staging row format.
            upload_date = 'Upload_Date'  # Upload-date key in the non-staging row format.
            video_title = 'Video_Title'  # Title key in the non-staging row format.
            video_views = 'Video_Views'  # View-count key in the non-staging row format.
            likes_count = 'Likes_Count'  # Like-count key in the non-staging row format.
            comments_count = 'Comments_Count'  # Comment-count key in the non-staging row format.

        # The f-string inserts schema, table, and the selected dictionary key names.
        # For staging, %({video_title})s becomes %(title)s; the driver supplies row["title"].
        # UPDATE names the table; SET assigns replacement values to the listed columns.
        # WHERE matches both ID and upload date; double quotes preserve column capitalization.
        # table must already be defined elsewhere.
        cur.execute(
            f"""
            UPDATE {schema}.{table}
            SET "Video_Title" = %({video_title})s,
                "Video_Views" = %({video_views})s,
                "Likes_Count" = %({likes_count})s,
                "Comments_Count" = %({comments_count})s
            WHERE "Video_ID" = %({video_id})s AND "Upload_Date" = %({upload_date})s;
            """, row
        )  # Execute the SQL with dictionary values bound to the named placeholders.

        conn.commit()  # Save the connection's pending transaction, including this update.

        # row[video_id] retrieves the ID using the selected key; logger is defined elsewhere.
        logger.info(f"Updated row with Video_ID: {row[video_id]}")  # Record successful execution with the video's ID.

    except Exception as e:  # Catch an Exception raised in the try block and store it in e.
        logger.error(f"Error updating row with Video_ID: {row[video_id]} - {e}")  # Log the video's ID and error message.
        raise e  # Raise the caught exception again so the caller can handle it.


def delete_rows(cur, conn, schema, ids_to_delete):  # Receive a cursor, connection, schema name, and collection of video IDs.
    try:  # Attempt the deletion and logging; failures go to the except block.
        # Wrap each ID in single quotes, join them with commas, and surround the list with parentheses.
        ids_to_delete = f"""({', '.join(f"'{id}'" for id in ids_to_delete)})"""

        # The f-string inserts the schema, table, and formatted IDs directly into the SQL.
        # table must be defined elsewhere; IN matches any ID in the parenthesized list.
        cur.execute(
            f"""
            DELETE FROM {schema}.{table}
            WHERE "Video_ID" IN {ids_to_delete};
            """
        )  # Delete all records whose Video_ID matches one of the supplied IDs.

        conn.commit()  # Save the connection's pending transaction, including these deletions.
        logger.info(f"Deleted rows with Video_IDs: {ids_to_delete}")  # Log the formatted IDs; logger must be defined elsewhere.

    except Exception as e:  # Catch an Exception from the try block and store it in e.
        logger.error(f"Error deleting rows with Video_IDs: {ids_to_delete} - {e}")  # Log the IDs and error message.
        raise e  # Raise the caught exception again so the caller can handle it.    