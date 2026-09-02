from pathlib import Path

import jinja2
from fastapi import FastAPI, Request, UploadFile, Form, File
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

import amc_runner
import rubric
import storage
import varseed
import zones
from llm_provider import DEFAULT_PROMPT, LLMError, get_provider

app = FastAPI(title="AMC evaluation spike")
templates = Jinja2Templates(directory="templates")

_DOWNLOADABLE = {
    "sujet": "out/sujet.pdf",
    "corrige": "out/corrige.pdf",
    "catalog": "out/catalog.pdf",
    "results": "out/results.csv",
}


def _log_path(pdir: Path, action: str) -> Path:
    logs_dir = pdir / "logs"
    logs_dir.mkdir(exist_ok=True)
    return logs_dir / f"{action}.log"


def _write_log(pdir: Path, action: str, code: int, log: str) -> None:
    _log_path(pdir, action).write_text(f"exit={code}\n{log}")


def _read_log(pdir: Path, action: str) -> str | None:
    path = _log_path(pdir, action)
    return path.read_text() if path.exists() else None


def _project_context(pid: str) -> dict:
    pdir = storage.project_dir(pid)
    files_present = {
        key: (pdir / rel).exists() for key, rel in _DOWNLOADABLE.items()
    }
    scans = sorted(p.name for p in (pdir / "scans").iterdir() if p.is_file())
    source_text = (pdir / "source.tex").read_text() if (pdir / "source.tex").exists() else ""
    logs = {
        action: _read_log(pdir, action)
        for action in ("prepare", "analyse", "associate", "note", "export", "annotate")
    }
    return {
        "meta": storage.load_meta(pid),
        "files_present": files_present,
        "scans": scans,
        "source_text": source_text,
        "students_uploaded": (pdir / "students.csv").exists(),
        "logs": logs,
        "rubric": rubric.load(pdir),
    }


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        request, "index.html", {"projects": storage.list_projects()}
    )


@app.post("/projects")
def create_project(name: str = Form(...)):
    pid = storage.create_project(name)
    return RedirectResponse(f"/projects/{pid}", status_code=303)


@app.get("/projects/{pid}", response_class=HTMLResponse)
def show_project(request: Request, pid: str):
    if not storage.project_exists(pid):
        return HTMLResponse("Project not found", status_code=404)
    ctx = {"pid": pid, **_project_context(pid)}
    return templates.TemplateResponse(request, "project.html", ctx)


@app.post("/projects/{pid}/source")
async def upload_source(pid: str, source_text: str = Form(...)):
    pdir = storage.project_dir(pid)
    (pdir / "source.tex").write_text(source_text)
    return RedirectResponse(f"/projects/{pid}", status_code=303)


@app.post("/projects/{pid}/render-variables")
async def render_variables(
    pid: str,
    template_text: str = Form(...),
    variables_text: str = Form(""),
    seed: int = Form(...),
):
    pdir = storage.project_dir(pid)
    variables = varseed.parse_variables_form(variables_text)
    try:
        rendered, values = varseed.render_source(template_text, variables, seed)
    except (varseed.VariableError, jinja2.TemplateError) as exc:
        _write_log(pdir, "prepare", 1, f"Variable rendering failed: {exc}")
        return RedirectResponse(f"/projects/{pid}", status_code=303)
    (pdir / "source.tex").write_text(rendered)
    (pdir / "source.tex.jinja").write_text(template_text)
    (pdir / "variables.txt").write_text(variables_text)
    _write_log(pdir, "prepare", 0, f"Rendered source.tex with seed={seed}, values={values}")
    return RedirectResponse(f"/projects/{pid}", status_code=303)


@app.post("/projects/{pid}/prepare")
async def run_prepare(pid: str, n_copies: int = Form(3)):
    pdir = storage.project_dir(pid)
    code, log = amc_runner.prepare(pdir, n_copies)
    _write_log(pdir, "prepare", code, log)
    return RedirectResponse(f"/projects/{pid}", status_code=303)


@app.get("/projects/{pid}/download/{which}")
def download(pid: str, which: str):
    if which not in _DOWNLOADABLE:
        return HTMLResponse("Unknown file", status_code=404)
    path = storage.project_dir(pid) / _DOWNLOADABLE[which]
    if not path.exists():
        return HTMLResponse("Not generated yet", status_code=404)
    return FileResponse(path)


@app.post("/projects/{pid}/students")
async def upload_students(pid: str, file: UploadFile = File(...)):
    pdir = storage.project_dir(pid)
    (pdir / "students.csv").write_bytes(await file.read())
    return RedirectResponse(f"/projects/{pid}", status_code=303)


@app.post("/projects/{pid}/scans")
async def upload_scans(pid: str, files: list[UploadFile] = File(...)):
    pdir = storage.project_dir(pid)
    scans_dir = pdir / "scans"
    for f in files:
        name = storage.safe_filename(f.filename or "scan")
        (scans_dir / name).write_bytes(await f.read())
    return RedirectResponse(f"/projects/{pid}", status_code=303)


@app.post("/projects/{pid}/analyse")
def run_analyse(pid: str):
    pdir = storage.project_dir(pid)
    code, log = amc_runner.analyse(pdir)
    _write_log(pdir, "analyse", code, log)
    return RedirectResponse(f"/projects/{pid}", status_code=303)


@app.post("/projects/{pid}/associate")
def run_associate(pid: str):
    pdir = storage.project_dir(pid)
    code, log = amc_runner.associate(pdir)
    _write_log(pdir, "associate", code, log)
    return RedirectResponse(f"/projects/{pid}", status_code=303)


@app.post("/projects/{pid}/note")
def run_note(pid: str):
    pdir = storage.project_dir(pid)
    code, log = amc_runner.note(pdir)
    _write_log(pdir, "note", code, log)
    return RedirectResponse(f"/projects/{pid}", status_code=303)


@app.post("/projects/{pid}/export")
def run_export(pid: str):
    pdir = storage.project_dir(pid)
    code, log = amc_runner.export_csv(pdir)
    _write_log(pdir, "export", code, log)
    return RedirectResponse(f"/projects/{pid}", status_code=303)


@app.post("/projects/{pid}/annotate")
def run_annotate(pid: str):
    pdir = storage.project_dir(pid)
    code, log = amc_runner.annotate(pdir)
    _write_log(pdir, "annotate", code, log)
    return RedirectResponse(f"/projects/{pid}", status_code=303)


@app.post("/projects/{pid}/rubric/items")
def add_rubric_item(pid: str, question: str = Form(...), label: str = Form(...), delta: float = Form(...)):
    pdir = storage.project_dir(pid)
    rubric.add_item(pdir, question, label, delta)
    return RedirectResponse(f"/projects/{pid}", status_code=303)


@app.post("/projects/{pid}/rubric/apply")
def apply_rubric_item(
    pid: str,
    student: str = Form(...),
    question: str = Form(...),
    item_id: int = Form(...),
):
    pdir = storage.project_dir(pid)
    rubric.apply_item(pdir, student, question, item_id)
    return RedirectResponse(f"/projects/{pid}", status_code=303)


@app.post("/projects/{pid}/llm-transcribe", response_class=HTMLResponse)
async def llm_transcribe(request: Request, pid: str, image: UploadFile = File(...)):
    pdir = storage.project_dir(pid)
    image_bytes = await image.read()
    provider = get_provider()
    try:
        text = provider.transcribe_image(image_bytes, DEFAULT_PROMPT)
        error = None
    except LLMError as exc:
        text = ""
        error = str(exc)
    ctx = {
        "pid": pid,
        "llm_result": text,
        "llm_error": error,
        **_project_context(pid),
    }
    return templates.TemplateResponse(request, "project.html", ctx)


@app.get("/projects/{pid}/grading", response_class=HTMLResponse)
def grading_page(request: Request, pid: str):
    pdir = storage.project_dir(pid)
    questions = zones.question_names(pdir)
    students = zones.students(pdir)
    cells = []
    for student in students:
        for question in questions:
            has_image = zones.get_combined_image(pdir, student, question) is not None
            if not has_image:
                continue
            cells.append(
                {
                    "student": student,
                    "question": question,
                    "suggestion": rubric.get_llm_suggestion(pdir, str(student), question),
                }
            )
    ctx = {"pid": pid, "meta": storage.load_meta(pid), "cells": cells, "rubric": rubric.load(pdir)}
    return templates.TemplateResponse(request, "grading.html", ctx)


@app.get("/projects/{pid}/zone-image/{student}/{question}")
def zone_image(pid: str, student: int, question: str):
    pdir = storage.project_dir(pid)
    image_bytes = zones.get_combined_image(pdir, student, question)
    if image_bytes is None:
        return HTMLResponse("No captured image for this student/question", status_code=404)
    return Response(content=image_bytes, media_type="image/png")


@app.post("/projects/{pid}/grading/{student}/{question}/transcribe")
def grading_transcribe(pid: str, student: int, question: str):
    pdir = storage.project_dir(pid)
    image_bytes = zones.get_combined_image(pdir, student, question)
    if image_bytes is None:
        return HTMLResponse("No captured image for this student/question", status_code=404)
    provider = get_provider()
    try:
        text = provider.transcribe_image(image_bytes, DEFAULT_PROMPT)
    except LLMError as exc:
        text = f"[LLM error: {exc}]"
    rubric.set_llm_suggestion(pdir, str(student), question, text)
    return RedirectResponse(f"/projects/{pid}/grading", status_code=303)
