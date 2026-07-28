import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .config import SUPABASE_JWT_SECRET
from .client import SupabaseAuthClient
from .schemas import UserResponse

security = HTTPBearer(auto_error=True)
auth_client = SupabaseAuthClient()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserResponse:
    """
    Dependency to validate the Bearer token and return the current user.
    Attempts local JWT decoding if SUPABASE_JWT_SECRET is configured,
    falling back to querying the Supabase Auth API otherwise.
    """
    token = credentials.credentials
    
    # 1. Try local offline validation if JWT Secret is configured
    if SUPABASE_JWT_SECRET and SUPABASE_JWT_SECRET != "your-jwt-secret-from-supabase-settings":
        try:
            # Supabase JWTs are HS256 signed and usually have audience "authenticated"
            payload = jwt.decode(
                token, 
                key=SUPABASE_JWT_SECRET, 
                algorithms=["HS256"],
                audience="authenticated"
            )
            
            user_id = payload.get("sub")
            email = payload.get("email")
            user_metadata = payload.get("user_metadata", {})
            
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload: missing sub claim"
                )
                
            return UserResponse(
                id=user_id,
                email=email,
                user_metadata=user_metadata
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            # If local verification fails, we can either raise 401 or fallback
            # In production, if JWT signature is invalid, we should reject.
            # But let's log and fallback to online verification in case of public key rotations or other configs.
            pass

    # 2. Fallback to online verification by calling Supabase API /auth/v1/user
    try:
        user_data = await auth_client.get_user(token)
        return UserResponse(
            id=user_data.get("id"),
            email=user_data.get("email"),
            user_metadata=user_data.get("user_metadata", {})
        )
    except HTTPException as e:
        # Re-raise the 401 / 403 or server errors
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}"
        )
