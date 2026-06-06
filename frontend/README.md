# SpendPilot Frontend

Next.js interface for the explainable multi-agent credit workflow.

## Run

Start the Python backend first:

```bash
cd ../backend
../modeling/.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

Then start the frontend:

```bash
cp .env.example .env.local
corepack pnpm install
corepack pnpm dev
```

Open `http://127.0.0.1:3000`.

The browser sends application fields and uploaded files to the Next.js API.
The Next server extracts bounded document signals and calls
`POST /modeling/analyze` on FastAPI. The response is converted into readable
readiness scores, adverse-risk percentages, feature contributions, Manager
consolidation, policy checks, and human-review state.

`SPENDPILOT_ALLOW_TYPESCRIPT_FALLBACK` is disabled by default. Set it to
`true` only when demonstrating the UI without the Python modeling service.
