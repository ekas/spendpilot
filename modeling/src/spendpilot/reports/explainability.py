"""Self-contained HTML visualization of governed decision explanations."""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from spendpilot.assistants.smoke import load_local_llm_smoke
from spendpilot.demo import run_sample_cases
from spendpilot.schemas.agent_report import FeatureContribution
from spendpilot.schemas.modeling import (
    LocalLLMProbePurpose,
    LocalLLMSmokeReport,
)
from spendpilot.orchestration.workflow import WorkflowResult


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
) -> Path:
    """Run deterministic cases and render one portable HTML artifact."""

    results = run_sample_cases(
        model_root,
        benchmark_report_path=benchmark_report_path,
    )
    benchmark = _load_json_if_present(Path(benchmark_report_path))
    smoke = _load_smoke_if_present(Path(smoke_report_path))
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        _render_report(
            results=results,
            benchmark=benchmark,
            smoke=smoke,
        )
    )
    return output


def _render_report(
    *,
    results: tuple[WorkflowResult, ...],
    benchmark: dict[str, object] | None,
    smoke: LocalLLMSmokeReport | None,
) -> str:
    generated = datetime.now(timezone.utc).isoformat()
    finalized = sum(result.decision.finalized for result in results)
    review_count = sum(result.review_task is not None for result in results)
    case_sections = "\n".join(
        _render_case(result, smoke) for result in results
    )
    benchmark_section = _render_benchmark(benchmark)
    local_section = _render_local_model(smoke)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SpendPilot Explainability Report</title>
<style>
:root {{
  color-scheme: light;
  --ink: #182026;
  --muted: #59636b;
  --line: #cbd2d8;
  --surface: #f6f8f9;
  --risk: #b42318;
  --safe: #147a43;
  --accent: #2458a6;
  --warning: #9a6700;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  background: #ffffff;
  color: var(--ink);
  font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}}
header, main, footer {{ width: min(1180px, calc(100% - 32px)); margin: auto; }}
header {{ padding: 34px 0 24px; border-bottom: 2px solid var(--ink); }}
h1 {{ margin: 0 0 8px; font-size: 30px; letter-spacing: 0; }}
h2 {{ margin: 0 0 16px; font-size: 22px; letter-spacing: 0; }}
h3 {{ margin: 0 0 10px; font-size: 17px; letter-spacing: 0; }}
p {{ margin: 6px 0; }}
.meta {{ color: var(--muted); }}
.warning {{
  margin: 22px 0;
  padding: 14px 16px;
  border-left: 4px solid var(--warning);
  background: #fff8e6;
}}
.summary {{
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  border-bottom: 1px solid var(--line);
}}
.summary div {{ padding: 18px 12px; border-right: 1px solid var(--line); }}
.summary div:last-child {{ border-right: 0; }}
.summary strong {{ display: block; font-size: 24px; }}
section {{ padding: 28px 0; border-bottom: 1px solid var(--line); }}
.decision {{
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 6px;
  margin-bottom: 18px;
}}
.decision div {{ padding: 12px; }}
.label {{ display: block; color: var(--muted); font-size: 12px; }}
.agents {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }}
.agent {{ border: 1px solid var(--line); border-radius: 6px; padding: 14px; overflow: hidden; }}
.agent table, .metrics {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
th, td {{
  text-align: left;
  padding: 7px 6px;
  border-bottom: 1px solid var(--line);
  overflow-wrap: anywhere;
}}
th {{ color: var(--muted); font-weight: 600; }}
.chart {{ width: 100%; height: auto; display: block; margin-top: 8px; }}
.narrative {{ margin-top: 18px; padding: 14px; border-left: 4px solid var(--accent); background: #eef4fc; }}
.fallback {{ border-left-color: var(--warning); background: #fff8e6; }}
.risk-text {{ color: var(--risk); }}
.safe-text {{ color: var(--safe); }}
.limitations {{ color: var(--muted); }}
footer {{ padding: 24px 0 40px; color: var(--muted); }}
@media (max-width: 860px) {{
  .summary, .agents, .decision {{ grid-template-columns: 1fr; }}
  .summary div, .decision div {{ border-right: 0; border-bottom: 1px solid var(--line); }}
}}
</style>
</head>
<body>
<header>
  <h1>SpendPilot Explainability Report</h1>
  <p>Deterministic policy decisions with evidence-linked model contributions.</p>
  <p class="meta">Generated {html.escape(generated)}</p>
</header>
<main>
  <div class="warning">
    Development demonstration only. The active tabular agents use synthetic
    labels, and the South German Credit benchmark does not match the SpendPilot
    applicant population. Nothing in this report is approved for real lending.
  </div>
  <div class="summary">
    <div><strong>{len(results)}</strong>offline cases</div>
    <div><strong>{finalized}</strong>automatically finalized</div>
    <div><strong>{review_count}</strong>human-review tasks</div>
  </div>
  {case_sections}
  {benchmark_section}
  {local_section}
</main>
<footer>
  Scores use adverse-risk orientation: 0 is lower risk and 1 is higher risk.
  Positive TreeSHAP contributions increase adverse risk; negative contributions
  are protective.
</footer>
</body>
</html>
"""


def _render_case(
    result: WorkflowResult,
    smoke: LocalLLMSmokeReport | None,
) -> str:
    case_id = html.escape(result.analysis_round.case_id)
    agent_sections = "\n".join(
        _render_agent(report) for report in result.reports
    )
    review = "required" if result.review_task else "not required"
    narrative = _narrative_for_case(smoke, result.analysis_round.case_id)
    return f"""
<section>
  <h2>{case_id}</h2>
  <div class="decision">
    <div><span class="label">Manager action</span>{html.escape(result.manager_report.proposed_action.value)}</div>
    <div><span class="label">Specialist disagreement</span>{str(result.manager_report.disagreement).lower()}</div>
    <div><span class="label">Policy action</span>{html.escape(result.decision.action.value)}</div>
    <div><span class="label">Finalized</span>{str(result.decision.finalized).lower()}</div>
    <div><span class="label">Human review</span>{review}</div>
  </div>
  <div class="agents">{agent_sections}</div>
  {narrative}
</section>
"""


def _render_agent(report) -> str:
    score = report.score
    reason_rows = "".join(
        f"<tr><td>{html.escape(contribution.feature)}</td>"
        f"<td>{html.escape(str(contribution.value))}</td>"
        f"<td>{html.escape(contribution.reason_code)}</td>"
        f"<td>{html.escape(', '.join(contribution.evidence_refs) or 'none')}</td></tr>"
        for contribution in report.top_contributors
    )
    limitations = "; ".join(report.limitations) or "None recorded."
    return f"""
<article class="agent">
  <h3>{html.escape(report.agent_id.value.replace('_', ' ').title())}</h3>
  <p><strong>{score:.3f}</strong> adverse risk | {html.escape(report.recommendation.value)}</p>
  {_risk_score_svg(score)}
  {_contribution_svg(report.top_contributors)}
  <table>
    <thead><tr><th>Feature</th><th>Value</th><th>Reason</th><th>Evidence</th></tr></thead>
    <tbody>{reason_rows}</tbody>
  </table>
  <p class="limitations">{html.escape(limitations)}</p>
</article>
"""


def _risk_score_svg(score: float) -> str:
    width = max(0.0, min(score, 1.0)) * 620
    color = "#b42318" if score > 0.6 else "#9a6700" if score > 0.3 else "#147a43"
    return f"""
<svg class="chart" viewBox="0 0 660 42" role="img" aria-label="Adverse risk score {score:.3f}">
  <rect x="20" y="12" width="620" height="14" fill="#e7ebee"/>
  <rect x="20" y="12" width="{width:.2f}" height="14" fill="{color}"/>
  <line x1="206" y1="7" x2="206" y2="31" stroke="#59636b"/>
  <line x1="392" y1="7" x2="392" y2="31" stroke="#59636b"/>
</svg>
"""


def _contribution_svg(
    contributions: Iterable[FeatureContribution],
) -> str:
    items = tuple(contributions)
    if not items:
        return "<p class=\"limitations\">No local contributions recorded.</p>"
    maximum = max(abs(item.contribution) for item in items) or 1.0
    rows = []
    for index, item in enumerate(items):
        y = 24 + index * 42
        width = abs(item.contribution) / maximum * 155
        positive = item.contribution > 0
        x = 480 if positive else 480 - width
        color = "#b42318" if positive else "#147a43"
        direction = contribution_direction(item.contribution)
        rows.append(
            f'<text x="8" y="{y + 4}" font-size="13" fill="#182026">'
            f"{html.escape(item.feature)}</text>"
            f'<text x="228" y="{y + 4}" font-size="12" fill="#59636b">'
            f"{item.contribution:+.3f}</text>"
            f'<rect data-direction="{html.escape(direction)}" '
            f'x="{x:.2f}" y="{y - 11}" width="{width:.2f}" height="16" '
            f'fill="{color}"/>'
        )
    height = 38 + len(items) * 42
    return f"""
<svg class="chart" viewBox="0 0 660 {height}" role="img" aria-label="TreeSHAP feature contributions">
  <line x1="480" y1="4" x2="480" y2="{height - 8}" stroke="#59636b"/>
  {''.join(rows)}
</svg>
"""


def _narrative_for_case(
    smoke: LocalLLMSmokeReport | None,
    case_id: str,
) -> str:
    if smoke is None:
        return (
            '<div class="narrative fallback"><strong>Local narrative:</strong> '
            "not evaluated. Deterministic Manager summary remains active.</div>"
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
        return (
            '<div class="narrative fallback"><strong>Local narrative fallback:</strong> '
            f"{html.escape(reason or 'schema validation failed')}</div>"
        )
    narrative = probe.narrative
    latency = (
        f"{narrative.assistant_latency_ms:.0f} ms"
        if narrative.assistant_latency_ms is not None
        else "not recorded"
    )
    return f"""
<div class="narrative">
  <strong>Experimental local narrative</strong>
  <p>{html.escape(narrative.summary)}</p>
  <p>{html.escape(narrative.disagreement_explanation)}</p>
  <p class="meta">{html.escape(narrative.assistant_model or smoke.model_name)} | {latency}</p>
</div>
"""


def _render_benchmark(benchmark: dict[str, object] | None) -> str:
    if benchmark is None:
        return "<section><h2>External benchmark</h2><p>Benchmark report unavailable.</p></section>"
    dataset = benchmark.get("dataset", {})
    evaluation = benchmark.get("evaluation", {})
    models = evaluation.get("models", {}) if isinstance(evaluation, dict) else {}
    xgboost = models.get("xgboost", {}) if isinstance(models, dict) else {}
    top_shap = benchmark.get("xgboost_top_shap", [])
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
        f"<li>{html.escape(str(item))}</li>"
        for item in limitations
    )
    dataset_name = (
        dataset.get("name", "South German Credit")
        if isinstance(dataset, dict)
        else "South German Credit"
    )
    return f"""
<section>
  <h2>External benchmark context</h2>
  <p>{html.escape(str(dataset_name))} is evaluation context only and never produces a SpendPilot applicant score.</p>
  <table class="metrics"><tbody>{metric_rows}</tbody></table>
  {_global_shap_svg(top_shap if isinstance(top_shap, list) else [])}
  <ul class="limitations">{limitation_items}</ul>
</section>
"""


def _global_shap_svg(items: list[object]) -> str:
    parsed = [
        item for item in items
        if isinstance(item, dict)
        and isinstance(item.get("mean_absolute_contribution"), (int, float))
    ][:10]
    if not parsed:
        return "<p class=\"limitations\">Global SHAP data unavailable.</p>"
    maximum = max(float(item["mean_absolute_contribution"]) for item in parsed)
    rows = []
    for index, item in enumerate(parsed):
        y = 24 + index * 34
        value = float(item["mean_absolute_contribution"])
        width = value / maximum * 360 if maximum else 0
        feature = str(item.get("feature", "unknown"))
        rows.append(
            f'<text x="8" y="{y + 3}" font-size="12" fill="#182026">'
            f"{html.escape(feature)}</text>"
            f'<rect x="290" y="{y - 10}" width="{width:.2f}" height="14" '
            'fill="#2458a6"/>'
            f'<text x="660" y="{y + 3}" text-anchor="end" '
            f'font-size="12" fill="#59636b">{value:.3f}</text>'
        )
    height = 34 + len(parsed) * 34
    return f"""
<h3>Benchmark global SHAP importance</h3>
<svg class="chart" viewBox="0 0 680 {height}" role="img" aria-label="Global benchmark SHAP importance">
  {''.join(rows)}
</svg>
"""


def _render_local_model(smoke: LocalLLMSmokeReport | None) -> str:
    if smoke is None:
        return """
<section>
  <h2>Experimental local Manager assistant</h2>
  <p>No local GGUF smoke report was found. Deterministic Manager behavior was used.</p>
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
<section>
  <h2>Experimental local Manager assistant</h2>
  <p><strong>{html.escape(smoke.model_name)}</strong> | {html.escape(smoke.model_file)}</p>
  <p class="meta">Model SHA-256: {html.escape(smoke.artifact_hash)}<br>
  Path SHA-256: {html.escape(smoke.model_path_hash)}</p>
  <p class="meta">{html.escape(smoke.llama_cpp_version)} | success rate {smoke.success_rate:.0%}</p>
  <p><span class="label">Non-authoritative routing proposal</span>{html.escape(routing_summary)}</p>
  <table class="metrics">
    <thead><tr><th>Probe</th><th>Case</th><th>Valid</th><th>Latency</th><th>Fallback</th></tr></thead>
    <tbody>{probe_rows}</tbody>
  </table>
  <p class="limitations">{html.escape(smoke.recommendation)}</p>
</section>
"""


def _format_metric(value: object, digits: int = 3) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.{digits}f}"
    return "n/a"


def _load_json_if_present(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text())
    return payload if isinstance(payload, dict) else None


def _load_smoke_if_present(path: Path) -> LocalLLMSmokeReport | None:
    if not path.exists():
        return None
    return load_local_llm_smoke(path)
