import psycopg
from typing import List, Optional, Dict, Any

class TaskRepository:
    """
    Repository class implementing the Repository Abstraction pattern
    to encapsulate all database access logic for tasks.
    """
    def __init__(self, conn: psycopg.Connection):
        self.conn = conn

    def get_all(self, done: Optional[bool] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
        query = "SELECT id, title, done, created_at, updated_at FROM tasks WHERE 1=1"
        params = []
        
        if done is not None:
            query += " AND done = %s"
            params.append(done)
            
        if search is not None:
            query += " AND LOWER(title) LIKE LOWER(%s)"
            params.append(f"%{search}%")
            
        query += " ORDER BY id ASC"
        
        with self.conn.cursor() as cursor:
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

    def get_by_id(self, task_id: int) -> Optional[Dict[str, Any]]:
        with self.conn.cursor() as cursor:
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

    def create(self, title: str) -> Dict[str, Any]:
        with self.conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO tasks(title, done) VALUES(%s, %s) RETURNING id, title, done;",
                (title, False)
            )
            row = cursor.fetchone()
            self.conn.commit()
            return row

    def update(self, task_id: int, title: str, done: bool) -> Optional[Dict[str, Any]]:
        with self.conn.cursor() as cursor:
            cursor.execute(
                "UPDATE tasks SET title=%s, done=%s WHERE id=%s RETURNING id, title, done;",
                (title, done, task_id)
            )
            row = cursor.fetchone()
            self.conn.commit()
            return row

    def delete(self, task_id: int) -> Optional[int]:
        with self.conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM tasks WHERE id=%s RETURNING id;",
                (task_id,)
            )
            row = cursor.fetchone()
            self.conn.commit()
            return row["id"] if row else None

    def reset(self) -> None:
        with self.conn.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE tasks RESTART IDENTITY CASCADE")
            self.conn.commit()
