# Paper exams with open questions: what exists, and what we have to build

## The goal

Build a web tool, in the spirit of Gradescope, that covers the whole life of a paper exam:

**Generation**

- keep a versioned question bank and assemble exams from it;
- produce several variants of the same exam from seeds, so neighbours do not get the same paper;
- support typed sub-questions: `mcq_single`, `mcq_multi`, `numeric`, `short_text`, `freeform`;
- render through LaTeX;
- print answer zones that are *identifiable and machine-locatable after scanning* — this is the crux;
- print a per-copy identifier (QR or code), or grade anonymously and associate later.

**Grading**

- import batches of scanned copies;
- auto-grade MCQ and simple numeric/textual answers;
- send the cropped image of an open answer to an LLM (local Ollama or an OpenAI-compatible endpoint) for a reading and a suggested mark;
- build and edit rubrics while grading, and have edits apply retroactively;
- export grades.

**Constraints that rule things in and out**

- Open questions and drawings are not a nice-to-have. Roughly ten of the ~16 questions on a real LINFO2241 paper are open. A tool that handles three is not a tool for this course.
- The LLM must sit inside the real grading pipeline, reading crops the system produced itself — not behind a manual image upload.
- Self-hostable, because student answer sheets are personal data.
- Modifiable, because every candidate below stops somewhere and the last mile is ours.

## Feature comparison

Columns are the candidate solutions — the ones that handle open questions on paper. Rows are grouped into exam generation and exam grading. Tools that only do MCQ, or only do the authoring half, are surveyed further down without a column.

**Legend** — ✅ yes · 🟡 partial, see notes · ❌ no · ❔ not verified · — not applicable

| Feature | Rex + nops | R/exams (lib) | AMC | Plom | ScanExam | Ans | Gradescope | Crowdmark |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **EXAM GENERATION** | | | | | | | | |
| Generates the exam at all | ✅ | ✅ | ✅ | 🟡 stamps | ❌ | ✅ | ❌ | 🟡 booklets |
| Web UI for authoring | ✅ | ❌ | 🟡 GUI | ❌ | — | ✅ | — | ❌ |
| Reusable question bank | 🟡 flat list | 🟡 files | 🟡 files | ❌ | — | ✅ | — | ❌ |
| Authoring format | Rmd / Rnw | Rmd / Rnw | LaTeX | your PDF | — | web editor | — | your PDF |
| LaTeX / math typesetting | ✅ | ✅ | ✅ | ✅ yours | — | 🟡 | — | ✅ |
| N variants from one source (seeds) | ✅ | ✅ | ✅ | 🟡 versions | — | 🟡 | — | ❌ |
| Random draw from a larger pool | ✅ | ✅ | ✅ | ❌ | — | ❔ | — | ❌ |
| Shuffled answer order | ✅ | ✅ | ✅ | ❌ | — | ❔ | — | ❌ |
| Typed sub-questions | 🟡 3 types | 🟡 5 types | 🟡 | ❌ | — | ✅ | — | ❌ |
| Open questions printed on the paper | ✅ | ✅ | ✅ | ✅ | — | ✅ | — | ✅ |
| Max open questions per paper | **3** | **3** (nops) | ∞ | ∞ | — | ∞ | — | ∞ |
| Machine-locatable zone for open answers | 🟡 fixed sheet | 🟡 fixed sheet | ❌ | ✅ per page | — | ✅ | — | ✅ |
| Dedicated drawing / figure space | 🟡 | 🟡 | 🟡 | ✅ | — | ✅ | — | ✅ |
| Per-copy identifier printed on the page | ✅ | ✅ | ✅ | ✅ QR | — | ✅ | — | ✅ |
| Scriptable / CI-able generation | 🟡 | ✅ | ✅ | ✅ | — | ❌ | — | ❌ |
| **EXAM GRADING** | | | | | | | | |
| Batch scan import | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Automatic copy ↔ student matching | ✅ | ❌ | ✅ | ✅ QR | ❔ | ✅ | ✅ | ✅ |
| MCQ auto-grading (OMR) | ✅ | ❌ | ✅ | ❌ | ❔ | ✅ | ✅ | 🟡 |
| **Per-question crop from the scan** | ❌ | ❌ | 🟡 boxes only | ✅ | ❔ | ✅ | ✅ | ✅ |
| Grade-by-question across all copies | ❌ | ❌ | 🟡 | ✅ | ✅ | ✅ | ✅ | ✅ |
| Rubrics editable mid-grading | ❌ | ❌ | 🟡 scoring rules | ✅ deltas | ✅ | ✅ | ✅ | ✅ |
| Rubric edits apply retroactively | ❌ | ❌ | ✅ re-run | ❔ | ❔ | ❔ | ✅ | ✅ |
| Multiple markers / teaching team | ❌ | ❌ | 🟡 | ✅ | ❔ | ✅ | ✅ | ✅ |
| Anonymous marking | ❌ | ❌ | ❌ | ✅ by design | ❔ | ✅ | 🟡 | 🟡 |
| Grouping of identical/similar answers | ❌ | ❌ | ❌ | ❌ | ❌ | ❔ | ✅ AI | ❔ |
| LLM-assisted grading of open answers | ❌ | ❌ | ❌ | ❌ | ❌ | ❔ | 🟡 closed | ❔ |
| Handwriting recognition | ❌ | ❌ | ❌ | ❌ | ❔ | ❔ | ✅ EN + math | ❔ |
| Annotated copies returned to students | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| CSV / grade export | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Item statistics / analysis | ✅ | ❌ | ✅ | 🟡 | ❌ | ✅ | ✅ | ✅ |
| **PRACTICAL** | | | | | | | | |
| Self-hosted, data stays local | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Licence / cost | GPL-3 | GPL | GPL | AGPL-3 | EPL-2.0 | paid SaaS | paid SaaS | paid SaaS |
| Can we change it | ✅ | ✅ | 🟡 C++/Perl | ✅ Python | ✅ Java | ❌ | ❌ | ❌ |

The row that decides everything is **per-question crop from the scan**. Every open-question workflow — manual, rubric-based, or LLM — needs the system to hand you a rectangle of pixels that it knows belongs to student *s*, question *q*. Exactly one self-hostable tool has it today: **Plom**. That single cell is the difference between "extend an existing system" and "write the capture layer ourselves", and it is why Plom deserves an evaluation before any more code is written.

---

## Plom

The find of this survey, and the closest thing to the goal that exists as free software. Python + Qt, AGPL-3.0, developed at UBC Mathematics and in production there since October 2018 across ~20 courses, including 1000+ student multi-section calculus with multiple markers.

**What it does.** You supply the blank exam as PDFs — one per version, all versions structurally identical. Plom stamps every page with QR codes carrying the paper, page and version, so after scanning it knows exactly which student and which question every image belongs to. Markers then work *one question, one version, across many students*: the client shows only the pages for the question they are assigned, they annotate the image directly, and they score with "deltas" (+1, −2 …) attached to reusable standard comments — which is a rubric in all but name. Markers never see student names or IDs; anonymity is a design property, not a setting. Annotated papers are returned, marks export.

**What it does not do.** No question bank, no seeds, no random draw from a pool, no answer shuffling — "versions" means *you* wrote three structurally-parallel papers. No OMR, so MCQ is marked by a human like everything else. And no LLM anywhere.

**Why it matters here.** Plom already solves the two problems that stopped both Rex and AMC: it locates answer regions on a scanned page reliably, and it has a marking loop that works at scale. The gap between Plom and this project's goal is *additive* — a generation front-end that emits Plom-compatible PDFs from a YAML bank, and an LLM suggestion attached to the rubric — rather than a fork of anything load-bearing.

**Verdict.** Evaluate this first, with a real LINFO2241 paper, before writing more capture code. Two things to check: whether the AGPL is acceptable for a UCLouvain deployment, and whether the marker client can be extended with an LLM suggestion panel or whether that has to live in a separate web layer over the Plom server.

## Rex + R/exams `nops`

A Shiny web front-end over R/exams. This is what the previous sessions went into, and where "that led to nothing" comes from.

**What works.** Authoring and importing exercises in Rmd/Rnw, a question list with points/sections/tags, *n* seeded variants with random draw from a pool, a scannable answer sheet, MCQ grading, statistics, CSV export. Self-hosted, GPL-3. Several real bugs were fixed along the way — details in `AGENTS.md`.

**Where it stops.** Three walls, all verified in the `exams` 2.4.4 source rather than guessed:

1. **Three open questions maximum**, because the open-answer sheet is a hand-drawn LaTeX `picture` page with layouts for exactly one, two or three answer boxes, and a scanner hard-coded to read three rows of point bubbles.
2. **No crop is ever produced.** That sheet is scanned only to read the *grader's* point bubbles. The handwriting is never extracted, stored or addressable. There is nothing to hand an LLM.
3. **Grading open answers needs a manual side-channel** — a ZIP of hand-assigned points that Rex never supplies, so evaluating any exam containing an open question fails outright.

**Verdict.** Good for the MCQ half of a paper. Structurally incapable of the open-question half. Not the base for this project.

## R/exams as a library

Dropping Rex and calling R/exams directly buys one thing: `exams2pdf` instead of `exams2nops`. That prints an exam with any mix of question types and no limit on open questions — because it prints no answer sheet at all, and therefore supports no scanning or grading whatsoever.

So R/exams gives *either* unlimited open questions with zero automation, *or* automation capped at three. It cannot give both. Useful as a rendering and question-bank engine; not a grading platform.

## Auto Multiple Choice (AMC)

The spike in `amc-spike/` proved AMC's pipeline works end to end in Docker, and its real asset is that it already stores **dewarped, aligned crops** in `capture.sqlite`, addressable by student and page. The wrapper reads them directly, so the LLM grading page needs no manual upload. That is the right architecture.

**Where it stops.** AMC does not capture `questionouverte`. The LaTeX package prints an open-answer frame, but no zone is registered in the layout, so no crop exists after analysis. The workaround — abusing a wide MCQ box as a text zone — crashes `AMC-detect` above roughly 3.5 cm of box width, a genuine out-of-bounds ROI bug in the C++ with no matching public report. The three-narrow-boxes stopgap works and was rightly rejected as a keeper.

A clean fix is well-scoped — a new `ZONE_OPEN` type through the LaTeX package, the layout database and the detector, plus an ROI clamp — but it means owning a C++/Perl/LaTeX fork, rebuilt and re-validated on every upstream release, to obtain a feature ("give me the pixels in this rectangle") that is a few dozen lines of OpenCV when you control the page geometry yourself. Full technical detail, including the bisection results and the schema, is in `AGENTS.md`.

**Verdict.** Was the front-runner; Plom displaces it. Keep the spike as a working reference for how a capture → crop → LLM → rubric loop feels, but do not start the fork.

## Ans

Commercial, and the closest match to the goal among the paid options — worth knowing because it is becoming the default at nearby universities. Ans covers both halves: a question bank with tags and learning objectives, papers authored in a web editor and printed, then scanned back in and graded online, anonymously, combining automatic scoring for closed questions with coordinated grading of open ones and consistency checks across a marking team.

Adopted institution-wide at Leiden from 2024-25, and in use at TU Delft and Erasmus Rotterdam.

**Verdict.** If this project fails or stalls, this is the thing to buy. It is also the strongest argument for asking UCLouvain what it already licenses before building anything. Ruled out as a base: SaaS, closed, no LLM control, and student scripts leave the institution.

## ScanExam

Open-source (EPL-2.0), Java/Maven. Grading only: fast navigation between scanned copies and a customisable, dynamic grading rubric. No generation side. The README states plainly that it is still in development and may have numerous bugs, and QR matching, MCQ auto-grading and export could not be confirmed from the repository page — hence the ❔ marks.

**Verdict.** Superseded by Plom, which does the same job with a decade of production use behind it.

## Gradescope

The benchmark. It does not generate exams — you upload the blank paper as a template PDF. From there: batch scan import, roster matching, bubble-sheet auto-grading, and for handwritten short answers an AI-assisted grouping step that clusters similar responses so you grade a *group* once. It compares each submission against the blank template by overlay and extracts the differences — the same "known geometry ⇒ crop" trick we need. Its AI reads English handwriting and mathematical notation. Rubrics are dynamic and edits apply retroactively.

**Where it stops for us.** SaaS, paid, and student scripts leave the institution — the reason this project exists. The AI is closed: no local model, no prompt control, no rubric-aware reasoning of our own.

**Verdict.** The feature target to copy, not a solution to adopt. Any UI we build should be judged against how fast Gradescope's group-and-rubric loop is.

## Crowdmark

Same commercial category, and it *does* produce the printed artefact: personalised, QR-tagged booklets generated from your PDF, which makes matching reliable and gives it real answer-zone knowledge. Per-question grading, rubrics, annotation and return, exports. But it generates booklets from a PDF you supply, not exams from a question bank — no items, no seeds, no variants. Same SaaS and data-residency objections.

**Verdict.** Ruled out with Gradescope, with less to copy.

## Build our own

The stack from the earlier design pass: FastAPI backend (native WebSockets, unlike Flask), React/TypeScript front-end, question bank as Git-versioned YAML with a database for the index and usage history, Tectonic for LaTeX, and an LLM abstraction over local Ollama and OpenAI-compatible endpoints.

**The architectural point.** The AMC fork was only necessary because the spike adopted AMC's *capture* pipeline. But we own generation anyway — that is a hard requirement, for the bank and the variants — and once we emit the page ourselves we know every answer zone's position in millimetres before it is printed. Capture then reduces to: print four fiducials and a QR carrying `(exam_id, copy_id, page)`; locate the marks; homography; crop the known rectangles, clamped to the image bounds; store keyed by student/page/question. A few hundred lines of Python and OpenCV, and it removes every limit in the table at once — no three-question cap, no box-width crash, and no distinction between an MCQ box and a drawing area, because a drawing is just a bigger rectangle. MCQ marks then come from a fill-ratio test over the known bubble rectangles, which is all `nops_scan` and `AMC-detect` are doing underneath their complications. The algorithm is written out in `AGENTS.md`.

**What is genuinely hard, and where the effort belongs:**

- Robust dewarping of phone photos and skewed scanner output. Fiducials plus a homography handle a lot; heavy perspective and page curl do not.
- The grading UI. Gradescope's speed comes from the group-then-rubric loop and keyboard shortcuts, not from AI. This is the part to copy carefully — or to inherit from Plom.
- LLM reliability on handwriting. Prior art exists: *Grading Handwritten Engineering Exams with Multimodal Large Language Models* (arXiv 2601.00730). Only its metadata was retrieved here, so read it before fixing prompts and confidence thresholds.
- The human-in-the-loop contract. An LLM suggestion must be a *proposal attached to a rubric item*, always visible next to the crop, never a silently applied mark.

**Verdict, revised.** This was the plan before Plom surfaced. Plom already owns the expensive, unglamorous half — QR page identification, per-question images, multi-marker rubrics, anonymity — and it is Python, which the rest of the stack already is. The honest sequence is now:

1. run a real LINFO2241 paper through Plom end to end;
2. if it holds, build only the two missing pieces on top: a YAML question bank that emits Plom-compatible versioned PDFs, and an LLM suggestion layer feeding the rubric;
3. build the capture layer from scratch only if step 1 fails, in which case the fiducial + homography design above stands, and AMC still is not worth forking.

---

## Also surveyed

**Authoring / item banking only** — these solve the generation half and nothing else:

- **GradeMaker Pro** — a serious authoring and item-banking system for print and online exams, used by City & Guilds, AQA and various examination councils. Whole-paper authoring or compilation from items, QC workflow, publishes to print and digital. No scanning, no grading of scripts. Cloud-hosted. *(Worth noting: searching for "FileMaker Pro" in this space returns this product — if GradeMaker was the intended name, this is the entry.)*
- **FileMaker Pro** (Claris) — a low-code database and RAD platform, not an exam product; no evidence of it being used as a paper-exam grading solution. Its only plausible role here would be as the *build platform* instead of FastAPI + React, and it is a poor fit: the hard parts of this project are OpenCV image processing, LaTeX generation and LLM calls, none of which FileMaker is good at, on top of per-seat licensing and a weak Linux/server story. Not recommended.

**Grading only, AI-first, commercial** — the new wave, all SaaS, all closed models:

- **Edufide** — grades scanned exams, handwritten work and MCQ in one flow, with reusable comments, rubrics and AI-assisted marking that explicitly keeps staff in control. LMS integrations (Canvas, Brightspace, Moodle, Blackboard, Sakai). Closest commercial analogue to what we want to build, minus generation and self-hosting.
- **Examino, GradeWithAI, Gradelab** — same category, rubric-based AI first passes over handwritten and PDF submissions. Useful as UX references for how an LLM suggestion is presented to a marker; not adoptable.

**Institutional digital-exam platforms** — **Inspera**, **WISEflow**. Large European assessment suites aimed at on-screen exams; paper is at best a side path. Relevant only as "what the university may already have a licence for", which is worth checking before building.

**Computer-based systems with a paper export** — **TCExam** (open source, PHP; can export paper tests and read them back with OMR) and **PrairieLearn** (open source, questions as code with generators — a genuinely good model for the question bank, worth reading for schema ideas even though it is online-first).

**MCQ-only** — cannot address the ten open questions on a LINFO2241 paper:

- **Moodle Offline Quiz** — free plugin, printed MCQ sheets scanned back into Moodle. Only if the whole course lives in Moodle.
- **Remark Office OMR / Remark Test Grading** — the long-standing commercial OMR product; robust, bubbles only.
- **ZipGrade, Akindi, ScanToGrade, Paper Exam Grader, Papeez** — Scantron replacements, bubbles only.
- **OMRChecker, FormScanner, OpenScanVision** — open-source OMR libraries. Useful as *components* for a second opinion on bubble reading; not exam systems.

**Adjacent, different problem** — **nbgrader** (Jupyter notebooks), **MarkUs** (code assignments). Neither touches paper, but both are worth a look for rubric data models.

## Open questions to settle next

1. **Does Plom hold for a LINFO2241 paper?** This is now the first experiment, and it makes questions 2–4 cheaper to answer.
2. Anonymous grading with later association, or per-student QR from the start? Not exclusive — the QR can encode an opaque copy id resolved only at export. Plom has already made this choice, in the direction we would probably choose.
3. Do we want variants at all if grading is per-question across copies? Variants complicate grouping badly: two students with different numbers cannot be grouped. Possibly variants for MCQ only, fixed text for open questions. Plom's "structurally identical versions" model is a middle path.
4. Which LLM, and on university hardware or a hosted endpoint? This decides what "self-hosted" is actually worth.
5. Is there a migration path for the ~118 LINFO2241 exercises already converted to R/exams Rmd in `../rex/exercises-linfo2241/`? The YAML schema should make a mechanical conversion possible.
6. What does UCLouvain already license — Ans, Inspera, WISEflow, Gradescope? Cheapest possible outcome of this whole project.

## References

- [Plom — Paperless Open Marking](https://plomgrading.org/) · [creating a test](https://plomgrading.org/docs/walkthrough/create.html) · [marking](https://plomgrading.org/docs/clientUse/marking.html) · [source](https://github.com/plomgrading/plom)
- [Ans — paper and digital exams](https://www.ans.app/paper-exams) · [Leiden University adoption](https://www.staff.universiteitleiden.nl/vr/science/science-teacher-platform/practical-organisation-of-education/ans)
- [Gradescope: AI-assisted grading and answer groups](https://guides.gradescope.com/hc/en-us/articles/24838908062093-AI-assisted-grading-and-answer-groups) · [product page](https://www.turnitin.com/products/gradescope/)
- [GradeMaker Pro](https://www.grademaker.com/) · [Edufide](https://edufide.com/)
- [ScanExam on GitHub](https://github.com/ScanExam/ScanExam)
- [Grading Handwritten Engineering Exams with Multimodal LLMs (arXiv 2601.00730)](https://arxiv.org/pdf/2601.00730)
- [Scantron alternatives compared: Remark, Gradescope, ZipGrade, AMC](https://www.scantograde.com/blog/scantron-alternatives-remark-gradescope-akindi-zipgrade-amc/)
- [FormScanner: Open-Source Solution for Grading Multiple-Choice Exams](https://eric.ed.gov/?id=EJ1085712)
- R/exams limits verified directly in `exams` 2.4.4 — see `AGENTS.md` for the exact call sites.
