import sys
from pathlib import Path
from fastapi import FastAPI

# Ensure backend directory is in sys.path for direct imports
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

try:
    from app.config import settings
except ImportError:
    from backend.app.config import settings

app = FastAPI(
    title="Outdoor Safety Agent API",
    description="API for the Outdoor Safety Agent system",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
