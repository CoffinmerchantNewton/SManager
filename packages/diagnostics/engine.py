from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SEVERITY_RANK = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
RULES_PATH = Path(__file__).with_name("recovery_actions.json")


def analyze_diagnosis(diagnosis: dict[str, Any], run_id: str | None = None) -> dict[str, Any]:
    """Turn raw flowctl findings into deterministic recovery guidance."""
    rules = load_rules()
    resolved_run_id = run_id or diagnosis.get("run_id") or "<run_id>"
    findings = diagnosis.get("findings") if isinstance(diagnosis, dict) else []
    if not isinstance(findings, list):
        findings = []

    recommendations = [recommendation_for_finding(item, rules, resolved_run_id) for item in findings]
    auto_allowed = bool(recommendations) and all(item["auto_allowed"] for item in recommendations)
    requires_operator = any(not item["auto_allowed"] for item in recommendations)
    highest = highest_severity(recommendations)
    next_action = choose_next_action(recommendations)

    return {
        "version": rules.get("version", 1),
        "run_id": resolved_run_id,
        "summary": {
            "finding_count": len(recommendations),
            "risk_level": highest,
            "auto_retry_allowed": auto_allowed,
            "requires_operator": requires_operator,
            "recommended_next_action": next_action,
        },
        "recommendations": recommendations,
    }


def recommendation_for_finding(finding: Any, rules: dict[str, Any], run_id: str) -> dict[str, Any]:
    item = finding if isinstance(finding, dict) else {}
    code = str(item.get("code") or "unknown")
    rule = match_rule(code, rules)
    node = item.get("node")
    recommendation = {
        "finding_code": code,
        "node": node,
        "severity": rule["severity"],
        "category": rule["category"],
        "action": rule["action"],
        "auto_allowed": bool(rule["auto_allowed"]),
        "reason": rule["reason"],
        "cli": format_cli(rule.get("cli_template"), run_id, node),
    }
    retry_after = rule.get("retry_after_action")
    if retry_after:
        recommendation["retry_after_action"] = retry_after
    return recommendation


def load_rules() -> dict[str, Any]:
    return json.loads(RULES_PATH.read_text(encoding="utf-8"))


def match_rule(code: str, rules: dict[str, Any]) -> dict[str, Any]:
    for rule in rules.get("rules", []):
        if code in rule.get("codes", []):
            return rule
    return rules["default_rule"]


def format_cli(template: str | None, run_id: str, node: Any) -> str | None:
    if not template:
        return None
    return template.format(run_id=run_id, node=node or "")


def highest_severity(recommendations: list[dict[str, Any]]) -> str:
    if not recommendations:
        return "info"
    return max(recommendations, key=lambda item: SEVERITY_RANK.get(item["severity"], 0))["severity"]


def choose_next_action(recommendations: list[dict[str, Any]]) -> str | None:
    if not recommendations:
        return None
    first = sorted(
        recommendations,
        key=lambda item: (-SEVERITY_RANK.get(item["severity"], 0), not item["auto_allowed"], item["action"]),
    )[0]
    return first["action"]
