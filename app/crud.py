import psycopg
from typing import List, Optional, Dict, Any

def db_get_tasks(
    conn: psycopg.Connection,
    done: Optional[bool] = None,
    search: Optional[str] = None,
    sort: Optional[str] = None,
    order: Optional[str] = "asc"
) -> List[Dict[str, Any]]:
    """
    Fetches tasks from the PostgreSQL database with optional filters, search, and sorting.
    """
    query = "SELECT id, title, done, created_at, updated_at FROM tasks WHERE 1=1"
    params = []

    if done is not None:
        query += " AND done = %s"
        params.append(done)

    if search is not None:
        query += " AND LOWER(title) LIKE LOWER(%s)"
        params.append(f"%{search}%")

    if sort is not None:
        if sort in ["id", "title", "done"]:
            direction = "DESC" if order.lower() == "desc" else "ASC"
            query += f" ORDER BY {sort} {direction}"
    else:
        query += " ORDER BY id ASC"

    with conn.cursor() as cursor:
        cursor.execute(query, params)
        rows = cursor.fetchall()

    tasks = []
    for row in rows:
        tasks.append({
            "id": row["id"],
            "title": row["title"],
            "done": row["done"],
            "created_at": row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else row["created_at"],
            "updated_at": row["updated_at"].isoformat() if hasattr(row["updated_at"], "isoformat") else row["updated_at"]
        })
    return tasks

def db_get_task_by_id(conn: psycopg.Connection, task_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetches a task by its ID from the PostgreSQL database.
    """
    with conn.cursor() as cursor:
        cursor.execute("SELECT id, title, done, created_at, updated_at FROM tasks WHERE id = %s", (task_id,))
        row = cursor.fetchone()
        if row:
            return {
                "id": row["id"],
                "title": row["title"],
                "done": row["done"],
                "created_at": row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else row["created_at"],
                "updated_at": row["updated_at"].isoformat() if hasattr(row["updated_at"], "isoformat") else row["updated_at"]
            }
    return None

def db_get_stats(conn: psycopg.Connection) -> Dict[str, int]:
    """
    Calculates task statistics directly from the database.
    """
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS total FROM tasks")
        row = cursor.fetchone()
        total = row["total"] if row else 0

        cursor.execute("SELECT COUNT(*) AS done_count FROM tasks WHERE done = TRUE")
        row = cursor.fetchone()
        done_count = row["done_count"] if row else 0

    open_count = total - done_count

    return {
        "total": total,
        "done": done_count,
        "open": open_count
    }

def db_get_detailed_stats(conn: psycopg.Connection) -> Dict[str, Any]:
    """
    Calculates detailed task statistics using SQL.
    """
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS total FROM tasks")
        row = cursor.fetchone()
        total = row["total"] if row else 0

        cursor.execute("SELECT COUNT(*) AS completed FROM tasks WHERE done = TRUE")
        row = cursor.fetchone()
        completed = row["completed"] if row else 0

    pending = total - completed
    percentage = (completed / total) * 100.0 if total > 0 else 0.0

    return {
        "total_tasks": total,
        "completed_tasks": completed,
        "pending_tasks": pending,
        "completion_percentage": round(percentage, 2)
    }

def db_create_task(conn: psycopg.Connection, title: str) -> Dict[str, Any]:
    """
    Inserts a new task into the database.
    """
    with conn.cursor() as cursor:
        cursor.execute(
            "INSERT INTO tasks(title,done) VALUES(%s,%s) RETURNING id,title,done;",
            (title, False)
        )
        row = cursor.fetchone()
        conn.commit()
        return row

def db_update_task(conn: psycopg.Connection, task_id: int, title: str, done: bool) -> Optional[Dict[str, Any]]:
    """
    Updates the task in the database and returns the updated row.
    """
    with conn.cursor() as cursor:
        cursor.execute(
            "UPDATE tasks SET title=%s, done=%s WHERE id=%s RETURNING id,title,done;",
            (title, done, task_id)
        )
        row = cursor.fetchone()
        conn.commit()
        return row

def db_delete_task(conn: psycopg.Connection, task_id: int) -> Optional[int]:
    """
    Deletes a task by its ID and returns the deleted task's ID if found.
    """
    with conn.cursor() as cursor:
        cursor.execute(
            "DELETE FROM tasks WHERE id=%s RETURNING id;",
            (task_id,)
        )
        row = cursor.fetchone()
        conn.commit()
        return row["id"] if row else None

def db_reset_tasks(conn: psycopg.Connection) -> None:
    """
    Deletes all tasks and resets the serial sequence within a transaction.
    """
    with conn.cursor() as cursor:
        cursor.execute("TRUNCATE TABLE tasks RESTART IDENTITY CASCADE")
        conn.commit()
