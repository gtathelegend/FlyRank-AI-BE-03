import uvicorn
import os
from fastapi import FastAPI, Request, Response, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from database import init_db, get_db_connection
from repository import TaskRepository
from seed import seed_db

app = FastAPI(
    title="Task API - AI Version",
    version="1.0",
    description=(
        "An AI-generated implementation of the task management API with Supabase Auth integration.\n\n"
        "## Authentication\n\n"
        "Protected endpoints require a **Bearer JWT** issued by Supabase.\n"
    ),
    openapi_tags=[
        {"name": "Authentication", "description": "Signup, login, and logout operations."},
        {"name": "Protected", "description": "Endpoints requiring valid Bearer JWT."},
        {"name": "Tasks", "description": "Task CRUD operations."},
    ],
)

@app.on_event("startup")
def on_startup():
    init_db()

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

# ------------------------------------------------------------------------------
# Auth Security & Dependencies
# ------------------------------------------------------------------------------

def _extract_bearer_token(auth_header: str | None) -> str | None:
    if not auth_header:
        return None
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1]
    return token if token.strip() else None

class CustomHTTPBearer(HTTPBearer):
    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials:
        auth_header = request.headers.get("Authorization")
        token = _extract_bearer_token(auth_header)
        if token is None:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Access token required",
                )
            return None
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

security = CustomHTTPBearer(auto_error=True)

class UserResponse(BaseModel):
    id: str = Field(..., description="The unique Supabase user ID")
    email: Optional[str] = Field(None, description="User email address")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    user_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadata")

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UserResponse:
    import httpx
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_KEY", "")

    token = credentials.credentials
    url = f"{supabase_url}/auth/v1/user"
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {token}",
    }

    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(url, headers=headers, timeout=5.0)
            if res.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                )
            data = res.json()
            return UserResponse(
                id=str(data.get("id")),
                email=data.get("email"),
                created_at=data.get("created_at"),
                user_metadata=data.get("user_metadata", {}),
            )
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

# ------------------------------------------------------------------------------
# Auth Routes
# ------------------------------------------------------------------------------

class UserCredentials(BaseModel):
    email: str
    password: str

@app.post("/auth/signup", status_code=201, tags=["Authentication"], summary="Register User")
async def signup(creds: UserCredentials):
    import httpx
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_KEY", "")

    url = f"{supabase_url}/auth/v1/signup"
    headers = {"apikey": supabase_key, "Content-Type": "application/json"}
    payload = {"email": creds.email.strip(), "password": creds.password}

    async with httpx.AsyncClient() as client:
        res = await client.post(url, headers=headers, json=payload, timeout=10.0)
        if res.status_code != 200:
            err_data = res.json() if res.headers.get("content-type") == "application/json" else {}
            msg = err_data.get("msg", "Signup failed")
            raise HTTPException(status_code=res.status_code, detail=msg)
        data = res.json()
        user_data = data.get("user", {})
        return {
            "message": "User registered successfully.",
            "user": UserResponse(
                id=str(user_data.get("id")),
                email=user_data.get("email"),
                user_metadata=user_data.get("user_metadata", {}),
            ),
        }

@app.post("/auth/login", tags=["Authentication"], summary="User Login")
async def login(creds: UserCredentials):
    import httpx
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_KEY", "")

    url = f"{supabase_url}/auth/v1/token?grant_type=password"
    headers = {"apikey": supabase_key, "Content-Type": "application/json"}
    payload = {"email": creds.email.strip(), "password": creds.password}

    async with httpx.AsyncClient() as client:
        res = await client.post(url, headers=headers, json=payload, timeout=10.0)
        if res.status_code != 200:
            err_data = res.json() if res.headers.get("content-type") == "application/json" else {}
            msg = err_data.get("error_description", "Invalid login credentials")
            raise HTTPException(status_code=res.status_code, detail=msg)
        data = res.json()
        user_data = data.get("user", {})
        return {
            "access_token": data.get("access_token"),
            "refresh_token": data.get("refresh_token"),
            "token_type": "bearer",
            "expires_in": data.get("expires_in"),
            "user": UserResponse(
                id=str(user_data.get("id")),
                email=user_data.get("email"),
                user_metadata=user_data.get("user_metadata", {}),
            ),
        }

@app.post("/auth/logout", status_code=204, tags=["Authentication"], summary="User Logout")
async def logout(
    _: UserResponse = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    import httpx
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_KEY", "")

    url = f"{supabase_url}/auth/v1/logout"
    headers = {"apikey": supabase_key, "Authorization": f"Bearer {credentials.credentials}"}

    async with httpx.AsyncClient() as client:
        try:
            await client.post(url, headers=headers, timeout=10.0)
        except Exception:
            pass
    return Response(status_code=204)

# ------------------------------------------------------------------------------
# Public & Protected Routes
# ------------------------------------------------------------------------------

@app.get("/public/info", tags=["Public"], summary="Public Information")
def public_info():
    return {"message": "Welcome stranger! This info is public."}

@app.get("/protected/profile", tags=["Protected"], summary="User Profile", response_model=UserResponse)
def protected_profile(current_user: UserResponse = Depends(get_current_user)):
    return current_user

@app.get("/protected/dashboard", tags=["Protected"], summary="User Dashboard")
def protected_dashboard(current_user: UserResponse = Depends(get_current_user)):
    return {
        "message": "Welcome to your dashboard.",
        "user": current_user,
    }

# ------------------------------------------------------------------------------
# Task CRUD Routes
# ------------------------------------------------------------------------------

class Task(BaseModel):
    id: int
    title: str
    done: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

@app.get("/tasks", response_model=List[Task], tags=["Tasks"], summary="List Tasks")
def get_tasks(done: Optional[bool] = None, search: Optional[str] = None):
    conn = get_db_connection()
    try:
        repo = TaskRepository(conn)
        return repo.get_all(done, search)
    finally:
        conn.close()

@app.get("/tasks/{task_id}", response_model=Task, tags=["Tasks"], summary="Get Task by ID")
def get_task(task_id: int):
    conn = get_db_connection()
    try:
        repo = TaskRepository(conn)
        task = repo.get_by_id(task_id)
        if task:
            return task
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    finally:
        conn.close()

@app.post("/reset", tags=["Tasks"], summary="Reset Tasks")
def reset_tasks():
    conn = get_db_connection()
    try:
        repo = TaskRepository(conn)
        repo.reset()
        seed_db(conn)
    finally:
        conn.close()
    return {"message": "Tasks reset successfully"}

# ------------------------------------------------------------------------------
# Custom OpenAPI Configuration for Bearer Auth
# ------------------------------------------------------------------------------

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

    openapi_schema.setdefault("components", {})
    openapi_schema["components"].setdefault("schemas", {})

    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Paste your Supabase access_token here.",
        }
    }

    _PROTECTED = {
        "/protected/profile": ["get"],
        "/protected/dashboard": ["get"],
        "/auth/logout": ["post"],
    }
    for path, methods in _PROTECTED.items():
        if path in openapi_schema["paths"]:
            for method in methods:
                if method in openapi_schema["paths"][path]:
                    openapi_schema["paths"][path][method]["security"] = [{"BearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
