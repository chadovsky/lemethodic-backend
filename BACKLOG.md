# BACKLOG.md

**Last updated:** 2026-05-15 (data-layer sweep — D-001..D-014 closed, D-020..D-025 in flight, Phase 2/3 placeholders added).
**Phase 1 Architecture Rework** — see `lemethodic-frontend/LEMETHODIC-CURRICULUM.md` v0.2.

Active and deferred work tracking. Tickets are organized by **Tag** —
the section a ticket lives in matches its `**Tag:**` line. Section
ordering: Active → P1 → P2 → Deferred → Closed → Shipped. The Active
Queue summary at the top of this file reproduces only the launch-critical
slate in priority order; bodies live below.

Re-runnable via `scripts/regen_backlog.py` — change classification
constants there and regenerate.

---

## NOTES — Data Layer field findings (2026-05-15)

Cross-cutting findings from the D-001..D-025 session. Captured here so future
agents don't rediscover them the hard way.

1. **PARSEME corpus pivot.** `gitlab.com/parseme/parseme_corpus_fr` does not
   exist — the live data lives at `gitlab.com/parseme/sharedtask-data` under
   `1.2/FR/`. The repo also gates anonymous clones in some regions. Workaround:
   a fake `.git` directory under `data-layer/raw/parseme/fr/` so the auto-clone
   step is skipped and the manually-fetched `.cupt` files are used in place.
   8,196 chunks landed after the synthetic-fixture purge.

2. **UniversalCEFR FR dataset.** Earlier agent assumption was that
   `cefr_sp_fr` was the French slice — it is not. That dataset is English-only
   (Arase 2022 EMNLP). The actual French resource is `readme_fr` (~1,670 rows).
   Re-ingest after the swap delivered 1,336 French chunks.

3. **Synthetic fixtures masquerading as real data.** PARSEME (D-010) and
   Tatoeba (D-014) both shipped with synthetic fixtures wired into the live
   ingest path, so early row counts were lying. Pattern to watch for: a
   `tests/generate_*_fixture.py` whose output gets read by the production
   parser. Fix in both cases was `DELETE FROM chunks WHERE source = '<src>'`
   followed by a clean re-ingest against the real corpus.

4. **Groq selected as the enrichment LLM.** Llama 3.3 70B via Groq's
   OpenAI-compatible endpoint — chosen for cost + throughput vs. Claude for
   the bulk-classification enrichment pass. API key stored in
   `data-layer/.env` (gitignored). One key was briefly exposed during a
   diagnostic dump and rotated post-exposure; rotation is captured in the
   D-021 history.

---

## Active Queue — Launch Critical (before soft beta launches)

In stated priority order. Full ticket bodies live below in the "Active — Launch Critical" section.

| # | Ticket | Title |
|---|---|---|
| 1 | **F-225** | Desktop verification protocol |
| 2 | **F-222** | Sign Out bug fix |
| 3 | **F-200** | Landing page desktop layout |
| 4 | **F-201** | Onboarding flow desktop layout |
| 5 | **F-202** | /ecole + L'École intro rebuild (responsive + content + methodology demo) |
| 6 | **F-203** | /progress dashboard desktop + responsive layout |
| 7 | **P-230.depth** | /progress real content for soft beta |
| 8 | **F-204** | /cluster/[slug] desktop layout |
| 9 | **F-205** | /speaking/* (Tâche surfaces) desktop layout |
| 10 | **F-206** | Auxiliary pages desktop (privacy/terms/refund/waitlist/signup) |
| 11 | **F-220** | Onboarding "intro framing" (Block 3 quiz-pop-up entry moment) |
| 12 | **F-221** | Exam-selector in onboarding + brand-layer rewrite |
| 13 | **V-009** | CouchesDiagnostic radar: 5-axis + brand labels |
| 14 | **V-010** | /ecole phase structure correction |
| 15 | **V-013** | Pre-launch surface completeness |
| 16 | **V-015** | Post-V-013 critical fixes + desktop redesign |
| 17 | **V-016** | Post-V-015 fixes (6 sub-tickets) |
| 18 | **F-300** | Platform repositioning + Store |
| 19 | **V-005** | Font system upgrade |
| 20 | **V-001** | Hero H1 + rotating kicker sizing |
| 21 | **V-002** | Em-dash strip across FE copy |
| 22 | **V-003** | Hero atmospheric typographic animation |
| 23 | **V-004** | Differentiation cards rebuild (Codersera-grade) |
| 24 | **V-011** | FinalCTA centering + color refresh |
| 25 | **F-210** | Icon system + custom LeMethodic icons |
| 26 | **F-211** | Loading states overhaul |
| 27 | **F-212** | Micro-animations + interaction feedback |
| 28 | **F-213** | Page transitions + motion design |
| 29 | **F-214** | Visual depth + design system extension |
| 30 | **P-234** | Cluster detail view |
| 31 | **P-105** | [M5.5] [P0] Server-side tier enforcement |
| 32 | **F-401** | [M5.5] [HIGH] Rate limiting on AI endpoints |
| 33 | **F-402** | [M5.5] [PERF] FK indexes |
| 34 | **F-403** | [M5.5] [SCALING] N+1 fixes |
| 35 | **P-106** | Stripe integration (subscription + one-time + Premium SKU) |
| 36 | **B-100** | Stripe via US LLC formation (Stripe Atlas) |
| 37 | **M-103** | YouTube anchor video -- French exam prep for English speakers |
| 38 | **M-104** | Reddit community engagement (broadened subreddit list) |
| 39 | **F-310** | Auth hardening (BE + FE) -- BE SHIPPED 2026-05-12; FE work remains |
| 40 | **F-311** | Token control infrastructure (BE) -- SHIPPED 2026-05-12 |
| 41 | **F-312** | RAG retrieval layer (BE) -- CC corpus + Chadi-authored (Path C, rescoped 2026-05-12) |
| 42 | **F-312.0** | RAG licensing pre-flight -- CLOSED 2026-05-12 (Path C selected) |
| 43 | **F-330** | Le Vocabulaire system (parent + V2 enumeration) (added 2026-05-12) |
| 44 | **F-320** | Le Vocabulaire DB schema (BE) (added 2026-05-12) |
| 45 | **F-321** | Le Vocabulaire Phase 1 seed -- Chadi tutoring artifacts (Path C, rescoped 2026-05-12) |

**Tickets 31-34 (added 2026-05-31 M5.5 BE audit):** P-105 rescoped from 7-day trial logic to standalone tier enforcement; F-401/402/403 newly filed. Slot positions reflect pre-revenue priority order. **M5.5 fully SHIPPED 2026-05-31** (P-105 8b59c07, F-402 a18c0dc, F-403 a487799, F-401 e32f36e).

**Tickets 39-45 (added 2026-05-12 strategic session):** slot positions pending Chadi triage. F-310 + F-311 are pre-launch blockers per Decision 4 -- should reorder toward the top of the queue when triage runs. F-322 / F-323 / F-324 (Le Vocabulaire FE + Diagnostic-Vocab link) filed under Post-launch P1 with Sprint-2 priority.

---
# Active — Launch Critical (42 tickets, before soft beta launches)

## F-225 — Desktop verification protocol
Milestone: DONE

**Filed:** 2026-05-04.
**Status:** Awaiting Verification (FE-side process gate landed 2026-05-04; protocol now enforced — first FE PRs going forward will exercise the 1440px + 375px screenshot requirement). Pattern (a) per Chadi 2026-05-04: the gate governs the **Awaiting Verification → Shipped** transition, not the push.
**Tag:** Active — Launch Critical (before soft beta launches).

**Priority:** HIGH (process — gates all FE PRs).

Process change driven by the soft-beta review surfacing universal mobile-only / desktop-broken state. Going forward:

- Every FE PR must include screenshot evidence at **1440px viewport** before approval.
- PR template adds a "Desktop verified at 1440px? [Y/N]" checkbox.
- CI step (Playwright snapshot OR lighthouse-ci) for any `app/**` change captures the affected route at 1440px and posts to the PR.
- Reviewer checklist includes: "Verified at 1440px? Y/N" — N blocks merge.

No more shipping mobile-only as "ready."

**Owner:** FE lead (PR template + CI wiring).

---

## F-222 — Sign Out bug fix
Milestone: M1

**Filed:** 2026-05-04.
**Status:** Awaiting Verification (FE-side fix delivered 2026-05-04; 1440px + 375px screenshots + interactive trace pending per F-225).
**Tag:** Active — Launch Critical (before soft beta launches).

**Priority:** Medium.

Sign Out flow has a bug — investigate + fix. Specifics TBD on triage; likely cookie-clear or redirect-loop issue (auth cookie set via `set_cookie("access_token", ..., httponly=True, samesite="lax")` on the API host; FE sign-out must hit a logout endpoint that clears cookie, then redirect home).

**Owner:** FE (likely; BE may need a `POST /auth/logout` endpoint if not present).

---

## F-200 — Landing page desktop layout
Milestone: M1

**Filed:** 2026-05-04 (BACKLOG restructure — soft-beta definition lock).
**Status:** Queued.
**Tag:** Active — Launch Critical (before soft beta launches).

**Priority:** HIGH (soft-beta requires platform fully responsive).

Landing page (`/`) currently mobile-only with white rails on desktop. Build the desktop layout: proper grid, full-width hero, multi-column pricing cards, footer that doesn't read as a stretched phone screen.

**Owner:** FE.
**Verification:** screenshot evidence at 1440px viewport per F-225.

---

## F-201 — Onboarding flow desktop layout
Milestone: M1

**Filed:** 2026-05-04.
**Status:** Queued.
**Tag:** Active — Launch Critical (before soft beta launches).

**Priority:** HIGH.

`/onboarding` (the 11-question flow) is mobile-only. Build the desktop layout: centered card on desktop with breathable margins, question-illustration pairing where applicable, no stretched phone aesthetic.

**Owner:** FE.
**Verification:** screenshot evidence at 1440px per F-225.

---

## F-202 — /ecole + L'École intro rebuild (responsive + content + methodology demo)
Milestone: M1

**Filed:** 2026-05-04.
**Status:** Queued.
**Tag:** Active — Launch Critical (before soft beta launches).

**Priority:** HIGH (soft-beta requires methodology visible in-product).

Rebuild `/ecole` and the L'École intro screen. Currently empty placeholder; doesn't hit the Promova visual benchmark locked in Block 3.

Required:
- Real intro content showcasing La Méthode en Couches with concrete examples (annotated transcript snippets, before/after corrections).
- Demonstrate methodology in-product, not just in marketing copy.
- Full responsive layout (mobile + desktop both first-class).
- Visual identity at Promova-bench level.

**Owner:** FE + Chadi (intro copy + example transcripts).
**Verification:** screenshot evidence at 1440px per F-225.

---

## F-203 — /progress dashboard desktop + responsive layout
Milestone: M1

**Filed:** 2026-05-04.
**Status:** Queued.
**Tag:** Active — Launch Critical (before soft beta launches).

**Priority:** HIGH.

P-230 v1 shipped 2026-05-03 (FE 3-commit set 28bf765) with the structural skeleton but is mobile-only. Build the desktop layout — multi-column dashboard grid, larger Snapshot block, side-by-side Goulet Stack and Recent Activity. Pairs with **P-230.depth** which scopes the content rebuild specifically.

**Owner:** FE.
**Verification:** screenshot evidence at 1440px per F-225.

---

## P-230.depth — /progress real content for soft beta
Milestone: M1

**Filed:** 2026-05-04 (split from P-230 v1 ship — depth deemed insufficient for soft-beta).
**Status:** Queued.
**Tag:** Active — Launch Critical (before soft beta launches).

**Priority:** HIGH.

P-230 v1 (FE 3-commit set ending 28bf765, 2026-05-03) shipped the structural skeleton: Snapshot, Today's focus, Goulet Stack, Recent activity. Soft-beta review 2026-05-04 flagged content depth as insufficient — sections render but feel placeholder-y.

Depth work needed:
- **Snapshot:** full Confidence Visualizer (Block 8) — not just CEFR letter, but the actual confidence interval visualization (`assigned.confidence` + `coverage` + `total_clusters_in_path` rendered as a band, not a chip).
- **Today's focus:** richer reason-code-driven copy until P-240b (Dialogue Box prose) lands. Each `reason_code` gets a per-Tâche-application-specific message variant.
- **Goulet Stack:** top-3 bottlenecks rendered with detected examples (transcript snippets) + suggested next-action per bottleneck.
- **Recent activity:** per-recording summaries (Tâche, length, top finding) — not just timestamps.

Pairs with **F-203** (desktop responsive layout for the same surface — different concern, same screen).

**Owner:** FE + Chadi (content authoring for example snippets + bottleneck copy).
**Depends on:** existing BE endpoints (`/me/level`, `/me/today`, `/me/recurring_modules` — all live).

---

## F-204 — /cluster/[slug] desktop layout
Milestone: M1

**Filed:** 2026-05-04.
**Status:** Queued.
**Tag:** Active — Launch Critical (before soft beta launches).

**Priority:** Medium-high.

Cluster detail page consumes the BE endpoints shipped in P-234. FE consumer is in progress; ensure the desktop layout is first-class — sidebar (lesson nav?) + content column, lesson markdown rendered with reading-width constraint, exercise pane next to lesson.

**Owner:** FE.
**Verification:** screenshot evidence at 1440px per F-225.

---

## F-205 — /speaking/* (Tâche surfaces) desktop layout
Milestone: M1

**Filed:** 2026-05-04.
**Status:** Queued.
**Tag:** Active — Launch Critical (before soft beta launches).

**Priority:** HIGH (Tâche surfaces are the core practice flow).

`/speaking/tache-1`, `/speaking/tache-2`, `/speaking/tache-3` and their session sub-routes are mobile-only. Build the desktop layout for each — recording panel + prompt panel side-by-side, transcript review ergonomics on a larger viewport, mic button doesn't stretch oddly.

**Owner:** FE.
**Verification:** screenshot evidence at 1440px per F-225.

---

## F-206 — Auxiliary pages desktop (privacy/terms/refund/waitlist/signup)
Milestone: M1

**Filed:** 2026-05-04.
**Status:** Queued.
**Tag:** Active — Launch Critical (before soft beta launches).

**Priority:** Medium.

Smaller-surface pages still mobile-only:
- `/privacy`, `/terms`, `/refund` (B-102 ship — content correct, layout cramped on desktop).
- `/onboarding/waitlist` (P-222 ship — desktop layout).
- `/signup`, `/login` (existing auth surfaces).

Reading-width constraint on policy pages; centered cards on auth pages.

**Owner:** FE.
**Verification:** screenshot evidence at 1440px per F-225.

---

## F-220 — Onboarding "intro framing" (Block 3 quiz-pop-up entry moment)
Milestone: M1

**Filed:** 2026-05-04.
**Status:** Queued.
**Tag:** Active — Launch Critical (before soft beta launches).

**Priority:** HIGH.

Block 3 strategy lock-in: onboarding should feel like a "seamless quiz pop-up entry moment" not a clinical 11-question form. Add a 1-screen intro framing the questionnaire ("Let's understand where you are. 11 quick questions, ~3 minutes, then a 3-recording diagnostic.") with personality + Chadi voice.

Reduces perceived friction at the threshold; sets expectation for the diagnostic stage immediately after.

**Owner:** FE + Chadi (intro copy in FR + EN).

---

## F-221 — Exam-selector in onboarding + brand-layer rewrite
Milestone: M1

**Filed:** 2026-05-04.
**Status:** **BE-side Awaiting Verification** — v2 commit `39954b2` (alembic `f3a4b5c6d7e8`) realigns to FE-locked 5-slug domain (commit 21a7edc). Supersedes v1 (`1dda6e9`, alembic `e1f2a3b4c5d6`). **Production v2 deploy + alembic migration landed 2026-05-05**: `q0_target_exam` required with exact 5-slug enum live; old `target_exam` API field cleanly renamed; `/onboarding/questions` returns 12 questions with q0 leading and q2 carrying `helpers_by_target_exam` (3 variants); q8 copy updated. **FE 21a7edc + BE v2 ready for E2E.** Behavioral verification (real onboarding submissions exercising each routing branch) pending Chadi's batch verification pass.
**Tag:** Active — Launch Critical (before soft beta launches).

**Priority:** HIGH (positioning pivot).

Brand pivot: "TCF prep" → **"French exam prep for English speakers"** (across exams). Routing rules:

- TCF / TEF B1 / B2 → active path (shared format DNA, content reusable).
- DELF B1 / B2 → active path (same DNA).
- DALF C1 / C2, FIDE, AP, DCL → "Coming soon" + email capture (Phase 2 content).

Implementation:
- Add Q-exam-target question to onboarding (slot before Q1 current_level).
- Branch waitlist screen — shared with P-222 plumbing, but copy varies by selected exam.
- Backend: new `target_exam` field on User + UserPathEnrollment (alembic migration); path resolver consumes `target_exam` for Phase 2 exam-specific routing; Phase 1 maps all active exams to b1_to_b2 path.

Marketing layer: TCF/TEF stays as primary entry persona (visa urgency); "all exams covered" sits adjacent in copy.

**Owner:** FE + BE + Chadi (brand copy + exam-route mapping table).
**Depends on:** F-201 (onboarding desktop layout).

---

## V-009 — CouchesDiagnostic radar: 5-axis + brand labels
Milestone: M2

**Status:** Active LC
**Tag:** Active — Launch Critical (before soft beta launches).
**Filed:** 2026-05-05
**Type:** FE methodology-content fix
**Priority:** Ship before any chrome work

**Problem:**
The "Where you stand today" radar chart (CouchesDiagnostic component, surfaces on /diagnostic and likely /paywall) shows 4 axes with generic labels: Content / Structure / Grammar / English Habits.

This contradicts the 5-couche model locked 2026-05-05 (F-202 + F-227 surfaced as moat-made-visible). User journey breaks at this point: onboarding → EcoleReveal → /ecole/intro reads "Five layers compose your French" → CouchesDiagnostic radar shows 4 axes with old generic labels. Methodology contradicts itself in-product.

**Fix:**
- Add 5th axis to radar: La Voix (Voice)
- Replace generic labels with user-facing brand labels:
  - EN: Range / Coherence / Accuracy / Fluency / Voice
  - FR: Étendue / Cohérence / Correction / Aisance / Voix
- Preserve current visual chrome (pink-peach fill, dashed outline, rounded card) — chrome migration stays in F-205.deep
- BE side: ensure the diagnostic feedback API returns 5 couche scores (Le Fond / Les Moules des Idées / Les Moules / Les Réflexes Anglais / La Voix) instead of 4. If BE currently returns 4-axis data, file a parallel BE ticket V-009.be for the API extension. FE side wires up to whatever the BE returns.

**Notes:**
- Visual chrome (radius, shadow, fill color, outline style) stays untouched. This ticket is methodology-content only.
- F-205.deep covers the chrome migration of CouchesDiagnostic when prioritized later.
- If BE doesn't return 5-couche data yet, FE displays the 5th axis as "Voice" with a "Coming soon" or muted state until BE catches up. Surface this in plan-first.

---

### V-009.be — Unify oral analysis surface to 5 couches (BE)
Milestone: M3

**Status:** Shipped 2026-06-01 (4fe3354).
**Tag:** Active — Launch Critical (before soft beta launches).
**Filed:** 2026-05-12 (parallel BE follow-up to V-009 FE; trigger met by V-016a shipping).
**Type:** BE methodology-surface alignment.
**Priority:** Ship after V-016a validates `methode_en_couches` shape in production.

**Trigger:** V-016a ships and the writing-side `methode_en_couches` + top-level `couches` array are validated in prod (smoke green, FE polling consumer renders 5 axes correctly).

**Scope:**
- `app/services/analysis.py` — extend the oral system prompt to score 5 couches (add `la_voix`); rewrite `analyse_par_couche` output shape OR introduce `methode_en_couches` parallel to writing for symmetry. Decide in plan-first which way to migrate (rename vs new key); writing path uses `methode_en_couches`, oral should match.
- `app/services/couche_labels.py` — extend `COUCHE_ORDER` from 4 → 5 by adding `la_voix`; extend `COUCHE_DISPLAY_LABELS` with `{en: "Voice", fr: "Voix"}`. Once unified, retire the writing-local `COUCHE_ORDER` / `COUCHE_DISPLAY_LABELS` / `_extract_couches` in `writing_analysis.py` in favor of the shared helper (drops a duplication that V-016a deliberately accepted as the price of shipping cleanly without cross-coupling).
- Existing `couches_array` callers in `app/routers/recordings.py` start emitting 5 rows automatically — verify FE radar handles the 5th row gracefully (it should already, since V-009 FE was shipped expecting 5 axes).
- Smoke test: extend or add a smoke covering the oral path emitting 5 couches end-to-end.

**Out of scope:** the writing path (already on 5 via V-016a); FE work (covered by V-009 FE).

**Why deferred:**
- V-016a ships first to de-risk the prompt rewrite + Claude scoring of La Voix on a single surface.
- If `la_voix` scores prove unstable in prod (Claude over/under-weights the new dimension), we tune the prompt on writing-only before propagating to oral.
- Once writing is stable, oral migration is a mechanical extension (same prompt pattern, same output shape, same display labels).

**Notes:**
- The writing-local 5-couche helpers in `writing_analysis.py` (`COUCHE_ORDER`, `COUCHE_DISPLAY_LABELS`, `_extract_couches`) are intentionally duplicated from `couche_labels.py`. V-009.be's last step is collapsing them.
- Old oral submissions stored with the 4-couche `analyse_par_couche` shape are pre-soft-beta — acceptable to leave as legacy; no migration script needed.

---

## V-010 — /ecole phase structure correction
Milestone: M1

**Status:** Active LC
**Tag:** Active — Launch Critical (before soft beta launches).
**Filed:** 2026-05-05
**Type:** FE methodology-content fix
**Priority:** Ship before any chrome work

**Problem:**
The /ecole home page shows 3 phase buttons: Fondations (Lessons 1-4) / Approfondissement (Lessons 5-16) / L'École Complète (Lessons 17-27).

This contradicts the curriculum structure locked 2026-05-05 and surfaced on /ecole/intro: **2 phases, Fondations 1-16 + Approfondissement 17-27.**

The current 3-phase structure is residue from the old 16-lesson era with milestones at lessons 4/10/16. When the curriculum expanded to 27 lessons, the phase buttons were never migrated.

**Fix:**
- Replace the 3-button row with 2 buttons:
  - Fondations / Lessons 1-16
  - Approfondissement / Lessons 17-27
- Update the progress bar logic accordingly: "0/27" overall, with phase-level completion fed from the same 27-lesson user state
- Verify the per-button click behavior still routes correctly (each button likely scrolls to or filters lessons in its range)
- Preserve current visual chrome (rounded buttons, padding, layout) — chrome migration stays in F-204.deep
- If milestones at lesson 4/10/16 still exist somewhere as badge triggers, those stay independent — file F-213.celebration (already filed) for the celebration treatment

**Notes:**
- The 3rd button "L'École Complète" was always confusing nomenclature — its range (17-27) overlapped with Approfondissement. Removing it cleanly.
- "L'École Complète" as a concept survives as the **completion state** (the user finishes all 27 lessons), not as a separate phase or surface. F-213.celebration handles the visual treatment of completion.
- F-204.deep covers chrome migration of TodayFocus and other /ecole section internals.

---

## V-013 — Pre-launch surface completeness
Milestone: M1

**Status:** Active LC
**Tag:** Active — Launch Critical (before soft beta launches).
**Filed:** 2026-05-06
**Type:** FE pre-launch blocker

**Problem:**
Production has placeholder/broken surfaces that ship to users:
- `/writing` shows "Coming soon (F-058)" despite F-224 backend live with 14 prompts seeded
- `/more` shows "Coming soon (F-058)" — never implemented
- Bottom nav (École/Speaking/Writing/Progress/More) shows on desktop, leaks mobile UX
- Desktop has no proper top nav — surfaces feel half-built

These are credibility hits for any first-time visitor.

**Three sub-tickets — all FE-only.** BE work for V-013a is already done (F-224 shipped 2026-05-06; endpoints live with 14 v1 prompts on prod).

**Confidence:** HIGH on V-013c direction. MEDIUM on V-013a/V-013b until plan-first surfaces UX details.

---

### V-013a — Wire /writing frontend to F-224 backend
Milestone: M1

- Consume `GET /api/writing/prompts` (14 prompts live, queryable by `tache_level` / `level` / `topic_tag` per F-224 endpoint extension)
- Display prompts library grouped by Tâche level (T1 / T2 / T3 sections; B1 vs B2 within)
- Click prompt → submission form (textarea, word counter against `min_words` / `max_words`, submit)
- `POST /api/writing/submit` → display Claude analysis result (4-layer feedback: Sentence Architecture / Grammatical Accuracy / Lexical Appropriateness / L1 Interference; per `writing_analysis.py`)
- Submission history (basic list view from `GET /api/writing/history/{user_id}`; expand interactions later)
- Render `prompt_fr` for FR users + `prompt_en` for EN users (i18n parallel rendering — both fields now present in API response per F-224)
- For Tâche 3 prompts, the `prompt_fr` body contains `**bold**` markers + `\n\n` paragraph breaks; FE rendering needs to handle (markdown render OR strip-and-paragraph)

### V-013b — Build /more page content
Milestone: M1

- Profile section (avatar, name, exam target from `q0_target_exam`, exam date from `q3_exam_date`)
- Settings (language toggle, current locale from `User.ui_language`)
- Account actions (logout, change password if applicable)
- About (version, support, terms link → `/terms`, privacy link → `/privacy`, refund link → `/refund`)
- Page exists on both mobile + desktop

### V-013c — Nav system overhaul
Milestone: M1

- Bottom nav: gate to `<md` breakpoint (mobile-only)
- Desktop: new `TopNav` component, in-product surfaces
- TopNav direction: **Apple-product-website level polish**
  - Left: LeMethodic logo wordmark
  - Center: École / Speaking / Writing / Progress nav links
  - Right: language toggle + profile avatar with dropdown
  - Sticky, subtle backdrop-blur on scroll, ~56px height
  - Spring hover transitions, ed-warm tint on hover
  - Active state: subtle underline or warm accent
- TopNav appears on in-product surfaces only (not landing `/`, `/fr`)
- Marketing landing nav stays as-is (LeMethodic wordmark + EN/FR toggle)

---

## V-015 — Post-V-013 critical fixes + desktop redesign
Milestone: M1

**Status:** Active LC
**Tag:** Active — Launch Critical (before soft beta launches).
**Filed:** 2026-05-06
**Type:** FE pre-launch blocker + redesign

Four sub-tickets, all FE-only. Surfaced after V-013 first-pass shipped — two correctness bugs (V-015a/b) + two desktop redesigns (V-015c/d) at the Apple-product-website tier.

---

### V-015a — Writing submit 422 fix (FE payload field rename)
Milestone: M1

- BE expects `body.student_text`, FE sends `body.text` → 422 on submit
- One-line fix in `api.writing.submit()` payload — rename `text` → `student_text`
- Reference: `app/routers/writing.py::submit_writing` consumes `SubmitWritingRequest.student_text`

### V-015b — Writing submit gate removal
Milestone: M1

- Currently submit button disabled below `min_words`
- Chadi feedback: word count is a guideline, not a hard gate
- Allow submit at any word count; show "below recommended" warning if under min, but don't disable the button
- BE accepts any non-empty `student_text` (only validates emptiness, not min/max — confirmed in `submit_writing`)

### V-015c — /speaking desktop redesign (full product treatment)
Milestone: M1

- Current state: 3 centered pastel cards (Tâche 1/2/3), narrow mobile-style column
- Chadi feedback: *"rethink this page from A to Z, it's a desktop website, there has to be tabs, useful options, think from a website product point of view"*
- Apple-product-website level layout — full desktop width, tabs/panels, structured content
- Plan-first with 2-3 layout proposals before implementation

### V-015d — /progress desktop redesign
Milestone: M1

- Current state: narrow centered column with Snapshot / Today's Focus / Recent Activity
- Same desktop product treatment needed as V-015c
- Multi-column dashboard, diagnostic progress prominently visible, per-couche scores, activity chart
- Plan-first with 2-3 layout proposals
- BE data already shipped (P-201, P-201.x, P-240, F-080d) — nothing new to wire from BE side

---

## V-016 — Post-V-015 fixes (6 sub-tickets)
Milestone: M1

**Status:** Active LC
**Tag:** Active — Launch Critical (before soft beta launches).
**Filed:** 2026-05-06
**Type:** Mixed (V-016a is BE-urgent; V-016b–f are FE)

Surfaced after V-015 first-pass shipped. V-016a is a production failure (writing submit timing out at 30s) — under investigation, plan-first reply pending. V-016b–f are FE-side polish.

---

### V-016a — Writing submit timeout (BE) — SHIPPED 2026-05-12
Milestone: DONE

**Status:** Shipped 2026-05-12 across three commits:
- `fd54bb8` (2026-05-07) — async writing-job pattern (POST returns 202 + job_id; FE polls GET /api/writing/jobs/{id}) + DO request_timeout stopgap.
- `217f8ea` (2026-05-07) — structured diagnostic logging at every job state transition + Claude-call duration.
- `f3aa23e` (2026-05-12) — full SYSTEM_PROMPT_WRITING rewrite to the 5-couche methodology (La Méthode en Couches); output schema swaps `analyse_par_couche` → `methode_en_couches` with uniform per-couche `{score, examiner_remark_fr, teacher_coaching}` shape; La Voix lit at v1; result_json gains top-level `couches` array for the FE polling consumer. Smoke `smoke_v016a.py` extended with Step 6 verifying the 5-couche surface.

**Root cause:** prompt-size + max_tokens, NOT Sonnet-specific latency. 2026-05-07 triage tested Haiku 4.5 fallback locally — 42.2s on a 55-word B1 sample, LONGER than Sonnet 4's 36.0s on a 97-word sample. Refuted the "Sonnet-specific" hypothesis. Bottleneck is the 3000+ token system prompt + large max_tokens output. Reverted to Sonnet; async-job pattern is the architectural fix.

**Original symptom (history):** user submits writing → 30s wait → Edge "This page couldn't load." V-015a fixed the 422 field name; production fail was downstream timeout.

**Bonus shipped in same line of work:** La Voix definition locked 2026-05-12 (native-French read vs translated-English read across register fit, idiomatic patterns, French rhetorical flow, cultural-fit phrasing, voice consistency). Writing path emits all 5 couches at v1; FE expectation from V-009 (2026-05-05) is met on the writing surface. Oral surface alignment is V-009.be (queued).

**Follow-up:** V-009.be (filed 2026-05-12, queued) — extend oral `analysis.py` to 5 couches, unify writing-local helpers with `couche_labels.py`. Trigger: V-016a validates `methode_en_couches` shape in production.

### V-016b — La Méthode en Couches copy revision (FE)
Milestone: M2

Value-statement copy per couche needs revision. FE-side rewrite.

### V-016c — /ecole desktop redesign (FE — full product treatment, not mobile column)
Milestone: M1

Apple-product-website tier layout. Same treatment as V-015c/d for /speaking + /progress.

### V-016d — Hero kicker amendment (FE)
Milestone: M1

- Bigger size
- Exam name in `--ed-warm-peach-deep`
- Continuous cycle 8-10× or infinite (not stop after 3)

### V-016e — Landing font fix (FE)
Milestone: M2

Switzer not loading on landing `/` — may be V-005 regression. FE investigation + fix.

### V-016f — Differentiation card 1 bars rework (FE)
Milestone: M2

Current 5-bar visualization reads meaningless without labels. Add labels OR replace with alternative typography callout per V-004's spec.

---

## F-300 — Platform repositioning + Store
Milestone: M1

**Status:** Active LC
**Tag:** Active — Launch Critical (before soft beta launches).
**Filed:** 2026-05-06; **detailed spec locked 2026-05-07.**
**Type:** Strategic surface restructure

**Strategic frame:**
LeMethodic positions as French learning platform, not exam prep service. New `/` lands platform-level, current landing moves to `/exam-prep`. New `/library` houses books + free resources for LemonSqueezy product approval.

**Note (BE side flag, unchanged from initial filing):** the strategic justification cites LemonSqueezy approval. Per B-100 (decided 2026-05-04 — Path B Paddle), the active MoR is Paddle, not LemonSqueezy. The 2026-05-07 spec keeps LemonSqueezy framing in F-300e — F-300 may need to reconcile with B-100 (re-flip B-100 to LemonSqueezy with the new product-shaped offering, OR rescope F-300e to Paddle). Surfacing for Chadi triage; not blocking F-300a/b/c/d FE work.

**Tagline locked:**
- H1: "Stop translating. Start producing French."
- Subhead: "The method, the exams, the books — built for English speakers."

**Sequencing:**
F-300b ships first (preserves existing UX during transition), then F-300a (new entry surface), then F-300c-g (store) when product catalog ready.

**Confidence:** HIGH on F-300a/b structure. MEDIUM on F-300c-g (e-commerce design needs plan-first). HIGH that this satisfies LemonSqueezy product-approval requirement (modulo the B-100 reconciliation note).

Strategic Claude drives FE prompts. Most BE work is F-300e (checkout), comes later in chain.

---

### F-300b — Current landing → `/exam-prep` (FE only)
Milestone: M1

- Create `/exam-prep` route
- Copy current `/` page content verbatim to `/exam-prep`
- Audit internal nav: `/signup`, `/onboarding`, `/paywall` flows still target `/exam-prep` funnel context
- Existing `/` preserved temporarily during transition

### F-300a — New `/` platform landing (FE only)
Milestone: M1

- Hero: locked tagline above ("Stop translating. Start producing French.")
- Hero CTA: "Start free diagnostic" → `/onboarding` (preserves existing funnel)
- Product cards section (3 cards):
  - Exam Prep → `/exam-prep`
  - Library → `/library`
  - Free Diagnostic → `/onboarding` (or merge into hero CTA)
- Compressed methodology section (5-couche names only, link to `/exam-prep` for depth)
- Final CTA → `/onboarding`
- Inherit V-012 soft-editorial styling
- Apple-product-website polish (per V-013c TopNav language)

### F-300c — `/library` store surface (FE)
Milestone: M1

- Grid of product cards (books + free resources mixed)
- Filters: format (epub / pdf / print), level (A1 / A2 / B1 / B2), topic
- Search bar
- $0 items badged "Free" — same flow, different price
- Empty state: "Catalog launching soon — pre-order to be notified"

### F-300d — Product detail pages `/library/[slug]` (FE)
Milestone: M1

- Cover image, title, author, description
- Format options + price
- "Add to cart" or "Download free" CTA per item
- Related items

### F-300e — Cart + LemonSqueezy checkout (FE + BE)
Milestone: M6

- Cart state (localStorage + persisted)
- LemonSqueezy checkout integration
- Order confirmation flow
- **BE:** webhook handler for purchase confirmation + entitlement granting
- **B-100 reconciliation pending** — see flag above; F-300e wiring depends on which MoR is canonical at build time

### F-300f — Free resources flow (FE + BE minor)
Milestone: M1

- $0 items: skip cart, direct download
- Email gate optional (capture user for marketing)
- **BE:** signed download URLs (likely DO Spaces presigned URLs — same pattern as TTS audio cache)

### F-300g — Pre-order / waitlist (FE + BE)
Milestone: M1

- Books not ready: "Notify me when available" CTA
- Email capture, persist to BE
- **BE:** waitlist table + email send on launch (could reuse P-222 waitlist plumbing — surface in plan-first)

---

## V-005 — Font system upgrade
Milestone: M2

**Status:** Active LC
**Tag:** Active — Launch Critical (before soft beta launches).
**Filed:** 2026-05-05
**Type:** FE foundation
**Priority:** Ship before V-003 and V-004 (cascades into both)

**Problem:**
Current pair (Geist sans + Source Serif 4) reads as "safe modern" — common, lacks personality. Not Codersera/Neuralink-tier creative voice.

**Fix:**
Replace Geist + Source Serif 4 with:
- **Switzer** (Fontshare, free including commercial use) — replaces Geist for sans/UI/body. 9 weights available. More character than Geist while staying clean.
- **Fraunces** (Google Fonts via Fontshare, free including commercial use) — replaces Source Serif 4 for display + serif accents. Variable font with opsz, wght, SOFT (terminal softness), WONK (italic expressiveness) axes. Used in real editorial publications.

Affects:
- next/font configuration
- Tailwind config (font-family tokens)
- globals.css (font CSS variables)
- All references to Geist or Source Serif 4 in components

Fraunces variable axes give expressive range — use opsz appropriately (optical sizing for headlines vs body), explore SOFT axis for editorial warmth where it earns its place.

Sequencing: Ship V-005 first. V-003 and V-004 inherit the new typographic system.

---

## V-001 — Hero H1 + rotating kicker sizing
Milestone: M1

**Status:** Active LC
**Tag:** Active — Launch Critical (before soft beta launches).
**Filed:** 2026-05-05
**Type:** FE bug fix

**Problem:**
Hero H1 ("The French speaking exam doesn't reward what you know...") overflows viewport on both desktop and mobile. Rotating kicker (TCF/TEF/DELF/DALF cycle) renders too small to read at distance.

**Fix:**
- Tighten H1 clamp on small viewports — current ceiling probably 96px, lower to ~72px on mobile, keep desktop max
- Bump rotating kicker from current size to ~20-24px (was ~14-16px)
- Verify on 375px mobile and 1440px desktop

---

## V-002 — Em-dash strip across FE copy
Milestone: M2

**Status:** Active LC
**Tag:** Active — Launch Critical (before soft beta launches).
**Filed:** 2026-05-05
**Type:** FE copy hygiene

**Problem:**
Em-dashes ("—") overused across landing copy, methodology copy (F-202, F-227), and various surfaces. Reads as AI-authored signature pattern.

**Fix:**
Audit all FE copy strings for em-dash usage. Replace with:
- Period (when separating two complete thoughts)
- Comma (when introducing supporting clause)
- Semicolon (when joining related independent clauses)
- Sentence restructure (when none of the above work)

Plan-first should surface replacements per-instance before pushing — judgment call required, not mechanical find-replace.

Affects: components/landing/copy.ts (heavy), components/ecole/intro/EcoleIntro.tsx (heavy), components/onboarding/EcoleReveal.tsx (light), other FE copy files where em-dashes appear.

---

## V-003 — Hero atmospheric typographic animation
Milestone: M2

**Status:** Active LC
**Tag:** Active — Launch Critical (before soft beta launches).
**Filed:** 2026-05-05
**Type:** FE visual depth

**Problem:**
Hero is too quiet. F-200 editorial restraint went too far — doesn't read Codersera/Neuralink-tier premium without atmospheric depth.

**Fix:**
Add SVG-based animated background layer to hero section:
- Massive French accent marks (é, à, ç, ô, î, ù) at 600-800px scale
- Very low opacity (4-6% on ed-bg)
- Slow drift animation (60s+ cycles, multiple marks staggered)
- Subtle parallax on scroll (transform translateY at scroll-progress * 0.2)
- One mark per region of hero, never overlapping
- Respects prefers-reduced-motion (static end-state shown)
- CSS + SVG only, no video, no JS animation library beyond what F-212 already has

Brand-aligned (French language = accent marks). Editorial (not playful). Premium without video assets.

---

## V-004 — Differentiation cards rebuild (Codersera-grade)
Milestone: M2

**Status:** Active LC
**Tag:** Active — Launch Critical (before soft beta launches).
**Filed:** 2026-05-05
**Type:** FE visual depth

**Problem:**
Three current differentiation cards under "Built specifically for the B1 → B2 wall" are identical text-only templates. Reads as quiet/generic. Not Codersera-tier.

**Fix:**
Rebuild each of the three cards with:
- Visual variation per card (no identical templates)
- A typographic callout per card (oversized accent — could be a couche number, a Greek-letter-style mark, a typographic ornament)
- Headline + body retained
- A small in-card visual element that reinforces the specific claim (e.g., for "Diagnostic-driven, not curriculum-driven" — a small SVG of the 5-couche stack with one layer illuminated)
- Hover state that reveals additional detail or shifts the visual element
- Cards should be visually distinct from each other, not three slots of the same template

Reference: Codersera's "Why Codersera" 6-card grid uses different micro-imagery per card, layered information, hover lifts. Adapt that pattern to LeMethodic's 3-card differentiation context.

---

## V-011 — FinalCTA centering + color refresh
Milestone: M2

**Status:** Active LC
**Tag:** Active — Launch Critical (before soft beta launches).
**Filed:** 2026-05-06
**Type:** FE visual refinement

**Problem (centering):**
FinalCTA section content reads as visually off-center on production /fr (likely also /en). Headline appears left-aligned or unbalanced; line break "Arrêtez de deviner ce / qui bloque votre B2." has orphan word "ce" at end of line 1.

**Problem (color):**
Section is monochromatic (ed-bg + ed-fg + ed-accent navy). Chadi feedback: "the colors that were used before in the website were much better." Pre-F-200 era had more color variety. Section reads as flat.

**Fix:**
Two-stage. Centering fix is mechanical (~15 min, no decision needed). Color refresh requires plan-first with 2-3 concrete options for Chadi to react to.

Centering fix:
- Audit FinalCTA container alignment (mx-auto + max-width verification)
- Headline text-align: center
- Headline line break — text-balance OR non-breaking space OR max-width tuning
- Verify FR + EN headlines, 1440px desktop + 375px mobile

Color refresh:
- Plan-first with git history check on FinalCTASection.tsx (pre-F-200 commits) to identify what colors existed before the editorial migration
- Propose 2-3 treatment options (e.g., accent on "B2" word, warmer trust-line color, section bg flip, button hover character)
- Chadi picks before push

May ship in stages: centering fix today as quick-win; color refresh as V-011.color subticket pending Chadi sign-off on plan-first proposals.

---

## F-210 — Icon system + custom LeMethodic icons
Milestone: M2

**Filed:** 2026-05-04.
**Status:** Queued.
**Tag:** Active — Launch Critical (before soft beta launches).

**Priority:** Medium-high (visual identity).

Custom icon set replacing generics:
- **Méthode marks** — visual representations of the 4 couches (Le Fond, Les Moules des Idées, Les Moules, Les Réflexes Anglais).
- **Tâche badges** — T1 / T2 / T3 with distinct visual treatment.
- **Level chips** — A2 / B1 / B2 / C1 with consistent typography.
- **Couches indicators** — small inline glyphs for inline reason-code rendering.

**Owner:** FE + designer.

---

## F-211 — Loading states overhaul
Milestone: M2

**Filed:** 2026-05-04.
**Status:** Queued.
**Tag:** Active — Launch Critical (before soft beta launches).

**Priority:** Medium-high.

Today many flows have silent waits or spinners with no context. Replace with:
- Animated loaders carrying rotating Chadi-voice messages ("Listening to your French..." / "Spotting Réflexes Anglais..." / "Checking against the moule...").
- Skeleton states for dashboard sections, `/progress`, `/diagnostic`, `/cluster/[slug]`.
- Recording analysis progress indicator (analysis takes 30-60s; currently a silent wait — surface estimated time + per-step progress).

**Owner:** FE + Chadi (rotating message copy in FR + EN).

---

## F-212 — Micro-animations + interaction feedback
Milestone: M2

**Filed:** 2026-05-04.
**Status:** Queued.
**Tag:** Active — Launch Critical (before soft beta launches).

**Priority:** Medium-high.

- Hover/tap states on every interactive element (currently inconsistent).
- Animated progress bars (couches scoring, recording cap timer, /progress percent-complete).
- Transition tokens centralized — `lib/motion.ts` already exists from P-115; extend coverage to every surface.
- `prefers-reduced-motion` respected throughout (audit + fix).

**Owner:** FE.

---

## F-213 — Page transitions + motion design
Milestone: M2

**Filed:** 2026-05-04.
**Status:** Queued.
**Tag:** Active — Launch Critical (before soft beta launches).

**Priority:** Medium.

- Onboarding question slide transitions (right-to-left as user advances, left-to-right on back).
- Staggered dashboard section reveal on `/progress` initial load.
- Celebration moment on diagnostic complete (level revealed) — restrained, methodology-honest, not gamified.
- Route-level fade between major surfaces (avoid hard cuts).

**Owner:** FE.

---

## F-214 — Visual depth + design system extension
Milestone: M2

**Filed:** 2026-05-04.
**Status:** Queued.
**Tag:** Active — Launch Critical (before soft beta launches).

**Priority:** Medium.

- Gradients on pastel surfaces — pulled from M-101a landing palette so landing and app share visual DNA.
- Card elevation tiers (1, 2, 3 shadow levels via design tokens).
- Typography rhythm — line-height + paragraph-spacing scale codified (currently ad-hoc per component).
- Empty-state illustrations — custom, not generic stock icons.

**Owner:** FE + designer.

---

## P-234 — Cluster detail view
Milestone: DONE

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** BE shipped 2026-05-03 (commit `7f54b88`); **FE consumer in progress.** Stays in active queue until FE ships their side.
**Tag:** Active — Launch Critical (before soft beta launches).

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation. Curriculum doc §10.4 / §7.8.

Per-cluster page with lesson + exercises + practice prompt + per-user state + recording history. Multi-format lesson rendering (markdown / PDF embed / video embed).

### BE side — shipped 2026-05-03 (commit `7f54b88`)

Two read-only endpoints back the FE detail page:

```
GET /api/clusters/{slug}              auth required
  → ClusterDetailResponse: id, slug, labels{i18n}, grammar_topic,
    vocabulary_theme{slug, labels} | null, tache_application,
    cefr_level, lesson{format, markdown, asset_url},
    practice_prompt{}, exercise_set[]
  404 on unknown slug. detection_rubric NOT exposed (Q1 — internal
  scoring infrastructure).

GET /api/users/me/clusters/{slug}     auth required
  → UserClusterStateResponse: cluster_slug, status, last_rubric_score,
    last_detection_result, revisit_count, first_started_at,
    last_status_change_at, absorbed_at, recording_history[<=10, newest first]
  404 on unknown slug. Graceful defaults when user has no
  UserClusterStatus row (Q3 — "not started" UX, not 404).
```

Plan-first lock-in (2026-05-03): Q1 detection_rubric hidden, Q2 history last 10 newest-first, Q3 no-UCS defaults, Q4 lesson_markdown FR-only Phase 1 (FE handles language hint), Q5 auth-only no path-enrollment scoping.

Recording history sourced from `UserClusterEvent` rows (Recording has no `cluster_id` FK); `detection_result` read from `findings_json["detection_result"]` per the P-200 persistence helper.

Files: `app/schemas/cluster.py` (new), `app/services/cluster_lookup.py` (new), `app/routers/clusters.py` (new), `main.py` (router registration), `scripts/smoke_p234.py` (new — 43 checks across 4 steps, all PASS).

No alembic migration. No new table, no new column. `recordings.py` / `conversations.py` / `users.py` untouched — purely additive.

### FE side — pending

Consumer of the two endpoints above. FE owns the detail page UI, multi-format lesson rendering (markdown highlight / PDF embed / video player), exercise interaction, practice CTA wiring, history rendering, and the language hint when `interface_language != fr` (lesson_markdown is FR-only Phase 1 per Q4).

When FE ships, this entry flips to fully Shipped and moves to the SHIPPED section.

---

## P-105 [M5.5] [P0] -- Server-side tier enforcement
Milestone: M5.5

**Filed:** 2026-04-30 (orig.: 7-day trial logic); rescoped 2026-05-31 to standalone tier enforcement per M5.5 BE audit.
**Status:** SHIPPED (master 8b59c07)
**Tag:** Active -- Launch Critical (before soft beta launches).

**Priority:** P0 (required before any user is charged).

`_resolve_user_tier()` in `app/services/tiers.py` returns `"free"` for all users unconditionally (Phase A placeholder). Every `require_tier()` dependency and every `enforce_min_tier()` call sees the user as free tier regardless of `users.subscription_tier`. Any registered user currently has full access to all premium endpoints. This is intentional during the pre-payment soft-launch window, but must be wired before charging users.

**Scope:** Wire `_resolve_user_tier()` to read `user.subscription_tier` from the User row. The DI shape is stable; the fix is `return getattr(user, "subscription_tier", "free")` in `_resolve_user_tier`. Smoke every endpoint that gates on `require_tier()` or `enforce_min_tier()` to confirm 402/403 is returned on under-tier tokens.

**Acceptance:**
- A free-tier token is rejected (402 or 403) from a subscription-gated endpoint.
- A subscription-tier token (manual DB fixture for the test) passes the same endpoint.
- Verified by pytest, not by FE gating.

**Dependencies:** None. Does not depend on Stripe, P-106, or B-100. Unblocks M6.

**Files:** `app/services/tiers.py` (resolver one-liner), `app/routers/vocab.py` (confirmed enforce_min_tier caller per audit), all other routers using `require_tier()` or `enforce_min_tier()` (confirm via grep before shipping).

**Branch:** master

**History:** Original P-105 Stripe trial mechanics scope (trial_started_at, trial_ends_at, subscription_status, stripe_customer_id, has_active_access) absorbed into P-106 [M6].

Resolver fix in app/services/tiers.py; enforcement test in tests/test_p105_tier_enforcement.py.

---

## F-401 [M5.5] [HIGH] -- Rate limiting on AI endpoints
Milestone: M5.5

**Filed:** 2026-05-31 per BE audit (Section 5 -- Security Checklist, finding 4).
**Status:** SHIPPED (master e32f36e).
**Tag:** Active -- Launch Critical (before soft beta launches).

**Priority:** HIGH (cost-runaway risk before paid launch).

Existing rate limiting in `app/services/rate_limit.py` covers 5 auth endpoints only. No per-user limits are applied to the metered AI-calling endpoints. A single authenticated user can drain the Claude, AssemblyAI, and ElevenLabs budgets in minutes.

**Scope:** Per-user rate limits on the four AI-calling endpoints below. Redis-backed (same infra as F-310 / F-311 rate limiter). Limit values configurable per endpoint via env var. Breach returns 429.

Endpoints to gate:
- `POST /api/recordings/{id}/transcribe` (AssemblyAI call)
- `POST /api/recordings/{id}/analyze` (Claude call)
- `POST /api/conversations/{id}/turns` (Claude call per turn)
- `POST /api/writing/submit` (Claude async job)

**Acceptance:**
- Exceeding the per-user limit on any of the four endpoints above returns 429.
- Limit is configurable per endpoint via env var without code change.
- Verified by pytest with a mocked Redis counter.

**Dependencies:** Redis available in BE runtime (same instance provisioned for F-310).

**Files:** `app/services/rate_limit.py` (extend limiter), `app/routers/recordings.py`, `app/routers/conversations.py`, `app/routers/writing.py`.

**Branch:** master

---

## F-402 [M5.5] [PERF] -- FK indexes
Milestone: M5.5

**Filed:** 2026-05-31 per BE audit (Section 3 -- Index Audit).
**Status:** SHIPPED (master a18c0dc)
**Tag:** Active -- Launch Critical (before soft beta launches).

**Priority:** HIGH for the top two; every analytics request is currently a full table scan compounded by N+1 full table scans on feedbacks.

**Scope:** Additive Alembic migration adding the five critical missing indexes confirmed by the 2026-05-31 audit. All five are CREATE INDEX only (no ALTER TABLE on existing columns). Migration qualifies for the OPTIONAL pg_dump tier per the production migration protocol: 100% additive, zero existing row mutations, clean downgrade.

Indexes to create:
- `ix_recordings_user_id` on `recordings(user_id)` -- HIGH: every analytics + history query filters on this column
- `ix_feedbacks_recording_id` on `feedbacks(recording_id)` -- HIGH: every lazy-load of r.feedback fires a full table scan without this index
- `ix_writing_submissions_user_id` on `writing_submissions(user_id)` -- MEDIUM
- `ix_writing_submissions_prompt_id` on `writing_submissions(prompt_id)` -- LOW-MEDIUM
- `ix_recordings_topic_id` on `recordings(topic_id)` -- LOW-MEDIUM

**Acceptance:**
- Migration applies clean: `alembic upgrade head`, `alembic downgrade -1`, re-upgrade all succeed.
- `EXPLAIN` on the analytics/dashboard query shows index usage for recordings.user_id and feedbacks.recording_id.

**Dependencies:** None. Coordinates with F-403 (indexes amplify the N+1 fix benefit but are not a sequencing requirement).

**Files:** New Alembic revision in `alembic/versions/`.

**Branch:** master

**Prod:** Migration applied 2026-05-31; alembic_version at f40200000001; 14 ix_* indexes verified (confirmed via DO App Platform Console alembic current).

---

## F-403 [M5.5] [SCALING] -- N+1 fixes
Milestone: M5.5

**Filed:** 2026-05-31 per BE audit (Section 1 -- N+1 Query Audit).
**Status:** SHIPPED (master a487799).
**Tag:** Active -- Launch Critical (before soft beta launches).

**Priority:** HIGH for analytics and recordings/history paths (a user with 50 recordings triggers 51+ queries per dashboard load today).

**Scope:** Add eager loading (selectinload or joinedload as appropriate) to the 7 endpoints the audit flagged as HIGH or MEDIUM risk. `GET /api/recordings` already uses joinedload correctly -- use that as the reference pattern.

Flagged endpoints (from the 2026-05-31 audit, Section 1):
- `GET /api/analytics/dashboard` -- HIGH: `.options(selectinload(Recording.feedback))` on the recording query
- `GET /api/analytics/progress` -- HIGH: selectinload(Recording.feedback)
- `GET /api/analytics/pass` -- HIGH: selectinload(Recording.feedback)
- `GET /api/admin/dashboard` -- MEDIUM: joinedload or selectinload on Feedback
- `GET /api/admin/users` -- HIGH (2N+1 compound): replace per-user recording + avg subquery loop with a single GROUP BY aggregate query across all users
- `GET /api/recordings/history` -- HIGH: `.options(joinedload(Recording.feedback))` to match the pattern already in the lean list endpoint
- `GET /api/writing/history` -- HIGH: `.options(joinedload(WritingSubmission.prompt))` to replace the explicit per-row subquery loop

**Acceptance:**
- Query count on each flagged endpoint drops to constant with respect to result size (assert or log-inspect).
- Existing response shapes unchanged.

**Dependencies:** None. Coordinates with F-402 (indexes amplify the benefit but are not a prerequisite).

**Files:** `app/routers/analytics.py`, `app/routers/admin.py`, `app/routers/recordings.py`, `app/routers/writing.py`.

**Branch:** master

---

## P-106 — Stripe integration (subscription + one-time + Premium SKU)
Milestone: M6

**Filed:** 2026-04-30; rescoped 2026-05-03 (Stripe → LemonSqueezy — Morocco constraint); rescoped 2026-05-04 (LemonSqueezy → Paddle, per B-100 Path B); **rescoped 2026-05-12 → Stripe SDK (Path C via US LLC, per B-100 Path C).**
**Status:** Queued (blocked on B-100 — Stripe Atlas LLC formation + activation).
**Tag:** Active — Launch Critical (before soft beta launches).

**Priority:** High (pre-launch).

Integrate Stripe SDK as the payment + subscription provider:
- **$29/mo subscription** SKU (recurring) — `subscription.create` with `trial_period_days=7` (drives P-105).
- **$199 Sprint one-time** SKU — Checkout Session in `payment` mode.
- **$499 Premium one-time/subscription** SKU (NEW — month 2-3 launch tier).
- **Webhook endpoint** for subscription + payment lifecycle events (`customer.subscription.created/updated/deleted`, `invoice.payment_succeeded/failed`, `customer.subscription.trial_will_end`). **HMAC signature verification on every webhook** via `Stripe-Signature` header — reject before any DB mutation (F-310 scope reference). Drives entitlement state on User rows.
- **Customer Portal** link for self-serve billing management (Stripe-hosted; deep-link from settings).
- Test-mode + production-mode key separation via env (mirror of existing `ANTHROPIC_API_KEY` / `ASSEMBLYAI_API_KEY` pattern).
- Subscription tier → FastAPI dependency-injection layer (consumed by F-310 auth-hardening's per-route gating).
- **7-day trial mechanics (absorbed from P-105 rescope 2026-05-31):** `subscription.create(trial_period_days=7)`; `customer.subscription.trial_will_end` webhook fires 3 days before expiry; `customer.subscription.updated` fires on transition to active-paid or deleted on lapse. User fields: `trial_started_at`, `trial_ends_at`, `subscription_status` (trialing | active | lapsed | canceled | none), `stripe_customer_id`, `stripe_subscription_id` -- alembic migration. Trial-start trigger: first authenticated session post-signup auto-creates a Stripe customer + subscription in trialing state. Entitlement helper `app/services/entitlement.py::has_active_access(user) -> bool` consumed by the tier-check DI layer. Lapsed-user UX: read-only access to past recordings + diagnostic; new recordings blocked with paywall redirect.

**Why Stripe (post-Paddle):** US LLC formation via Stripe Atlas (B-100 Path C) routes around the Morocco merchant constraint that originally blocked Stripe. Net wins over Paddle: ~7% fee delta (2.9% + $0.30 vs ~5% + $0.50), cleaner subscription API, native trial mechanics, better-documented webhook lifecycle, mature TypeScript SDK.

**Depends on:** B-100 (Stripe Atlas LLC formation + activation -- application pending Chadi 2026-05-12+). P-105 [M5.5] must be live before trial gates are enforced (tier enforcement is a P-105 pre-requisite, not a P-106 scope item).

**Out of scope:** geographic price differentiation (the original "dual + geographic pricing" framing) — Phase 1 ships with single global $29/$199/$499 pricing. Stripe's native Tax + multi-currency support revisits post-launch if conversion data warrants.

---

## B-100 — Stripe via US LLC formation (Stripe Atlas)
Milestone: M6

**Filed:** 2026-04-30 (Stripe account setup); renamed 2026-05-03 Stripe → LemonSqueezy (Morocco constraint); reframed 2026-05-04 to MoR provider selection (LemonSqueezy approval stalled); decided 2026-05-04 Path B — Paddle; **rescoped 2026-05-12 → Path C: Stripe via US LLC formation (Stripe Atlas).**
**Status:** In Progress — Chadi to initiate Stripe Atlas application (Path C locked 2026-05-12).
**Tag:** Active — Launch Critical (before soft beta launches).

**Priority:** HIGH (pre-launch -- unblocks P-106).

**Path C rationale:** Stripe at 2.9% + $0.30 vs Paddle ~5% + $0.50 = ~7% fee delta. Breakeven on LLC setup cost (~$500 Stripe Atlas + registered agent year 1) lands at ~250 paying subs. At Chadi's projected scale (5,000+ Y1 users with even modest paid-conversion), the savings recover the slip within the first month. The 2-6 week Stripe Atlas processing slip is acceptable because the product isn't ready to charge anyone yet — payment timeline is no longer the launch critical path. Quality-gated launch (per F-300 framing) means payments can land alongside or after first paid feature, not before.

**Scope:**
- ✗ Stripe Atlas application — $500 flat, Delaware LLC, registered agent year 1, immediate Stripe activation on LLC formation.
- ✗ EIN issuance via Atlas (typically same-week after LLC formation).
- ✗ Mercury business bank account — pairs with Atlas LLC for US business banking.
- ✗ Stripe activation + sandbox/production API key separation.
- ✗ Storefront / Stripe Checkout configuration (product naming, branding, terms link to `/terms`).
- ✗ Three SKUs: **$29/mo subscription + $199 Sprint one-time + $499 Premium** (month 2-3 launch).
- ✗ Webhook secret for backend HMAC signature verification.

**Decision history:**
- 2026-05-03: Stripe → LemonSqueezy (Morocco constraint — Stripe doesn't onboard Morocco-based merchants directly).
- 2026-05-04: LemonSqueezy → Paddle (LemonSqueezy KYC stalled; Path B locked).
- 2026-05-12: Paddle → Stripe via US LLC (Path C). LLC structure routes around Morocco constraint cleanly; Stripe's lower fee + cleaner subscription API justify the setup slip.

**Decision-making ceiling (locked 2026-05-12):** No further payment pivots without documented failure of Path C. Three pivots in 9 days is the ceiling — break this rule and we have a decision-making problem, not a payment-processor problem.

**Fee structure expectation:** 2.9% + $0.30 per transaction (Stripe standard).

**Owner:** Chadi (Atlas application / EIN / Mercury / Stripe storefront) → handoff to Engineering for API key + webhook configuration once activated.

**Unblocks:** P-106 (integration — rescoped to Stripe SDK), P-105 (trial logic — rescoped to Stripe `trial_period_days`).

**Timeline:** Stripe Atlas processing 2-6 weeks per public timeline; EIN issuance ~1 week post-LLC; Mercury onboarding ~3-5 business days post-EIN. Total: 3-8 weeks Chadi → handoff to Engineering.

---

## M-103 — YouTube anchor video — French exam prep for English speakers
Milestone: polish-defer

**Filed:** 2026-04-30; scope-reduced 2026-05-02; **rescoped 2026-05-04** (TCF-only → all-exams positioning to match brand-layer pivot).
**Status:** Queued.
**Tag:** Active — Launch Critical (before soft beta launches).

**Priority:** Medium (pre-launch credibility artifact, not a sustained channel commitment).

**Scope (rescoped):** 1 anchor video pre-launch — ~5-10 min, framed around the L1-interference moat ("Why English speakers all make the same French mistakes — and how to actually fix them"). Anchors LeMethodic as a **French exam prep platform for English speakers**, not TCF-only. Examples can pull from any of TCF/TEF/DELF B1/B2 since the format DNA is shared. Establishes the channel + serves as a referral asset; cadence is **not** committed pre-launch.

**Re-evaluate post-launch:** if the anchor video drives meaningful traffic or referral signal within 4-8 weeks, decide whether to commit to a sustained cadence (monthly anchor + occasional shorts) or leave the channel as a one-shot artifact. Default: leave as-is unless signal is clear.

**Owner:** Chadi (recording + editing + thumbnail). Solo founder cost is high — no monthly commitment until signal justifies it.

---

## M-104 — Reddit community engagement (broadened subreddit list)
Milestone: polish-defer

**Filed:** 2026-04-30; **rescoped 2026-05-04** (broader subreddit roster to match all-exams brand pivot).
**Status:** Queued.
**Tag:** Active — Launch Critical (before soft beta launches).

**Priority:** Medium.

Reddit-as-acquisition: helpful comments on relevant threads with low-key LeMethodic mentions only when contextually appropriate. Subreddit roster post-pivot:

- r/French — general French learning, broad reach.
- r/TEF, r/DELF — exam-specific (smaller but high-intent).
- r/learnfrench — beginner-skewed; still a feeder for B1/B2 students post-discovery.
- r/immigrationcanada — visa-urgency persona (TCF/TEF), highest conversion intent.
- r/expats, r/IWantOut — adjacent visa/immigration audiences.
- r/learnlanguages, r/languagelearning — broad-language learners likely to need exam prep.

**Cadence:** light — 2-3 thoughtful comments per week, no link-spamming. Track which subs convert (informally) for post-launch reallocation.

**Owner:** Chadi.

---

## F-310 — Auth hardening (BE + FE) — BE SHIPPED 2026-05-12
Milestone: DONE

**Filed:** 2026-05-12 (strategic session — Decision 4).
**Status:** **BE Shipped 2026-05-12** across 6 commits (Phases A-E + F-310.1).
FE work (hCaptcha widget render, email-verification UI, refresh-on-401
interceptor, password-reset UI) remains; tracked in lemethodic-frontend
BACKLOG as the cross-ref from FE-side F-072 supersede.
**Tag:** Active — Launch Critical (before soft beta launches).
**Type:** BE + FE security infrastructure.

**Shipped commits (BE):**
- `4bb44fb` — Phase A foundation services (Redis client, hCaptcha verify,
  Stripe HMAC helper, tier DI placeholder, Resend email helper).
- `e397122` — Phase B migration + JWT refresh flow + 5 new endpoints
  (refresh, verify-email, verify-email/resend, password-reset/request,
  password-reset/confirm) + email_verified_at hard gate on protected routes.
- `babfa5d` — Phase C rate-limit middleware + hCaptcha wiring + email send
  on register/resend/password-reset.
- `9ae7e34` — Phase D Stripe webhook endpoint shell (option a, no DB writes).
- `618f447` — Phase E smoke_f310.py (14 steps, 49 PASS) + webhooks.py
  to_dict bug fix.
- `a999a5f` — F-310.1 X-Forwarded-For client IP fix for DO LB proxy hop.

**Production state at close (2026-05-12):**
- Migration h6f7g8e9d0c1 applied; 5 new users columns + 3 token tables
  + 2 CHECK constraints live.
- Soft-beta cohort grandfathered (email_verified_at = NOW() for all
  pre-migration users).
- All 9 new auth endpoints listed in prod /openapi.json.
- Auto-deploy on push to master = the production rollout mechanism.

**Env vars (Chadi to set in DO console for full enforcement):**
- `ENV=production` — REQUIRED. Activates F-310.1 XFF parsing + cookie
  secure flag. Without it, rate-limit buckets share across users
  (broken at scale) AND cookies remain non-secure (HTTP-intercept risk
  on any redirect path).
- `REDIS_URL` — REQUIRED for rate limit + refresh-token revocation.
  Provision DO Managed Redis (Frankfurt region to pair with the app).
  Without it: rate limit fail-opens (no enforcement); refresh-token
  revocation falls back to DB-only authoritative check.
- `RESEND_API_KEY` — REQUIRED for email delivery. Without it:
  register / verify-email/resend / password-reset/request succeed
  (2xx) but no email lands. Existing soft-beta accounts can still
  use the app (grandfathered); new registrations are stuck unverified.
- `HCAPTCHA_SECRET` + `HCAPTCHA_SITEKEY` — REQUIRED to enforce bot
  defense. Without them: captcha verification no-ops.
- `STRIPE_WEBHOOK_SECRET` — set when P-106 / B-100 land. Without it:
  webhook endpoint 400s every signature (correct posture; Stripe
  isn't sending events until B-100 ships).

**Original scope (preserved for history):**

**Priority:** HIGH — **pre-launch blocker.** At 5K+ Y1 user projection, weak auth means unlimited free-tier account creation and lost cost control. Existential security/cost issue, not a nice-to-have.

**Priority:** HIGH — **pre-launch blocker.** At 5K+ Y1 user projection, weak auth means unlimited free-tier account creation and lost cost control. Existential security/cost issue, not a nice-to-have.

**Scope:**
- **JWT lifecycle:** 15-minute access token + 7-day refresh token. Refresh on every access — rotation on every refresh (revoke old refresh, issue new). HttpOnly + Secure + SameSite=Lax cookie storage. Redis-backed refresh-token revocation list keyed by `jti`; access tokens stateless (signature + exp check only).
- **/auth rate limiting:** 5 attempts per IP per 15 minutes (login + register + password-reset). Exponential backoff on failure (1s → 2s → 4s → 8s → 16s). 10-attempt lockout per IP per hour with admin-clearable Redis key.
- **Email verification gate:** hard gate on all NEW registrations (post-2026-05-12). Existing soft-beta accounts grandfathered as verified — backfill migration sets `email_verified_at = NOW()` for users created before deploy date. Email-verification token: signed JWT with 24h expiry, single-use (consumed on click, marked in Redis).
- **hCaptcha:** on registration form + password-reset form. Fail-closed: reject submission if hCaptcha response missing or invalid.
- **Stripe webhook HMAC verification:** every Stripe webhook arrives with `Stripe-Signature` header. Verify via `stripe.Webhook.construct_event(payload, sig, webhook_secret)` BEFORE any DB mutation. Reject 400 on bad signature. (Coordinates with P-106 scope — same code path.)
- **Subscription-tier check via FastAPI DI:** `Depends(require_tier("free" | "subscription" | "sprint" | "premium"))` decorator on every protected route. Tier resolution reads from User.subscription_status. **Ship with `tier=free` placeholder for all users until P-105 lands** — the DI layer is in place but enforcement table is empty. P-105 populates real tier values; F-310 doesn't block on P-105.

**Absorbs FE-side F-072 scope** (FE ticket marked Superseded by F-310 in lemethodic-frontend BACKLOG; cross-reference only — BE doesn't edit FE BACKLOG).

**Depends on:** Redis (also dependency of F-311 — provision once, share).

**Sequencing:** ship before P-105/P-106 (so the DI layer exists when tier values populate). Do NOT block on B-100 timeline (auth hardening doesn't need Stripe live).

**Owner:** BE (JWT + rate limiter + email verification + webhook HMAC + DI) + FE (hCaptcha widget + email verification UI + refresh flow on 401).

**Smoke:** new `scripts/smoke_f310.py` — JWT rotation, rate-limit triggering, email-gate enforcement on new accounts, grandfathering for old accounts, webhook HMAC accept/reject cases, DI tier-gate with `tier=free` default. **Shipped 2026-05-12 with 15 steps / 54 assertions / 0 failures.**

---

### F-310.1 — X-Forwarded-For client IP fix — SHIPPED 2026-05-12
Milestone: DONE

**Filed:** 2026-05-12 (pulled forward from "post-Phase-E" to "ship before any cohort onboarding").
**Status:** Shipped 2026-05-12 (commit `a999a5f`).
**Tag:** Active — Launch Critical (before soft beta launches).
**Parent:** F-310.

**Problem:** DO App Platform's load balancer fronts the app container. `request.client.host` reads the LB's internal IP, not the user's. Without the fix, all users behind the LB share one rate-limit bucket — the moment one user trips the limit, every concurrent user is blocked.

**Fix:** `app/services/rate_limit.py::_client_ip` now branches on `settings.ENV`:
- Non-production: `request.client.host` (local dev, no proxy).
- Production: parse `X-Forwarded-For`, trust the LAST entry (DO appends real client IP; first entries may be attacker-spoofed).

**Smoke coverage:** Step 15 in `scripts/smoke_f310.py` (5 sub-assertions: ENV-dev branch, ENV-production trust, spoofing-defeat verification, no-XFF fallback, no-client sentinel).

**Limitation flagged in docstring:** "trust last entry" pattern is correct ONLY for single trusted proxy hop. Adding a CDN in front of DO requires revisiting the trust position. Not relevant for soft beta; track if/when CDN ships.

**Chadi prod action required:** set `ENV=production` in DO env vars. Without it the fix is a no-op (still uses `request.client.host` = broken state).

---

## F-311 — Token control infrastructure (BE) — SHIPPED 2026-05-12
Milestone: DONE

**Filed:** 2026-05-12 (strategic session — Decision 4).
**Status:** **BE Shipped 2026-05-12** across 5 phases / commits. No FE
component (purely BE infrastructure). Production-ready.
**Tag:** Active — Launch Critical (before soft beta launches).
**Type:** BE cost-control infrastructure.

**Shipped commits:**
- `9b25652` — Phase A foundation (anthropic_client + ai_router +
  prompt_safety + config additions).
- `6ba3e2c` — Phase B analysis.py + writing_analysis.py refactor →
  centralized client, model routing, max_tokens 8192→1600, cache enabled.
- `e925519` — Phase C 4 inline httpx call sites refactored (tache_1/2,
  argument_assistant, transcript_suggestions). Examiner routes to haiku.
- `a7706c1` — Phase D diagnostic_rate_limit + DI wrappers on the 3
  analysis endpoints + injection check on writing/upload.
- `9a912ba` — Phase E smoke_f311.py (45 assertions, all PASS) + live
  Claude cost validation + 2 pattern loosenings caught during smoke.

**Production state at close (2026-05-12):**
- Every Claude API call site routes through anthropic_client.call_anthropic.
- Diagnostic helpers (analysis, writing_analysis) cap output at 1600
  tokens (down from 8192) + cache system prompts via Anthropic's
  prompt-caching beta.
- Examiner turns (tache_1, tache_2) route to haiku-4-5 (down from sonnet-4),
  ~10x cost cut per turn.
- 3 analysis endpoints (recordings/upload, conversations/end, writing/submit)
  enforce per-user-per-UTC-day quota: free=5 / sub=30 / sprint=60 / premium=unlimited.
- Prompt injection check on writing/submit + recordings/upload (argument_structure
  field). 12 patterns; conservative on English; French content unaffected.

**Live-validated cost-saving math (Phase E smoke step 11):**
- Cache hit ratio: **90.1%** on a real-Claude call within the 5-min window.
- Per-call cost: $0.01073 (cache write) vs $0.00107 (cache read).
- Projected at 5K users × 3 diagnostic/month: **$144.94/mo savings on
  diagnostic alone** ($160.95 no-cache → $16.01 cached).
- Examiner-turn sonnet→haiku savings compound on top (not measured but
  ~10x per turn).

**Env vars (Chadi to set in DO console for full enforcement):**
- `REDIS_URL` — REQUIRED for diagnostic quota enforcement (same Redis
  as F-310). Without it: quota fails-open with WARNING; cost-control
  layer is dark.
- `ENABLE_PROMPT_CACHE=true` (default) — keep set for the 90% savings.
- `ENABLE_PROMPT_INJECTION_CHECK=true` (default) — keep set unless
  false-positive rate surfaces.
- `MAX_TOKENS_DIAGNOSTIC=1600` (default) — env-overrideable. Lower
  if smoke shows safe room; never raise above 2400.
- `MODEL_DIAGNOSTIC=claude-sonnet-4-6` (default per Decision 4) —
  override to `claude-sonnet-4-20250514` for rollback to pre-F-311
  model if quality regresses.
- `MODEL_EXAMINER=claude-haiku-4-5` (default per Q2a) — override to
  `claude-sonnet-4-6` for rollback if Tâche 1/2 examiner quality drops.
- `DIAGNOSTIC_RATE_LIMIT_FREE/SUBSCRIPTION/SPRINT=5/30/60` (defaults).

**Original scope (preserved for history):**

**Priority:** HIGH — **pre-launch blocker.** At 5K+ Y1 user projection, uncapped diagnostic abuse blows up Anthropic API costs before subscription revenue compensates. Existential cost issue.

**Priority:** HIGH — **pre-launch blocker.** At 5K+ Y1 user projection, uncapped diagnostic abuse blows up Anthropic API costs before subscription revenue compensates. Existential cost issue.

**Scope:**
- **Redis-backed per-user rate limiter** scoped by subscription tier. Limits:
  - `tier=free`: 5 diagnostic sessions/day
  - `tier=subscription` ($29/mo): 30 diagnostic sessions/day
  - `tier=sprint` ($199): 60 diagnostic sessions/day
  - `tier=premium` ($499): unlimited (no Redis check)
  - Counter key: `tokens:{user_id}:diagnostic:{YYYY-MM-DD}` with 25h TTL.
- **Model routing:** `claude-haiku-4-5-20251001` for vocab exercises + lookups (cheaper, faster, sufficient for lexical retrieval). `claude-sonnet-4-6` for diagnostic scoring (depth required). Routing decision in a single helper `app/services/ai_router.py::pick_model(task: Literal["vocab" | "diagnostic" | "rag_synthesis"])`.
- **Anthropic prompt caching** on system prompts. Mark long system prompts with `cache_control: {"type": "ephemeral"}` to hit 90% cost reduction on repeat. Coordinates with V-016a's 3000+ token writing system prompt — prime caching candidate.
- **Hard cap `max_tokens=800`** on every diagnostic response. Already in writing path (set to 8192 — lower this to 800 per Decision 4). Note: V-016a's 5-couche output schema fits comfortably under 800 tokens with the dual-channel block intact; verify with a smoke output-token measurement.
- **Prompt-injection detection layer pre-Claude:** reject system-override patterns before the API call. Detect: `IGNORE PREVIOUS INSTRUCTIONS`, `You are now`, `<\|im_start\|>`, `<\|system\|>`, and the standard injection corpus. Return 400 to the user; log the rejected payload to a separate audit table for review. Layer lives at `app/services/prompt_safety.py`.

**Depends on:** F-310 (tier resolution + Redis) — F-311 reads tier from F-310's DI layer.

**Note on max_tokens=800:** V-016a currently sets `max_tokens=8192` in `_call_claude` for the writing flow. Lowering this is a F-311 sub-task; verify the 5-couche output fits under 800 in production samples first. If output truncation surfaces, raise to 1200 — but never back to 8192 without re-justification.

**Owner:** BE.

**Smoke:** new `scripts/smoke_f311.py` — rate-limit triggering per tier, model routing, prompt-cache hit verification on repeat calls, max_tokens enforcement, injection-pattern rejection.

---

## F-312 — RAG retrieval layer (BE) — CC corpus + Chadi-authored content
Milestone: TBD

**Filed:** 2026-05-12 (strategic session — Decision 2). **Rescoped 2026-05-12 (Path C locked):** dropped OQLF + Académie sources entirely; corpus now sourced from CC-licensed corpora + Chadi's tutoring artifacts.
**Status:** Queued — F-312.0 sign-off received (Path C). No remaining licensing gate; engineering can start on Chadi's go-ahead.
**Tag:** Active — Launch Critical (before soft beta launches).
**Type:** BE diagnostic-credibility infrastructure.

**Priority:** HIGH (Launch). Diagnostic feedback grounded in a curated corpus of L1-interference patterns Chadi has actually seen across 7,000+ hours of tutoring + CC-licensed reference data. The credibility moat is Chadi's authored methodology, not third-party authority quoting.

**Scope:**
- **Postgres schema:** new `linguistic_corpus` table — columns: `id`, `chunk` (the pattern excerpt or example sentence), `correction` (the prescribed alternative), `error_type` (anglicism | calque | preposition | faux-ami | register | grammar | ...), `source` (`chadi_authored` | `wiktionary_fr` | `tatoeba` | `curated`), `source_url` (nullable; populated for CC-licensed sources), `register` (formal | informal | neutral | quebec | european), `exam_tag` (tcf | tef | delf | dalf | null), `cefr_level` (a1..c2 | null), `embedding` (pgvector or alternative), `created_at`.
- **Ingest scripts:**
  - `scripts/ingest_wiktionary_fr.py` — pulls relevant French entries from the Wiktionary dump (CC BY-SA 4.0). Idempotent per page-id + revision.
  - `scripts/ingest_tatoeba.py` — pulls sentence pairs from Tatoeba's CSV exports (CC BY 2.0 FR). Filtered to anglophone-relevant patterns at ingest time.
  - `scripts/ingest_chadi_artifacts.py` — extraction pipeline over Chadi's tutoring `.docx` archive. Approach (extraction vs. manual curation) determined by F-321 sample audit. Source = `chadi_authored`. URL = null (no public source).
- **Retrieval at diagnostic call-time:** before each `analyze_writing` (and later `analyze_recording`) Claude call, embed the student text + top-N semantic search against `linguistic_corpus`. Inject top 5-15 matches into the system prompt as in-context examples. **Citation format change vs. original scope:** instead of "according to the OQLF, this is an anglicism," output reads "Le Méthodic methodology library" — internal corpus, no external source attribution required.
- **Source-attribution surface:** when a retrieved row has a `source_url` (Wiktionary, Tatoeba), the diagnostic output may carry a `see_also: {"label": "Wiktionnaire", "url": "..."}` field per Berne-art-10 short-citation defensibility. Chadi-authored rows surface no external link.

**Out of scope (initial ship):**
- Real-time corpus updates (run ingest weekly via cron post-launch).
- User-correction feedback loop (Phase 2).
- OQLF + Académie sourcing — dropped per Path C decision; **F-312.1 tracks parallel authorization-request channel** if either body ever clears.

**Depends on:** F-311 (model routing — embedding + RAG synthesis use haiku, retrieval is local Postgres + pgvector), F-321 (sample audit determines Chadi-artifact ingest approach).

**Owner:** BE (ingest pipelines + retrieval + schema) + Chadi (corpus curation review + artifact archive ownership).

---

### F-312.0 — RAG licensing pre-flight (HARD GATE on F-312) — CLOSED
Milestone: DONE

**Filed:** 2026-05-12 (strategic session — Decision 2).
**Status:** **Closed 2026-05-12 — Path C selected by Chadi.** Decision memo at `docs/F-312-licensing-decision.md`. F-312 + F-321 unblocked. F-312.1 filed as parallel low-priority Path-A track.
**Tag:** Active — Launch Critical (before soft beta launches).
**Type:** Legal / licensing research.

**Priority:** Closed.

**Scope:** read OQLF + Académie française terms; produce decision memo with source-by-source verdict + path recommendation.

**Findings (2026-05-12 research pass — full detail in memo):**
1. **OQLF BDL** — original URL `oqlf.gouv.qc.ca/conditions_utilisation.html` returns 404. BDL is now under the Vitrine linguistique (`vitrinelinguistique.oqlf.gouv.qc.ca`); governing terms live at `quebec.ca/droit-auteur` (Quebec government umbrella). Regime: **"tous droits réservés" — reproduction, download, storage, translation, adaptation, publication explicitly prohibited without prior written authorization**. Authorization channel: `droitdauteur@mcc.gouv.qc.ca`.
2. **Académie française** — terms at `academie-francaise.fr/mentions-legales`. Regime: **all rights reserved, digital reproduction "formellement interdite sauf autorisation expresse", personal use only, commercial use explicitly excluded**. Educational exception is paper-only + free + with attribution — does not cover Le Méthodic's paid SaaS use case. Authorization channel: `contact@academie-francaise.fr`.

**Recommended path (BE Claude analysis — not legal advice):** **Path C — curated CC corpus + Chadi-authored content**. Both authoritative sources prohibit Le Méthodic's intended use without prior authorization; Paths A (authorization) and B (fair-use snippet) are either calendar-uncertain or legally thin. Path C unblocks F-312 + F-321 immediately and reinforces Chadi's authored-methodology moat over third-party authority quoting.

**Decision matrix (Chadi picks one):**
- **Path A — License + redistribute:** file written requests with both bodies. 2-12 weeks, possibly never. F-312 + F-321 blocked until response.
- **Path B — Fair-use snippet + link-only:** ≤30-word excerpts, attribution + link, no full-text storage. Legal margin thin. Recommend French-copyright lawyer sign-off before committing.
- **Path C — Curated CC + Chadi-authored corpus:** Wiktionary FR (CC BY-SA), Tatoeba (CC BY 2.0), Chadi-authored content from 7,000+ hours of tutoring. F-312 + F-321 rescope accordingly; F-312.1 sub-ticket may be filed to pursue Path A in parallel as low-priority background.

**Deliverable:** `docs/F-312-licensing-decision.md` (committed 2026-05-12).

**Sign-off:** Chadi 2026-05-12 — Path C selected. F-312 + F-321 rescoped same-day to CC corpus + Chadi-authored content. F-312.1 filed as low-priority parallel Path-A track.

---

### F-312.1 — Parallel Path-A authorization-request track (OQLF + Académie)
Milestone: polish-defer

**Filed:** 2026-05-12 (Chadi sign-off on Path C with parallel Path-A track).
**Status:** Queued — Chadi-owned, asynchronous. **Not a launch gate.** F-312 + F-321 ship without this.
**Tag:** Post-launch P2 — signal-driven (defer until real signal).
**Parent:** F-312 / F-312.0.

**Priority:** Low — no engineering work, zero downside to having outstanding.

**Scope:** Chadi sends written authorization-request emails to both bodies:
- **OQLF / Quebec government:** `droitdauteur@mcc.gouv.qc.ca`. Describe Le Méthodic, intended educational use of BDL entries, attribution commitment, expected scale.
- **Académie française:** `contact@academie-francaise.fr`. Describe Le Méthodic, intended educational use of "Dire, ne pas dire" entries, attribution commitment, expected scale.

If either body responds positively (any timeline — 2 weeks, 2 years), the corpus enriches:
- `linguistic_corpus.source` enum extends with `oqlf_bdl` and/or `academie_dndp`.
- New ingest scripts under `scripts/ingest_oqlf_bdl.py` / `scripts/ingest_academie_dndp.py` per the original F-312 plan, gated on the actual license terms received.
- Diagnostic output gains the "according to the OQLF" / "according to the Académie française" source-attribution surface that the original F-312 scope envisioned.

If neither ever responds: zero impact. F-312 ships and runs forever on CC + Chadi-authored content.

**Owner:** Chadi (email drafting + send + tracking responses). No engineering owner until/unless a license is granted.

**Trigger for engineering work:** positive response with license terms in hand from at least one body.

**Filed:** 2026-05-12 (strategic session — Decision 3).
**Status:** Queued — parent ticket; MVP children F-320..F-323 + F-324 link below.
**Tag:** Active — Launch Critical (before soft beta launches).
**Type:** New product surface — third pillar alongside L'École and Le Diagnostic.

**Priority:** HIGH (Launch — MVP) + V2 sub-bullets deferred.

**Strategic frame (locked 2026-05-12):** Le Vocabulaire is a Lexogoth-equivalent web-based chunk-based French vocabulary system. Distinct from L'École (curriculum) and Le Diagnostic (oral/written examiner). Lives alongside them as a third product surface. **Without Le Vocabulaire, Le Méthodic is exam-prep only. With it, the product serves both general French learners and exam candidates — one engine, two audiences.**

**MVP scope (Launch — children below):**
- **F-320** — DB schema (chunk, translation, topic, source, register, exam_tag, cefr_level + user personal lists tables).
- **F-321** — Phase 1 seed from Chadi's tutoring archive (3 topic sets, 500-800 entries). **F-321.audit** sample-audit pre-step determines extraction-vs-curation approach. Rescoped 2026-05-12 to Path C.
- **F-322** — Practice UI (FE) — hide/reveal, self-grade, personal lists.
- **F-323** — Test UI (FE) — MCQ, matching, dropdown, completion.
- **F-324** — Diagnostic ↔ Vocab link (BE + FE) — flagged errors auto-suggest vocab topics. Sprint 2 priority.

**V2 scope (NOT separate tickets yet — enumerated here per Chadi's 2026-05-12 decomposition decision; file as F-330.x sub-tickets when triggered):**
- **F-330.tutor** — Tutor mode: teachers build custom databases, assign to students. Distinct user role + assignment tables.
- **F-330.lists** — Personal lists + spaced-repetition scheduling (SRS) on user-built lists. Box-promotion logic, daily review queue.
- **F-330.partition** — Topic library partition: free general FR (arts, loisirs, voyages, société — Vocabulaire progressif style) vs exam-specific (TCF, DELF, TEF vocabulary by task type). Two different content corpus shapes.
- **F-330.authoring** — Exercise authoring admin tooling: admin surface for building MCQ/matching/dropdown/completion sets at scale.

**Triggers for V2 sub-tickets:** post-launch P1 — once MVP usage data shows which surface matters most (tutor mode for the B2B-tutoring angle, SRS for retention, etc.), file the relevant F-330.x and prioritize.

**Owner:** BE (F-320, F-321, F-324 BE side) + FE (F-322, F-323, F-324 FE side) + Chadi (content sourcing decisions, V2 prioritization).

---

## F-320 — Le Vocabulaire DB schema (BE)
Milestone: M4

**Filed:** 2026-05-12 (strategic session — Decision 3, MVP).
**Status:** Queued.
**Tag:** Active — Launch Critical (before soft beta launches).
**Parent:** F-330.

**Priority:** Launch.

**Scope:**
- New tables:
  - `vocab_chunks` — `id`, `chunk_fr`, `chunk_en` (optional, for FR↔EN exercises), `topic_id` (FK→vocab_topics), `source` (URL or docx filename, nullable), `source_type` (`CC_corpus | chadi_authored | book_lab | third_party_publisher_DO_NOT_EXTRACT` — parent F-330 enum, supersedes the pre-Path-C `oqlf | academie | curated` text per Decision D2 approved 2026-05-12), `register` (nullable: `formel | semi_formel | informel | argotique`), `exam_tag` (`tcf | tef | delf | dalf | null`), `cefr_level`, `created_at`, `updated_at`.
  - `vocab_topics` — `slug`, `labels{i18n}` (JSONB), `description{i18n}` (JSONB), `corpus_partition` (`free_general | exam_tagged_TCF | exam_tagged_DELF | exam_tagged_TEF` per parent F-330 enum), `cefr_level_min`, `cefr_level_max`, `created_at`. Distinct from P-202 `vocabulary_themes` per Decision D1 approved 2026-05-12 (different concept, different lifecycle).
  - `user_vocab_lists` — `user_id`, `list_id`, `name`, `created_at`. Personal-list metadata.
  - `user_vocab_list_chunks` — `list_id`, `chunk_id`, `added_at`. Join table for personal lists.
  - `user_vocab_progress` — `user_id`, `chunk_id`, `seen_count`, `correct_count`, `last_seen_at`. Per-chunk progress (feeds SRS in F-330.lists later).
- Alembic migration with explicit Postgres extensions (pgvector if F-312 lands first; otherwise no vector column at MVP).
- Pydantic schemas + ORM models.

**Out of scope:** SRS scheduling logic (F-330.lists V2); exam-specific corpus partition data (handled in F-321 seed).

**Owner:** BE.

**Smoke:** new `scripts/smoke_f320.py` — schema verification, idempotent migration, sample insert/query.

---

## F-321 — Le Vocabulaire Phase 1 seed (BE) — Chadi tutoring artifacts
Milestone: M4

**Filed:** 2026-05-12 (strategic session — Decision 3, MVP). **Rescoped 2026-05-12 (Path C locked):** dropped OQLF as ingest source; corpus now sourced from Chadi's `.docx` tutoring archive in `C:\Users\pc\Downloads`. **Audit verified 2026-05-13** — 35-file sample, verdict `mixed` (29% HIGH / 29% PARTIAL / 17% NEEDS_MANUAL / 26% SKIP); F-321 implementation = hybrid pipeline.
**Status:** Phases B/C/D shipped 2026-05-13 (commit history). Phase E (seed) BLOCKED on Chadi review of `seeds/vocab/phase1_review.csv`.
**Tag:** Active — Launch Critical (before soft beta launches).
**Parent:** F-330.

**Priority:** Launch.

**Phase 1 scope (locked 2026-05-13):**
- 3 topics: `faux_amis`, `calques_anglais`, `prepositions_a_de_dans_par_pour` (BACKLOG-hint trio, finalized by Chadi 2026-05-13 — `subjonctif_emploi` and `faire_causatif` dropped from Phase 1 as L'École-side curriculum content, see F-321.curriculum).
- Target: 500-800 seeded chunks (achievable from a 1,684-chunk review pool post-noise-filter).
- Idempotent ingest pipeline via `scripts/seed_f321_phase1.py` (Phase E — gated on Chadi's reviewed `seeds/vocab/phase1.csv`).

**Pipeline shipped (Phases B/C/D):**
- **`app/services/f321_classifier.py`** — pre-classification filename + content publisher-import skip filters (catches CLE International / Hachette FLE / Claire Miquel / ISBN markers); duplicate-suffix collapse for `(1)`/`(2)`/`_-_Copie` variants; Haiku 4.5 classifier wrapper with 4-value verdict + source_type + suggested_topic_slug.
- **`app/services/f321_extractors.py`** — three extractors: table (python-docx 2-column FR/EN walker), regex (paragraph gloss patterns `FR (EN)` / `FR — EN` / `FR : EN`), Haiku-assisted (PARTIAL/NEEDS_MANUAL fallback with strict JSON-array output + lenient-parser fallback for max-token truncation).
- **`scripts/classify_f321_docx.py`** — Phase B runner (203 raw .docx → 170 post-dedup → classified via Haiku, retry on 429 with backoff). Cost: $0.20.
- **`scripts/extract_f321_phase1.py`** — Phase C runner. `--mode table-regex-only` for deterministic; `--mode validation` for the mandatory 5-file Haiku slice + Chadi sign-off gate; `--mode post-validation` after the gate marker file exists. Cost: $0.19 (Haiku slices).
- **`scripts/dedup_f321_phase1.py`** — Phase D runner. Noise filter drops exercise numbering / placeholder lines / section headers before hash dedup on normalized `chunk_fr`. Splits output into Phase 1 review CSV (3-topic scope + Les_Moules + preposition content-inference) and Phase 2 deferred CSV (everything else from chadi_authored + book_lab).
- **Tests:** `tests/test_f321_classifier.py` (33 cases) + `tests/test_f321_extractors.py` (20 cases) cover skip filters, dedup, gloss regex patterns, table column heuristics, Haiku response parser.

**Phase 1 pipeline numbers (2026-05-13):**
- 203 raw `.docx` → 170 post-dedup → 117 eligible (HIGH/PARTIAL/NEEDS_MANUAL with source_type ∈ {chadi_authored, book_lab}) → 6,462 raw chunks → 5,529 post-noise-filter → 4,483 unique post-dedup → **1,684 in Phase 1 review** + 2,799 in Phase 2 deferred.
- Phase 1 topic distribution: prepositions 941 / faux_amis 566 / calques_anglais 177.
- Phase 1 extractor distribution: table 1,196 / regex 306 / haiku 182.
- Phase 1 source_type: chadi_authored 1,547 / book_lab 137 (Les_Moules_Complete_Framework.docx).
- Estimated Chadi review burden: 2-3 hours (12 chunks/min triage pace).
- Total Phase B+C cost: $0.39 (ceiling $5.00, comfortably under).

**Hard exclusions (per audit lock + Decision F1 2026-05-13):**
- 17 files pre-skipped as `third_party_publisher_DO_NOT_EXTRACT` (filename patterns `*Progressif*` / `*Communication_Progressive*` / `*Niveau_*` + content markers CLE International / Hachette FLE / Claire Miquel / ISBN). Tagged but never sent to Haiku, never extracted.

**Phase E gate (next dispatch):**
- Chadi reviews `seeds/vocab/phase1_review.csv` offline. Marks each row `review_status` ∈ {accept, reject, edit}. Re-commits as `seeds/vocab/phase1.csv`.
- BE writes `scripts/seed_f321_phase1.py` — idempotent upsert (topic-on-slug + chunk-on-(topic_id, normalized chunk_fr)). Supports `--dry-run`.
- Seed ASK message surfaces per gate #7 (destructive prod DB INSERT): inline script + dry-run output + sample 10 rows + post-seed validation queries + rollback SQL.

**Out of scope (this dispatch):** Phase E seed; F-321.curriculum (60-file L'École redirect — filed separately); Phase 2 topic expansion (subjonctif_emploi / faire_causatif / others); Wiktionary FR + Tatoeba ingests (F-312); exam-specific tagging (F-330.partition).

**Depends on:** F-320 (schema), F-321.audit (sample-audit gate — verified).

**Owner:** BE (pipeline shipped) + Chadi (artifact archive owner + offline `phase1_review.csv` review + post-extraction correction).

---

## F-321.curriculum — Route L'École content out of Le Vocabulaire (BE)
Milestone: M4

**Filed:** 2026-05-13 (during F-321 implementation — audit identified ~60 `.docx` files as foundation-grammar content that belongs in L'École's 16-lesson surface, not Le Vocabulaire's lexical-chunk catalog).
**Status:** Queued.
**Tag:** Post-launch P2 — defer until F-321 Phase E seeds the 3-topic Phase 1 corpus and Le Vocabulaire surface is in production.
**Parent:** F-330.

**Priority:** Medium (post-launch).

**Scope:**
Route ~60 L'École curriculum files identified during F-321.audit (foundation grammar — articles, COD/COI, subjonctif, prépositions, faire causatif, conditional, conjugation) to L'École's existing 16-lesson surface (P-053). Decide per-file:
- **Extends existing lesson:** file content augments a lesson already in the seed (e.g., `cours_articles_*` files → extends the articles lesson; `Phase_3_Pronoms_Relatifs_Egor_COMPLET.docx` → extends the pronouns lesson).
- **Seeds new lesson:** file is a coherent unit not currently covered (e.g., `Le_Faire_Causatif.docx` → new lesson if Phase 2 Approfondissement has the slot).
- **Absorbed into module library (F-080):** file is a remediation pattern not a lesson (e.g., L1-interference notes → seed a `RemediationModule` row).

**Inputs:**
- `data/f321_extraction.csv` already contains the chunks from these files (tagged `source_type='chadi_authored'`, ended up in `phase2_deferred.csv`).
- The classifier `suggested_topic_slug` field is the per-file topic hint (`subjonctif_emploi`, `articles_french_with_languages_quantifiers`, etc. — anything outside the locked Phase 1 trio).
- L'École's existing 27-lesson sequence (16 Phase 1 Fondations + 11 Phase 2 Approfondissement per F-087) is the routing target.

**Out of scope:** Le Vocabulaire Phase 2 topic expansion (separate ticket if/when launched). Authored content modifications (Chadi-only).

**Depends on:** F-321 Phase E seed (so we know which chunks landed in Le Vocabulaire vs need routing); F-080 module library; P-053 L'École curriculum.

**Owner:** BE (routing decisions + new-lesson seed scripts) + Chadi (per-file lesson-vs-module decisions).

---

# Post-launch P1 (2-4 weeks after launch)

## F-061.1 — Tache2Picker reads live BE catalog instead of hardcoded literal (FE)
Milestone: M3

**Filed:** 2026-05-13 (during F-BUGS-001-BE-A — Tâche 2 production-drift incident).
**Status:** Queued.
**Tag:** Post-launch P1 — regression prevention; high signal-to-effort.
**Owner:** FE.

**Priority:** Medium (defensive — would have surfaced the 2026-05-13 prod gap immediately on launch instead of waiting for Chadi to manually flag).

**Scope:**
- `components/speaking/Tache2Picker.tsx` currently renders a hardcoded `SCENARIOS` literal listing the 5 Tâche 2 scenario codes. This literal stayed in lockstep with the BE seed file (`scripts/seed_tache2_scenarios.py`) by author convention, NOT by build-time verification.
- Wire `Tache2Picker` to fetch `GET /api/conversations/scenarios` at mount, render the live BE catalog, drop the hardcoded literal.
- Add an empty-state branch: when the API returns `{"scenarios": []}`, render a "No scenarios available — contact support" surface instead of a silent empty picker.
- Loading state: render a 3-card skeleton while the fetch resolves. Error state: render "Failed to load scenarios — retry" with a retry button.

**Why now:** Pre-F-BUGS-001-BE-A (today), the BE seed never ran on prod from launch until 2026-05-13. The hardcoded FE literal listed 5 scenarios while prod served 0; every Tâche 2 conversation-start was a silent 404. Live-data binding would have surfaced an empty picker immediately on first load, escalating the bug days-or-weeks earlier.

**Out of scope:** Caching / SWR optimization (one-time fetch on Tâche 2 entry is fine for Phase 1 traffic levels); admin UI for scenario CRUD (separate ticket if/when needed).

**Depends on:** Nothing — `GET /api/conversations/scenarios` is already live (F-049 endpoint).

---

## F-BUGS-001-BE-A.content — Tâche 2 placeholder content replacement (BE seed + Chadi authoring)
Milestone: M3

**Filed:** 2026-05-13 (during F-BUGS-001-BE-A — first-ever prod execution of F-049 seeder exposed that the seed payload is placeholder text).
**Status:** Queued.
**Tag:** Post-launch P1 — HIGH priority for product quality but not blocking (users can interact with scenarios using placeholder content; the placeholders are structurally complete).
**Owner:** Chadi (content authoring) + BE (re-seed pipeline OR admin endpoint for content updates).

**Priority:** HIGH (defensible scenario quality is core to the Tâche 2 differentiator) but **not launch-blocking** — the placeholder briefs + examiner_persona + data_targets are structurally complete and yield a working end-to-end flow today; only the prose quality is degraded vs. Chadi's polished authoring.

**Context:**
Per `scripts/seed_tache2_scenarios.py` header (filed F-049): "Every brief, persona, and data_targets entry below is a placeholder that Chadi replaces before Day 7 with the authored text from the Yarden documents." The seed never ran on prod from launch until 2026-05-13 (F-BUGS-001-BE-A) so production users were 404'ing on every Tâche 2 start — but now that the seed has run, the placeholder content is live and visible to users.

Each of the 5 scenarios (`ami_demenagement`, `agence_voyages`, `bibliotheque`, `nouveau_collegue_quebecois`, `agence_immobiliere_canada`) has 3 fields needing replacement: `candidate_brief_{fr,en,es}`, `examiner_persona`, `data_targets`. Placeholders are marked with `# CHADI:` comments in the seed file.

**Scope:**
1. **Chadi:** author final FR/EN/ES briefs + examiner_persona + data_targets per scenario, sourced from Yarden Livraison 1 documents. ~5 × 3 fields = 15 text blocks; estimate 4-8 hours.
2. **BE:** when Chadi delivers the polished payloads, either:
   - Edit the seed file in-place and re-run the seeder (idempotent — upserts on `code`, overwrites placeholder text). Surfaces as gate #7 prod seed ASK per refined contract (see CLAUDE.md migration protocol). Single-shot replacement.
   - OR build a lightweight admin endpoint (`PATCH /api/admin/tache2/scenarios/{code}`) for in-place editing without a redeploy. Heavier engineering but enables future content-tuning without re-seed-execute cycles.

**Recommendation:** seed-file path (option 1). Tâche 2 scenario content is low-frequency-changed authored material; an admin endpoint adds surface area for low return.

**Depends on:** F-BUGS-001-BE-A (Tâche 2 catalog now live in prod — done).

---

## F-322 — Le Vocabulaire practice UI (FE)
Milestone: M4

**Filed:** 2026-05-12 (strategic session — Decision 3, MVP).
**Status:** Queued.
**Tag:** Post-launch P1 (Sprint 2 priority per strategic session 2026-05-12).
**Parent:** F-330.

**Priority:** Sprint 2 (post-soft-beta-launch).

**Scope (FE-only):**
- Practice mode UI: hide/reveal one language, self-grade (knew it | partial | didn't know), build personal lists from the current set.
- Topic browser surface (browse `vocab_topics`).
- Personal-lists CRUD UI.
- Consumes BE endpoints exposed by F-320 (GET /api/vocab/topics, GET /api/vocab/chunks?topic=..., POST /api/vocab/lists, etc. — endpoint surface filed at F-320 ship time).

**Owner:** FE.

---

## F-323 — Le Vocabulaire test UI (FE)
Milestone: M4

**Filed:** 2026-05-12 (strategic session — Decision 3, MVP).
**Status:** Queued.
**Tag:** Post-launch P1 (Sprint 2 priority per strategic session 2026-05-12).
**Parent:** F-330.

**Priority:** Sprint 2.

**Scope (FE-only):**
- Test mode UI: MCQ, matching (drag-drop), dropdown selection, exact-completion typing (Lexogoth Toolbox style).
- Scoring surface: per-question result + topic-level summary.
- Retake flow.
- Consumes BE endpoints from F-320.

**Owner:** FE.

---

## F-324 — Diagnostic ↔ Vocab link (BE + FE)
Milestone: M4

**Filed:** 2026-05-12 (strategic session — Decision 3, MVP / Sprint 2).
**Status:** Queued.
**Tag:** Post-launch P1 (Sprint 2 priority per strategic session 2026-05-12).
**Parent:** F-330.

**Priority:** Sprint 2.

**Scope:**
- **BE:** when a diagnostic flags an error (writing or oral), match the error's `couche` + `error_type` against `vocab_topics` and surface 1-3 suggested topic-slugs in the diagnostic response (`suggested_vocab_topics: [...]`).
- **FE:** render suggested topics as inline CTAs on the diagnostic results screen ("Practice this with Le Vocabulaire →").
- Mapping table: error_type → relevant topic_slugs (curated by Chadi; lives in `app/services/vocab_suggestions.py` as a static dict at MVP, promotable to DB-backed later).

**Depends on:** F-320 (vocab schema), F-321 (seed), V-016a methode_en_couches surface (shipped — error couche is already in diagnostic output).

**Owner:** BE + FE + Chadi (error-type → topic mapping).

---

## F-325 — Le Vocabulaire vocab browse (BE + FE)
Milestone: M4

**Filed:** 2026-05-12 (operating-contract dispatch — fills the BE endpoint gap left implicit at F-320 ship-time per BACKLOG line 1369).
**Status:** BE shipped (Phase B/C/D + commit). FE pending (filed as F-325.fe under separate dispatch).
**Tag:** Active — Launch Critical (gates F-322 FE practice UI + F-323 FE test UI + F-324 BE/FE diagnostic-vocab link).
**Parent:** F-330.

**Priority:** Launch.

**Scope (BE):**
- `GET /api/vocab/topics` — list with optional `corpus_partition` filter. Returns metadata for ALL partitions regardless of tier; each row carries a `locked: bool` reflecting whether the current user's tier permits chunk access. FE renders 🔒 upsell card on locked rows (Decision D2 approved 2026-05-12).
- `GET /api/vocab/topics/{slug}` — single topic + `chunk_count` (post-exclusion). Runtime tier gate on exam_tagged_* partitions (Decision D3); 404 on unknown slug; 403 with F-310 `tier_insufficient` body shape on tier mismatch.
- `GET /api/vocab/topics/{slug}/chunks` — paginated chunks with multi-filter: `cefr_level` (string), `exam_tag` (enum), `register` (enum). Pagination: `limit` default 50 / cap 100, `offset` default 0 (Decision D5). Ordering id ASC for stable pagination.
- Hard exclusion of `source_type='third_party_publisher_DO_NOT_EXTRACT'` from all chunk responses (Decision D4) — provenance pointers never served verbatim. `chunk_count` and pagination `total` reflect post-exclusion counts.
- Tier-gate is RUNTIME per-handler (not a DI factory) because the required tier depends on the topic's `corpus_partition`, decided per-slug, not per-route (Decision D3). Reuses F-310 contract via new `enforce_min_tier()` + `user_tier_satisfies()` helpers added to `app/services/tiers.py` (additive, no F-310 behavior change).
- Pytest convention introduced (Decision D6) — `tests/test_vocab_browse.py` with FastAPI TestClient, `pytest.ini` minimal config. Phase D smoke (`scripts/smoke_f325.py`) stays end-to-end against local Postgres.

**Scope (FE):** Filed as **F-325.fe** under separate dispatch. Vocab topic browser surface at FE route `/vocabulaire`. Renders locked-card upsell on `locked=true` rows. Consumes the 3 BE endpoints above.

**Out of scope:** Personal-lists endpoints (`POST/GET/DELETE /api/vocab/lists`, `POST /api/vocab/lists/{id}/chunks`, `POST /api/vocab/progress/{chunk_id}`) — filed under a later dispatch. F-322 / F-323 FE practice + test UIs remain FE-only as originally filed (BACKLOG lines 1356, 1375).

**Depends on:** F-320 (schema; ORM + pydantic shapes already in `app/models/vocabulaire.py` + `app/schemas/vocabulaire.py`).

**Owner:** BE (this ticket) + FE (F-325.fe).

**Smoke:** `scripts/smoke_f325.py` — empty-DB shape check + seeded fixture covering all filter / tier / pagination paths.

---

## P-107 — Soft satisfaction guarantee copy + refund flow
Milestone: TBD

**Filed:** 2026-04-30.
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Priority:** Medium (pre-launch).

Stub — spec TBD.

---

## P-108 — Pronunciation feedback (basic)
Milestone: TBD

**Filed:** 2026-04-30.
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Priority:** Medium (post-launch).

Stub — spec TBD.

---

## P-110 — Onboarding refinement (TCF-specific)
Milestone: TBD

**Filed:** 2026-04-30.
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Priority:** Medium (pre-launch).

Stub — spec TBD.

---

## P-211b — Render-time student-facing filter for cluster lesson body
Milestone: TBD

**Filed:** 2026-05-02.
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Priority:** Medium.
**Parent:** P-211.

P-211 ingests cluster `lesson_markdown` verbatim from the authored docs, including author meta-notes that are not student-facing — e.g. `## Why most students fail this in production`, `## Authoring notes (for Chadi, not for the student)`, `## Spiral connection (where this cluster comes back)`. The decision was: keep the source intact in the DB and decide what to render at the UI layer.

**Trigger:** when the cluster detail view (P-234) is implemented.

**Scope:** define the filter contract — either a section-heading denylist applied client-side, or a markdown delimiter pattern (`<!-- author -->`, `<!-- student -->`) that the authoring side starts emitting. Land filter logic in the frontend renderer; backend stays pristine.

---

## P-213 — Dialogue Box template authoring
Milestone: TBD

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation. Curriculum doc §10.2 / Block 5.

Stub migrated from FE. Author 30-50 Dialogue Box templates (Block 5) varied by context. Placeholders for detected data. Owner: Chadi (authoring). Depends on P-240 (prescription engine — Active LC). Full original body in FE BACKLOG until B-106 consolidation ships.

---

## P-220.z — Onboarding per-question illustrations and pastels (Phase 1 polish)
Milestone: polish-defer

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

## P-231 — Speaking dashboard
Milestone: TBD

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation. Curriculum doc §10.4 / §7.5.

Stub migrated from FE. Implement §7.5 — new surface drilled down from Speaking tab. Includes Block 3 (Recording Replay with Inline Diagnostics). Full original body in FE BACKLOG until B-106 consolidation ships.

---

## P-232 — Per-Tâche dashboards
Milestone: TBD

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation. Curriculum doc §10.4 / §7.6.

Stub migrated from FE. Three dashboards (T1, T2, T3). Block 3 reused. Depends on P-231. Full original body in FE BACKLOG until B-106 consolidation ships.

---

## P-233 — Curriculum view (path surface)
Milestone: TBD

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation. Curriculum doc §10.4 / §7.7.

Stub migrated from FE. New surface accessible from main nav. Includes Block 4 (Path Topography). Depends on P-203 + P-204 (shipped) + P-210 (shipped). Full original body in FE BACKLOG until B-106 consolidation ships.

---

## P-235 — Ceiling Marker Map
Milestone: TBD

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation. Curriculum doc §10.4 / Block 1.

Stub migrated from FE. Implement Block 1. Surfaceable from Overall Progress (method mode) and Curriculum view (method mode). Consumes P-200 marker firings (shipped). Full original body in FE BACKLOG until B-106 consolidation ships.

---

## P-236 — Mistake Repository
Milestone: TBD

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation. Curriculum doc §10.4 / Block 7.

Stub migrated from FE. Standalone tab inside Progress. Reads `user_cluster_events` (the append-only event log from P-204) — the composite (user_id, created_at) index supports the "newest events for user X" query at scale. Full original body in FE BACKLOG until B-106 consolidation ships.

---

## P-237 — Time-Adaptive UI (lean version)
Milestone: TBD

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation. Curriculum doc §10.4 / Block 6.

Stub migrated from FE. Implement Block 6 lean version. `daysUntilExam` reads + conditional rendering for Dialogue Box copy, Goulet Stack ordering, exam countdown weight, practice CTA emphasis. Full mode redesigns deferred to P-267 (Phase 2). Depends on P-230 + P-231 + P-233. Full original body in FE BACKLOG until B-106 consolidation ships.

---

## P-240b — Today's focus prose layer (Dialogue Box rendering)
Milestone: TBD

**Filed:** 2026-05-02 (split from P-240 plan-first scope).
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Priority:** Post-launch P1.
**Source:** LEMETHODIC-CURRICULUM v0.2 §7.2 Block 5 — "The Dialogue Box".
**Dependencies:** P-240 (shipped 2026-05-02) + P-213 (queued — Chadi authoring 30-50 templates).
**Trigger:** P-213 ships.

Render the Block 5 Dialogue Box prose layer in the `dialogue_box` slot of `TodayActionResponse` (already reserved as null in P-240's contract — purely additive).

Block 5 is "not a chart" — short Chadi-voice contextual messages with placeholders for detected data. Example from §7.2:

> "Last week you cleared 3 of your top 5 bottlenecks. Today's focus: relative pronouns. Why this one? Because it shows up in your last 4 Tâche 2 recordings, and it's blocking the leap to fluent question-framing."

P-213 produces 30-50 template variants (after good week, after plateau, after regression, mid-cluster, end-of-phase). P-240b is the engine that picks the right template given the user's current `reason_code` + recent UserClusterEvent history + cluster context, then fills the placeholders.

Algorithm scope (TBD when P-213 lands): keyed selection on `reason_code` + recency signals (e.g., regression + 3+ events in 7 days → "regression streak" template). Placeholder fill from already-shipped detection telemetry (cluster name, recording count, Tâche application, last fail timestamp).

Out of scope: Claude API call for prose generation. Templates are authored content — selection + fill is rule-based.

---

## P-241 — Cluster-level prescription
Milestone: TBD

**Filed:** 2026-05-01.
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Phase:** Phase 1 Architecture Rework.
**Source:** LEMETHODIC-CURRICULUM v0.2 §10.

Backend scope: engine logic for cluster-level prescriptions feeding P-240. Stub — full spec in `lemethodic-frontend/LEMETHODIC-CURRICULUM.md`.

---

## P-250 — Threshold calibration
Milestone: TBD

**Filed:** 2026-05-01.
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Phase:** Phase 1 Architecture Rework.
**Source:** LEMETHODIC-CURRICULUM v0.2 §10.

Backend scope: calibration tooling for tuning detector / scoring thresholds against real data. Stub — full spec in `lemethodic-frontend/LEMETHODIC-CURRICULUM.md`.

---

## P-251 — Lesson content delivery infrastructure
Milestone: TBD

**Filed:** 2026-05-01.
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Phase:** Phase 1 Architecture Rework.
**Source:** LEMETHODIC-CURRICULUM v0.2 §10.

Backend scope: storage + serve endpoints for lesson content. Stub — full spec in `lemethodic-frontend/LEMETHODIC-CURRICULUM.md`.

---

## P-260.5 — Author 3 TCF Canada mock exams for Sprint product
Milestone: TBD

**Filed:** 2026-05-02; **deferred 2026-05-03** to month-2 post-soft-beta launch event (Sprint product is not on the soft-beta surface).
**Status:** Deferred — month 2 launch event, ~12-18h authoring post-soft-beta.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Priority:** HIGH-when-triggered (Sprint product cannot ship without these mocks).
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

**Trigger:** month-2 post-soft-beta launch event. Soft-beta launches without the Sprint product surface; Sprint goes live alongside the month-2 announcement event. These mocks are the content blocker for that event.

---

## F-226 — FR voice audit + full-app sweep (tu-form vs vous-form)
Milestone: M2

**Filed:** 2026-05-04.
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Priority:** Medium-high (Phase 1 voice consistency — post-soft-beta).

FE flagged a Block 3 drift during the 2026-05-04 founder check-in: the locked spec is **tu-form** (informal, Chadi-tutor voice), but production is rendering **vous-form** across `/onboarding` + `EcoleReveal` + likely other surfaces.

**Scope:** full-app sweep of FR copy strings to enforce tu-form per the locked Block 3 voice spec.

Surfaces to audit:
- Onboarding (11 questions + helper copy + intro screen + waitlist).
- EcoleReveal post-onboarding screen.
- /ecole + L'École intro (will re-author under F-202 — coordinate).
- /progress dashboard copy (Snapshot, Today's focus reason-code variants, Goulet Stack, recent activity).
- /diagnostic feedback page copy.
- /speaking/* Tâche briefings + recording prompts + transcript review copy.
- /cluster/[slug] lesson body, exercise prompts, practice CTA copy.
- Auxiliary pages: /privacy, /terms, /refund, /signup, /login, error states, paywall copy.
- BE-side: any FR string in seeds, Tâche prompts, Tâche 1 opening lines, scoring rubric prose, detection rubric labels (`Cluster.labels` JSONB), exercise set prompts (`Cluster.exercise_set` JSONB), VocabularyTheme labels.

**Method:**
1. Grep FR-language source files (FE strings, BE seeds, JSONB seed loaders) for `vous`, `votre`, `vos`, conjugated `vous` verb endings (`-ez` second-person plural).
2. Manual review — many `-ez` endings are also imperative which is independent of formality.
3. Replace with `tu`, `ton`, `ta`, `tes`, second-person singular conjugations.
4. EcoleReveal verified flip end-to-end as the smoke case.

**Trigger:** Post-soft-beta. Soft-beta can ship with vous-form drift (functional, just off-voice); pre-public-launch must be tu-form throughout.

**Owner:** FE + BE (seed audit) + Chadi (FR review on edge cases — some second-person plural is genuinely contextual, e.g., when addressing a hypothetical interlocutor in a Tâche 2 scenario).

---

## B-101 — Legal entity decision
Milestone: M6

**Filed:** 2026-04-30.
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Priority:** Medium.

Stub — spec TBD.

---

## B-104 — Email marketing infrastructure
Milestone: TBD

**Filed:** 2026-04-30.
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Priority:** Medium.

Stub — spec TBD.

---

## B-105 — Analytics setup
Milestone: TBD

**Filed:** 2026-04-30.
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Priority:** Medium.

Stub — spec TBD.

---

## B-106 — BACKLOG architecture consolidation
Milestone: TBD

**Filed:** 2026-05-02.
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Priority:** Post-launch P1.
**Source:** Two-BACKLOG drift discovered during M-101a planning (2026-05-02).

**Scope:** pick a single canonical BACKLOG location and migration strategy. Today there are two BACKLOG files — one in `chadovsky/lemethodic-backend` (this repo, `## ID — Title` format, tag-grouped, regen-tooled) and one in `chadovsky/lemethodic-frontend` (`### ID — Title` format, week-grouped Shipped + scope-grouped Queued). Drift inventory at filing: 23 FE-only tickets, 43 BE-only tickets, 19 shared (6 title conflicts, 12 status conflicts including 7 BE-shipped-but-FE-says-Queued tickets). Neither file alone shows the full project.

Options to pick from:
- **(A) BE-canonical** — single file in this repo; FE Claude reads via raw URL or git submodule. Existing regen tooling works as-is. Requires FE workflow change.
- **(B) FE-canonical** — single file in frontend repo; BE Claude reads via raw URL. Requires migrating regen tooling + format conversion.
- **(C) Deduplicated repo** — extract BACKLOG to a third repo (or `lemethodic-meta` / `lemethodic-tickets`). Both Claudes read it. Cleanest separation but adds a repo and access pattern.
- **(D) Unified single BACKLOG in BE-canonical format** — migrate FE-only tickets into BE BACKLOG; deprecate FE's file with a one-line redirect. Use existing BE regen + tag scheme. Simplest end state.

Recommended path (per BE's drift report 2026-05-02): **D**. Reasoning: BE's tag-grouped + regen-tooled file is more current; migrating ~23 FE-only tickets is straightforward; deprecating the FE file removes a source of confusion; both Claude workflows update to read this file as source of truth.

**Trigger:** post-launch. Pre-launch the work is shippable on the existing two-file model with manual reconciliation; consolidation is structural debt cleanup, not a launch blocker.

**Risk if deferred:** continued drift. Each new ticket filed in the wrong file widens the gap. Mitigation: cross-post critical tickets between files manually until B-106 ships.

---

## C-100 — Clean up test user id=5 from production DB
Milestone: TBD

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation.

Stub migrated from FE. A test user (id=5) and any orphaned data it owns linger in production. Identify owned rows (recordings, conversations, user_cluster_*) and remove. One-shot SQL cleanup via DO Console or a one-shot script. Trivial scope. Full original body in FE BACKLOG until B-106 consolidation ships.

---

## F-109 — Full name not preserved end-to-end
Milestone: M1

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation.

Stub migrated from FE. Full-name field set during signup gets dropped or truncated somewhere in the BE/FE pipeline — round-trip doesn't preserve the original input cleanly. Investigate: signup endpoint validation, User.full_name persistence, /me serializer, FE display rendering. Bug fix; not a structural change. Full original body in FE BACKLOG until B-106 consolidation ships.

---

## M-101.z — Landing page custom hero asset + per-section icons
Milestone: polish-defer

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation. Filed during M-101 FE rebuild planning.

Stub migrated from FE. Author or commission the landing page's custom hero asset + per-section icons (Phase 1 polish). M-101a ships with placeholder/borrowed P-220 imagery; this ticket replaces with brand-specific assets. Same shape as P-220.z's per-question illustrations. Owner: Chadi (commissioning) + Engineering (wire-up). Trigger: post-launch when visual polish becomes priority over functional shipping. Full original body in FE BACKLOG until B-106 consolidation ships.

---

## M-102 — Convert Preply reviews to social proof
Milestone: polish-defer

**Filed:** 2026-04-30.
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Priority:** Medium.

Stub — spec TBD.

---

## M-107 — Express Entry Discord/Telegram outreach
Milestone: polish-defer

**Filed:** 2026-04-30.
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Priority:** Medium.

Stub — spec TBD.

---

## M-108 — Beta user testimonial pipeline
Milestone: M8

**Filed:** 2026-04-30.
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Priority:** High.

Stub — spec TBD.

---

# Post-launch P2 — signal-driven

## P-102 — Visual quality pass
Milestone: TBD

**Filed:** 2026-04-30.
**Status:** Queued.
**Tag:** Post-launch P2 — signal-driven (defer until real signal).

**Priority:** Medium (post-launch).

Tailwind UI template, ~$300 budget. Stub — spec TBD.

---

## P-103.1 — Optional: tighter audio cap + duration enforcement
Milestone: TBD

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
Milestone: TBD

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

## P-104.x — Wall-clock setTimeout cap fallback for deep-throttle edge case
Milestone: TBD

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** Queued.
**Tag:** Post-launch P2 — signal-driven (defer until real signal).
**Parent:** P-104.

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation.

Stub migrated from FE. Sub-ticket of P-104 (background tab timer drift fix). When the browser deep-throttles tabs in the background past a threshold, even Date.now()-corrected timers can still drift; this ticket adds a wall-clock-cap fallback. Trigger: real-user reports of recording duration drift after P-104 ships. Full original body in FE BACKLOG until B-106 consolidation ships.

---

## P-109 — TCF Canada speaking simulator MVP
Milestone: TBD

**Filed:** 2026-04-30.
**Status:** Queued.
**Tag:** Post-launch P2 — signal-driven (defer until real signal).

**Priority:** High (pre-launch).

Stub — spec TBD.

---

## P-210.1 — Per-persona path forking
Milestone: TBD

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
Milestone: TBD

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
Milestone: TBD

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
Milestone: TBD

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
Milestone: TBD

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

## EX-100 — Evaluate execution tooling for ticket-by-ticket efficiency
Milestone: TBD

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** Queued — review needed.
**Tag:** Post-launch P2 — signal-driven (defer until real signal).

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation.

Stub migrated from FE. Cross-cutting tooling evaluation — review whether the current ticket-by-ticket execution flow (plan-first → spike → review → ship) has bottlenecks worth addressing (template scaffolding, repeated boilerplate, etc.). Trigger: post-launch retrospective. Full original body in FE BACKLOG until B-106 consolidation ships.

---

## M-106 — Blog launch
Milestone: polish-defer

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
Milestone: TBD

**Filed:** 2026-05-01.
**Status:** Deferred — Phase 2 (post-launch).
**Tag:** Phase 2 / deferred indefinitely.

**Phase:** Phase 2 (post-launch).
**Source:** LEMETHODIC-CURRICULUM v0.2 §10.

Backend scope: writing-track analysis pipeline. Stub — full spec in `lemethodic-frontend/LEMETHODIC-CURRICULUM.md`. Scope overlaps with P-300 (Writing pedagogy build) — reconcile when both specs exist.

---

## P-261 — Writing dashboard
Milestone: TBD

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** Deferred — Phase 2 (post-launch).
**Tag:** Phase 2 / deferred indefinitely.

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation. Curriculum doc §10.7.

Stub migrated from FE. Phase 2 dashboard surface for the writing track. Pairs with P-260 (writing analysis pipeline). Full original body in FE BACKLOG until B-106 consolidation ships.

---

## P-262 — Cross-modal prescription
Milestone: TBD

**Filed:** 2026-05-01.
**Status:** Deferred — Phase 2 (post-launch).
**Tag:** Phase 2 / deferred indefinitely.

**Phase:** Phase 2 (post-launch).
**Source:** LEMETHODIC-CURRICULUM v0.2 §10.

Backend scope: prescription that draws across modalities (oral + writing). Stub — full spec in `lemethodic-frontend/LEMETHODIC-CURRICULUM.md`.

---

## P-263 — A2 path full content
Milestone: TBD

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** Deferred — Phase 2 (post-launch).
**Tag:** Phase 2 / deferred indefinitely.

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation. Curriculum doc §10.7.

Stub migrated from FE. Author the full A2→B1 path content (Phase A2.1 through A2.4). Phase 2 — currently only B1→B2 ships in Phase 1. Owner: Chadi. Full original body in FE BACKLOG until B-106 consolidation ships.

---

## P-264 — B2→C1 path full content
Milestone: TBD

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** Deferred — Phase 2 (post-launch).
**Tag:** Phase 2 / deferred indefinitely.

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation. Curriculum doc §10.7.

Stub migrated from FE. Author the full B2→C1 path content. Phase 2. Owner: Chadi. Full original body in FE BACKLOG until B-106 consolidation ships.

---

## P-265 — C1→C2 path
Milestone: TBD

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** Deferred — Phase 2 (post-launch).
**Tag:** Phase 2 / deferred indefinitely.

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation. Curriculum doc §10.7.

Stub migrated from FE. Author the C1→C2 path. Phase 2 — out of scope for the Phase 1 product per curriculum doc §4.4. Full original body in FE BACKLOG until B-106 consolidation ships.

---

## P-266 — Tense + conjugation + idiomaticity detectors
Milestone: TBD

**Filed:** 2026-05-01.
**Status:** Deferred — Phase 2 (post-launch).
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

## P-268 — Audio-synced playback for Recording Replay
Milestone: polish-defer

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** Deferred — Phase 2 (post-launch).
**Tag:** Phase 2 / deferred indefinitely.

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation. Curriculum doc §10.7.

Stub migrated from FE. Sync audio playback with transcript word-level timing for Block 3 Recording Replay. Needs a streamed-audio endpoint (per P-103.2 design notes) + word-timing data from STT (already captured). Phase 2. Full original body in FE BACKLOG until B-106 consolidation ships.

---

## P-269 — Streak system
Milestone: polish-defer

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** Deferred — Phase 2 (post-launch).
**Tag:** Phase 2 / deferred indefinitely.

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation. Curriculum doc §10.7.

Stub migrated from FE. Daily streak tracking + UI surface. Needs persistence (BE-side: User.last_active_at + streak counter) + dashboard rendering (FE). Phase 2. Full original body in FE BACKLOG until B-106 consolidation ships.

---

## P-300 — Writing pedagogy build
Milestone: TBD

**Filed:** 2026-04-30 (renumbered from P-200 on 2026-05-01).
**Status:** Queued.
**Tag:** Phase 2 / deferred indefinitely.

**Priority:** High (Phase 2, post-launch).

Analysis prompts + 5-criterion scoring + diagnostic surface for the
writing track. Stub — spec TBD. Scope overlaps with curriculum P-260 (Writing analysis pipeline) — reconcile when both specs exist.

---

## P-301 — TEF exam support
Milestone: polish-defer

**Filed:** 2026-04-30 (renumbered from P-201 on 2026-05-01).
**Status:** Queued.
**Tag:** Phase 2 / deferred indefinitely.

**Priority:** Medium (Phase 2, post-launch).

Multi-exam routing (F-091) + TEF-specific prompts + TEF scoring
rubric. Stub — spec TBD.

---

## P-302 — DELF exam support
Milestone: polish-defer

**Filed:** 2026-04-30 (renumbered from P-202 on 2026-05-01).
**Status:** Queued.
**Tag:** Phase 2 / deferred indefinitely.

**Priority:** Medium (Phase 2, post-launch).

Stub — spec TBD.

---

## P-303 — Italian-audience expansion
Milestone: polish-defer

**Filed:** 2026-04-30 (renumbered from P-203 on 2026-05-01).
**Status:** Queued.
**Tag:** Phase 2 / deferred indefinitely.

**Priority:** Low (Phase 2, post-launch).

Per Chadi's noted interest in Italian-speaking French learners.
Stub — spec TBD.

---

## F-077.x — Convert JSON-as-Text columns to JSONB
Milestone: TBD

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
Milestone: TBD

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
Milestone: TBD

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
Milestone: TBD

**Filed:** 2026-04-30.
**Status:** Queued.
**Tag:** Phase 2 / deferred indefinitely.

**Priority:** Low.

Stub — spec TBD.

---

## B-200 — Book-Lab store surface
Milestone: TBD

**Filed:** 2026-05-04.
**Status:** Queued.
**Tag:** Phase 2 / deferred indefinitely.

**Priority:** Phase 2 (post-launch, post-revenue).

Book-Lab is Chadi's separate French learning publishing venture (shared methodology). Phase 2 surface — `/store` or `/books` on lemethodic.com — to upsell Book-Lab products to LeMethodic users + cross-pollinate audiences.

Out of scope for soft beta. Trigger: Book-Lab product catalogue stabilized **and** LeMethodic has paying users (signal threshold TBD).

**Owner:** Chadi.

---

# Closed

## M-105 — LinkedIn long-form content
Milestone: DONE

**Filed:** 2026-04-30; closed 2026-05-02.
**Status:** Closed — decided not to pursue. LinkedIn is the wrong audience for the visa-urgent persona; the B2B angle (immigration consultants / employer-sponsored TCF prep) is not a current channel and not a priority.
**Tag:** Closed — decided not to pursue.

**Re-open trigger:** B2B angle becomes a real channel (e.g., immigration-consultant referral pipeline material).

Original priority was Medium. Decided not to pursue per 2026-05-02 marketing triage — solo founder bandwidth is the binding constraint, and Reddit (M-104) + YouTube (M-103) cover the visa-urgent persona at lower cost with better audience fit.

---

# Shipped

## F-BUGS-001-BE-A — Tâche 2 agence_voyages production drift — SHIPPED 2026-05-13
Milestone: DONE

**Filed:** 2026-05-13 (Chadi flagged via FE-side 404 trace — every Tâche 2 conversation-start was returning `HTTP 404 "Unknown or inactive scenario_code 'agence_voyages'"`).
**Status:** Shipped 2026-05-13. Prod fix executed by Chadi via DO console + verified.
**Tag:** Shipped — bug fix.

**Root cause:**
The F-049 seeder (`scripts/seed_tache2_scenarios.py`) **never ran against production from launch until 2026-05-13**. Local dev DB had all 5 scenarios seeded (the seeder ran on every fresh dev checkout per `docker-compose up + alembic upgrade head + seed`); prod's `tache2_scenarios` table was empty. Every Tâche 2 conversation-start request hit the 404 branch in `app/routers/conversations.py:642`:

```python
scenario = db.query(Tache2Scenario).filter(
    Tache2Scenario.code == code, Tache2Scenario.is_active == True
).first()
if not scenario:
    raise HTTPException(404, f"Unknown or inactive scenario_code '{code}'")
```

Production was silently broken on the entire Tâche 2 surface from launch. The FE-side hardcoded `SCENARIOS` literal in `components/speaking/Tache2Picker.tsx` continued to render the picker as if the catalog existed — so users saw 5 selectable scenarios but every click 404'd. **Chadi was the first to flag** (no monitoring or canary caught it).

**Diagnosis pipeline (gate #7 ASK, 2026-05-13):**
1. BE-side investigation confirmed local DB had all 5 scenarios + `is_active=True`. Bug must be a prod-vs-local drift.
2. Gate #7 ASK surfaced two branches (Case A: row missing; Case B: `is_active=False`) with diagnostic query + matching fix + rollback for each.
3. Chadi ran `psql "$PROD_DATABASE_URL" -c "SELECT ... FROM tache2_scenarios WHERE code='agence_voyages';"` — result: `(0 rows)`. Full table query: 0 rows. **Case A confirmed; AND scope expanded to "all 5 scenarios missing, not just agence_voyages".**
4. Fix: `python -m scripts.seed_tache2_scenarios` via DO console. Output: `Seeded Tâche 2 scenarios: 5 inserted, 0 updated.`
5. Post-fix verification: 5 rows, all `is_active=True`, codes match canonical set (`ami_demenagement`, `agence_voyages`, `bibliotheque`, `nouveau_collegue_quebecois`, `agence_immobiliere_canada`).

**Regression canary:** `scripts/smoke_f_bugs_001_be_a.py` — local-Postgres FastAPI TestClient walk-through of GET `/scenarios` + POST `/start` with `scenario_code=agence_voyages`. 10 PASS checks. Asserts: seed row exists + is_active + difficulty=A2_B1; `/scenarios` lists agence_voyages; `/start` returns 2xx with conversation_id and tache_mode echo; unknown-code path still returns 404 (error path intact). Runnable as smoke after every BE deploy.

**Process learning — operating contract amendment (2026-05-13):**
This incident exposes a gap in gate #7 documentation: the migration protocol (CLAUDE.md "Production migration protocol") covers `alembic upgrade head` auto-application but says nothing about **seeder scripts**. Local seeder runs (the convention being "the seeder ran on fresh dev checkout") do not propagate to prod automatically because `alembic upgrade head` only runs migrations, not seed scripts. **CLAUDE.md migration protocol section amended in same commit** to flag seeder scripts as gate #7 prod-execution items alongside migrations: every future BE ticket involving a seeder script must include explicit "run the seeder on prod" step in the dispatch plan + a corresponding gate #7 ASK before the seeder fires.

**Follow-up tickets filed (same commit):**
- **F-061.1** (Post-launch P1, FE) — wire `Tache2Picker` to GET `/api/conversations/scenarios` live data instead of the hardcoded `SCENARIOS` literal. Would have surfaced this gap on launch day instead of waiting for Chadi to flag.
- **F-BUGS-001-BE-A.content** (Post-launch P1, Chadi + BE) — replace the placeholder briefs + examiner_persona + data_targets in `scripts/seed_tache2_scenarios.py` with Chadi's polished authoring per the `# CHADI: replace before Day 7` markers in the seed file. Placeholder content is structurally complete but reads as generic.

**Files in this commit:**
- `scripts/smoke_f_bugs_001_be_a.py` — regression canary (NEW)
- `BACKLOG.md` — this entry + F-061.1 + F-BUGS-001-BE-A.content
- `CLAUDE.md` — migration protocol: seeder scripts flagged under gate #7

No code change, no migration, no DB write from BE this commit. Prod fix already executed by Chadi.

---

## B-102 — Privacy policy + ToS + Refund
Milestone: DONE

**Filed:** 2026-04-30; **scope expanded 2026-05-03** to include the Refund page (originally just Privacy + ToS).
**Status:** Shipped 2026-05-03 (FE-side, `lemethodic-frontend` commit `3216d4d`). Three pages live at `/privacy`, `/terms`, `/refund` with footer integration on the landing page.

**Priority:** HIGH (pre-launch — required for paid product launch + LemonSqueezy storefront compliance).

Three legal/policy pages shipped as static FE routes:
- `/privacy` — privacy policy.
- `/terms` — terms of service.
- `/refund` — refund policy (added to scope alongside the LemonSqueezy pivot — Merchant of Record arrangement requires a clear refund stance).

Footer links on the landing page surface all three. Authoring owned by Chadi; rendering owned by Engineering (FE).

**BE role:** none. Pure static content + FE routing.

---

## F-079 — Custom domain wiring (lemethodic.com → Vercel)
Milestone: DONE

**Filed:** 2026-04-28; reframed 2026-05-02 (Vercel deploy already shipped).
**Status:** Shipped 2026-05-03 (DNS at Namecheap, A record `@` → `216.198.79.1`, Vercel auto-provisioned SSL via Let's Encrypt). Valid configuration verified end-to-end.

**Priority:** HIGH (pre-launch — without DNS the FE has no canonical production URL).

Shipped:
- ✓ Vercel deploy (pre-2026-05-02).
- ✓ DNS A record `@` → `216.198.79.1` configured at Namecheap.
- ✓ Vercel custom domain wired (`lemethodic.com` + `www`).
- ✓ HTTPS via Vercel-managed Let's Encrypt cert.
- ✓ Backend CORS allowlist: production origin injected via `FRONTEND_ORIGIN` env var on App Platform (no code change needed — `main.py` already reads this from env at boot).

**Owner shipped:** Chadi (DNS + Vercel) + Engineering (env config — no code commit required).

**Depended on:** F-078 (backend production URL — shipped earlier).

---

## F-110 — Recordings list endpoint
Milestone: DONE

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
Milestone: DONE

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
Milestone: DONE

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

## F-223 — "Le raccourci" copy bleed cleanup
Milestone: DONE

**Filed:** 2026-05-04.
**Status:** **Shipped 2026-05-06** — both FE-side (delete in `lemethodic-frontend` landed 2026-05-04) and BE-side (delete commit `e7d0ea1` 2026-05-06) complete. Per Chadi 2026-05-06: log-pull verification skipped — Jinja templates dead by architecture (Next.js FE on Vercel handles all user-facing pages from `lemethodic.com`; BE FastAPI serves API endpoints only). Production verification 2026-05-06: `GET /` + `GET /admin` + `GET /writing` all return 404 (was 200 with Jinja); `/health` + `/api/writing/prompts` + `/onboarding/questions` + `/api/users/me` all unchanged. 5,358 lines of pre-rebrand HTML retired plus 23 lines of handler code in `main.py` + the unused `HTMLResponse` import.

**Priority:** Medium (consistency).

"Le Raccourci" was the original section name; renamed to "L'École". Stragglers exist in both repos (FE strings, BE seed data, copy docs). Full grep + replace.

**Verification:** zero matches for `raccourci` (case-insensitive) in shipped strings across both repos.

**Owner:** FE + BE.

---

## F-224 — Writing Dashboard build (FE consumer + prompt seed)
Milestone: DONE

**Filed:** 2026-05-04.
**Status:** **Shipped 2026-05-06** — v1 pack landed end-to-end with **real Claude-based 4-layer analysis** (not placeholder). BE schema migration `f4d5e6c7b8a9` (commit `ae785a4`) added 5 canonical columns + 2 CHECK constraints; legacy columns retained with auto-backfill. 14 v1 prompts seeded to prod DB by Chadi 2026-05-06; distribution verified `(1,B1)=6 / (2,B1)=4 / (2,B2)=1 / (3,B2)=3`. API-side independent confirmation 2026-05-06: `/api/writing/prompts` returns 14 rows with all 13 fields (8 legacy + 5 canonical). FE consumer is the next leg — strategic Claude drafts the FE prompt under the reverted protocol.

**Priority:** Medium.

### Discovery (2026-05-04)

The 2026-05-04 plan-first assumed empty BE writing surface. **Reality found during implementation:**

- `app/models/writing.py` — `WritingPrompt` + `WritingSubmission` ORM classes, shipped via `alembic/versions/57c313935953_initial_schema.py`.
- `app/routers/writing.py` — 4 endpoints, all live in production:
  - `GET /api/writing/prompts` (filterable by level)
  - `POST /api/writing/submit` (Claude-backed analysis, async)
  - `GET /api/writing/history/{user_id}` (auth-gated: own user or admin)
  - `GET /api/writing/submission/{submission_id}`
- `app/services/writing_analysis.py` — 405 LoC of Claude-based 4-layer methodology analysis (Sentence Architecture / Grammatical Accuracy / Lexical Appropriateness / L1 Interference). Returns scored feedback per layer + overall score + word count + per-error correction.
- `app/templates/writing.html` — legacy Jinja template (will be deleted under F-223 path-2 alongside `index.html`/`admin.html` once log pull confirms zero traffic).

**Implication for the (c) lock-in:** the (a) framing — "auto-graded analysis requires P-260 promotion" — is incorrect. The auto-graded analysis pipeline already exists. P-260's "writing analysis pipeline (Phase 2 deferred)" labeling is BACKLOG-codebase desync (observation; not a new ticket — fold cleanup into F-226 voice-audit sweep if needed).

The (c) lock-in remains a defensible product choice (render submissions without surfacing analysis to keep soft-beta expectations conservative), but it's no longer constraint-driven — the FE consumer can choose whether to render the existing analysis or hide it behind a placeholder. Decision deferred to FE plan-first turn for F-224 FE.

### BE-side scope shipped this round (commit `3ac274c`)

- **Seed relocation + cleanup** (`scripts/seed_writing_prompts.py`, replaces root-level `seed_writing_prompts.py`): 18 prompts (7 B1 + 7 B2 + 4 C1) across argumentative / essay / formal_letter / opinion_essay types. Accents normalized (older B1+C1 batches were ASCII-stripped — `commande` → `commandé`, `Ecrivez` → `Écrivez`, etc.). Drops `Base.metadata.create_all()` (Alembic owns schema post-F-077). Idempotent: re-runs skip existing prompts via prompt_text match.
- **Production seed pending Chadi:** `python -m scripts.seed_writing_prompts` against prod DB (same pattern as `seed_b1_b2_path.py` / `ingest_b1_b2_cluster_content.py`). Local DB seeded + verified — endpoint returns 18 prompts, distribution correct per level.

### FE-side scope (next FE prompt after F-221)

Build the `/writing` dashboard consuming existing BE endpoints. Decisions to surface in the FE plan-first turn:

- Render existing analysis (4-layer feedback) or hide behind a "Analysis coming Phase 2" placeholder per (c) lock-in?
- Submission UX: prompt picker → composition → submit → feedback view.
- History list visual treatment (list rows vs grid cards).
- Empty state when user has zero submissions.
- Visual identity per locked direction (EMDL + fluentpath.ai + Neuralink).

**Owner:** BE (seed relocation, this round — Awaiting Verification) → FE (dashboard consumer, next round).

---

## P-103 — Audio upload security hardening (user_id-prefixed storage keys)
Milestone: DONE

**Filed:** 2026-04-30.
**Status:** Shipped 2026-05-01 — sub-item 2 (user_id-prefixed keys + helper). Sub-items 1 and 3 closed during scoping.
**Priority:** HIGH (pre-launch blocker).

Originally three sub-items (size cap, user_id ownership, auth-checked serve). Audit on 2026-05-01 found:

- **Sub-item 1 — size cap:** already shipped as F-075a (two-layer defense, 10 MB cap, 413 response, verification harness in `scripts/verify_f075a_size_cap.py`). No further work in P-103. Optional follow-up tracked in **P-103.1**.
- **Sub-item 2 — user_id ownership:** shipped 2026-05-01. New helper `app/services/storage.py::user_upload_key(user_id, ext)` returns `uploads/{user_id}/{uuid4}.{ext}`. The four upload sites (`recordings.py::upload_and_analyze`, `recordings.py::transcribe_only`, `audio.py::upload_and_transcribe`, `conversations.py::append_turn` legacy F-048 path) now route through it. Migration: Option A — old recordings stay at `uploads/<uuid>.<ext>` and both shapes coexist forever; any future read path must accept both. The "candidate audio is write-only from the API surface" invariant is documented in the storage.py module docstring.
- **Sub-item 3 — auth-checked serve:** no current serve endpoint for candidate audio (audit confirmed — the conversation turn serializer at `conversations.py::_serialize_turn` deliberately filters candidate `audio_url` out of responses, and there is no `/api/recordings/{id}/audio` endpoint). Closed; deferred to **P-103.2** if/when a playback feature is specified.

**Estimate:** delivered.

---

## P-104 — Background tab timer drift fix
Milestone: DONE

**Filed:** 2026-04-30.
**Status:** Shipped 2026-05-01 (FE-side, commit `fluentpath-frontend@48b61a1`).

**Priority:** HIGH (pre-launch blocker).

Recording timer drifted when the browser tab was backgrounded — Chrome throttles `setInterval` / `setTimeout` callbacks in hidden tabs (≥1Hz cap, paused entirely under intensive throttling after ~5 min hidden + 30s idle). The original counter-based pattern (`setInterval(() => onTick(remaining - 1), 1000)`) drifted by N seconds for every N missed ticks.

Fixed FE-side via wall-clock reconciliation:
- `components/speaking/CountdownTimer.tsx` (F-076) — owned-mode polls every 250ms, but each tick computes `Math.floor((Date.now() - startTime) / 1000)`. Wall-clock-immune. `visibilitychange` listener forces immediate tick on refocus.
- `hooks/useAudioRecorder.ts` (P-104, 2026-05-01) — `durationMs` driven by `Date.now()` deltas (not `performance.now()`, which Chrome throttles). `visibilitychange` listener forces recompute on refocus so downstream `useEffect([durationMs])` watchers — including per-Tâche cap auto-stops — fire promptly.

**No BE role.** Confirmed 2026-05-03 plan-first investigation: `duration_seconds` arrives as a Form field on `/api/recordings/upload` + `/api/conversations/turn/upload` and is stored verbatim — client-reported metadata, not authoritative for STT/analysis. The audio file itself is the source of truth. No server-side timing reconciliation needed by product design (no scoring/billing fraud vector). Web Worker timer (option B) ruled out — Chrome page-visibility throttling now applies to dedicated workers too. Server-side validation (option C) ruled out — adds latency without product benefit.

P-104.x (deep-throttle setTimeout fallback for the 5+ min unattended case) remains FE-side, deferred. Stays on FE BACKLOG; not migrated to BE.

---

## P-200 — Diagnostic engine: detector implementation
Milestone: DONE

**Filed:** 2026-05-01.
**Status:** Shipped 2026-05-02 (BE only — no FE consumer yet; the dashboard reads will land with §7 dashboard work).

Commits (3-commit set):
- Migration: `c4f2d1e3a0b5_p200_detection_columns.py` — adds `last_detection_result` on `user_cluster_statuses` (CHECK ∈ {clean, wobble, fail, not_observed}) and `findings_json` JSONB on `user_cluster_events`.
- Engine: `32bce5b` — `app/services/detection.py` (cluster detection via Claude, modeled on `module_detector.py` F-080b pattern), `app/schemas/detection.py` (Pydantic), `app/services/cluster_status_persistence.py`.
- Integration: `54e2040` — wires `detect_clusters` into `analyze_tache_1/2/3` after F-080b's `detect_modules`; wires `persist_detection_result` into both finalization paths (`recordings.py /upload` for Tâche 3; `conversations.py /end` for Tâche 1+2). Failure isolation identical to F-080b — never blocks the recording response.

**Production:** detection now runs on every new recording across all 3 Tâches. Cluster findings persist to `user_cluster_statuses` (latest snapshot) + `user_cluster_events` (per-recording payload in `findings_json`). Lifecycle (`status` column) untouched — that axis remains independent and will be driven by P-241 (cluster-level prescription).

**Phase:** Phase 1 Architecture Rework.
**Source:** LEMETHODIC-CURRICULUM v0.2 §10.

Backend scope shipped: one Claude call per recording (Q2 decision), filtered to clusters where `tache_application == recording.tache_mode` AND `detection_rubric.markers` is non-empty (placeholders B1.4 + B1.5 excluded automatically). Per-cluster best-effort parsing in `_coerce_payload` — one malformed finding doesn't lose the rest. 34 smoke checks pass (`scripts/smoke_p200.py`). Calibration is post-launch (P-250).

---

## P-201 — Diagnostic engine: level assignment + confidence
Milestone: DONE

**Filed:** 2026-05-01.
**Status:** Shipped 2026-05-02 (BE only — FE consumer is the §7 dashboard work). **P-201.x follow-up shipped 2026-05-03** (commit `2b13b01`) — adds `total_clusters_in_path` to `AssignedBlock` so the FE can render "8 of 13 areas evaluated" without deriving the denominator from `n_clusters_evaluated / coverage`.

Commits (2-commit set + 1 follow-up):
- Migration: `247a44e` — `d7e4f3c2b1a9_p201_user_level_assessments.py`. Append-only `user_level_assessments` table with CHECK constraints on `assigned_level` (∈ below_B1 / B1_emerging / B1_solid / above_B1 / insufficient_data) and `assigned_confidence` (∈ high / medium / low). Composite index `(user_id, computed_at)` for the "latest assessment for user X" query.
- Service + endpoint + integration: `ecf8e21` — `app/services/level_assignment.py` (rule-based algorithm: hybrid coverage × agreement, hardcoded thresholds), `app/schemas/level.py` (Pydantic dual-axis response), `GET /api/users/me/level` endpoint, trigger hooks in `recordings.py` + `conversations.py` (fires when `recording_count >= 3`, F-080b/P-200 failure isolation), `scripts/smoke_p201.py` (8 steps, 49 checks).
- **P-201.x follow-up: `2b13b01`** — `total_clusters_in_path: int` on `AssignedBlock` (P-230 dashboard prep). Computed in users.py from the frozen ratio: `round(n_eval / coverage)` when coverage > 0; 0 on the degenerate coverage=0 case (which by construction implies n_eval=0 — trigger early-returns before persisting). No alembic migration; the denominator is recoverable from existing persisted fields with float64 precision sufficient for the small-integer regime. Frozen-at-assessment-time semantics: a user assessed when path=13 keeps total=13 even after curriculum growth — assessment reflects the path state at compute time. Smoke updates to smoke_p201.py + smoke_p221.py — both PASS. Production verified: AssignedBlock now exposes `[level, confidence, coverage, n_clusters_evaluated, total_clusters_in_path, computed_at]`.

**Production:** dual-axis level reporting now live. `GET /api/users/me/level` returns `{self_reported, assigned, agreement}` for any authenticated user; `assigned` block populates after the user has 3+ recordings; `agreement` field signals `matches | discrepancy | self_only | assigned_only | neither` so the FE can render at-a-glance.

**Honest level labels** (below_B1 / B1_emerging / B1_solid / above_B1 / insufficient_data) instead of raw CEFR codes — Phase 1's 13 authored clusters are all B1, so we directly validate B1 but only INFER above/below. Labels graduate to {A2, B1, B2, C1} when other-level curriculum content lands (P-211b).

**Phase:** Phase 1 Architecture Rework.
**Source:** LEMETHODIC-CURRICULUM v0.2 §10.

Backend scope shipped: trigger fires `recording_count >= 3` (any Tâche distribution); algorithm reads latest detection per cluster from `user_cluster_statuses`; cluster denominator dynamic via `_count_active_clusters_for_user_path` (generalizes when other paths land); INSERT-only writes preserve full assessment history for P-250 calibration + dashboard "level over time" surface (Block 8 Confidence Visualizer per §7). Threshold calibration deferred to P-250 against beta data.

---

## P-202 — Cluster data model
Milestone: DONE

**Filed:** 2026-05-01.
**Status:** Shipped 2026-05-01 (commit `d5595b3`).
**Phase:** Phase 1 Architecture Rework.
**Source:** LEMETHODIC-CURRICULUM v0.2 §10.

Backend scope: SQLAlchemy + Alembic schema for the cluster concept. Migration `a8f3e2c4b5d1` created `clusters`, `vocabulary_themes` (seeded with 27 §5.1 themes), with JSONB i18n labels and the prose-faithful `DetectionRubric` shape (relaxed in commit `11a175d` for P-211 ingest).

---

## P-203 — Path data model
Milestone: DONE

**Filed:** 2026-05-01.
**Status:** Shipped 2026-05-01 (commit `d5595b3`).
**Phase:** Phase 1 Architecture Rework.
**Source:** LEMETHODIC-CURRICULUM v0.2 §10.

Backend scope: SQLAlchemy + Alembic schema for the path concept (sequence of clusters). Migration `a8f3e2c4b5d1` created `paths`, `phases`, and `path_clusters` (join + ordering, with `is_optional` for persona compression).

---

## P-204 — User progress model
Milestone: DONE

**Filed:** 2026-05-01.
**Status:** Shipped 2026-05-01 (commit `d5595b3`).
**Phase:** Phase 1 Architecture Rework.
**Source:** LEMETHODIC-CURRICULUM v0.2 §10.

Backend scope: SQLAlchemy + Alembic schema tracking per-user progress through clusters and paths. Migration `a8f3e2c4b5d1` created `user_path_enrollments` (with partial unique index for one-active-enrollment-per-user), `user_cluster_statuses` (snapshot), and `user_cluster_events` (append-only log with `(user_id, created_at)` composite index for Block 7 Mistake Repository).

---

## P-210 — B1→B2 path seed (1 path, 5 phases, 22 cluster slots)
Milestone: DONE

**Filed:** 2026-05-01.
**Status:** Shipped 2026-05-01 (commit `79cd629`); production seeded same-day via `scripts/seed_b1_b2_path.py` against the prod DB.
**Phase:** Phase 1 Architecture Rework.

Idempotent one-shot seed. Cluster slugs follow the 4-segment marker convention (`B1.1.C1` .. `B1.5.C22`) so a marker_id like `B1.1.C1.a` maps cleanly back to its cluster. Lesson content, exercise sets, practice prompts, detection rubrics, and vocabulary theme assignments left empty — populated by P-211. See `scripts/seed_b1_b2_path.py`. Per-persona path forking deferred to P-210.1.

---

## P-211 — Cluster content authoring
Milestone: DONE

**Filed:** 2026-05-01.
**Status:** Shipped 2026-05-01 (commit `d862794`); production ingested same-day via `scripts/ingest_b1_b2_cluster_content.py` against the prod DB.
**Phase:** Phase 1 Architecture Rework.
**Source:** LEMETHODIC-CURRICULUM v0.2 §10.

Backend scope: data ingestion infrastructure for authoring cluster content. Parses the 4 vendored cluster docs in `docs/clusters/` (synced from `lemethodic-frontend/curriculum/clusters/`); for each of the 13 authored clusters writes `lesson_markdown`, `practice_prompt`, `detection_rubric` (prose-faithful per the relaxed schema), and updates `tache_application` to match the authored prompt header (7 of 13 flip from the seed default). The 9 placeholder clusters (B1.4 + B1.5) get a placeholder string. Ten markers in 2 clusters (B1.1.C1, B1.1.C2) auto-rewritten from legacy 3-segment to canonical 4-segment, with a loud warning summary — source-doc fix tracked in P-211a.

---

## P-212 — Starter cluster seed
Milestone: DONE

**Filed:** 2026-05-01; superseded 2026-05-02.
**Status:** Superseded by P-210 + P-211 (shipped 2026-05-01). The 22-cluster B1→B2 path is in production with 13 clusters fully authored and 9 placeholders pending Les Moules content. Nothing in P-212's original scope remains uncovered.

**Phase:** Phase 1 Architecture Rework.
**Source:** LEMETHODIC-CURRICULUM v0.2 §10.

Original scope (preserved for history): backend seed script populating the starter cluster set for soft-beta launch. Now covered by P-210 (`scripts/seed_b1_b2_path.py`, commit `79cd629`) for the 1 path / 5 phases / 22 cluster slots, and P-211 (`scripts/ingest_b1_b2_cluster_content.py`, commit `d862794`) for content. Both running against production.

---

## P-220 — Onboarding questionnaire rebuild
Milestone: DONE

**Filed:** 2026-05-01.
**Status:** Shipped 2026-05-02 (BE + FE + production verification complete).

Commits:
- BE backend: `4c272da` (POST /onboarding/submit + GET /onboarding/questions, schema migration `b3a55c1e0001`, Pydantic schemas, routing service, smoke).
- BE follow-up: `bb76eb8` (`interface_language` field — optional `Literal["en","fr"]`, persists to `User.ui_language`).
- FE rebuild: `ab524e1` (lemethodic-frontend — data-driven flow, 11 questions, en/fr i18n, EcoleReveal rewrite).

**Production verified:** `lemethodic-frontend.vercel.app/onboarding` walked through end-to-end. All 4 verification rounds green.

**Phase:** Phase 1 Architecture Rework.
**Source:** LEMETHODIC-CURRICULUM v0.2 §10; copy spec at `docs/P-220-onboarding-questionnaire-copy.md`.

Backend scope shipped: schema migration `b3a55c1e0001` (7 new User columns + `UserPathEnrollment.persona` with CHECK constraints), Pydantic schemas, FR + EN question content, routing service (Q1+Q2 → path slug; Q3 → persona; Q3+Q7 → capacity warning; Q11 → UI mode default), and 2 endpoints (`GET /onboarding/questions`, `POST /onboarding/submit`). Legacy `POST /api/users/onboarding` kept accept-and-no-op with a `Deprecation` header for the FE migration window. Q4-Q10 routing deferred to P-220.x. Q12 reminder time deferred to P-220.y.

---

## P-221 — Diagnostic flow integration
Milestone: DONE

**Filed:** 2026-05-01.
**Status:** Shipped 2026-05-02 (single commit `c475bb7`).

**Phase:** Phase 1 Architecture Rework.
**Source:** LEMETHODIC-CURRICULUM v0.2 §10.

Backend scope: read-only state machine over the 3-recording diagnostic flow. New endpoint `GET /api/diagnostic/state` returns `stage` (in_progress | complete | no_path), `recordings_done`, per-Tâche coverage, `next_recommended_tache`, and `latest_assessment_id`. Drives the FE banner on `/ecole` and the one-time diagnostic-results screen.

Plan-first lock-in (2026-05-02): Q1=(B) implicit-with-banner — first 3 recordings ARE the diagnostic, no hard gating. Q2=(B) `/ecole` with diagnostic banner — `redirect_to_diagnostic` becomes "show banner" rather than "navigate elsewhere". Q3=stage="complete" derived from "latest UserLevelAssessment exists" (no new column; converges with P-201's recording_count >= 3 trigger). Q4=(C) lightweight diagnostic-results screen as one-time gate (FE-side, consumes already-shipped data).

`AssignedBlock` on `GET /api/users/me/level` extended with `n_clusters_evaluated` so the FE results screen can render coverage telemetry without a second endpoint hit. Already persisted on `UserLevelAssessment`; just exposed.

No alembic migration. No new table, no new column. `recordings.py` / `conversations.py` untouched — purely additive.

Files: `app/schemas/diagnostic.py` (new), `app/services/diagnostic_state.py` (new), `app/routers/diagnostic.py` (new), `app/schemas/level.py` (extended), `app/routers/users.py` (pass-through), `main.py` (router registration), `scripts/smoke_p221.py` (new — 32 checks across 4 steps, all PASS).

Production verified 2026-05-02: 56 paths in `/openapi.json`, 27 schemas, `/api/diagnostic/state` registered, `DiagnosticStateResponse` + `TacheCoverage` schemas present, `AssignedBlock` carries `coverage` + `n_clusters_evaluated`.

FE follow-up (P-221.fe — file when needed): `/ecole` banner consuming `/api/diagnostic/state`, `/diagnostic/results` one-time gate consuming `/api/users/me/level` + `/api/diagnostic/state`. Out of BE scope.

---

## P-222 — Waitlist UX for A2 and B2+ paths
Milestone: DONE

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** Shipped 2026-05-03 (FE-side, `lemethodic-frontend` commits `59fb2c6` + `deff02b` + `820d788`). Production verified on `lemethodic.com/onboarding/waitlist`.

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation. Curriculum doc §8.4.

When a user's diagnostic places them on a not-yet-built path (A2→B1, B2→C1, C1→C2), the FE renders a waitlist screen at `/onboarding/waitlist` with explanation copy + optional fallback offer (b1_to_b2 preview when pedagogically plausible) + email capture for early-access notification.

**BE role:** none beyond what already shipped with P-220. The `OnboardingSubmitResponse` already carries `waitlist=true` + `waitlist_reason="path_not_active"` + `fallback_path_offered=<slug | null>` on the relevant level pairs. FE consumes these and renders accordingly.

**Email capture wiring:** FE-side only for now (likely posting to a third-party form / email tool). If a BE endpoint becomes necessary, file as P-222.x — currently not needed since the FE flow is self-contained.

**FE consumer of P-220 contract:** verified end-to-end against production API. Q1=`not_sure` users correctly bypass waitlist into b1_to_b2; A2→B1, B2→C1, C1→C2 users correctly land on the waitlist screen with localized reason copy mapped from the `waitlist_reason` slug.

---

## P-230 — Overall Progress dashboard rebuild
Milestone: DONE

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** v1 shipped 2026-05-03 (FE-side, `lemethodic-frontend` 3-commit set ending `28bf765`); **deemed insufficient for soft-beta 2026-05-04** — sections render but feel placeholder-y. Real content + depth rebuild filed as **P-230.depth** (Active LC). v1 entry preserved here for ship-history; depth work tracked in the new ticket.

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation. Curriculum doc §10.4 / §7.4.

`/progress` rebuilt per curriculum doc §7.4 — Calm mode (default) layout: Snapshot (Block 8 Confidence Visualizer) + Today's focus (Block 5 Dialogue Box, fallback copy keyed on `reason_code` until P-240b ships) + Goulet Stack (Block 2, top 3 bottlenecks) + Recent activity calendar. Method mode opt-in toggle adds Block 1 Ceiling Marker Map and Block 7 Mistake Repository link. Replaces the original P-100 surface entirely.

**BE consumer surfaces:**
- `GET /api/users/me/level` — Snapshot block reads `assigned.level / confidence / coverage / n_clusters_evaluated / total_clusters_in_path` (P-201 + P-201.x).
- `GET /api/users/me/today` — Today's focus reads `action.{kind, cluster_slug, tache_application, practice_prompt, reason_code}` + `context.{current_phase_position, clusters_remaining_in_path, last_recording_at}` (P-240). Renders FE-authored fallback copy keyed on `reason_code`; `dialogue_box` field stays null until P-240b.
- `GET /api/users/me/recurring_modules` — feeds the Goulet Stack (F-080d, pre-existing).

**BE role this ticket:** none beyond what already shipped. P-201 + P-201.x + P-240 + F-080d covered the full data surface.

**FE follow-up (filed elsewhere):** Block 1 Ceiling Marker Map = P-235; Block 7 Mistake Repository = P-236; Block 6 Time-Adaptive UI = P-237. All Post-launch P1.

---

## P-240 — Today's recommended action
Milestone: DONE

**Filed:** 2026-05-01.
**Status:** Shipped 2026-05-02 (single commit `6b8ee43` — action layer). Prose layer deferred as **P-240b** (Post-launch P1, blocked on P-213).

**Phase:** Phase 1 Architecture Rework.
**Source:** LEMETHODIC-CURRICULUM v0.2 §10.5 (drives §7.4 section 2 "Today's focus" surface).

Backend scope: read-only prescription engine over user's enrolled path. New endpoint `GET /api/users/me/today` returns `action` (kind / cluster_id / cluster_slug / tache_application / practice_prompt / reason_code), `context` (current_phase_id / current_phase_position / clusters_remaining_in_path / last_recording_at), and `dialogue_box` (reserved null slot for P-240b prose layer). Replaces the hardcoded "Tâche 2 · Agence de voyages" DailyActionCard on /ecole.

Plan-first lock-in (2026-05-02): rule-based not LLM (Q2) — 13-cluster Phase 1 inventory makes LLM overkill, latency-sensitive hot path, determinism over creativity. On-demand not cached (Q3) — <10ms total query cost, cache invalidation harder than the savings. Separate endpoint not embedded in `/diagnostic/state` (Q4) — different lifecycles (diagnostic state is set-it-and-forget-it, today's action evolves on every recording). Scope split (Q1) — action layer this commit, prose layer P-240b.

Rule chain (first-match-wins, factored in `app/services/recommendation.py::_pick_cluster` so P-241 can import it for hard navigation gating):

1. `regression` — any cluster with `last_detection_result == "fail"` (even when lifecycle status is `absorbed`). The "regression on what user thought was solid" case dominates needs_revisit.
2. `needs_revisit` — `status == "needs_revisit"`.
3. `in_progress` — `status == "in_progress"`. Consistency wins over advancing.
4. `next_in_path` — lowest-position `not_started` cluster (rows missing from UserClusterStatus treated as not_started).
5. `free_practice` — all path clusters absorbed, no active fail.
6. `no_path` — no active enrollment (mirrors `/api/diagnostic/state`'s `no_path` semantics).

Tiebreak across multiple matches within a rule: lowest `PathCluster.position` (advance the path linearly).

`UserPathEnrollment.current_phase_id` / `current_cluster_id` cache columns exist but have ZERO writers in app code (verified via grep, 2026-05-02). Algorithm derives current cluster + phase on-the-fly from `UserClusterStatus` + `PathCluster.position` ordering. Revisit caching once a writer ships.

Files: `app/schemas/today.py` (new), `app/services/recommendation.py` (new), `app/routers/today.py` (new), `main.py` (router registration), `scripts/smoke_p240.py` (new — 33 checks across 4 steps, all PASS).

No alembic migration. No new table, no new column. `recordings.py` / `conversations.py` / `users.py` untouched — purely additive.

P-241 (cluster-level prescription / hard navigation gate) imports `_pick_cluster` directly when it ships; same rule chain, different enforcement teeth.

FE follow-up (P-240.fe — file when needed): replace `DailyActionCard` hardcoded content on /ecole's HomeScreen with a fetch-and-render against `/api/users/me/today`. Out of BE scope.

---

## M-100 — Past Preply student outreach
Milestone: DONE

**Filed:** 2026-04-30.
**Status:** Shipped 2026-05-03 (re-engagement outreach to past Preply students completed by Chadi).

**Priority:** HIGH (highest leverage, costs zero).

Re-engagement angle, not first contact. Outreach delivered.

---

## M-101 — Landing page copy in LeMethodic voice
Milestone: DONE

**Filed:** 2026-04-30.
**Status:** Shipped 2026-05-03 (landing page on `lemethodic.com` renders the LeMethodic-voice copy from the authored doc; M-101a delivered the FE implementation).

**Priority:** High.

Authored copy in LeMethodic voice (Chadi's tutoring tone, 4-couches framing, anglophone-Canadian beachhead positioning) is live at `lemethodic.com` via the M-101a implementation ship. Three pricing cards, Sprint waitlist CTA, footer integration with `/privacy` + `/terms` + `/refund` (B-102). Verified end-to-end on production.

Out of scope (filed elsewhere): hero asset polish + per-section illustrations → **M-101.z** (post-launch P1).

---

## Data Layer (D-tickets)

### D-001 — Step 0 scaffolding ✅ DONE
Milestone: DONE
Scaffolded `data-layer/`: Makefile, `sql/001_schema.sql`, `scripts/common.py`, ingestion framework (`base.py`), 2 full parsers + 5 skeletons, enrichment runner, vectorize, review/audit harness. Reference: `data-layer/README.md`.

### D-002 — Environment setup ✅ DONE
Milestone: DONE
`docker-compose up -d` → pgvector/pgvector:pg16 container live on port 5432; `data-layer/.env` populated (DB URL + Groq key).

### D-003 — Apply schema ✅ DONE
Milestone: DONE
`sql/001_schema.sql` applied via `make schema`; `chunks` table + ancillary tables created with pgvector extension enabled.

### D-004 — Capture decisions ✅ DONE
Milestone: DONE
`make decide` ran and persisted the corpus-source decision log (PARSEME / CollFrEn / DBnary / Anki / Lexique3 / UniversalCEFR / Tatoeba in scope) into the run artifacts.

### D-010 — Implement PARSEME ingestion ✅ DONE
Milestone: DONE
`data-layer/scripts/ingest/parseme.py` — `.cupt` parser groups tokens by MWE id (one chunk per MWE), handles discontinuous spans, skips multi-word ranges + empty nodes, maps all 8 PARSEME categories (VID / IRV / LVC.* / VPC.* / MVC / IAV) to chunk_type. Live corpus pivot to `gitlab.com/parseme/sharedtask-data 1.2/FR` documented in NOTES (1).

### D-011 — Implement CollFrEn ingestion ✅ DONE
Milestone: DONE
`data-layer/scripts/ingest/collfren.py` — openpyxl reader for `FR_disambiguated_SyntagmaticLF_v1b.xlsx` pairs KEYWORD/VALUE into bilingual FR-EN collocation chunks; strips `_..._` + `[…]` markers; uses postposed `~` subcategorisation column to order value-first vs. keyword-first.

### D-012 — Implement DBnary ingestion ✅ DONE
Milestone: DONE
 d-022/dbnary-debug
Status: ✅ DONE
File: data-layer/scripts/ingest/dbnary.py
Delivered: streaming Turtle parser (quote-aware subject-block splitter + per-block rdflib parse + cross-subject reference caches) that emits chunks with surface_fr, pos_pattern, English translations, and FR examples — avoids the multi-GB OOM of naive `rdflib.Graph().parse()`. (Initial implementation shipped only smoke-tested against synthetic Turtle; the real-corpus follow-up is D-022, which made the parser actually emit chunks against the live `fr_dbnary_ontolex.ttl` dump.)

`data-layer/scripts/ingest/dbnary.py` — streaming Turtle parser (quote-aware subject-block splitter + per-block rdflib parse + cross-subject reference caches) emitting surface_fr / pos_pattern / EN translations / FR examples; avoids multi-GB OOM of naive `rdflib.Graph().parse()`. (Debugging follow-on lives in D-022.)
 master

### D-013 — Implement Anki ingestion ✅ DONE
Milestone: DONE
`data-layer/scripts/ingest/anki.py` — per-model field-order dispatch across multi-model `.apkg` decks (one deck may bundle 17 note types); HTML / cloze / entity / style stripping; validated against two AnkiWeb decks.

### D-014 — Validate Tatoeba example-attachment ✅ DONE
Milestone: DONE
`data-layer/scripts/ingest/tatoeba.py` — validated 8/8 attachments on a 5-chunk sample; fixed punctuation-stripping bug in tokenizer; profiled n-gram lookup at 200k×21k (21.6s) → DB insert is the bottleneck, prefix-tree not warranted.

### D-020 — Run ingest pipeline 🟡 IN PROGRESS
Milestone: TBD
Status: IN PROGRESS — split by source. `make ingest` is no longer a single unattended run; each source has its own state because of corpus-availability + parser-debug surface area.

 docs/backlog-may15
| Source | Status | Notes |
|---|---|---|
| PARSEME | ✅ | 8,196 chunks (post synthetic-fixture cleanup; from `gitlab.com/parseme/sharedtask-data 1.2/FR` — see NOTES 1 + 3) |
| CollFrEn | ✅ | 6,627 chunks |
| AnkiWeb | ✅ | 5,005 chunks |
| Lexique3 | ✅ | 125,652 chunks |
| UniversalCEFR | ✅ | 1,336 chunks (French only, post English cleanup — uses `readme_fr` not `cefr_sp_fr`; see NOTES 2) |
| Tatoeba | ⏳ | in flight, ~728k+ examples attached and counting |
| DBnary | ❌ | BLOCKED on D-022 debug agent |

### D-021 — Groq enrichment integration 🟡 IN PROGRESS
Milestone: DONE
Agent on `d-021/groq-enrichment`. Replaces the original "run enrich pipeline" placeholder. Llama 3.3 70B via Groq's OpenAI-compatible endpoint; key in `data-layer/.env` (gitignored); rotation done post-exposure (see NOTES 4). Provider wiring shipped (`feat(D-021): add Groq LLM provider for enrichment`); WIP on universal_cefr enrichment path.

### D-022 — DBnary parser debug 🟡 IN PROGRESS
Milestone: DONE
Agent on `d-022/dbnary-debug`. Replaces the original "run vectorize pipeline" placeholder. After streaming-parser fixes the parser currently produces ~944 rows / 72s on the diagnostic slice; smoke harness at `data-layer/tests/smoke_dbnary_slice.py` + `tests/diagnose_dbnary.py`. Unblocks the DBnary row in D-020.

### D-023 — Wikipedia FR cultural ingester 🟡 IN PROGRESS
Milestone: TBD
Agent on `d-023/wikipedia-fr-cultural`. Targets DELF + AP coverage (cultural reference base — French-canonical articles, register-rich prose). Source survey + parser scaffold in flight.

### D-021 — Groq LLM provider for enrichment ✅ DONE
Milestone: DONE
Status: DONE (2026-05-15)
File: data-layer/scripts/enrich.py, data-layer/scripts/test_groq.py, data-layer/config.example.yml
Summary: Added "groq" provider to `LLMClient` via Groq's OpenAI-compatible Chat Completions endpoint (`https://api.groq.com/openai/v1/chat/completions`) with `Authorization: Bearer` from `GROQ_API_KEY` (loaded from `data-layer/.env` via python-dotenv with a no-dep fallback parser). Rate-limit handling: HTTP 429 triggers exponential backoff (1, 2, 4, 8, 16, 32, 60 s; honours `Retry-After` header when present) with retry logging. `config.yml` / `config.example.yml` switched to `provider: groq`, `model: llama-3.3-70b-versatile`; Ollama config kept inline as commented fallback. Smoke-tested via `python -m scripts.test_groq` (translates "bonjour" → "hello"); pipeline run itself (`make enrich`) still pending under D-021.run.

### D-021.run — Run enrich pipeline
Milestone: TBD
Status: BLOCKED by D-020
Action: make enrich (cloud LLM via Groq per D-021)
master

### D-024 — DALF C1/C2 literary ingester 🟡 IN PROGRESS
Milestone: TBD
Agent on `d-024/dalf-c-level`. Literary-register source for C1/C2 — feeds the DALF exam variant (see E-003).

### D-025 — Naturalisation source research 🟡 IN PROGRESS
Milestone: TBD
Agent on `d-025/naturalisation-research`. Source-survey only — identifying licensable corpora for the FR-naturalisation exam variant (E-004). No parser yet.

 d-022/dbnary-debug
### D-022 — Debug DBnary ingestion (real-corpus streaming) ✅ DONE
Milestone: DONE
Status: ✅ DONE (2026-05-15)
File: data-layer/scripts/ingest/dbnary.py
Bug: prior D-012 implementation only ever ran against a synthetic-Turtle smoke fixture. Against the real 1.2 GB `fr_dbnary_ontolex.ttl` dump it consumed 27 minutes of CPU and yielded zero chunks. Three root causes:
1. **No incremental yield.** `parse_dbnary_stream` accumulated every entry into a dict and only emitted chunks in a final post-EOF loop. At ~35s per 100k lines (×255 for the full file ≈ 2.5h), the run never reached the yield phase before being killed.
2. **English-translation linking broken.** Real DBnary points `dbnary:isTranslationOf` at the *entry* URI (e.g. `fra:accueil__nom__1`), not at a sense URI as the synthetic fixture assumed — so `_resolve_english_translation` matched zero translations and `surface_en` would have been null on every chunk anyway.
3. **Blank-node definitions/examples leaked bnode IDs as text.** Real DBnary wraps `skos:definition` / `skos:example` in `[ rdf:value "..."@fr ]` blank nodes; the parser stored `str(bnode)` (e.g. `'na868ce4a10f145b0af72e4ef7055ecfeb1'`) instead of resolving via `rdf:value`.
Fix: streaming flush keyed on lemma-group boundaries — when a new `LexicalEntry` subject appears, the previous entry is built into a chunk and its referenced forms/senses/translations are dropped from the caches. Bnode `rdf:value` resolution pre-pass per block. `_resolve_english_translation` now matches both entry-URI and sense-URI translation sources. POS no longer overwritten with `None` when `dbnary:partOfSpeech` succeeds `lexinfo:partOfSpeech`. `_block_is_interesting` short-circuits non-English `dbnary:Translation` blocks (≈95% of all triples) → ~6× parser speedup. Periodic `log.info` every 50k blocks shows pending entries + cache sizes so future regressions surface immediately. Peak tracked memory bounded at ~23 MB across the full run.
Delivered: 487,590 DBnary chunks in `chunks` (`chunk_sources.source_name='DBnary'`); 119,946 with `surface_en` populated; 639,142 example sentences in `chunk_examples`. Idempotent on re-run (ON CONFLICT upsert). Diagnostic + smoke harnesses retained as `data-layer/tests/diagnose_dbnary.py` and `data-layer/tests/smoke_dbnary_slice.py` against a committed 5k-line slice fixture.
Follow-up: `D-023 — Run vectorize pipeline` (`make vectorize`, ~24h) is now unblocked.

### D-024 — Implement literary / academic French ingester (DALF C1/C2 corpus) ✅ DONE
Milestone: TBD
Status: ✅ DONE (2026-05-15)
File: data-layer/scripts/ingest/literary_fr.py
Goal: seed the C-level vocabulary tier with literary noun-phrase / multi-word-expression chunks for DALF C1/C2 prep. Three sub-sources sharing one spaCy `fr_core_news_lg` extractor (3-15-token noun_chunk + amod-tail expansion + first-`nmod` PP graft):
- **Project Gutenberg FR** (PD post-1850): 16/17 curated works (Hugo / Flaubert / Maupassant / Zola — Flaubert *L'Éducation sentimentale* #12723 404'd; Balzac / Stendhal intentionally excluded as their oeuvres pre-date the 1850 cutoff). source_name `Gutenberg_FR`.
- **HuggingFace UniversalCEFR** (`kwiqiz_fr` + `readme_fr`, FR-only datasets discovered via `huggingface_hub.list_datasets(author='UniversalCEFR')` — the existing `universal_cefr.py` was looking for the non-existent `cefr_sp_fr`). Filters to `cefr_level in (C1, C2)`; license CC-BY-NC-4.0 / CC-BY-SA-NC-4.0. source_name `UniversalCEFR` (same bucket; provenance distinguished by `source_version='kwiqiz+readme-c-level'`).
- **French Wikipedia** (`Catégorie:Article de qualité` + `Catégorie:Bon article` via the MediaWiki API, 597 vetted titles). source_name `Wikipedia_FR_Quality`, license CC-BY-SA-3.0.

Heuristic-removal correction (mid-implementation): the first Gutenberg sweep auto-tagged every extracted phrase as `cefr_level='C1'`; DB diagnostic against the resulting 66,872 rows showed A1 vocabulary like *homme* / *eau* / *vivre* polluting the C1 bucket. Fix: only propagate `cefr_level` when the source itself labels each row's level (UniversalCEFR carries per-row `cefr_level`; Gutenberg + Wikipedia land with `cefr_level=NULL`). Per-chunk levels are now D-021 enrichment's job. The bad C1 labels were stripped in-place via `UPDATE chunks SET cefr_level=NULL WHERE id IN (SELECT chunk_id FROM chunk_sources WHERE source_name='Gutenberg_FR')`. Residual C1/C2-tagged Gutenberg chunks (76 C1 + 5 C2 in spot-check) come from cross-source dedup with UniversalCEFR rows that carry the explicit label — the COALESCE upsert preserves the explicit level.

Delivered chunk counts (2026-05-15 post-revision):
- `Gutenberg_FR`: 66,872 chunks, all `cefr_level=NULL` (apart from the cross-source overlaps above).
- `UniversalCEFR` (this run): 4,244 chunks total, 2,500 at C1 + 565 at C2 (source-explicit) — clears the 2,000+ C1 / 500+ C2 ticket target.
- `Wikipedia_FR_Quality`: 250,542 chunks at the time the BACKLOG entry was written (the per-article phrase pass was still running into a long deduplication tail past that snapshot — re-running is idempotent), all `cefr_level=NULL` (Groq enrichment will score per chunk).

Constraints honoured: pre-1850 works skipped (Balzac / Stendhal corpus filtered out), no modern copyrighted literature, `HF_TOKEN` env var honoured for gated datasets, polite MediaWiki polling (UA + 0.4 s/request, max 300 titles per category).

### D-030 — Review queue (500 chunks)
Milestone: TBD
Status: BLOCKED by D-023 (vectorize pipeline)
Action: make review-queue + human review ~6h

### D-023 — Wikipedia FR cultural ingestion ✅ DONE
Milestone: TBD
Status: ✅ DONE (2026-05-15)
Branch: d-023/wikipedia-fr-cultural
File: data-layer/scripts/ingest/wikipedia_fr.py
Summary: French Wikipedia article ingester for cultural / civilizational chunks unlocking DELF (European cultural content) + AP French (Franco-anglophone overlap). MediaWiki action API: per top-level category, BFS depth-1 collects up to 350 page titles via `list=categorymembers` (cmtype=page→subcat fallback), then bulk `prop=extracts|pageprops` (20 titles/call) fetches lead extracts + disambiguation flags + follows redirects. Topic mapping: `culture-fr-europe` for Culture/Littérature/Cuisine/Société française; `culture-fr-anglo` for Histoire/Personnalités/Géographie de la France (first category to claim a title wins on cross-category dedup). Filters: skips disambiguation pages and stubs (lead < 100 chars). Politeness: 1 req/s floor + descriptive User-Agent (Wikipedia API policy); per-category title lists + per-title summaries cache to JSON under raw/wikipediafr/ → re-runs hit zero network. Override `_upsert_row` attaches topic_codes via merge UPDATE (idempotent across re-runs). Result: **1,877 chunks** ingested across both topic codes (1,244 culture-fr-europe / 633 culture-fr-anglo), 1,877 lead-extract examples linked, source_version=2026-05-15, source_license=CC-BY-SA (recorded in chunk_sources for D-031 audit).

### D-025 — Naturalisation source candidates (research) ✅ RESEARCH COMPLETE
Milestone: TBD
Status: ✅ RESEARCH COMPLETE (2026-05-15)
Branch: d-025/naturalisation-research
Document: data-layer/docs/D-025-naturalisation-sources.md
Summary: surveyed 14 candidate sources for French naturalisation interview prep content (Livret du citoyen, Charte des droits et devoirs, data.gouv.fr examen civique QCM datasets, vie-publique.fr fiches, formation-civique.interieur, Wikipédia FR, INSEE, INED, Élysée, Sénat Junior, Gallica pre-1925 manuels, OpenClassrooms MOOCs, third-party prep sites, HuggingFace). Three P0 sources cleared on license (Etalab Licence Ouverte 2.0): data.gouv.fr QCM × 2 (258 + N official Q&A) and Charte (Décret 2012-127). Livret du citoyen confirmed under etalab-2.0 via Légifrance footer on the approving arrêté (INTV2202117A). Proposed 10-code naturalisation topic taxonomy mirroring the 5 themes of the official examen civique program. No ingestion attempted — blocked on D-031 license audit and a topic-taxonomy schema migration (new `exam_track` discriminator).
Next: D-031 audit of the 6 P0/P1 sources → ingestion sprint (~2 BE days after green light).

### D-030 — Review queue (500 chunks)
Milestone: TBD
Status: BLOCKED downstream (waits on D-020 sources completing + D-021 enrichment + a vectorize pass).
Action: `make review-queue` + human review ~6h.
 master

### D-031 — License audit
Milestone: TBD
Status: BLOCKED by D-030.
Action: `make license-audit` + manual sign-off.

---

## Surface Wiring (W-tickets — Phase 2 placeholders)

Stubs filed 2026-05-15. Each surfaces a slice of the data layer to the FE. Bodies to be authored when D-020..D-022 close and the chunk corpus is review-clean.

### W-001 — Le Vocabulaire surface wiring (placeholder)
Milestone: M4
Wire `/vocabulaire` FE surface to the enriched `chunks` table. Depends on D-020 (Tatoeba + DBnary in), D-021 (enrichment labels), D-030 (review pass).

### W-002 — L'École surface wiring (placeholder)
Milestone: M1
Wire L'École cluster/lesson surface to curriculum-tagged chunks. Depends on D-021 enrichment label set being finalised.

### W-003 — Le Diagnostic surface wiring (placeholder)
Milestone: M3
Wire La Carte / Le Goulet / L'Ordonnance retrieval to the chunk + vector store so diagnostic feedback cites real corpus exemplars rather than the in-prompt placeholder set.

### W-004 — Cross-surface retrieval API (placeholder)
Milestone: TBD
Shared retrieval endpoint consumed by W-001 / W-002 / W-003 — chunk lookup by `chunk_type`, `cefr_level`, `theme`, and similarity. Defers F-312's RAG layer plumbing.

### W-005 — Review-queue admin surface (placeholder)
Milestone: TBD
Admin-only surface for clearing D-030's 500-chunk review queue. Depends on W-004's retrieval primitives being stable.

---

## Exam Product Variants (E-tickets — Phase 3 placeholders)

Stubs filed 2026-05-15. Each is a top-of-funnel product variant beyond the TCF Canada beachhead. All depend on the matching ingester (D-023..D-025) plus the surface wiring (W-001..W-005) being live.

### E-001 — DELF variant (placeholder)
Milestone: polish-defer
Cultural-reference + register-rich exam variant. Depends on D-023 (Wikipedia FR cultural ingester) + W-001..W-005.

### E-002 — AP French variant (placeholder)
Milestone: polish-defer
US high-school AP French exam variant. Depends on D-023 + W-001..W-005.

### E-003 — DALF C1/C2 variant (placeholder)
Milestone: polish-defer
Literary-register exam variant. Depends on D-024 (DALF C1/C2 literary ingester) + W-001..W-005.

### E-004 — Naturalisation variant (placeholder)
Milestone: polish-defer
FR-naturalisation linguistic-test variant. Depends on D-025 (naturalisation source research) + W-001..W-005.

---

## Mapping notes — M0 milestone tagging (2026-05-25)

TBD tickets below have ambiguous milestone assignments. One-line questions for Chadi.

- **B-104 — Email marketing infrastructure** — Conflicts with FE B-104 = Paywall (M6); recommend renumbering this BE ticket to B-110: what is the correct milestone for email marketing infrastructure?
- **F-312** — RAG retrieval layer: M3 prerequisite for scorer quality or a separate infrastructure track outside V1.0 milestones?
- **P-107, P-108, P-110** — Soft satisfaction guarantee, pronunciation feedback, onboarding refinement: M7 soft-gate items or polish-defer?
- **P-211b, P-211a, P-211c** — Cluster content sub-tickets: M4 (La Bibliothèque corpus) or M3 (L'Examen content authoring)?
- **P-213** — Dialogue Box template authoring: M4 (Bibliothèque) or M1 (L'École surface)?
- **P-240b** — Today's focus prose layer (Dialogue Box rendering): M1 dashboard completeness or post-launch?
- **P-260.5** — Author 3 TCF Canada mock exams: M3 (L'Examen) prerequisite or post-launch content work?
- **P-231, P-232, P-233, P-235, P-236, P-237, P-241** — Post-launch P1 dashboard + prescription surfaces: any required for soft-beta sign-off (M7) or all polish-defer?
- **P-250, P-251** — Threshold calibration + lesson content delivery: M4 or post-launch?
- **P-260, P-261, P-262, P-263, P-264, P-265, P-266** — Phase 2 writing + expansion: all polish-defer?
- **P-300** — Writing pedagogy: confirmed polish-defer (writing deferred to V1.1+ per CLAUDE.md)?
- **B-105** — Analytics setup: M6 (revenue infrastructure) or M7/M8 (pre-beta ops)?
- **B-106** — BACKLOG architecture consolidation: ops task — which session should run this?
- **B-103, B-200** — Trademark research + Book-Lab store: polish-defer / V1.1+?
- **C-100** — Clean up test user id=5 from production DB: M7 pre-ship housekeeping or run now?
- **P-102** — Visual quality pass: M2 (visual coherence) or M7 (satisfaction gate quality review)?
- **P-103.1, P-103.2** — Deferred audio cap + authenticated-audio-serve: M1 edge case or polish-defer?
- **P-104.x** — Wall-clock setTimeout cap fallback: M1 pre-launch blocker or polish-defer?
- **P-109** — TCF Canada speaking simulator MVP: M3 (L'Examen scope) or post-launch standalone?
- **P-210.1** — Per-persona path forking: M1 (onboarding/path) or post-launch routing?
- **P-211b** — Render-time student-facing filter for cluster lesson body: M1 (L'École surface) or M4?
- **P-220.x, P-220.y** — Onboarding routing engine full + notification scheduling: M1 (onboarding harden) or post-launch?
- **F-077.x, F-078.x, F-111** — JSONB migration, async storage, DO Spaces debug: M6 pre-revenue tech debt or polish-defer?
- **EX-100** — Execution tooling evaluation: not milestone-gated — close as ops or defer to M7?
- **D-020** — Run ingest pipeline: M4 prerequisite (vocab corpus) — which D-tickets must close first?
- **D-021.run** — Run enrichment pipeline (blocked on D-020): M4 prerequisite?
- **D-023, D-024, D-025** — Wikipedia FR cultural, DALF C1/C2, naturalisation ingesters: all polish-defer (feed E-001..E-004) or any of these in M4 scope?
- **D-030, D-031** — Corpus review pass + post-ingest QA: M4 prerequisite for vocab corpus quality?
- **W-004** — Cross-surface retrieval API: M3 (diagnostic) or M4 (vocab) prerequisite?
- **W-005** — Review-queue admin surface: M4 prerequisite or polish-defer?

