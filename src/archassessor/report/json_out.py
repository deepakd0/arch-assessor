"""JSON report renderer (spec 005 §3).

Canonical assessment JSON, optionally with a caller-supplied generated_at
timestamp. Absent by default so equal assessments stay byte-identical.
"""

from __future__ import annotations

import json

from archassessor.engine.evaluate import Assessment, assessment_to_json


def render_json(assessment: Assessment, *, generated_at: str | None = None) -> str:
    text = assessment_to_json(assessment)
    if generated_at is None:
        return text
    payload = json.loads(text)
    payload["generated_at"] = generated_at
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
