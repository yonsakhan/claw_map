import os
import getpass
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Settings:
    pg_user = os.getenv("POSTGRES_USER", getpass.getuser())
    pg_host = os.getenv("POSTGRES_HOST", "localhost")
    pg_port = os.getenv("POSTGRES_PORT", "5432")
    pg_db = os.getenv("POSTGRES_DB", "claw_map")
    postgres_url = os.getenv("POSTGRES_URL", f"postgresql+psycopg://{pg_user}@{pg_host}:{pg_port}/{pg_db}")
    mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    mongo_db = os.getenv("MONGO_DB", "claw_map")
    mongo_raw_collection = os.getenv("MONGO_RAW_COLLECTION", "raw_profiles")

    # LLM Config
    openai_api_key = os.getenv("OPENAI_API_KEY")
    openai_api_base = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
    model_name = os.getenv("MODEL_NAME", "moonshot-v1-8k")  # Default to moonshot for Kimi key
    xhs_cookie = os.getenv("XHS_COOKIE")


settings = Settings()
