import sys
from pathlib import Path
from fastapi import FastAPI

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app.config import settings

app = FastAPI(
    title="Outdoor Safety Agent API",
    description="API for the Outdoor Safety Agent system",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
