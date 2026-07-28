import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, StrictStr, StrictBool
from typing import Optional, List
from database import init_db, get_db_connection
from repository import TaskRepository
from seed import seed_db

app = FastAPI(
    title="Task API - AI Version",
    version="1.0",
    description="An alternative AI-generated implementation of the task management API using Repository Pattern.",
)

@app.on_event("startup")
def on_startup():
    init_db()

# Pydantic schemas for documentation and validation
class Task(BaseModel):
    id: int
    title: str
    done: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class TaskCreate(BaseModel):
    title: StrictStr = Field(..., description="The title of the task")

class TaskUpdate(BaseModel):
    title: Optional[StrictStr] = Field(None, description="The updated title of the task")
    done: Optional[StrictBool] = Field(None, description="The updated status of the task")

class ErrorResponse(BaseModel):
    error: str

# Custom exception handler for Pydantic validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    if errors:
        err = errors[0]
        loc = err.get("loc", [])
        field = loc[-1] if loc else "field"
        msg = err.get("msg", "Invalid value")
        err_type = err.get("type", "")
        if err_type == "missing":
            return JSONResponse(status_code=400, content={"error": "Title is required"})
        elif "string" in err_type:
            return JSONResponse(status_code=400, content={"error": "Title must be a string"})
        elif "bool" in err_type:
            return JSONResponse(status_code=400, content={"error": "Done must be a boolean"})
        return JSONResponse(status_code=400, content={"error": f"Invalid value for {field}: {msg}"})
    return JSONResponse(status_code=400, content={"error": "Invalid request body"})

@app.get("/", response_model=dict, summary="Root Metadata")
def read_root():
    return {
        "name": "Task API - AI Version",
        "version": "1.0",
        "endpoints": ["/tasks"]
    }

@app.get("/health", response_model=dict, summary="Health Status")
def read_health():
    return {"status": "ok"}

@app.get("/tasks", response_model=List[Task], summary="List Tasks")
def get_tasks(done: Optional[bool] = None, search: Optional[str] = None):
    conn = get_db_connection()
    try:
        repo = TaskRepository(conn)
        return repo.get_all(done, search)
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Failed to retrieve tasks"})
    finally:
        conn.close()

@app.get("/tasks/{task_id}", response_model=Task, summary="Get Task by ID")
def get_task(task_id: int):
    conn = get_db_connection()
    try:
        repo = TaskRepository(conn)
        task = repo.get_by_id(task_id)
        if task:
            return task
        return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Failed to retrieve task"})
    finally:
        conn.close()

@app.post("/tasks", response_model=Task, status_code=201, summary="Create Task")
async def create_task(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    if not isinstance(body, dict):
        return JSONResponse(status_code=400, content={"error": "Request body must be a JSON object"})

    if "title" not in body:
        return JSONResponse(status_code=400, content={"error": "Title is required"})

    title = body["title"]
    if not isinstance(title, str):
        return JSONResponse(status_code=400, content={"error": "Title must be a string"})

    if not title.strip():
        return JSONResponse(status_code=400, content={"error": "Title cannot be empty or whitespace only"})

    conn = get_db_connection()
    try:
        repo = TaskRepository(conn)
        new_task = repo.create(title)
        return JSONResponse(status_code=201, content=new_task)
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Failed to create task"})
    finally:
        conn.close()

@app.put("/tasks/{task_id}", response_model=Task, summary="Update Task")
async def update_task(task_id: int, request: Request):
    conn = get_db_connection()
    try:
        repo = TaskRepository(conn)
        target_task = repo.get_by_id(task_id)
        if not target_task:
            return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})

        try:
            body = await request.json()
        except Exception:
            return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

        if not isinstance(body, dict) or not body:
            return JSONResponse(status_code=400, content={"error": "At least one update field must be provided"})

        has_title = "title" in body
        has_done = "done" in body

        if not has_title and not has_done:
            return JSONResponse(status_code=400, content={"error": "At least one update field must be provided"})

        if has_title:
            title = body["title"]
            if not isinstance(title, str):
                return JSONResponse(status_code=400, content={"error": "Title must be a string"})
            if not title.strip():
                return JSONResponse(status_code=400, content={"error": "Title cannot be empty or whitespace only"})

        if has_done:
            done = body["done"]
            if not isinstance(done, bool):
                return JSONResponse(status_code=400, content={"error": "Done must be a boolean"})

        updated_title = body["title"] if has_title else target_task["title"]
        updated_done = body["done"] if has_done else target_task["done"]

        updated_task = repo.update(task_id, updated_title, updated_done)
        if not updated_task:
            return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})
        return JSONResponse(status_code=200, content=updated_task)
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Failed to update task"})
    finally:
        conn.close()

@app.delete("/tasks/{task_id}", status_code=204, summary="Delete Task")
def delete_task(task_id: int):
    conn = get_db_connection()
    try:
        repo = TaskRepository(conn)
        deleted_id = repo.delete(task_id)
        if deleted_id is None:
            return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})
        return Response(status_code=204)
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Failed to delete task"})
    finally:
        conn.close()

@app.post("/reset", summary="Reset Tasks")
def reset_tasks():
    conn = get_db_connection()
    try:
        repo = TaskRepository(conn)
        repo.reset()
        seed_db(conn)
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Failed to reset tasks"})
    finally:
        conn.close()
    return {"message": "Tasks reset successfully"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
