import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL:
    raise ValueError("SUPABASE_URL environment variable is missing or empty")

if not SUPABASE_KEY:
    raise ValueError("SUPABASE_KEY environment variable is missing or empty")

# Initialize and expose the single, reusable Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
