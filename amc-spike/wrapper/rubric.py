"""Custom Gradescope-style rubric overlay, kept separate from AMC's own scoring.

AMC only auto-scores checkbox (OMR) answers via a static per-question scoring
formula. For open/manual questions we let the grader build a rubric on the
fly (point deltas with a description) and apply items per student answer,
independent of and in addition to AMC's own note/export pipeline.
"""

import json
from pathlib import Path

_DEFAULT = {"items": {}, "grades": {}}


def _rubric_path(pdir: Path) -> Path:
    return pdir / "rubric.json"


def load(pdir: Path) -> dict:
    path = _rubric_path(pdir)
    if not path.exists():
        return json.loads(json.dumps(_DEFAULT))
    return json.loads(path.read_text())


def save(pdir: Path, rubric: dict) -> None:
    _rubric_path(pdir).write_text(json.dumps(rubric, indent=2))


def add_item(pdir: Path, question: str, label: str, delta: float) -> dict:
    rubric = load(pdir)
    items = rubric["items"].setdefault(question, [])
    item = {"id": len(items) + 1, "label": label, "delta": delta}
    items.append(item)
    save(pdir, rubric)
    return item


def apply_item(pdir: Path, student: str, question: str, item_id: int) -> dict:
    rubric = load(pdir)
    key = f"{student}/{question}"
    applied = rubric["grades"].setdefault(key, {"item_ids": []})
    if item_id not in applied["item_ids"]:
        applied["item_ids"].append(item_id)
    save(pdir, rubric)
    return applied


def set_llm_suggestion(pdir: Path, student: str, question: str, text: str) -> None:
    rubric = load(pdir)
    key = f"{student}/{question}"
    entry = rubric["grades"].setdefault(key, {"item_ids": []})
    entry["llm_suggestion"] = text
    save(pdir, rubric)


def get_llm_suggestion(pdir: Path, student: str, question: str) -> str | None:
    rubric = load(pdir)
    return rubric["grades"].get(f"{student}/{question}", {}).get("llm_suggestion")


def grade_total(pdir: Path, student: str, question: str) -> float:
    rubric = load(pdir)
    items = {i["id"]: i for i in rubric["items"].get(question, [])}
    applied = rubric["grades"].get(f"{student}/{question}", {"item_ids": []})
    return sum(items[i]["delta"] for i in applied["item_ids"] if i in items)
