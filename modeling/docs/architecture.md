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
contract. The demo uses deterministic credibility rules plus monotonic
XGBoost affordability and credit-risk models. XGBoost native contribution
output provides TreeSHAP explanations.

All specialist scores use one convention: `0` is lower adverse risk and `1`
is higher adverse risk.

### Manager agent

The manager receives the frozen specialist reports and:

- checks that all required specialists responded;
- detects disagreement and requests for more data;
- prepares a bounded summary for a human reviewer;
- preserves every specialist score and evidence reference unchanged.

Deterministic consolidation remains authoritative. Optional OpenRouter and
local llama.cpp assistants translate structured reports into reviewer-facing
language and propose feedback targets. Provider and model provenance, request
metadata, and local latency are stored with accepted output. Schema validation
and Manager allowlists reject malformed or unauthorized output.

The local adapter uses a GGUF path supplied at runtime and a private
`llama-server` bound to `127.0.0.1`. Phi-1.5 is treated as experimental because
it is a base model without an embedded chat template. It has no path to
specialist scores, policy rules, or final decisions.

### Policy engine

The policy engine is deterministic and versioned. It evaluates manager and
specialist outputs, applies review rules, and produces the only authoritative
decision record.

### Human review

Cases are queued for review when reports disagree, contain an adverse
recommendation, request more information, are incomplete, or trigger a policy
guardrail. Human resolutions are inputs to the policy engine, not direct
database edits.

### Feedback and offline learning

Reviewer corrections and verified applicant appeals create new immutable
analysis rounds. The Manager routes the accepted feedback, all three
specialists rerun against one revised snapshot, and policy requires a new human
resolution.

Repayment observations are handled by a separate offline learning subsystem.
They create mature outcome labels and point-in-time datasets, but cannot modify
the active model registry or production decision workflow.

The South German Credit model is a research benchmark only. Its aggregate
metrics and limitations may be supplied to the Manager, but it cannot score a
SpendPilot case because the feature populations do not match.

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
       |
Repayment outcomes -> offline evaluation and approved model candidates
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

The standalone explainability report renders the same stored explanation
contracts as inline HTML, CSS, and SVG. Positive TreeSHAP values are shown as
risk-increasing and negative values as protective. The generated report is an
ignored local artifact and contains no applicant names or raw documents.
