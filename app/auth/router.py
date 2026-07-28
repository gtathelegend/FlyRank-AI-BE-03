from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials
from .client import SupabaseAuthClient
from .schemas import UserCredentials, TokenResponse, AuthSuccessResponse, UserResponse
from .config import validate_config
from .dependencies import security, get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])
auth_client = SupabaseAuthClient()

@router.post(
    "/signup",
    response_model=AuthSuccessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Registers a new user with email and password via Supabase Auth."
)
async def signup(credentials: UserCredentials):
    # Ensure configuration is loaded
    validate_config()
    
    # Clean inputs
    email = credentials.email.strip()
    password = credentials.password
    
    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password cannot be empty"
        )
        
    result = await auth_client.signup(email, password)
    
    # Parse results - handle both nested user and root-level user response formats
    user_data = result.get("user")
    if not isinstance(user_data, dict):
        user_data = result if "id" in result else {}

    user = UserResponse(
        id=user_data.get("id"),
        email=user_data.get("email"),
        user_metadata=user_data.get("user_metadata", {})
    )
    
    # Check if verification is required
    # In Supabase, if email confirmation is enabled, the session is empty/null on signup.
    session = result.get("session")
    message = "User registered successfully."
    if not session:
        message += " Please check your email to confirm registration before logging in."
        
    return AuthSuccessResponse(
        message=message,
        user=user
    )

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User Login",
    description="Authenticates credentials and returns a Bearer access token."
)
async def login(credentials: UserCredentials):
    validate_config()
    
    email = credentials.email.strip()
    password = credentials.password
    
    result = await auth_client.login(email, password)
    
    user_data = result.get("user", {})
    user = UserResponse(
        id=user_data.get("id"),
        email=user_data.get("email"),
        user_metadata=user_data.get("user_metadata", {})
    )
    
    return TokenResponse(
        access_token=result.get("access_token"),
        refresh_token=result.get("refresh_token"),
        token_type=result.get("token_type", "bearer"),
        expires_in=result.get("expires_in"),
        user=user
    )

@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="User Logout",
    description=(
        "Invalidates the current session token via Supabase. "
        "Requires a valid Bearer token — the token is fully verified before "
        "the session is revoked. Returns 204 No Content on success."
    ),
)
async def logout(
    _: UserResponse = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    The get_current_user dependency (via Depends) fully verifies the token
    against Supabase before this handler runs.  The raw token is then used
    to perform the actual sign-out HTTP call so we don't mutate the shared
    SDK session object.

    FastAPI deduplicates the underlying CustomHTTPBearer call automatically,
    so the Authorization header is parsed exactly once per request.
    """
    token = credentials.credentials
    try:
        await auth_client.logout(token)
    except HTTPException:
        # Already a well-formed HTTP error — re-raise unchanged.
        raise
    except Exception:
        # Network errors, unexpected SDK failures — never leak internals.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Logout failed. Please try again.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)

