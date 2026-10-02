# Outdoor Safety Agent (Weather-Agent)

An AI-powered outdoor activity safety system that combines real-time weather alerts, standardized operating procedures (SOP), policy DSL, and LangGraph orchestration to provide deterministic safety recommendations.

## Project Structure

```
outdoor-safety-agent/
│
├── backend/          # FastAPI service & application logic
│   └── app/
│       ├── __init__.py
│       ├── config.py
│       └── main.py
├── policies/         # SOP schema & safety policies
├── evals/            # Evaluation benchmarks
├── fixtures/         # Test fixtures & mock weather payloads
├── mcp/              # Model Context Protocol integrations
├── frontend/         # Web interface
├── tests/            # Automated test suites
├── docs/             # Architecture & design documentation
│
├── .env.example      # Environment variables template
├── .gitignore        # Git ignore rules (secrets & caches)
├── README.md         # Project documentation
└── pyproject.toml    # Project metadata & dependencies
```

## Getting Started

### 1. Environment Setup

Make sure you have Python 3.11 or 3.12 installed.

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install fastapi uvicorn pydantic pydantic-settings \
langgraph langchain langchain-openai \
httpx pyyaml python-dotenv
```

### 3. Configure Environment

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

### 4. Run the API

From the `backend/` directory:

```bash
uvicorn app.main:app --reload
```

Or from the project root:

```bash
uvicorn backend.app.main:app --reload
```

### 5. Verify Health Endpoint

Navigate to:
- Health check: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- Interactive API Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
