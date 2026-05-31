# Le Methodic -- Release Roadmap

**Source of truth for milestone definitions.** Ticket bodies live in `BACKLOG.md`; milestone membership is recorded in each ticket's `Milestone:` field. This file defines what each milestone means and what its acceptance criteria are.

**Current operating mode:** manual, one micro-feature per session.
See `docs/prd-v1.md` (sections 1--7) for the full feature inventory.
See `BACKLOG.md` for the per-ticket queue.

---

## M1 -- Soft Beta

Responsive product across every in-app surface. First external cohort can register, run a full oral diagnostic (Tache 1/2/3), view results, and navigate L'Ecole and Le Vocabulaire surfaces on both mobile and desktop without hitting placeholder copy or broken layouts.

**Acceptance criteria:**
1. Landing page, onboarding flow, /ecole, /speaking/*, /progress, /cluster/[slug], and auxiliary pages (privacy/terms/refund/signup) all verified at 1440px and 375px per F-225 protocol.
2. Exam-selector (F-221) live with 5-slug routing; onboarding submits without 422.
3. CouchesDiagnostic radar shows 5 axes with brand labels (V-009).
4. /ecole phase structure shows 2 phases (Fondations 1-16, Approfondissement 17-27) per V-010.
5. Writing surface wired to F-224 backend; submit succeeds without timeout (V-016a).
6. Navigation: bottom nav mobile-only; TopNav desktop (V-013c).

---

## M2 -- Visual Polish

Platform reads at Codersera/Neuralink-tier visual quality on all surfaces. Font system, typography, micro-animations, and hero atmosphere are locked.

**Acceptance criteria:**
1. Switzer + Fraunces font system live across all surfaces (V-005).
2. Hero atmospheric animation (accent marks, parallax) shipping respects prefers-reduced-motion (V-003).
3. Differentiation cards visually distinct with per-card micro-imagery (V-004).
4. Loading states across all AI-heavy flows carry rotating Chadi-voice messages (F-211).
5. Em-dash strip complete across all FE copy (V-002).

---

## M3 -- Post-Launch P1

Defensive hardening and highest-signal post-launch features. Tache 2 catalog is live and correct. FE consumes live BE data instead of hardcoded literals.

**Acceptance criteria:**
1. Tache 2 Picker reads live BE catalog (F-061.1); empty-state and error-state branches tested.
2. Tache 2 scenario content replaced from placeholder to Chadi-authored text (F-BUGS-001-BE-A.content).
3. RAG wiring for diagnostic surface (W-003): La Carte / Le Goulet retrieval cites corpus exemplars.

---

## M4 -- Le Vocabulaire

Third product pillar live alongside L'Ecole and Le Diagnostic. Phase 1 seed (faux_amis, calques_anglais, prepositions) confirmed in production; practice and test UI accessible to users.

**Acceptance criteria:**
1. Le Vocabulaire DB schema live (F-320); alembic migration applied on prod.
2. Phase 1 seed (F-321) reviewed by Chadi and seeded on prod via gate-7 protocol; 500+ rows in vocab_chunks covering the 3 Phase 1 topics.
3. Practice UI (F-322): hide/reveal, self-grade, personal lists functional.
4. Test UI (F-323): MCQ, matching, dropdown, completion modes functional.
5. L'Ecole content routed out of Le Vocabulaire where applicable (F-321.curriculum).

---

## M5 -- AI Infrastructure

Oral analysis aligned to 5 couches. RAG retrieval layer wired into runtime for both oral and writing. Le Maitre (ElevenLabs Chadi-clone) active on L'Ecole and Le Vocabulaire surfaces. Activation layer (D-028/D-029/D-033) live.

**Acceptance criteria:**
1. Oral analysis (analysis.py) emits 5 couches; COUCHE_ORDER unified with writing (V-009.be).
2. RAG retrieval wired at diagnostic call-time for writing and oral (F-312 + data-layer/vectorize.py runtime hook).
3. Le Maitre voice active on L'Ecole lesson narration and Le Vocabulaire feedback paths.
4. B2 scarcity addressed (D-034 enrichment run confirms >= 500 native B2 chunks).

---

## M5.5 -- BE Pre-Monetization Hardening

Server-side security and performance prerequisites that must be complete before any user is charged. M6 assumes this milestone is already shipped.

**Acceptance criteria:**
1. Tier enforced server-side: free-tier token rejected (402/403) from any paid endpoint; paid-tier token passes; verified by pytest, not by FE gating (P-105).
2. AI endpoints rate-limited per user: breach of per-endpoint limit returns 429; limit configurable via env var (F-401).
3. FK indexes present and in use: recordings.user_id and feedbacks.recording_id indexed; EXPLAIN confirms index usage on analytics queries (F-402).
4. Flagged endpoints free of N+1: query count on each of the 7 audited endpoints (analytics/dashboard, analytics/progress, analytics/pass, admin/dashboard, admin/users, recordings/history, writing/history) is constant with respect to result size (F-403).

---

## M6 -- Stripe + LLC + Paywall UI

Payment infrastructure and paywall live. Users can subscribe, enter a 7-day free trial, and be correctly gated after trial expiry. Server-side tier enforcement is already live from M5.5 -- this milestone wires the Stripe subscription state into that enforcement layer.

**Acceptance criteria:**
1. Stripe Atlas LLC formed and activated; Stripe API keys in DO env (B-100).
2. Stripe integration live: $29/mo subscription, $199 Sprint one-time, $499 Premium SKUs; webhook endpoint verifying HMAC signature (P-106).
3. 7-day trial mechanics: new user auto-enrolled on first session; trial_will_end webhook fires 3 days early; transition to active-paid or lapse handled correctly (P-106 trial scope).
4. Paywall UI: lapsed/trial-expired users see paywall redirect; past recordings remain read-only accessible (FE).
5. Legal entity decision resolved (B-101).

Note: tier enforcement (returning the correct tier from DB) is M5.5 scope (P-105), not M6 scope. M6 only populates real subscription_tier values into the DB via Stripe webhook handling.

---

## M7 -- Pre-Ship Sign-Off

Quality gate before public launch. All soft-beta cohort feedback addressed. Analytics and observability instrumented. Test user and placeholder data removed from production.

**Acceptance criteria:**
1. All M1-M6 tickets in Shipped state.
2. Test user (id=5) and orphaned data removed from production DB (C-100).
3. FR voice audit complete; tu-form enforced across all copy (F-226).
4. Analytics setup live (B-105): product telemetry capturing conversion funnel.
5. ENV=production, REDIS_URL, RESEND_API_KEY, HCAPTCHA_SECRET confirmed set in DO console.

---

## M8 -- Post-Launch Growth

Post-launch retention and social proof. Triggered by conversion signal from the first paying cohort.

**Acceptance criteria:**
1. Beta user testimonial pipeline seeded with first 5 testimonials (M-108).
2. Reddit community engagement cadence established (M-104).
3. YouTube anchor video published (M-103).
4. F-321 Phase 2 topic expansion decision made based on usage data from Phase 1.
