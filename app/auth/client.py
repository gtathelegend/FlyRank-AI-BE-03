import httpx
from fastapi import HTTPException, status
from .config import SUPABASE_URL, SUPABASE_ANON_KEY

class SupabaseAuthClient:
    """
    Async client wrapping the Supabase GoTrue Auth API via direct HTTP requests.
    """
    
    @staticmethod
    def _get_headers(token: str = None) -> dict:
        headers = {
            "apikey": SUPABASE_ANON_KEY,
            "Content-Type": "application/json"
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    async def signup(self, email: str, password: str) -> dict:
        url = f"{SUPABASE_URL}/auth/v1/signup"
        payload = {"email": email, "password": password}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url, 
                    headers=self._get_headers(), 
                    json=payload,
                    timeout=10.0
                )
                if response.status_code != 200:
                    try:
                        err_data = response.json()
                        err_msg = err_data.get("msg", err_data.get("error_description", "Signup failed"))
                    except Exception:
                        err_msg = response.text or "Signup failed"
                    raise HTTPException(
                        status_code=response.status_code, 
                        detail=err_msg
                    )
                return response.json()
            except httpx.RequestError as e:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Failed to connect to Supabase auth service: {str(e)}"
                )

    async def login(self, email: str, password: str) -> dict:
        url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
        payload = {"email": email, "password": password}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url, 
                    headers=self._get_headers(), 
                    json=payload,
                    timeout=10.0
                )
                if response.status_code != 200:
                    try:
                        err_data = response.json()
                        err_msg = err_data.get("error_description", err_data.get("msg", "Invalid credentials"))
                    except Exception:
                        err_msg = response.text or "Login failed"
                    raise HTTPException(
                        status_code=response.status_code, 
                        detail=err_msg
                    )
                return response.json()
            except httpx.RequestError as e:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Failed to connect to Supabase auth service: {str(e)}"
                )

    async def logout(self, token: str) -> bool:
        url = f"{SUPABASE_URL}/auth/v1/logout"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url, 
                    headers=self._get_headers(token),
                    timeout=10.0
                )
                # Logout normally returns 204 No Content
                if response.status_code not in (200, 204):
                    try:
                        err_data = response.json()
                        err_msg = err_data.get("msg", "Logout failed")
                    except Exception:
                        err_msg = response.text or "Logout failed"
                    raise HTTPException(
                        status_code=response.status_code, 
                        detail=err_msg
                    )
                return True
            except httpx.RequestError as e:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Failed to connect to Supabase auth service: {str(e)}"
                )

    async def get_user(self, token: str) -> dict:
        url = f"{SUPABASE_URL}/auth/v1/user"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url, 
                    headers=self._get_headers(token),
                    timeout=5.0
                )
                if response.status_code != 200:
                    try:
                        err_data = response.json()
                        err_msg = err_data.get("msg", "Session invalid or expired")
                    except Exception:
                        err_msg = response.text or "Session invalid or expired"
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED, 
                        detail=err_msg
                    )
                return response.json()
            except httpx.RequestError as e:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Failed to connect to Supabase auth service: {str(e)}"
                )
