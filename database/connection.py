import os
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

# Initialize official Supabase Client
supabase: Client | None = None

if SUPABASE_URL and SUPABASE_KEY and SUPABASE_URL != "https://your-project.supabase.co":
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Connected to Supabase Project successfully!")
    except Exception as e:
        print(f"⚠️ Supabase connection warning: {e}")
else:
    print("ℹ️ Supabase credentials not set in .env. Running in local fallback mode.")

def get_supabase_client() -> Client | None:
    """Returns the active Supabase client instance."""
    return supabase
