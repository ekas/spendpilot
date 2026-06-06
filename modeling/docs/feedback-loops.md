# Governed Feedback Loops

SpendPilot has two feedback paths with different authorities and timing.

## Case Re-analysis

Case feedback comes from an authorized reviewer or an applicant appeal:

```text
feedback submission
  -> evidence verification
  -> Manager target selection
  -> revised immutable case snapshot
  -> all three specialists rerun
  -> report deltas
  -> mandatory human review
  -> deterministic policy decision
```

The submitted event remains unchanged. Verification and Manager routing produce
an accepted copy containing the selected specialist targets. Applicant feedback
must include evidence references, and every reference must exist in the revised
snapshot.

All specialists rerun so their reports remain comparable against the same data
version. Only targeted specialists receive the accepted feedback event and mark
it in `responded_feedback_ids`. Model adapters receive only the revised
`CaseSnapshot`; they never receive reviewer or applicant prose.

Each re-analysis creates:

- a new snapshot identifier;
- an `AnalysisRound` linked to its parent;
- new immutable specialist reports;
- per-agent `AgentReportDelta` records;
- a new policy decision and human-review task.

Previous snapshots, reports, decisions, and feedback submissions are retained.

## Repayment Outcomes

Repayment observations form an offline learning path:

```text
servicer / ledger / bureau event
  -> append-only deduplicated outcome store
  -> 90+ DPD within 12 months label
  -> point-in-time training dataset
  -> candidate model evaluation
  -> explicit human approval
  -> separate deployment process
```

A positive label matures when a 90-or-more-days-past-due event occurs inside the
12-month observation window. A negative label matures only when the complete
window ends without such an event.

Dataset examples use the exact snapshot referenced by the original finalized
approval decision. Snapshots created after the decision cutoff are rejected.
Declined, referred, non-final, and immature cases are not included.

Outcome ingestion has no access to the production `ModelRegistry`. Approval of
a candidate is an audit artifact, not an automatic deployment.
