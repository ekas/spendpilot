# Decision Data Flow

## 1. Intake

1. Accept the current backend `Applicant` payload.
2. Apply document hints conservatively: lower verified income and employment,
   but higher expenses, debt, utilization, and delinquencies.
3. Replace document names with opaque hashes.
4. Exclude applicant name and raw document text from the modeling snapshot.
5. Tokenize applicant identifiers and isolate raw PII.

## 2. Snapshot

Create an immutable case snapshot containing:

- product and requested amount;
- feature values with transformation versions;
- references to source evidence;
- missing-data indicators;
- a content hash and creation timestamp.

Agents receive the snapshot identifier and permitted feature subset. They do
not mutate shared application state.

## 3. Parallel Assessment

The workflow runs all three specialists independently:

```text
case snapshot
  +-> credibility model
  +-> affordability model
  +-> credit-risk model
```

Each result includes a model version, calibrated score, recommendation,
reason codes, feature contributions, evidence references, limitations, and
monotonicity-check status.

Scores are adverse-risk probabilities: lower is safer and higher is riskier.

## 4. Manager Consolidation

The manager validates the report set and emits:

- the original reports unchanged;
- missing-agent identifiers;
- agreement or disagreement status;
- a proposed action for policy evaluation;
- a concise review summary.

The manager cannot issue a final decision.

When enabled, OpenRouter or the local llama.cpp adapter receives only compact
structured reports, deltas, reason codes, opaque evidence references, and
aggregate benchmark context. Both require schema-valid JSON and store actual
model provenance. OpenRouter denies data-collecting providers and requests
zero-data-retention routing. The local adapter binds to loopback and reads the
GGUF path from a command argument or environment variable. Narratives are
stored separately from deterministic consolidation.

## 5. Policy Evaluation

The deterministic policy engine applies versioned rules:

- incomplete reports route to `REQUEST_MORE_DATA`;
- disagreement routes to `REFER`;
- any `DECLINE` or `REFER` recommendation requires human review;
- unanimous valid `APPROVE` reports may be finalized automatically;
- policy or fairness guardrails override automatic processing.

## 6. Human Review

A reviewer can:

- approve the proposed action;
- request additional evidence;
- challenge a report and request re-analysis;
- override the proposed action with a mandatory reason;
- escalate the case.

The action is stored as a signed resolution and returned to the policy engine
for finalization.

## 7. Decision and Monitoring

The final record contains:

- case and snapshot identifiers;
- specialist report and model versions;
- manager consolidation;
- triggered policy rules;
- reviewer identity and rationale, when applicable;
- final action and reason codes;
- trace and decision timestamps.

Outcomes later feed model calibration, drift, stability, and fairness
monitoring. They never update production models automatically.

## 8. Case Feedback

1. Store the reviewer correction or applicant appeal as an immutable event.
2. Verify every evidence reference against a revised case snapshot.
3. Let the Manager select the specialist targets.
4. Create an `AnalysisRound` linked to the previous round.
5. Rerun all specialists against the revised snapshot.
6. Mark targeted responses and calculate report deltas.
7. Route the new round to mandatory human review.
8. Return the human resolution to the policy engine.

Raw feedback rationale is retained for audit but is not supplied to model
adapters or transformed into model features.

## 9. Outcome Feedback

1. Append and deduplicate repayment events from approved sources.
2. Link events to the finalized approval decision.
3. Label 90+ days past due within 12 calendar months as the primary outcome.
4. Mature negative labels only after the full observation window.
5. Join labels to the exact original decision snapshot.
6. Evaluate candidate models offline.
7. Require explicit validation and approval before any separate deployment.
