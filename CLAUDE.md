# TCF ORAL PRACTICE TOOL — CLAUDE.md

## Project Identity

This is **Le Méthodic** (lemethodic.com) — a web app where French learners (primarily English-speaking Canadians preparing for TCF Canada, plus a broader pivot to TCF/TEF/DELF/DALF/FIDE/AP/DCL) record oral responses + submit writing to exam-style prompts and receive instant AI-powered feedback using Chadi's proprietary 5-couche methodology (La Méthode en Couches). Dead names: TCF Oral Practice Tool, FluentPath, FluentPrep, Le Raccourci.

**This is NOT a generic language learning app.** The competitive edge is the 4-layer diagnostic framework (La Méthode en Couches) built from 7,000+ hours of tutoring anglophone French learners. No other tool evaluates L1 interference patterns at this depth.

---

## Tech Stack

- **Backend:** Python 3 + FastAPI + SQLAlchemy + Alembic (PostgreSQL local + prod, F-077)
- **Speech-to-Text:** AssemblyAI API
- **AI Analysis:** Anthropic Claude API (claude-sonnet-4-20250514) — processes transcriptions through the 5-layer Méthode en Couches prompt (writing path on the full 5 couches as of V-016a; oral path on 4 couches until V-009.be lifts La Voix)
- **Frontend:** Vanilla HTML/CSS/JS served via FastAPI templates (Jinja2)
- **Auth:** Session-based with hashed passwords
- **File uploads:** Audio recordings stored in `uploads/`

---

## Architecture Overview

```
main.py                  → App entry point, mounts routers
app/
├── models/              → SQLAlchemy models (User, Topic, Recording, Analysis)
├── routers/             → FastAPI route handlers
├── services/
│   ├── analysis.py      → Oral analysis engine (4 couches today; V-009.be lifts to 5)
│   └── writing_analysis.py → Writing analysis engine (5 couches, La Méthode en Couches)
├── templates/           → Jinja2 HTML templates (index.html, admin.html)
└── static/              → CSS, JS, images
alembic/                 → Alembic migrations (F-077)
alembic.ini              → Alembic config
docker-compose.yml       → Local PostgreSQL (F-077)
scripts/                  → Seeders + verification harnesses
scripts/archive/         → Retired one-off SQLite migration scripts (F-077)
archive/                 → Pre-routers async scaffold orphans (F-077)
tests/                   → Test suite
uploads/                 → User audio recordings
requirements.txt         → Python dependencies
```

---

## Local development

The backend runs against PostgreSQL locally (F-077; same engine as prod). One-command setup:

```bash
docker-compose up -d                  # start local PostgreSQL (port 5432)
alembic upgrade head                  # create / migrate schema
python -m scripts.seed_f077_min_fixtures   # one User + one Tache1Opening — required for F-075a/b harnesses on a fresh DB
python -m uvicorn main:app --reload   # backend
```

- `docker-compose down` stops the container; data persists via the `postgres_data` named volume.
- `docker-compose down -v` nukes local data and starts fresh.
- Direct `psql` access: `psql postgresql://fluentpath:fluentpath_local_dev@localhost:5432/fluentpath`
- The local-dev password is intentionally non-secret (it's local only and never shipped). Production uses a managed PostgreSQL with a real secret injected via `DATABASE_URL`.
- Browser cookies from prior SQLite-era sessions reference user IDs that no longer exist — clear cookies for `localhost` after the switch and re-register/login.

### Schema changes
Use Alembic, never `Base.metadata.create_all`:
```bash
alembic revision --autogenerate -m "<short description>"
# review the generated file; keep `default=datetime.datetime.utcnow` Python-side
alembic upgrade head
```

### Production migration protocol (locked 2026-05-12 via F-310 contract refinement)

DO App Platform is configured with `deploy_on_push: true` and a run command of `alembic upgrade head && uvicorn ...` (see `.do/app.yaml`). **Every push to `master` auto-deploys and auto-applies pending migrations.** There is no separate "apply" step that ops can gate on.

This means migration approval must fire **before push**, not before a separate apply step that doesn't exist. The protocol:

1. **Local verification cycle** — apply against local docker postgres + verify `alembic upgrade head` clean → `alembic downgrade -1` clean → `alembic upgrade head` idempotent re-apply clean. Capture user counts, row counts, leftover-artifact counts.

2. **Migration ASK message** (sent to Chadi before the push that contains the migration file) must include:
   - Full migration file content **inline** (not just a reference path).
   - Generated SQL preview via `alembic upgrade <prev_rev>:<new_rev> --sql`.
   - Local verification confirmation (upgrade + downgrade + re-upgrade output).
   - **pg_dump command for Chadi to run against prod** — see pg_dump pre-flight tiering below.
   - Rollback command (`alembic downgrade -1`).

   **pg_dump pre-flight tiering (refined 2026-05-12 via F-320 contract refinement):**
   - **REQUIRED** — pg_dump is the primary point-in-time backup and Chadi must capture + confirm file path + size + row count BEFORE approving the push when ANY of the following apply:
     - Migration includes `ALTER TABLE` on existing tables (column add/drop/type change), OR
     - Migration includes `INSERT` / `UPDATE` / `DELETE` DML on existing data, OR
     - Migration adds a NOT NULL column with backfill, OR
     - Migration touches `users` / auth-related tables / payment-adjacent tables (`refresh_tokens`, `email_verification_tokens`, `password_reset_tokens`, anything Stripe-adjacent).
   - **OPTIONAL** — pg_dump is skipped and the DO daily auto-backup serves as fallback when the migration is **100% additive** (only `CREATE TABLE` / `CREATE INDEX` / `CREATE CONSTRAINT` on NEW objects, zero touch on existing tables). SQL preview must prove zero `ALTER` / `INSERT` / `UPDATE` / `DELETE` on existing data; ASK message states "pg_dump skipped — additive-only" so the tiering decision is auditable.

   Tiering rationale: 100% additive migrations have a clean `alembic downgrade -1` path that loses zero existing data (the new tables ship empty); a pg_dump for additive migrations protects against nothing the rollback can't already restore. Non-additive migrations need pg_dump because rollback alone can't recover dropped/mutated rows.

3. **Chadi pre-push actions:**
   - If pg_dump REQUIRED: run the pg_dump command against prod, confirm backup file path + size + row count.
   - Read the inline migration file + SQL preview.
   - Approve the push.

4. **BE pushes to master** → DO auto-deploys → migration auto-applies. BE confirms post-deploy state via prod probes (`/health`, `/openapi.json`, a representative endpoint that exercises new schema).

If anything fails post-deploy: `alembic downgrade -1` runs by pushing a revert commit (or via DO console if available). For REQUIRED-tier migrations, the pg_dump from step 3 is the emergency restore path; for OPTIONAL-tier migrations, the downgrade is sufficient and the DO daily auto-backup is the secondary fallback.

### Seeder scripts — gate #7 prod-execution required (added 2026-05-13 via F-BUGS-001-BE-A contract refinement)

`scripts/seed_*.py` runners ARE NOT auto-applied to production. The DO App Platform run command is `alembic upgrade head && uvicorn ...` — migrations auto-apply, seeders do not. Local-dev convention is "run the seeder after every fresh `docker-compose up` + `alembic upgrade head`", but that convention does NOT extend to prod deploys. Result of the gap before this amendment: F-049's Tâche 2 scenario seeder lived in master from launch but never ran on prod, so every Tâche 2 conversation-start returned HTTP 404 until 2026-05-13 (F-BUGS-001-BE-A).

**Protocol for every BE ticket that adds OR modifies a `scripts/seed_*.py` runner OR depends on seeded data being live in prod:**

1. **Dispatch plan MUST include an explicit "run the seeder on prod" step** with the exact command (typically `python -m scripts.seed_<name>` via DO console terminal). Treat this step as a discrete deliverable, not an implicit follow-up.
2. **Surface a gate #7 seed ASK to Chadi BEFORE the seeder fires on prod.** Same shape as the migration ASK:
   - Inline seed file content (or diff if updating an existing seeder).
   - SQL preview of the INSERT/UPDATE statements the seeder will issue against prod.
   - Idempotency claim (e.g., "upsert by `code` — re-running is safe; existing rows updated in place").
   - Diagnostic query Chadi runs FIRST to confirm prod state pre-seed (e.g., `SELECT COUNT(*) FROM <table>;`).
   - Rollback SQL (typically `DELETE FROM <table> WHERE <constraint>;` — only safe if no downstream FK rows have been created since the seed).
   - Post-seed verification query Chadi runs to confirm the rows landed correctly.
3. **Chadi runs the seeder on prod via DO console** after approving the ASK. BE does NOT execute prod writes; Chadi does, with seed ASK content as the runbook.
4. **Post-seed verification:** Chadi confirms the seed succeeded via the query from step 2. BE may then run a smoke script (e.g., `scripts/smoke_*.py`) against the FE-facing endpoint that exercises the newly-seeded data to confirm end-to-end flow.

**Tiering parity with pg_dump:** seeder pre-flight backup follows the same REQUIRED-vs-OPTIONAL split as migrations:
- **REQUIRED pg_dump** when the seeder runs against a non-empty table (existing rows could be overwritten by the upsert path), OR touches `users` / auth / payment-adjacent tables, OR the rollback path is non-trivial (FK cascades, computed fields).
- **OPTIONAL pg_dump** when the seeder runs against a known-empty table (pure-insert pattern, no overwrite risk). Bootstrap seeds (first prod execution of a seeder against a 0-row table) typically qualify OPTIONAL.

**Gate triggers that still ASK before commit (not push) per operating contract:**
- Payment/billing/subscription logic changes (gate #10) — shape question before code.
- Stripe webhook secret rotation (gate #6).
- `.env` file edits (gate #5).
- Anything destructive (gate #7) — includes seeder prod execution per the section above.

---

## The Methodology — La Méthode en Couches (5 Couches)

This is the heart of the product. The AI analysis engines (`analysis.py` for oral, `writing_analysis.py` for writing) evaluate production across 5 layers. The writing path emits the full 5-couche surface as of V-016a (2026-05-12); the oral path is scheduled to align in V-009.be.

| Couche | Name | What It Measures |
|--------|------|-----------------|
| 1 | **Le Fond** | Ideas, arguments, examples, relevance to the topic |
| 2 | **Les Moules des Idées** | Discourse organization — does the student structure thought like a French speaker? (context-first vs. point-first, thèse-antithèse-synthèse, etc.) |
| 3 | **Les Moules** | Sentence-level architecture — does each sentence sound French or like translated English? |
| 4 | **Les Réflexes Anglais** | L1 interference — English habits bleeding through: faux-amis, calques, missing *ne*, preposition errors, anglicisms |
| 5 | **La Voix** | Native-French read vs. translated-English read. Register fit, idiomatic patterns, French rhetorical flow, cultural-fit phrasing, voice consistency across paragraphs. Detects whether a native French writer would recognize the text as "thinking in French" vs "translating from English." |

### Feedback Output — Le Diagnostic

The analysis returns:
1. **La Carte** — 5 scores (0-20 per couche) + overall /20 (mean of the 5 couches, rounded to 1 decimal)
2. **Le Goulet** — THE bottleneck. Which couche is dragging everything down?
3. **Les Patterns** — Specific patterns detected and missing per couche
4. **L'Ordonnance** — Prioritized action items (what to fix first)

**IMPORTANT:** Never rename these layers or use academic terminology like "L1 interference" or "discourse patterns" in user-facing text. Use the French methodology names above. This is a branded product.

---

## Topics Database

- **84 topics** seeded across **7 themes** (Vie quotidienne, Société, Éducation, Technologie, Environnement, Culture, Travail)
- Each topic has: `theme`, `sous_theme`, `question`, `target_levels` (B1/B2/C1)
- Topics follow TCF Tâche 3 format (monologue argumenté)

---

## Current State & What's Done

✅ Backend API (FastAPI + SQLAlchemy)
✅ User auth (register, login, sessions)
✅ Audio recording in browser (MediaRecorder API)
✅ Deepgram STT integration
✅ 5-layer Méthode en Couches analysis engine (writing_analysis.py — V-016a 2026-05-12; analysis.py oral still at 4, V-009.be queued)
✅ 84 topics seeded across 7 themes
✅ Basic frontend (index.html) — functional but needs redesign
✅ Admin page (admin.html) — functional but still uses old level-based dropdown

---

## What Needs to Be Done (Priority Order)

### Phase 1 — Frontend Redesign
1. **index.html** — New user flow:
   - Target level selector (B1 / B2 / C1)
   - Theme-based topic browsing (cards or accordion by theme)
   - Recording interface with timer and waveform
   - 4-layer feedback display: La Carte (scores), Le Goulet (bottleneck), Les Patterns, L'Ordonnance
   - Progress history (past recordings with scores)

2. **admin.html** — Update:
   - Remove level dropdown from "Ajouter un sujet"
   - Add theme/sous_theme fields instead
   - Show topics organized by theme with counts
   - Bulk import capability

### Phase 2 — Deployment
- DigitalOcean $12/month droplet
- PostgreSQL (replace SQLite)
- Nginx reverse proxy + SSL (Let's Encrypt)
- Domain TBD (brand name pending)
- Environment: `.env` with SECRET_KEY, DEEPGRAM_API_KEY, ANTHROPIC_API_KEY, DATABASE_URL

### Phase 3 — Monetization & Polish
- Stripe subscription integration (freemium: 3 free recordings/month, then paid)
- Progress charts over time (per-couche score evolution)
- PDF export of Le Diagnostic
- Password reset flow
- Mobile-responsive design
- Social sharing of progress

### Phase 4 — Scale
- Mobile app (React Native or Flutter)
- Influencer/tutor affiliate program
- Additional exam types (TEF, DELF)
- Italian-speaking learner support

---

## Code Conventions

- Python: type hints, docstrings on public functions
- HTML templates: Jinja2 syntax, inline CSS/JS is fine for now (single-file templates)
- API responses: JSON with consistent error format `{"detail": "message"}`
- Database: Alembic for migrations, never edit models without creating a migration
- Environment variables: all secrets in `.env`, never hardcoded

---

## Key Files to Know

| File | Purpose |
|------|---------|
| `main.py` | App entry, router mounting, static files |
| `app/services/analysis.py` | Oral analysis — 4-couche prompt + Claude call (V-009.be will lift to 5) |
| `app/services/writing_analysis.py` | **THE CORE for writing** — 5-couche La Méthode en Couches prompt + Claude API call |
| `app/templates/index.html` | Main user-facing page |
| `app/templates/admin.html` | Admin dashboard for topic management |
| `app/models/` | SQLAlchemy models |
| `app/routers/` | API endpoints |
| `requirements.txt` | Python dependencies |

---

## Owner Context

**Chadi** — French language tutor, 7,000+ hours teaching anglophones online (primarily via Preply). Based in Morocco, students mostly in Canada. Created La Méthode en Couches, La Méthode Triple Action, La Méthode Eureka, and the 5-box spaced repetition system. Also running Book-Lab (French learning publishing venture). This tool is the SaaS arm of his methodology.

---

## Don'ts

- Don't suggest switching to React/Vue/Next.js — vanilla HTML/JS is intentional for now
- Don't use internal methodology names in user-facing text — these are code/backend only: La Carte, Le Goulet, L'Ordonnance, Le Diagnostic, La Méthode en Couches, Le Fond, Les Moules, Les Moules des Idées, Les Réflexes Anglais, La Voix. User-facing labels (V-009 lock, 2026-05-05; La Voix added V-016a 2026-05-12):
  - EN: Range, Coherence, Accuracy, Fluency, Voice, Your #1 Blocker, Priority fixes
  - FR: Étendue, Cohérence, Correction, Aisance, Voix, Votre frein principal, Corrections prioritaires
  - ES: Alcance, Coherencia, Corrección, Fluidez, Voz, Tu bloqueador #1, Correcciones prioritarias
  - Internal names stay only in `analysis.py`, `writing_analysis.py`, backend code, and `CLAUDE.md`
- Don't use academic jargon (e.g. "L1 interference", "discourse patterns") in user-facing text
- Don't create separate CSS/JS files — keep templates self-contained for now
- Don't suggest features not in the phase plan above without asking
- Don't use placeholder/lorem ipsum content — use real French TCF examples
- Don't break existing functionality when adding features — test first
