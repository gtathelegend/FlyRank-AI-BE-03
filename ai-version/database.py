import os
import time
import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    """
    Creates and returns a connection to the PostgreSQL database.
    Retries in case database container is not ready yet.
    """
    retries = 5
    while retries > 0:
        try:
            return psycopg.connect(DATABASE_URL, row_factory=dict_row)
        except psycopg.OperationalError as e:
            retries -= 1
            if retries == 0:
                raise e
            time.sleep(2)

def init_db():
    """
    Initializes the database schema and performs seeding if the table is empty.
    """
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cursor:
                # Create table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        id SERIAL PRIMARY KEY,
                        title TEXT NOT NULL,
                        done BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                # Create indexes
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_title ON tasks(title)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_done ON tasks(done)")
                
                # Check row count for seeding
                cursor.execute("SELECT COUNT(*) AS count FROM tasks")
                count = cursor.fetchone()["count"]
                
                if count == 0:
                    seed_tasks = [
                        ("Complete backend assignment", False),
                        ("Review HTTP status codes", True),
                        ("Test API with Swagger", False)
                    ]
                    cursor.executemany(
                        "INSERT INTO tasks (title, done) VALUES (%s, %s)",
                        seed_tasks
                    )
                    conn.commit()
    finally:
        conn.close()
