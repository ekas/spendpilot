"""Interactive, self-contained visualization of governed decisions."""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from spendpilot.assistants.smoke import load_local_llm_smoke
from spendpilot.demo import (
    run_case_snapshots,
    run_sample_cases,
    sample_case_snapshots,
)
from spendpilot.ingestion import load_external_cases
from spendpilot.orchestration.workflow import WorkflowResult
from spendpilot.reports.humanize import (
    agent_method_label,
    contribution_explanation,
    evidence_summary,
    format_feature_value,
    human_label,
    policy_explanation,
    reason_explanation,
)
from spendpilot.schemas.agent_report import (
    AgentId,
    AgentReport,
    FeatureContribution,
)
from spendpilot.schemas.case import CaseSnapshot
from spendpilot.schemas.modeling import (
    LocalLLMProbePurpose,
    LocalLLMSmokeReport,
)


AGENT_ORDER = {
    AgentId.CREDIBILITY: 0,
    AgentId.AFFORDABILITY: 1,
    AgentId.CREDIT_RISK: 2,
}


def contribution_direction(contribution: float) -> str:
    """Translate SHAP sign into a stable adverse-risk direction."""

    if contribution > 0:
        return "increases risk"
    if contribution < 0:
        return "protective"
    return "neutral"


def generate_explainability_report(
    *,
    model_root: Path | str,
    benchmark_report_path: Path | str,
    smoke_report_path: Path | str,
    output_path: Path | str,
    input_path: Path | str | None = None,
) -> Path:
    """Run deterministic cases and render one portable HTML artifact."""

    if input_path is None:
        snapshots = sample_case_snapshots()
        results = run_sample_cases(
            model_root,
            benchmark_report_path=benchmark_report_path,
        )
    else:
        requests = load_external_cases(input_path)
        snapshots = tuple(request.to_snapshot() for request in requests)
        results = run_case_snapshots(
            model_root,
            snapshots,
            benchmark_report_path=benchmark_report_path,
        )
    benchmark = _load_json_if_present(Path(benchmark_report_path))
    smoke = _load_smoke_if_present(Path(smoke_report_path))
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        _render_report(
            results=results,
            snapshots=snapshots,
            benchmark=benchmark,
            smoke=smoke,
        )
    )
    return output


def _render_report(
    *,
    results: tuple[WorkflowResult, ...],
    snapshots: tuple[CaseSnapshot, ...],
    benchmark: dict[str, object] | None,
    smoke: LocalLLMSmokeReport | None,
) -> str:
    generated = datetime.now(timezone.utc).isoformat()
    finalized = sum(result.decision.finalized for result in results)
    review_count = sum(result.review_task is not None for result in results)
    tabs = "".join(
        _render_case_tab(result, index, index == 1)
        for index, result in enumerate(results, start=1)
    )
    panels = "\n".join(
        _render_case(result, snapshot, smoke, index == 1)
        for index, (result, snapshot) in enumerate(
            zip(results, snapshots, strict=True),
            start=1,
        )
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SpendPilot Agent Decision Explorer</title>
<style>
:root {{
  color-scheme: light;
  --ink: #172027;
  --muted: #5c6871;
  --line: #cbd3d8;
  --surface: #f5f7f8;
  --surface-strong: #e9eef1;
  --risk: #b42318;
  --safe: #147a43;
  --accent: #176b87;
  --manager: #5c4b99;
  --warning: #986500;
  --white: #ffffff;
}}
* {{ box-sizing: border-box; }}
html {{ scroll-behavior: smooth; }}
body {{
  margin: 0;
  background: var(--white);
  color: var(--ink);
  font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}}
button {{ font: inherit; }}
header, main, footer {{
  width: min(1240px, calc(100% - 32px));
  margin: auto;
}}
header {{
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 24px;
  padding: 30px 0 22px;
  border-bottom: 2px solid var(--ink);
}}
h1 {{ margin: 0; font-size: 30px; letter-spacing: 0; }}
h2 {{ margin: 0 0 16px; font-size: 22px; letter-spacing: 0; }}
h3 {{ margin: 0 0 10px; font-size: 17px; letter-spacing: 0; }}
p {{ margin: 6px 0; }}
.meta {{ color: var(--muted); font-size: 13px; }}
.warning {{
  margin: 22px 0 0;
  padding: 13px 16px;
  border-left: 4px solid var(--warning);
  background: #fff8e6;
}}
.summary {{
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-top: 22px;
  border: 1px solid var(--line);
  border-radius: 6px;
}}
.summary div {{ padding: 15px 18px; border-right: 1px solid var(--line); }}
.summary div:last-child {{ border-right: 0; }}
.summary strong {{ display: block; font-size: 24px; }}
.case-tabs {{
  display: flex;
  gap: 2px;
  margin-top: 26px;
  border-bottom: 1px solid var(--line);
}}
.case-tab {{
  appearance: none;
  border: 0;
  border-bottom: 3px solid transparent;
  background: transparent;
  color: var(--muted);
  padding: 10px 16px 9px;
  cursor: pointer;
}}
.case-tab:hover {{ color: var(--ink); background: var(--surface); }}
.case-tab[aria-selected="true"] {{
  color: var(--ink);
  border-bottom-color: var(--accent);
  font-weight: 700;
}}
.case-panel {{ padding: 28px 0; border-bottom: 1px solid var(--line); }}
.case-panel[hidden] {{ display: none; }}
.case-heading {{
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}}
.status {{
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 13px;
  font-weight: 700;
}}
.status::before {{
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--safe);
  content: "";
}}
.status.review::before {{ background: var(--warning); }}
.pipeline {{
  display: grid;
  grid-template-columns: minmax(160px, 0.9fr) 42px minmax(250px, 1.5fr) 42px
    minmax(160px, 0.9fr) 42px minmax(180px, 1fr);
  align-items: center;
  gap: 0;
  padding: 18px;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 6px;
}}
.stage {{
  min-width: 0;
  padding: 14px;
  background: var(--white);
  border: 1px solid var(--line);
  border-top: 4px solid var(--accent);
  border-radius: 6px;
}}
.stage.manager {{ border-top-color: var(--manager); }}
.stage.policy {{ border-top-color: var(--warning); }}
.stage.output {{ border-top-color: var(--safe); }}
.stage.output.review {{ border-top-color: var(--warning); }}
.stage-label {{
  color: var(--muted);
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
}}
.stage-value {{ margin-top: 4px; font-size: 16px; font-weight: 750; }}
.stage-detail {{ color: var(--muted); font-size: 12px; overflow-wrap: anywhere; }}
.flow-link {{
  position: relative;
  height: 2px;
  background: var(--line);
}}
.flow-link::before {{
  position: absolute;
  top: -4px;
  right: -1px;
  width: 0;
  height: 0;
  border-top: 5px solid transparent;
  border-bottom: 5px solid transparent;
  border-left: 7px solid var(--muted);
  content: "";
}}
.flow-link::after {{
  position: absolute;
  top: -3px;
  left: 0;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent);
  content: "";
  animation: move-data 2.8s linear infinite;
}}
@keyframes move-data {{
  from {{ transform: translateX(0); }}
  to {{ transform: translateX(32px); }}
}}
.agent-lane {{ display: grid; gap: 8px; }}
.agent-node {{
  width: 100%;
  display: grid;
  grid-template-columns: 30px 1fr auto;
  align-items: center;
  gap: 9px;
  padding: 9px 10px;
  border: 1px solid var(--line);
  border-left: 4px solid var(--accent);
  border-radius: 5px;
  background: var(--white);
  color: var(--ink);
  text-align: left;
  cursor: pointer;
}}
.agent-node:hover, .agent-node:focus-visible {{
  border-color: var(--accent);
  outline: 2px solid #b8d9e3;
  outline-offset: 1px;
}}
.agent-node.active {{ background: #edf7fa; border-color: var(--accent); }}
.agent-code {{
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border: 1px solid var(--accent);
  border-radius: 50%;
  color: var(--accent);
  font-size: 12px;
  font-weight: 800;
}}
.agent-node strong {{ display: block; font-size: 13px; }}
.agent-node small {{ color: var(--muted); }}
.node-score {{ font-variant-numeric: tabular-nums; font-weight: 750; }}
.input-strip {{
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  margin-top: 14px;
  border: 1px solid var(--line);
  border-radius: 6px;
}}
.input-strip div {{ min-width: 0; padding: 10px 12px; border-right: 1px solid var(--line); }}
.input-strip div:last-child {{ border-right: 0; }}
.label {{ display: block; color: var(--muted); font-size: 11px; }}
.input-strip strong {{ display: block; overflow-wrap: anywhere; }}
.agents {{
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-top: 22px;
}}
.agent {{
  min-width: 0;
  padding: 15px;
  border: 1px solid var(--line);
  border-top: 4px solid var(--accent);
  border-radius: 6px;
  overflow: hidden;
  transition: border-color 160ms ease, box-shadow 160ms ease;
}}
.agent.active {{
  border-color: var(--accent);
  box-shadow: 0 0 0 3px #d8ebf1;
}}
.agent-heading {{
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 12px;
}}
.score-number {{ font-size: 24px; font-weight: 780; font-variant-numeric: tabular-nums; }}
.recommendation {{
  padding: 3px 7px;
  border-radius: 4px;
  background: var(--surface-strong);
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
}}
.recommendation.approve {{ color: var(--safe); background: #e9f6ee; }}
.recommendation.decline {{ color: var(--risk); background: #fcebea; }}
.recommendation.refer, .recommendation.request-more-data {{
  color: var(--warning);
  background: #fff5d9;
}}
.risk-gauge {{ width: 100%; height: auto; display: block; margin: 8px 0 12px; }}
.chart-title {{ margin: 14px 0 7px; font-size: 12px; font-weight: 750; }}
.shap-chart {{ display: grid; gap: 5px; }}
.contribution-row {{
  width: 100%;
  display: grid;
  grid-template-columns: minmax(105px, 1fr) 78px minmax(120px, 1.25fr);
  align-items: center;
  gap: 7px;
  padding: 6px 4px;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: var(--ink);
  text-align: left;
  cursor: pointer;
}}
.contribution-row:hover, .contribution-row:focus-visible {{
  background: var(--surface);
  outline: 1px solid var(--line);
}}
.feature-name {{ overflow-wrap: anywhere; font-size: 12px; }}
.feature-impact {{ color: var(--muted); font-size: 12px; font-variant-numeric: tabular-nums; text-align: right; }}
.shap-track {{
  position: relative;
  height: 16px;
  background: #eef1f3;
  overflow: hidden;
}}
.shap-track::after {{
  position: absolute;
  top: 0;
  bottom: 0;
  left: 50%;
  width: 1px;
  background: #7e8991;
  content: "";
}}
.shap-bar {{ position: absolute; top: 2px; height: 12px; width: var(--bar-size); }}
.shap-bar.increases {{ left: 50%; background: var(--risk); }}
.shap-bar.protective {{ right: 50%; background: var(--safe); }}
.shap-bar.neutral {{ left: 50%; width: 2px; background: var(--muted); }}
.contribution-detail {{
  min-height: 58px;
  margin-top: 9px;
  padding: 9px 10px;
  background: var(--surface);
  border-left: 3px solid var(--accent);
  font-size: 12px;
}}
.reason-list {{
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin: 10px 0 0;
  padding: 0;
  list-style: none;
}}
.reason-list li {{
  padding: 3px 6px;
  border: 1px solid var(--line);
  border-radius: 4px;
  color: var(--muted);
  font-size: 11px;
  overflow-wrap: anywhere;
}}
.governance {{
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 14px;
  margin-top: 16px;
}}
.narrative, .policy-detail {{
  padding: 14px;
  border-left: 4px solid var(--accent);
  background: #eef7fa;
}}
.narrative.fallback {{ border-left-color: var(--warning); background: #fff8e6; }}
.policy-detail {{ border-left-color: var(--warning); background: #fff8e6; }}
.rule-list {{ margin: 8px 0 0; padding-left: 18px; }}
.reference-section {{ padding: 28px 0; border-bottom: 1px solid var(--line); }}
.reference-grid {{ display: grid; grid-template-columns: 1fr 1.25fr; gap: 20px; }}
.metrics {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
.metrics th, .metrics td {{
  padding: 7px 6px;
  border-bottom: 1px solid var(--line);
  text-align: left;
  overflow-wrap: anywhere;
}}
.metrics th {{ color: var(--muted); font-weight: 600; }}
.importance-chart {{ display: grid; gap: 7px; }}
.importance-row {{
  display: grid;
  grid-template-columns: minmax(140px, 1fr) minmax(140px, 2fr) 52px;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}}
.importance-track {{ height: 14px; background: var(--surface-strong); }}
.importance-bar {{ height: 100%; background: var(--accent); }}
.limitations {{ color: var(--muted); }}
footer {{ padding: 24px 0 40px; color: var(--muted); }}
@media (max-width: 1000px) {{
  .pipeline {{
    grid-template-columns: 1fr;
    gap: 8px;
  }}
  .flow-link {{ width: 2px; height: 24px; margin: auto; }}
  .flow-link::before {{
    top: auto;
    right: -4px;
    bottom: -1px;
    border-top: 7px solid var(--muted);
    border-right: 5px solid transparent;
    border-bottom: 0;
    border-left: 5px solid transparent;
  }}
  .flow-link::after {{ top: 0; left: -3px; animation: move-data-mobile 2s linear infinite; }}
  @keyframes move-data-mobile {{
    from {{ transform: translateY(0); }}
    to {{ transform: translateY(17px); }}
  }}
  .agents {{ grid-template-columns: 1fr; }}
  .input-strip {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
  .input-strip div:nth-child(3) {{ border-right: 0; }}
  .input-strip div:nth-child(-n+3) {{ border-bottom: 1px solid var(--line); }}
}}
@media (max-width: 700px) {{
  header, .case-heading {{ align-items: start; flex-direction: column; }}
  .summary, .governance, .reference-grid {{ grid-template-columns: 1fr; }}
  .summary div {{ border-right: 0; border-bottom: 1px solid var(--line); }}
  .summary div:last-child {{ border-bottom: 0; }}
  .case-tabs {{ overflow-x: auto; }}
  .case-tab {{ flex: 0 0 auto; }}
  .input-strip {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
  .input-strip div {{ border-bottom: 1px solid var(--line); }}
  .input-strip div:nth-child(2n) {{ border-right: 0; }}
  .input-strip div:nth-last-child(-n+2) {{ border-bottom: 0; }}
  .contribution-row {{ grid-template-columns: minmax(90px, 1fr) 72px minmax(100px, 1.2fr); }}
}}
@media (prefers-reduced-motion: reduce) {{
  html {{ scroll-behavior: auto; }}
  .flow-link::after {{ animation: none; }}
}}
</style>
</head>
<body>
<header>
  <div>
    <h1>SpendPilot Agent Decision Explorer</h1>
    <p>PII-minimized inputs, parallel specialist analysis, governed decisions.</p>
  </div>
  <p class="meta">Generated {html.escape(generated)}</p>
</header>
<main>
  <div class="warning">
    Development demonstration only. The tabular agents use synthetic labels,
    and the South German Credit benchmark does not represent SpendPilot
    applicants. This system is not approved for production lending.
  </div>
  <div class="summary">
    <div><strong>{len(results)}</strong>offline cases</div>
    <div><strong>{finalized}</strong>automatic approvals</div>
    <div><strong>{review_count}</strong>human-review routes</div>
  </div>
  <nav class="case-tabs" role="tablist" aria-label="Demo cases">
    {tabs}
  </nav>
  {panels}
  {_render_supported_inputs()}
  {_render_benchmark(benchmark)}
  {_render_local_model(smoke)}
</main>
<footer>
  Scores use adverse-risk orientation: 0 is lower risk and 1 is higher risk.
  Red factors raise the model's risk estimate and green factors lower it.
  Only the deterministic policy engine creates decisions.
</footer>
<script>
(() => {{
  const tabs = [...document.querySelectorAll(".case-tab")];
  const panels = [...document.querySelectorAll(".case-panel")];

  function selectCase(caseId) {{
    tabs.forEach((tab) => {{
      const selected = tab.dataset.caseId === caseId;
      tab.setAttribute("aria-selected", String(selected));
      tab.tabIndex = selected ? 0 : -1;
    }});
    panels.forEach((panel) => {{
      panel.hidden = panel.dataset.caseId !== caseId;
    }});
  }}

  tabs.forEach((tab, index) => {{
    tab.addEventListener("click", () => selectCase(tab.dataset.caseId));
    tab.addEventListener("keydown", (event) => {{
      if (!["ArrowLeft", "ArrowRight"].includes(event.key)) return;
      event.preventDefault();
      const offset = event.key === "ArrowRight" ? 1 : -1;
      const target = tabs[(index + offset + tabs.length) % tabs.length];
      selectCase(target.dataset.caseId);
      target.focus();
    }});
  }});

  document.querySelectorAll(".agent-node").forEach((node) => {{
    node.addEventListener("click", () => {{
      const panel = node.closest(".case-panel");
      panel.querySelectorAll(".agent-node, .agent").forEach(
        (item) => item.classList.remove("active")
      );
      node.classList.add("active");
      const target = document.getElementById(node.dataset.agentTarget);
      target.classList.add("active");
      target.scrollIntoView({{ behavior: "smooth", block: "center" }});
    }});
  }});

  document.querySelectorAll(".contribution-row").forEach((row) => {{
    const update = () => {{
      const detail = document.getElementById(row.dataset.detailTarget);
      detail.textContent = row.dataset.detail;
    }};
    row.addEventListener("mouseenter", update);
    row.addEventListener("focus", update);
    row.addEventListener("click", update);
  }});
}})();
</script>
</body>
</html>
"""


def _render_case_tab(
    result: WorkflowResult,
    index: int,
    selected: bool,
) -> str:
    case_id = result.analysis_round.case_id
    return (
        f'<button class="case-tab" role="tab" '
        f'data-case-id="{html.escape(case_id)}" '
        f'aria-controls="panel-{html.escape(case_id)}" '
        f'aria-selected="{str(selected).lower()}" '
        f'tabindex="{0 if selected else -1}">Case {index}</button>'
    )


def _render_case(
    result: WorkflowResult,
    snapshot: CaseSnapshot,
    smoke: LocalLLMSmokeReport | None,
    selected: bool,
) -> str:
    case_id = result.analysis_round.case_id
    reports = tuple(
        sorted(result.reports, key=lambda report: AGENT_ORDER[report.agent_id])
    )
    status_class = "review" if result.review_task else ""
    status_text = (
        "Human review required"
        if result.review_task
        else "Automatically finalized"
    )
    agents = "\n".join(
        _render_agent(report, snapshot) for report in reports
    )
    return f"""
<section class="case-panel" id="panel-{html.escape(case_id)}"
  data-case-id="{html.escape(case_id)}" role="tabpanel"
  {"hidden" if not selected else ""}>
  <div class="case-heading">
    <div>
      <h2>{html.escape(_case_display_name(case_id))}</h2>
      <p class="meta">Case reference: {html.escape(case_id)} | Initial assessment</p>
    </div>
    <span class="status {status_class}">{status_text}</span>
  </div>
  {_render_pipeline(result, snapshot, reports)}
  {_render_input_strip(snapshot)}
  <div class="agents">{agents}</div>
  <div class="governance">
    {_narrative_for_case(smoke, case_id)}
    {_render_policy_detail(result)}
  </div>
</section>
"""


def _render_pipeline(
    result: WorkflowResult,
    snapshot: CaseSnapshot,
    reports: tuple[AgentReport, ...],
) -> str:
    case_id = result.analysis_round.case_id
    agent_nodes = "".join(_render_agent_node(report) for report in reports)
    output_class = "review" if result.review_task else ""
    output_value = (
        "Human review queue"
        if result.review_task
        else result.decision.action.value.replace("_", " ").title()
    )
    output_detail = (
        f"Policy action: {result.decision.action.value}"
        if result.review_task
        else "Final decision record created"
    )
    return f"""
<div class="pipeline" aria-label="Input to decision workflow">
  <div class="stage">
    <span class="stage-label">1. Input snapshot</span>
    <div class="stage-value">{html.escape(snapshot.product.value.replace("_", " ").title())}</div>
    <div class="stage-detail">{html.escape(snapshot.currency)} {_format_number(snapshot.requested_amount)} requested<br>
    {len(snapshot.evidence_refs)} supporting documents; personal identifiers removed</div>
  </div>
  <div class="flow-link" aria-hidden="true"></div>
  <div>
    <span class="stage-label">2. Parallel specialist agents</span>
    <div class="agent-lane">{agent_nodes}</div>
  </div>
  <div class="flow-link" aria-hidden="true"></div>
  <div class="stage manager">
    <span class="stage-label">3. Manager agent</span>
    <div class="stage-value">{html.escape(result.manager_report.proposed_action.value.replace("_", " ").title())}</div>
    <div class="stage-detail">Specialist disagreement: {str(result.manager_report.disagreement).lower()}<br>
    Reports preserved unchanged: {len(result.manager_report.reports)}</div>
  </div>
  <div class="flow-link" aria-hidden="true"></div>
  <div>
    <div class="stage policy">
      <span class="stage-label">4. Policy engine</span>
      <div class="stage-value">Consumer credit rules</div>
      <div class="stage-detail">{len(result.decision.policy_rules)} policy rule
      {"" if len(result.decision.policy_rules) == 1 else "s"} applied</div>
    </div>
    <div class="stage output {output_class}" style="margin-top:8px">
      <span class="stage-label">5. Governed output</span>
      <div class="stage-value">{html.escape(output_value)}</div>
      <div class="stage-detail">{html.escape(output_detail)}<br>Linked to this assessment</div>
    </div>
  </div>
</div>
"""


def _render_agent_node(report: AgentReport) -> str:
    name = report.agent_id.value.replace("_", " ").title()
    code = {
        AgentId.CREDIBILITY: "C",
        AgentId.AFFORDABILITY: "A",
        AgentId.CREDIT_RISK: "R",
    }[report.agent_id]
    target = f"{report.case_id}-{report.agent_id.value}"
    return f"""
<button class="agent-node" data-agent-target="{html.escape(target)}">
  <span class="agent-code">{code}</span>
  <span><strong>{html.escape(name)}</strong>
  <small>{html.escape(report.recommendation.value.replace("_", " "))}</small></span>
  <span class="node-score">{report.score:.0%}</span>
</button>
"""


def _render_input_strip(snapshot: CaseSnapshot) -> str:
    features = snapshot.features
    values = (
        ("Monthly income", features.get("monthly_income"), snapshot.currency),
        ("Monthly expenses", features.get("monthly_expenses"), snapshot.currency),
        ("Existing debt", features.get("existing_debt"), snapshot.currency),
        ("Credit utilization", features.get("credit_utilization"), "percent"),
        ("Employment", features.get("employment_months"), "months"),
        (
            "Evidence status",
            (
                "complete"
                if not snapshot.missing_fields
                else f"{len(snapshot.missing_fields)} missing"
            ),
            None,
        ),
    )
    items = "".join(
        f"<div><span class=\"label\">{html.escape(label)}</span>"
        f"<strong>{html.escape(_format_input_value(value, unit))}</strong></div>"
        for label, value, unit in values
    )
    return f'<div class="input-strip">{items}</div>'


def _render_agent(
    report: AgentReport,
    snapshot: CaseSnapshot,
) -> str:
    agent_id = f"{report.case_id}-{report.agent_id.value}"
    recommendation_class = report.recommendation.value.replace("_", "-")
    contributions = _contribution_chart(
        report.top_contributors,
        agent_id,
        snapshot,
    )
    reasons = "".join(
        f"<li>{html.escape(reason_explanation(reason))}</li>"
        for reason in report.reason_codes
    )
    limitations = "; ".join(report.limitations) or "None recorded."
    return f"""
<article class="agent" id="{html.escape(agent_id)}">
  <div class="agent-heading">
    <div>
      <span class="stage-label">{html.escape(agent_method_label(report.agent_id))}</span>
      <h3>{html.escape(report.agent_id.value.replace("_", " ").title())}</h3>
    </div>
    <span class="recommendation {recommendation_class}">{html.escape(report.recommendation.value.replace("_", " "))}</span>
  </div>
  <span class="label">Estimated risk score: lower is safer</span>
  <div class="score-number">{report.score:.0%}</div>
  {_risk_score_svg(report.score)}
  <div class="chart-title">Key factors behind this score</div>
  {contributions}
  <ul class="reason-list">{reasons}</ul>
  <p class="limitations">{html.escape(limitations)}</p>
</article>
"""


def _risk_score_svg(score: float) -> str:
    marker = 24 + max(0.0, min(score, 1.0)) * 612
    color = (
        "#b42318"
        if score > 0.6
        else "#986500"
        if score > 0.3
        else "#147a43"
    )
    return f"""
<svg class="risk-gauge" viewBox="0 0 660 64" role="img"
  aria-label="Adverse risk score {score:.0%}">
  <rect x="24" y="18" width="184" height="12" fill="#cce8d6"/>
  <rect x="208" y="18" width="184" height="12" fill="#fae6a9"/>
  <rect x="392" y="18" width="244" height="12" fill="#f3c5c1"/>
  <line x1="{marker:.2f}" y1="10" x2="{marker:.2f}" y2="39"
    stroke="{color}" stroke-width="4"/>
  <circle cx="{marker:.2f}" cy="10" r="5" fill="{color}"/>
  <text x="24" y="53" font-size="11" fill="#5c6871">0.0</text>
  <text x="199" y="53" font-size="11" fill="#5c6871">0.3</text>
  <text x="384" y="53" font-size="11" fill="#5c6871">0.6</text>
  <text x="620" y="53" font-size="11" fill="#5c6871">1.0</text>
</svg>
"""


def _contribution_chart(
    contributions: Iterable[FeatureContribution],
    agent_id: str,
    snapshot: CaseSnapshot,
) -> str:
    items = tuple(contributions)
    detail_id = f"{agent_id}-contribution-detail"
    if not items:
        return '<p class="limitations">No local contributions recorded.</p>'
    maximum = max(abs(item.contribution) for item in items) or 1.0
    rows = []
    for item in items:
        direction = contribution_direction(item.contribution)
        css_direction = (
            "increases"
            if item.contribution > 0
            else "protective"
            if item.contribution < 0
            else "neutral"
        )
        width = abs(item.contribution) / maximum * 48
        feature_label = human_label(item.feature)
        formatted_value = format_feature_value(item.feature, item.value)
        evidence = evidence_summary(
            item.evidence_refs,
            snapshot.evidence_refs,
        )
        detail = (
            f"{feature_label}: {formatted_value}. This factor "
            f"{'raises risk' if item.contribution > 0 else 'lowers risk' if item.contribution < 0 else 'has little effect'}. "
            f"{contribution_explanation(item.reason_code, item.contribution)} "
            f"{evidence}"
        )
        rows.append(
            f'<button class="contribution-row" '
            f'data-direction="{html.escape(direction)}" '
            f'data-detail-target="{html.escape(detail_id)}" '
            f'data-detail="{html.escape(detail, quote=True)}">'
            f'<span class="feature-name">{html.escape(feature_label)}</span>'
            f'<span class="feature-impact">'
            f'{"Raises risk" if item.contribution > 0 else "Lowers risk" if item.contribution < 0 else "Neutral"}'
            f"</span>"
            f'<span class="shap-track"><span class="shap-bar {css_direction}" '
            f'style="--bar-size:{width:.2f}%"></span></span></button>'
        )
    first = items[0]
    first_label = human_label(first.feature)
    first_value = format_feature_value(first.feature, first.value)
    initial_detail = (
        f"{first_label}: {first_value}. This factor "
        f"{'raises risk' if first.contribution > 0 else 'lowers risk' if first.contribution < 0 else 'has little effect'}. "
        f"{contribution_explanation(first.reason_code, first.contribution)} "
        f"{evidence_summary(first.evidence_refs, snapshot.evidence_refs)}"
    )
    return (
        f'<div class="shap-chart">{"".join(rows)}</div>'
        f'<div class="contribution-detail" id="{html.escape(detail_id)}" '
        f'aria-live="polite">{html.escape(initial_detail)}</div>'
    )


def _render_policy_detail(result: WorkflowResult) -> str:
    rules = "".join(
        f"<li>{html.escape(policy_explanation(rule.rule_id, rule.description))}</li>"
        for rule in result.decision.policy_rules
    )
    review = "required" if result.review_task else "not required"
    return f"""
<div class="policy-detail">
  <strong>Deterministic policy result</strong>
  <p>{html.escape(result.decision.action.value.replace("_", " ").title())};
  finalized: {str(result.decision.finalized).lower()}; human review: {review}.</p>
  <ul class="rule-list">{rules}</ul>
</div>
"""


def _narrative_for_case(
    smoke: LocalLLMSmokeReport | None,
    case_id: str,
) -> str:
    if smoke is None:
        return (
            '<div class="narrative fallback"><strong>Local Manager '
            "assistant fallback</strong><p>No GGUF smoke report was found. "
            "The deterministic Manager summary remains active.</p></div>"
        )
    probe = next(
        (
            item
            for item in smoke.probes
            if item.purpose is LocalLLMProbePurpose.NARRATIVE
            and item.case_id == case_id
        ),
        None,
    )
    if probe is None or not probe.success or probe.narrative is None:
        reason = probe.fallback_reason if probe else "probe not found"
        latency = (
            f" after {probe.latency_ms:.0f} ms"
            if probe and probe.latency_ms is not None
            else ""
        )
        return (
            '<div class="narrative fallback"><strong>Local Manager '
            f"assistant fallback</strong><p>{html.escape(reason or 'schema validation failed')}"
            f"{html.escape(latency)}. Deterministic consolidation was used.</p></div>"
        )
    narrative = probe.narrative
    latency = (
        f"{narrative.assistant_latency_ms:.0f} ms"
        if narrative.assistant_latency_ms is not None
        else "not recorded"
    )
    return f"""
<div class="narrative">
  <strong>Experimental local Manager narrative</strong>
  <p>{html.escape(narrative.summary)}</p>
  <p>{html.escape(narrative.disagreement_explanation)}</p>
  <p class="meta">{html.escape(narrative.assistant_model or smoke.model_name)}
  | {latency} | no decision authority</p>
</div>
"""


def _render_benchmark(benchmark: dict[str, object] | None) -> str:
    if benchmark is None:
        return (
            '<section class="reference-section"><h2>External benchmark</h2>'
            "<p>Benchmark report unavailable.</p></section>"
        )
    dataset = benchmark.get("dataset", {})
    evaluation = benchmark.get("evaluation", {})
    models = evaluation.get("models", {}) if isinstance(evaluation, dict) else {}
    xgboost = models.get("xgboost", {}) if isinstance(models, dict) else {}
    metrics = (
        ("ROC-AUC", xgboost.get("roc_auc_mean")),
        ("PR-AUC", xgboost.get("pr_auc_mean")),
        ("Brier score", xgboost.get("brier_score_mean")),
        (
            "Calibration error",
            xgboost.get("expected_calibration_error_mean"),
        ),
    )
    metric_rows = "".join(
        f"<tr><th>{html.escape(label)}</th><td>{_format_metric(value)}</td></tr>"
        for label, value in metrics
    )
    limitations = benchmark.get("limitations", [])
    limitation_items = "".join(
        f"<li>{html.escape(str(item))}</li>" for item in limitations
    )
    dataset_name = (
        dataset.get("name", "South German Credit")
        if isinstance(dataset, dict)
        else "South German Credit"
    )
    top_shap = benchmark.get("xgboost_top_shap", [])
    return f"""
<section class="reference-section">
  <h2>External benchmark context</h2>
  <div class="reference-grid">
    <div>
      <p><strong>{html.escape(str(dataset_name))}</strong> is aggregate
      evaluation context only. It never produces a SpendPilot applicant score.</p>
      <table class="metrics"><tbody>{metric_rows}</tbody></table>
      <ul class="limitations">{limitation_items}</ul>
    </div>
    <div>
      <h3>Most influential benchmark factors</h3>
      {_global_importance_chart(top_shap if isinstance(top_shap, list) else [])}
    </div>
  </div>
</section>
"""


def _global_importance_chart(items: list[object]) -> str:
    parsed = [
        item
        for item in items
        if isinstance(item, dict)
        and isinstance(item.get("mean_absolute_contribution"), (int, float))
    ][:10]
    if not parsed:
        return '<p class="limitations">Global SHAP data unavailable.</p>'
    maximum = max(float(item["mean_absolute_contribution"]) for item in parsed)
    rows = []
    for item in parsed:
        value = float(item["mean_absolute_contribution"])
        width = value / maximum * 100 if maximum else 0
        rows.append(
            '<div class="importance-row">'
            f'<span>{html.escape(human_label(str(item.get("feature", "unknown"))))}</span>'
            f'<span class="importance-track"><span class="importance-bar" '
            f'style="display:block;width:{width:.2f}%"></span></span>'
            f"<strong>{value:.3f}</strong></div>"
        )
    return f'<div class="importance-chart">{"".join(rows)}</div>'


def _render_supported_inputs() -> str:
    return """
<section class="reference-section">
  <h2>Inputs accepted from outside the demo</h2>
  <p>The current external interface accepts a validated JSON file. The same
  adapter can later sit behind an API, form, database import, or event stream
  without changing the specialist agents.</p>
  <div class="reference-grid">
    <div>
      <h3>Applicant and loan information</h3>
      <ul>
        <li>Requested amount, product type, and three-letter currency.</li>
        <li>Monthly income, regular monthly expenses, and outstanding debt.</li>
        <li>Credit usage, recent late payments, overdrafts, and employment history.</li>
        <li>Whether income has been verified.</li>
      </ul>
    </div>
    <div>
      <h3>Documents and verified extraction signals</h3>
      <ul>
        <li>Document identifiers for identity, bank statement, and proof of income.</li>
        <li>Optional conservative numeric hints extracted from documents.</li>
        <li>Document coverage and consistency indicators.</li>
        <li>Names are optional; names and raw document text are removed before scoring.</li>
      </ul>
    </div>
  </div>
  <p class="meta">Use <code>evaluate-input --input cases.json</code> for JSON
  results, or <code>explainability-report --input cases.json</code> for this
  interactive report.</p>
</section>
"""


def _render_local_model(smoke: LocalLLMSmokeReport | None) -> str:
    if smoke is None:
        return """
<section class="reference-section">
  <h2>Experimental local Manager assistant</h2>
  <p>No local GGUF smoke report was found. Deterministic behavior was used.</p>
</section>
"""
    probe_rows = "".join(
        f"<tr><td>{html.escape(probe.purpose.value)}</td>"
        f"<td>{html.escape(probe.case_id or 'n/a')}</td>"
        f"<td>{str(probe.success).lower()}</td>"
        f"<td>{_format_metric(probe.latency_ms, digits=0)} ms</td>"
        f"<td>{html.escape(probe.fallback_reason or '')}</td></tr>"
        for probe in smoke.probes
    )
    routing = next(
        (
            probe.routing_proposal
            for probe in smoke.probes
            if probe.purpose is LocalLLMProbePurpose.FEEDBACK_ROUTING
            and probe.success
            and probe.routing_proposal is not None
        ),
        None,
    )
    routing_summary = (
        ", ".join(target.value for target in routing.proposed_targets)
        if routing is not None
        else "deterministic fallback"
    )
    return f"""
<section class="reference-section">
  <h2>Experimental local Manager assistant</h2>
  <div class="reference-grid">
    <div>
      <p><strong>{html.escape(smoke.model_name)}</strong> |
      {html.escape(smoke.model_file)}</p>
      <p class="meta">Model SHA-256: {html.escape(smoke.artifact_hash)}<br>
      Path SHA-256: {html.escape(smoke.model_path_hash)}<br>
      {html.escape(smoke.llama_cpp_version)}</p>
      <p><span class="label">Schema-valid response rate</span>
      <strong>{smoke.success_rate:.0%}</strong></p>
      <p><span class="label">Non-authoritative routing proposal</span>
      {html.escape(routing_summary)}</p>
      <p class="limitations">{html.escape(smoke.recommendation)}</p>
    </div>
    <table class="metrics">
      <thead><tr><th>Probe</th><th>Case</th><th>Valid</th><th>Latency</th><th>Fallback</th></tr></thead>
      <tbody>{probe_rows}</tbody>
    </table>
  </div>
</section>
"""


def _format_input_value(value: object, unit: str | None) -> str:
    if unit == "percent" and isinstance(value, (int, float)):
        return f"{float(value) * 100:.0f}%"
    if unit == "months" and isinstance(value, (int, float)):
        return f"{int(value)} months"
    if unit and isinstance(value, (int, float)):
        return f"{unit} {_format_number(value)}"
    return str(value)


def _format_number(value: object) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):,.0f}"
    try:
        return f"{float(value):,.0f}"
    except (TypeError, ValueError):
        return str(value)


def _format_metric(value: object, digits: int = 3) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.{digits}f}"
    return "n/a"


def _case_display_name(case_id: str) -> str:
    if case_id.startswith("demo_case_"):
        return f"Case {case_id.removeprefix('demo_case_')}"
    return case_id.replace("_", " ").strip().title()


def _load_json_if_present(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text())
    return payload if isinstance(payload, dict) else None


def _load_smoke_if_present(path: Path) -> LocalLLMSmokeReport | None:
    if not path.exists():
        return None
    return load_local_llm_smoke(path)
