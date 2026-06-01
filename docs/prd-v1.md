# Le Méthodic — Product Requirements Document v1
**UI-First Execution Plan · Manual Mode**

> **Generated:** May 21, 2026
> **Replaces:** `lemethodic-backlog-2026-05-18.md` (orchestrator backlog deprecated; parse_backlog / dispatch_agent / n8n-workflow files dead)
> **Source of truth:** this file. `BACKLOG.md` in each repo points back to PRD entries; do not let the two diverge.

---

## 1. Framework

### 1.1 Manual Mode (locked May 21)
The orchestrator path (parse_backlog → dispatch_agent → n8n) is killed. Cost projected $200–400/sprint, unaffordable at Y0 revenue. Replacement workflow:

- **Plan with Opus** (claude.ai) — one micro-feature briefed per session, brief becomes the PRD entry below
- **Execute with Sonnet** (Claude Code in VS Code) — implements the brief in one focused session
- **/compact between sessions** with focus directive, e.g. `/compact focus on UI-002 acceptance criteria`
- **Operating cost ceiling:** ~$20–50/mo Claude.ai

### 1.2 UI-First Sequencing
Backend moats (F-336–340 RAG retrieval modes, F-322 validator, F-327 voice pipeline, F-336+ embeddings) are scheduled in Sections 3–5 — **after** UI shells are complete. Rationale: a working UI with mocks generates user-flow feedback and lets beta cohorts validate experience. A backend without a UI cannot ship.

This is not "skipping the moat." Memory #23 V2-or-nothing posture holds: soft-beta = V2 with Le Maître + RAG + activation layer. The sequence just inverts the build order so user-visible surfaces compile first.

### 1.3 One Micro-Feature Per Session
Each PRD entry below is one Claude Code session. No multi-feature dispatches, no parallel agent work.

**Session discipline:**
1. Open session: paste the PRD entry as the first message to Sonnet
2. Sonnet writes tests first (or alongside), then code, then runs the tests
3. Close session: `git commit` + push the feature branch
4. Update the PRD entry `Status` line to `Shipped` and add the merge commit SHA
5. Between sessions: `/compact focus on <entry-id> <specific aspect>` before opening the next

### 1.4 Section Map (this PRD)
| § | Section | ID Range | Count | Maps to 4-Step Strategic Sequence |
|---|---------|----------|-------|-----------------------------------|
| 1 | UI Shells | UI-001 to UI-015 | 15 | Step 0 (parallel with data layer) |
| 2 | Mock Data + UI Polish | MOCK-001 to MOCK-012 | ~12 | Step 1 |
| 3 | Backend Wiring | BE-001 to BE-022 | ~22 | Step 2b |
| 4 | Content Pipeline | CON-001 to CON-014 | ~14 | Step 2b → 3 |
| 5 | AI Infrastructure | AI-001 to AI-018 | ~18 | Step 2a → 3 |
| 6 | Legal + Business Formation | LGL-001 to LGL-008 | ~8 | Step 3 |
| 7 | Launch | LCH-001 to LCH-009 | ~9 | Step 3 |
| | **Total** | | **~98** | |

---

## 2. Conventions

### 2.1 Git
- **Backend repo** (`chadovsky/lemethodic-backend`) — branch from `master`. Local: `C:\Users\pc\Downloads\tcf-oral-tool\tcf-oral-tool`
- **Frontend repo** (`chadovsky/lemethodic-frontend`) — branch from `main`. Local: `C:\Users\pc\Downloads\fluentpath-frontend`
- **Per-feature branch naming:** `feat/<id-lowercased>-<short-name>`
  - Example: `feat/ui-001-landing-hero`
  - Example: `feat/be-007-vocab-list-endpoint`
- **Merge strategy:** squash-merge to base branch
- **Tagging:** tag at end of each Section, or every 5 shipped entries — whichever comes first. Tag format: `v0.<section>.<count>` (e.g. `v0.1.5` after UI-005 ships)

### 2.2 Tests = Spec
Tests are written first or alongside code. Never after. If you find yourself writing tests after, stop and re-open the session.
- **Frontend:** vitest for unit/component tests, Playwright for e2e flows
- **Backend:** pytest for unit + integration tests
- Every PRD entry below lists specific test file paths and test names that must exist green before the branch can squash-merge

### 2.3 Acceptance Criteria
Format: **Given / When / Then**. 2–5 acceptance lines per entry. Each acceptance line must map to at least one named test.

### 2.4 Status Vocabulary
- `Not Started` — entry exists in this PRD, no branch created
- `In Progress` — branch exists, work underway, tests not all green
- `Shipped` — squash-merged to base, branch deleted, PRD updated with merge SHA

### 2.5 PowerShell-Safe Command Style
All shell commands written for Chadi must be single-line PowerShell-safe. Escape curly braces as `'stash@{N}'` (single quotes). No multi-line heredocs.

### 2.6 Out-of-Scope Discipline
Every entry has an explicit **Out** list. Items in Out are not "not needed for launch" — they are scheduled in a later section. Adding them in the current entry creates rework.

---

## Section 1 — UI Shells (UI-001 to UI-015)

**Goal:** every user-visible surface renders with placeholder content. No real data, no live API calls, no AI integrations. Each entry compiles, renders responsively, has a Playwright smoke test confirming it loads, and ships behind a feature branch.

**Why this section first:** rendering all surfaces validates information architecture before any backend cost is incurred. Beta cohort can be invited to navigate the shell and surface flow problems before AI/content investment.

---

### UI-001 — Landing page hero

**Status:** Not Started
**Branch:** `feat/ui-001-landing-hero` (FE, from `main`)
**Effort:** 1 session (~2–4h)

#### Scope
**In:**
- Headline: **"Pass TCF Canada. Get to Quebec."** (locked per memory — hero message)
- Subheadline: one-line positioning Le Méthodic as a method-based oral exam prep platform for anglophone TCF Canada candidates pursuing Quebec PR (exact wording iterates in MOCK-001)
- Primary CTA button: text placeholder "Start your prep" — routes to `/signup` (404 acceptable at this stage; route stub created here)
- Background: solid color drawn from brand palette via CSS variables (no images, no video, no avatar)
- Responsive: renders correctly at 375px (mobile), 768px (tablet), 1280px+ (desktop)
- Brand typography: pick a distinctive display font for the headline (not Inter, not Roboto, not system) and a refined body font — choices recorded in `tailwind.config.js` or `app/fonts.ts`

**Out (deferred, do not add):**
- Le Maître avatar (scheduled in Section 5 alongside ElevenLabs voice work; adding the avatar shell here creates rework when the real persona ships)
- Wispr Flow–style animated product demo (scheduled in MOCK-002; blocked on pre-work: Wispr reference screenshots, Nanobanana sample images)
- Social proof badges, testimonials (UI-003)
- Pricing teaser (UI-004)
- Footer (UI-004)
- A/B variant routing
- Analytics (PostHog/Plausible) — Section 7

#### Acceptance (Given/When/Then)
1. **Given** a visitor on desktop (1280×800), **When** they load `/`, **Then** headline, subheadline, and CTA all render above the fold without scroll.
2. **Given** a visitor on mobile (375×667), **When** they load `/`, **Then** the hero renders without horizontal overflow and the CTA has a minimum 44×44px tap target.
3. **Given** a visitor on the hero, **When** they click the CTA, **Then** the router navigates to `/signup` (a stub page that renders an empty container is acceptable).
4. **Given** the hero rendered, **When** Lighthouse runs against `/`, **Then** Accessibility ≥ 95 and Performance ≥ 90 (no images means this is easy to hit).

#### Tests
- `tests/unit/landing/Hero.test.tsx` (vitest) — renders headline, subheadline, CTA; CTA has correct href; passes ARIA role checks
- `tests/e2e/landing-hero.spec.ts` (Playwright) — desktop viewport loads `/`, hero visible, CTA click navigates to `/signup`; repeats on mobile viewport

#### Files Touched
- `app/page.tsx` — root landing route, renders `<Hero />`
- `app/signup/page.tsx` — stub page so the CTA click doesn't 404 (empty container is fine)
- `components/landing/Hero.tsx` — new component
- `tailwind.config.js` or `app/fonts.ts` — font registration if using next/font
- `tests/unit/landing/Hero.test.tsx`
- `tests/e2e/landing-hero.spec.ts`

#### Dependencies
None. This is the first UI shell — no upstream blockers.

#### Notes
- Headline copy is locked. Sub and CTA copy may iterate in MOCK-001 polish pass.
- Do not add Le Maître avatar. ElevenLabs work happens in Section 5 (AI Infrastructure). Premature avatar placement creates rework.
- Distinctive font choice matters here — this is the first impression and the brand signal. Pick something with character; do not default to Inter.

---

### UI-002 — Landing persona-match section

**Status:** Not Started
**Branch:** `feat/ui-002-landing-persona` (FE, from `main`)
**Effort:** 1 session (~2–4h)

#### Scope
**In:**
- Section heading: "Built for visa-urgent anglophone candidates" (or similar — exact copy provisional)
- Three-column value-prop block (1 column on mobile, 3 on desktop ≥1024px):
  - Column 1: TCF Canada–specific (not generic French exam prep)
  - Column 2: Designed for English speakers (5-couche layer "Les Réflexes Anglais" surfaces here)
  - Column 3: Method-based, not vocabulary memorization
- Each column: icon placeholder (geometric SVG, not avatar/photo), heading, 1–2 sentence body
- Renders directly below `<Hero />` on `/`
- Responsive: stacks vertically below 1024px

**Out:**
- Real icons (placeholder geometric SVGs only; final iconography is MOCK-003)
- Animated reveal on scroll (Motion library — scheduled in MOCK-005)
- Stats / numbers ("90% of users pass" — needs real data, scheduled in Section 7)
- DALF C1 secondary persona — not surfaced here (primary persona only on landing per GTM lock May 17)

#### Acceptance (Given/When/Then)
1. **Given** desktop ≥1024px, **When** the visitor scrolls past the hero, **Then** three columns render side-by-side with equal height.
2. **Given** mobile <1024px, **When** the visitor scrolls past the hero, **Then** columns stack vertically with consistent spacing.
3. **Given** the section rendered, **When** Lighthouse audits accessibility, **Then** all heading hierarchy is correct (h2 for section, h3 for columns) and contrast ratios pass WCAG AA.

#### Tests
- `tests/unit/landing/PersonaMatch.test.tsx` (vitest) — renders 3 columns, correct heading hierarchy
- `tests/e2e/landing-persona.spec.ts` (Playwright) — desktop shows 3 columns, mobile shows stacked layout

#### Files Touched
- `app/page.tsx` — add `<PersonaMatch />` below `<Hero />`
- `components/landing/PersonaMatch.tsx` — new component
- `components/landing/icons/` — geometric SVG placeholders (3 files)
- `tests/unit/landing/PersonaMatch.test.tsx`
- `tests/e2e/landing-persona.spec.ts`

#### Dependencies
- UI-001 must be `Shipped` (this section attaches below the hero)

---

### UI-003 — Landing methodology preview (5-couche visual)

**Status:** Not Started
**Branch:** `feat/ui-003-landing-methodology` (FE, from `main`)
**Effort:** 1 session (~3–5h)

#### Scope
**In:**
- Section heading: "The 5-Couche Method" (locked terminology per memory)
- Visual representation of the five layers, in order:
  1. Le Fond
  2. Les Moules des Idées
  3. Les Moules
  4. Les Réflexes Anglais
  5. La Voix
- Each layer renders as a horizontal band, stacked, with the layer name and a 1-sentence description
- Layers are visually distinct (different background tones from a single palette ramp — no rainbow)
- Bottom CTA: "See how it works" → routes to `/method` (stub page, can 404 or render empty)

**Out:**
- Real interactive demo of the method (deferred to MOCK-006 with placeholder audio, then AI-005 with real voice)
- Animated layer reveal (MOCK-005)
- Linkage to L'École lesson list (Section 3 wires this)
- Beacco / FEI rubric references (these stay in admin/methodology docs, not user-facing landing)

#### Acceptance (Given/When/Then)
1. **Given** the methodology section loaded, **When** rendered on desktop, **Then** five layers display in vertical stack with consistent height and clear visual separation.
2. **Given** the section on mobile, **When** rendered, **Then** the five-layer stack remains readable (text doesn't truncate, layer names visible).
3. **Given** the CTA at the bottom, **When** clicked, **Then** the router navigates to `/method`.

#### Tests
- `tests/unit/landing/MethodologyPreview.test.tsx` (vitest) — renders 5 layers in correct order with correct French labels
- `tests/e2e/landing-methodology.spec.ts` (Playwright) — section visible, layer order correct, CTA navigates

#### Files Touched
- `app/page.tsx` — add `<MethodologyPreview />` below `<PersonaMatch />`
- `app/method/page.tsx` — stub page
- `components/landing/MethodologyPreview.tsx` — new component
- `components/landing/CouchesLayer.tsx` — single-layer sub-component
- `tests/unit/landing/MethodologyPreview.test.tsx`
- `tests/e2e/landing-methodology.spec.ts`

#### Dependencies
- UI-001, UI-002 must be `Shipped`

#### Notes
- The 5-couche is the brand moat surfaced visually. Get the typography and layer differentiation right — it's the proof point that Le Méthodic isn't another Duolingo clone.
- Exact French copy for each layer description should be reviewed by Chadi before merge.

---

### UI-004 — Landing pricing teaser + footer

**Status:** Not Started
**Branch:** `feat/ui-004-landing-pricing-footer` (FE, from `main`)
**Effort:** 1 session (~3–4h)

#### Scope
**In:**
- Pricing teaser section (above footer):
  - 5 tiers as cards: $9–19 à la carte / $19 Daily Bundle / $29 Exam Bundle / $49 Pro / $199 Sprint (one-time)
  - Each card: tier name, price, 2-line description, "Choose" CTA (routes to `/signup?tier=<slug>`)
  - Daily Bundle visually highlighted as "Most popular" (positioning per memory)
- Footer:
  - Logo placeholder
  - 3 link columns: Product (L'École, Le Vocabulaire, Le Diagnostic), Company (About, Method, Blog), Legal (ToS, Privacy — both stub `/legal/tos` and `/legal/privacy`)
  - Copyright line: "© 2026 Le Méthodic"
- Sticky nav header on top of page: logo + Sign in (routes to `/login` stub)

**Out:**
- Live Stripe checkout integration (Section 6 — LGL after Atlas + EIN)
- Free tier promotion (free funnel deferred to V1.1 per memory #23 Q8 — do not surface a free option here)
- Tier comparison table (deferred — current cards are enough for landing teaser)
- Currency switcher (USD only at launch)
- Newsletter signup in footer (deferred to Section 7 marketing)

#### Acceptance (Given/When/Then)
1. **Given** desktop, **When** the visitor scrolls to pricing, **Then** five tier cards render in a row (or 3+2 grid below 1280px) with Daily Bundle visually distinct.
2. **Given** mobile, **When** the visitor scrolls to pricing, **Then** cards stack vertically with Daily Bundle still visually distinct.
3. **Given** any tier card, **When** the CTA is clicked, **Then** the router navigates to `/signup?tier=<tier-slug>` with the correct query param.
4. **Given** the footer rendered, **When** the visitor clicks ToS or Privacy, **Then** the router navigates to the stub legal page.
5. **Given** the sticky header, **When** the visitor scrolls down the page, **Then** the header remains visible at the top.

#### Tests
- `tests/unit/landing/PricingTeaser.test.tsx` (vitest) — renders 5 tiers, Daily Bundle highlighted, CTAs have correct query params
- `tests/unit/landing/Footer.test.tsx` (vitest) — renders 3 link columns + copyright
- `tests/unit/landing/StickyHeader.test.tsx` (vitest) — renders logo + Sign in link
- `tests/e2e/landing-pricing.spec.ts` (Playwright) — clicks Daily Bundle CTA, lands on `/signup?tier=daily-bundle`
- `tests/e2e/landing-footer.spec.ts` (Playwright) — footer links navigate correctly

#### Files Touched
- `app/page.tsx` — add `<PricingTeaser />` and `<Footer />`
- `app/layout.tsx` — add `<StickyHeader />` to root layout
- `app/legal/tos/page.tsx`, `app/legal/privacy/page.tsx` — stub pages
- `app/login/page.tsx` — stub page
- `components/landing/PricingTeaser.tsx`, `components/landing/Footer.tsx`, `components/layout/StickyHeader.tsx`
- 5 test files as listed

#### Dependencies
- UI-001, UI-002, UI-003 must be `Shipped`

#### Notes
- Pricing copy is locked per memory. Do not invent new tiers or rename.
- The "Most popular" highlight on Daily Bundle is a GTM positioning decision (memory: $19 Daily Bundle is the anchor tier).

---

### UI-005 — Sign-up form shell

**Status:** Not Started
**Branch:** `feat/ui-005-signup-form-shell` (FE, from `main`)
**Effort:** 1 session (~3–5h)

#### Scope
**In:**
- `/signup` page replaces the empty stub from UI-001
- Form fields: email, password, confirm-password
- Client-side validation only at this stage:
  - Email format
  - Password ≥ 8 chars
  - Password match
- Validation errors shown inline below each field
- Submit button: disabled until validation passes; on click, shows a loading state then redirects to `/onboarding` (stub page)
- Reads `?tier=<slug>` query param from URL (set by pricing CTAs in UI-004) and displays "Signing up for: <tier>" above the form
- "Already have an account? Sign in" link → routes to `/login` stub
- Responsive: form is single column, max-width ~440px, centered

**Out:**
- Real auth wiring (Supabase / NextAuth / custom JWT — Section 3, BE-001)
- OAuth (Google, Apple) — scheduled in Section 3
- Email verification flow — scheduled in Section 3
- hCaptcha integration — scheduled in Section 3 (F-406 auth hardening)
- Password strength meter beyond length check — defer to MOCK-008
- Server-side validation — defer to BE-001

#### Acceptance (Given/When/Then)
1. **Given** a fresh visitor on `/signup`, **When** they leave the email field empty and click Submit, **Then** the Submit button stays disabled and inline error shows "Email is required."
2. **Given** valid email and matching passwords, **When** Submit is clicked, **Then** button shows a loading state for ≥300ms then router navigates to `/onboarding`.
3. **Given** the URL `/signup?tier=daily-bundle`, **When** the page renders, **Then** "Signing up for: Daily Bundle" displays above the form.
4. **Given** mismatched passwords, **When** the user blurs the confirm-password field, **Then** inline error shows "Passwords don't match" and Submit is disabled.
5. **Given** mobile viewport, **When** the page renders, **Then** the form fits in viewport without horizontal scroll and inputs have 44×44px minimum tap target.

#### Tests
- `tests/unit/signup/SignupForm.test.tsx` (vitest) — validation behavior, error messages, submit disabled/enabled states, tier query param display
- `tests/e2e/signup-flow.spec.ts` (Playwright) — fills form, submits, lands on `/onboarding`; tests validation errors; tests tier param

#### Files Touched
- `app/signup/page.tsx` — replaces UI-001 stub with `<SignupForm />`
- `app/onboarding/page.tsx` — stub page
- `components/auth/SignupForm.tsx` — new component
- `components/auth/FormField.tsx` — reusable field with inline error
- `lib/validation/signup.ts` — pure validation logic, easy to unit test
- `tests/unit/signup/SignupForm.test.tsx`
- `tests/e2e/signup-flow.spec.ts`

#### Dependencies
- UI-001 must be `Shipped` (the `/signup` stub from UI-001 is replaced here)
- UI-004 should be `Shipped` (pricing CTAs need to be wired to land here with `?tier=<slug>`)

#### Notes
- This is the last UI shell before app interior begins (UI-006 = dashboard shell).
- All validation is client-side. Do NOT wire to any auth backend in this entry. Real auth is BE-001. Adding even a fake POST endpoint creates confusion about what's mocked vs real.

---

### UI-006 to UI-015 — Section 1 remaining entries (titles only)

To be populated in subsequent planning sessions. Order reflects user journey through the app.

| ID | Title | Purpose |
|----|-------|---------|
| UI-006 | App shell (post-login) | Sidebar nav + main content frame, no data |
| UI-007 | Dashboard shell | Progress widgets as placeholders, recent activity stub |
| UI-008 | L'École lesson list view | Grid of 27 lesson cards (Fondations 1–16, Approfondissement 17–27), static |
| UI-009 | L'École lesson detail view | Content area + audio player placeholder + navigation between lessons |
| UI-010 | Le Vocabulaire browse view | Chunk list with filters (CEFR level, source) — UI only, fake data |
| UI-011 | Le Vocabulaire practice view | Flashcard-style shell, front/back placeholder |
| UI-012 | Le Vocabulaire test view | Multi-choice quiz shell |
| UI-013 | Le Diagnostic landing | Persona match, exam overview, "Start Diagnostic" CTA |
| UI-014 | Le Diagnostic Tâche 1/2/3 unified shell | Question display + recording UI placeholder + timer |
| UI-015 | Le Diagnostic results view | 5-couche score breakdown placeholder + recommendations stub |

Each will be populated with the same template structure (Scope/Out/Acceptance/Tests/Files/Dependencies/Notes) when its planning session opens.

---

## Section 2 — Mock Data + UI Polish (MOCK-001 to MOCK-012)

**Goal:** every UI shell from Section 1 displays realistic-looking data, has motion polish, and feels like a finished product even though no backend is wired. This is the section that turns shells into a demo-able product. Beta cohort can be invited at end of this section.

**Strategic step:** maps to Step 1 (data layer continues in parallel; mocks here are JSON fixtures hand-curated by Chadi).

**ID range:** MOCK-001 to MOCK-012. To be populated in subsequent planning sessions.

---

## Section 3 — Backend Wiring (BE-001 to BE-022)

**Goal:** replace mock JSON fixtures with real API calls to the existing FastAPI backend at `chadovsky/lemethodic-backend`. One surface at a time. Auth first (BE-001), then user identity (BE-002), then content surfaces (BE-003 to BE-005).

**Architecture lock (May 23, 2026):** Path A confirmed. The FastAPI backend ships as-is: 47 endpoints, 30 SQLAlchemy models, full AI integration (AssemblyAI STT + Claude 4-couche oral + Claude 5-couche writing + ai_router + TTS cache + argument scaffold), refresh-token JWT auth, email verification, password reset. 53,821 LOC. **This section wires the FE to existing endpoints. It does not create new endpoints, rewrite backend logic, or introduce Prisma / Neon / NextAuth / Supabase.**

**Strategic step:** maps to Step 2b (surface wiring).

**ID range:** BE-001 to BE-022. BE-001 to BE-005 fully specified below. BE-006 to BE-022 to be populated in subsequent planning sessions.

---

### BE-001 — Wire FE auth forms to existing auth endpoints

**Status:** Not Started
**Branch:** `feat/be-001-auth-wiring` (FE, from `main`)
**Effort:** 1–2 sessions (~4–8h)

#### Scope
**In:**
- Wire `/signup` form (`components/auth/SignupForm.tsx`) to `POST /api/auth/register`
- Wire `/login` form to `POST /api/auth/login` — BE sets `access_token` + `refresh_token` as httpOnly cookies on response; FE does not store tokens in JS
- Wire `/api/auth/refresh` on 401 response in the API client (transparent token refresh, single retry)
- Wire logout button (in app shell nav) to `POST /api/auth/logout` — clears cookies, redirects to `/`
- Wire email-verification confirm page to `POST /api/auth/verify-email` — reads `?token=<jwt>` from email link
- Wire password-reset request form to `POST /api/auth/password-reset/request`
- Wire password-reset confirm form to `POST /api/auth/password-reset/confirm` — reads `?token=<jwt>` from email link
- hCaptcha: add `@hcaptcha/react-hcaptcha` client-side widget to `/signup` and `/login`; include the `h-captcha-response` field in the POST body (BE `app/services/captcha.py` already validates it server-side)
- `middleware.ts`: protect `(app)` routes — redirect unauthenticated requests to `/login`; keep `/dashboard` and `/account` in `EXCLUDED_PREFIXES` so `TopNav` stays hidden on authenticated shell routes (carry-forward from MOCK-006)
- `lib/api/client.ts`: thin fetch wrapper — base URL from `NEXT_PUBLIC_API_URL` env var, `credentials: "include"` on all requests (required for cookie transport), 401-intercept → call `/api/auth/refresh` → retry original request once

**Out:**
- OAuth (Google, Apple) — deferred to V1.1
- Rate-limit UI feedback beyond generic error state — deferred
- Prisma / Neon / NextAuth / Supabase — **explicitly excluded**; architecture lock May 23 confirms BE auth already exists and ships as-is
- FE-side token storage (localStorage, sessionStorage) — cookies are set exclusively by BE; FE treats itself as stateless

#### Acceptance (Given/When/Then)
1. **Given** a new user fills `/signup` with valid email + password + passing hCaptcha, **When** they submit, **Then** `POST /api/auth/register` returns 201, BE sets cookies, and the router navigates to `/onboarding`.
2. **Given** a returning user fills `/login` with correct credentials, **When** they submit, **Then** `POST /api/auth/login` returns 200, httpOnly cookies are set, and the router navigates to `/(app)/dashboard`.
3. **Given** the access token is expired and the refresh token is valid, **When** the FE makes any API call, **Then** the client transparently calls `/api/auth/refresh`, receives a new access token cookie, and retries the original request without user interaction.
4. **Given** an unauthenticated user visits `/(app)/dashboard`, **When** `middleware.ts` evaluates the request, **Then** they are redirected to `/login`.
5. **Given** a logged-in user clicks Logout, **When** `POST /api/auth/logout` completes, **Then** cookies are cleared and they land on `/`.
6. **Given** a user clicks the email-verification link, **When** they land on `/verify-email?token=<jwt>`, **Then** `POST /api/auth/verify-email` fires and the page shows "Email confirmed. You can now log in."

#### Tests
- `tests/unit/auth/AuthApiClient.test.ts` (vitest) — mocked fetch: asserts `credentials: "include"` on every call; asserts 401 triggers refresh then retries; covers register, login, logout, refresh
- `tests/unit/auth/SignupForm.test.tsx` (vitest) — submits form, calls `register()`, navigates on success, shows inline error on 409 (email already exists)
- `tests/unit/auth/LoginForm.test.tsx` (vitest) — submits form, calls `login()`, navigates on success, shows "Invalid credentials" on 401
- `tests/e2e/auth-register.spec.ts` (Playwright) — end-to-end sign-up with test-mode hCaptcha bypass token, lands on `/onboarding`
- `tests/e2e/auth-login.spec.ts` (Playwright) — logs in with seeded test user, lands on `/(app)/dashboard`
- `tests/e2e/auth-middleware.spec.ts` (Playwright) — unauthenticated visit to `/dashboard` redirects to `/login`
- `tests/e2e/auth-logout.spec.ts` (Playwright) — logs in, clicks logout, lands on `/`, verify `/dashboard` redirects again

#### Files Touched (FE repo)
- `lib/api/client.ts` — new: base fetch wrapper with `credentials: "include"` + 401-intercept + refresh
- `lib/api/auth.ts` — new: typed wrappers for all 7 auth endpoints
- `app/login/page.tsx` — replace stub with `<LoginForm />`
- `components/auth/LoginForm.tsx` — new login form with hCaptcha widget
- `components/auth/SignupForm.tsx` — add hCaptcha widget, wire to `lib/api/auth.ts`
- `app/verify-email/page.tsx` — new: reads `?token`, fires `verifyEmail()`, shows result
- `app/password-reset/request/page.tsx` — new: reset-request form
- `app/password-reset/confirm/page.tsx` — new: reads `?token`, new-password form
- `middleware.ts` — protect `(app)` routes; carry-forward `EXCLUDED_PREFIXES` from MOCK-006 unchanged
- `.env.local.example` — add `NEXT_PUBLIC_API_URL=http://localhost:8000` and `NEXT_PUBLIC_HCAPTCHA_SITE_KEY`
- 7 test files as listed

#### Dependencies
- UI-005 must be `Shipped` (`/signup` form shell exists)
- MOCK-006 must be `Shipped` (`TopNav` + `EXCLUDED_PREFIXES` pattern established; BE-001 carries it forward unchanged)
- BE FastAPI server running locally at `http://localhost:8000` (`docker-compose up -d` + `alembic upgrade head` + `uvicorn`)

#### Notes
- hCaptcha test-mode site key (`10000000-ffff-ffff-ffff-000000000001`) returns a valid bypass token for e2e tests; set via `NEXT_PUBLIC_HCAPTCHA_SITE_KEY`.
- Do not store tokens in JS. Cookies are set by BE exclusively. FE is stateless with respect to auth.
- In prod, `NEXT_PUBLIC_API_URL` must share origin with the FE (same-site cookie transport) or BE must set `SameSite=None; Secure` with an explicit CORS allow-list. Confirm deployment topology with Chadi before prod deploy.

---

### BE-002 — Wire user identity to dashboard greeting and email-verification banner

**Status:** Shipped — squash-merged 6361b70d84cc60564503c8ee0f6ad79bfcd33ab1
**Branch:** `feat/be-002-user-identity` (FE, from `main`)
**Effort:** 1 session (~2–4h)

#### Scope
**In:**
- `app/(app)/dashboard/page.tsx` — Server Component: fetch `GET /api/users/me` at render time; render "Bonjour, {first_name}" greeting (fall back to email prefix if `first_name` is null)
- `app/(app)/dashboard/page.tsx` — also fetch `GET /api/users/me/level` to display the user's current assessed level (B1 / B2 / C1) in the dashboard header widget
- `app/(app)/layout.tsx` — read `GET /api/users/me` in the authenticated shell layout; if `email_verified === false`, render a dismissible `<EmailVerificationBanner />` above the main content area
- `lib/api/users.ts` — typed fetch wrappers for `GET /api/users/me` and `GET /api/users/me/level`
- `types/user.ts` — `UserMe` and `UserLevel` TypeScript interfaces matching BE JSON shapes (derive from `/openapi.json` on the running BE, or `app/schemas/level.py`)

**Out:**
- Full profile edit page (`/account/profile`) — deferred
- Level reassessment / re-onboarding flow — separate entry
- Avatar / profile photo upload — deferred to V1.1
- `/exam-prep` landing page — **do not touch** `LandingPage.tsx`; it has no auth dependency

#### Acceptance (Given/When/Then)
1. **Given** a logged-in user with `first_name: "Marie"`, **When** they load `/(app)/dashboard`, **Then** the page renders "Bonjour, Marie" without a client-side loading flash (SSR, no hydration gap).
2. **Given** a logged-in user with `email_verified: false`, **When** they load any `(app)` route, **Then** the dismissible email-verification banner appears at the top of the layout; dismissal persists for the session (no localStorage required — component state only).
3. **Given** a logged-in user with `email_verified: true`, **When** they load the dashboard, **Then** no banner is rendered.
4. **Given** `GET /api/users/me/level` returns `{ level: "B2" }`, **When** the dashboard renders, **Then** the level widget displays "B2".

#### Tests
- `tests/unit/dashboard/DashboardGreeting.test.tsx` (vitest) — renders "Bonjour, Marie" from mocked `UserMe`; falls back to email prefix when `first_name` is null
- `tests/unit/dashboard/EmailVerificationBanner.test.tsx` (vitest) — renders when `email_verified === false`; absent when `true`; dismiss button hides it
- `tests/unit/users/UsersApiClient.test.ts` (vitest) — mocked fetch: correct URLs, `credentials: "include"` on both endpoints
- `tests/e2e/dashboard-greeting.spec.ts` (Playwright) — logs in as test user, loads dashboard, "Bonjour" greeting visible

#### Files Touched (FE repo)
- `lib/api/users.ts` — new: `getMe()`, `getMyLevel()` typed wrappers
- `types/user.ts` — new: `UserMe`, `UserLevel` interfaces
- `app/(app)/dashboard/page.tsx` — SSR fetch + greeting + level widget
- `app/(app)/layout.tsx` — email-verification banner fetch + conditional render
- `components/app/EmailVerificationBanner.tsx` — new dismissible banner
- `components/dashboard/GreetingHeader.tsx` — new: name + level display
- 4 test files as listed

#### Dependencies
- BE-001 must be `Shipped` (auth cookies required for authenticated GET calls)
- UI-007 must be `Shipped` (dashboard shell exists)

#### Notes
- These are Server Components. Use `cookies()` from `next/headers` to forward the session cookie: `fetch(url, { headers: { Cookie: cookies().toString() } })`. No `useEffect`, no SWR here.
- Inspect `app/schemas/level.py` in the BE repo and the running `/openapi.json` to confirm exact field names before writing `UserLevel` — field names may differ from assumptions.

---

### BE-003 — Wire L'École lesson list and reconcile FE fixture with BE schema

**Status:** Not Started
**Branch:** `feat/be-003-ecole-wiring` (FE, from `main`)
**Effort:** 1–2 sessions (~4–8h)

#### Scope
**In:**
- **Schema reconciliation first (required before writing any code):** run local BE, call `GET /api/ecole/lessons`, capture full JSON response. Document actual field shape in `docs/api-shapes/ecole-lessons.md` (FE repo). Compare against `lib/data/lessons.ts` (27-lesson FE fixture, 16 Fondations + 11 Approfondissement). Identify mismatches. **BE wins — BE is canonical** (real data, Alembic-managed schema). Map BE fields to FE `Lesson` type; update `types/ecole.ts`.
- Replace `lib/data/lessons.ts` static import in lesson-list Server Component with a `GET /api/ecole/lessons` fetch
- Lesson detail: fetch `GET /api/ecole/lessons/{lesson_id}` to replace static fixture lookup
- Quiz: wire `GET /api/ecole/lessons/{lesson_id}/quiz` (returns `EcoleQuizQuestion[]`) to the quiz component
- Quiz submission: wire `POST /api/ecole/lessons/{lesson_id}/quiz/submit` — optimistic update on answer selection, confirm on submit
- User progress: fetch `GET /api/ecole/progress`, display completion indicators on lesson cards
- `lib/api/ecole.ts` — typed wrappers for all 5 L'École endpoints

**Out:**
- Migrating the lesson route structure — `app/ecole/intro`, `app/ecole/lesson/[id]`, `app/ecole/quiz` currently sit outside the `(app)` authenticated shell; flag as route debt with a comment, do not migrate here
- Audio player wiring to TTS — deferred to AI infrastructure section
- Lesson content authoring (admin) — deferred
- Pagination on lesson list — defer if BE returns all lessons in one response (verify during reconciliation)

#### Acceptance (Given/When/Then)
1. **Given** a logged-in user visits the L'École lesson list, **When** the page loads, **Then** lessons are fetched from `GET /api/ecole/lessons`; `lib/data/lessons.ts` is no longer imported by any component.
2. **Given** BE returns `EcoleLesson` objects, **When** the FE maps them to the `Lesson` type, **Then** all lesson titles render correctly and no TypeScript errors exist.
3. **Given** a user completes a quiz via `POST /api/ecole/lessons/{id}/quiz/submit`, **When** they return to the lesson list, **Then** the completed lesson shows a visual completion indicator sourced from `GET /api/ecole/progress`.
4. **Given** `GET /api/ecole/lessons` fails (network error), **When** the page renders, **Then** an error state displays — no blank page, no uncaught exception.

#### Tests
- `tests/unit/ecole/EcoleApiClient.test.ts` (vitest) — correct URLs, method, credentials for all 5 endpoints; `types/ecole.ts` shapes match mocked BE responses
- `tests/unit/ecole/LessonList.test.tsx` (vitest) — renders lesson cards from mocked API response; renders error state on fetch failure
- `tests/unit/ecole/LessonDetail.test.tsx` (vitest) — renders lesson content from mocked detail response
- `tests/e2e/ecole-lesson-list.spec.ts` (Playwright) — logged-in user loads lesson list, ≥1 lesson card rendered
- `tests/e2e/ecole-quiz.spec.ts` (Playwright) — clicks into lesson, submits quiz answer, completion indicator appears on return to list

#### Files Touched (FE repo)
- `lib/api/ecole.ts` — new: typed wrappers for all 5 L'École endpoints
- `types/ecole.ts` — new/updated: `EcoleLesson`, `EcoleQuizQuestion`, `UserEcoleProgress` interfaces (derived from BE schema reconciliation)
- `docs/api-shapes/ecole-lessons.md` — new: actual JSON response shape captured from running BE
- `app/ecole/page.tsx` (or equivalent lesson-list page) — replace `lib/data/lessons.ts` import with SSR fetch
- `app/ecole/lesson/[id]/page.tsx` — replace fixture lookup with `GET /api/ecole/lessons/{id}` fetch
- `app/ecole/lesson/[id]/quiz/page.tsx` — wire quiz fetch + submit
- `lib/data/lessons.ts` — **delete** after confirming no remaining imports
- 5 test files as listed

#### Dependencies
- BE-001 must be `Shipped` (authenticated fetch)
- BE-002 must be `Shipped` (user context in layout)
- UI-008, UI-009 must be `Shipped` (lesson list + detail shells exist)

#### Notes
- Block at least 1h for reconciliation before writing code: run BE locally, curl `GET /api/ecole/lessons`, compare response to `lib/data/lessons.ts`, resolve naming mismatches (e.g. BE may use `titre` where FE uses `title`).
- Route debt to flag: `app/ecole/intro`, `app/ecole/lesson/[id]`, `app/ecole/quiz` are outside `(app)` shell — unauthenticated users can currently reach them. Add `// TODO BE-003: move ecole routes inside (app) shell` comment; schedule migration as a separate entry.
- If `GET /api/ecole/lessons` returns paginated results, implement a page-1 fetch for now and note the limit.

---

### BE-004 — Wire Le Vocabulaire browse and reconcile flat-FE vs hierarchical-BE schema

**Status:** Not Started
**Branch:** `feat/be-004-vocab-wiring` (FE, from `main`)
**Effort:** 2 sessions (~6–10h; schema reconciliation adds complexity)

#### Scope
**In:**
- **Schema reconciliation first:** call `GET /api/vocab/topics` and `GET /api/vocab/topics/{slug}/chunks` against local BE. Document response shapes in `docs/api-shapes/vocab.md`.
  - BE hierarchy: `VocabularyTheme → Cluster → Path → Phase → VocabTopic → VocabChunk` + `UserVocabList / UserVocabProgress`
  - FE fixture: `lib/data/chunks.ts` — flat array of ~60 chunks used for browse-view filtering
  - **Resolution (default):** flatten BE responses into the FE array shape for V1.0. FE gets `chunks[]` from `GET /api/vocab/topics/{slug}/chunks` with query params for CEFR level filter. Hierarchy exposure scheduled for V1.1.
- `lib/vocab/filter.ts` — refactor into a pure `buildChunkParams(filters)` helper that maps FE filter state (level, theme) to query params for `GET /api/vocab/topics/{slug}/chunks`
- `hooks/useChunks.ts` — SWR hook: calls `/api/vocab/topics/{slug}/chunks` with params from `buildChunkParams()`; replaces all direct `lib/data/chunks.ts` imports in browse components
- `GET /api/clusters/{slug}` — wire to cluster detail view if the UI shell for it exists
- `lib/api/vocab.ts` — typed wrappers for all 3 vocab endpoints
- Flag all `components/home/*` consumers that import `lib/data/chunks.ts` — add `// TODO BE-004: migrate to useChunks()` comment; migrate in this entry only if trivial (< 5 lines change per file); otherwise schedule separately

**Out:**
- `UserVocabList` / `UserVocabProgress` SRS / personal lists — deferred; requires flashcard practice UI (UI-011, UI-012 must ship first)
- Vocabulary theme admin / bulk import — deferred
- V1.1 hierarchy exposure (theme → cluster → path → phase navigation) — explicitly out of scope

#### Acceptance (Given/When/Then)
1. **Given** a logged-in user loads the vocab browse view, **When** the page renders, **Then** chunks are fetched from `GET /api/vocab/topics/{slug}/chunks`; `lib/data/chunks.ts` is no longer imported.
2. **Given** the user applies a CEFR level filter (e.g. "B2"), **When** `useChunks()` re-fetches, **Then** `buildChunkParams()` maps the filter to the correct query param and the displayed chunks update.
3. **Given** `GET /api/vocab/topics/{slug}/chunks` fails, **When** the browse view renders, **Then** an error state displays with a retry option.
4. **Given** BE returns `VocabChunk` objects, **When** the FE flattens them, **Then** no TypeScript errors exist and all fields used in UI (French text, CEFR level, source) map cleanly.

#### Tests
- `tests/unit/vocab/VocabApiClient.test.ts` (vitest) — correct URLs + query params for all 3 endpoints; credentials included
- `tests/unit/vocab/buildChunkParams.test.ts` (vitest) — pure function: given filter state → expected query param string; covers level filter, no-filter, multi-filter
- `tests/unit/vocab/useChunks.test.ts` (vitest + msw) — mock `/api/vocab/topics/test-slug/chunks`, assert hook returns flattened array; assert re-fetches on filter change
- `tests/e2e/vocab-browse.spec.ts` (Playwright) — logged-in user loads vocab browse, chunks visible; applies B2 filter, list updates
- `tests/e2e/vocab-cluster.spec.ts` (Playwright, if cluster detail page exists) — navigates to a cluster, content renders

#### Files Touched (FE repo)
- `lib/api/vocab.ts` — new: typed wrappers for `GET /api/vocab/topics`, `GET /api/vocab/topics/{slug}/chunks`, `GET /api/clusters/{slug}`
- `types/vocab.ts` — new/updated: `VocabTopic`, `VocabChunk`, `Cluster` interfaces
- `docs/api-shapes/vocab.md` — new: actual JSON shapes from running BE; records flat-vs-hierarchy decision with V1.1 note
- `lib/vocab/filter.ts` — refactor to `buildChunkParams()` pure helper
- `hooks/useChunks.ts` — new SWR hook
- `lib/data/chunks.ts` — **delete** after confirming no remaining imports
- `components/home/*` — migrate or add TODO comment per consumer
- 5 test files as listed

#### Dependencies
- BE-001 must be `Shipped` (auth)
- BE-002 must be `Shipped` (user context)
- UI-010 must be `Shipped` (vocab browse shell)
- `swr` package present in `package.json` (add if missing)

#### Notes
- `GET /api/vocab/topics` returns topic-level objects; chunks are under `GET /api/vocab/topics/{slug}/chunks`. Browse view likely needs a default slug or iterates over topics — resolve during reconciliation and document in `docs/api-shapes/vocab.md`.
- If `components/home/*` consumers are non-trivial to migrate (> 5 lines), add the TODO comment, open a tracked follow-up, and do not let that migration block this branch from merging.
- Record the flat-vs-hierarchy decision explicitly in `docs/api-shapes/vocab.md`: "V1.0 flattens BE chunks response. V1.1 will expose Theme → Cluster navigation once UI-010 browse view is redesigned for hierarchy."

---

### BE-005 — Wire Les Tâches and reconcile three-model BE vs unified-fixture FE

**Status:** Not Started
**Branch:** `feat/be-005-taches-wiring` (FE, from `main`)
**Effort:** 2 sessions (~6–10h; three-source composition adds complexity)

#### Scope
**In:**
- **Schema reconciliation first:** call `GET /api/conversations/scenarios` (Tâche 2) and `GET /api/recordings/tache3-topics` (Tâche 3) against local BE. Document both shapes in `docs/api-shapes/taches.md`. Note that Tâche 1 has no pre-fetch — the opening is drawn server-side when `POST /api/conversations/start` fires with `tache_type: "tache1"`.
  - BE: three separate models — `Tache1Opening`, `Tache2Scenario`, `TestTopic`
  - FE fixture: `lib/data/taches.ts` — single unified `Tache` type with 3 static entries (one per tache type)
  - **Resolution:** replace static fixture with a composed fetch. At page load, call the relevant BE endpoint(s) and normalize into the FE `Tache` shape via `lib/taches/normalize.ts`. Preserve the `durationSeconds` prop (carry-forward from MOCK-010 timer).
- `lib/api/taches.ts` — typed wrappers for:
  - `GET /api/conversations/scenarios` → Tâche 2 scenario list
  - `POST /api/conversations/start` → start a session (body: `{ tache_type, topic_id?, scenario_id? }`)
  - `GET /api/conversations/{id}` → fetch ongoing conversation state
  - `POST /api/conversations/{id}/turn` → send a user text turn
  - `GET /api/recordings/tache3-topics` → Tâche 3 topic list for topic selection
- Tâche 3 topic selector: replace `lib/data/taches.ts` static entry with `GET /api/recordings/tache3-topics` fetch; render real topics
- Tâche 2 scenario selector: replace static entry with `GET /api/conversations/scenarios` fetch; render real scenarios
- `POST /api/conversations/start` wiring: on "Start" CTA click, fire with selected scenario/topic; navigate to conversation view with returned `conversation_id` in the URL
- Conversation turn loop: `POST /api/conversations/{id}/turn` on text submit; `GET /api/conversations/{id}` for turn history
- `lib/data/taches.ts` — **delete** after confirming no remaining imports

**Out:**
- `POST /api/conversations/{id}/end` + scoring result display — deferred; requires Le Diagnostic results view (UI-015) to be shipped
- `POST /api/conversations/{id}/turn/{n}/supersede` — deferred
- AssemblyAI STT wiring for audio turns — deferred to AI infrastructure section
- `POST /api/recordings/upload` + `POST /api/recordings/transcribe` — deferred to AI section
- Real-time streaming of AI examiner turns — deferred

#### Acceptance (Given/When/Then)
1. **Given** a logged-in user visits the Tâche 2 view, **When** the page loads, **Then** real scenarios are fetched from `GET /api/conversations/scenarios` and rendered; `lib/data/taches.ts` static fixture is not used.
2. **Given** a logged-in user selects a Tâche 3 topic, **When** they click "Start", **Then** `POST /api/conversations/start` fires with `{ tache_type: "tache3", topic_id: <selected> }` and the router navigates to the conversation view with `conversation_id` in the URL.
3. **Given** an active conversation, **When** the user submits a text turn, **Then** `POST /api/conversations/{id}/turn` fires and the examiner's response turn renders in the conversation view.
4. **Given** the timer component, **When** a conversation starts, **Then** `durationSeconds` is sourced from the normalized `Tache` object, not from the deleted static fixture.
5. **Given** `GET /api/conversations/scenarios` fails, **When** the Tâche 2 view loads, **Then** an error state renders; the static fixture is not used as a fallback.

#### Tests
- `tests/unit/taches/TachesApiClient.test.ts` (vitest) — correct URLs, methods, request bodies, credentials for all 5 endpoints
- `tests/unit/taches/normalizeTache.test.ts` (vitest) — pure function: given `Tache2Scenario` BE shape → expected FE `Tache` with `durationSeconds` preserved; covers all 3 tache types
- `tests/unit/taches/TacheSelector.test.tsx` (vitest) — renders scenario list from mocked BE response; renders error state on failure
- `tests/e2e/taches-flow.spec.ts` (Playwright) — logged-in user selects Tâche 2 scenario → clicks Start → conversation view opens with `conversation_id` in URL; sends a text turn → examiner response renders
- `tests/e2e/tache3-topic-selection.spec.ts` (Playwright) — Tâche 3 topic list renders from BE, user selects one, Start fires

#### Files Touched (FE repo)
- `lib/api/taches.ts` — new: typed wrappers for all 5 endpoints
- `types/taches.ts` — new/updated: `Tache2Scenario`, `TestTopic`, `Conversation`, `ConversationTurn` interfaces; unified FE `Tache` type with `durationSeconds`
- `lib/taches/normalize.ts` — new: `normalizeTache(source, type)` pure function mapping BE shapes to FE `Tache`
- `docs/api-shapes/taches.md` — new: actual JSON shapes from running BE for all 3 tache endpoints; records normalization decisions
- `app/(app)/diagnostic/tache/[type]/page.tsx` (or equivalent) — replace fixture with composed fetch
- `lib/data/taches.ts` — **delete** after confirming no remaining imports
- 5 test files as listed

#### Dependencies
- BE-001 must be `Shipped` (auth)
- BE-002 must be `Shipped` (user context)
- UI-014 must be `Shipped` (Tâche unified shell with timer)
- Tâche data seeded in local BE: `python -m scripts.seed_tache1_openings`, `python -m scripts.seed_tache2_scenarios`, `python -m scripts.seed_tache3_prompts`

#### Notes
- `durationSeconds` is load-bearing for MOCK-010 timer behavior. If BE does not store this per scenario, derive it from `target_levels` (B1 = 120s, B2 = 150s, C1 = 180s — confirm exact values against `Tache2Scenario` and `TestTopic` model fields in the BE repo).
- Tâche 1 has no pre-fetch (opening prompt is drawn server-side at conversation start). FE just fires `POST /api/conversations/start` with `tache_type: "tache1"` and renders whatever the first turn response contains.
- `POST /api/conversations/{id}/turn` accepts either a text body or an audio file. Wire text-only here. Audio upload wiring is deferred to AI section.

---

### BE-covered features without FE UI surfaces (deferred)

The following FastAPI endpoints are fully implemented in the BE and confirmed functional, but have zero corresponding UI surfaces in the current UI shells (Section 1) or mock layer (Section 2). They are not scoped for BE-001 through BE-005 and are deferred to later PRD sections or V1.1+:

- **`/api/writing/*`** — complete 5-couche writing analysis pipeline (`WritingPrompt`, `WritingSubmission`, `WritingSubmissionJob` with async polling). FE has no writing surface in any current UI shell. Scheduled for a future BE entry once a writing submission UI is designed.
- **`/api/analytics/{dashboard,progress,coverage,pass}`** — per-user score history and couche-level progress charts. No analytics UI exists yet. Scheduled after Le Diagnostic results view ships and accumulates real data.
- **`/api/today/me/today`** — daily action recommendation based on recurring weak modules. Will wire into the dashboard once enough session data makes the recommendation meaningful; likely V1.1.
- **`/api/onboarding/*`** — question-tree → level assignment (`UserLevelAssessment`). Overlaps with the `/onboarding` stub from UI-005; needs onboarding-questions UX designed before wiring; scheduled as a standalone BE entry.
- **`/api/modules` + `/api/users/me/recurring_modules`** — remediation module suggestions tied to weak couches (session-detected module history). No UI surface yet; scheduled alongside Le Diagnostic results wiring.
- **`/api/oral/generate-structure`** — argument scaffold (Claude call). Candidate for a pre-recording scaffold widget inside the Tâche shell; deferred to AI infrastructure section.

PRD §3 (Backend Wiring) is intentionally scoped to the surfaces that UI shells currently expose. These deferred endpoints will be picked up as their corresponding UI surfaces ship in later sections.

---

## Section 4 — Content Pipeline (CON-001 to CON-014)

**Goal:** real content lives behind the surfaces. F-321 vocab review (Phase 1 CSV regen complete 2026-06-01; row count updated post-reclassification) lands here. L'École 27 lessons get methodology-visible content. Le Diagnostic Tâche library expands to 50 scenarios (F-061.2 Livraison 2/2).

**Strategic step:** maps to Step 2b → Step 3.

**ID range:** CON-001 to CON-014. To be populated in subsequent planning sessions.

**Critical note:** F-321 vocab CSV review is the highest-leverage Chadi-bottlenecked work right now. CON-001 will be the entry that absorbs that workstream into the PRD.

**F-321 corpus-completeness limitation (discovery note 2026-06-01):** The Phase 1 CSV regen (per-chunk reclassification dispatch) works from the 1,684 rows already in `phase1_review.csv`. Chunks from source .docx files that the original per-file classifier (Phase B) tagged with a non-Phase-1 topic slug are absent from the 1,684 and cannot be recovered without re-running Phase B and C extraction. In practice this means any true faux_amis or calques_anglais content that lived in files the Phase B Haiku classified as "other/grammar" topics was silently excluded. Scope of the gap is unknown without re-running Phase B. This is a known limitation accepted for this pass; full corpus completeness is an M4 follow-up scoped as CON-001 pre-work. No action required before Chadi's Phase 1 triage.

---

## Section 5 — AI Infrastructure (AI-001 to AI-018)

**Goal:** Le Maître ElevenLabs voice deployed across L'École, Le Vocabulaire, Le Diagnostic onboarding. OpenAI TTS-1-HD remains the examiner voice for Tâches (brand-critical, non-negotiable). RAG layer goes live with 6 retrieval modes. F-322 validator (3 tiers, web admin + Slack + CSV, eager sample Tier B). 2-pass Diagnostic scoring: Pass 2 V1, Pass 1 V1.5+.

**Strategic step:** maps to Step 2a (runtime stack swap) → Step 3.

**ID range:** AI-001 to AI-018. To be populated in subsequent planning sessions.

**Critical note:** Whisper (STT) and Piper (vocab TTS narration) are fine in this section. **Never** swap OpenAI TTS-1-HD for the examiner voice — that's the brand signal locked May 19.

---

## Section 6 — Legal + Business Formation (LGL-001 to LGL-008)

**Goal:** Delaware LLC via Stripe Atlas → EIN → Mercury bank → Stripe activation (B-100 sequence). Lawyer engagement immediate at start of this section, 4-week lead time (B-101, $3–5K CAD legal budget). ToS, privacy policy, pseudonym + NER + retention policy (per architecture lock Q4). Data subject rights + cookie banner.

**Strategic step:** maps to Step 3.

**ID range:** LGL-001 to LGL-008. To be populated in subsequent planning sessions.

---

## Section 7 — Launch (LCH-001 to LCH-009)

**Goal:** Stripe live, payments confirmed end-to-end, monitoring (Sentry / PostHog / uptime), programmatic SEO foundation (M-013), authored blog scaffolding, YouTube channel structure, beta cohort invited (30–50 beta → 200–500 soft → 5K+ Y1 public).

**Strategic step:** maps to Step 3.

**ID range:** LCH-001 to LCH-009. To be populated in subsequent planning sessions.

**Launch gate:** all of Section 1 (UI shells) + all of Section 2 (mocks) + critical path through Sections 3–5 + all of Section 6 must be `Shipped` before LCH-009 (public launch) can ship. Quality-gated, no date pressure (memory lock).

---

## Appendix A — Migration from Old Backlog

The following old-style ticket IDs are absorbed into PRD entries below. As each old ticket is migrated, this table gets a new row.

| Old ID | New PRD ID | Notes |
|--------|-----------|-------|
| _(empty)_ | _(empty)_ | Populated as entries are written |

Old IDs continue to appear in git commit history and the deprecated `lemethodic-backlog-2026-05-18.md`. New work must use PRD IDs.

---

## Appendix B — Files Killed by This PRD

The following files are deprecated as of May 21, 2026. Do not reference, do not regenerate:
- `parse_backlog.py` (orchestrator)
- `dispatch_agent.py` (orchestrator)
- `n8n-workflow.json` (orchestrator)
- `lemethodic-workload-allocation.html` (assumed multi-agent capacity, obsolete in solo mode)
- `LeMethodic_Master_Backlog.docx` (was already dead per prior memory lock)

The strategic artifacts from May 17–18 (`lemethodic-architecture-v2.html`, `lemethodic-gtm-v2.html`, `lemethodic-ops-blueprint-v1.html`, `lemethodic-revenue-estimator.html`) remain valid reference documents — they inform the PRD but the PRD is now the execution source of truth.

---

*End of PRD v1.*
