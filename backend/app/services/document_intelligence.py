from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path
from uuid import uuid4
from typing import Any

from fastapi import UploadFile

# Hard cap to protect memory for hackathon demo environment.
MAX_READ_BYTES = 2 * 1024 * 1024
UPLOADS_DIR = Path(__file__).resolve().parents[2] / "uploads"


NUMBER_PATTERNS = {
    "monthly_income": [r"monthly[_\s-]*income\D*([0-9]+(?:\.[0-9]+)?)", r"income\D*([0-9]+(?:\.[0-9]+)?)"],
    "monthly_expenses": [r"monthly[_\s-]*expenses\D*([0-9]+(?:\.[0-9]+)?)", r"expenses\D*([0-9]+(?:\.[0-9]+)?)"],
    "existing_debt": [r"existing[_\s-]*debt\D*([0-9]+(?:\.[0-9]+)?)", r"debt\D*([0-9]+(?:\.[0-9]+)?)"],
    "credit_utilization": [r"credit[_\s-]*utilization\D*([0-9]+(?:\.[0-9]+)?)", r"utilization\D*([0-9]+(?:\.[0-9]+)?)"],
    "delinquencies_12m": [r"delinquencies[_\s-]*12m\D*([0-9]+)", r"delinquencies\D*([0-9]+)"],
    "employment_months": [r"employment[_\s-]*months\D*([0-9]+)", r"employment\D*([0-9]+)\s*months"],
    "overdrafts_90d": [r"overdrafts[_\s-]*90d\D*([0-9]+)", r"overdrafts\D*([0-9]+)"],
}


def _safe_decode(raw: bytes) -> str:
    return raw.decode("utf-8", errors="ignore")


def _extract_from_csv(text: str) -> dict[str, float]:
    out: dict[str, float] = {}
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        for key in NUMBER_PATTERNS:
            if key in row and row[key] not in (None, ""):
                try:
                    out[key] = float(row[key])
                except ValueError:
                    continue
        if out:
            break
    return out


def _extract_from_json(text: str) -> dict[str, float]:
    out: dict[str, float] = {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return out

    if isinstance(payload, dict):
        source = payload
    elif isinstance(payload, list) and payload and isinstance(payload[0], dict):
        source = payload[0]
    else:
        return out

    for key in NUMBER_PATTERNS:
        if key in source:
            try:
                out[key] = float(source[key])
            except (TypeError, ValueError):
                continue
    return out


def _extract_with_regex(text: str) -> dict[str, float]:
    out: dict[str, float] = {}
    lowered = text.lower()
    for key, patterns in NUMBER_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, lowered)
            if match:
                try:
                    out[key] = float(match.group(1))
                    break
                except ValueError:
                    continue
    return out


def _normalize_hints(hints: dict[str, float]) -> dict[str, Any]:
    normalized: dict[str, Any] = dict(hints)
    if "credit_utilization" in normalized:
        util = float(normalized["credit_utilization"])
        # Accept either ratio form (0.62) or percentage form (62).
        normalized["credit_utilization"] = util / 100 if util > 1 else util

    for int_key in ("delinquencies_12m", "employment_months", "overdrafts_90d"):
        if int_key in normalized:
            normalized[int_key] = int(round(float(normalized[int_key])))
    return normalized


def _signals_from_text(text: str) -> dict[str, Any]:
    lowered = text.lower()
    income_verified = "income verified" in lowered or "verified income" in lowered
    consistency_flags: list[str] = []

    if "fraud" in lowered or "forg" in lowered:
        consistency_flags.append("POTENTIAL_FRAUD_SIGNAL")
    if "inconsistent" in lowered or "mismatch" in lowered:
        consistency_flags.append("DOCUMENT_DATA_MISMATCH")

    hints = _extract_with_regex(text)
    return {
        "income_verified_from_docs": income_verified,
        "consistency_flags": consistency_flags,
        "numeric_hints": hints,
    }


async def analyze_uploaded_documents(files: list[UploadFile]) -> dict[str, Any]:
    evidence_refs: list[str] = []
    all_text_parts: list[str] = []
    merged_hints: dict[str, float] = {}
    consistency_flags: list[str] = []
    unreadable_files: list[str] = []

    for upload in files:
        evidence_refs.append(upload.filename or "unnamed_document")
        raw = await upload.read(MAX_READ_BYTES)
        await upload.seek(0)
        ext = Path(upload.filename or "").suffix.lower()

        if not raw:
            unreadable_files.append(upload.filename or "unnamed_document")
            continue

        text = _safe_decode(raw)
        if not text.strip() and ext in {".pdf", ".png", ".jpg", ".jpeg"}:
            unreadable_files.append(upload.filename or "unnamed_document")
            continue

        all_text_parts.append(text)

        per_file_hints: dict[str, float] = {}
        if ext == ".json":
            per_file_hints.update(_extract_from_json(text))
        elif ext == ".csv":
            per_file_hints.update(_extract_from_csv(text))

        signal = _signals_from_text(text)
        per_file_hints.update(signal["numeric_hints"])

        for key, value in per_file_hints.items():
            merged_hints[key] = value

        for flag in signal["consistency_flags"]:
            if flag not in consistency_flags:
                consistency_flags.append(flag)

    merged_hints = _normalize_hints(merged_hints)
    joined_text = "\n".join(all_text_parts)
    coverage_score = min(1.0, len(merged_hints) / 7)

    lowered_all = joined_text.lower()
    income_verified_from_docs = "income verified" in lowered_all or "verified income" in lowered_all

    return {
        "evidence_refs": evidence_refs,
        "document_text": joined_text[:12000],
        "document_signals": {
            "numeric_hints": merged_hints,
            "consistency_flags": consistency_flags,
            "coverage_score": round(coverage_score, 2),
            "income_verified_from_docs": income_verified_from_docs,
            "unreadable_files": unreadable_files,
        },
    }


async def persist_uploaded_documents(files: list[UploadFile], case_id: str) -> list[str]:
    case_dir = UPLOADS_DIR / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    stored_paths: list[str] = []

    for upload in files:
        original_name = upload.filename or "unnamed_document"
        safe_name = f"{uuid4().hex[:8]}_{Path(original_name).name}"
        target_path = case_dir / safe_name

        raw = await upload.read(MAX_READ_BYTES)
        await upload.seek(0)
        target_path.write_bytes(raw)
        stored_paths.append(str(target_path))

    return stored_paths
