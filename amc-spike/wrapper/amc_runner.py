"""Thin wrappers around the `auto-multiple-choice <action> ...` CLI.

Flag names below were grounded by reading AMC 1.6.0's actual Perl sources
inside the Debian package (GetProjectOptions blocks in each AMC-<action>.pl),
not guessed. `prepare` was additionally validated end-to-end against a real
LaTeX source. `analyse`/`association-auto`/`note`/`export`/`annotate` use the
same grounded flags but have not yet been exercised against a real scanned
copy in this spike -- expect to iterate on them once real/simulated scans are
available (see README "Known limitations").
"""

import subprocess
from pathlib import Path


def _run(action: str, args: list[str], timeout: int = 900) -> tuple[int, str]:
    cmd = ["auto-multiple-choice", action, *args]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired as exc:
        return 1, f"Command timed out after {timeout}s: {exc}"
    log = f"$ {' '.join(cmd)}\n{proc.stdout}\n{proc.stderr}"
    return proc.returncode, log


def prepare(pdir: Path, n_copies: int) -> tuple[int, str]:
    """Build the subject/solution/catalog PDFs and the scoring database
    (mode "sb"; "b" builds the marks scale -- without it `note`/`annotate`
    silently run on an empty scoring DB), then import the box-position
    layout into layout.sqlite via the `meptex` action (without this, `analyse`
    later fails with "No layout"). Both gaps were found while validating this
    spike against AMC's actual CLI behaviour.
    """
    out_dir = pdir / "out"
    data_dir = pdir / "data"
    calage = data_dir / "calage.xy"
    args = [
        "--mode", "sb",
        "--source", str(pdir / "source.tex"),
        "--data", str(data_dir),
        "--out-sujet", str(out_dir / "sujet.pdf"),
        "--out-corrige", str(out_dir / "corrige.pdf"),
        "--out-catalog", str(out_dir / "catalog.pdf"),
        "--out-calage", str(calage),
        "--n-copies", str(n_copies),
        "--prefix", str(out_dir) + "/",
    ]
    code, log = _run("prepare", args)
    if code != 0:
        return code, log
    mep_code, mep_log = _run(
        "meptex", ["--src", str(calage), "--data", str(data_dir)]
    )
    return mep_code, log + "\n" + mep_log


def analyse(pdir: Path) -> tuple[int, str]:
    scans = sorted(str(p) for p in (pdir / "scans").iterdir() if p.is_file())
    if not scans:
        return 1, "No scan files uploaded in scans/."
    args = ["--data", str(pdir / "data"), "--cr", str(pdir / "cr"), *scans]
    return _run("analyse", args)


def associate(pdir: Path) -> tuple[int, str]:
    """Auto-association requires a question acting as the student's code
    (--notes-id), e.g. a digit-box \\AMCcode question. Our minimal test
    source has no such question, so this will report an error unless the
    exam defines one -- see README "Known limitations".
    """
    students_csv = pdir / "students.csv"
    if not students_csv.exists():
        return 1, "No students.csv uploaded; upload one to run association-auto."
    args = [
        "--data", str(pdir / "data"),
        "--liste", str(students_csv),
        "--liste-key", "id",
        "--notes-id", "code",
    ]
    return _run("association-auto", args)


def note(pdir: Path) -> tuple[int, str]:
    args = ["--data", str(pdir / "data"), "--seuil", "0.5"]
    return _run("note", args)


def export_csv(pdir: Path) -> tuple[int, str]:
    out_csv = pdir / "out" / "results.csv"
    args = [
        "--data", str(pdir / "data"),
        "--module", "CSV",
        "--output", str(out_csv),
    ]
    students_csv = pdir / "students.csv"
    if students_csv.exists():
        args += ["--fich-noms", str(students_csv)]
    return _run("export", args)


def annotate(pdir: Path) -> tuple[int, str]:
    pdf_dir = pdir / "cr" / "corrections" / "pdf"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    args = [
        "--cr", str(pdir / "cr"),
        "--data", str(pdir / "data"),
        "--subject", str(pdir / "out" / "sujet.pdf"),
        "--pdf-dir", str(pdf_dir),
    ]
    return _run("annotate", args)
