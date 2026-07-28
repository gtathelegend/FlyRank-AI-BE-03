import os
import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    """
    Creates and returns a connection to the PostgreSQL database.
    """
    conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
    return conn

def init_db():
    """
    Initializes the database schema if the table does not exist.
    """
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        id SERIAL PRIMARY KEY,
                        title TEXT NOT NULL,
                        done BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_title ON tasks(title)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_done ON tasks(done)")
    finally:
        conn.close()
