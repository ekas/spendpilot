# SpendPilot Modeling

Explainable, human-governed consumer-credit agents, decision orchestration, and
offline model-learning tools.

## Local setup

Python 3.11 or newer is required. XGBoost on macOS also requires OpenMP.
The optional GGUF smoke test uses llama.cpp with Metal:

```bash
cd modeling
brew install libomp llama.cpp
python -m venv .venv
.venv/bin/python -m pip install -e '.[dev,ml,llm]'
```

Build the local artifacts and run the governed workflow:

```bash
.venv/bin/python -m spendpilot.cli train-synthetic
.venv/bin/python -m spendpilot.cli benchmark-south-german
.venv/bin/python -m spendpilot.cli demo
```

Create an OpenRouter API key and expose it only in the local shell:

```bash
export OPENROUTER_API_KEY="replace_with_your_key"
.venv/bin/python -m spendpilot.cli demo --with-openrouter
```

The demo runs the three backend sample applications through deterministic
credibility rules, trained affordability and credit-risk models, the Manager,
policy evaluation, and human-review routing. OpenRouter supplies only a bounded
narrative and validated feedback-routing proposal. The default
`openrouter/free` router may select different free models, so the actual model
and request identifiers are stored in the narrative.

Run the experimental local Phi-1.5 GGUF through schema-constrained narrative
and feedback-routing probes:

```bash
.venv/bin/python -m spendpilot.cli local-llm-smoke \
  --gguf-path /Users/saurav/Desktop/slm_2025/models/phi-1.5.Q4_K_M.gguf
```

The path may instead be provided through `SPENDPILOT_GGUF_PATH`. The command
starts one private `llama-server` on `127.0.0.1:8080`, uses a 2,048-token
context, a 256-token output limit, temperature zero, one parallel request, and
llama.cpp JSON-schema constraints. Phi-1.5 is a base model without an embedded
chat template, so every response remains experimental and deterministic
Manager fallback stays active.

Generate the self-contained offline explainability report:

```bash
.venv/bin/python -m spendpilot.cli explainability-report \
  --output artifacts/reports/explainability-demo.html
```

The HTML needs no web server or external assets. It includes the three sample
cases, specialist scores, local TreeSHAP contributions, evidence references,
policy and human-review routing, benchmark metrics, and local-model reliability.
Names, raw documents, model files, API keys, and generated reports remain
outside Git.

## Validation

```bash
.venv/bin/python -m pytest
```

Architecture and governance documents are under `docs/`. Runtime package code
is under `src/spendpilot/`, and repayment outcomes remain an offline-only
learning input. Datasets, model binaries, and benchmark reports are local
ignored artifacts.
