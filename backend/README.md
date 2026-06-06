# DecisionOS Company Spend Intelligence Backend

Run:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open http://127.0.0.1:8000/docs

Persistence:

- Cases are persisted in SQLite (`backend/data/decisionos.db`) instead of in-memory storage.
- Optional override for DB path: set environment variable `DECISIONOS_DB_PATH`.

Key endpoints:

- GET /modeling/health
- POST /modeling/analyze
- GET /cases/samples
- GET /cases
- GET /cases/review-queue
- GET /cases/compare-periods
- POST /cases/create
- POST /cases/create-with-upload (multipart form + files)

Period comparison:

- Compare two date ranges (for example January vs February):

```text
GET /cases/compare-periods?period_a_start=2026-01-01&period_a_end=2026-01-31&period_b_start=2026-02-01&period_b_end=2026-02-28
```

- Returns side-by-side metrics for both periods: volume, decision counts/rates, finance-review rate, and average specialist scores.

Upload flow:

- Use `POST /cases/create-with-upload` with spend profile fields as form fields and one or more files in `files`.
- The backend extracts machine-readable signals from uploaded documents (json/csv/text and best-effort regex extraction), stores files under `backend/uploads/<case_id>/`, and injects derived signals into specialist agents.
- Agents then include document-derived evidence in spend efficiency, variance risk, and data quality analysis.

Testing:

- Install dependencies from `requirements.txt`.
- Run API tests from the backend directory:

```bash
pytest -q
```

Postman:

- Import collection file: `backend/postman/DecisionOS_Backend.postman_collection.json`
- Import environment file: `backend/postman/DecisionOS_Local.postman_environment.json`
- Set `base_url` variable (default: `http://127.0.0.1:8000`)
- For upload requests, attach one or more local files to the `files` form field.

This is a hackathon-safe demo of a multi-agent monthly spend intelligence workflow:
Data Quality Agent, Spend Efficiency Agent, Budget Variance Agent, Manager Agent, and deterministic spend policy engine.

The `/modeling` endpoints connect the frontend credit workflow to the package
under `../modeling`. `POST /modeling/analyze` accepts the backend-compatible
applicant contract, removes names and raw document text before scoring, runs
the three specialists in parallel, and returns adverse-risk probabilities,
reason codes, evidence references, Manager consolidation, deterministic policy,
and human-review routing.

Set `SPENDPILOT_MODEL_ARTIFACT_ROOT` to override the default
`modeling/artifacts/models` location. When trained artifacts are unavailable,
the endpoint uses transparent development scorecards and reports that fallback
in `model_runtime.source`.
