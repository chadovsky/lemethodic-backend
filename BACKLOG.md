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

## F-078.x — Async storage migration (`aioboto3`)

**Filed:** F-078 (production deploy + Spaces), 2026-04-28.
**Status:** post-launch.

Replace `boto3` synchronous calls in `app/services/storage.py` with `aioboto3` async equivalents. boto3's `put_object` / `get_object` / `head_object` block the event loop during the round-trip (~50–200 ms per call on Spaces). At soft-beta scale (5–10 concurrent users) this is fine — typical session has 1 upload every 30–60 s. Past ~10 simultaneous uploads it serializes and tail latency starts climbing.

**Scope:**
- Add `aioboto3` to `requirements.txt`.
- Promote `write_bytes` / `read_bytes` / `exists` / `stream_response` to `async def` in the Spaces branch; the local-disk branch can stay sync (it's already cheap).
- Update every caller — tts.py is already async; the four upload routes are already async; `/tts_audio` handler is currently sync (`def`) and needs `async def` if it goes through the async branch. Only ~6 sites total.
- Streaming reads (`stream_response`) should switch from `read_bytes()`-then-`Response(content=...)` to FastAPI's `StreamingResponse` so a 5 MB file doesn't sit fully in memory before the response starts.

**Estimate:** 2–3h.

**Out of scope:** lifecycle policies on Spaces (separate post-launch ticket — orphaned upload cleanup, TTS cache eviction).

---

## F-079 — Frontend production deploy (Vercel + environment wiring)

**Filed:** 2026-04-28.
**Status:** pre-launch. Placeholder — will be properly specced before implementation.

Pre-launch. Deploy `fluentpath-frontend` to Vercel production. Configure `NEXT_PUBLIC_API_URL` pointing at backend production URL (set after F-078 ships). Update backend CORS allowlist (`main.py`) to include the frontend production domain in addition to `localhost`.

**Estimate:** 1–2h.

**Depends on:** F-078 (backend production URL must exist before frontend can point at it).

---

## F-110 — Recordings list endpoint

**Filed:** 2026-04-30.
**Status:** in progress.
**Unblocks:** P-100.

`GET /api/recordings` — REST-canonical list endpoint over the current user's recordings. Distinct from the existing `/api/recordings/history` (which is the dashboard dump with topic + transcript preview + score breakdown); this one is sized for the recordings list view in the new frontend.

**Spec:**
- Authenticated; scoped to the current user's recordings only.
- Query params: `?limit=N` (default 50, max 100). `Query(default=50, ge=1, le=100)` — out-of-range returns 422, not silent clamping.
- Ordered by `created_at DESC`.
- Response shape per recording:
  ```json
  {
    "id": int,
    "tache_mode": "tache_1" | "tache_2" | "tache_3" | "writing" | "legacy" | null,
    "created_at": "2026-04-30T10:00:00",
    "cefr_level": "B2" | null,
    "clb_level": 8 | null,
    "couches": [
      {"key": "le_fond", "score": 4.0, "display_label_en": "Étendue", "display_label_fr": "Étendue"},
      {"key": "les_moules_des_idees", "score": 3.5, ...},
      {"key": "les_moules", "score": 3.0, ...},
      {"key": "les_reflexes_anglais", "score": 3.5, ...}
    ]
  }
  ```
- Recordings without a Feedback row return `cefr_level: null`, `clb_level: null`, `couches: []` — uniform shape so the frontend doesn't special-case missing keys.
- `joinedload(Recording.feedback)` issues a single `LEFT OUTER JOIN`; no N+1.

**Naming divergence from F-088:** F-088's couches array uses `internal_key`; F-110's spec asks for `key`. The new endpoint returns `key` per spec; `/api/recordings/history` and `/api/recordings/{id}` continue to return `internal_key`. Frontend reconciliation strategy is open — either migrate everyone to `key` (small follow-up) or accept the divergence.

**Out of scope:**
- Status filtering (`?status=done` etc.) — frontend can filter client-side off `cefr_level !== null`.
- Pagination beyond `limit` (offset / cursor) — soft beta corpus stays under 100 recordings per user.
- Frontend wiring — separate repo (`lemethodic-frontend`).

---

## F-110.1 — Reconcile couches `internal_key` → `key` across older endpoints

**Filed:** 2026-04-30.
**Status:** blocked on coordination decision (see below).
**Parent:** F-110.

F-110 introduced `key` as the per-couche field name on `GET /api/recordings`. Existing endpoints still emit `internal_key`:
- `GET /api/recordings/history`
- `GET /api/recordings/{id}` (the main diagnostic endpoint)
- `app/services/couche_labels.py::couches_array` (the helper feeding both)

Goal: a single `key` name across every endpoint that returns couches.

**Frontend coupling — verified 2026-04-30 in `fluentpath-frontend/lib/api.ts`:**
- L316 — `interface RawCouche { internal_key: CoucheKey ... }`
- L470 — `KNOWN_COUCHE_KEYS.has(c.internal_key as CoucheKey)`
- L472 — `key: c.internal_key as CoucheKey`

`mapDiagnosticBlock` IS the normalizer, but it READS `internal_key` and WRITES `key`. A backend-only rename would silently empty every couches array in the diagnostic page (filter rejects every row because `c.internal_key` is `undefined`).

**Three coordination strategies:**

1. **Atomic cutover** — Backend ships `key`-only at the same time as frontend reads `c.key`. Cleanest end state; brief breakage window if either side ships first. Best when both repos can deploy together.

2. **Backend dual-emission (transition window)** — Backend emits BOTH `key` and `internal_key` on `couches_array` output. Frontend migrates to `key` whenever convenient. Backend then drops `internal_key` in a F-110.2 follow-up after the frontend deploy lands. Lowest risk; biggest cleanup tail.

3. **Frontend leads** — Frontend reads `c.key ?? c.internal_key` (fallback). Backend renames whenever ready. Frontend later removes the fallback. Unusual ordering — only worth it if the frontend deploy is much faster than the backend.

**My lean:** Option 2 (dual-emission). Pre-launch context — soft beta is days away, not weeks. Eliminating sync risk during launch week is worth the small cleanup tail. The dual-emission code is one line in `couches_array`; the F-110.2 cleanup is also one line.

**Scope of the actual rename pass (whichever strategy):**
- `app/services/couche_labels.py::couches_array` — emit `key` (and optionally `internal_key` in transition).
- `app/routers/recordings.py::list_recordings` (F-110) — already emits `key`; remove the inline re-shape once `couches_array` does the right thing natively.
- `app/routers/recordings.py::get_history` — already calls `couches_array`; transparent change once the helper is fixed.
- `app/routers/recordings.py::get_recording` (the `/{id}` endpoint) — search for any other call site to confirm; it likely calls `couches_array` too.
- Any other caller of `couches_array` — grep before changing.

**Estimate:** 30 min for the backend pass + frontend coordination overhead.

---
