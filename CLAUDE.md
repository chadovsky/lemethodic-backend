# Le Méthodic Backend — CLAUDE.md

## Execution Source of Truth

**`docs/prd-v1.md` is the execution source of truth as of 2026-05-21.** The old `BACKLOG.md` is superseded but kept in-repo for audit trail — do not add new entries to it.

**Current operating mode:** manual, one micro-feature per session, UI-first sequencing.
- Plan with Opus (claude.ai) → execute with Sonnet (Claude Code) → `/compact focus on <entry-id>` between sessions.
- Sequence: Section 1 (UI shells) → Section 2 (mocks + polish) → Section 3 (BE wiring) → Section 4 (content) → Section 5 (AI infra) → Section 6 (legal) → Section 7 (launch).
- **FE consumes this BE via `/api/*`.** FE PRD is at Section 3 (BE wiring), 5/22 shipped (BE-001–005), main at 4fd9ea3, tag v0.3.5.
- **BE feature work is paused** during FE Section 3 except for reactive bug fixes and discovery notes. The lift from 4-couche to 5-couche oral (V-009.be) and the RAG runtime wiring open in Section 5 (AI infra).

**Deprecated orchestrator workflow (do not regenerate or reference):**
- `parse_backlog.py`
- `dispatch_agent.py`
- `mark_done.py`
- `n8n-workflow.json`
- `setup-orchestrator.md`

These files defined the multi-agent orchestrator path killed on 2026-05-21 (cost projection $200–400/sprint, unaffordable at Y0 revenue). Replaced by Manual Mode above. See `docs/prd-v1.md` §1.1.

---

## Four principles

1. **No silent assumptions.** If you don't know what a function does or what shape an endpoint returns, read the code. Don't guess.
2. **Scope is sacred.** A 50-line feature stays 50 lines. Don't expand to 500 because "it might be useful later." V1.1+ is a real place we put things.
3. **Don't touch what wasn't requested.** Orthogonal changes (formatting, refactoring, renaming) are forbidden in feature work. Open a separate PR if it matters.
4. **No "it works" without evidence.** Run the tests. Run the smoke scripts. Say which ones passed. If they failed, fix them — don't skip them.

---

## Project Identity

This is **Le Méthodic** (lemethodic.com) — a web app where French learners (primarily English-speaking Canadians preparing for TCF Canada, plus a broader pivot to TCF/TEF/DELF/DALF/FIDE/AP/DCL) record oral responses + submit writing to exam-style prompts and receive instant AI-powered feedback using Chadi's proprietary 5-couche methodology (La Méthode en Couches). Dead names: TCF Oral Practice Tool, FluentPath, FluentPrep, Le Raccourci.

**This is NOT a generic language learning app.** The competitive edge is the 5-layer diagnostic framework (La Méthode en Couches) built from 7,000+ hours of tutoring anglophone French learners. No other tool evaluates L1 interference patterns at this depth.

---

## Tech Stack

- **Backend:** Python 3 + FastAPI + SQLAlchemy + Alembic + PostgreSQL (local via docker-compose; prod = DigitalOcean managed Postgres FRA1).
- **Speech-to-Text:** AssemblyAI API.
- **AI Analysis:** Anthropic Claude via `app/services/ai_router.py` — routes to current Claude Opus / Sonnet / Haiku tiers by task. **Model strings live in `ai_router.py`, never inline in business logic.** Verify `ai_router.py` is on current tiers periodically — the model string `claude-sonnet-4-20250514` documented in earlier CLAUDE.md revisions is now stale.
- **Voice:**
  - **ElevenLabs** for **Le Maître** (Chadi-clone) — unified tutor persona across L'École, Le Vocabulaire, and Le Diagnostic onboarding.
  - **OpenAI TTS-1-HD** is **examiner-only** for Tâches. Brand-critical, non-negotiable. Do not propose swapping it for Piper / Supertonic / cheaper alternatives — those can be evaluated for L'École / Vocabulaire narration only.
  - Sophie is dead as a persona. Do not reintroduce.
- **Optional model routing for cost control:** Mistral Large for FR-critical scoring / enrichment / couche tagging; Groq Llama for bulk classification. OpenAI for embeddings. All routed through `ai_router.py`.
- **Frontend:** **Not in this repo.** FE lives in `chadovsky/lemethodic-frontend` (branch: `main`) — Next.js 16 + Tailwind v4 + React 19. This BE serves `/api/*` only. Legacy `app/templates/` and `app/static/` survive in the repo from the pre-Next.js era but should not be extended.
- **Auth:** session-based with hashed passwords + refresh tokens (F-406), rate limits, hCaptcha on entry surfaces. Auth is consumed FE-side via `ProtectedRoute` wrapping the `(app)` route group.

---

## Architecture Path A (locked 2026-05-23)

The BE is **preserved**. We wire FE surfaces to existing endpoints; we do not rewrite this BE in Next.js Route Handlers, Prisma, Drizzle, or anything else. Symmetric statement to the FE CLAUDE.md.

**Endpoints already shipped but deferred FE-side to V1.1+** (do not propose deprecating or rewriting these — they're production-ready, FE just hasn't built the surfaces yet):
- `/api/writing/*` — full writing pipeline.
- `/api/analytics/{dashboard,progress,coverage}`.
- `/api/today/me/today` — daily action recommendation.
- `/api/onboarding/*` — partial overlap with current signup; FE wiring scheduled.
- `/api/modules` + `/api/users/me/recurring_modules` — remediation modules.
- `/api/oral/generate-structure` — argument scaffold.

---

## Architecture Overview

```
main.py                  → App entry point, mounts routers
app/
├── models/              → SQLAlchemy models (30+: User, Topic, Recording, Analysis, refresh_tokens, etc.)
├── routers/             → FastAPI route handlers (18 routers, 47 endpoints)
├── schemas/             → Pydantic request/response schemas (separate from ORM models)
└── services/
    ├── ai_router.py     → Model-tier routing for Claude / Mistral / Groq calls
    ├── analysis.py      → Oral analysis engine (4 couches today; V-009.be queued to lift to 5)
    ├── writing_analysis.py → Writing analysis engine (5 couches, live since V-016a 2026-05-12)
    └── ... (AssemblyAI STT, TTS cache, Tâche 1/2/3 services, transcript suggestions)
alembic/                 → Alembic migrations (F-077)
alembic.ini              → Alembic config
.do/                     → DigitalOcean App Platform spec (auto-deploy on push to master)
docker-compose.yml       → Local PostgreSQL
data/                    → Static data files
data-layer/              → RAG corpus + `vectorize.py` (scaffolded, NOT wired into runtime as of 2026-05-23)
docs/                    → docs/prd-v1.md is the source of truth
scripts/                 → Seeders + F-321 vocab pipeline + smoke tests + verification harnesses
  └── archive/           → Retired one-off SQLite migration scripts (F-077)
seeds/                   → DB seed payloads
storage/                 → File storage
tests/                   → pytest test suite
uploads/                 → User audio recordings (gitignored)
archive/                 → Pre-routers async scaffold orphans (F-077)
```

**Repo hygiene notes:**
- A stray `{app` directory exists at repo root from a botched PowerShell brace expansion (PowerShell doesn't do bash-style `{a,b}` expansion). Safe to delete — `Remove-Item -Recurse -Force '{app'` — but not urgent.
- `.claude/` directory exists at repo root for Claude Code skills/agents scaffolding. Gap 2 work (encoding the standard ship cycle as skills) will live there.

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
- The local-dev password is intentionally non-secret (it's local only and never shipped). Production uses managed PostgreSQL with a real secret injected via `DATABASE_URL`.
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

## Data assets

The corpus has grown substantially beyond the original 84 Tâche 3 topics. As of the data-layer Phase 1 close (May 2026):

- **945K FR chunks** across 9 sources: DBnary, Wiki AdQ, Lexique3, Gutenberg, PARSEME, CollFrEn, Anki, UniversalCEFR, WikipediaFR.
- **1.56M Tatoeba** sentence pairs.
- **9,249 native CEFR-tagged chunks** ready for retrieval.
- **F-321 Phase 1**: 1,684 vocab rows awaiting Chadi offline triage (highest-leverage Chadi-bottlenecked work right now).
- **B2 scarcity identified**: only ~250 native B2 chunks → **D-034** targeted enrichment run is underway.
- **Original 84 topics** seeded across 7 themes (Vie quotidienne, Société, Éducation, Technologie, Environnement, Culture, Travail), TCF Tâche 3 format (monologue argumenté) — still in use for Tâche 3 prompts; complemented but not replaced by the chunk corpus.

The RAG retrieval layer (`data-layer/vectorize.py`) is **scaffolded but not yet hooked into runtime**. Section 5 (AI infra) in the PRD opens the wiring work.

---

## Current state (as of 2026-05-23)

- **53,821 LOC**, 47 endpoints across 18 routers, 30+ SQLAlchemy models.
- **AI fully wired**: AssemblyAI STT, Claude oral 4-couche analysis, Claude writing 5-couche analysis (V-016a), Tâche 1/2/3 services, argument scaffold, transcript suggestions, TTS cache, `ai_router` for model tiering.
- **V-009.be queued**: lift the oral analysis path from 4 to 5 couches to match writing.
- **RAG runtime not yet wired** — `data-layer/vectorize.py` exists; retrieval endpoints opening in Section 5.
- **FE consumes via `/api/*`** — see Section 3 (BE wiring) in the FE PRD. 5/22 entries shipped via BE-001–005 (auth, user identity, L'École, vocab, tâches).
- **Production stable**: `seal-app-75fiu.ondigitalocean.app`, DO managed Postgres FRA1, deploy-on-push to `master`.

---

## Priority order

Canonical: `docs/prd-v1.md`. Don't maintain a parallel priority list in this file.

While FE is mid-Section 3, BE work is paused except for:
- Reactive bug fixes.
- F-321 vocab review (Chadi offline, 1,684 rows in queue).
- Schema preservation / discovery notes ahead of Section 5 (AI infra), which will lift V-009.be, wire RAG, and add the activation layer (D-028 / D-029 / D-033).

---

## Code Conventions

- Python: type hints, docstrings on public functions.
- **Pydantic schemas** in `app/schemas/` are separate from SQLAlchemy models in `app/models/`. Schemas govern API contracts; models govern persistence. Don't conflate.
- API responses: JSON with consistent error format `{"detail": "message"}`.
- Database: Alembic for migrations, never edit models without creating a migration. Never `Base.metadata.create_all` outside tests.
- **AI calls route through `app/services/ai_router.py`** — never hardcode model strings in business logic. The router is the one place model versions live, which means version bumps happen in one diff.
- Environment variables: all secrets in `.env`, never hardcoded.
- Tests in `tests/` (pytest). Smoke scripts in `scripts/smoke_*.py` for prod-facing verification. Verification harnesses in `scripts/` per ticket.

---

## Key Files to Know

| File | Purpose |
|------|---------|
| `main.py` | App entry, router mounting, static files |
| `app/routers/*.py` | 18 routers covering auth, recordings, conversations, L'École, writing, vocab, users, onboarding, analytics, admin, Stripe webhook, etc. |
| `app/models/*.py` | 30+ SQLAlchemy models |
| `app/schemas/*.py` | Pydantic request/response schemas |
| `app/services/ai_router.py` | Model-tier routing for Claude / Mistral / Groq |
| `app/services/analysis.py` | Oral analysis — 4-couche prompt + Claude call (V-009.be will lift to 5) |
| `app/services/writing_analysis.py` | **THE CORE for writing** — 5-couche La Méthode en Couches prompt + Claude API call |
| `alembic/versions/` | Migrations |
| `scripts/` | Seeders, F-321 vocab pipeline (classify / dedup / extract), smoke tests, verification harnesses |
| `data-layer/` | RAG corpus + `vectorize.py` (scaffolded, not wired) |
| `.do/app.yaml` | DigitalOcean App Platform spec — `deploy_on_push: true`, `alembic upgrade head && uvicorn ...` |
| `requirements.txt` | Python dependencies |

---

## Git workflow + environment

- **BE branch is `master`. FE is `main`. Not interchangeable.**
- Branch name: `feat/<id>-<name>` (e.g., `feat/v-009-be-five-couche-oral`).
- Squash-merge to `master`. Always. No merge commits.
- **`master` auto-deploys via DO App Platform** (`deploy_on_push: true`) and auto-applies pending migrations (`alembic upgrade head` in the run command). The migration ASK + pg_dump pre-flight protocol above is what protects this.
- Update PRD status on feature branch before squash-merge — status line in `docs/prd-v1.md` moves to `Shipped` with the post-squash SHA.
- BE does not tag every-5 the way FE does; FE tags govern section milestones.
- **PRD (`docs/prd-v1.md`) is the source of truth.**
- Dev machine: Windows + PowerShell. Use `code.cmd` not `code` (PATH hijack).
- PowerShell escapes curly braces in stash refs: `'stash@{0}'` (single quotes).
- Multi-line pastes break PowerShell — single-line, joined with `;`.
- **Never call the product FluentPrep, FluentPath, TCF Oral Practice Tool, or Le Raccourci.** It's Le Méthodic.

---

## Owner Context

**Chadi** — French language tutor, 7,000+ hours teaching anglophones online (primarily via Preply). Based in Morocco, students mostly in Canada. Created La Méthode en Couches, La Méthode Triple Action, La Méthode Eureka, and the 5-box spaced repetition system. Also running Book-Lab (French learning publishing venture). This tool is the SaaS arm of his methodology.

---

## Don'ts

- **Don't rewrite this BE in Next.js Route Handlers, Prisma, Drizzle, or anything else.** Architecture Path A is locked. We wire FE surfaces to existing `/api/*`; new endpoints get added to FastAPI, not migrated out of it.
- **Don't propose deprecating the V1.1+-deferred endpoints** (`/api/writing/*`, `/api/analytics/*`, `/api/today/*`, `/api/modules`, `/api/oral/generate-structure`). They exist, they work, they're waiting for FE surfaces.
- **Don't break the V-009.be queue.** The oral analysis path is mid-transition from 4 to 5 couches. Changes that touch `analysis.py` need to be checked against the queued lift.
- **Don't suggest swapping OpenAI TTS-1-HD on the examiner voice** for Piper / Supertonic / Whisper TTS / any other engine. Examiner voice is brand-critical. Vocab/École narration is fair game for cheaper alternatives.
- **Don't use internal methodology names in user-facing text** — these stay backend-only: La Carte, Le Goulet, L'Ordonnance, Le Diagnostic, La Méthode en Couches, Le Fond, Les Moules, Les Moules des Idées, Les Réflexes Anglais, La Voix. User-facing labels (V-009 lock, 2026-05-05; La Voix added V-016a 2026-05-12):
  - **EN**: Range, Coherence, Accuracy, Fluency, Voice, Your #1 Blocker, Priority fixes
  - **FR**: Étendue, Cohérence, Correction, Aisance, Voix, Votre frein principal, Corrections prioritaires
  - **ES**: Alcance, Coherencia, Corrección, Fluidez, Voz, Tu bloqueador #1, Correcciones prioritarias
  - Internal names stay only in `analysis.py`, `writing_analysis.py`, backend code, and `CLAUDE.md`.
- **Don't use academic jargon** (e.g. "L1 interference", "discourse patterns") in user-facing text.
- **Don't hardcode model strings** in business logic. Route through `ai_router.py`.
- **Don't suggest features not in `docs/prd-v1.md`** without asking.
- **Don't use placeholder/lorem ipsum content** — use real French TCF examples.
- **Don't break existing functionality** when adding features — test first.

---

## Done definition

A BE feature is done when:

1. Tests pass (pytest unit + integration + smoke script against affected endpoints).
2. If migration: migration ASK was sent + approved per the protocol above, pg_dump tier honored.
3. If seeder: seed ASK was sent + approved + Chadi ran the seeder on prod via DO console + post-seed verification query confirmed.
4. PRD status line moved to `Shipped` with the post-squash SHA on the feature branch.
5. Squash-merged to `master` → DO auto-deploys.
6. Post-deploy probe confirms (`/health` + representative endpoint exercising the new code).
7. Branch deleted locally and on origin.