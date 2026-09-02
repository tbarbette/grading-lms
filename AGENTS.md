# AGENTS.md

Working notes for coding agents on this project. `TOOLING.md` is the human-facing decision document — read it for *why*. This file is the *what was verified*, so nothing here has to be re-derived.

Facts below were established by running the code, not by reading documentation, unless marked **unverified**.

## Project

Build a self-hosted, Gradescope-like system for paper exams whose questions are mostly **open** (~10 of ~16 on a real LINFO2241 paper): generate variants from a question bank, print machine-locatable answer zones, scan, crop each answer, and put an LLM suggestion in front of a human marker attached to a rubric.

Non-negotiables: self-hosted (student scripts are personal data); the LLM reads crops the system produced itself, never a manual upload; open questions and drawings are first-class.

**Current direction:** evaluate **Plom** before writing more capture code. It is the only self-hostable tool that already produces per-question images from scans. Do not start the AMC fork.

## Layout

```
lms/
├── TOOLING.md          state of the art, comparison, verdicts (humans)
├── AGENTS.md           this file
└── amc-spike/          working AMC + FastAPI prototype, kept as reference
    ├── Dockerfile, docker-compose.yml
    ├── test-data/
    └── wrapper/        main.py, amc_runner.py, zones.py, llm_provider.py, rubric.py
```

Related, outside this repo:

- `../rex/Rex` — patched fork of the Rex Shiny app (see below). Not upstream.
- `../rex/exercises-linfo2241/` — **118 LINFO2241 exercises** converted to R/exams Rmd: 51 choice (32 `schoice`, 19 `mchoice`) + 67 `string`, spanning exams 2023-01 through 2026-08. Any new question-bank schema should be mechanically convertible from these.

## Verified: R/exams and the `nops` format

Against `exams` 2.4.4. These are the walls that killed the Rex route.

**Max three open questions per exam.** `exams2nops`:

```r
if (sum(nchoice < 1L) > 3L)
    stop("currently only up to three exercises that are not schoice/mchoice are supported")
```

Not arbitrary in the sense of being easy to lift — it is a hardcoded A4 layout replicated in three places:

1. `exams:::make_nops_string_page` draws the open-answer sheet as a LaTeX `picture` with `switch(n, '1'=…, '2'=…, '3'=…)`. There is no fourth branch: at `n=4` the switch returns `NULL` and the page renders with **zero answer boxes** (confirmed by calling it directly). Box heights are 183 / 89 / 57 mm for n = 1 / 2 / 3.
2. Same function: the grader's point strip has exactly three bubble rows at `y = 237, 230, 223`, gated by `if (n > 1L)` / `if (n > 2L)`.
3. `nops_scan` reads it back with `read_nops_answers(ss, …, n = 3L, adjust = TRUE)` then `substr(…, 1, 17)` — three groups of five bubbles plus two spaces.

The five bubbles per row are quarter-credit steps: `nops_eval(string_points = seq(0, 1, 0.25))`.

**No crop is ever produced.** The open-answer sheet is scanned only for those point bubbles. Handwriting is never extracted or stored. Nothing to give an LLM.

**Open answers cannot be auto-graded.** `nops_eval` requires a `string_scans` ZIP containing `Daten2.txt` with hand-assigned points, else `'string_scans' need to be provided for open-ended exercises`. Rex never passes it (`worker.R:1137` `param_nops_eval`), so evaluating any exam with a `string` exercise fails.

**Other `exams2nops` constraints**, for anyone generating nops-compatible input:

- `cloze` rejected outright; choice exercises must have 2–5 alternatives.
- `seed` must be an `n × (pool size)` matrix — `mm <- length(file_raw)` in `xexams`, *not* the exam length.
- `nsamp` must be a **vector** with one entry per block. A scalar is recycled by `xexams` but `exams2nops` computes `nexrc <- sum(nsamp)` before recycling, so the answer sheet ends up with fewer rows than the exam has questions.
- With `file` as a list of blocks, every exercise within a block must have the same alternative count. With a flat vector, no such check.

## Verified: patches applied to `../rex/Rex`

Local fork only, not upstream. Useful if the MCQ half is ever reused; otherwise historical.

- `worker.R:357` — parser accepts `extype: string`; the `E1006`/`E1007` choice checks are scoped to `schoice`/`mchoice` (a string exercise has no answerlist, so `E1006` fired next once `E1005` was widened).
- `worker.R:554-599` — exam building rewritten: mixed types allowed (`E1019` deleted — it rejected *any* type variation, including `schoice` + `mchoice`); blocks refined by answer count with open text sorted last; `nsamp` computed as a proper per-block vector via a new `distributeExercises()` helper; the ≤3 open-question cap now counts *drawn* questions, not selected ones.
- New codes: `E1037` (>3 open text), `E1039` (fewer exam exercises than blocks), `E1040` (asked for more exercises than selected), `W1009` (blocks were split). `E1019`, `E1033`, `E1038` are now dead rows in `errorCodes.csv`.
- `www/script.js` — `getTypeText` renders `string` as "Open Text" (was printing `undefined`); the type toggle is guarded so clicking an open-text exercise cannot silently rewrite it to `schoice`; `setLanguage` whitelists `de`/`en` so the server's `f_langDeEn(1)` re-apply signal stops poisoning the language cookie and resetting the UI to German on every error modal.
- `app.html` + `script.js` — "All examinable" is now "Invert examinable" (`examExerciseInvert`), inverting per exercise instead of a global all-on/all-off toggle.

Docker notes for that repo: `rocker/shiny:4.2.2` is amd64-only so the `rex` service needs `platform: linux/amd64`; the worker must **not** be pinned (`texlive-full` fails under qemu — `fmtutil` crashes LuaTeX during `tex-common` post-install). `dockerfile_worker` needs `libssl-dev` and `libcurl4-openssl-dev` or `openssl`/`curl`/`magick`/`qpdf` fail to compile on arm64 — and `install.packages` only *warns*, so the failure surfaces much later as a crash loop.

## Verified: AMC

The pipeline works end to end in Docker. Order matters, and two steps are not obvious:

```
prepare --mode sb      # NOT --mode s: 's' does not build the scoring database
meptex --src calage.xy --data …   # mandatory, or analyse fails with "ERR: Scan : No layout"
analyse scan1.png scan2.png
note
export --module CSV
annotate
```

**Crops already exist.** After `analyse`, `data/capture.sqlite` holds `capture_zone` with `student`, `page`, `type`, `id_a`, `id_b`, `imagedata`. For `ZONE_BOX` (`type=4`), `imagedata` is a dewarped, aligned PNG of that box. `wrapper/zones.py` reads them directly (`get_combined_image(...)`) — no manual upload anywhere in the grading page.

**The blocker.** AMC does not capture `questionouverte`. The LaTeX package prints the frame, but no zone is registered in the layout, so no crop exists.

**The ROI bug.** Using a wide MCQ box as a text zone crashes `AMC-detect`:

```
cv::Exception (-215:Assertion failed) 0 <= roi.x && … roi.x + roi.width <= m.cols
```

Bisected by box width: 3 cm ✓, 3.5 cm ✓, 4 cm ✗, 4.5 cm ✗, 6 cm ✗; 3 cm × 8 cm ✓. **Width-dependent, not area or aspect ratio.** Cause is in the zoom-saving step, which builds `cv::Mat roi = illustr(cv::Rect(...))` from transformed corners plus a margin; for some widths the rectangle leaves the image. No matching public bug report found.

Current stopgap in the spike — three narrow `choiceshoriz` boxes recombined with Pillow (~651×277 px) — **works but is explicitly rejected**; do not build on it.

Source was cloned to `/tmp/amc-src` (gone now). Files that matter if the fork is ever revived: `AMC-detect.cc` (`mesure_case()`, `restreint()`), `AMC-perl/AMC/DataModule/capture.pm` (zone type constants, `capture_zone` schema), `tex/automultiplechoice.dtx.in`, `tex/Makefile`.

## Verified: Plom

Python + Qt, AGPL-3.0, `github.com/plomgrading/plom` (mirror; development is on GitLab). In production at UBC Mathematics since 2018, ~20 courses, up to 1000+ students with multiple markers.

- Takes **supplied PDFs**, one per version, all versions structurally identical. Does *not* generate from source; LaTeX is optional (`mockplom.sty` only previews margin adequacy).
- Stamps every page with QR codes; needs margin space reserved for them.
- One page belongs to exactly one question; a question may span contiguous pages.
- Markers are assigned *one question and one version*, and see only those responses across many students. They annotate the image and score with deltas (+1, −2 …) attached to reusable standard comments.
- Markers never see student name or ID.
- **Unverified:** whether rubric edits apply retroactively, any plugin/API surface for injecting an LLM suggestion, grade-export details, OMR (believed absent — all marking is human).

## The capture algorithm, if we build it

Only needed if Plom fails evaluation. The point: **we own generation, so we know every answer zone in millimetres before printing.** Capture is then not a computer-vision research problem.

1. Print four fiducial corner marks and a QR carrying `(exam_id, copy_id, page)`. The QR removes page identification entirely.
2. After scanning, locate the four marks and compute a homography; warp the page to nominal geometry.
3. Crop each zone by its known mm rectangle, **clamped** to `0 ≤ x`, `0 ≤ y`, `x + w ≤ cols`, `y + h ≤ rows` — this is exactly the clamp `AMC-detect` is missing.
4. Store the crop keyed by student / page / question.

MCQ marks come from a fill-ratio test over the known bubble rectangles on the same warped image — which is all `nops_scan` and `AMC-detect` do underneath their complications. This removes every limit at once: no three-question cap, no box-width crash, and no distinction between an MCQ box and a drawing area.

Stack decided earlier: FastAPI (native WebSockets), React/TypeScript, question bank as Git-versioned YAML plus a DB for index and usage history, Tectonic for LaTeX, LLM abstraction over local Ollama and OpenAI-compatible endpoints.

**Where the effort actually goes** — none of these are solved by the capture step:

- Robust dewarping of phone photos and skewed scanner output. Fiducials plus a homography handle a lot; heavy perspective and page curl do not.
- The grading UI. Gradescope's speed comes from the group-then-rubric loop and keyboard shortcuts, not from AI. Copy it carefully, or inherit it from Plom.
- LLM reliability on handwriting. Prior art: *Grading Handwritten Engineering Exams with Multimodal Large Language Models* (arXiv 2601.00730). Only its metadata was retrieved here — read it before fixing prompts and confidence thresholds.

**Human-in-the-loop contract:** an LLM output is a *proposal attached to a rubric item*, always displayed next to the crop, never a silently applied mark.

## Environment gotchas

- **Never pipe a build command whose exit code matters.** `docker compose up --build | tail -40` returns `tail`'s status; a failed build reads as success. Capture `REAL_EXIT=$?` before any pipe.
- The Rex containers run with `cap_drop: ALL` and `no-new-privileges`, so even `docker exec -u 0` cannot delete root-owned files that `docker cp` left in the shared `/tmp` volume. Use a throwaway privileged container: `docker run --rm -v rex_shared-content:/v alpine rm -rf /v/<file>`.
- `/tmp` is a **shared volume** between the Rex web and worker containers — test artefacts written there are visible to the app. Clean up.
- Apple Silicon: prefer native arm64 images; only pin `linux/amd64` where no arm64 manifest exists.

## Conventions

- Verify claims against source or a run before writing them down; mark anything unverified as such, here and in `TOOLING.md`.
- Keep `TOOLING.md` prose and decision-oriented. Reproducible detail — schemas, exact call sites, command sequences, bisection results — belongs here.
- `amc-spike/` is reference material now. Do not extend it without a decision to revive the AMC route.
