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

## Deploy to Vercel

The demo deployment uses a hybrid architecture:

1. Vercel hosts the Next.js application from `frontend/`.
2. This laptop runs FastAPI and the trained XGBoost artifacts.
3. ngrok exposes only the local FastAPI port over HTTPS.
4. Vercel stores that ngrok URL in `SPENDPILOT_MODELING_API_URL`.

Start the trained modeling API from the repository root:

```bash
cd backend
../modeling/.venv/bin/python -m uvicorn app.main:app \
  --host 127.0.0.1 --port 8000
```

In another terminal, expose it:

```bash
ngrok http 8000
```

If the ngrok URL changes, update Vercel and redeploy:

```bash
cd frontend
vercel env add SPENDPILOT_MODELING_API_URL production \
  --value https://YOUR-NGROK-DOMAIN --force --yes --no-sensitive
vercel deploy --prod --yes
```

The laptop must remain awake, connected to the internet, and running both
processes. This is appropriate for a demo; a production deployment should move
the modeling API to a persistent container service.
