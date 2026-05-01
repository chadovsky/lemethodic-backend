---
SYNCED COPY — DO NOT EDIT HERE
Source of truth: github.com/chadovsky/lemethodic-frontend/blob/main/LEMETHODIC-CURRICULUM.md
This is a read-only mirror for backend reference (P-200..P-269 ticket implementation, P-202 schema design, etc).
To re-sync: re-fetch from frontend repo, replace this file, commit.
Last sync: 2026-05-01 (v0.2)
---

# LEMETHODIC-CURRICULUM.md

**Status:** Draft v0.2 — second pass, dashboard architecture rebuilt, all v0.1 open questions resolved
**Authoritative scope:** This document defines the pedagogical model, level diagnostic, curriculum paths, dashboard hierarchy, and onboarding-to-content bridge for LeMethodic. It supersedes the original P-100 dashboard spec and frames the full P-200 architecture work.
**Last updated:** 2026-05-01 (v0.2)
**Author of source model:** Chadi Bakhay (7,000+ hours TCF/DELF tutoring experience, Book-Lab pedagogy IP)
**Drafted by:** Co-PM (Claude) — flagging `[INFERRING]` where extrapolating beyond stated model, `[ASSERTING]` where operationalizing the stated model into specific decisions.

---

## 1. Why this document exists

LeMethodic sells data-visualized progress to French learners preparing for high-stakes exams (TCF, TEF, DELF). The product's competitive moat is **method-as-brand** — a structured pedagogical journey codified into software, not a generic practice tool with a coat of paint.

Until this document exists, every UI decision, prescription engine choice, and onboarding question is guesswork. The dashboards have no curriculum behind them; the prescription engine has nothing to prescribe; the onboarding has no path to route into.

This document codifies the curriculum. Everything downstream — dashboard content, ticket scope, content authoring priorities, Phase 1 vs Phase 2 split — derives from here.

---

## 2. Pedagogical foundations

### 2.1 The CEFR progression model (the spine)

Each CEFR level is a **qualitatively different game**, not a harder version of the same game. The transition between levels is not "more drills" but a structural shift in what the learner can do:

| Level | Core ability | What the leap to the next level requires |
|---|---|---|
| **A2** | Can speak (in fragments) | Achieve sentence stability — the engine works |
| **B1** | Can communicate (in flawed but real sentences) | L1 detachment + structural sophistication (stop translating, start subordinating) |
| **B2** | Can argue (correctly but without nuance) | Refinement under pressure (idiomatic, flexible, controlled) |
| **C1** | Can think in the language | Native effortlessness |
| **C2** | Can live in the language | (Out of scope for Phase 1 product) |

The implication: a curriculum that just "teaches more grammar" cannot move a B1 student to B2. The student has to make a *qualitative shift*, and the curriculum's job is to engineer that shift.

### 2.2 Ceiling marker philosophy

The product does **not** use a single global error severity score. It uses **per-level ceiling markers** — specific patterns that, when present, prevent progression to the next level.

A wrong article means different things at different levels:
- At A2: the article system isn't acquired yet → blocks A2→B1 transition
- At B2: a residual error under pressure → does not block B2→C1 transition

Same surface error, different diagnostic meaning. The diagnostic engine must read errors **in the context of the level being assessed**.

### 2.3 The sentence assembly vs sentence structure boundary

The clearest operational definition of A2 vs B1, drawn from Chadi's tutoring experience:

> **A2** = the learner does not fully control the engine of the sentence. Production is fragments, memorized chunks, infinitives substituting for conjugation, dropped pronouns, broken negation.
>
> **B1** = sentences exist (even when wrong). The engine runs. The learner builds sentences — they're just often built incorrectly.
>
> **B2** = sentences are correct. The bottleneck shifts from grammatical engine to discursive precision, idiomatic phrasing, and nuance.
>
> **C1** = correctness is automatic. The bottleneck is native-likeness.

### 2.4 Threshold metric

Errors are measured as **errors per 100 words**, not errors per minute or errors per recording. This normalizes across recording lengths and writing samples.

A category-specific threshold defines the boundary. **Numbers below are placeholders.** Real values come from P-250 calibration against Chadi's documented Preply students.

| Category | A2→B1 boundary (errors/100 words) | B1→B2 boundary | B2→C1 boundary |
|---|---|---|---|
| Tense choice | <8 | <3 | <1 |
| Conjugation | <10 | <4 | <1 |
| Prepositions | <8 | <4 | <2 |
| Pronoms relatifs | n/a (rarely attempted) | <3 | <1 |
| L1 transfer (sentence structure) | n/a | <2 (sharp drop is the signal) | 0 detectable |

### 2.5 Building blocks: grammar + vocabulary + Tâche application

Vocabulary is not a separate axis from grammar. It is the **carrier wave**. Grammar is exercised through topical content. A student practicing "L'environnement et la pollution" simultaneously activates:

- Vocabulary (les émissions, le réchauffement, durable, lutter contre…)
- Grammar (passé composé to describe what was done, conditionnel for hypotheticals, subjonctif après "il faut que")
- Tâche application (a TCF Tâche 3 monologue prompt on this theme)

This three-fold integration is the **cluster**. Clusters are the curriculum's atomic unit, not lessons. (See §5.)

### 2.6 The spiral method

The curriculum is not strictly linear. It uses **spiral progression**: a cluster is taught, the path moves on, and earlier clusters are revisited at deeper levels later.

Example: pronouns are introduced in the B1 path (basic COD/COI). The student moves on to relative clauses, subordination, etc. Later in the B2 path, pronouns are revisited with double pronoun placement (`me le donner`, `lui en parler`) and stylistic variants. Same topic, deeper layer, after intermediate material has been absorbed.

`[ASSERTING]` Phase 1 product implements simplified spiral: each path has 3-4 phases, and later phases explicitly revisit clusters from earlier phases with deeper exercises.

---

## 3. Level-by-level diagnostic model

This section defines the ceiling markers per level. The diagnostic engine reads a submission (recording or writing), detects which markers fire, and assigns a level.

### 3.1 A2 ceiling markers (what blocks A2→B1)

Phase 1 detection: existing analysis pipeline supports A2-level marker detection. No Phase 2 deferral.

Source: Chadi's diagnostic ranking, ordered by severity.

1. **Sentence structure breakdown** — production lacks subject-verb-complement frame. Examples: "Moi aller travail demain", "Pas comprendre question". The strongest A2 signal.
2. **Conjugation instability in present tense** — "je va", "nous fait", "ils prend". The present tense is not automated.
3. **Infinitive substitution** — using infinitive where a conjugated verb is needed. "hier je aller au travail", "je manger avec lui".
4. **Negation breakdown** — "ne…pas" not internalized. Variants: "je comprends pas" (acceptable orally but unstable), "pas je comprends", "je pas comprends".
5. **Pronoun absence or misuse** — dropping subject pronouns ("va au marché"), confusing tonic and unstressed forms ("lui parle moi").
6. **Severe preposition confusion** — chaotic, inconsistent use. "je vais au Maroc en lundi", "je parle avec à lui".
7. **Article system not acquired** — missing, random, or overused. "je mange pomme", "j'aime le chocolat" (overgeneralization).
8. **Severely limited vocabulary** — overuse of "faire", "chose", "très bon / très mauvais".
9. **Word order issues** — "je demain vais travailler", "toujours je mange ici".
10. **Phonetic spelling in writing** — "komsa", "bocou", "parske".

**Transition criterion (A2→B1):** sentence structure stable across submissions. Markers 1-4 below tolerable thresholds. Markers 5-10 may persist but are no longer the dominant signal.

### 3.2 B1 ceiling markers (what blocks B1→B2)

1. **L1 transfer (sentence structure translated from English)** — the #1 B1 signal. "Je suis d'accord avec que…", "Je pense que c'est important de faire…" used incorrectly structurally. The learner is translating instead of thinking in French.
2. **Preposition errors (systemic)** — "dépend sur", "intéressé par à", "aller à travail". Deeply systemic, hard to fake. B1 learners guess; B2 learners control verb-preposition pairs automatically.
3. **Verb argument structure errors** — "demander quelqu'un" (instead of demander à quelqu'un), "expliquer quelque chose" (missing indirect object). Shows incomplete verb encoding.
4. **Pronoun avoidance or misplacement (COD/COI/y/en)** — "Je donne le livre à lui", "Je parle de ça" (instead of j'en parle). B1 = avoidance; B2 = flexible automatic use.
5. **Inability to build complex sentences** — overuse of et, parce que; lack of relative clauses (qui, que, dont), subordination (bien que, tandis que, ce qui). The ceiling marker for B1 written/spoken production.
6. **Tense system weakness** — narrative confusion, passé composé/imparfait distinction broken, everything in passé composé, no background vs. action.
7. Agreement errors (gender/number) — common but not decisive. Many B2s still slip here.
8. Article misuse — frequent but not decisive at this transition.
9. Lexical approximation — "chose", "truc", repetitive verbs. Affects richness, not classification.
10. Spelling/accent — lowest diagnostic value at this transition.

**Transition criterion (B1→B2):** L1 transfer markers reduced to occasional. Subordination present. Verb-preposition pairs and pronouns largely automatic. Agreement and article errors may persist.

### 3.3 B2 ceiling markers (what blocks B2→C1)

1. **Lack of discursive precision** — generic ideas. "C'est important dans la société", "Il y a des avantages et des inconvénients". The #1 B2 ceiling marker.
2. **Limited connector range** — overuse of et, mais, parce que, donc. Lack of cependant, en revanche, dans la mesure où, d'autant plus que.
3. **Imperfect register control** — mixing informal lexicon ("genre, trucs, super") with formal contexts.
4. **Awkward collocations** — "faire une décision", "prendre une expérience". Grammar correct, native ear rejects.
5. **Hesitation in complex syntax** — relative clauses started but not closed cleanly: "les personnes que… qui… euh…".
6. Inconsistent advanced structures — subjunctive sometimes correct, sometimes broken: "il faut que il fait…".
7. Over-reliance on safe structures — repeating "je pense que…", "il y a…", "on peut…".
8. Residual preposition errors — present but inconsistent, not systematic.
9. Minor agreement errors under pressure.
10. Pronunciation/fluency imperfections.

**Transition criterion (B2→C1):** discursive depth, varied connectors, register-aware. Collocation errors rare. Complex syntax under control.

### 3.4 C1 ceiling markers (what blocks C1→C2)

`[INFERRING — out of Phase 1 scope, included for completeness]`

1. Lack of idiomaticity (still "learner-like" phrasing).
2. Limited stylistic flexibility (same tone throughout).
3. Subtle collocation imperfections.
4. Argumentation lacks sharpness or original framing.
5. Overuse of safe high-level structures.
6. Slight register mismatches.
7. Hesitation in dense or abstract expression.
8. Rare but noticeable preposition/article imperfections.
9. Slight redundancy or wordiness.
10. Minor agreement slips under pressure.

**Transition criterion (C1→C2):** out of Phase 1 scope.

### 3.5 The diagnostic decision rule

For any submission, the engine scans for ceiling markers from A2 upward. The level assigned is the **highest level whose ceiling markers do NOT fire dominantly**.

Pseudocode:

```
def assign_level(submission):
    if A2_markers_fire_dominantly(submission):
        return "A2"
    if B1_markers_fire_dominantly(submission):
        return "B1"
    if B2_markers_fire_dominantly(submission):
        return "B2"
    if C1_markers_fire_dominantly(submission):
        return "C1"
    return "C2"  # out of scope, treat as C1+
```

"Dominantly" means: the markers' aggregate density exceeds the level's threshold (per §2.4). Refining this rule is a calibration task (P-250).

---

## 4. The four paths

Each path is structured in **phases**. Each phase contains 3-5 clusters (§5). Phases compress or expand based on student timeline (urgency-driven).

### 4.1 A2 → B1 path: "Build the engine"

**Goal:** stabilize the grammatical engine. Move from fragment production to flawed-but-real sentence production.

**Phase A2.1 — Engine basics:** present tense + basic pronouns; articles + gender intuition starter; negation system.

**Phase A2.2 — First past + first future:** passé composé with avoir/être; futur proche; common irregular verbs (être, avoir, aller, faire, pouvoir, vouloir, savoir).

**Phase A2.3 — Sentence assembly:** question formation; basic connectors (et, mais, parce que, donc); adjective placement and basic agreement.

**Phase A2.4 — Spiral revisit + Tâche prep:** revisit pronouns (now with COD basics); revisit articles (now with partitive); intro to imparfait (just for routine descriptions); first guided Tâche 1 attempts.

**Vocabulary themes (A2 path):** family, daily activities, food and shopping, body and health, home, school, weather, basic time expressions, greetings and politeness, basic professions.

**Estimated duration:** 12 weeks at 4-6 hrs/week practice.

### 4.2 B1 → B2 path: "Stop translating, start structuring"

**Goal:** detach from L1 (English) sentence structure, acquire subordination and pronoun automation, master tense system.

**This is Chadi's beachhead path** — the most-used path in Phase 1.

**Phase B1.1 — Tense mastery:** imparfait vs passé composé (the narrative distinction); plus-que-parfait; futur simple + futur antérieur; conditionnel présent (introduction).

**Phase B1.2 — Pronoun automation:** COD / COI placement; pronouns y and en; double pronouns (me le, lui en, etc.); pronoms toniques.

**Phase B1.3 — Subordination:** pronoms relatifs simples (qui, que, dont, où); intermediate connectors (cependant, néanmoins, en revanche, d'ailleurs); discours indirect au présent; expression de la cause.

**Phase B1.4 — L1 detachment (the make-or-break phase):** verb-preposition pairs (the systemic preposition fix); Les Moules (sentence architecture, anti-translation reflexes — Chadi's existing IP); question formation under pressure (Tâche 2 specific); expression de la conséquence.

**Phase B1.5 — Spiral revisit + B2 entry-test prep:** revisit tenses with concordance des temps starter; revisit subordination with bilan exercises; intro to subjonctif présent (just après il faut que / je veux que); intro to gérondif; expression du but.

**Vocabulary themes (B1→B2 path):** society and politics, environment and ecology, technology and media, work and economy, education, travel and culture, health and lifestyle, urban vs rural living, debates and opinions, family dynamics in modern society, immigration and identity, science and innovation.

**Estimated duration:** 8 weeks at 4-6 hrs/week practice (compressible to 4-6 weeks for Cram persona, expandable to 12 for Foundation persona).

**Cluster count target:** 15-20 unique clusters across the 5 phases. (Increased from v0.1 estimate of 10-12, per Chadi's review.)

### 4.3 B2 → C1 path: "From correct to refined"

**Goal:** add discursive precision, register control, idiomatic phrasing.

**Phase B2.1 — Advanced structures:** subjonctif (présent, passé, après expressions de doute / nécessité / émotion); conditionnel passé and contrefactuels; discours indirect au passé (concordance des temps); gérondif (correct usage, not decorative); l'opposition et la concession.

**Phase B2.2 — Discursive sophistication:** nominalisation (transforming verbs to nouns); la mise en relief (c'est…que, ce qui…c'est); advanced connectors (d'autant plus que, sous prétexte que, à condition que); l'expression de la quantité (avancé); l'expression de la comparaison.

**Phase B2.3 — Refinement:** Les Moules des Idées (rhetorical patterns — Chadi's existing IP); register awareness (formel / standard / familier); collocation banks per topic; place de l'adjectif qualificatif (stylistic); les indéfinis (avancé).

**Phase B2.4 — Spiral revisit + C1 entry tasting:** revisit subordination at C1 depth; revisit pronouns with stylistic variants; intro to interrogation avec inversion; first attempts at C1-style argumentation.

**Vocabulary themes (B2→C1 path):** abstract debate (justice, liberté, identité), professional registers (legal, medical, business), cultural production (cinéma, littérature, arts), philosophical and social commentary, economics and policy, geopolitics, climate and sustainability discourse.

**Estimated duration:** 10 weeks at 4-6 hrs/week practice.

### 4.4 C1 → C2 path: "Native-likeness"

`[INFERRING — out of Phase 1 product scope, sketched for completeness]`

**Goal:** idiomaticity, stylistic effortlessness, rhetorical control under pressure.

**Phase C1.1 — Idiomatic depth.** **Phase C1.2 — Stylistic range.** **Phase C1.3 — Rhetorical mastery.**

This path is **not part of Phase 1**. C1 candidates entering the product see "Diagnostic available, full path coming Q4 2026" and are routed to the B2→C1 path's most advanced clusters as interim content.

---

## 5. The cluster system

A **cluster** is the atomic curriculum unit. Every cluster contains:

1. **Grammar topic** — one focused grammatical pattern (e.g., subjonctif présent after expressions of doubt)
2. **Vocabulary theme** — a thematic field (e.g., l'environnement) that contextualizes the grammar
3. **Tâche application** — a TCF-shaped task (Tâche 1, 2, or 3 prompt) that forces the student to use both grammar and vocabulary

A cluster's outputs:

- A **lesson** (explanation + examples — delivered as a mix of formats per cluster: in-app markdown for short conceptual lessons, downloadable PDF for reference-style content, embedded video for high-demonstration topics like pronunciation or rhythm)
- An **exercise set** (typically 5-15 items, calibrated to the grammar topic)
- A **practice prompt** (a Tâche-shaped prompt the student records or writes)
- A **detection rubric** (what the diagnostic engine looks for in the student's production to score the cluster as "absorbed" or "needs revisit")

`[ASSERTING]` This cluster shape is consistent across all paths. The diagnostic engine, dashboards, and prescription engine all operate on cluster as the unit. Lesson delivery format (markdown / PDF / video) is decided per cluster during authoring (P-211), not enforced uniformly.

### 5.1 Cluster taxonomy (drawn from canonical French textbook organization)

The grammar progression Chadi uploaded (Chapitres 1-32 from the blue/teal grammar reference) is a near-canonical curriculum. Extracted as cluster candidates:

**A2 grammar clusters:** Présent indicatif, Articles (définis/indéfinis/partitifs), Passé récent + passé composé, Imparfait + passé composé (introduction), Plus-que-parfait, Pronoms personnels toniques, Doubles pronoms personnels, Pronoms possessifs et démonstratifs, Le gérondif et le participe présent, Pronoms relatifs simples, L'expression du futur, Le futur antérieur, L'infinitif présent et passé, Les verbes avec ou sans préposition + infinitif, L'expression du passif.

**B1/B2 grammar clusters:** Conditionnel présent (construction + utilisation), Conditionnel passé (construction + utilisation), Subjonctif présent (construction + utilisation), Subjonctif passé, Indicatif ou subjonctif?, Le superlatif, Le discours indirect (au présent), Le discours indirect (au passé), L'expression de la cause, L'expression de la conséquence, Les expressions de temps, L'expression du but, L'opposition et la concession, La condition et l'hypothèse.

**B2/C1 grammar clusters:** Les verbes pronominaux, Les expressions impersonnelles, Verbes à constructions multiples, Verbes avec ou sans préposition, Interrogation avec inversion du sujet, La négation, La mise en relief, Les indéfinis, Les pronoms relatifs complexes, La nominalisation, Place de l'adjectif qualificatif, Les adverbes (avancé), Les articles (avancé), Le complément de nom, La situation dans l'espace, L'expression du temps (avancé), La manière et le moyen, L'expression de la quantité, L'expression de la comparaison, L'hypothèse et la condition (avancé).

**Vocabulary theme clusters (cross-level):** Drawn from the Vocabulaire Progressif and similar topical references — Les usages / La politesse, La famille, L'amour / Les sentiments, Le caractère / La personnalité, La communication, Le corps / Les mouvements / La santé, La description physique / L'apparence, Les vêtements / La mode / Les couleurs, La maison / Le logement, Les activités quotidiennes, Les produits alimentaires / Les commerces / Faire les courses, La cuisine / Les repas / Le restaurant, Le temps qui passe / Le temps qu'il fait / Le climat, L'école / L'enseignement, Les professions / La vie professionnelle, La technologie / Les médias, L'argent / La banque, La poste / Les services / L'administration, La géographie / La francophonie, La ville / La campagne / Les directions, Les transports / La circulation, Le tourisme / Les voyages / Les vacances, Les loisirs / Les sports / Les jeux, Les arts / Les spectacles / La culture, Nature et environnement, Diversité / Politique / Société, Débats et opinions.

**Total cluster space:** ~80-100 distinct clusters across all four paths and all combinations of grammar + vocabulary. Phase 1 prioritizes 15-20 clusters in the B1→B2 path, plus 3-4 starter clusters each for A2 and B2 paths (waitlist preview content).

### 5.2 Spiral revisits

Within a path, later phases revisit clusters from earlier phases at deeper layers. Within the cluster system, spiral takes the form:

- A first-encounter cluster: introduction + basic exercises + simple Tâche prompt
- A revisit cluster: same grammar topic, more advanced vocabulary theme, more demanding Tâche prompt, focus on automation under pressure

Example: "Pronoms COD/COI" in Phase B1.2 (introduction + recognition exercises + Tâche 1 prompt where pronouns are required) → revisited in Phase B1.5 with Les Moules anti-translation focus + Tâche 2 prompt requiring fluid pronoun substitution under conversational pressure.

---

## 6. Diagnostic engine spec

### 6.1 Inputs

- Audio recordings (Tâche 1, Tâche 2, Tâche 3 — all tasks already in the product)
- Writing submissions (Phase 2 — see ticket roster)

### 6.2 Pipeline

For each submission:

1. **Transcription** (already in product via existing ASR pipeline)
2. **Tokenization + word count** (compute words for the per-100-word denominator)
3. **Error detection per category** — leverage existing analysis (the four couches already scored: Étendue, Cohérence, Correction, Aisance) plus new category-specific detectors:
   - Tense choice errors (parser-based)
   - Conjugation errors (morphological analysis)
   - L1 transfer (pattern matching against known calques)
   - Preposition errors (verb-preposition validation)
   - Subordination presence (count of relative clauses, complex sentences)
   - Connector variety (vocabulary diversity in connector lexicon)
   - A2 sentence structure breakdown detection
   - A2 infinitive substitution detection
4. **Marker firing computation** — for each level (A2/B1/B2/C1), compute which markers fired and their density
5. **Level assignment** — apply the rule from §3.5
6. **Cluster-level diagnosis** — for clusters the student has been working on, score "absorbed" / "partial" / "needs revisit" based on detection rubric matches

### 6.3 Confidence scoring

Each level assignment carries a confidence:
- **High confidence** — multiple submissions agree, ceiling markers are clearly above/below threshold
- **Medium** — single submission, markers near threshold
- **Low** — first submission, ambiguous markers, recommend additional diagnostic recordings

Dashboard surfaces show confidence to the student. Low confidence triggers "we need 2 more recordings to be sure of your level" UX.

### 6.4 Phase 1 implementation realism

`[ASSERTING]` Building all detectors in §6.2 step 3 by June 30 is unrealistic. Phase 1 ships with:

- Detectors that already exist (the four couches scoring)
- L1 transfer detector (high-leverage, calibrated against known patterns from Les Moules)
- Preposition error detector (verb-preposition pair validation against a lexicon)
- Subordination counter (count of qui/que/dont/où/lequel + count of subordinating conjunctions)
- Connector variety scorer (token-level diversity in connector use)
- A2 sentence structure breakdown detector (heuristic: presence of conjugated verb per main clause)
- A2 infinitive substitution detector (heuristic: conjugated verb missing where context requires)

This is enough for level assignment with medium confidence across all four levels. Other detectors (tense choice, idiomaticity, register awareness) are Phase 2.

---

## 7. Dashboard hierarchy

This section is the heart of the product's competitive positioning. The dashboards are not progress charts. They are the **method made visible**.

### 7.1 Three design principles

**Principle 1 — Show the method, don't hide it.** Most ed-tech hides pedagogy from the user. "You scored 75%" tells the user nothing about WHY. LeMethodic's value is the *why*. Dashboards make the method visible — the ceiling markers, the L1 transfer detection, Les Moules violations — explicitly, with plain-language explanation. Risk of overwhelm is mitigated by Principle 2.

**Principle 2 — Two modes, one product.** Every dashboard supports two modes:

- **Calm mode (default)** — minimal numbers, friendly framing, single recommended action. For students who get anxious looking at error breakdowns. For exam-week brain.
- **Method mode (toggleable)** — full diagnostic exposure, ceiling markers ranked, error categories visualized, L1 patterns highlighted. For students who want to understand why.

This is rare in ed-tech. Most products pick one stance (gamified-friendly vs. clinical-detailed) and force everyone into it. Letting the student pick is a small UX choice with a large positioning consequence. **Calm is the default; method is opt-in.**

**Principle 3 — Time-aware, not just data-aware.** Every other ed-tech dashboard treats today and exam-day as equivalent points on a chart. LeMethodic doesn't. With 8 weeks to exam, the dashboard looks different than with 2 weeks to exam. Different content, different urgency, different recommended action. As exam date approaches, dashboards reorganize.

### 7.2 The eight building blocks

Eight reusable dashboard elements that compose into the surface views. Each one is an idea on its own; together they form the product's visual vocabulary.

#### Block 1 — The Ceiling Marker Map

A grid visualization showing ALL detected ceiling markers across recent submissions, mapped onto the level transition the student is working through.

- Horizontal axis: the levels (A2 / B1 / B2 / C1)
- Vertical axis: the ceiling markers, ordered by Chadi's severity ranking
- Each cell: colored — red (firing dominantly), yellow (firing occasionally), green (cleared)
- The student's "current level" is the column where reds and yellows concentrate

Surfaced in: Overall Progress (method mode), Curriculum view (method mode).

What the student gets: an honest picture of "where am I stuck." Not a number, not a percentage. A map.

What the product gets: visual proof of method depth. Screenshots are sharable on social media. Marketing artifact.

#### Block 2 — The Goulet Stack

The bottleneck visualization, made central. A vertical stack:

- Top of stack: the #1 ceiling marker firing right now. Specific, named. "L1 transfer in question formation."
- Below: secondary markers, decreasing severity.
- Below those: cleared markers (greyed out, "you used to struggle with this — now resolved").
- Each marker is a card. Click in = see examples from your recent recordings + the cluster designed to fix it.

Visual metaphor: a funnel. The bottleneck at the top is what you work on now. Once cleared, it grays out and the next bottleneck rises.

Surfaced in: Overall Progress (calm mode default — top 3 only; method mode shows full stack).

#### Block 3 — Recording Replay With Inline Diagnostics

When a student plays back a recording from history, the dashboard shows the transcription with inline diagnostic annotations:

- Green underline on uses of B2 structures (gérondif used correctly, etc.)
- Red highlight on detected ceiling markers (L1 transfer, wrong preposition)
- Click any annotation = explanation + cluster link
- Audio playback synced to text — the highlighted word is the word being spoken

This is what a tutor does in person. Listen, mark up. No tutor-tech product does this in real-time playback today. (Some have post-hoc text feedback. None integrate it with audio playback.)

Surfaced in: Speaking dashboard, per-Tâche dashboards.

Effort medium because it requires word-level timestamps from the ASR (existing AssemblyAI output supports this) plus a UI for synced annotations.

#### Block 4 — Path Topography View

Instead of a linear "Phase 1 → Phase 2 → Phase 3" progress bar, show the path as a topographic map.

- Each cluster is a node
- Nodes are arranged by depth (entry-level clusters at edges, advanced clusters at center)
- Edges connect clusters that share dependencies
- Student's current position: a glowing node
- Visited nodes: filled
- Unlocked-but-not-started: outlined
- Locked: greyed
- Spiral revisits: shown as return paths to earlier nodes

This visualizes the spiral method. Linear progress bars can't show spirals. Topographies can.

Surfaced in: Curriculum view (centerpiece).

Implementation: D3.js force-directed graph or Sankey. Already available in stack.

#### Block 5 — The Dialogue Box

A dashboard element that's not a chart. A contextual short message from the system, written like Chadi would write it.

> "Last week you cleared 3 of your top 5 bottlenecks. Today's focus: relative pronouns. Why this one? Because it shows up in your last 4 Tâche 2 recordings, and it's blocking the leap to fluent question-framing."

Prescription engine output, but presented as text not as data. The student feels like there's a tutor on the other side.

Chadi writes the templates. The system fills them with detected data. Chadi becomes the voice of the product.

Surfaced in: Overall Progress (top of view, both modes).

Templates needed: 30-50, varied by context (after good week, after plateau, after regression, mid-cluster, end-of-phase). Authoring task for Chadi.

#### Block 6 — Time-Adaptive UI (lean version, Phase 1)

The dashboards adapt based on `daysUntilExam`. **Lean version:** existing surfaces stay the same structure, but content and emphasis adapt.

- "Today's focus" Dialogue Box copy varies (relaxed framing >30 days; urgent framing 15-30 days; crammed framing <15 days)
- Goulet Stack ordering shifts (in cram mode, short-fix bottlenecks rise above slow-fix bottlenecks — fix what you can fix in time)
- Exam countdown gains visual weight as it shrinks (small text → bold → red urgent)
- Practice CTAs prefer high-leverage clusters when time is short

Phase 2 layers on full mode redesigns (Foundation / Acceleration / Cram modes with different navigation structures). Phase 1 ships the lean version which delivers ~70% of the value at ~20% of the cost.

Surfaced in: All dashboards. Meta-feature.

#### Block 7 — The Mistake Repository

Every detected ceiling marker, across all submissions, indexed and searchable.

- "Show me every L1 transfer pattern I've made"
- "Show me every preposition error from the past month"
- Each entry: the original sentence, the detected error, the correct version, the cluster that addresses it

A study tool. Students review their own mistakes the way they'd review flashcards. Aggregate view = pattern recognition.

Surfaced in: Overall Progress (method mode link), as a standalone tab inside Progress.

Effort small because data already exists in submission analysis. UX is a search + filter view.

#### Block 8 — The Confidence Visualizer

Diagnostic confidence (§6.3) shown as a meter, not a percentage:

- Three states: low / medium / high
- Plain language: "We're not sure yet — give us 2 more recordings" / "We have a strong read on you"
- Drives behavior: low confidence triggers "take diagnostic" CTAs in primary positions

Addresses the trust risk: students are more forgiving of "we're calibrating" than of "you're A2" when they think they're B1.

Surfaced in: Overall Progress snapshot (always visible).

### 7.3 Hierarchy and surface composition

```
Overall Progress (home of the Progress tab)
├── Speaking Dashboard (drill-down from Speaking tab OR from Progress)
│   ├── Tâche 1 Dashboard
│   ├── Tâche 2 Dashboard
│   └── Tâche 3 Dashboard
├── Mistake Repository (tab within Progress)
└── Writing Dashboard (drill-down from Writing tab — Phase 2)

Curriculum view (separate tab in main nav)
├── Path Topography (centerpiece)
├── Cluster detail (drill-down per cluster)
└── My Path overview (current phase, upcoming clusters)
```

### 7.4 Overall Progress dashboard composition

**Calm mode (default):**

1. **Snapshot** — current detected level, target, exam countdown, Confidence Visualizer (Block 8)
2. **Today's focus** — Dialogue Box (Block 5), single CTA from prescription engine
3. **Goulet Stack (top 3)** (Block 2) — visual centerpiece, top 3 bottlenecks only
4. **Recent activity** — calendar view (kept from current implementation)
5. **Toggle**: top-right "Method mode →"

**Method mode (toggled):**

1. Snapshot — same
2. Today's focus — same
3. **Ceiling Marker Map** (Block 1) — full grid replaces the Goulet Stack
4. **Mistake Repository link** (Block 7) — "browse your detected patterns"
5. **Goulet Stack (full)** (Block 2) — all bottlenecks, including cleared
6. Recent activity — same
7. Toggle: "← Calm mode"

Both modes time-adapt per Block 6.

### 7.5 Speaking dashboard composition

- Estimated TCF speaking score with band visualizer
- Per-Tâche cards (T1, T2, T3) with last submission preview + drill-into-Tâche-dashboard CTA
- **Recording Replay with Inline Diagnostics** (Block 3) — accessible from any submission in history
- Speaking-specific patterns (fluency, hesitation, prosody — Phase 2)

### 7.6 Per-Tâche dashboards (T1, T2, T3)

- Score history line chart with band overlay
- Last recording with **Inline Diagnostics** (Block 3, reused)
- Cluster connection (which clusters this Tâche tests)
- Practice CTA with cluster-aligned prompt selection (random vs. cluster-specific)

### 7.7 Curriculum view composition

- Path header — "B1 → B2 (Visa-Urgent)" with phase indicator
- **Path Topography View** (Block 4) — centerpiece
- Side panel: current cluster detail
- Phase indicator: where you are in the spiral
- Time-adaptive (Block 6) reorganization based on `daysUntilExam`

### 7.8 Cluster detail view

- Cluster header — grammar topic + vocabulary theme + Tâche application
- Lesson — content rendered per delivery format (in-app markdown / embedded PDF / embedded video)
- Exercises — exercise set with answer checking
- Practice prompt — the cluster-specific Tâche prompt with record button
- My history — past attempts at this cluster's exercises and prompts, scored

### 7.9 Writing dashboard (Phase 2)

Mirror of Speaking dashboard but for written submissions. Out of Phase 1 scope.

### 7.10 Mistake Repository (standalone tab)

- Search bar + category filters
- Chronological feed of detected errors
- Per-entry: original sentence, error highlight, correction, link to addressing cluster
- Aggregation view: "Your top error patterns this month"

---

## 8. Onboarding-to-path bridge

### 8.1 The current state

Onboarding asks: current level, target level, exam date. **The answers do not change anything downstream.** This is the gap.

### 8.2 The redesign

Onboarding becomes the path-routing system. A questionnaire (~10-12 screens, expanded from original 6-screen target) with answers that map directly to:

- Path entry point (which level path the student starts on)
- Initial diagnostic prompts (what to record / write first)
- Compression factor (how to fit the path into available time)
- Vocabulary theme prioritization (which themes the student needs first)
- Time-adaptive UI mode (Foundation / Acceleration / Cram)

Each question must earn its place — it must drive a downstream decision. Questions that don't influence routing get cut.

### 8.3 Onboarding questions and their downstream effects

`[ASSERTING — proposing]`

| Question | Answer options | Downstream effect |
|---|---|---|
| What's your French level today? | A2 / B1 / B2 / Not sure | Sets initial path; "Not sure" routes to extended diagnostic |
| What's your target level? | B1 / B2 / B2+ / C1 | Sets path target and exam-ready threshold |
| When is your exam? | Date picker, "no exam yet" | Sets path duration + compression factor + Block 6 time-adaptive mode |
| Why are you learning French? | Visa (TCF Canada) / Job / Studies / Personal | Sets vocabulary theme priorities + Tâche emphasis |
| What's your strongest skill today? | Speaking / Writing / Reading / Listening | Diagnostic emphasis (record-first vs write-first) |
| What's your weakest skill? | Same options | Cluster prioritization within path |
| How many hours/week can you commit? | <3 / 3-5 / 5-10 / 10+ | Path compression factor + practice volume |
| Any specific topics you'll be tested on? | (Multi-select theme list) | Vocabulary cluster prioritization |
| What's your native language? | English / Other | L1 transfer detector calibration (Les Moules optimized for English speakers) |
| Have you taken a French exam before? | Yes / No / Recently | Diagnostic flow length (skip prelim if recent results) |
| Do you prefer detailed feedback or simple guidance? | Detailed / Simple | Default mode (method vs. calm) |
| Daily reminder time preference | Time picker / no reminders | Notification scheduling (post-launch, infra-permitting) |

After questionnaire: 3 diagnostic recordings (one per Tâche). Diagnostic confirms or adjusts the level the student self-reported.

### 8.4 Waitlist UX for unbuilt paths (Phase 1)

For levels where Phase 1 has only diagnostic, not full content (A2 path beyond starter clusters, C1 path):

- Diagnostic runs as normal
- Result page: "You're at level X. Your path is in active development — full curriculum ships [date]. While you wait, here's what we recommend [free resources / partner content / interim cluster recommendations from adjacent path]."
- Subscription continues to charge during waitlist period only if user explicitly opts in to "early access subscription" — otherwise free during waitlist
- Email when their path ships

`[ASSERTING]` This protects the brand: students don't pay for empty product. But it requires the diagnostic + diagnostic explanation to be valuable enough on its own that students stay engaged through the waitlist period.

---

## 9. Phase 1 vs Phase 2 split

### 9.1 What ships June 30 (Phase 1, Gamma scope per Chadi)

**Diagnostic engine:**
- L1 transfer detector
- Preposition error detector
- Subordination counter
- Connector variety scorer
- A2 sentence structure breakdown + infinitive substitution detectors
- Couches scoring (existing)
- Level assignment with confidence
- All four levels (A2, B1, B2, C1) supported by diagnostic

**Curriculum content:**
- B1 → B2 path: full content authored (15-20 clusters, lessons + exercises + practice prompts)
- A2 → B1 path: minimal content — first 3-4 starter clusters only, rest is waitlist
- B2 → C1 path: minimal content — first 3-4 starter clusters only, rest is waitlist
- C1 → C2 path: not built, waitlist only

**Dashboards (per §7):**
- Overall Progress (Block 2 + Block 5 + Block 8 + calm/method toggle + Block 6 lean)
- Speaking dashboard (Block 3)
- Per-Tâche dashboards (Block 3 reused)
- Curriculum view (Block 4)
- Cluster detail
- Mistake Repository (Block 7)
- Method mode adds Block 1 (Ceiling Marker Map)

**Onboarding:**
- Full questionnaire per §8.3 (10-12 screens)
- Diagnostic flow integrated
- Waitlist UX for A2 / B2+ candidates

**Prescription:**
- Single-modal (speaking only)
- "Today's recommended action" via Dialogue Box (Block 5) driven by current cluster + ceiling marker detection
- No cross-modal yet

### 9.2 What ships Phase 2 (post-launch)

- Writing analysis pipeline
- Writing dashboard + per-activity dashboards
- Cross-modal prescription (speaking + writing patterns combined)
- Full A2 path, B2→C1 path, C1→C2 path content
- Tense choice + conjugation + idiomaticity detectors
- Streak system (F-067)
- Per-Tâche-prompt difficulty calibration
- Adaptive cluster recommendation (engine learns what works per user)
- **Time-adaptive full mode redesigns** (Foundation / Acceleration / Cram with different navigation structures, beyond Phase 1 lean version)
- Audio-synced playback for Recording Replay (Block 3 enhancement)

### 9.3 Content authoring requirements (Phase 1)

This is the operational gap. By June 30 launch, the following must exist as authored content:

**B1 → B2 path (15-20 clusters):** lesson (1-3 pages markdown OR PDF reference OR short video), exercise set (5-15 items), practice prompt (1 Tâche-shaped prompt), detection rubric (what to look for in submissions). Mixed delivery format per cluster: short conceptual lessons in-app markdown, reference-style content as downloadable PDF, demonstration-heavy topics (pronunciation, prosody) as embedded video.

**A2 → B1 path (3-4 starter clusters):** same structure, less content.

**B2 → C1 path (3-4 starter clusters):** same structure, less content.

**Onboarding copy:** all questions + all waitlist UX copy in EN and FR.

**Dialogue Box templates (Block 5):** 30-50 templates varied by context. Each template uses placeholders for detected data (e.g., `{cluster_name}`, `{streak_count}`).

**Diagnostic explanation copy:** for each level, plain-language explanation of "you're at this level because [ceiling markers fired]" — written once per level, referenced by engine output.

`[ASSERTING]` Content authoring is the launch-blocking activity. Code work without content = empty product. Chadi's tutor experience makes him the only person who can author this content. Time allocation: estimate 80-100 hours of focused writing across 8 weeks pre-launch (increased from v0.1's 60-80 estimate due to expanded cluster count and Dialogue Box templates).

---

## 10. Ticket roster

This roster supersedes the original P-100 spec and the placeholder P-200 tickets. Tickets are sequenced by dependency.

### 10.1 Foundation tickets (must ship first, in order)

**P-200 — Diagnostic engine: detector implementation**
Priority: HIGH. Pre-launch blocker.
Scope: implement L1 transfer detector, preposition error detector, subordination counter, connector variety scorer, A2 sentence structure detector, A2 infinitive substitution detector. Plug into existing analysis pipeline alongside couches scoring. Output ceiling markers per level.

**P-201 — Diagnostic engine: level assignment + confidence**
Priority: HIGH. Depends on P-200.
Scope: implement level assignment rule (§3.5). Add confidence scoring. Surface level + confidence on diagnostic page and Snapshot via Block 8.

**P-202 — Cluster data model**
Priority: HIGH.
Scope: backend schema for clusters (grammar topic, vocabulary theme, Tâche application, lesson reference, exercise set reference, prompt reference, detection rubric, lesson delivery format flag). Migration. CRUD for clusters via admin or seed script.

**P-203 — Path data model**
Priority: HIGH. Depends on P-202.
Scope: backend schema for paths (level start, level target, phases, cluster sequence per phase). Path entity, Phase entity, PathCluster join table.

**P-204 — User progress model**
Priority: HIGH. Depends on P-202, P-203.
Scope: backend schema for user's path enrollment, current phase, current cluster, cluster status (not_started / in_progress / absorbed / needs_revisit), cluster history.

### 10.2 Content scaffolding tickets

**P-210 — B1→B2 path seed data**
Priority: HIGH. Depends on P-202, P-203. Pre-launch blocker.
Scope: seed the B1→B2 path's 15-20 clusters in the database (titles + structure only; content authored separately). Phase boundaries defined.

**P-211 — Cluster content authoring (Chadi work, not engineering)**
Priority: HIGH. Pre-launch blocker.
Scope: author lesson + exercise set + practice prompt + detection rubric for each B1→B2 cluster. Decide delivery format per cluster (markdown / PDF / video). Delivered as files into the system.
Owner: Chadi.

**P-212 — Starter cluster seed for A2 and B2 paths**
Priority: MEDIUM. Pre-launch.
Scope: seed first 3-4 clusters of A2→B1 path and first 3-4 of B2→C1 path. Used as waitlist preview content.

**P-213 — Dialogue Box template authoring**
Priority: MEDIUM. Pre-launch.
Scope: author 30-50 Dialogue Box templates (Block 5) varied by context. Placeholders for detected data. Owner: Chadi.

### 10.3 Onboarding tickets

**P-220 — Onboarding questionnaire rebuild**
Priority: HIGH. Depends on P-203.
Scope: rebuild current onboarding to match §8.3 (10-12 screens). Each answer maps to user profile fields that drive path assignment.

**P-221 — Diagnostic flow integration**
Priority: HIGH. Depends on P-201, P-220.
Scope: after questionnaire, run 3 diagnostic recordings (one per Tâche). Engine output updates user level. Path assignment confirmed/adjusted.

**P-222 — Waitlist UX for A2 and B2+ paths**
Priority: HIGH. Pre-launch.
Scope: when user diagnostic places them in a not-yet-built path, show waitlist screen with explanation, free interim resources, optional early-access opt-in.

### 10.4 Dashboard tickets (full §7 implementation)

**P-230 — Overall Progress dashboard rebuild**
Priority: HIGH. Depends on P-201, P-204.
Scope: rebuild /progress per §7.4. Calm mode default + method mode opt-in. Includes Block 2 (Goulet Stack), Block 5 (Dialogue Box), Block 8 (Confidence Visualizer). Replaces current P-100 surface entirely.

**P-231 — Speaking dashboard**
Priority: HIGH.
Scope: implement §7.5. New surface, drill-down from Speaking tab. Includes Block 3 (Recording Replay with Inline Diagnostics).

**P-232 — Per-Tâche dashboards**
Priority: MEDIUM. Depends on P-231.
Scope: implement §7.6. Three dashboards (T1, T2, T3). Block 3 reused.

**P-233 — Curriculum view (path surface)**
Priority: HIGH. Depends on P-203, P-204, P-210.
Scope: implement §7.7. New surface accessible from main nav. Includes Block 4 (Path Topography).

**P-234 — Cluster detail view**
Priority: HIGH. Depends on P-202, P-211.
Scope: implement §7.8. Per-cluster page with lesson, exercises, prompt, history. Multi-format lesson rendering (markdown / PDF embed / video embed).

**P-235 — Ceiling Marker Map**
Priority: HIGH (method mode visibility moat). Depends on P-200, P-201.
Scope: implement Block 1. Surfaceable from Overall Progress (method mode) and Curriculum view (method mode).

**P-236 — Mistake Repository**
Priority: MEDIUM. Depends on P-200.
Scope: implement Block 7. Standalone tab inside Progress.

**P-237 — Time-Adaptive UI (lean version)**
Priority: HIGH. Meta-ticket affecting all dashboards. Depends on P-230, P-231, P-233.
Scope: implement Block 6 lean version. `daysUntilExam` reads + conditional rendering for Dialogue Box copy, Goulet Stack ordering, exam countdown weight, practice CTA emphasis. Full mode redesigns deferred to Phase 2.

### 10.5 Prescription engine tickets

**P-240 — Today's recommended action**
Priority: HIGH. Depends on P-204, P-213.
Scope: prescription logic — given user's current path/phase/cluster + recent submissions + Dialogue Box template selection, output the single recommended next action. Surface on Overall Progress §7.4 section 2.

**P-241 — Cluster-level prescription**
Priority: MEDIUM.
Scope: when a cluster's detection rubric scores "needs revisit", prescription engine routes user back to that cluster instead of advancing.

### 10.6 Calibration and content ops

**P-250 — Threshold calibration**
Priority: HIGH. Depends on P-200, P-211.
Scope: run real recordings of known-level students (Chadi's existing Preply students with documented levels) through the diagnostic. Tune thresholds in §2.4 and §3.x against ground truth. Iterate until level assignment agrees with Chadi's expert judgment ≥80% of the time.

**P-251 — Lesson content delivery infrastructure**
Priority: MEDIUM.
Scope: implement multi-format lesson delivery (markdown rendered in-app, PDF embedded with download option, video embedded). Specify file storage on Spaces, versioning, FE rendering.

### 10.7 Phase 2 stub tickets (filed but deferred)

**P-260 — Writing analysis pipeline** (Phase 2)
**P-261 — Writing dashboard** (Phase 2)
**P-262 — Cross-modal prescription** (Phase 2)
**P-263 — A2 path full content** (Phase 2)
**P-264 — B2→C1 path full content** (Phase 2)
**P-265 — C1→C2 path** (Phase 2)
**P-266 — Tense + conjugation + idiomaticity detectors** (Phase 2)
**P-267 — Time-Adaptive UI full mode redesigns** (Phase 2 — Foundation / Acceleration / Cram with different navigation structures)
**P-268 — Audio-synced playback for Recording Replay** (Phase 2)
**P-269 — Streak system** (Phase 2 — F-067 reframed)

---

## 11. Open questions and risks

### 11.1 v0.1 questions — resolved in v0.2

1. ✅ **Threshold calibration** — proceed with placeholders, calibrate in P-250.
2. ✅ **Cluster count for B1→B2** — expanded to 15-20 (from 10-12).
3. ✅ **Lesson delivery format** — mix per cluster (markdown / PDF / video). Decision per cluster during authoring.
4. ✅ **A2 detection completeness** — Phase 1 (existing analysis pipeline supports A2 detectors).
5. ✅ **Onboarding question count** — expand beyond 8 (now 10-12). Each question earns its place by routing decision.

### 11.2 New v0.2 open questions

1. **Block 1 (Ceiling Marker Map) visibility default.** Currently shown only in method mode. Should it be visible (collapsed) in calm mode too, with "tap to expand" UX? Tradeoff: discoverability vs. overwhelm.
2. **Block 4 (Path Topography) on mobile.** D3 force-directed graphs are challenging on 380px viewports. Mobile rendering may need a simplified linear-with-hints fallback. Decision needed during P-233.
3. **Time-adaptive thresholds.** §7.2 Principle 3 references >30 days / 15-30 days / <15 days as the time bands. Are those right? Do TCF candidates' anxiety patterns actually shift at those marks, or different?
4. **Dialogue Box templates: how many is enough?** 30-50 estimate from §9.3. Could be too few (feels repetitive) or too many (authoring overhead). Real number emerges from beta testing.

### 11.3 Risks

1. **Content authoring is the critical path.** P-211 + P-213 = 80-100 hours of Chadi's writing. If it slips, launch slips. No engineering workaround.
2. **Threshold calibration assumes ground truth.** P-250 needs Chadi's documented assessments of past students. If documentation is informal, calibration is qualitative not quantitative.
3. **Diagnostic precision matters for trust.** A student diagnosed as A2 who feels they're B1 will churn fast. Block 8 (Confidence Visualizer) is the safety valve. If confidence display is weak, level disagreement = churn.
4. **Waitlist UX risk for non-beachhead personas.** A2 and B2+ students seeing "your path coming later" may not subscribe at all. Acceptable risk because beachhead is B1→B2, but worth tracking acquisition by entry level.
5. **Prescription engine simplicity.** Phase 1 prescription is not adaptive — it follows the path. If users want "Duolingo-like adaptive recommendations," Phase 1 will feel rigid. Mitigation: marketing positions LeMethodic as structured-and-curated, not adaptive.
6. **Method mode discoverability.** If calm mode is the default and method mode is opt-in, users who would benefit from method mode may never find it. Mitigation: first-week onboarding nudges users to "try method mode for full diagnostic detail" once.
7. **Block 4 (Path Topography) over-engineering.** Force-directed graphs are visually impressive but can become unreadable as cluster count grows. May need simplification or a hybrid linear-with-spiral-callouts visualization.

### 11.4 Decisions deferred to later passes

- Exact cluster sequence within each phase of each path
- Lesson outlines and exercise structures (P-211 authoring work)
- Writing analysis architecture (Phase 2)
- Streak system mechanics (F-067, deferred to Phase 2)
- Cross-modal pattern detection (Phase 2)
- Full mode time-adaptive UI (Phase 2)

---

## 12. Update log

- **2026-05-01 — v0.1 initial draft.** Co-PM (Claude) authored from Chadi's pedagogical model and uploaded textbook references. Awaiting Chadi review pass.
- **2026-05-01 — v0.2 second pass.** All v0.1 open questions resolved. §7 Dashboard hierarchy fully rebuilt — three design principles (show the method / two modes / time-aware) and 8 building blocks (Ceiling Marker Map, Goulet Stack, Recording Replay with Inline Diagnostics, Path Topography, Dialogue Box, Time-Adaptive UI lean, Mistake Repository, Confidence Visualizer). Calm mode default + method mode opt-in. Time-adaptive lean version in Phase 1; full mode redesigns deferred to Phase 2. Cluster count for B1→B2 expanded to 15-20. Onboarding expanded to 10-12 questions. Lesson delivery format = mix per cluster. A2 detection moved to Phase 1. Ticket roster expanded from 24 to 33 tickets (including Phase 2 stubs).

---

**End of document.**
