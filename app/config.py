import os
from pathlib import Path
from dotenv import load_dotenv

# 1. Define the project root directory (one level up from /app)
# This ensures .env is found even if uvicorn is started from a different folder.
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

# 2. Load environment variables from the absolute path of the .env file
# Note: The .env file must be located in the project root (trial task/).
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    print(f"WARNING: .env file not found at {ENV_PATH}")

class Settings:
    PROJECT_NAME: str = "Automated Book Generation System"
    VERSION: str = "0.1.0"
    
    # AI Engine (Gemini)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Database (Supabase)
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    
    # Notifications (Webhook)
    TEAMS_WEBHOOK_URL: str = os.getenv("TEAMS_WEBHOOK_URL", "")
    SLACK_WEBHOOK_URL: str = os.getenv("SLACK_WEBHOOK_URL", "")

settings = Settings()

# Non-secret debug check to verify if critical variables are correctly loaded
if not settings.SUPABASE_URL:
    print("DEBUG: SUPABASE_URL is currently EMPTY. Check your .env file.")
else:
    print(f"DEBUG: SUPABASE_URL detected (length: {len(settings.SUPABASE_URL)} chars).")
