# MOPPA Backend (FastAPI)

## Quick Start

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run development server:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Endpoints

- `GET /` root message
- `GET /health` health check
- `GET /docs` Swagger UI
