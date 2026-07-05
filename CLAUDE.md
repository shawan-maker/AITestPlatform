# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AITestPlatform (巧乐AI智能体测试平台 / ChocoTest) — a full-stack AI-powered test management platform supporting requirement management, API testing, functional testing, AI-driven test case generation, and test execution/reporting.

## Commands

### Backend (Python 3.10+, FastAPI)

```bash
# Start server (port 8000)
python main.py

# Database migrations (Aerich wrapper)
python scripts/db_manage.py init-db            # First-time setup
python scripts/db_manage.py migrate -m "desc"  # Generate migration after model changes
python scripts/db_manage.py upgrade            # Apply pending migrations
python scripts/db_manage.py downgrade          # Rollback last migration

# Run tests (pytest with asyncio_mode=auto, testpaths=tests)
pytest
pytest tests/ai_generation/test_api_generation.py  # single test file

# Smoke tests (hit live backend)
python tests/smoke/project_smoke_test.py
python tests/smoke/knowledge_smoke_test.py
python tests/smoke/api_test_smoke_test.py
# ... see tests/smoke/*_smoke_test.py
```

### Frontend (Vue 3 + Vite, Node 18+)

```bash
cd frontend
npm install
npm run dev          # Dev server on port 5173 (proxies /api to backend)
npm run build        # Production build
```

### Validation after code changes

```bash
# Frontend compile check (in frontend/)
npx vite build --mode development

# Backend syntax check (root)
python -c "import py_compile; import os; [py_compile.compile(os.path.join(r, f)) for r,d,fs in os.walk('service') for f in fs if f.endswith('.py')]"
```

### i18n

Translation files live in `frontend/src/i18n/` (zh-CN.json, en-US.json). Use `python update_i18n.py` as a template for programmatic additions.

## Architecture

### Backend Module Structure

All business logic is under `service/`, organized by domain. Each module follows a consistent pattern:

- `models.py` — Tortoise ORM models (registered in `service/core/config.py` → `TORTOISE_ORM`)
- `api.py` — FastAPI `APIRouter` with endpoint definitions
- `schemas.py` — Pydantic request/response schemas
- `*_service.py` — Business logic layer (services called by API routes)
- Sub-modules may have their own `api.py`/`models.py` (e.g., `service/api_test/interface/`, `service/test_execution/run/`)

All routers are aggregated in `service/router.py` and mounted at `/api/v1`.

### Key Modules

| Module | Purpose |
|--------|---------|
| `service/user` | Auth (JWT access+refresh), user management, bootstrap super admin |
| `service/project` | Projects, members (viewer/editor/owner roles), modules |
| `service/knowledge` | Document upload/versioning, RAG indexing, Swagger/OpenAPI/AI parsing, downstream import to requirements & interfaces |
| `service/functional_test` | Functional test case catalog, CRUD |
| `service/api_test` | API interfaces (versioned), base cases, runnable test cases, debug execution, dependency inference, catalog |
| `service/test_environment` | Test environments with variables, DB configs, file configs, global functions |
| `service/test_management` | Test suites, tasks, defect management, picker |
| `service/test_execution` | Test runs (serial/parallel), suite/task runners, progress tracking, reports, manual runs, defect creation |
| `service/ai_generation` | AI agent sessions with SSE streaming, functional/API case generation via LangGraph |

### Core Infrastructure (`service/core/`)

- **config.py** — All settings from `.env`, `TORTOISE_ORM` config (model registration required here)
- **deps.py** — FastAPI dependency injection: `get_current_active_user`, `require_project_editor`, `require_project_viewer`, etc.
- **security.py** — JWT token creation/decoding (python-jose), bcrypt password hashing
- **redis.py** — Async Redis client for token revocation blacklists (gracefully degrades if unavailable)
- **response.py** — `success()` wrapper returning `{code, message, data, timestamp}` format
- **pagination.py** — `paginate(qs, page, page_size)` returning `(total, items)` tuple
- **exceptions.py** — `AppException(message, code)` caught by global handler
- **enums.py** — All domain enums (shared across modules)

### Auth Flow

JWT with access + refresh tokens. Access tokens carry `jti` for Redis-based revocation. Dependency chain in `deps.py`: `get_access_payload` → `get_current_user` → `get_current_active_user` → role-specific guards. Project access is checked via `require_project_viewer` / `require_project_editor` / `require_project_owner_or_super_admin`.

### AI Generation & SSE Streaming

AI agents (LangGraph) run asynchronously and stream results via Server-Sent Events. Backend: `service/ai_generation/agent_stream.py` produces SSE events. Frontend: `frontend/src/utils/sse.js` (`postEventStream`, `consumeSseStream`) handles the stream. Agent timeout defaults to 600s, configurable via `AI_AGENT_TIMEOUT_SECONDS` env var. Mock mode available for tests (`API_TEST_GEN_MOCK=1`, `FUNCTIONAL_GEN_MOCK=1`).

### Knowledge/RAG Pipeline

Documents go through: upload → parse (Swagger/OpenAPI structured parse or AI parse) → index (RAG) → downstream import. Parse routing logic is in `service/knowledge/rules/parse_router.py`. Swagger/OpenAPI files always use structured parse regardless of user-selected mode. Save state for requirements and interfaces is computed by `service/knowledge/document/save_state.py`.

### Frontend Architecture

- **Vue 3** with Composition API, **Pinia** stores, **vue-router** with route guards
- **Element Plus** UI, **Monaco Editor** for code editing, **ECharts** for charts
- **vue-i18n** for zh-CN / en-US internationalization
- Axios client (`src/utils/request.js`) with automatic token refresh on 401
- Route guards (`src/router/guards.js`) handle auth checks, project access, and permission loading
- SCSS variables auto-injected via Vite (`@use "@/styles/variables.scss" as *`)
- `@` alias maps to `src/` directory
- Route files split by domain under `src/router/routes/`

### Default Dev Accounts

- Auto-created super admin on first boot: `admin` / `123456` (see `service/user/bootstrap.py`)
- Test account: `test1213` / `123456`

### Environment

Copy `.env.example` to `.env`. Key vars: `DATABASE_URL` (MySQL), `REDIS_URL`, `JWT_SECRET_KEY`, LLM config (`LLM_BINDING_HOST`, `LLM_BINDING_API_KEY`, `LLM_MODEL`).

### Other Directories

- `agents/` — Standalone agent scripts (case generation)
- `workflow/` — Workflow orchestration scripts for API case generation pipelines
- `mcp_tools/` — MCP tool definitions
- `config/settings.py` — RAG/LLM runtime config (separate from `.env`-based core config)
- `scripts/` — Management utilities, DB migrations (`scripts/migrations/`), migration repair scripts
