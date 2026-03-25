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

## Docker Note

If the backend container can resolve `nominatim.openstreetmap.org` but outbound HTTPS fails with `[Errno 101] Network is unreachable`, the host is usually fine and the container is hitting an unusable IPv6 path first.

The repo's `docker-compose.yml` temporarily disables IPv6 for the `backend` service so `requests` can use the working IPv4 path. After redeploying, verify from the container with:

```bash
docker compose exec backend python - <<'PY'
import requests
r = requests.get(
    "https://nominatim.openstreetmap.org/search",
    params={"q": "Iran", "format": "json", "limit": 1},
    timeout=10,
)
print(r.status_code)
print(r.text[:200])
PY
```

If you later fix Docker IPv6 routing on the host, you can remove the `backend.sysctls` IPv6 settings from `docker-compose.yml`.
