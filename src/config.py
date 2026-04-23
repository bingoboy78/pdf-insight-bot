import os

class Settings:
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")
    
    VOLUME_NAME = "pdf-insight-storage"
    VOLUME_PATH = "/data"
    JOBS_DIR = "/data/jobs"

settings = Settings()
