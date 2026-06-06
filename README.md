# SpendPilot

SpendPilot combines a Next.js review interface, FastAPI services, and an
explainable multi-agent credit modeling workspace.

- `frontend/` contains the browser UI and its server-side API adapter.
- `backend/` exposes the governed Python modeling workflow over HTTP.
- `modeling/` contains the three specialists, Manager, policy engine,
  human-review routing, training, benchmarking, and explainability tools.

## Run locally

```bash
cd modeling
.venv/bin/python -m pip install -e '.[dev,ml,llm]'
.venv/bin/python -m spendpilot.cli train-synthetic

cd ../backend
../modeling/.venv/bin/uvicorn app.main:app --reload --port 8000

cd ../frontend
cp .env.example .env.local
corepack pnpm install
corepack pnpm dev
```

Open `http://127.0.0.1:3000`. The UI sends applicant fields and document
signals to FastAPI. FastAPI removes direct PII, executes the specialists in
parallel, sends their immutable reports to the Manager, applies deterministic
policy, and returns human-review routing and explanations.

If trained artifacts are absent, the same workflow uses transparent,
monotonic development scorecards and reports that fallback in its provenance.
