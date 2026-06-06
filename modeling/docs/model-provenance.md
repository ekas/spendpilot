# Model Provenance

## Backend-Compatible Specialists

The Data Credibility Agent is deterministic. It evaluates required-document
presence, income verification, extraction coverage, and consistency flags.
Each rule produces an explicit contribution and reason code.

The Affordability and Credit Risk Agents are development models trained from
25,000 generated cases with seed `20260606`. Their labels come from versioned
transparent scorecard formulas plus bounded random noise.

Affordability features are debt-to-income ratio, installment burden, expense
ratio, recent overdrafts, and unverified income. Credit-risk features are
utilization, recent delinquencies, employment shortfall, annual debt ratio,
and recent overdrafts. Every feature has a positive monotonic adverse-risk
constraint.

Training uses separate train, calibration, and test partitions. Platt
calibration is stored as JSON. XGBoost models are stored in native JSON and
checked against the SHA-256 value in their manifest. Native XGBoost
contributions provide local TreeSHAP explanations.

These models demonstrate the complete architecture. They are not approved for
real lending because synthetic labels do not represent repayment outcomes.

## South German Credit

The benchmark downloads UCI dataset 573 from its official archive and verifies
archive SHA-256:

```text
0b40d40eb7321693d559e247a556f88a6cc8df8489c3cb2ae084db7592584551
```

The raw target is normalized from `0=bad, 1=good` to `bad_credit=1`. Age,
personal status/sex, and foreign-worker fields are excluded from scoring and
retained only for optional audits.

Logistic regression and XGBoost are evaluated with repeated stratified
five-fold cross-validation. Reports include ROC-AUC, PR-AUC, Brier score,
expected calibration error, fold uncertainty, and global SHAP importance.

The data are historical, sampled from 1973 to 1975, oversample bad credits,
contain a transformed amount field, and do not match SpendPilot inputs. The
benchmark never creates applicant-level SpendPilot scores.

## OpenRouter Manager Assistant

The default hosted route is `openrouter/free`. OpenRouter may select a
different free model for each request, so the returned model ID and request ID
are attached to every accepted Manager narrative. Requests use temperature
zero, a 256-token output limit, and strict JSON-schema response mode.

The provider preferences require parameter support, deny endpoints that collect
data, and request zero-data-retention routing. If no free endpoint can satisfy
those requirements, the assistant fails closed to deterministic Manager
behavior.

OpenRouter receives no applicant name, raw document, unrestricted feedback
comment, or hidden chain-of-thought. It returns schema-validated JSON for:

- a reviewer-facing narrative;
- disagreement explanation and review focus;
- a non-authoritative feedback-routing proposal.

The Manager validates feedback identifiers, mandatory targets, and allowed
specialists. Invalid JSON, timeouts, missing targets, and unauthorized targets
fall back to deterministic behavior. The hosted model cannot change snapshots,
reports, scores, policy rules, or decisions.

## Experimental Local GGUF Assistant

The optional local runtime uses Homebrew `llama.cpp`, Metal acceleration, and a
loopback-only HTTP server. The model file is supplied through `--gguf-path` or
`SPENDPILOT_GGUF_PATH`; it is never copied into the repository.

The current smoke target is `phi-1.5.Q4_K_M.gguf`. Phi-1.5 is a pretrained base
model without an embedded chat template, so it is not promoted even when
llama.cpp grammar constraints produce schema-valid JSON. Runtime controls are:

```text
context size:       2048 tokens
output limit:       256 tokens
temperature:        0
parallel requests:  1
transport:          http://127.0.0.1:8080
```

The smoke artifact records one-way hashes of the model path and model content,
the llama.cpp build, latency, schema validity, fallback status, and
recommendation. Malformed JSON, timeout, server failure, invalid feedback
targets, or unsupported output falls back to the deterministic Manager. If
structured reliability is inadequate, the next candidate is
Phi-4-mini-instruct Q4_K_M rather than granting more authority to Phi-1.5.

## Local Artifacts

Generated content remains ignored by Git:

```text
data/raw/                         downloaded benchmark source
artifacts/models/                 XGBoost, calibration, and manifests
artifacts/reports/                benchmark, smoke, and HTML reports
artifacts/logs/                   local llama.cpp server logs
```

Committed code, configuration, checksums, seeds, schemas, and tests are
sufficient to reproduce these artifacts.
