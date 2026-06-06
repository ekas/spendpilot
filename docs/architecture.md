# SpendPilot Architecture

## Purpose

SpendPilot supports explainable consumer-credit decisions with three independent
specialist agents, a lightweight manager agent, explicit human review, and a
deterministic policy engine.

The language model is a communication component. It does not calculate risk,
modify specialist scores, or issue final credit decisions.

## Components

### Specialist agents

- **Data Credibility Agent** checks completeness, provenance, inconsistencies,
  and source reliability.
- **Affordability Agent** assesses income stability, expense burden, free cash
  flow, and repayment capacity.
- **Credit Risk Agent** estimates probability of default from repayment and
  utilization features.

Each agent wraps a versioned model adapter and returns the same `AgentReport`
contract. Production adapters will use monotonic XGBoost and TreeSHAP.

### Manager agent

The manager receives the frozen specialist reports and:

- checks that all required specialists responded;
- detects disagreement and requests for more data;
- prepares a bounded summary for a human reviewer;
- preserves every specialist score and evidence reference unchanged.

The initial scaffold uses deterministic summarization. A quantized
Phi-4-mini-instruct adapter can later translate the structured summary into
reviewer-facing language without changing its facts.

### Policy engine

The policy engine is deterministic and versioned. It evaluates manager and
specialist outputs, applies review rules, and produces the only authoritative
decision record.

### Human review

Cases are queued for review when reports disagree, contain an adverse
recommendation, request more information, are incomplete, or trigger a policy
guardrail. Human resolutions are inputs to the policy engine, not direct
database edits.

## Runtime Boundaries

The initial implementation is a modular Python application:

```text
API / batch caller
       |
Case snapshot + evidence references
       |
Parallel specialist execution
       |
Manager consolidation
       |
Deterministic policy evaluation
       |
Human review when required
       |
Policy-controlled finalization
```

The modules can be separated into services later without changing the public
contracts.

## Explainability

Every report links:

```text
model score
  -> reason code
  -> feature contribution
  -> engineered feature
  -> evidence reference
  -> immutable case snapshot
```

The audit record stores model versions, policy versions, evidence hashes, human
actions, and final reason codes. Hidden model chain-of-thought is neither
requested nor persisted.
