import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from fastapi.middleware.cors import CORSMiddleware
from app.api.chat import router as chat_router

app = FastAPI(
    title="Outdoor Safety Agent API",
    description="Deterministic safety chatbot backed by live Open-Meteo weather and 25 safety SOPs",
    version="1.0.0",
)

# Enable CORS for local development and integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register safety chat API routes
app.include_router(chat_router)

# Serve Frontend SPA
frontend_dir = root_dir / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    @app.get("/")
    def serve_frontend():
        """Serves the main interactive outdoor safety chat frontend."""
        return FileResponse(str(frontend_dir / "index.html"))


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
