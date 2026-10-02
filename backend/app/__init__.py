from pathlib import Path

# Route all backend.app submodule imports directly to app directory
__path__ = [str(Path(__file__).resolve().parent.parent.parent / "app")]
