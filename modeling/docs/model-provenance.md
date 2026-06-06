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

## Phi Manager Assistant

`mlx-community/Phi-4-mini-instruct-4bit` is used as a pretrained model without
fine-tuning. It runs one request at a time with at most 2,048 input tokens, 256
output tokens, and deterministic sampling.

Phi receives no applicant name, raw document, unrestricted feedback comment,
or hidden chain-of-thought. It returns schema-validated JSON for:

- a reviewer-facing narrative;
- disagreement explanation and review focus;
- a non-authoritative feedback-routing proposal.

The Manager validates feedback identifiers, mandatory targets, and allowed
specialists. Invalid JSON, timeouts, missing targets, and unauthorized targets
fall back to deterministic behavior. Phi cannot change snapshots, reports,
scores, policy rules, or decisions.

## Local Artifacts

Generated content remains ignored by Git:

```text
data/raw/                         downloaded benchmark source
artifacts/models/                 XGBoost, calibration, and manifests
artifacts/reports/                benchmark and evaluation reports
models/phi/                       pretrained Phi weights
```

Committed code, configuration, checksums, seeds, schemas, and tests are
sufficient to reproduce these artifacts.
