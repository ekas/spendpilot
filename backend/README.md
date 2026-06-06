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

This is a hackathon-safe demo of a multi-agent consumer credit workflow:
Data Credibility Agent, Affordability Agent, Credit Risk Agent, Manager Agent, and deterministic policy engine.
