def seed_db(conn):
    """
    Checks if the tasks table is empty. If empty, inserts the canonical seed tasks.
    """
    # Check current row count
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS count FROM tasks")
        row = cursor.fetchone()
        count = row["count"] if row else 0

        if count == 0:
            # Define seed tasks: boolean done maps to True/False
            seed_tasks = [
                ("Complete backend assignment", False),
                ("Review HTTP status codes", True),
                ("Test API with Swagger", False)
            ]
            
            # Insert them using parameterized queries
            cursor.executemany(
                "INSERT INTO tasks (title, done) VALUES (%s, %s)",
                seed_tasks
            )
            conn.commit()
