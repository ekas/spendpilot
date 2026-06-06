# SpendPilot

**Explainable multi-agent credit and spend intelligence system** with transparent decision-making, specialist agent collaboration, and policy-driven outcomes.

SpendPilot combines a Next.js 15 frontend UI, Python FastAPI modeling service, and a governed multi-agent workflow to provide auditable, interpretable credit decisions.

🚀 **[Live Demo](https://spendpilot-fintech-app.vercel.app/)** | 📖 [CLAUDE.md](./CLAUDE.md)

## Components

- **Frontend** (`frontend/`): Next.js 15 + React 19 browser UI for applicant analysis and decision review
- **Modeling** (`modeling/`): Python package with specialist agents, Manager consolidation, policy engine, and explainability tools
- **API Server** (`modeling/src/spendpilot/server.py`): FastAPI service exposing `/modeling/analyze` endpoint

---

## Try the Live Demo

👉 **[https://spendpilot-fintech-app.vercel.app/](https://spendpilot-fintech-app.vercel.app/)**

No setup required! Upload a document, enter applicant details, and watch the multi-agent workflow analyze the case in real-time. See specialist reports, policy decisions, and explainability breakdowns.

---

## Quick Start (5 minutes)

### Prerequisites

- **Python 3.11+** (for modeling service)
- **Node.js 18+** & **pnpm** (for frontend)
- **macOS**: `brew install libomp` (XGBoost dependency)

### 1. Setup & Run Modeling Service (Terminal 1)

```bash
cd modeling

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or: .venv\Scripts\activate on Windows

# Install dependencies
pip install -e '.[dev,ml,llm]'

# Start FastAPI server (http://127.0.0.1:8000)
python -m uvicorn src.spendpilot.server:app --host 127.0.0.1 --port 8000 --reload
```

**Expected output:**

```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

### 2. Setup & Run Frontend (Terminal 2)

```bash
cd frontend

# Install dependencies
corepack pnpm install

# Create environment file (if needed)
cp .env.example .env.local  # or edit .env.local manually

# Start dev server (http://127.0.0.1:3003)
corepack pnpm dev
```

**Expected output:**

```
▲ Next.js 15.5.19
- Local:        http://localhost:3003
- Ready in XXXms
```

### 3. Open in Browser

👉 **Visit: http://127.0.0.1:3003**

Enter applicant details, upload documents, and watch the multi-agent workflow analyze in real-time.

---

## Architecture

### Data Flow

```
Frontend (Next.js)
    ↓
/api/analyze (Next.js API Route)
    ↓
Python Modeling Service (FastAPI, port 8000)
    ├─ Credibility Agent (document verification)
    ├─ Affordability Agent (income & spending analysis)
    ├─ Credit Risk Agent (payment history & utilization)
    ├─ Manager Agent (consolidates & resolves disagreements)
    └─ Policy Engine (applies deterministic rules)
    ↓
Decision + Explanations + Evidence References
```

### Key Features

✅ **Multi-Agent Parallel Analysis**
- Three specialist agents run independently, analyzing complementary risk dimensions
- Manager Agent consolidates findings and resolves disagreements

✅ **Explainable Decisions**
- Each decision includes feature contributions, reason codes, and evidence references
- Feature SHAP scores show exactly what drove each recommendation
- Transparent fallback to development scorecards when trained models unavailable

✅ **Policy-Driven Routing**
- Deterministic policy rules determine automatic approval, referral, or decline
- Human review queue for edge cases and agent disagreements

✅ **Applicant Profile Dashboard**
- Input metrics aligned with modeling schema:
  - Financial profile (income, expenses, debt, credit utilization)
  - Risk indicators (delinquencies, overdrafts, employment history)
  - Derived metrics (debt-to-income ratio, affordability score)
- Color-coded health indicators and trend analysis

✅ **PII-Minimized Processing**
- Applicant names stripped before scoring
- Only machine-readable signals preserved
- All decisions use anonymized applicant references

---

## Project Structure

```
spendpilot/
├── modeling/                          # Python modeling package
│   ├── src/spendpilot/
│   │   ├── agents/                   # Specialist agent implementations
│   │   ├── orchestration/            # Workflow, policy engine, review queue
│   │   ├── models/                   # XGBoost + rule-based model adapters
│   │   ├── training/                 # Model training pipelines
│   │   ├── benchmark/                # Evaluation tools
│   │   ├── ingestion/                # Document extraction & signal processing
│   │   ├── schemas/                  # Pydantic data contracts
│   │   ├── assistants/               # LLM-based narrative & routing
│   │   ├── cli.py                    # CLI commands (demo, train, evaluate)
│   │   └── server.py                 # FastAPI server (NEW)
│   ├── tests/                        # Unit tests
│   └── pyproject.toml
│
├── frontend/                         # Next.js 15 frontend
│   ├── app/
│   │   ├── api/                      # API routes (/api/analyze, /api/cases)
│   │   ├── dashboard/                # Analysis results dashboard
│   │   └── page.tsx                  # Input form & document upload
│   ├── components/                   # React components
│   │   ├── dashboard/                # Dashboard panels (NEW: ApplicantProfilePanel)
│   │   ├── agents/                   # Agent visualization
│   │   ├── upload/                   # File upload & form inputs
│   │   └── ui/                       # Base UI components
│   ├── lib/
│   │   ├── api/                      # API client functions
│   │   ├── backend/                  # Business logic (agents, policy, transform)
│   │   ├── types.ts                  # TypeScript interfaces (NEW: modeling fields)
│   │   └── utils.ts                  # Formatting utilities (NEW: null-safe)
│   └── package.json
│
└── CLAUDE.md                         # Architecture & development guide
```

---

## Development

### Running Tests

```bash
# Modeling tests
cd modeling
.venv/bin/python -m pytest

# Specific test file
.venv/bin/python -m pytest tests/test_agents.py::test_affordability_agent -v
```

### CLI Commands (Modeling)

```bash
cd modeling

# Train synthetic models
.venv/bin/python -m spendpilot.cli train-synthetic

# Run interactive demo (generates sample cases)
.venv/bin/python -m spendpilot.cli demo

# Evaluate against South German Credit dataset
.venv/bin/python -m spendpilot.cli benchmark-south-german

# Generate HTML explainability report
.venv/bin/python -m spendpilot.cli explainability-report \
  --input examples/external-cases.json \
  --output artifacts/reports/report.html

# Evaluate custom JSON input
.venv/bin/python -m spendpilot.cli evaluate-input --input examples/custom.json
```

### Environment Variables

**Frontend** (`.env.local`):

```env
SPENDPILOT_MODELING_API_URL=http://127.0.0.1:8000
SPENDPILOT_ALLOW_TYPESCRIPT_FALLBACK=false
NEXT_PUBLIC_SUPABASE_URL=...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
```

**Modeling** (optional):

```env
SPENDPILOT_GGUF_PATH=/path/to/phi-1.5.gguf
OPENROUTER_API_KEY=...
```

### Frontend Development

```bash
cd frontend

# Install dependencies
corepack pnpm install

# Run dev server with hot reload
corepack pnpm dev

# Build for production
corepack pnpm build && corepack pnpm start

# Lint & format
corepack pnpm lint

# Prisma database commands
corepack pnpm db:migrate      # Create migration
corepack pnpm db:push         # Push schema to database
corepack pnpm db:studio       # Open Prisma Studio
```

---

## API Specification

### POST `/modeling/analyze`

**Request:**

```json
{
  "case_id": "case_001",
  "snapshot_id": "snap_001",
  "applicant": {
    "monthly_income": 3000,
    "monthly_expenses": 1500,
    "requested_amount": 5000,
    "existing_debt": 2000,
    "credit_utilization": 0.45,
    "delinquencies_12m": 0,
    "employment_months": 24,
    "overdrafts_90d": 1,
    "income_verified": true
  }
}
```

**Response:**

```json
{
  "reports": [
    {
      "agent_id": "affordability",
      "score": 0.11,
      "recommendation": "approve",
      "reason_codes": ["AFFORDABILITY_PROFILE_STABLE"],
      "top_contributors": [
        {
          "feature": "debt_to_income",
          "value": 0.19,
          "contribution": -1.38,
          "reason_code": "HIGH_DTI"
        }
      ]
    }
  ],
  "manager_report": {
    "proposed_action": "approve",
    "summary": "All specialists recommend approval..."
  },
  "decision": {
    "action": "approve",
    "reason_codes": ["UNANIMOUS_AUTOMATIC_APPROVAL"]
  },
  "review_task": null
}
```

### GET `/modeling/health`

**Response:**

```json
{
  "status": "healthy",
  "service": "spendpilot-modeling",
  "version": "0.1.0"
}
```

---

## Recent Updates (Latest Session)

✨ **What's New:**

- ✅ FastAPI server created (`modeling/src/spendpilot/server.py`) — unifies HTTP endpoint with Python agents
- ✅ **Applicant Profile Panel** in dashboard — displays all modeling input fields with health indicators
- ✅ Type-safe data mapping — CaseSnapshot now includes all modeling schema fields
- ✅ Robust null-safety — formatting functions handle undefined values gracefully
- ✅ Updated CLAUDE.md — complete architecture guide with development instructions
- ✅ Live demo deployed to Vercel — https://spendpilot-fintech-app.vercel.app/

---

## Important Notes

### PII Handling

- Applicant names are **never** included in model scoring
- Use `applicant_reference` (generated ID) for applicant identification
- Raw document text is stripped before analysis

### Trained Models

- Models stored in `modeling/artifacts/models/`
- Fallback to transparent development scorecards when artifacts unavailable
- All decisions include model version and confidence scores

### Deployment Considerations

- Frontend requires Python modeling service to be running on port 8000
- Set `SPENDPILOT_ALLOW_TYPESCRIPT_FALLBACK=true` only for demo mode without Python
- TypeScript fallback agents are less capable than trained models

---

## Troubleshooting

### Port Already in Use

```bash
# Find process on port 8000
lsof -i :8000
kill -9 <PID>

# Or use different port
python -m uvicorn src.spendpilot.server:app --port 8001
# Update SPENDPILOT_MODELING_API_URL accordingly
```

### Missing Dependencies

```bash
# Ensure Python venv is activated
source modeling/.venv/bin/activate  # macOS/Linux
modeling\.venv\Scripts\activate      # Windows

# Reinstall dependencies
pip install -e '.[dev,ml,llm]'
```

### Frontend Connection Error

- Verify modeling service is running: `curl http://127.0.0.1:8000/modeling/health`
- Check frontend logs in browser DevTools Console
- Ensure `.env.local` has correct `SPENDPILOT_MODELING_API_URL`

---

## License & Attribution

Built during Anthropic Hackathon 2026. Multi-agent architecture inspired by collaborative decision-making principles.

---

## Getting Help

- 📖 See **CLAUDE.md** for detailed architecture & common workflows
- 🐛 Check frontend console and server logs for detailed error messages
- 💬 Review agent reports in dashboard for decision reasoning
