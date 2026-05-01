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
**Status:** shipped 2026-04-30 (commit `b25298e`).
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

**Naming divergence from F-088 (resolved 2026-05-01):** F-088's couches array originally used `internal_key`. F-110.1 + F-110.2 reconciled this — every endpoint that returns couches now uses `key` as the per-entry identifier. No divergence remains.

**Out of scope:**
- Status filtering (`?status=done` etc.) — frontend can filter client-side off `cefr_level !== null`.
- Pagination beyond `limit` (offset / cursor) — soft beta corpus stays under 100 recordings per user.
- Frontend wiring — separate repo (`lemethodic-frontend`).

---

## F-110.1 — Reconcile couches `internal_key` → `key` across older endpoints

**Filed:** 2026-04-30.
**Status:** Shipped 2026-05-01. Backend dual-emission landed 2026-04-30 (commit `ca993d1`); frontend migration landed 2026-05-01 (`lemethodic-frontend` commit `c5f9b45`); backend `internal_key` removal in F-110.2.
**Parent:** F-110.

F-110 introduced `key` as the per-couche field name on `GET /api/recordings`. Existing endpoints still emit `internal_key`:
- `GET /api/recordings/history`
- `GET /api/recordings/{id}` (the main diagnostic endpoint)
- `app/services/couche_labels.py::couches_array` (the helper feeding both)

Goal: a single `key` name across every endpoint that returns couches.

**Frontend coupling — verified 2026-04-30 in `fluentpath-frontend/lib/api.ts`:**
- `interface RawCouche` (type) — declares `internal_key: CoucheKey`.
- `KNOWN_COUCHE_KEYS` filter — `.filter((c) => KNOWN_COUCHE_KEYS.has(c.internal_key as CoucheKey))`.
- `mapDiagnosticBlock` mapper — reads `c.internal_key` and writes `key`.

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

## F-110.2 — Drop `internal_key` from `couches_array`

**Filed:** 2026-04-30.
**Status:** Shipped 2026-05-01.
**Parent:** F-110.1.

Cleanup of the F-110.1 dual-emission window. Once `fluentpath-frontend/lib/api.ts` migrates from `c.internal_key` to `c.key` (and the legacy admin template at `app/templates/index.html:3459` does the same), drop `internal_key` from `couches_array`'s output so the API surface has one canonical name.

**Concrete cleanup steps:**
- `app/services/couche_labels.py::couches_array` — remove the `"internal_key": key,` line and update the docstring.
- `app/routers/recordings.py::list_recordings` (F-110) — the inline re-shape currently reads `entry["internal_key"]`; switch to `entry["key"]` (or remove the re-shape entirely since `couches_array` now emits the spec shape natively).
- `app/templates/index.html:3459` — `c.internal_key` → `c.key`. (Internal admin tool, can ship in the same backend commit since it lives in this repo.)
- Grep for any other `internal_key` references that crept in during the transition window — there should be zero.

**Pre-condition gate:** verify with the frontend team / `fluentpath-frontend` repo that no consumer reads `c.internal_key` anymore. F-110.1 verified the call sites in `lib/api.ts`: `interface RawCouche` (type), `KNOWN_COUCHE_KEYS` filter, `mapDiagnosticBlock` mapper. All three must read `c.key` before this ticket can ship.

**Estimate:** 15 min.

---

## F-111 — Investigate DO Spaces Limited Access key `InvalidArgument`

**Filed:** 2026-04-30.
**Status:** post-launch.

During the launch-week debug of a production 500 on `/api/conversations/{id}/turn`, we found that the rotated DO Spaces key (Limited Access scope) was returning `InvalidArgument` on every operation against the bucket — `PutObject` (audio uploads) and `HeadObject` (F-052 TTS cache lookups) alike. Replacing it with a Full Access key resolved both immediately. No other variable changed (same bucket, region, endpoint, code path).

The Limited Access scope is supposed to grant per-bucket `s3:*` equivalent permissions via DO's IAM-like model. Either (a) the scope was mis-applied at key-creation time, (b) DO's Limited Access does not in fact support the operations we need, or (c) there's a bug in DO's auth layer that returns `InvalidArgument` (with a null `Message`) instead of `AccessDenied` for scope mismatches — which is what we observed and is what made the bug nearly impossible to diagnose from response payloads.

**Risk:** the Full Access key currently in production has broader privileges than the principle of least privilege calls for. It can list/delete other buckets in the account, rotate credentials, etc. If this key leaks, the blast radius is the whole Spaces account, not just our app's bucket.

**Scope:**
- Re-create a Limited Access key against the same bucket and reproduce the failure with the minimal Python repro we used in DO Console.
- If reproducible, escalate to DO support with the repro: minimal `boto3.client("s3")` + `put_object` against a bucket-scoped Limited Access key returning `InvalidArgument` with no `Message`.
- If non-reproducible (i.e. it works now), document as a one-off and re-attempt the rollover to a Limited Access key in production.
- Regardless of outcome, swap production back to a Limited Access key once the root cause is understood.

**Estimate:** 1–2h for the repro pass; unknown for the DO support cycle.

**Out of scope:** introducing a separate IAM-style policy layer in front of Spaces. The fix is to use DO's own scoping correctly, not to invent our own.

---

## P-102 — Visual quality pass

**Filed:** 2026-04-30.
**Status:** Queued.
**Priority:** Medium (post-launch).

Tailwind UI template, ~$300 budget. Stub — spec TBD.

---

## P-103 — Audio upload security hardening (user_id-prefixed storage keys)

**Filed:** 2026-04-30.
**Status:** Shipped 2026-05-01 — sub-item 2 (user_id-prefixed keys + helper). Sub-items 1 and 3 closed during scoping.
**Priority:** HIGH (pre-launch blocker).

Originally three sub-items (size cap, user_id ownership, auth-checked serve). Audit on 2026-05-01 found:

- **Sub-item 1 — size cap:** already shipped as F-075a (two-layer defense, 10 MB cap, 413 response, verification harness in `scripts/verify_f075a_size_cap.py`). No further work in P-103. Optional follow-up tracked in **P-103.1**.
- **Sub-item 2 — user_id ownership:** shipped 2026-05-01. New helper `app/services/storage.py::user_upload_key(user_id, ext)` returns `uploads/{user_id}/{uuid4}.{ext}`. The four upload sites (`recordings.py::upload_and_analyze`, `recordings.py::transcribe_only`, `audio.py::upload_and_transcribe`, `conversations.py::append_turn` legacy F-048 path) now route through it. Migration: Option A — old recordings stay at `uploads/<uuid>.<ext>` and both shapes coexist forever; any future read path must accept both. The "candidate audio is write-only from the API surface" invariant is documented in the storage.py module docstring.
- **Sub-item 3 — auth-checked serve:** no current serve endpoint for candidate audio (audit confirmed — the conversation turn serializer at `conversations.py::_serialize_turn` deliberately filters candidate `audio_url` out of responses, and there is no `/api/recordings/{id}/audio` endpoint). Closed; deferred to **P-103.2** if/when a playback feature is specified.

**Estimate:** delivered.

---

## P-103.1 — Optional: tighter audio cap + duration enforcement

**Filed:** 2026-05-01.
**Status:** Queued.
**Priority:** Low (post-launch, validate first).

Two possible tightenings to the F-075a size cap:

- Lower `MAX_AUDIO_UPLOAD_BYTES` below 10 MB if real-user data shows nobody legitimately uploads files near the cap.
- Enforce `MAX_AUDIO_SECONDS = 900` server-side. Currently declared in `app/config.py` but not consumed anywhere — duration is taken on trust from the client's `duration_seconds` form field, which the user can spoof.

Validate with usage data before tightening. Premature tightening risks 413-ing legitimate recordings.

**Estimate:** 30 min if validated.

---

## P-103.2 — Deferred: authenticated candidate-audio serve endpoint

**Filed:** 2026-05-01.
**Status:** Deferred — build only when a playback feature is specified.
**Priority:** Medium (when needed).

Today candidate audio is write-only from the API surface (no GET endpoint exposes user-uploaded recordings; the conversation turn serializer at `conversations.py::_serialize_turn` deliberately filters candidate `audio_url` out of the response). If a future feature requires playback (e.g. recordings list lets users replay their own clips), the design must be:

- Path: `GET /api/recordings/{id}/audio` (or equivalent under conversations).
- Auth: `Depends(get_current_user)`.
- Ownership: load the `Recording`, assert `recording.user_id == current_user.id` before serving.
- Body: either streamed via `storage.stream_response(...)` or a short-TTL presigned URL (5 minutes typical).
- Tolerate both storage-key shapes: pre-P-103 `uploads/<uuid>.<ext>` and post-P-103 `uploads/<user_id>/<uuid>.<ext>`. The DB-level ownership check is authoritative; do not parse the storage key to determine ownership.
- Never expose raw `uploads/*` paths via any GET endpoint.

The invariant statement lives in `app/services/storage.py`'s module docstring; honor it when designing this endpoint.

**Estimate:** 2h when the feature is specified.

---

## P-104 — Background tab timer drift fix

**Filed:** 2026-04-30.
**Status:** Queued.
**Priority:** HIGH (pre-launch blocker).

Recording timer drifts when the browser tab is backgrounded. Stub — spec TBD.

---

## P-105 — 7-day free trial logic

**Filed:** 2026-04-30.
**Status:** Queued.
**Priority:** High (pre-launch).

Stub — spec TBD.

---

## P-106 — Stripe integration with dual + geographic pricing

**Filed:** 2026-04-30.
**Status:** Queued.
**Priority:** High (pre-launch).

Stub — spec TBD.

---

## P-107 — Soft satisfaction guarantee copy + refund flow

**Filed:** 2026-04-30.
**Status:** Queued.
**Priority:** Medium (pre-launch).

Stub — spec TBD.

---

## P-108 — Pronunciation feedback (basic)

**Filed:** 2026-04-30.
**Status:** Queued.
**Priority:** Medium (post-launch).

Stub — spec TBD.

---

## P-109 — TCF Canada speaking simulator MVP

**Filed:** 2026-04-30.
**Status:** Queued.
**Priority:** High (pre-launch).

Stub — spec TBD.

---

## P-110 — Onboarding refinement (TCF-specific)

**Filed:** 2026-04-30.
**Status:** Queued.
**Priority:** Medium (pre-launch).

Stub — spec TBD.

---

## M-100 — Past Preply student outreach

**Filed:** 2026-04-30.
**Status:** Queued.
**Priority:** HIGH (highest leverage, costs zero).

Re-engagement angle, not first contact. Stub — spec TBD.

---

## M-101 — Landing page copy in LeMethodic voice

**Filed:** 2026-04-30.
**Status:** Queued.
**Priority:** High.

Stub — spec TBD.

---

## M-102 — Convert Preply reviews to social proof

**Filed:** 2026-04-30.
**Status:** Queued.
**Priority:** Medium.

Stub — spec TBD.

---

## M-103 — YouTube channel launch

**Filed:** 2026-04-30.
**Status:** Queued.
**Priority:** Medium.

Stub — spec TBD.

---

## M-104 — Reddit community engagement

**Filed:** 2026-04-30.
**Status:** Queued.
**Priority:** Medium.

Stub — spec TBD.

---

## M-105 — LinkedIn long-form content

**Filed:** 2026-04-30.
**Status:** Queued.
**Priority:** Medium.

Stub — spec TBD.

---

## M-106 — Blog launch

**Filed:** 2026-04-30.
**Status:** Queued.
**Priority:** Medium.

Stub — spec TBD.

---

## M-107 — Express Entry Discord/Telegram outreach

**Filed:** 2026-04-30.
**Status:** Queued.
**Priority:** Medium.

Stub — spec TBD.

---

## M-108 — Beta user testimonial pipeline

**Filed:** 2026-04-30.
**Status:** Queued.
**Priority:** High.

Stub — spec TBD.

---

## B-100 — Stripe account setup

**Filed:** 2026-04-30.
**Status:** Queued.
**Priority:** HIGH (pre-launch).

Stub — spec TBD.

---

## B-101 — Legal entity decision

**Filed:** 2026-04-30.
**Status:** Queued.
**Priority:** Medium.

Stub — spec TBD.

---

## B-102 — Privacy policy + ToS

**Filed:** 2026-04-30.
**Status:** Queued.
**Priority:** HIGH (pre-launch).

Stub — spec TBD.

---

## B-103 — Trademark research on "LeMethodic"

**Filed:** 2026-04-30.
**Status:** Queued.
**Priority:** Low.

Stub — spec TBD.

---

## B-104 — Email marketing infrastructure

**Filed:** 2026-04-30.
**Status:** Queued.
**Priority:** Medium.

Stub — spec TBD.

---

## B-105 — Analytics setup

**Filed:** 2026-04-30.
**Status:** Queued.
**Priority:** Medium.

Stub — spec TBD.

---

## P-200 — Writing pedagogy build

**Filed:** 2026-04-30.
**Status:** Queued.
**Priority:** High (Phase 2, post-launch).

Analysis prompts + 5-criterion scoring + diagnostic surface for the
writing track. Stub — spec TBD.

---

## P-201 — TEF exam support

**Filed:** 2026-04-30.
**Status:** Queued.
**Priority:** Medium (Phase 2, post-launch).

Multi-exam routing (F-091) + TEF-specific prompts + TEF scoring
rubric. Stub — spec TBD.

---

## P-202 — DELF exam support

**Filed:** 2026-04-30.
**Status:** Queued.
**Priority:** Medium (Phase 2, post-launch).

Stub — spec TBD.

---

## P-203 — Italian-audience expansion

**Filed:** 2026-04-30.
**Status:** Queued.
**Priority:** Low (Phase 2, post-launch).

Per Chadi's noted interest in Italian-speaking French learners.
Stub — spec TBD.

---
