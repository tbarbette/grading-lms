"""Read AMC's own automatically-captured answer-zone crops out of its sqlite
DBs, so the LLM-assisted grading step operates on the *real*, already
corner-mark-aligned scan crop AMC produced during `analyse` -- no manual
image upload/crop needed.

Key finding (validated by inspecting capture.sqlite after a real `analyse`
run): every checkbox/box answer zone (ZONE_BOX, type=4 in AMC's own enum)
gets its cropped pixel image stored automatically as a BLOB in
`capture_zone.imagedata`, regardless of whether it ends up ticked. AMC does
NOT do this for `questionouverte` (free-text) zones -- those aren't tracked
at all. So: to get an auto-captured crop for a free-text answer, author the
question as a single/multi-choice `question` (see test-data/source.tex,
question "explain") using `\\AMCboxDimensions{width=...,height=...}` to make
the tickbox(es) themselves a writing area -- AMC then captures/crops it like
any other box, and we read it back here.

Second finding: AMC's C++ OMR detector (AMC-detect, via OpenCV) crashes if a
single box is wider than ~3.5cm (bisected empirically; height is not limited
the same way, 3cm x 8cm works). To still support a "big" answer area, author
it as several side-by-side boxes (`choiceshoriz`, each under the width
limit, same question id) and stitch the crops back into one wide image here.
"""

import io
import sqlite3
from pathlib import Path

from PIL import Image

ZONE_BOX = 4


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def question_id_for_name(pdir: Path, name: str) -> int | None:
    layout_db = pdir / "data" / "layout.sqlite"
    if not layout_db.exists():
        return None
    with _connect(layout_db) as conn:
        row = conn.execute(
            "SELECT question FROM layout_question WHERE name = ?", (name,)
        ).fetchone()
    return row["question"] if row else None


def question_names(pdir: Path) -> list[str]:
    layout_db = pdir / "data" / "layout.sqlite"
    if not layout_db.exists():
        return []
    with _connect(layout_db) as conn:
        rows = conn.execute("SELECT name FROM layout_question ORDER BY question").fetchall()
    return [r["name"] for r in rows]


def students(pdir: Path) -> list[int]:
    capture_db = pdir / "data" / "capture.sqlite"
    if not capture_db.exists():
        return []
    with _connect(capture_db) as conn:
        rows = conn.execute(
            "SELECT DISTINCT student FROM capture_zone WHERE student > 0 ORDER BY student"
        ).fetchall()
    return [r["student"] for r in rows]


def get_box_image(
    pdir: Path, student: int, question_name: str, answer: int = 1
) -> bytes | None:
    """Return the cropped PNG/JPEG bytes AMC captured for one specific answer box."""
    question_id = question_id_for_name(pdir, question_name)
    if question_id is None:
        return None
    capture_db = pdir / "data" / "capture.sqlite"
    if not capture_db.exists():
        return None
    with _connect(capture_db) as conn:
        row = conn.execute(
            """
            SELECT imagedata FROM capture_zone
            WHERE student = ? AND type = ? AND id_a = ? AND id_b = ?
              AND imagedata IS NOT NULL AND length(imagedata) > 0
            """,
            (student, ZONE_BOX, question_id, answer),
        ).fetchone()
    return bytes(row["imagedata"]) if row and row["imagedata"] else None


def get_combined_image(pdir: Path, student: int, question_name: str) -> bytes | None:
    """Return every answer-box crop for this question, stitched side by side
    into one wide PNG -- reconstructs a "big" answer area out of several
    narrow AMC boxes (see module docstring for why boxes must stay narrow).
    """
    question_id = question_id_for_name(pdir, question_name)
    if question_id is None:
        return None
    capture_db = pdir / "data" / "capture.sqlite"
    if not capture_db.exists():
        return None
    with _connect(capture_db) as conn:
        rows = conn.execute(
            """
            SELECT imagedata FROM capture_zone
            WHERE student = ? AND type = ? AND id_a = ?
              AND imagedata IS NOT NULL AND length(imagedata) > 0
            ORDER BY id_b
            """,
            (student, ZONE_BOX, question_id),
        ).fetchall()
    if not rows:
        return None
    images = [Image.open(io.BytesIO(bytes(r["imagedata"]))) for r in rows]
    if len(images) == 1:
        combined = images[0]
    else:
        total_width = sum(img.width for img in images)
        max_height = max(img.height for img in images)
        combined = Image.new("RGB", (total_width, max_height), "white")
        x = 0
        for img in images:
            combined.paste(img, (x, 0))
            x += img.width
    buf = io.BytesIO()
    combined.save(buf, format="PNG")
    return buf.getvalue()
