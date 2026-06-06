# DecisionOS Consumer Credit Backend

Run:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open http://127.0.0.1:8000/docs

Key endpoints:
- GET /cases/samples
- GET /cases
- GET /cases/review-queue
- POST /cases/create
- POST /cases/create-with-upload (multipart form + files)

Upload flow:
- Use `POST /cases/create-with-upload` with applicant fields as form fields and one or more files in `files`.
- The backend extracts machine-readable signals from uploaded documents (json/csv/text and best-effort regex extraction), stores files under `backend/uploads/<case_id>/`, and injects derived signals into specialist agents.
- Agents then include document-derived evidence in affordability, risk, and data-credibility analysis.

