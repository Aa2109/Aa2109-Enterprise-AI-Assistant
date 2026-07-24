# Enterprise AI Assistant

An extensible foundation for an enterprise AI assistant with a FastAPI backend,
retrieval-augmented generation services, agent orchestration, and local
development infrastructure.

## Status

The repository is currently in **Sprint 0: platform foundation**. The initial
backend exposes health endpoints and runs locally with PostgreSQL, Redis, Qdrant,
and MinIO through Docker Compose.

## Architecture

```text
Enterprise-AI-Assistant/
├── backend/
│   ├── agents/          Agent orchestration and domain workflows
│   ├── api/             HTTP routes, including health checks
│   ├── app/             Application startup, settings, and logging
│   ├── models/          Persistence models
│   ├── rag/             Retrieval and document-processing components
│   ├── repositories/    Data-access abstractions
│   ├── schemas/         Request and response contracts
│   ├── services/        Application services
│   ├── tests/           Automated tests
│   ├── tools/           Reusable agent tools
│   └── workers/         Background jobs
├── frontend/            Frontend application (planned)
├── infrastructure/
│   └── docker/          Container build definitions
├── docs/                Design and operational documentation
├── docker-compose.yml    Local service stack
└── pyproject.toml        Python dependencies and quality tooling
```

## Technology Stack

| Area | Technology |
| --- | --- |
| API | FastAPI and Uvicorn |
| Language | Python 3.12 |
| Configuration | Pydantic Settings and `.env` |
| Relational database | PostgreSQL 16 |
| Cache and messaging foundation | Redis 7 |
| Vector database | Qdrant |
| Object storage | MinIO |
| Testing | pytest and HTTPX |
| Code quality | Ruff and mypy |
| Containers | Docker Compose |

## Prerequisites

Install the following tools before starting:

- Python 3.12
- Git
- Docker Desktop with the Linux engine enabled
- PowerShell

The project can use the existing local `venv` or a new `.venv`. Both are ignored
by Git.

## Local Python Setup

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Run the API directly:

```powershell
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

## Run the Full Stack

Start Docker Desktop first, then run:

```powershell
docker compose config
docker compose up --build
```

The API is available at `http://localhost:8000`.

Supporting services:

| Service | URL or port |
| --- | --- |
| FastAPI | `http://localhost:8000` |
| PostgreSQL | `localhost:5432` |
| Redis | `localhost:6379` |
| Qdrant HTTP | `http://localhost:6333` |
| Qdrant gRPC | `localhost:6334` |
| MinIO API | `http://localhost:9000` |
| MinIO console | `http://localhost:9001` |

Stop the stack while retaining persistent data:

```powershell
docker compose down
```

Remove service volumes only when a complete local reset is required:

```powershell
docker compose down -v
```

## API Health Checks

Liveness does not require external services:

```powershell
Invoke-RestMethod http://localhost:8000/health/live
```

Readiness checks PostgreSQL, Redis, Qdrant, and MinIO:

```powershell
Invoke-RestMethod http://localhost:8000/health/ready
```

`/health/live` returns HTTP 200 when the process is running. `/health/ready`
returns HTTP 200 only when all configured dependencies are available and HTTP 503
otherwise.

Interactive API documentation is available at:

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI schema: `http://localhost:8000/openapi.json`

## Quality Checks

Run these commands before opening a pull request:

```powershell
python -m ruff format .
python -m ruff check .
python -m mypy backend
python -m pytest
```

## Git Workflow

- `main`: stable release branch
- `develop`: default working and integration branch
- `feature/<short-name>`: focused branches created from `develop`

Typical feature workflow:

```powershell
git checkout develop
git pull
git checkout -b feature/short-description

# Make changes, then validate them.
python -m ruff check .
python -m mypy backend
python -m pytest

git add .
git commit -m "feat: describe the change"
git push -u origin feature/short-description
```

Feature branches merge into `develop`. Tested integration changes are promoted
from `develop` to `main` for releases.

## Sprint 0 Roadmap

- Establish repository conventions and branch workflow
- Make local configuration safe and repeatable
- Run PostgreSQL, Redis, Qdrant, and MinIO with health-gated startup
- Add FastAPI application and dependency-aware health checks
- Add automated tests, formatting, linting, and type checking
- Add database models and migrations
- Add the first document-ingestion and retrieval slice
- Add CI checks for pull requests

## Security Notes

- Never commit `.env` or production credentials.
- Replace all default local service credentials before deploying anywhere shared.
- Do not log access keys, tokens, passwords, authorization headers, or sensitive prompts.
- Add authentication, secret management, network restrictions, and database
  migrations before production deployment.

## License

License information will be added before the first public release.
