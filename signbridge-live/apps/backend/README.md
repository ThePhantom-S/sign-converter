# SignBridge Live — Backend

FastAPI backend for the SignBridge Live accessibility platform.

## Phase 1 (current)

Infrastructure in place:

- FastAPI application with lifespan management
- Pydantic settings from environment variables
- Structured logging (request ID, endpoint, duration)
- Redis connection manager (ephemeral state)
- Supabase client manager (persistent data)
- JWT-ready security utilities
- Rate limiting (SlowAPI)
- CORS configuration
- Standardized error responses
- Health endpoints

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

Optional for full dependency health checks:

- Redis 7+
- Supabase project

## Setup

```bash
cd apps/backend
cp .env.example .env
uv sync
```

Edit `.env` with your credentials. Redis and Supabase can be disabled for local development:

```env
REDIS_ENABLED=false
SUPABASE_ENABLED=false
```

## Run

From the repository root:

```bash
make backend
```

Or directly:

```bash
cd apps/backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness probe |
| GET | `/api/v1/health` | Liveness probe (versioned) |
| GET | `/api/v1/health/detailed` | Readiness with Redis/Supabase status |
| GET | `/docs` | OpenAPI docs (non-production) |

## Environment Variables

See [`.env.example`](.env.example) for the full list.

## Development

```bash
make lint    # ruff
make format  # black
make test    # pytest
```

## Folder Structure

```
app/
├── api/
│   ├── dependencies/   # FastAPI dependencies
│   ├── middleware/     # Request context, logging
│   └── routes/         # Route handlers
├── core/               # Config, logging, Redis, Supabase, security
├── schemas/            # Pydantic request/response models
├── services/           # Business logic
├── utils/              # Shared utilities
└── main.py             # Application entry point
```

Future phases will add modules under `ai/`, `cv/`, and `speech/` without changing this foundation.
