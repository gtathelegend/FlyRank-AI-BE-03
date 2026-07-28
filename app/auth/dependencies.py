from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .schemas import UserResponse


def _extract_bearer_token(auth_header: str | None) -> str | None:
    """
    Parse the Authorization header and return the raw token string.
    Returns None if the header is missing, not Bearer-prefixed,
    has extra parts, or the token portion is empty.
    """
    if not auth_header:
        return None
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1]
    return token if token.strip() else None


class CustomHTTPBearer(HTTPBearer):
    """
    Drop-in replacement for HTTPBearer that returns a consistent
    {"error": "Access token required"} 401 on any header problem
    instead of FastAPI's default {"detail": "..."} shape.
    """
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


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UserResponse:
    """
    Stage 3: Verify the Bearer token against Supabase.

    Calls supabase.auth.get_user(token) — the SDK validates the JWT
    server-side; no local decoding is performed here.

    Raises 401 with a generic message on any failure so that
    Supabase internals, stack traces, and token values are never
    leaked to the caller.
    """
    # Import here to avoid a circular import and to keep the
    # supabase client initialisation outside the module-level scope
    # of this auth helper.
    from app.supabase_client import supabase

    token = credentials.credentials  # already validated non-empty by CustomHTTPBearer

    try:
        response = supabase.auth.get_user(token)
        user = response.user

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

        # Safely coerce created_at to an ISO-8601 string regardless of
        # whether Supabase returns a datetime object or a plain string.
        created_at_raw = getattr(user, "created_at", None)
        if created_at_raw is not None and hasattr(created_at_raw, "isoformat"):
            created_at = created_at_raw.isoformat()
        else:
            created_at = str(created_at_raw) if created_at_raw is not None else None

        return UserResponse(
            id=str(user.id),
            email=user.email,
            created_at=created_at,
            user_metadata=dict(user.user_metadata) if user.user_metadata else {},
        )

    except HTTPException:
        # Re-raise our own 401s unchanged.
        raise
    except Exception:
        # Catch AuthApiError, network errors, malformed responses, etc.
        # Never log the token or expose Supabase internals.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
