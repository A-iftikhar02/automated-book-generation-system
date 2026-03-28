from supabase import create_client, Client
from ..config import settings
import sys

# Ensure environment variables are loaded
if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_KEY must be set in the .env file.")
    sys.exit(1)

# Initialize the Supabase client
# This client is reusable across the project
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
