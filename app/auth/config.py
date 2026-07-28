import os
from dotenv import load_dotenv

# Load environment variables (useful for local development outside Docker)
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY", "")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")

def validate_config():
    """
    Validates that necessary configuration is present and not set to default placeholders.
    """
    missing = []
    if not SUPABASE_URL or "your-supabase-project" in SUPABASE_URL:
        missing.append("SUPABASE_URL")
    if not SUPABASE_ANON_KEY or any(placeholder in SUPABASE_ANON_KEY for placeholder in ["your-anon-public-key", "your-supabase-anon-key"]):
        missing.append("SUPABASE_ANON_KEY")
    
    if missing:
        print(f"WARNING: Missing or placeholder configuration for: {', '.join(missing)}")
        print("Please configure real values in .env to use Supabase authentication.")
        return False
    return True
