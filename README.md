# MOPPA

MOPPA (Model Prediction Performance Assessment) is a pipeline-style evaluation system for model forecasting performance.

## What It Does

- Ingests real-world events from configured data sources.
- Generates verifiable questions by level (L1-L4).
- Runs model predictions on published questions.
- Backfills ground truth after deadlines.
- Computes scores and publishes leaderboards.
- Collects feedback to continuously improve templates and rules.

## Current Repository Status

- `moppa_backend/`: FastAPI skeleton with health endpoints.
- `frontend/`: Vue + Vite starter scaffold.
- `docs/`: SOP, data model design, and process documentation.

## Security Baseline

- Never store plaintext credentials, tokens, or internal endpoints in repo files.
- Use environment variables or a secrets manager (Vault/KMS).
- Keep only examples/placeholders in docs and `.env.example`.

## Quick Start

### Backend

```bash
cd moppa_backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Roadmap (High Level)

1. Build DB schema + migrations for core entities.
2. Implement S1-S6 MVP workflow with idempotent scheduling.
3. Add scoring + leaderboard API and frontend pages.
4. Add test, CI, and observability gates.
