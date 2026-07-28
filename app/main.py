import uvicorn
import os
import redis
from fastapi import FastAPI, Request, Response, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field
from typing import List, Optional
from .database import init_db, get_db_connection
from .seed import seed_db
from .crud import db_get_tasks, db_get_task_by_id, db_get_stats, db_create_task, db_update_task, db_delete_task, db_reset_tasks, db_get_detailed_stats

# Auth integration imports
from .auth.router import router as auth_router
from .auth.dependencies import get_current_user
from .auth.schemas import UserResponse

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

app = FastAPI(
    title="Task API",
    version="1.0",
    description=(
        "A task-management REST API with Supabase Auth integration.\n\n"
        "## Authentication\n\n"
        "Protected endpoints require a **Bearer JWT** issued by Supabase.\n\n"
        "**Workflow:**\n"
        "1. `POST /auth/signup` — create an account\n"
        "2. `POST /auth/login` — receive an `access_token`\n"
        "3. Click **Authorize** (top-right) and paste the token\n"
        "4. Call any 🔒 protected endpoint\n"
        "5. `POST /auth/logout` — invalidate the session\n\n"
        "Public endpoints (🔓) work without any token."
    ),
    openapi_tags=[
        {
            "name": "Authentication",
            "description": "Signup, login, and logout via Supabase Auth.",
        },
        {
            "name": "Protected",
            "description": "Endpoints that require a valid Bearer JWT. "
                           "Click **Authorize** and paste your `access_token` first.",
        },
        {
            "name": "Tasks",
            "description": "Public CRUD operations on the task list.",
        },
    ],
)

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

# Mount the Auth Router
app.include_router(auth_router)

@app.on_event("startup")
def on_startup():
    init_db()
    conn = get_db_connection()
    try:
        seed_db(conn)
    finally:
        conn.close()

    # Redis ping check
    try:
        r = redis.Redis.from_url(REDIS_URL)
        r.ping()
        print("Redis connection check successful: PING -> PONG")
    except Exception as e:
        print(f"Redis connection check failed: {e}. Note: Redis is not mandatory for CRUD.")






# Pydantic schemas for documentation
class Task(BaseModel):
    id: int = Field(..., description="The unique integer ID of the task")
    title: str = Field(..., description="The title of the task")
    done: bool = Field(..., description="The status of the task")
    created_at: Optional[str] = Field(None, description="The creation timestamp of the task")
    updated_at: Optional[str] = Field(None, description="The last update timestamp of the task")


class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message details")

class StatsResponse(BaseModel):
    total: int = Field(..., description="The total number of tasks")
    done: int = Field(..., description="The number of tasks that are completed")
    open: int = Field(..., description="The number of tasks that are not completed")

@app.get(
    "/",
    summary="Get API Metadata",
    description="Returns metadata about the Task API, including name, version, and endpoints.",
    responses={
        200: {
            "description": "API metadata returned successfully.",
            "content": {
                "application/json": {
                    "example": {
                        "name": "Task API",
                        "version": "1.0",
                        "endpoints": ["/tasks"]
                    }
                }
            }
        }
    }
)
def read_root():
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"]
    }

@app.get(
    "/health",
    summary="Check API Health Status",
    description="Returns the health status of the server and database connection.",
    responses={
        200: {
            "description": "Server and database are healthy.",
            "content": {
                "application/json": {
                    "example": {"status": "ok", "database": "connected"}
                }
            }
        },
        503: {
            "description": "Database is not connected.",
            "content": {
                "application/json": {
                    "example": {"status": "error", "database": "disconnected"}
                }
            }
        }
    }
)
def read_health():
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            return {"status": "ok", "database": "connected"}
        finally:
            conn.close()
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "database": "disconnected"}
        )

@app.get(
    "/tasks",
    summary="List All Tasks",
    description="Retrieves a list of all existing tasks stored in-memory, optionally filtered by done status and/or search term.",
    response_model=List[Task],
    responses={
        200: {
            "description": "Successfully retrieved task list."
        }
    }
)
def get_tasks(
    done: Optional[bool] = None,
    search: Optional[str] = None,
    sort: Optional[str] = None,
    order: Optional[str] = "asc"
):
    if sort is not None and sort not in ["id", "title", "done"]:
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid sort field: {sort}. Allowed fields: id, title, done"}
        )
    if order is not None and order.lower() not in ["asc", "desc"]:
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid order: {order}. Allowed values: asc, desc"}
        )

    conn = get_db_connection()
    try:
        return db_get_tasks(conn, done, search, sort, order)
    finally:
        conn.close()

@app.get(
    "/stats",
    summary="Get Task Statistics",
    description="Returns calculated statistics (total, done, open tasks) from the current in-memory task list.",
    response_model=StatsResponse,
    responses={
        200: {
            "description": "Successfully retrieved stats."
        }
    }
)
def get_stats():
    conn = get_db_connection()
    try:
        return db_get_stats(conn)
    finally:
        conn.close()

class DetailedStatsResponse(BaseModel):
    total_tasks: int = Field(..., description="The total number of tasks")
    completed_tasks: int = Field(..., description="The number of completed tasks")
    pending_tasks: int = Field(..., description="The number of pending tasks")
    completion_percentage: float = Field(..., description="The completion percentage of tasks")

@app.get(
    "/tasks/stats",
    summary="Get Detailed Task Statistics",
    description="Returns detailed statistics including total, completed, pending tasks and completion percentage.",
    response_model=DetailedStatsResponse,
    responses={
        200: {
            "description": "Successfully retrieved detailed stats."
        }
    }
)
def get_detailed_stats():
    conn = get_db_connection()
    try:
        return db_get_detailed_stats(conn)
    finally:
        conn.close()

@app.post(
    "/reset",
    summary="Reset Tasks",
    description="Restores the original 3 example tasks back into the in-memory store.",
    responses={
        200: {
            "description": "Successfully reset tasks list to original seed data.",
            "content": {
                "application/json": {
                    "example": {"message": "Tasks reset successfully"}
                }
            }
        }
    }
)
def reset_tasks():
    conn = get_db_connection()
    try:
        db_reset_tasks(conn)
        seed_db(conn)
    finally:
        conn.close()
    return {"message": "Tasks reset successfully"}


@app.get(
    "/tasks/{task_id}",
    summary="Retrieve a Task by ID",
    description="Fetches a specific task using its unique integer ID.",
    response_model=Task,
    responses={
        200: {
            "description": "Successfully retrieved task."
        },
        404: {
            "model": ErrorResponse,
            "description": "Task not found."
        }
    }
)
def get_task(task_id: int):
    conn = get_db_connection()
    try:
        task = db_get_task_by_id(conn, task_id)
        if task:
            return task
        return JSONResponse(status_code=404, content={"error": "Task not found"})
    finally:
        conn.close()

@app.post(
    "/tasks",
    summary="Create a New Task",
    description="Creates a new task with an auto-incremented ID and done set to False.",
    response_model=Task,
    status_code=201,
    responses={
        201: {
            "description": "Task successfully created."
        },
        400: {
            "model": ErrorResponse,
            "description": "Missing, empty, whitespace-only, or invalid title format."
        }
    }
)
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
        new_task = db_create_task(conn, title)
        return JSONResponse(status_code=201, content=new_task)
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Failed to create task"})
    finally:
        conn.close()

@app.put(
    "/tasks/{task_id}",
    summary="Update a Task by ID",
    description="Updates the title, done status, or both fields of a specific task.",
    response_model=Task,
    responses={
        200: {
            "description": "Task successfully updated."
        },
        400: {
            "model": ErrorResponse,
            "description": "No valid fields provided, invalid title format, or non-boolean done state."
        },
        404: {
            "model": ErrorResponse,
            "description": "Task not found."
        }
    }
)
async def update_task(task_id: int, request: Request):
    conn = get_db_connection()
    try:
        # First verify if task exists
        target_task = db_get_task_by_id(conn, task_id)
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

        updated_task = db_update_task(conn, task_id, updated_title, updated_done)
        if not updated_task:
            return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})
        return JSONResponse(status_code=200, content=updated_task)
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Failed to update task"})
    finally:
        conn.close()

@app.delete(
    "/tasks/{task_id}",
    summary="Delete a Task by ID",
    description="Deletes a specific task. Returns 204 No Content.",
    status_code=204,
    responses={
        204: {
            "description": "Task successfully deleted."
        },
        404: {
            "model": ErrorResponse,
            "description": "Task not found."
        }
    }
)
def delete_task(task_id: int):
    conn = get_db_connection()
    try:
        deleted_id = db_delete_task(conn, task_id)
        if deleted_id is None:
            return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})
        return Response(status_code=204)
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Failed to delete task"})
    finally:
        conn.close()

@app.get(
    "/public/info",
    summary="Get Public Information",
    description="Returns public metadata about the application without authentication."
)
def read_public_info():
    return {
        "message": "Welcome stranger! This info is public."
    }

@app.get(
    "/protected/profile",
    tags=["Protected"],
    summary="Get Authenticated User Profile",
    description=(
        "Verifies the Bearer token against Supabase Auth and returns safe user "
        "information (id, email, created_at). Returns 401 for any invalid, "
        "expired, tampered, or revoked token."
    ),
    response_model=UserResponse,
    responses={
        200: {"description": "Authenticated user info returned."},
        401: {"description": "Missing, malformed, expired, or invalid token."},
    },
)
def read_protected_profile(current_user: UserResponse = Depends(get_current_user)):
    return current_user

@app.get(
    "/protected/dashboard",
    tags=["Protected"],
    summary="Get Authenticated User Dashboard",
    description=(
        "Returns a welcome message and verified user information. "
        "Requires a valid Bearer token. Protected via the shared "
        "get_current_user dependency — no authentication logic duplicated here."
    ),
    responses={
        200: {"description": "Dashboard data returned."},
        401: {"description": "Missing, malformed, expired, or invalid token."},
    },
)
def read_protected_dashboard(
    current_user: UserResponse = Depends(get_current_user),
):
    return {
        "message": "Welcome to your dashboard.",
        "user": current_user,
    }

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        tags=app.openapi_tags,
        routes=app.routes,
    )

    # ── Ensure component sections exist ──────────────────────────────────────
    openapi_schema.setdefault("components", {})
    openapi_schema["components"].setdefault("schemas", {})

    # ── Stage 5: Declare the HTTPBearer security scheme ───────────────────────
    # This is the official FastAPI/OpenAPI pattern — no secrets are embedded;
    # only the scheme type and JWT format hint are declared.
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": (
                "Paste your Supabase `access_token` here (obtained from "
                "`POST /auth/login`). Format: `<token>` — do NOT include the "
                "word 'Bearer'; Swagger adds it automatically."
            ),
        }
    }

    # ── Stamp security requirement onto every protected path/method ───────────
    # Public routes (/public/info, /tasks/*, /health, /) intentionally omitted.
    _PROTECTED: dict[str, list[str]] = {
        "/protected/profile":   ["get"],
        "/protected/dashboard": ["get"],
        "/auth/logout":         ["post"],
    }
    for path, methods in _PROTECTED.items():
        if path in openapi_schema["paths"]:
            for method in methods:
                if method in openapi_schema["paths"][path]:
                    openapi_schema["paths"][path][method]["security"] = [
                        {"BearerAuth": []}
                    ]

    # ── CRUD request-body schemas (unchanged from previous stages) ────────────
    openapi_schema["components"]["schemas"]["TaskCreateRequest"] = {
        "type": "object",
        "required": ["title"],
        "properties": {
            "title": {
                "type": "string",
                "description": "The title of the new task",
            }
        },
    }
    openapi_schema["components"]["schemas"]["TaskUpdateRequest"] = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "The updated title of the task",
            },
            "done": {
                "type": "boolean",
                "description": "The updated done status of the task",
            },
        },
    }

    paths = openapi_schema["paths"]
    if "/tasks" in paths and "post" in paths["/tasks"]:
        paths["/tasks"]["post"]["requestBody"] = {
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/TaskCreateRequest"}
                }
            },
            "required": True,
        }
    if "/tasks/{task_id}" in paths and "put" in paths["/tasks/{task_id}"]:
        paths["/tasks/{task_id}"]["put"]["requestBody"] = {
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/TaskUpdateRequest"}
                }
            },
            "required": True,
        }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
