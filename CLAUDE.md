# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**SpendPilot** is an explainable multi-agent credit/spend intelligence system with three integrated components:

- **Frontend** (`frontend/`): Next.js 15 + React 19 browser UI for applicant review and decision routing
- **Backend** (`backend/`): FastAPI service that orchestrates the multi-agent workflow and exposes REST endpoints
- **Modeling** (`modeling/`): Python package containing specialist agents, Manager decision consolidation, policy engine, training, benchmarking, and explainability tools

## Architecture & Data Flow

The system implements a governed multi-agent workflow:

1. **Frontend** → sends applicant fields + documents to Next.js API server (`/api/analyze`)
2. **Next.js API routes** → extract machine-readable signals from documents, call Python modeling service
3. **Python Modeling Service** (port 8000 by default) → runs three specialist agents in parallel:
   - **Data Quality Agent**: analyzes document consistency and data completeness
   - **Spend Efficiency Agent**: evaluates spending patterns and efficiency metrics
   - **Budget Variance Agent**: assesses variance risk and budget adherence
4. **Manager Agent** → consolidates specialist reports into a unified assessment
5. **Policy Engine** → applies deterministic spend/credit policy rules
6. **Human Review Routing** → determines cases needing manual review
7. **Response** → returns decision, explanations, evidence references, and feature contributions back to frontend

**Key insight**: Names and raw document text are stripped before scoring to prevent PII leakage. When trained model artifacts are unavailable, the system falls back to transparent development scorecards in `model_runtime.source`.

**Note**: The Python modeling service runs on port 8000 for development. The Next.js frontend includes TypeScript agent fallbacks for demo mode when the Python service is unavailable (`SPENDPILOT_ALLOW_TYPESCRIPT_FALLBACK=true`).

### Modeling Package Structure

```
modeling/src/spendpilot/
├── agents/           # Specialist agent implementations
├── orchestration/    # Manager and policy orchestration logic
├── models/          # ML model definitions and loading
├── training/        # Model training pipelines
├── benchmark/       # Benchmark evaluation tools
├── ingestion/       # Document extraction and signal processing
├── schemas/         # Pydantic schemas for data contracts
├── assistants/      # LLM-based narrative and routing
├── reports/         # HTML report generation
└── outcomes/        # Training outcome tracking (offline)
```

### Frontend Structure

```
frontend/
├── app/             # Next.js 15 app router
├── components/      # React components (UI, forms, displays)
├── lib/             # Utilities, API clients, Prisma schema
├── hooks/           # React hooks
├── public/          # Static assets
└── prisma/          # ORM schema for case persistence (Supabase)
```

## Development Commands

### Full Stack Local Development

```bash
# 1. Modeling setup (Python 3.11+ required) — runs the Python service on port 8000
cd modeling
brew install libomp llama.cpp  # macOS: XGBoost needs OpenMP
python -m venv .venv
.venv/bin/python -m pip install -e '.[dev,ml,llm]'
.venv/bin/python -m spendpilot.cli demo  # Starts the modeling service

# 2. Frontend (in another terminal)
cd frontend
cp .env.example .env.local
corepack pnpm install
corepack pnpm dev
# UI: http://127.0.0.1:3000
# Frontend will call the Python modeling service at http://127.0.0.1:8000/modeling/analyze
```

### Modeling Package

```bash
cd modeling

# Build local trained artifacts
.venv/bin/python -m spendpilot.cli train-synthetic

# Benchmark against South German Credit dataset
.venv/bin/python -m spendpilot.cli benchmark-south-german

# Interactive demo with frontend
.venv/bin/python -m spendpilot.cli demo

# Evaluate custom input JSON
.venv/bin/python -m spendpilot.cli evaluate-input --input examples/external-cases.json

# Generate offline HTML explainability report
.venv/bin/python -m spendpilot.cli explainability-report \
  --input examples/external-cases.json \
  --output artifacts/reports/external-case.html

# Local Phi-1.5 GGUF LLM smoke test
.venv/bin/python -m spendpilot.cli local-llm-smoke --gguf-path /path/to/phi-1.5.gguf

# With OpenRouter API key (bounded narrative + feedback routing)
export OPENROUTER_API_KEY="..."
.venv/bin/python -m spendpilot.cli demo --with-openrouter

# Run tests
.venv/bin/python -m pytest
```

### Frontend & Modeling Integration

The frontend's Next.js API routes (`/frontend/app/api/`) handle HTTP requests and integration with the Python modeling service:

```bash
cd frontend

# The frontend looks for the Python modeling service at http://127.0.0.1:8000
# Set SPENDPILOT_MODELING_API_URL in .env.local to override

# Key integration points:
# - /api/analyze          → calls Python /modeling/analyze
# - /api/cases            → case CRUD and persistence
# - /api/health           → checks Python service health
# - lib/backend/          → TypeScript helpers and fallback agents
```

### Frontend

```bash
cd frontend

# Install dependencies
corepack pnpm install

# Development server
corepack pnpm dev

# Build for production
corepack pnpm build && corepack pnpm start

# Linting
corepack pnpm lint

# Prisma commands
corepack pnpm db:generate        # Generate Prisma client
corepack pnpm db:push           # Push schema to database
corepack pnpm db:migrate        # Create migration
corepack pnpm db:reset          # Force reset database
corepack pnpm db:studio         # Open Prisma Studio
```

## Key Technical Details

### Input Schema

Cases accept JSON with this structure:

```json
{
  "case_id": "...",
  "snapshot_id": "...",
  "applicant_reference": "...",
  "product": "credit_line",
  "currency": "USD",
  "requested_amount": 5000,
  "monthly_income": 3000,
  "monthly_expenses": 1500,
  "outstanding_debt": 2000,
  "credit_utilization": 0.45,
  "late_payments": 0,
  "recent_overdrafts": 1,
  "employment_months": 24,
  "income_verified": true,
  "document_ids": ["..."],
  "optional_documents": ["..."]
}
```

**Important**: `applicant_reference` is preferred over applicant names. Names and raw document text are stripped before scoring.

### Key API Endpoints

The Python modeling service exposes these endpoints (available at `http://127.0.0.1:8000` during development):

| Method | Endpoint                | Purpose                                                               |
|--------|------------------------|-----------------------------------------------------------------------|
| `POST` | `/modeling/analyze`     | Core credit/spend scoring workflow (called by `/api/analyze`)        |
| `GET`  | `/modeling/health`      | Service health check                                                  |

**Note**: Case creation, listing, and retrieval are handled by the Next.js API routes in `frontend/app/api/cases/`.

### Environment Variables

**Frontend** (`.env.local`):

```env
SPENDPILOT_ALLOW_TYPESCRIPT_FALLBACK=false  # Enable TypeScript agent fallback if Python service unavailable
SPENDPILOT_MODELING_API_URL=http://127.0.0.1:8000  # Python modeling service URL (default shown)
NEXT_PUBLIC_SUPABASE_URL=...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
```

**Modeling** (optional):

```env
SPENDPILOT_GGUF_PATH=/path/to/phi-1.5.gguf  # Local GGUF model for local LLM narratives
OPENROUTER_API_KEY=...  # For OpenRouter LLM narratives and bounded feedback routing
```

### Case Persistence

- Cases are persisted through the Next.js API routes in `frontend/app/api/cases/`
- Database backing (Supabase Postgres or local SQLite) is configured in the frontend
- Documents uploaded via the frontend are extracted and stored via Supabase storage or local filesystem
- Machine-readable signals are auto-injected into specialist agents by the Python modeling service

### Database & ORM

**Frontend** uses Prisma for case schema and Supabase for persistence. Run migrations with:

```bash
corepack pnpm db:migrate
```

### Testing

```bash
# Modeling tests (agents, models, workflows)
cd modeling && .venv/bin/python -m pytest

# Test specific file or test
cd modeling && .venv/bin/python -m pytest tests/test_agents.py::test_data_credibility_agent -v

# Run all tests with verbose output
cd modeling && .venv/bin/python -m pytest -v
```

### Testing the Modeling Service Endpoint

The Python modeling service provides `/modeling/analyze` at `http://127.0.0.1:8000`. Test directly with:

```bash
curl -X POST http://127.0.0.1:8000/modeling/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "case_id": "test-case-1",
    "snapshot_id": "snapshot_1",
    "applicant": {
      "monthly_income": 3000,
      "monthly_expenses": 1500,
      "requested_amount": 5000,
      "outstanding_debt": 2000,
      "credit_utilization": 0.45,
      "late_payments": 0,
      "recent_overdrafts": 1,
      "employment_months": 24,
      "income_verified": true
    }
  }'
```

## Common Workflows

### Add a New Specialist Agent

1. Implement in `modeling/src/spendpilot/agents/`
2. Define input schema and output report
3. Register in `orchestration/workflow.py`
4. Update Manager consolidation logic
5. Add tests in `modeling/tests/`

### Create a New Model

1. Add model definition to `modeling/src/spendpilot/models/`
2. Implement training pipeline in `modeling/src/spendpilot/training/`
3. Save artifacts to `modeling/artifacts/models/`
4. Update model loading in orchestration layer
5. Add benchmark evaluation

### Add a Frontend API Endpoint

1. Create route handler in `frontend/app/api/<name>/route.ts`
2. Define request/response types in `frontend/lib/types.ts` or inline
3. Import any modeling utilities from `frontend/lib/backend/`
4. Test via `POST http://127.0.0.1:3000/api/<name>`

### Frontend UI Changes

1. Update components in `frontend/components/`
2. Add API calls in `frontend/lib/api/`
3. Test at `http://127.0.0.1:3000`
4. Verify case submission and decision display

## Important Notes

- **PII Handling**: Names and raw documents are always stripped before scoring. Do not add PII to model inputs or explanations.
- **Python Service Required**: Development requires the Python modeling service running on port 8000. The frontend includes a TypeScript-only fallback, but it's less capable than the Python implementation.
- **Fallback behavior**: When trained artifacts are unavailable, the system uses transparent development scorecards. Set `SPENDPILOT_ALLOW_TYPESCRIPT_FALLBACK=true` to enable frontend-only demo mode without Python service.
- **NextJS 15 Breaking Changes**: Check `node_modules/next/dist/docs/` for API/convention differences from older versions.
- **Python 3.11+**: Required for modeling package; XGBoost on macOS needs OpenMP (`brew install libomp`).
- **Modeling service URL**: The frontend looks for the Python service at `http://127.0.0.1:8000` by default. Override with `SPENDPILOT_MODELING_API_URL` environment variable.
- **Model artifact location**: Models are loaded from `modeling/artifacts/models/` by default.
