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
| 31 | **P-105** | 7-day free trial logic |
| 32 | **P-106** | Paddle integration with subscription + one-time SKU |
| 33 | **B-100** | Paddle account setup |
| 34 | **M-103** | YouTube anchor video — French exam prep for English speakers |
| 35 | **M-104** | Reddit community engagement (broadened subreddit list) |

---
# Active — Launch Critical (35 tickets, before soft beta launches)

## F-225 — Desktop verification protocol

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

**Filed:** 2026-05-04.
**Status:** Awaiting Verification (FE-side fix delivered 2026-05-04; 1440px + 375px screenshots + interactive trace pending per F-225).
**Tag:** Active — Launch Critical (before soft beta launches).

**Priority:** Medium.

Sign Out flow has a bug — investigate + fix. Specifics TBD on triage; likely cookie-clear or redirect-loop issue (auth cookie set via `set_cookie("access_token", ..., httponly=True, samesite="lax")` on the API host; FE sign-out must hit a logout endpoint that clears cookie, then redirect home).

**Owner:** FE (likely; BE may need a `POST /auth/logout` endpoint if not present).

---

## F-200 — Landing page desktop layout

**Filed:** 2026-05-04 (BACKLOG restructure — soft-beta definition lock).
**Status:** Queued.
**Tag:** Active — Launch Critical (before soft beta launches).

**Priority:** HIGH (soft-beta requires platform fully responsive).

Landing page (`/`) currently mobile-only with white rails on desktop. Build the desktop layout: proper grid, full-width hero, multi-column pricing cards, footer that doesn't read as a stretched phone screen.

**Owner:** FE.
**Verification:** screenshot evidence at 1440px viewport per F-225.

---

## F-201 — Onboarding flow desktop layout

**Filed:** 2026-05-04.
**Status:** Queued.
**Tag:** Active — Launch Critical (before soft beta launches).

**Priority:** HIGH.

`/onboarding` (the 11-question flow) is mobile-only. Build the desktop layout: centered card on desktop with breathable margins, question-illustration pairing where applicable, no stretched phone aesthetic.

**Owner:** FE.
**Verification:** screenshot evidence at 1440px per F-225.

---

## F-202 — /ecole + L'École intro rebuild (responsive + content + methodology demo)

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

**Filed:** 2026-05-04.
**Status:** Queued.
**Tag:** Active — Launch Critical (before soft beta launches).

**Priority:** HIGH.

P-230 v1 shipped 2026-05-03 (FE 3-commit set 28bf765) with the structural skeleton but is mobile-only. Build the desktop layout — multi-column dashboard grid, larger Snapshot block, side-by-side Goulet Stack and Recent Activity. Pairs with **P-230.depth** which scopes the content rebuild specifically.

**Owner:** FE.
**Verification:** screenshot evidence at 1440px per F-225.

---

## P-230.depth — /progress real content for soft beta

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

**Filed:** 2026-05-04.
**Status:** Queued.
**Tag:** Active — Launch Critical (before soft beta launches).

**Priority:** Medium-high.

Cluster detail page consumes the BE endpoints shipped in P-234. FE consumer is in progress; ensure the desktop layout is first-class — sidebar (lesson nav?) + content column, lesson markdown rendered with reading-width constraint, exercise pane next to lesson.

**Owner:** FE.
**Verification:** screenshot evidence at 1440px per F-225.

---

## F-205 — /speaking/* (Tâche surfaces) desktop layout

**Filed:** 2026-05-04.
**Status:** Queued.
**Tag:** Active — Launch Critical (before soft beta launches).

**Priority:** HIGH (Tâche surfaces are the core practice flow).

`/speaking/tache-1`, `/speaking/tache-2`, `/speaking/tache-3` and their session sub-routes are mobile-only. Build the desktop layout for each — recording panel + prompt panel side-by-side, transcript review ergonomics on a larger viewport, mic button doesn't stretch oddly.

**Owner:** FE.
**Verification:** screenshot evidence at 1440px per F-225.

---

## F-206 — Auxiliary pages desktop (privacy/terms/refund/waitlist/signup)

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

**Filed:** 2026-05-04.
**Status:** Queued.
**Tag:** Active — Launch Critical (before soft beta launches).

**Priority:** HIGH.

Block 3 strategy lock-in: onboarding should feel like a "seamless quiz pop-up entry moment" not a clinical 11-question form. Add a 1-screen intro framing the questionnaire ("Let's understand where you are. 11 quick questions, ~3 minutes, then a 3-recording diagnostic.") with personality + Chadi voice.

Reduces perceived friction at the threshold; sets expectation for the diagnostic stage immediately after.

**Owner:** FE + Chadi (intro copy in FR + EN).

---

## F-221 — Exam-selector in onboarding + brand-layer rewrite

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

## V-010 — /ecole phase structure correction

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

- Consume `GET /api/writing/prompts` (14 prompts live, queryable by `tache_level` / `level` / `topic_tag` per F-224 endpoint extension)
- Display prompts library grouped by Tâche level (T1 / T2 / T3 sections; B1 vs B2 within)
- Click prompt → submission form (textarea, word counter against `min_words` / `max_words`, submit)
- `POST /api/writing/submit` → display Claude analysis result (4-layer feedback: Sentence Architecture / Grammatical Accuracy / Lexical Appropriateness / L1 Interference; per `writing_analysis.py`)
- Submission history (basic list view from `GET /api/writing/history/{user_id}`; expand interactions later)
- Render `prompt_fr` for FR users + `prompt_en` for EN users (i18n parallel rendering — both fields now present in API response per F-224)
- For Tâche 3 prompts, the `prompt_fr` body contains `**bold**` markers + `\n\n` paragraph breaks; FE rendering needs to handle (markdown render OR strip-and-paragraph)

### V-013b — Build /more page content

- Profile section (avatar, name, exam target from `q0_target_exam`, exam date from `q3_exam_date`)
- Settings (language toggle, current locale from `User.ui_language`)
- Account actions (logout, change password if applicable)
- About (version, support, terms link → `/terms`, privacy link → `/privacy`, refund link → `/refund`)
- Page exists on both mobile + desktop

### V-013c — Nav system overhaul

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

**Status:** Active LC
**Tag:** Active — Launch Critical (before soft beta launches).
**Filed:** 2026-05-06
**Type:** FE pre-launch blocker + redesign

Four sub-tickets, all FE-only. Surfaced after V-013 first-pass shipped — two correctness bugs (V-015a/b) + two desktop redesigns (V-015c/d) at the Apple-product-website tier.

---

### V-015a — Writing submit 422 fix (FE payload field rename)

- BE expects `body.student_text`, FE sends `body.text` → 422 on submit
- One-line fix in `api.writing.submit()` payload — rename `text` → `student_text`
- Reference: `app/routers/writing.py::submit_writing` consumes `SubmitWritingRequest.student_text`

### V-015b — Writing submit gate removal

- Currently submit button disabled below `min_words`
- Chadi feedback: word count is a guideline, not a hard gate
- Allow submit at any word count; show "below recommended" warning if under min, but don't disable the button
- BE accepts any non-empty `student_text` (only validates emptiness, not min/max — confirmed in `submit_writing`)

### V-015c — /speaking desktop redesign (full product treatment)

- Current state: 3 centered pastel cards (Tâche 1/2/3), narrow mobile-style column
- Chadi feedback: *"rethink this page from A to Z, it's a desktop website, there has to be tabs, useful options, think from a website product point of view"*
- Apple-product-website level layout — full desktop width, tabs/panels, structured content
- Plan-first with 2-3 layout proposals before implementation

### V-015d — /progress desktop redesign

- Current state: narrow centered column with Snapshot / Today's Focus / Recent Activity
- Same desktop product treatment needed as V-015c
- Multi-column dashboard, diagnostic progress prominently visible, per-couche scores, activity chart
- Plan-first with 2-3 layout proposals
- BE data already shipped (P-201, P-201.x, P-240, F-080d) — nothing new to wire from BE side

---

## V-016 — Post-V-015 fixes (6 sub-tickets)

**Status:** Active LC
**Tag:** Active — Launch Critical (before soft beta launches).
**Filed:** 2026-05-06
**Type:** Mixed (V-016a is BE-urgent; V-016b–f are FE)

Surfaced after V-015 first-pass shipped. V-016a is a production failure (writing submit timing out at 30s) — under investigation, plan-first reply pending. V-016b–f are FE-side polish.

---

### V-016a — Writing submit timeout (BE — URGENT, under investigation)

**Symptom:** user submits writing → 30s wait → Edge "This page couldn't load." V-015a fixed the 422 field name; production still fails downstream.

**Hypotheses (under plan-first investigation 2026-05-06):**
- `writing_analysis.py` Claude API call exceeding DO worker timeout
- Synchronous Claude calls without timeout protection
- Large 4-layer prompt overhead from current methodology
- Async/await chain leaking back to sync

**Fix paths to evaluate (plan-first surfaces choice):**
- Reduce analysis time (smaller prompt, cheaper model first pass, parallel layer analysis)
- Increase DO worker timeout
- Async background job pattern (return job_id immediately, FE polls)

Plan-first reply will surface root cause + recommended fix before any push.

### V-016b — La Méthode en Couches copy revision (FE)

Value-statement copy per couche needs revision. FE-side rewrite.

### V-016c — /ecole desktop redesign (FE — full product treatment, not mobile column)

Apple-product-website tier layout. Same treatment as V-015c/d for /speaking + /progress.

### V-016d — Hero kicker amendment (FE)

- Bigger size
- Exam name in `--ed-warm-peach-deep`
- Continuous cycle 8-10× or infinite (not stop after 3)

### V-016e — Landing font fix (FE)

Switzer not loading on landing `/` — may be V-005 regression. FE investigation + fix.

### V-016f — Differentiation card 1 bars rework (FE)

Current 5-bar visualization reads meaningless without labels. Add labels OR replace with alternative typography callout per V-004's spec.

---

## F-300 — Platform repositioning + Store

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

- Create `/exam-prep` route
- Copy current `/` page content verbatim to `/exam-prep`
- Audit internal nav: `/signup`, `/onboarding`, `/paywall` flows still target `/exam-prep` funnel context
- Existing `/` preserved temporarily during transition

### F-300a — New `/` platform landing (FE only)

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

- Grid of product cards (books + free resources mixed)
- Filters: format (epub / pdf / print), level (A1 / A2 / B1 / B2), topic
- Search bar
- $0 items badged "Free" — same flow, different price
- Empty state: "Catalog launching soon — pre-order to be notified"

### F-300d — Product detail pages `/library/[slug]` (FE)

- Cover image, title, author, description
- Format options + price
- "Add to cart" or "Download free" CTA per item
- Related items

### F-300e — Cart + LemonSqueezy checkout (FE + BE)

- Cart state (localStorage + persisted)
- LemonSqueezy checkout integration
- Order confirmation flow
- **BE:** webhook handler for purchase confirmation + entitlement granting
- **B-100 reconciliation pending** — see flag above; F-300e wiring depends on which MoR is canonical at build time

### F-300f — Free resources flow (FE + BE minor)

- $0 items: skip cart, direct download
- Email gate optional (capture user for marketing)
- **BE:** signed download URLs (likely DO Spaces presigned URLs — same pattern as TTS audio cache)

### F-300g — Pre-order / waitlist (FE + BE)

- Books not ready: "Notify me when available" CTA
- Email capture, persist to BE
- **BE:** waitlist table + email send on launch (could reuse P-222 waitlist plumbing — surface in plan-first)

---

## V-005 — Font system upgrade

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

## P-105 — 7-day free trial logic

**Filed:** 2026-04-30; **scope clarified 2026-05-03** (post Stripe → LemonSqueezy pivot); **rescoped 2026-05-04** (LemonSqueezy → Paddle per B-100 Path B decision).
**Status:** Queued (blocked on P-106 / B-100 — Paddle account + integration must land first).
**Tag:** Active — Launch Critical (before soft beta launches).

**Priority:** High (pre-launch).

7-day free trial gating new-user access to the paid feature set. Implementation uses Paddle's native trial mechanics (subscription created with `trial_ends_at`; webhook fires on trial expiry transitioning the user to active-paid or lapsed).

Backend scope:
- New entitlement state on User: `trial_started_at`, `trial_ends_at`, `subscription_status` (trialing | active | lapsed | canceled | none) — alembic migration.
- Trial-start trigger: first authenticated session post-signup auto-creates a Paddle subscription in trialing state (no card required for trial entry; card collected at trial-end transition).
- Gating decision lives in a single helper `app/services/entitlement.py::has_active_access(user) -> bool`. Callers: recording upload, conversation start, /api/users/me/today.
- Lapsed-user UX: read-only access to past recordings + diagnostic; new recordings blocked with paywall redirect.

**Depends on:** P-106 (Paddle integration), B-100 (Paddle account approval).

**Owner:** Engineering. Trial copy + paywall wording owned by M-101 / Chadi.

---

## P-106 — Paddle integration with subscription + one-time SKU

**Filed:** 2026-04-30; rescoped 2026-05-03 (Stripe → LemonSqueezy — Morocco constraint); **rescoped 2026-05-04 (LemonSqueezy → Paddle, per B-100 Path B decision).**
**Status:** Queued (blocked on B-100 — Paddle account approval).
**Tag:** Active — Launch Critical (before soft beta launches).

**Priority:** High (pre-launch).

Integrate Paddle API as the payment + subscription provider:
- **$29/mo subscription** SKU for the recurring product.
- **$199 one-time** SKU for the Sprint product (3-week TCF crash-prep cohort).
- Webhook endpoint(s) for subscription lifecycle events (created, updated, canceled, payment_failed) — drives entitlement state on User rows.
- Customer portal link for self-serve billing management (Paddle hosts; we just deep-link).
- Test-mode + production-mode key separation via env (mirror of existing `ANTHROPIC_API_KEY` / `ASSEMBLYAI_API_KEY` pattern).

**Why Paddle (post-LemonSqueezy):** Stripe doesn't onboard Morocco-based merchants. LemonSqueezy attempted (KYC submitted 2026-05-03); approval stalled with no confirmed timeline. Paddle is also MoR (handles tax, EU VAT, US sales tax) and accepts Morocco; selected 2026-05-04 per B-100 Path B for the more transparent / faster approval process. Fee structure ~5% + $0.50 (similar to LemonSqueezy; Stripe-equivalent rates not available given geographic constraint).

**Depends on:** B-100 (Paddle account approval — application pending Chadi 2026-05-04+).

**Out of scope:** geographic price differentiation (the original "dual + geographic pricing" framing) — LemonSqueezy supports purchase-power-parity adjustments natively but Phase 1 ships with a single global $29/mo + $199 Sprint price. Geographic pricing revisits post-launch if conversion data warrants.

---

## B-100 — Paddle account setup

**Filed:** 2026-04-30; renamed 2026-05-03 Stripe → LemonSqueezy (Morocco constraint); reframed 2026-05-04 to MoR provider selection (LemonSqueezy approval stalled); **decided 2026-05-04: Path B — Paddle.** Active scope = Paddle account setup + integration prep.
**Status:** In Progress — Chadi to apply for Paddle merchant account (Path B locked).
**Tag:** Active — Launch Critical (before soft beta launches).

**Priority:** HIGH (pre-launch — blocks P-106 + P-105).

Set up the Paddle merchant account (MoR — handles tax, EU VAT, US sales tax — accepts Morocco-based founders), configure storefront, provision API keys for backend integration:

- ✗ Paddle merchant account application (Chadi).
- ✗ Identity verification + KYC submission.
- ✗ Account approval — pending Paddle review.
- ✗ Storefront configuration (product naming, branding, terms link to `/terms`).
- ✗ Two SKUs: $29/mo subscription + $199 one-time Sprint.
- ✗ Sandbox + production API keys generated and handed to engineering for env injection.
- ✗ Webhook secret generated for backend signature verification.

**Decision history:** Stripe blocked (no Morocco merchants). LemonSqueezy attempted 2026-05-03; approval stalled with no confirmed timeline. Path B selected 2026-05-04 — Paddle is also MoR, accepts Morocco, has a more transparent / faster approval process per industry signal.

**Fee structure expectation:** ~5% + $0.50 per transaction (similar to LemonSqueezy; Stripe-equivalent rates not available given the geographic constraint).

**Owner:** Chadi (account / KYC / storefront) → handoff to Engineering for API key + webhook configuration once approved.

**Unblocks:** P-106 (integration — rescope to Paddle SDK), P-105 (trial logic — provider-agnostic in spec; integration-specific in code).

---

## M-103 — YouTube anchor video — French exam prep for English speakers

**Filed:** 2026-04-30; scope-reduced 2026-05-02; **rescoped 2026-05-04** (TCF-only → all-exams positioning to match brand-layer pivot).
**Status:** Queued.
**Tag:** Active — Launch Critical (before soft beta launches).

**Priority:** Medium (pre-launch credibility artifact, not a sustained channel commitment).

**Scope (rescoped):** 1 anchor video pre-launch — ~5-10 min, framed around the L1-interference moat ("Why English speakers all make the same French mistakes — and how to actually fix them"). Anchors LeMethodic as a **French exam prep platform for English speakers**, not TCF-only. Examples can pull from any of TCF/TEF/DELF B1/B2 since the format DNA is shared. Establishes the channel + serves as a referral asset; cadence is **not** committed pre-launch.

**Re-evaluate post-launch:** if the anchor video drives meaningful traffic or referral signal within 4-8 weeks, decide whether to commit to a sustained cadence (monthly anchor + occasional shorts) or leave the channel as a one-shot artifact. Default: leave as-is unless signal is clear.

**Owner:** Chadi (recording + editing + thumbnail). Solo founder cost is high — no monthly commitment until signal justifies it.

---

## M-104 — Reddit community engagement (broadened subreddit list)

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

## P-213 — Dialogue Box template authoring

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation. Curriculum doc §10.2 / Block 5.

Stub migrated from FE. Author 30-50 Dialogue Box templates (Block 5) varied by context. Placeholders for detected data. Owner: Chadi (authoring). Depends on P-240 (prescription engine — Active LC). Full original body in FE BACKLOG until B-106 consolidation ships.

---

## P-220.z — Onboarding per-question illustrations and pastels (Phase 1 polish)

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

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation. Curriculum doc §10.4 / §7.5.

Stub migrated from FE. Implement §7.5 — new surface drilled down from Speaking tab. Includes Block 3 (Recording Replay with Inline Diagnostics). Full original body in FE BACKLOG until B-106 consolidation ships.

---

## P-232 — Per-Tâche dashboards

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation. Curriculum doc §10.4 / §7.6.

Stub migrated from FE. Three dashboards (T1, T2, T3). Block 3 reused. Depends on P-231. Full original body in FE BACKLOG until B-106 consolidation ships.

---

## P-233 — Curriculum view (path surface)

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation. Curriculum doc §10.4 / §7.7.

Stub migrated from FE. New surface accessible from main nav. Includes Block 4 (Path Topography). Depends on P-203 + P-204 (shipped) + P-210 (shipped). Full original body in FE BACKLOG until B-106 consolidation ships.

---

## P-235 — Ceiling Marker Map

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation. Curriculum doc §10.4 / Block 1.

Stub migrated from FE. Implement Block 1. Surfaceable from Overall Progress (method mode) and Curriculum view (method mode). Consumes P-200 marker firings (shipped). Full original body in FE BACKLOG until B-106 consolidation ships.

---

## P-236 — Mistake Repository

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation. Curriculum doc §10.4 / Block 7.

Stub migrated from FE. Standalone tab inside Progress. Reads `user_cluster_events` (the append-only event log from P-204) — the composite (user_id, created_at) index supports the "newest events for user X" query at scale. Full original body in FE BACKLOG until B-106 consolidation ships.

---

## P-237 — Time-Adaptive UI (lean version)

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation. Curriculum doc §10.4 / Block 6.

Stub migrated from FE. Implement Block 6 lean version. `daysUntilExam` reads + conditional rendering for Dialogue Box copy, Goulet Stack ordering, exam countdown weight, practice CTA emphasis. Full mode redesigns deferred to P-267 (Phase 2). Depends on P-230 + P-231 + P-233. Full original body in FE BACKLOG until B-106 consolidation ships.

---

## P-240b — Today's focus prose layer (Dialogue Box rendering)

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

## P-260.5 — Author 3 TCF Canada mock exams for Sprint product

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

## B-106 — BACKLOG architecture consolidation

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

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation.

Stub migrated from FE. A test user (id=5) and any orphaned data it owns linger in production. Identify owned rows (recordings, conversations, user_cluster_*) and remove. One-shot SQL cleanup via DO Console or a one-shot script. Trivial scope. Full original body in FE BACKLOG until B-106 consolidation ships.

---

## F-109 — Full name not preserved end-to-end

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation.

Stub migrated from FE. Full-name field set during signup gets dropped or truncated somewhere in the BE/FE pipeline — round-trip doesn't preserve the original input cleanly. Investigate: signup endpoint validation, User.full_name persistence, /me serializer, FE display rendering. Bug fix; not a structural change. Full original body in FE BACKLOG until B-106 consolidation ships.

---

## M-101.z — Landing page custom hero asset + per-section icons

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** Queued.
**Tag:** Post-launch P1 (2-4 weeks after launch).

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation. Filed during M-101 FE rebuild planning.

Stub migrated from FE. Author or commission the landing page's custom hero asset + per-section icons (Phase 1 polish). M-101a ships with placeholder/borrowed P-220 imagery; this ticket replaces with brand-specific assets. Same shape as P-220.z's per-question illustrations. Owner: Chadi (commissioning) + Engineering (wire-up). Trigger: post-launch when visual polish becomes priority over functional shipping. Full original body in FE BACKLOG until B-106 consolidation ships.

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

## P-104.x — Wall-clock setTimeout cap fallback for deep-throttle edge case

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** Queued.
**Tag:** Post-launch P2 — signal-driven (defer until real signal).
**Parent:** P-104.

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation.

Stub migrated from FE. Sub-ticket of P-104 (background tab timer drift fix). When the browser deep-throttles tabs in the background past a threshold, even Date.now()-corrected timers can still drift; this ticket adds a wall-clock-cap fallback. Trigger: real-user reports of recording duration drift after P-104 ships. Full original body in FE BACKLOG until B-106 consolidation ships.

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

## EX-100 — Evaluate execution tooling for ticket-by-ticket efficiency

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** Queued — review needed.
**Tag:** Post-launch P2 — signal-driven (defer until real signal).

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation.

Stub migrated from FE. Cross-cutting tooling evaluation — review whether the current ticket-by-ticket execution flow (plan-first → spike → review → ship) has bottlenecks worth addressing (template scaffolding, repeated boilerplate, etc.). Trigger: post-launch retrospective. Full original body in FE BACKLOG until B-106 consolidation ships.

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
**Status:** Deferred — Phase 2 (post-launch).
**Tag:** Phase 2 / deferred indefinitely.

**Phase:** Phase 2 (post-launch).
**Source:** LEMETHODIC-CURRICULUM v0.2 §10.

Backend scope: writing-track analysis pipeline. Stub — full spec in `lemethodic-frontend/LEMETHODIC-CURRICULUM.md`. Scope overlaps with P-300 (Writing pedagogy build) — reconcile when both specs exist.

---

## P-261 — Writing dashboard

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** Deferred — Phase 2 (post-launch).
**Tag:** Phase 2 / deferred indefinitely.

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation. Curriculum doc §10.7.

Stub migrated from FE. Phase 2 dashboard surface for the writing track. Pairs with P-260 (writing analysis pipeline). Full original body in FE BACKLOG until B-106 consolidation ships.

---

## P-262 — Cross-modal prescription

**Filed:** 2026-05-01.
**Status:** Deferred — Phase 2 (post-launch).
**Tag:** Phase 2 / deferred indefinitely.

**Phase:** Phase 2 (post-launch).
**Source:** LEMETHODIC-CURRICULUM v0.2 §10.

Backend scope: prescription that draws across modalities (oral + writing). Stub — full spec in `lemethodic-frontend/LEMETHODIC-CURRICULUM.md`.

---

## P-263 — A2 path full content

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** Deferred — Phase 2 (post-launch).
**Tag:** Phase 2 / deferred indefinitely.

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation. Curriculum doc §10.7.

Stub migrated from FE. Author the full A2→B1 path content (Phase A2.1 through A2.4). Phase 2 — currently only B1→B2 ships in Phase 1. Owner: Chadi. Full original body in FE BACKLOG until B-106 consolidation ships.

---

## P-264 — B2→C1 path full content

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** Deferred — Phase 2 (post-launch).
**Tag:** Phase 2 / deferred indefinitely.

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation. Curriculum doc §10.7.

Stub migrated from FE. Author the full B2→C1 path content. Phase 2. Owner: Chadi. Full original body in FE BACKLOG until B-106 consolidation ships.

---

## P-265 — C1→C2 path

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** Deferred — Phase 2 (post-launch).
**Tag:** Phase 2 / deferred indefinitely.

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation. Curriculum doc §10.7.

Stub migrated from FE. Author the C1→C2 path. Phase 2 — out of scope for the Phase 1 product per curriculum doc §4.4. Full original body in FE BACKLOG until B-106 consolidation ships.

---

## P-266 — Tense + conjugation + idiomaticity detectors

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

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** Deferred — Phase 2 (post-launch).
**Tag:** Phase 2 / deferred indefinitely.

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation. Curriculum doc §10.7.

Stub migrated from FE. Sync audio playback with transcript word-level timing for Block 3 Recording Replay. Needs a streamed-audio endpoint (per P-103.2 design notes) + word-timing data from STT (already captured). Phase 2. Full original body in FE BACKLOG until B-106 consolidation ships.

---

## P-269 — Streak system

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** Deferred — Phase 2 (post-launch).
**Tag:** Phase 2 / deferred indefinitely.

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation. Curriculum doc §10.7.

Stub migrated from FE. Daily streak tracking + UI surface. Needs persistence (BE-side: User.last_active_at + streak counter) + dashboard rendering (FE). Phase 2. Full original body in FE BACKLOG until B-106 consolidation ships.

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

## B-200 — Book-Lab store surface

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

**Filed:** 2026-04-30; closed 2026-05-02.
**Status:** Closed — decided not to pursue. LinkedIn is the wrong audience for the visa-urgent persona; the B2B angle (immigration consultants / employer-sponsored TCF prep) is not a current channel and not a priority.
**Tag:** Closed — decided not to pursue.

**Re-open trigger:** B2B angle becomes a real channel (e.g., immigration-consultant referral pipeline material).

Original priority was Medium. Decided not to pursue per 2026-05-02 marketing triage — solo founder bandwidth is the binding constraint, and Reddit (M-104) + YouTube (M-103) cover the visa-urgent persona at lower cost with better audience fit.

---

# Shipped

## B-102 — Privacy policy + ToS + Refund

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

## F-223 — "Le raccourci" copy bleed cleanup

**Filed:** 2026-05-04.
**Status:** **Shipped 2026-05-06** — both FE-side (delete in `lemethodic-frontend` landed 2026-05-04) and BE-side (delete commit `e7d0ea1` 2026-05-06) complete. Per Chadi 2026-05-06: log-pull verification skipped — Jinja templates dead by architecture (Next.js FE on Vercel handles all user-facing pages from `lemethodic.com`; BE FastAPI serves API endpoints only). Production verification 2026-05-06: `GET /` + `GET /admin` + `GET /writing` all return 404 (was 200 with Jinja); `/health` + `/api/writing/prompts` + `/onboarding/questions` + `/api/users/me` all unchanged. 5,358 lines of pre-rebrand HTML retired plus 23 lines of handler code in `main.py` + the unused `HTMLResponse` import.

**Priority:** Medium (consistency).

"Le Raccourci" was the original section name; renamed to "L'École". Stragglers exist in both repos (FE strings, BE seed data, copy docs). Full grep + replace.

**Verification:** zero matches for `raccourci` (case-insensitive) in shipped strings across both repos.

**Owner:** FE + BE.

---

## F-224 — Writing Dashboard build (FE consumer + prompt seed)

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

## P-220 — Onboarding questionnaire rebuild

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

**Filed:** 2026-05-02 (migrated from chadovsky/lemethodic-frontend BACKLOG).
**Status:** Shipped 2026-05-03 (FE-side, `lemethodic-frontend` commits `59fb2c6` + `deff02b` + `820d788`). Production verified on `lemethodic.com/onboarding/waitlist`.

**Source:** FE BACKLOG (lemethodic-frontend) pre-2026-05-02 reconciliation. Curriculum doc §8.4.

When a user's diagnostic places them on a not-yet-built path (A2→B1, B2→C1, C1→C2), the FE renders a waitlist screen at `/onboarding/waitlist` with explanation copy + optional fallback offer (b1_to_b2 preview when pedagogically plausible) + email capture for early-access notification.

**BE role:** none beyond what already shipped with P-220. The `OnboardingSubmitResponse` already carries `waitlist=true` + `waitlist_reason="path_not_active"` + `fallback_path_offered=<slug | null>` on the relevant level pairs. FE consumes these and renders accordingly.

**Email capture wiring:** FE-side only for now (likely posting to a third-party form / email tool). If a BE endpoint becomes necessary, file as P-222.x — currently not needed since the FE flow is self-contained.

**FE consumer of P-220 contract:** verified end-to-end against production API. Q1=`not_sure` users correctly bypass waitlist into b1_to_b2; A2→B1, B2→C1, C1→C2 users correctly land on the waitlist screen with localized reason copy mapped from the `waitlist_reason` slug.

---

## P-230 — Overall Progress dashboard rebuild

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

**Filed:** 2026-04-30.
**Status:** Shipped 2026-05-03 (re-engagement outreach to past Preply students completed by Chadi).

**Priority:** HIGH (highest leverage, costs zero).

Re-engagement angle, not first contact. Outreach delivered.

---

## M-101 — Landing page copy in LeMethodic voice

**Filed:** 2026-04-30.
**Status:** Shipped 2026-05-03 (landing page on `lemethodic.com` renders the LeMethodic-voice copy from the authored doc; M-101a delivered the FE implementation).

**Priority:** High.

Authored copy in LeMethodic voice (Chadi's tutoring tone, 4-couches framing, anglophone-Canadian beachhead positioning) is live at `lemethodic.com` via the M-101a implementation ship. Three pricing cards, Sprint waitlist CTA, footer integration with `/privacy` + `/terms` + `/refund` (B-102). Verified end-to-end on production.

Out of scope (filed elsewhere): hero asset polish + per-section illustrations → **M-101.z** (post-launch P1).

---

