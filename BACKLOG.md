# BACKLOG.md

Post-launch / deferred work. Active sprint tickets live in their own scope; this file tracks items explicitly punted out of an in-flight ticket so they don't get lost.

---

## F-077.x — Convert JSON-as-Text columns to JSONB

**Filed:** F-077 (PostgreSQL local-dev parity), 2026-04-27.
**Status:** post-launch.

The codebase stores JSON-shaped data in `Column(Text)` with `json.dumps()` / `json.loads()` in application code. Approx 8–12 such columns across `Feedback`, `Recording`, `Conversation`, `RemediationModule`, `EcoleQuizQuestion`, `Tache2Scenario`, possibly others. Convert to PostgreSQL `JSONB` for native indexing, querying, and storage efficiency.

**Scope:**
- Rewrite affected `Column(Text)` declarations to `Column(JSONB)` (or SQLAlchemy's portable `JSON` if cross-engine matters — JSONB if not).
- Drop `json.dumps()` on every write site; drop `json.loads()` on every read site. SQLAlchemy handles serialization for native JSON columns.
- One Alembic migration per logical group, with `USING column::jsonb` casts for in-place conversion (production data is already valid JSON text by construction; the cast should not lose data, but the migration must include a smoke-test step that round-trips a sample row).
- Add JSONB GIN indexes on commonly-queried paths if any (e.g. `data_targets ? 'foo'`, `criteria_breakdown @> '[{"criterion_key":"X"}]'`).

**Estimate:** 1–2 days. Mostly mechanical edits across read/write call sites; the discipline cost is making sure no caller still wraps the value in `json.dumps()`.

**Out of scope:** schema redesign of the JSON shapes themselves (those stay).

---

## F-079 — Frontend production deploy (Vercel + environment wiring)

**Filed:** 2026-04-28.
**Status:** pre-launch. Placeholder — will be properly specced before implementation.

Pre-launch. Deploy `fluentpath-frontend` to Vercel production. Configure `NEXT_PUBLIC_API_URL` pointing at backend production URL (set after F-078 ships). Update backend CORS allowlist (`main.py`) to include the frontend production domain in addition to `localhost`.

**Estimate:** 1–2h.

**Depends on:** F-078 (backend production URL must exist before frontend can point at it).

---
