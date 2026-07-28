from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .client import SupabaseAuthClient
from .schemas import UserResponse

class CustomHTTPBearer(HTTPBearer):
    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials:
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Access token required"
                )
            return None
            
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Access token required"
                )
            return None
            
        token = parts[1]
        if not token.strip():
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Access token required"
                )
            return None
            
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

security = CustomHTTPBearer(auto_error=True)
auth_client = SupabaseAuthClient()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserResponse:
    """
    Dependency to validate the Bearer token presence and return a dummy user for Stage 2.
    Route should simply accept the presence of a token.
    """
    token = credentials.credentials
    
    # Stage 2: Do NOT verify the token yet and do not contact Supabase.
    return UserResponse(
        id="00000000-0000-0000-0000-000000000000",
        email="unverified@example.com",
        user_metadata={"status": "unverified", "token": token}
    )
