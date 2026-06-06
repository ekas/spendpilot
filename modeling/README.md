# SpendPilot Modeling

Explainable, human-governed consumer-credit agents, decision orchestration, and
offline model-learning tools.

## Local setup

Python 3.11 or newer is required. XGBoost on macOS also requires OpenMP:

```bash
cd modeling
brew install libomp
python -m venv .venv
.venv/bin/python -m pip install -e '.[dev,ml,llm]'
```

Build the local artifacts and run the governed workflow:

```bash
.venv/bin/python -m spendpilot.cli train-synthetic
.venv/bin/python -m spendpilot.cli benchmark-south-german
.venv/bin/python -m spendpilot.cli demo
```

Phi is an optional, explicit download of roughly 2.2 GB:

```bash
.venv/bin/python -m spendpilot.cli setup-phi
.venv/bin/python -m spendpilot.cli demo --with-phi
```

The demo runs the three backend sample applications through deterministic
credibility rules, trained affordability and credit-risk models, the Manager,
policy evaluation, and human-review routing. Phi supplies only a bounded
narrative and validated feedback-routing proposal.

## Validation

```bash
.venv/bin/python -m pytest
```

Architecture and governance documents are under `docs/`. Runtime package code
is under `src/spendpilot/`, and repayment outcomes remain an offline-only
learning input. Datasets, model binaries, benchmark reports, and Phi weights
are local ignored artifacts.
