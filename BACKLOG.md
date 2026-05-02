# BACKLOG.md

**Last updated:** 2026-05-02 (re-baseline pass + 5-decision follow-up).
**Phase 1 Architecture Rework** — see `lemethodic-frontend/LEMETHODIC-CURRICULUM.md` v0.2.

Active and deferred work tracking. Tickets are organized by **Tag** —
the section a ticket lives in matches its `**Tag:**` line. Section
ordering: Active → P1 → P2 → Deferred → Closed → Shipped. The Active
Queue summary at the top of this file reproduces only the launch-critical
slate in priority order; bodies live below.

Re-runnable via `scripts/regen_backlog.py` — change classification
constants there and regenerate.

---

## Active Queue — Launch Critical (60-day target)

In stated priority order. Full ticket bodies live below in the "Active — Launch Critical" section.

| # | Ticket | Title |
|---|---|---|
| 1 | **P-220** | Onboarding questionnaire |
| 2 | **P-200** | Diagnostic engine: detector implementation |
| 3 | **P-201** | Diagnostic engine: level assignment + confidence |
| 4 | **P-221** | Diagnostic flow integration |
| 5 | **P-104** | Background tab timer drift fix |
| 6 | **P-240** | Today's recommended action |
| 7 | **F-079** | Custom domain wiring (lemethodic.com → Vercel) |
| 8 | **P-105** | 7-day free trial logic |
| 9 | **P-106** | Stripe integration with dual + geographic pricing |
| 10 | **P-260.5** | Author 3 TCF Canada mock exams for Sprint product |
| 11 | **B-100** | Stripe account setup |
| 12 | **B-102** | Privacy policy + ToS |
| 13 | **M-100** | Past Preply student outreach |
| 14 | **M-101** | Landing page copy in LeMethodic voice |
| 15 | **M-103** | YouTube channel launch (scope-reduced) |
| 16 | **M-104** | Reddit community engagement |

---
# Active — Launch Critical (16 tickets, 60-day target)

## P-220 — Onboarding questionnaire

**Filed:** 2026-05-01.
**Status:** Backend shipped 2026-05-02 (commits `4c272da` schema + endpoints + smoke; `bb76eb8` `interface_language` follow-up). FE rebuild in flight (separate ticket on the frontend repo).
**Tag:** Active — Launch Critical (60-day target).

**Phase:** Phase 1 Architecture Rework.
**Source:** LEMETHODIC-CURRICULUM v0.2 §10; copy spec at `docs/P-220-onboarding-questionnaire-copy.md`.

Backend scope: schema migration `b3a55c1e0001` (7 new User columns + `UserPathEnrollment.persona` with CHECK constraints), Pydantic schemas, FR + EN question content, routing service (Q1+Q2 → path slug; Q3 → persona; Q3+Q7 → capacity warning; Q11 → UI mode default), and 2 endpoints (`GET /onboarding/questions`, `POST /onboarding/submit`). Legacy `POST /api/users/onboarding` kept accept-and-no-op with a `Deprecation` header for the FE migration window. Q4-Q10 routing deferred to P-220.x. Q12 reminder time deferred to P-220.y.

---

## P-200 — Diagnostic engine: detector implementation

**Filed:** 2026-05-01.
**Status:** Queued.
**Tag:** Active — Launch Critical (60-day target).

**Phase:** Phase 1 Architecture Rework.
**Source:** LEMETHODIC-CURRICULUM v0.2 §10.

Backend scope: per-couche pattern detector implementation feeding the diagnostic flow. Stub — full spec in `lemethodic-frontend/LEMETHODIC-CURRICULUM.md`.

---

## P-201 — Diagnostic engine: level assignment + confidence

**Filed:** 2026-05-01.
**Status:** Queued.
**Tag:** Active — Launch Critical (60-day target).

**Phase:** Phase 1 Architecture Rework.
**Source:** LEMETHODIC-CURRICULUM v0.2 §10.

Backend scope: level assignment logic and confidence scoring on top of the detectors. Stub — full spec in `lemethodic-frontend/LEMETHODIC-CURRICULUM.md`.

---

## P-221 — Diagnostic flow integration

**Filed:** 2026-05-01.
**Status:** Queued.
**Tag:** Active — Launch Critical (60-day target).

**Phase:** Phase 1 Architecture Rework.
**Source:** LEMETHODIC-CURRICULUM v0.2 §10.

Backend scope: engine wiring — connect detectors + level assignment + confidence into onboarding and the recordings pipeline. Stub — full spec in `lemethodic-frontend/LEMETHODIC-CURRICULUM.md`.

---

## P-104 — Background tab timer drift fix

**Filed:** 2026-04-30.
**Status:** Queued.
**Tag:** Active — Launch Critical (60-day target).

**Priority:** HIGH (pre-launch blocker).

Recording timer drifts when the browser tab is backgrounded. Stub — spec TBD.

---

## P-240 — Today's recommended action

**Filed:** 2026-05-01.
**Status:** Queued.
**Tag:** Active — Launch Critical (60-day target).

**Phase:** Phase 1 Architecture Rework.
**Source:** LEMETHODIC-CURRICULUM v0.2 §10.

Backend scope: prescription endpoint returning the next-best action for a user given their diagnostic state. Stub — full spec in `lemethodic-frontend/LEMETHODIC-CURRICULUM.md`.

---

## F-079 — Custom domain wiring (lemethodic.com → Vercel)

**Filed:** 2026-04-28; reframed 2026-05-02 (Vercel deploy already shipped).
**Status:** Vercel deploy shipped (`lemethodic-frontend.vercel.app`). Custom domain wiring pending.
**Tag:** Active — Launch Critical (60-day target).

**Priority:** HIGH (pre-launch — without DNS the FE has no canonical production URL).

Remaining work:
- ✓ Vercel deploy: shipped.
- ✗ DNS A records (registrar → Vercel) — pending.
- ✗ Vercel custom domain config (`lemethodic.com` + `www` subdomain) — pending.
- ✗ Backend CORS allowlist (`main.py`) update to include `https://lemethodic.com` — pending.
- ✗ Verify HTTPS via Vercel-managed Let's Encrypt cert.

**Estimated effort:** ~1 hour of Chadi's time (DNS + Vercel config + propagation wait). No engineering work beyond the CORS allowlist line.

**Owner:** Chadi (DNS + Vercel) + Engineering (one-line CORS update).

**Depends on:** F-078 (backend production URL must exist before frontend can point at it).

---

## P-105 — 7-day free trial logic

**Filed:** 2026-04-30.
**Status:** Queued.
**Tag:** Active — Launch Critical (60-day target).

**Priority:** High (pre-launch).

Stub — spec TBD.

---

## P-106 — Stripe integration with dual + geographic pricing

**Filed:** 2026-04-30.
**Status:** Queued.
**Tag:** Active — Launch Critical (60-day target).

**Priority:** High (pre-launch).

Stub — spec TBD.

---

## P-260.5 — Author 3 TCF Canada mock exams for Sprint product

**Filed:** 2026-05-02.
**Status:** Queued.
**Tag:** Active — Launch Critical (60-day target).

**Priority:** HIGH (pre-launch blocker for Sprint product).
**Source:** Strategy session — Sprint product scope refinement.
**Depends on:** none (authoring, no code).

**Scope:** author 3 full TCF Canada mock exams. Each mock contains:

- **Tâche 1 prompt** — structured interview, 2 min, no preparation.
- **Tâche 2 prompt** — interactive exercise, 5.5 min including 2 min preparation.
- **Tâche 3 prompt** — point of view, 4.5 min, no preparation.
- **Scoring rubrics** aligned to TCF Canada CEFR criteria (A1 through C2).
- **Sample strong responses** at B2 level for each Tâche.
- **Common error patterns** to flag in evaluation.

**Owner:** Chadi (authoring).

**Estimated effort:** 12–18 hours total (~4–6 hours per mock).

**Trigger:** pre-launch — Sprint product cannot ship without these.

---

## B-100 — Stripe account setup

**Filed:** 2026-04-30.
**Status:** Queued.
**Tag:** Active — Launch Critical (60-day target).

**Priority:** HIGH (pre-launch).

Stub — spec TBD.

---

## B-102 — Privacy policy + ToS

**Filed:** 2026-04-30.
**Status:** Queued.
**Tag:** Active — Launch Critical (60-day target).

**Priority:** HIGH (pre-launch).

Stub — spec TBD.

---

## M-100 — Past Preply student outreach

**Filed:** 2026-04-30.
**Status:** Queued.
**Tag:** Active — Launch Critical (60-day target).

**Priority:** HIGH (highest leverage, costs zero).

Re-engagement angle, not first contact. Stub — spec TBD.

---

## M-101 — Landing page copy in LeMethodic voice

**Filed:** 2026-04-30.
**Status:** Queued.
**Tag:** Active — Launch Critical (60-day target).

**Priority:** High.

Stub — spec TBD.

---

## M-103 — YouTube channel launch (scope-reduced)

**Filed:** 2026-04-30; scope-reduced 2026-05-02.
**Status:** Queued.
**Tag:** Active — Launch Critical (60-day target).

**Priority:** Medium (pre-launch credibility artifact, not a sustained channel commitment).

**Scope (reduced):** 1 anchor video pre-launch as a credibility artifact — ~5-10 min, exam-prep tactic on a topic with low SEO competition (e.g., "TCF Canada Tâche 3 — what scoring actually rewards"). Single video establishes the channel + serves as a referral asset; cadence is **not** committed pre-launch.

**Re-evaluate post-launch:** if the anchor video drives meaningful traffic or referral signal within 4-8 weeks, decide whether to commit to a sustained cadence (monthly anchor + occasional shorts) or leave the channel as a one-shot artifact. Default: leave as-is unless signal is clear.

**Owner:** Chadi (recording + editing + thumbnail). Solo founder cost is high — no monthly commitment until signal justifies it.

---

## M-104 — Reddit community engagement

**Filed:** 2026-04-30.
**Status:** Queued.
**Tag:** Active — Launch Critical (60-day target).

**Priority:** Medium.

Stub — spec TBD.

---

# Post-launch P1 (2-4 weeks after launch)

## P-107 — Soft satisfaction guarantee copy + refund flow

**Filed:** 2026-04-30.
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Priority:** Medium (pre-launch).

Stub — spec TBD.

---

## P-108 — Pronunciation feedback (basic)

**Filed:** 2026-04-30.
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Priority:** Medium (post-launch).

Stub — spec TBD.

---

## P-110 — Onboarding refinement (TCF-specific)

**Filed:** 2026-04-30.
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Priority:** Medium (pre-launch).

Stub — spec TBD.

---

## P-211b — Render-time student-facing filter for cluster lesson body

**Filed:** 2026-05-02.
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Priority:** Medium.
**Parent:** P-211.

P-211 ingests cluster `lesson_markdown` verbatim from the authored docs, including author meta-notes that are not student-facing — e.g. `## Why most students fail this in production`, `## Authoring notes (for Chadi, not for the student)`, `## Spiral connection (where this cluster comes back)`. The decision was: keep the source intact in the DB and decide what to render at the UI layer.

**Trigger:** when the cluster detail view (P-234) is implemented.

**Scope:** define the filter contract — either a section-heading denylist applied client-side, or a markdown delimiter pattern (`<!-- author -->`, `<!-- student -->`) that the authoring side starts emitting. Land filter logic in the frontend renderer; backend stays pristine.

---

## P-220.z — Per-question illustrations and pastels (Phase 1 polish)

**Filed:** 2026-05-02.
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Priority:** Post-launch P1.
**Source:** P-220 FE rebuild plan-first.
**Depends on:** P-220 (FE rebuild).

**Scope:** author or commission per-question illustrations + pastel backgrounds for the 11 onboarding questions. The P-220 FE rebuild cycles the existing 6 illustrations/pastels as a placeholder; this ticket replaces them with question-specific assets.

**Owner:** Chadi (illustrations or commissioning) + Engineering (wire-up).

**Trigger:** post-launch, when visual polish becomes priority over functional shipping.

---

## P-241 — Cluster-level prescription

**Filed:** 2026-05-01.
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Phase:** Phase 1 Architecture Rework.
**Source:** LEMETHODIC-CURRICULUM v0.2 §10.

Backend scope: engine logic for cluster-level prescriptions feeding P-240. Stub — full spec in `lemethodic-frontend/LEMETHODIC-CURRICULUM.md`.

---

## P-250 — Threshold calibration

**Filed:** 2026-05-01.
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Phase:** Phase 1 Architecture Rework.
**Source:** LEMETHODIC-CURRICULUM v0.2 §10.

Backend scope: calibration tooling for tuning detector / scoring thresholds against real data. Stub — full spec in `lemethodic-frontend/LEMETHODIC-CURRICULUM.md`.

---

## P-251 — Lesson content delivery infrastructure

**Filed:** 2026-05-01.
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Phase:** Phase 1 Architecture Rework.
**Source:** LEMETHODIC-CURRICULUM v0.2 §10.

Backend scope: storage + serve endpoints for lesson content. Stub — full spec in `lemethodic-frontend/LEMETHODIC-CURRICULUM.md`.

---

## B-101 — Legal entity decision

**Filed:** 2026-04-30.
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Priority:** Medium.

Stub — spec TBD.

---

## B-104 — Email marketing infrastructure

**Filed:** 2026-04-30.
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Priority:** Medium.

Stub — spec TBD.

---

## B-105 — Analytics setup

**Filed:** 2026-04-30.
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Priority:** Medium.

Stub — spec TBD.

---

## M-102 — Convert Preply reviews to social proof

**Filed:** 2026-04-30.
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Priority:** Medium.

Stub — spec TBD.

---

## M-107 — Express Entry Discord/Telegram outreach

**Filed:** 2026-04-30.
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Priority:** Medium.

Stub — spec TBD.

---

## M-108 — Beta user testimonial pipeline

**Filed:** 2026-04-30.
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Priority:** High.

Stub — spec TBD.

---

# Post-launch P2 — signal-driven

## P-102 — Visual quality pass

**Filed:** 2026-04-30.
**Status:** Queued.
**Tag:** Post-launch P2 — signal-driven (defer until real signal).

**Priority:** Medium (post-launch).

Tailwind UI template, ~$300 budget. Stub — spec TBD.

---

## P-103.1 — Optional: tighter audio cap + duration enforcement

**Filed:** 2026-05-01.
**Status:** Queued.
**Tag:** Post-launch P2 — signal-driven (defer until real signal).

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
**Tag:** Post-launch P2 — signal-driven (defer until real signal).

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

## P-109 — TCF Canada speaking simulator MVP

**Filed:** 2026-04-30.
**Status:** Queued.
**Tag:** Post-launch P2 — signal-driven (defer until real signal).

**Priority:** High (pre-launch).

Stub — spec TBD.

---

## P-210.1 — Per-persona path forking

**Filed:** 2026-05-01.
**Status:** Queued (deferred until validated demand).
**Tag:** Post-launch P2 — signal-driven (defer until real signal).

**Priority:** Low.
**Parent:** P-210.

When a second persona with materially different cluster sequencing emerges (e.g. foundation persona requiring slower B1.1 phase, or job-prep persona requiring different vocabulary themes), fork the `b1_to_b2` path into per-persona variants. Migration: add `b1_to_b2_visa_urgent` / `b1_to_b2_foundation` / `b1_to_b2_general`, or repurpose the existing `b1_to_b2` entry. Decide format (multiple Path rows vs Path-with-variants column) at filing time.

**Trigger:** real demand from beta users in non-visa-urgent personas, or pedagogical decision that the paths must materially differ.

Currently the schema has one `b1_to_b2` path serving the visa-urgent persona (seeded by P-210, `scripts/seed_b1_b2_path.py`). Personalization for other personas happens at runtime via dashboards, prompts, and copy — not via separate paths. Acceptable for Phase 1.

---

## P-211a — Normalize marker_id format in source cluster docs

**Filed:** 2026-05-02.
**Status:** Queued.
**Tag:** Post-launch P2 — signal-driven (defer until real signal).

**Priority:** Low.
**Parent:** P-211.

The 4-segment canonical format `{level}.{phase_num}.C{cluster_num}.{letter}` is locked backend-side (schema + Pydantic). Two clusters in `lemethodic-frontend/curriculum/clusters/B1.1-clusters-1-and-2.md` (Cluster 1, Cluster 2) use the legacy 3-segment form (`B1.1.a`, `B1.2.a`). The P-211 ingest auto-rewrites them at parse time and emits a loud warning summary, but the source docs should be normalized so authoring drift doesn't accumulate.

**Trigger:** when frontend cluster docs get a v0.2 pass (or any other authoring touch on the B1.1 file).

**Scope:** rewrite 10 marker references inline in `B1.1-clusters-1-and-2.md`. Re-vendor to `docs/clusters/`. Rerun ingest with `--force` to confirm no rewrites surface in the summary banner.

---

## P-211c — Vocabulary theme assignment pass

**Filed:** 2026-05-02.
**Status:** Queued.
**Tag:** Post-launch P2 — signal-driven (defer until real signal).

**Priority:** Low.
**Parent:** P-211 (also touches P-210).

P-210 (path seed) and P-211 (content ingest) both leave `cluster.vocabulary_theme_id = NULL` on all 22 B1→B2 clusters. The 27 vocabulary themes are seeded in `vocabulary_themes` by the P-202 migration; the cluster→theme mapping isn't authored yet. Pedagogical decision per cluster: which `vocabulary_themes.slug` contextualizes its grammar topic (e.g. B1.3.C13 "Expression de la cause" → likely `debats_opinions`; B1.2.C7 "Y et EN" → cross-cutting, may legitimately stay NULL).

**Trigger:** post-Phase 1, once theme-driven UX surfaces (theme filters on the recordings list, theme-grouped progress views) are designed and need a real cluster→theme mapping to drive them.

**Scope:** Chadi-led mapping pass producing a `cluster_slug → theme_slug` table (or NULL); short SQL UPDATE batch keyed by slug. No schema change — column is already nullable per the P-202 design call.

---

## P-220.x — Onboarding routing engine (full)

**Filed:** 2026-05-02.
**Status:** Queued.
**Tag:** Post-launch P2 — signal-driven (defer until real signal).

**Priority:** Medium (post-launch, signal-driven).
**Parent:** P-220.

P-220 ships the questionnaire schema + endpoints + stub routing logic for Q1+Q2 (path slug) and Q11 (UI mode). Q4-Q10 answers are stored on the user record but do not yet drive any backend behavior — see `# TODO P-220.x` comments in `app/routers/onboarding.py::submit_onboarding`.

This ticket concretizes routing for the remaining 6 effects:
- Q4 (motivation) → vocabulary theme priority weighting
- Q5 (strongest skill) → diagnostic emphasis (record vs write first; speaking-first when strong-in-speaking, etc.)
- Q6 (weakest skill blocker type) → cluster prioritization within path (which clusters surface first on the dashboard)
- Q8 (topics tested on) → cluster prioritization, theme-filtered diagnostic prompts
- Q9 (native language) → L1 detector calibration (Phase 2 — no-op until non-English detectors exist)
- Q10 (prior exam history) → credibility-of-self-assessment signal feeding the diagnostic confidence score

**Trigger:** beta cohort signups produce real distribution of answers + the §7 dashboard work commits to a cluster-prioritization mechanism (re-order vs overlay vs sort).

**Depends on:** P-221 (diagnostic flow), P-234 (cluster detail view).

**Estimate:** 2-3 days once dependencies land.

---

## P-220.y — Notification scheduling (Q12 reminder time)

**Filed:** 2026-05-02.
**Status:** Queued.
**Tag:** Post-launch P2 — signal-driven (defer until real signal).

**Priority:** Low (deferred until notification infrastructure exists).
**Parent:** P-220.

§8.3 originally listed Q12 ("daily reminder time preference") as part of the questionnaire. P-220 omitted it entirely — there's no notification infrastructure to plug a `reminder_time` value into yet (no email/push/SMS sender, no scheduling worker, no quiet-hours logic).

When notifications ship as a feature, this ticket adds:
- `reminder_time` column on `users` (TIME, nullable)
- Q12 question + options in `app/services/onboarding_questions.py`
- `q12_reminder_time` field on `OnboardingSubmitRequest` Pydantic model
- Wiring into the notification sender

**Trigger:** notification infrastructure exists (separate ticket, currently unfiled).

**Estimate:** 30 min once the sender exists.

---

## M-106 — Blog launch

**Filed:** 2026-04-30; deferred 2026-05-02.
**Status:** Queued (deferred with explicit trigger).
**Tag:** Post-launch P2 — signal-driven (defer until real signal).

**Priority:** Medium.

**Trigger:** 3+ months post-launch, sustained traction, revenue justifying content investment. The long-tail SEO payoff is real but takes 6-12 months to compound — investing pre-launch competes with YouTube (M-103) and Reddit (M-104) for solo founder time without faster returns.

**Scope (when triggered):** SEO'd long-form content targeting visa-urgent search terms ("TCF Canada Tâche 3 examples", "Express Entry French requirements", "B1 to B2 in 3 months"). Repurpose YouTube anchor video transcripts where applicable.

Stub — full spec TBD when trigger fires.

---

# Phase 2 / deferred indefinitely

## P-260 — Writing analysis pipeline

**Filed:** 2026-05-01.
**Status:** Queued.
**Tag:** Phase 2 / deferred indefinitely.

**Phase:** Phase 2 (post-launch).
**Source:** LEMETHODIC-CURRICULUM v0.2 §10.

Backend scope: writing-track analysis pipeline. Stub — full spec in `lemethodic-frontend/LEMETHODIC-CURRICULUM.md`. Scope overlaps with P-300 (Writing pedagogy build) — reconcile when both specs exist.

---

## P-262 — Cross-modal prescription

**Filed:** 2026-05-01.
**Status:** Queued.
**Tag:** Phase 2 / deferred indefinitely.

**Phase:** Phase 2 (post-launch).
**Source:** LEMETHODIC-CURRICULUM v0.2 §10.

Backend scope: prescription that draws across modalities (oral + writing). Stub — full spec in `lemethodic-frontend/LEMETHODIC-CURRICULUM.md`.

---

## P-266 — Phase 2 detectors

**Filed:** 2026-05-01.
**Status:** Queued.
**Tag:** Phase 2 / deferred indefinitely.

**Phase:** Phase 2 (post-launch).
**Source:** LEMETHODIC-CURRICULUM v0.2 §10.

Backend scope: detectors specific to Phase 2 modalities. Stub — full spec in `lemethodic-frontend/LEMETHODIC-CURRICULUM.md`.

---

## Frontend-only curriculum tickets (P-222, P-230..P-237, P-261, P-267..P-269)

See `lemethodic-frontend/BACKLOG.md` for full roster. No backend scope.

---

## Phase 2 expansion (renumbered from P-200..P-203)

Renumbered 2026-05-01 to free P-200..P-269 for Phase 1 Architecture Rework. See `lemethodic-frontend/LEMETHODIC-CURRICULUM.md` v0.2 §10.

---

## P-300 — Writing pedagogy build

**Filed:** 2026-04-30 (renumbered from P-200 on 2026-05-01).
**Status:** Queued.
**Tag:** Phase 2 / deferred indefinitely.

**Priority:** High (Phase 2, post-launch).

Analysis prompts + 5-criterion scoring + diagnostic surface for the
writing track. Stub — spec TBD. Scope overlaps with curriculum P-260 (Writing analysis pipeline) — reconcile when both specs exist.

---

## P-301 — TEF exam support

**Filed:** 2026-04-30 (renumbered from P-201 on 2026-05-01).
**Status:** Queued.
**Tag:** Phase 2 / deferred indefinitely.

**Priority:** Medium (Phase 2, post-launch).

Multi-exam routing (F-091) + TEF-specific prompts + TEF scoring
rubric. Stub — spec TBD.

---

## P-302 — DELF exam support

**Filed:** 2026-04-30 (renumbered from P-202 on 2026-05-01).
**Status:** Queued.
**Tag:** Phase 2 / deferred indefinitely.

**Priority:** Medium (Phase 2, post-launch).

Stub — spec TBD.

---

## P-303 — Italian-audience expansion

**Filed:** 2026-04-30 (renumbered from P-203 on 2026-05-01).
**Status:** Queued.
**Tag:** Phase 2 / deferred indefinitely.

**Priority:** Low (Phase 2, post-launch).

Per Chadi's noted interest in Italian-speaking French learners.
Stub — spec TBD.

---

## F-077.x — Convert JSON-as-Text columns to JSONB

**Filed:** F-077 (PostgreSQL local-dev parity), 2026-04-27.
**Status:** post-launch.
**Tag:** Phase 2 / deferred indefinitely.


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
**Tag:** Phase 2 / deferred indefinitely.


Replace `boto3` synchronous calls in `app/services/storage.py` with `aioboto3` async equivalents. boto3's `put_object` / `get_object` / `head_object` block the event loop during the round-trip (~50–200 ms per call on Spaces). At soft-beta scale (5–10 concurrent users) this is fine — typical session has 1 upload every 30–60 s. Past ~10 simultaneous uploads it serializes and tail latency starts climbing.

**Scope:**
- Add `aioboto3` to `requirements.txt`.
- Promote `write_bytes` / `read_bytes` / `exists` / `stream_response` to `async def` in the Spaces branch; the local-disk branch can stay sync (it's already cheap).
- Update every caller — tts.py is already async; the four upload routes are already async; `/tts_audio` handler is currently sync (`def`) and needs `async def` if it goes through the async branch. Only ~6 sites total.
- Streaming reads (`stream_response`) should switch from `read_bytes()`-then-`Response(content=...)` to FastAPI's `StreamingResponse` so a 5 MB file doesn't sit fully in memory before the response starts.

**Estimate:** 2–3h.

**Out of scope:** lifecycle policies on Spaces (separate post-launch ticket — orphaned upload cleanup, TTS cache eviction).

---

## F-111 — Investigate DO Spaces Limited Access key `InvalidArgument`

**Filed:** 2026-04-30.
**Status:** post-launch.
**Tag:** Phase 2 / deferred indefinitely.


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

## B-103 — Trademark research on "LeMethodic"

**Filed:** 2026-04-30.
**Status:** Queued.
**Tag:** Phase 2 / deferred indefinitely.

**Priority:** Low.

Stub — spec TBD.

---

# Closed

## M-105 — LinkedIn long-form content

**Filed:** 2026-04-30; closed 2026-05-02.
**Status:** Closed — decided not to pursue. LinkedIn is the wrong audience for the visa-urgent persona; the B2B angle (immigration consultants / employer-sponsored TCF prep) is not a current channel and not a priority.
**Tag:** Closed — decided not to pursue.

**Re-open trigger:** B2B angle becomes a real channel (e.g., immigration-consultant referral pipeline material).

Original priority was Medium. Decided not to pursue per 2026-05-02 marketing triage — solo founder bandwidth is the binding constraint, and Reddit (M-104) + YouTube (M-103) cover the visa-urgent persona at lower cost with better audience fit.

---

# Shipped

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

## P-202 — Cluster data model

**Filed:** 2026-05-01.
**Status:** Shipped 2026-05-01 (commit `d5595b3`).
**Phase:** Phase 1 Architecture Rework.
**Source:** LEMETHODIC-CURRICULUM v0.2 §10.

Backend scope: SQLAlchemy + Alembic schema for the cluster concept. Migration `a8f3e2c4b5d1` created `clusters`, `vocabulary_themes` (seeded with 27 §5.1 themes), with JSONB i18n labels and the prose-faithful `DetectionRubric` shape (relaxed in commit `11a175d` for P-211 ingest).

---

## P-203 — Path data model

**Filed:** 2026-05-01.
**Status:** Shipped 2026-05-01 (commit `d5595b3`).
**Phase:** Phase 1 Architecture Rework.
**Source:** LEMETHODIC-CURRICULUM v0.2 §10.

Backend scope: SQLAlchemy + Alembic schema for the path concept (sequence of clusters). Migration `a8f3e2c4b5d1` created `paths`, `phases`, and `path_clusters` (join + ordering, with `is_optional` for persona compression).

---

## P-204 — User progress model

**Filed:** 2026-05-01.
**Status:** Shipped 2026-05-01 (commit `d5595b3`).
**Phase:** Phase 1 Architecture Rework.
**Source:** LEMETHODIC-CURRICULUM v0.2 §10.

Backend scope: SQLAlchemy + Alembic schema tracking per-user progress through clusters and paths. Migration `a8f3e2c4b5d1` created `user_path_enrollments` (with partial unique index for one-active-enrollment-per-user), `user_cluster_statuses` (snapshot), and `user_cluster_events` (append-only log with `(user_id, created_at)` composite index for Block 7 Mistake Repository).

---

## P-210 — B1→B2 path seed (1 path, 5 phases, 22 cluster slots)

**Filed:** 2026-05-01.
**Status:** Shipped 2026-05-01 (commit `79cd629`); production seeded same-day via `scripts/seed_b1_b2_path.py` against the prod DB.
**Phase:** Phase 1 Architecture Rework.

Idempotent one-shot seed. Cluster slugs follow the 4-segment marker convention (`B1.1.C1` .. `B1.5.C22`) so a marker_id like `B1.1.C1.a` maps cleanly back to its cluster. Lesson content, exercise sets, practice prompts, detection rubrics, and vocabulary theme assignments left empty — populated by P-211. See `scripts/seed_b1_b2_path.py`. Per-persona path forking deferred to P-210.1.

---

## P-211 — Cluster content authoring

**Filed:** 2026-05-01.
**Status:** Shipped 2026-05-01 (commit `d862794`); production ingested same-day via `scripts/ingest_b1_b2_cluster_content.py` against the prod DB.
**Phase:** Phase 1 Architecture Rework.
**Source:** LEMETHODIC-CURRICULUM v0.2 §10.

Backend scope: data ingestion infrastructure for authoring cluster content. Parses the 4 vendored cluster docs in `docs/clusters/` (synced from `lemethodic-frontend/curriculum/clusters/`); for each of the 13 authored clusters writes `lesson_markdown`, `practice_prompt`, `detection_rubric` (prose-faithful per the relaxed schema), and updates `tache_application` to match the authored prompt header (7 of 13 flip from the seed default). The 9 placeholder clusters (B1.4 + B1.5) get a placeholder string. Ten markers in 2 clusters (B1.1.C1, B1.1.C2) auto-rewritten from legacy 3-segment to canonical 4-segment, with a loud warning summary — source-doc fix tracked in P-211a.

---

## P-212 — Starter cluster seed

**Filed:** 2026-05-01; superseded 2026-05-02.
**Status:** Superseded by P-210 + P-211 (shipped 2026-05-01). The 22-cluster B1→B2 path is in production with 13 clusters fully authored and 9 placeholders pending Les Moules content. Nothing in P-212's original scope remains uncovered.

**Phase:** Phase 1 Architecture Rework.
**Source:** LEMETHODIC-CURRICULUM v0.2 §10.

Original scope (preserved for history): backend seed script populating the starter cluster set for soft-beta launch. Now covered by P-210 (`scripts/seed_b1_b2_path.py`, commit `79cd629`) for the 1 path / 5 phases / 22 cluster slots, and P-211 (`scripts/ingest_b1_b2_cluster_content.py`, commit `d862794`) for content. Both running against production.

---

