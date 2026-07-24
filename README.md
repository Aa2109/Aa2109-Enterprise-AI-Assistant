# Enterprise AI Assistant

Initial backend foundation for an enterprise AI assistant.

## Local Python setup

The project targets Python 3.12 and keeps dependencies in `pyproject.toml`.
The existing `venv` directory is local-only and is ignored by Git.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Run the API directly:

```powershell
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

## Configuration

```powershell
Copy-Item .env.example .env
```

Use `.env` for local values. It is ignored by Git and must not contain production
credentials in a shared checkout.

## Quality checks

```powershell
python -m ruff format .
python -m ruff check .
python -m mypy backend
python -m pytest
```

## Run the local stack

Docker Desktop must be running.

```powershell
docker compose config
docker compose up --build
```

The API is available at `http://localhost:8000`. Check liveness and readiness:

```powershell
Invoke-RestMethod http://localhost:8000/health/live
Invoke-RestMethod http://localhost:8000/health/ready
```

Supporting services use these local ports:

- PostgreSQL: `5432`
- Redis: `6379`
- Qdrant: `6333` (HTTP) and `6334` (gRPC)
- MinIO API: `9000`
- MinIO console: `9001`

Stop the stack while retaining data:

```powershell
docker compose down
```

Remove the local service volumes as well only when a clean reset is required:

```powershell
docker compose down -v
```

## Branching strategy

- `main`: stable releases
- `develop`: integration branch
- `feature/<short-name>`: focused development branches created from `develop`

Run quality checks before merging feature branches into `develop`, then promote
tested changes from `develop` to `main`.
