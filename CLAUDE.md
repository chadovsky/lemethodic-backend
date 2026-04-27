# TCF ORAL PRACTICE TOOL — CLAUDE.md

## Project Identity

This is **Chadi's TCF Oral Practice Tool** — a web app where French learners (primarily English-speaking Canadians preparing for TCF Canada) record oral responses to exam-style prompts and receive instant AI-powered feedback using Chadi's proprietary methodology.

**This is NOT a generic language learning app.** The competitive edge is the 4-layer diagnostic framework (La Méthode en Couches) built from 7,000+ hours of tutoring anglophone French learners. No other tool evaluates L1 interference patterns at this depth.

---

## Tech Stack

- **Backend:** Python 3 + FastAPI + SQLAlchemy + Alembic (PostgreSQL local + prod, F-077)
- **Speech-to-Text:** AssemblyAI API
- **AI Analysis:** Anthropic Claude API (claude-sonnet-4-20250514) — processes transcriptions through the 4-layer Les Moules prompt
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
│   └── analysis.py      → THE CORE — 4-layer Les Moules AI analysis engine
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

---

## The Methodology — La Méthode en Couches (4 Couches)

This is the heart of the product. The AI analysis engine in `analysis.py` evaluates oral production across 4 layers:

| Couche | Name | What It Measures |
|--------|------|-----------------|
| 1 | **Le Fond** | Ideas, arguments, examples, relevance to the topic |
| 2 | **Les Moules des Idées** | Discourse organization — does the student structure thought like a French speaker? (context-first vs. point-first, thèse-antithèse-synthèse, etc.) |
| 3 | **Les Moules** | Sentence-level architecture — does each sentence sound French or like translated English? |
| 4 | **Les Réflexes Anglais** | L1 interference — English habits bleeding through: faux-amis, calques, missing *ne*, preposition errors, anglicisms |

### Feedback Output — Le Diagnostic

The analysis returns:
1. **La Carte** — 4 scores (0-5 per couche) + overall /20
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
✅ 4-layer Les Moules analysis engine (analysis.py)
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
| `app/services/analysis.py` | **THE CORE** — 4-layer Les Moules prompt + Claude API call |
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
- Don't use internal methodology names in user-facing text — these are code/backend only: La Carte, Le Goulet, L'Ordonnance, Le Diagnostic, La Méthode en Couches, Le Fond, Les Moules, Les Moules des Idées, Les Réflexes Anglais. User-facing labels are:
  - EN: Content, Idea Structure, Sentence Quality, English Habits, Your #1 Blocker, Priority fixes
  - FR: Contenu, Structure des idées, Qualité des phrases, Réflexes anglais, Votre frein principal, Corrections prioritaires
  - ES: Contenido, Estructura, Calidad frase, Hábitos inglés, Tu bloqueador #1, Correcciones prioritarias
  - Internal names stay only in `analysis.py`, backend code, and `CLAUDE.md`
- Don't use academic jargon (e.g. "L1 interference", "discourse patterns") in user-facing text
- Don't create separate CSS/JS files — keep templates self-contained for now
- Don't suggest features not in the phase plan above without asking
- Don't use placeholder/lorem ipsum content — use real French TCF examples
- Don't break existing functionality when adding features — test first
