"""UGCORA Studio launcher."""
import os
import uvicorn
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", "8000"))
    reload_flag = os.getenv("APP_ENV", "production") == "development"
    uvicorn.run("app.main:app", host=host, port=port, reload=reload_flag)
