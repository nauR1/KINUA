import json
from pathlib import Path

RULESET = json.loads(Path(__file__).with_name("rules.json").read_text(encoding="utf-8"))


class ClinicalRulesEngine:
    version = RULESET["version"]

    def evaluate(self, measurement: dict) -> list[dict]:
        results = []
        for rule in RULESET["rules"]:
            # Fail closed: an undocumented or pending threshold never triggers a clinical association.
            if (
                not rule["enabled"]
                or rule["status"] != "validated"
                or not rule["source"]
                or rule["threshold"] is None
            ):
                continue
            if (
                rule["measurement"] == measurement["key"]
                and measurement["value"] is not None
                and measurement["value"] > rule["threshold"]
            ):
                results.append(rule)
        return results


class AttentionEngine:
    def explain(self, measurement: dict) -> dict:
        d = measurement["details"]
        return {
            "region": d["region"],
            "side": d["side"],
            "severity": "informational",
            "state": "needs_review",
            "confidence": measurement["confidence"],
            "description": f"{measurement['label']}: {measurement['value']:.1f} {measurement['unit']}. Medida objetiva para revisão; sem classificação de normalidade.",
            "explanation": {
                "method": d["method"],
                "landmarks": d["landmarks"],
                "threshold_status": "threshold_pending_validation",
                "frame_index": 0,
                "related_factors": [],
                "suggested_tests": [],
                "reason": "Medida registrada a partir de landmarks visíveis no plano confirmado. Não foi aplicado limiar clínico.",
            },
        }
