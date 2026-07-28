from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any

class UserCredentials(BaseModel):
    email: str = Field(..., description="The user's email address")
    password: str = Field(..., description="The user's password")

class UserResponse(BaseModel):
    id: str = Field(..., description="The unique Supabase user ID (UUID)")
    email: Optional[str] = Field(None, description="The user's email address")
    created_at: Optional[str] = Field(None, description="ISO-8601 timestamp of account creation")
    user_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Safe user-supplied metadata")

class TokenResponse(BaseModel):
    access_token: str = Field(..., description="The JWT access token used for bearer authentication")
    refresh_token: Optional[str] = Field(None, description="The refresh token to obtain a new access token")
    token_type: str = Field("bearer", description="The token type (always bearer)")
    expires_in: Optional[int] = Field(None, description="Number of seconds until the token expires")
    user: Optional[UserResponse] = Field(None, description="Detailed info of the authenticated user")

class AuthSuccessResponse(BaseModel):
    message: str = Field(..., description="Success message")
    user: Optional[UserResponse] = Field(None, description="Detailed info of the user")
