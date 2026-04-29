# Block 4 — Vision-Driven Backlog

**Date:** April 29, 2026
**Purpose:** Translate strategy into tickets. The holy document.
**Reading time:** ~25 min. Reference document — keep open while working.

---

## How this document works

This backlog has three ticket prefixes:

- **P-xxx** = Product tickets (code, infrastructure, features)
- **M-xxx** = Marketing tickets (content, channels, outreach)
- **B-xxx** = Business operations tickets (legal, brand, pricing infrastructure, ops)

Tickets are organized by **Phase**:

- **Phase 1** = Now → June 30, 2026 (~2 months). Soft beta launch + first paying users.
- **Phase 2** = July 1 → October 31, 2026 (~4 months). Public launch, content engine, Writing tab, exam simulator.
- **Phase 3** = November 1, 2026 → April 30, 2027 (~6 months). Coursera-shape platform, video courses, score guarantee, tutor tier.

Each ticket has: `[ID] Title · Owner · Effort · Phase · Notes`

Owners: **Chadi** (you), **Claude Code** (your AI dev), **v0/Vercel** (design tool), **External** (designer/copywriter/etc you might hire).

Effort: S (1-3 hours), M (4-12 hours), L (1-3 days), XL (4-7 days), XXL (1+ weeks).

---

## Top of stack — what locked from strategy session

**From Block 1:** Position E (Speaking Lab) growing to D (Coursera-shape) over 12 months.
**From Block 2:** $19.99/month or $99 for 6 months, 7-day free trial, geographic pricing for India/Brazil/Vietnam, score guarantee phased in over 3 phases.
**From Block 3:** Method-as-brand (not founder-as-brand). Visa-Urgent TCF Candidate persona. La Méthode central to identity. Three positioning sentences in three contexts.

**12-month target:** $100K ARR (~500 paying users at blended ARPU).

---

# PHASE 1 — Soft Beta + First Paying Users

**Window:** Now → June 30, 2026
**Goal:** Validate the product with 10-30 beta users, convert ~10 to paying users, build first TCF-specific testimonials.
**Success metric:** 10 paying users at $19.99/month or $99 lifetime by June 30.

---

## P-100 series — Product (Phase 1)

### P-100 · Real Progress Dashboard · Claude Code · L · Phase 1
**Why:** Locked in Block 3 reactions — Progress moved from Phase 2 to Phase 1. Without it, beta users can't see improvement, the diagnostic feels like a one-shot result, "human + AI completeness" thesis breaks.
**Scope:**
- Per-recording: 4 Couches scores (Le Fond / Les Moules des Idées / Les Moules / Les Réflexes Anglais)
- Trend over time (line chart, last 10 recordings)
- Top 3 recurring errors with module recommendation
- Time-spent stat (last 7 days)
- Streak counter (consecutive days with activity)
**Acceptance:** User opens Progress tab, sees scores trending up/down, knows which Couche to focus on next, sees personalized recommendation.

### P-101 · Naming decision + branding refresh · Chadi · L · Phase 1 (URGENT — blocks marketing)
**Why:** FluentPath has both a Norwegian competitor (fluentpath.ai) and namespace conflict. FluentLab taken (fluentlab.org IELTS). Block 3 locked Method-as-brand approach.
**Scope:**
- Run domain availability check on 5-10 candidates aligned with Méthode-as-brand identity
- Strong candidates to test: Aisance, Maîtrise, LeCap, MéthodeBakhay (you rejected pedagogy names yesterday, but worth revisiting given namespace closing)
- Reserve .com + .ai domains
- Decide on logo direction (text-only vs. icon+text)
- Update GitHub repos (chadovsky/fluentpath-backend → new name)
- Update DigitalOcean app name
- Update Vercel project name
**Acceptance:** New name locked. Domains owned. Repos renamed. Production URLs updated.
**Note:** This blocks all marketing tickets. Do this in week 1 of Phase 1.

### P-102 · Visual quality pass via Tailwind UI template · Chadi + v0 · L · Phase 1
**Why:** Block 2 acknowledgment — "FluentLab is more aesthetic" is a real concern. Aesthetic gap is closable in 2-3 days for ~$300.
**Scope:**
- Buy Tailwind UI template ($150-300) — recommend Catalyst or Studio template
- Use v0 to iterate on landing page, dashboard, recording session UI
- Apply consistent design system: typography, spacing, colors, button styles
- Pastel color palette per Promova benchmark (locked in earlier sprint)
**Acceptance:** Production frontend has consistent visual quality across all screens. Subjectively: feels "professional" not "scrappy."

### P-103 · Audio upload + serve security hardening · Claude Code · M · Phase 1
**Why:** Carried over from previous sprint as known security debt. Pre-launch security item.
**Scope:**
- Server-side audio upload size cap (max 5MB or similar)
- user_id association on audio files
- Auth-checked serve routes (only the recording owner can fetch their audio)
**Acceptance:** Curl test confirms unauthorized requests get 403. Upload >5MB rejected at API.

### P-104 · Background tab timer drift fix on PTT 60s cap · Claude Code · S · Phase 1
**Why:** Carried over. Edge case but real for users tabbing away.
**Scope:** Use Date-based timer instead of setTimeout drift on Push-to-Talk 60s cap.
**Acceptance:** Tab away during recording, come back, timer is accurate.

### P-105 · 7-day free trial logic · Claude Code · L · Phase 1
**Why:** Locked from Block 2 — trial-first reduces conversion friction massively.
**Scope:**
- New user signup → automatic trial start, no credit card required (Magoosh-style)
- Trial countdown visible in app
- Day 5: in-app reminder to convert
- Day 6: email reminder ("trial ends tomorrow")
- Day 8: trial expired, account locked except for "upgrade" page
**Acceptance:** Full trial → paywall flow tested end-to-end.

### P-106 · Stripe integration with dual pricing · Claude Code · L · Phase 1
**Why:** Need to actually take money. Dual pricing (subscription + one-time) per Block 2.
**Scope:**
- $19.99/month subscription
- $99 one-time for 6-month access
- Geographic pricing: $9.99/mo and $59 one-time for India/Brazil/Vietnam/Egypt/Morocco/Philippines (use IP-based detection via Stripe)
- Receipt emails
- Cancellation flow (no dark patterns — Block 2 noted Promova's billing complaints)
**Acceptance:** Test card completes both subscription and one-time purchase. Geographic pricing detected correctly via VPN test.

### P-107 · "Soft satisfaction guarantee" copy + refund flow · Chadi + Claude Code · S · Phase 1
**Why:** Block 2 phased score guarantee. Phase 1 promises completion+experience refund, not score.
**Scope:**
- Pricing page copy: "Complete L'École path (16 lessons) + 3 mock exams. If you don't feel more confident in your speaking, full refund within 30 days."
- Internal refund flow (manual approval initially, automated later)
- Refund-eligibility tracker per user
**Acceptance:** A user can request refund, you can approve, money returns via Stripe.

### P-108 · Pronunciation feedback (basic) · Claude Code · XL · Phase 1
**Why:** FluentLab does this. PrepMyFuture doesn't. Differentiator + closes obvious feature gap.
**Scope:**
- Use existing AssemblyAI integration to extract pronunciation confidence per word
- Highlight low-confidence words in transcription view
- Surface as 5th dimension under "Les Réflexes Anglais" couche
**Acceptance:** User records, sees specific words flagged for pronunciation.
**Note:** Carried from existing F-058 backlog. Closes critical FluentLab feature parity.

### P-109 · TCF Canada exam simulator MVP · Claude Code · XL · Phase 1
**Why:** "Mock exam" is a critical conversion claim. Without it, marketing copy can't say "practice the real exam."
**Scope:**
- Full TCF Speaking simulation: Tâche 1 (2 min interview, no prep), Tâche 2 (5.5 min interaction, 2 min prep), Tâche 3 (4.5 min monologue, 1.5 min prep)
- Timer enforcement per task
- Examiner-style audio prompts (pre-recorded TTS)
- Combined score across all 3 tasks
- Comparison to user's previous mock attempts
**Acceptance:** User completes full mock simulation in ~12 minutes, gets unified score.

### P-110 · Onboarding refinement · Chadi + v0 · M · Phase 1
**Why:** Current 6-screen onboarding works but pre-strategy. Now that persona is locked (Visa-Urgent TCF Candidate), onboarding should reflect this.
**Scope:**
- Screen 1: "Quand passez-vous votre TCF/TEF?" (with date picker)
- Screen 2: "Quel score visez-vous?" (NCLC 4-9)
- Screen 3: "Votre niveau de français actuel?" (A0 → C1)
- Screen 4: "Combien de temps par jour?" (15min → 60min+)
- Screen 5: "Création de votre plan personnalisé..."
- Screen 6: First diagnostic recording
**Acceptance:** Onboarding produces a personalized 8-week plan based on TCF date and current level.

---

## M-100 series — Marketing (Phase 1)

### M-100 · Past Preply student outreach · Chadi · S · Phase 1 (DO THIS FIRST)
**Why:** Block 2 noted weakness — Preply leverage is real but specific. Past students are warmest beta pool.
**Scope:**
- Pull list of every Preply student you've worked with (memory says ~50-100)
- Filter for: still learning French, exam-prep focused, Anglophone
- Email/Preply message: "I'm building [BRAND]. Want early access free?"
- Target: 20% response rate = 10-20 beta users
**Acceptance:** 10+ confirmed beta users from past Preply network.
**Effort:** 4 hours total work (compile list, draft message, send).

### M-101 · Landing page copy in [BRAND] voice · Chadi + Claude · M · Phase 1
**Why:** Three positioning sentences locked in Block 3. Need to deploy them.
**Scope:**
- Hero: Candidate 3 — "[BRAND] est ce que PrepMyFuture a oublié — l'expression orale, enfin entraînée correctement"
- Subhead: Candidate 2 (paraphrased) — "7 000 heures d'enseignement TCF, transformées en coaching IA disponible 24/7"
- About section: Founder story — Chadi, 7,000 hours, Les Moules, La Méthode Triple Action
- Method section: La Méthode en Couches explained visually (4 Couches with one-line descriptions)
- Pricing section: $19.99/mo or $99/6mo, 7-day free trial
- Testimonials: 3-5 real Preply review screenshots (with permission)
- FAQ: TCF-specific questions ("Will this prepare me for NCLC 7?", "How is this different from PrepMyFuture?")
**Acceptance:** Landing page reads as if a TCF coach with strong opinions wrote it, not as if an AI app generated it.

### M-102 · Convert top Preply reviews to social proof · Chadi · S · Phase 1
**Why:** Block 1 finding — 59 Preply reviews are real social proof if extracted with permission.
**Scope:**
- Identify top 10 Preply reviews
- Reach out to each student: "Can I quote you on the new site? With your name + photo if comfortable."
- Get explicit permission (screenshot of email reply)
- Format as testimonials on landing page + dedicated /testimonials page
**Acceptance:** 5+ on-record testimonials with name + result + permission.

### M-103 · YouTube channel launch · Chadi · L · Phase 1
**Why:** Block 3 method-as-brand strategy. Screen-share videos teaching method, optional face-cam.
**Scope:**
- Channel name: [BRAND] in French + English
- First 3 videos in 30 days:
  1. "Pourquoi vous échouez à la TCF expression orale" (~6-8 min, French audio, English subtitles)
  2. "La Méthode en Couches: Les 4 niveaux d'évaluation TCF" (~10 min)
  3. "Tâche 3 TCF: Comment répondre en 4.5 minutes" (~12 min)
- Format: Screen-share with method diagrams, voice-only or face-cam in corner
- SEO titles + descriptions targeting "TCF preparation," "TCF Canada speaking," "TCF NCLC 7"
**Acceptance:** 3 videos uploaded, each 500+ views in first 30 days through Reddit + LinkedIn cross-promotion.
**Effort:** ~6-8 hours per video including scripting, recording, editing, uploading.

### M-104 · Reddit community engagement · Chadi · S/recurring · Phase 1
**Why:** r/Canada_PR has 100K+ members. Direct path to Visa-Urgent TCF Candidate persona.
**Scope:**
- Identify 5 target subs: r/Canada_PR, r/ImmigrationCanada, r/EuropeFIRE, r/French (TCF subset), r/learnfrench
- Rule: 90% value-driven posts, 10% link-back. Don't spam.
- Weekly cadence: 2-3 substantive comments per sub, 1 longer post per week
- Format: Answer questions about TCF speaking section, share tips from method, occasionally link to YouTube video or blog post
**Acceptance:** 3+ Reddit users sign up for [BRAND] trial directly attributable to Reddit posts in first 60 days.

### M-105 · LinkedIn long-form content (French + English) · Chadi · M/recurring · Phase 1
**Why:** Block 3 channel — LinkedIn skews professional, matches "Visa-Urgent TCF Candidate" who's career-focused.
**Scope:**
- Post 1-2 per week, alternating French and English
- Topics: TCF method explainers, common mistakes, exam strategy, Express Entry insights
- Use La Méthode names explicitly to brand
- Include CTA: "Comment below if you want a free trial"
**Acceptance:** LinkedIn account at 500+ followers within 60 days, 3+ trial signups attributable.

### M-106 · Blog launch on [BRAND].com/blog · Chadi · M/recurring · Phase 1
**Why:** SEO compounds. Long-form content explains method, ranks for TCF queries.
**Scope:**
- 1-2 posts per month minimum
- First 3 priority articles:
  1. "How to prepare for TCF Canada speaking section: The complete guide"
  2. "What is NCLC 7 and how do you actually achieve it?"
  3. "TCF vs TEF Canada: Which exam should you take?"
- Each article 1500-2500 words, with internal links to product
**Acceptance:** First 3 articles published. Indexed by Google within 30 days.

### M-107 · Express Entry Discord/Telegram outreach · Chadi · S · Phase 1
**Why:** These communities have thousands of active immigrants planning their applications. Highest-intent audience.
**Scope:**
- Identify 5-10 active French-PR-focused Discords/Telegrams
- Join, observe, contribute value
- After 2 weeks of value-only contribution, soft-mention [BRAND] when contextually appropriate
- DO NOT spam.
**Acceptance:** 5+ trial signups attributable to Discord/Telegram in 60 days.

### M-108 · Beta user testimonial pipeline · Chadi · M · Phase 1
**Why:** Block 3 noted — your existing Preply testimonials are generic French. Need TCF-specific case studies fast.
**Scope:**
- For every beta user who improves measurably, request 30-min recorded conversation
- Edit into 60-second testimonial video
- Get written permission to use across marketing
- Target: 5 video testimonials by end of Phase 1
**Acceptance:** 5+ video testimonials from real TCF candidates with measurable improvement.

---

## B-100 series — Business Operations (Phase 1)

### B-100 · Stripe account setup with geographic pricing · Chadi · M · Phase 1
**Why:** Need this before P-106 ticket can ship.
**Scope:**
- Stripe account + tax setup (Morocco-based)
- Configure products: $19.99/mo subscription, $99 one-time, $9.99/mo geo, $59 one-time geo
- Webhook endpoint to sync Stripe → app database
- Test mode → live mode transition
**Acceptance:** Test purchases succeed in test mode. Money flows to your bank in live mode.

### B-101 · Legal entity decision · Chadi · L · Phase 1
**Why:** As you start taking money, you need a legal entity to receive it.
**Scope:**
- Decide: Moroccan SARL, Estonia e-Residency company, Delaware LLC, or stay sole proprietor for now
- Considerations: tax implications, payment processor preferences, ability to scale
- Consult with accountant if needed (~$150-300 one-time)
**Acceptance:** Legal entity decided. Bank account opened in entity name.
**Note:** This can be deferred briefly — Stripe can pay sole proprietor for first few months.

### B-102 · Privacy policy + Terms of Service · Chadi + AI · S · Phase 1
**Why:** Required for Stripe, required for legal compliance, required for trust.
**Scope:**
- Use a template generator (Termly, GetTerms, similar) — $15-30 cost
- Customize for: data we collect, how we use it, refund policy, account termination, jurisdiction
- Publish at /privacy and /terms
**Acceptance:** Both pages live and linked from footer.

### B-103 · Trademark research on new name · Chadi · S · Phase 1
**Why:** After P-101 picks a name, verify it's not trademarked in your target markets.
**Scope:**
- USPTO search (US trademark)
- INPI search (France/EU trademark)
- WIPO Global Brand Database (worldwide)
- If clear, file your own trademark application (optional but recommended for serious brand investment) — ~$300-500 USD
**Acceptance:** Name verified clear in US/EU/WIPO. Trademark filing decision made.

### B-104 · Email marketing infrastructure · Chadi · S · Phase 1
**Why:** Trial users need email reminders. Beta users need updates. You need a mailing list.
**Scope:**
- Sign up: ConvertKit, MailerLite, or Buttondown (~$0-29/month based on list size)
- Templates: trial welcome, day 5 reminder, day 7 expiring, conversion thanks, monthly newsletter
- Segments: trial users, paid users, churned users, beta-only
- Connect to Stripe for automatic segmentation
**Acceptance:** New trial signup triggers welcome email. List is segmented properly.

### B-105 · Analytics setup · Chadi + Claude Code · S · Phase 1
**Why:** Without analytics, you can't know what's working in marketing. Without that, Phase 2 decisions are blind.
**Scope:**
- Plausible Analytics or Fathom (privacy-friendly, ~$9/month)
- Track: traffic sources, signup conversion, trial→paid conversion
- Add Stripe-side events for revenue tracking
- Weekly review habit (Sundays, 30 min)
**Acceptance:** First weekly review completed by end of Phase 1 week 2.

---

## Phase 1 prioritization — what week 1 looks like

If you're staring at this thinking "where do I start?":

**Week 1 (May 1-7):**
- P-101 (naming decision) — blocks marketing
- M-100 (past Preply outreach) — start the beta pipeline
- B-100 (Stripe setup) — start the payment infrastructure
- P-100 (Progress dashboard) start

**Week 2 (May 8-14):**
- P-100 (Progress dashboard) ship
- P-105 (trial logic) start
- P-102 (visual quality pass) start
- M-101 (landing page copy) start

**Week 3 (May 15-21):**
- P-105 + P-106 (trial + Stripe) ship
- P-102 (visual quality) ship
- M-101 (landing page) ship
- Beta launch to first 10 users

**Week 4 (May 22-31):**
- Iterate on beta feedback
- M-103 (first YouTube video) ship
- M-104, M-105, M-106 (Reddit + LinkedIn + Blog) cadence starts
- M-102 (testimonials) start

**Weeks 5-8 (June):**
- P-108 (pronunciation feedback) ship
- P-109 (TCF mock exam simulator) ship
- P-107 (refund flow) ship
- M-103 cadence continues (3 videos by end of Phase 1)
- First paying user conversions
- M-108 (testimonial pipeline) starts capturing

**Phase 1 success markers (June 30):**
- 30+ beta users
- 10+ paying users at $19.99 or $99
- 3 YouTube videos live
- Landing page production-ready
- Trial → paid conversion measurable
- First 5 video testimonials in pipeline

---

# PHASE 2 — Public Launch + Content Engine + Writing Tab

**Window:** July 1 → October 31, 2026
**Goal:** Move from soft beta to public launch. Build sustainable content engine. Launch Writing tab. Test tutor classroom MVP.
**Success metric:** 100+ paying users by October 31. ~$25K MRR run rate.

---

## P-200 series — Product (Phase 2)

### P-200 · Writing tab MVP · Claude Code · XXL · Phase 2
**Why:** Locked in earlier rec. TCF Canada has Written Expression section (3 exercises, 60 min). Currently uncovered by [BRAND].
**Scope:**
- 3 task types matching TCF Written Expression
- AI feedback on grammar, vocabulary, coherence using same La Méthode framework as speaking
- Time-tracked writing sessions
- Submission → analysis → diagnostic
**Acceptance:** User completes 3-task TCF writing simulation, gets unified diagnostic.

### P-201 · TCF Canada full mock exam · Claude Code · XL · Phase 2
**Why:** P-109 (Phase 1) was speaking simulator only. Phase 2 expands to full TCF (Listening + Reading + Writing + Speaking).
**Scope:**
- Question banks for Listening (39 MCQ, 35 min)
- Question banks for Reading (39 MCQ, 60 min)
- Existing Writing module
- Existing Speaking simulator
- Combined CEFR/NCLC score across all 4 sections
**Acceptance:** User completes full 2h47m TCF simulation with realistic scoring.

### P-202 · Spaced repetition system (5-box) · Claude Code · L · Phase 2
**Why:** Memory mentions you have a 5-box spaced repetition system. Build it into product.
**Scope:**
- Vocabulary, common errors, and Les Moules patterns surfaced via SRS
- Daily cards practice
- Box-based review intervals (Leitner system)
**Acceptance:** User reviews daily cards, sees clear retention improvement.

### P-203 · Tutor Classroom MVP (B2B test) · Claude Code · XL · Phase 2
**Why:** Block 1 + 2 + 3 finding — Position C (Tutor-in-a-box) is genuinely strategic. Phase 2 tests with 2-3 friendly tutors.
**Scope:**
- "Tutor invites students" flow
- Dashboard showing per-student progress
- Comparative view (all students at once)
- Note-taking on each student
- Recommendations for next session focus
**Acceptance:** 2-3 friendly tutors (likely from your Preply network) actively using the classroom feature with their students.

### P-204 · Mobile responsiveness pass · Claude Code · L · Phase 2
**Why:** ~50-70% of users will be mobile-first. Current Next.js implementation is desktop-first.
**Scope:**
- Audit each screen on iPhone + Android
- Fix recording UI on mobile (touch interactions, microphone permissions)
- Fix dashboard responsive layout
- Fix navigation
**Acceptance:** Lighthouse mobile score 80+. Manual test on real iPhone + Android passes.

### P-205 · iOS PWA shell (no native app yet) · Claude Code · M · Phase 2
**Why:** Without a real iOS app, users have to bookmark. PWA gives "add to home screen" experience cheaply.
**Scope:**
- PWA manifest + service worker
- "Add to home screen" prompt on iOS
- App icon, splash screen
- Push notifications setup
**Acceptance:** Users can "install" [BRAND] on iPhone home screen, looks like an app.

---

## M-200 series — Marketing (Phase 2)

### M-200 · YouTube cadence — 1 video per week · Chadi · M/recurring · Phase 2
**Why:** Phase 1 proved the format. Phase 2 scales it.
**Scope:**
- 16 videos in 4 months (1/week)
- Topics: weekly TCF coaching tip, monthly long-form (15-20 min) on a Couche, quarterly student case study
- Build out: TCF preparation series (8 episodes)
**Acceptance:** YouTube subscriber count 1,000+ by end of Phase 2.

### M-201 · TikTok account (non-face content) · Chadi · M/recurring · Phase 2
**Why:** Block 3 noted you're uncomfortable with face content. TikTok works without face — text-on-screen, screen-share, animated examples.
**Scope:**
- 3 posts per week, 30-60 sec each
- Format: text-on-screen "Common TCF mistake", "Méthode tip", "Did you know..."
- French + English alternating
- Use trending sounds where appropriate
**Acceptance:** 3,000+ followers in 4 months. 3+ trial signups attributable to TikTok.
**Effort:** 30-60 min per video using CapCut + screen recordings.

### M-202 · Email newsletter — weekly · Chadi · M/recurring · Phase 2
**Why:** Email converts 10x better than social. Build the asset.
**Scope:**
- Weekly newsletter to all [BRAND] users + opt-in subscribers
- Format: 1 method tip, 1 student story (with permission), 1 product update, 1 CTA
- Length: 300-500 words
**Acceptance:** 500+ subscribers by end of Phase 2.

### M-203 · Paid ads test (~$300/month budget) · Chadi · L · Phase 2
**Why:** Once you have product-market fit (Phase 1 validated), paid ads accelerate growth. Low-budget test.
**Scope:**
- Meta ads: $200/month, target Express Entry candidates
- Google Search: $100/month, target "TCF preparation," "TCF Canada speaking"
- Track: CAC vs. LTV
- Decision criterion: if CAC < $50 and LTV > $100, scale up
**Acceptance:** First paid customer attribution within 30 days. CAC measured.

### M-204 · Affiliate program · Chadi · M · Phase 2
**Why:** French language coaches, immigration consultants, YouTube TCF creators have audience overlap.
**Scope:**
- 25% commission on first month, 10% recurring (or $20 flat per signup)
- Tracking via Stripe
- Affiliate page on site
- Outreach to 20 potential affiliates: French YouTubers (TCFonline, etc.), immigration consultants, French tutors
**Acceptance:** 5+ active affiliates, 10+ signups via affiliate program.

### M-205 · Podcast guest spots · Chadi · M · Phase 2
**Why:** Other people's audiences = your audience. Lower face-time discomfort than your own podcast.
**Scope:**
- Identify 10 podcasts: French-learning, immigration to Canada, language pedagogy
- Pitch with: "I built [BRAND] using La Méthode after 7,000 hours teaching"
- Target: 5 appearances in 4 months
**Acceptance:** 5 podcast appearances, 10+ trial signups attributable.

---

## B-200 series — Business Operations (Phase 2)

### B-200 · First hire decision · Chadi · L · Phase 2 (only if MRR justifies)
**Why:** Solo founder + Preply + product + marketing = bottleneck. First hire could be content (~$1,500/mo) or VA (~$500-1,000/mo).
**Scope:**
- Decision triggered when MRR > $3,000
- Most likely first hire: content writer (blog + LinkedIn), 10-15 hrs/week
- Source: Upwork, Fiverr Pro, or LinkedIn freelancers
**Acceptance:** Decision documented. If hired, onboarded within 30 days.

### B-201 · Customer support process · Chadi · M · Phase 2
**Why:** With 100+ users, support volume becomes real. Need a system.
**Scope:**
- Help docs (FAQ, troubleshooting)
- Support email: support@[brand].com
- Response time SLA: 24h for paid users, 48h for trial
- Use Crisp, Intercom, or HelpScout (~$25-50/month)
**Acceptance:** Support inbox with templated responses for common questions.

### B-202 · Feedback loop · Chadi · S/recurring · Phase 2
**Why:** Phase 2 product decisions need user data, not Chadi opinions.
**Scope:**
- Monthly user survey (NPS + 3 open questions)
- In-app feedback widget
- Review feedback in monthly product planning session
**Acceptance:** Monthly survey running. NPS score tracked. Feedback feeds backlog prioritization.

### B-203 · Phase out Preply hours systematically · Chadi · L · Phase 2
**Why:** Preply is bridge income, not engine. Phase out tied to MRR.
**Scope:**
- Decision rule: when [BRAND] MRR ≥ 50% of Preply income, cut Preply hours by 50%
- When MRR ≥ 100% of Preply income, cut to 5 hrs/week (most strategic students only)
- When MRR ≥ 200%, fully phase out
- Communicate with Preply students 30 days in advance
**Acceptance:** Preply hours adjusted on milestones. Dignity preserved with long-term students.

---

## Phase 2 success markers (October 31)

- 100+ paying users
- $25K+ MRR
- 16 YouTube videos live, 1,000+ subscribers
- TikTok account at 3,000+ followers
- Newsletter at 500+ subscribers
- 5+ affiliate partners active
- Tutor classroom MVP tested with 2-3 tutors
- Mobile experience polished
- First hire decision made (or deferred with reason)

---

# PHASE 3 — Coursera-Shape Platform + Real Score Guarantee + Tutor Tier

**Window:** November 1, 2026 → April 30, 2027
**Goal:** Position D realized — full platform with video courses, downloadable docs, adaptive paths. Real score guarantee backed by data. Public Tutor Classroom tier.
**Success metric:** 500+ paying users. $100K+ ARR. Profitable solo or small team.

---

## P-300 series — Product (Phase 3)

### P-300 · Video course production · Chadi + Editor · XXL · Phase 3
**Why:** This is the big Phase 3 commitment locked from Block 2 — Magoosh charges $99-$399 for self-paced test prep BECAUSE it has video lessons. You don't, yet.
**Scope:**
- 30-50 video lessons covering TCF curriculum
- Each: 8-12 minutes, screen-share + voice + occasional face-cam
- Production team: Chadi (instructor) + editor on retainer (~$500-1,000/month)
- Hosted on the [BRAND] platform (not YouTube — premium content stays gated)
**Acceptance:** Full TCF preparation course (30-50 videos) live on platform.
**Effort:** This is months of work. Plan it in phases — 10 videos/month for 5 months.

### P-301 · Adaptive learning paths · Claude Code · XXL · Phase 3
**Why:** Beyond static L'École path. After diagnostic, generate personalized 8-week curriculum.
**Scope:**
- Diagnostic identifies weakest Couche
- System generates personalized lesson sequence
- Adapts as user progresses (good performance = skip lessons; struggle = remediation)
**Acceptance:** Two users with different diagnostics see different lesson sequences.

### P-302 · Real Score Guarantee infrastructure · Claude Code · XL · Phase 3
**Why:** Block 2 committed to phased score guarantee. Phase 3 launches the real one.
**Scope:**
- Pre-program mock score → post-program mock score comparison
- Calibration against actual TCF results from Phase 1-2 users (~50-100 data points)
- "If your TCF Canada result is lower than NCLC 6, full refund + free 1-on-1 session"
- Refund eligibility tracker
**Acceptance:** Real guarantee in marketing copy backed by data.

### P-303 · Tutor Classroom public launch · Claude Code · L · Phase 3
**Why:** Phase 2 tested with 2-3 tutors. Phase 3 launches publicly.
**Scope:**
- Tutor pricing tier: $30/month per tutor, includes 10 student seats
- Self-service tutor signup
- Classroom dashboard with insights, progress tracking, session prep tools
- Marketing landing page for tutors
**Acceptance:** 10+ tutors using paid Tutor Classroom tier.

### P-304 · DELF/TEF expansion · Claude Code · L · Phase 3
**Why:** Phase 1-2 was TCF Canada focused. Phase 3 expands product to TEF Canada and DELF B1/B2.
**Scope:**
- Format-specific content for each exam
- Differentiated mock exam simulators
- Updated marketing with all 3 exam paths
**Acceptance:** Users can prepare for TEF Canada or DELF B1/B2 in addition to TCF Canada.

---

## M-300 series — Marketing (Phase 3)

### M-300 · International expansion (Italian + Spanish-speaking French learners) · Chadi · L · Phase 3
**Why:** You've already developed content for Italian-speaking French learners (memory). Phase 3 expands platform to serve them.
**Scope:**
- Italian-language landing page
- Italian-language YouTube content (subtitles or dedicated videos)
- DELF/TEF for Italian speakers content
- Then: Spanish-speaking French learners (LATAM market)
**Acceptance:** First 50 Italian-speaking users acquired.

### M-301 · Conference / event presence · Chadi · M · Phase 3
**Why:** Build authority in the French language pedagogy space.
**Scope:**
- 2-3 conference appearances: language teaching conferences, TCF/TEF educator events
- Speaking topic: "Teaching speaking with AI: lessons from 1,000+ TCF candidates"
**Acceptance:** Speaker badge at 2+ conferences.

---

## B-300 series — Business Operations (Phase 3)

### B-300 · Team expansion to 2-3 people · Chadi · L · Phase 3
**Why:** $100K ARR can support a small team. Solo founder is bottleneck.
**Scope:**
- Hire 1: content + community manager (full-time, ~$2K/month)
- Hire 2: video editor on retainer (~$1K/month)
- Optional Hire 3: TCF teacher to handle VIP tier (contractor, ~$500-1K/month based on volume)
**Acceptance:** Team of 2-3 in place. Chadi's time freed for product + strategy.

### B-301 · Investor decision · Chadi · L · Phase 3 (optional)
**Why:** At $100K ARR, you have validation. Could raise seed ($500K-2M) to accelerate, OR stay bootstrapped and profitable.
**Scope:**
- Decision: bootstrap or raise?
- If raise: pitch deck, target 5-10 pre-seed/seed investors in edtech + immigrationtech
- If bootstrap: hold growth pace, reinvest profits
**Acceptance:** Decision documented and committed to.

---

# Cross-cutting commitments

## Marketing time commitment (locked)

- 20 hrs/week dedicated to marketing across Phase 1-3
- Distribution: 8 hrs YouTube, 4 hrs TikTok/social, 3 hrs Reddit/Discord, 3 hrs LinkedIn, 2 hrs email/outreach
- This is non-negotiable for hitting $100K ARR target

## Preply phase-out commitments

- Phase 1: Continue current Preply load (~25 hrs/week) as bridge income
- Phase 2 milestone: When [BRAND] MRR ≥ 50% Preply, cut Preply by half
- Phase 2-3 milestone: When MRR ≥ 100% Preply, cut to 5 hrs/week
- Phase 3 milestone: When MRR ≥ 200% Preply, fully phase out

## Methodology naming commitment (LOCKED)

Every product surface uses La Méthode names explicitly:
- "La Méthode en Couches" on diagnostic
- "Les Moules" on sentence-architecture exercises
- "Les Moules des Idées" on B2+ rhetoric content
- "La Méthode Triple Action" as overarching brand methodology

This is the cheapest, highest-impact moat. Don't skip it.

## What [BRAND] will NOT do

- Will not become a general French app (no Duolingo competition)
- Will not become a tutoring marketplace (no Preply competition)
- Will not chase free-tier perfection (free trial yes, free product no)
- Will not have founder face on TikTok daily (Method-as-brand, not Founder-as-brand)
- Will not launch features before Phase rules say (Writing in Phase 2 not Phase 1, etc.)
- Will not skip the testimonial pipeline (M-108 → M-200 etc.)

---

# Sanity check — is this achievable?

**Honest read:** Phase 1 in 2 months is aggressive but possible if you commit the 70hrs/week pace. Phase 2 is realistic if Phase 1 hits markers. Phase 3 depends on Phase 2 momentum.

**Biggest risks to flag:**
1. **Time bottleneck.** 70hrs/week is sprint mode. You can't sustain for 12 months without burning out. Around month 4-6, hire to relieve content burden.
2. **Money bottleneck.** Phase 1 needs ~$500-1000 outlay (Tailwind UI, Stripe fees, domain, basic ads test). If you're truly without budget, raise it through 2-3 weeks of intensive Preply tutoring before launching.
3. **Audience bottleneck.** Visa-Urgent TCF Candidate persona needs to be reachable through English/French SEO. If your first 30 days of content don't generate organic traffic, paid ads become essential earlier than planned.

**None of these are blockers. All are addressable.**

---

# Immediate next steps (this week)

1. **P-101 (naming decision)** — Block this conversation gets stuck without it
2. **M-100 (Preply outreach)** — Highest-leverage marketing action, costs zero
3. **B-100 (Stripe setup)** — Infrastructure for everything downstream
4. **P-100 (Progress dashboard)** — Closes Phase 1 product gap

These four things this week. Everything else next week.

---

# Confidence summary

- Phase 1 backlog is operational and shippable: **high**
- Phase 2 backlog is solid but assumes Phase 1 success: **medium-high**
- Phase 3 backlog is directionally correct, details will refine: **medium**
- Marketing 20 hrs/week is hard but doable: **medium-high**
- $100K ARR in 12 months is achievable if all commitments hold: **medium**
- Method-as-brand strategy through entire backlog: **high**
- This document is the "holy" doc you wanted: **high**

---

# How to use this document going forward

- **Review weekly** every Sunday for 30 min. Update ticket status.
- **Update mid-phase** when reality diverges from plan. Don't pretend tickets shipped that didn't.
- **Reference in every conversation with Claude/Claude Code** — this is the canonical source of truth.
- **Commit it to your repo** alongside HANDOVER.md, CLAUDE.md, DECISIONS.md.

This is your strategy-to-steps document. Use it.

---

**End of Block 4. End of strategy session.**
