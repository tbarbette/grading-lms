"""Project storage: filesystem layout and metadata for AMC spike projects.

Each project lives under PROJECTS_DIR/<uuid4 hex>/ with a fixed sub-layout so
amc_runner.py can pass stable paths to the AMC CLI:

  <project>/
    meta.json        # {"id", "name", "created_at", "n_copies"}
    source.tex       # AMC LaTeX source (edited via the web UI)
    students.csv      # optional student list for association-auto
    data/             # AMC's own sqlite DBs (layout/report/capture/scoring...)
    out/              # sujet.pdf, corrige.pdf, catalog.pdf, results.csv
    cr/               # AMC "compte-rendu" working dir (analyse/note/annotate)
    scans/            # uploaded scanned answer sheets
    rubric.json       # our own Gradescope-style rubric overlay (see rubric.py)
"""

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from config import PROJECTS_DIR

_SUBDIRS = ("data", "out", "cr", "scans")


def project_dir(project_id: str) -> Path:
    return PROJECTS_DIR / project_id


def list_projects() -> list[dict]:
    if not PROJECTS_DIR.exists():
        return []
    projects = []
    for child in sorted(PROJECTS_DIR.iterdir()):
        meta_file = child / "meta.json"
        if meta_file.exists():
            projects.append(json.loads(meta_file.read_text()))
    return sorted(projects, key=lambda m: m.get("created_at", ""), reverse=True)


def load_meta(project_id: str) -> dict:
    return json.loads((project_dir(project_id) / "meta.json").read_text())


def save_meta(project_id: str, meta: dict) -> None:
    (project_dir(project_id) / "meta.json").write_text(json.dumps(meta, indent=2))


def create_project(name: str) -> str:
    project_id = uuid.uuid4().hex
    pdir = project_dir(project_id)
    for sub in _SUBDIRS:
        (pdir / sub).mkdir(parents=True, exist_ok=True)
    meta = {
        "id": project_id,
        "name": name.strip() or project_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    save_meta(project_id, meta)
    return project_id


def project_exists(project_id: str) -> bool:
    # project_id is only ever a value we generated (uuid4 hex), but guard
    # against path traversal defensively since it also flows through URLs.
    return bool(re.fullmatch(r"[0-9a-f]{32}", project_id)) and (
        project_dir(project_id) / "meta.json"
    ).exists()


def safe_filename(name: str) -> str:
    """Strip any path components / unsafe characters from an uploaded filename."""
    name = Path(name).name
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    return name or "file"
