# Decision Governance

## Authority

- Specialist agents provide evidence-bound recommendations.
- The manager coordinates communication and summarizes disagreements.
- Authorized humans resolve review tasks.
- Only the deterministic policy engine creates final decision records.

## Mandatory Human Review

Review is required when:

- specialist recommendations disagree;
- any specialist recommends `DECLINE` or `REFER`;
- required evidence or a required report is missing;
- model confidence, calibration, or monotonicity checks fail;
- the case is outside the validated model population;
- a fraud, identity, fairness, or policy guardrail triggers;
- an applicant appeals a decision.

## Model Controls

Every production model must have:

- a registered owner, purpose, and validated population;
- immutable training-data and feature lineage;
- a versioned artifact and approval status;
- calibration, stability, performance, and fairness results;
- monotonic constraints documented by feature;
- reason-code mappings reviewed by risk and compliance;
- a rollback target and retirement process.

A logistic scorecard remains the audit benchmark for monotonic XGBoost credit
models. Material disagreement between benchmark and production models is a
review trigger.

## Explanation Rules

- Explanations must reference factors actually used by the model.
- Reason codes must map to evidence-backed feature contributions.
- The manager may rewrite approved reasons for clarity but may not invent,
  remove, or reorder principal reasons without a deterministic rule.
- Raw chain-of-thought is not an explanation artifact.

## Audit and Security

- Store raw PII separately from agent and trace records.
- Use immutable snapshot hashes and append-only decision events.
- Propagate case, workflow, trace, model, and policy version identifiers.
- Record all human views, challenges, overrides, and resolutions.
- Never place PII, credentials, or raw documents in telemetry baggage.
