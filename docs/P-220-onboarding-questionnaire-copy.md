# P-220 — Onboarding Questionnaire Copy (FR + EN)

**Path:** Onboarding rebuild
**Audience:** Anglophone TCF/TEF/DELF candidates, primarily Visa-Urgent persona
**Format:** 11 questions, multi-screen flow (~3-5 min completion)
**Voice:** Direct, specific, no marketing fluff, no condescension
**Status:** Draft v0.1 for P-220 backend integration

---

## Voice principles applied

- Never use the word "journey." Never use "your French journey." That phrase is the SaaS-onboarding-template smell.
- No emoji.
- No "Let's get started!" or "Just a few questions."
- Each question's framing tells the user *why we're asking* in one short line, so the questionnaire feels like data collection for their benefit, not a marketing funnel.
- Skip-friendly where possible (Q4, Q5, Q6, Q9, Q10) — never block users on questions they can't answer with confidence.
- French is for French speakers and for users whose UI language is FR. English is for everyone else. Both versions are equally first-class — neither is a "translation."
- Microcopy reflects exam-realistic vocabulary: TCF, niveaux CECRL (A2/B1/B2/C1/C2), Tâche.

---

## Question 1 — Current French level

**Type:** single_select
**Required:** yes
**Routing effect:** path slug (Q1 + Q2)

### EN

**Heading:** Where are you with French right now?
**Helper:** This sets your starting point. If you're not sure, that's fine — pick the closest match and we'll calibrate from your first recordings.
**Options:**
- A2 — I can handle short, simple conversations on familiar topics
- B1 — I can describe experiences, opinions, and follow most slow conversations
- B2 — I can express myself fluently and discuss most topics with confidence
- C1 — I'm comfortable in nearly any situation but want to refine
- Not sure

### FR

**Heading:** Où en êtes-vous en français aujourd'hui ?
**Helper:** Ceci définit votre point de départ. Si vous hésitez, choisissez le niveau le plus proche — nous ajusterons à partir de vos premiers enregistrements.
**Options:**
- A2 — Je gère des conversations simples sur des sujets familiers
- B1 — Je peux décrire des expériences, des opinions, et suivre la plupart des échanges
- B2 — Je m'exprime avec aisance et peux discuter de la plupart des sujets avec confiance
- C1 — Je suis à l'aise dans presque toutes les situations mais je veux affiner
- Je ne sais pas

---

## Question 2 — Target level

**Type:** single_select
**Required:** yes
**Routing effect:** path slug (Q1 + Q2)

### EN

**Heading:** What level do you need to reach?
**Helper:** For most immigration and academic applications, B2 is the threshold. Pick the level required by your goal.
**Options:**
- B1 — Required for some work permits and basic certifications
- B2 — Required for Express Entry, most universities, professional credentials
- C1 — Required for advanced academic admission or specialized professions
- C2 — Native-equivalent mastery
- I don't know what level I need

### FR

**Heading:** Quel niveau devez-vous atteindre ?
**Helper:** Pour la plupart des demandes d'immigration et d'admission, B2 est le seuil. Choisissez le niveau requis par votre objectif.
**Options:**
- B1 — Requis pour certains permis de travail et certifications de base
- B2 — Requis pour Entrée Express, la plupart des universités, les titres professionnels
- C1 — Requis pour les admissions universitaires avancées ou certains métiers
- C2 — Maîtrise équivalente au natif
- Je ne sais pas quel niveau je dois atteindre

---

## Question 3 — Exam date

**Type:** date_input + "no exam scheduled" toggle
**Required:** yes (with no-exam option)
**Routing effect:** persona derivation (foundation / acceleration / cram)

### EN

**Heading:** When is your exam scheduled?
**Helper:** Your timeline shapes how we sequence your work. Pick a date or tell us no exam is scheduled.
**Input type:** Date picker (min: today, max: today + 18 months)
**Toggle option:** No exam scheduled — I'm preparing without a deadline

### FR

**Heading:** Quand est votre examen ?
**Helper:** Votre échéance détermine la cadence de votre préparation. Indiquez la date ou précisez qu'aucun examen n'est prévu.
**Input type:** Sélecteur de date (min : aujourd'hui, max : aujourd'hui + 18 mois)
**Toggle option:** Aucun examen prévu — je me prépare sans échéance

**Persona derivation logic** (note for BE):
- exam_date ≤ 6 weeks from today → persona = `cram`
- exam_date 6 weeks to 6 months → persona = `acceleration`
- exam_date > 6 months OR no exam scheduled → persona = `foundation`

---

## Question 4 — Why learning (motivation)

**Type:** single_select
**Required:** no (optional, "Prefer not to say" available)
**Routing effect:** captured for P-220.x routing (vocabulary theme priorities)

### EN

**Heading:** What's driving this?
**Helper:** Your reason shapes which topics we prioritize. We won't share this — it's just for tailoring your work.
**Options:**
- Immigration to Canada or another francophone country
- Professional credential or job requirement
- University admission or studies
- Personal interest or family connection
- Other / Prefer not to say

### FR

**Heading:** Qu'est-ce qui vous motive ?
**Helper:** Votre raison oriente les sujets que nous priorisons. Cette information reste confidentielle — elle sert uniquement à personnaliser votre préparation.
**Options:**
- Immigration au Canada ou dans un pays francophone
- Titre professionnel ou exigence d'emploi
- Admission universitaire ou études
- Intérêt personnel ou attaches familiales
- Autre / Préfère ne pas répondre

---

## Question 5 — Strongest skill

**Type:** single_select
**Required:** no
**Routing effect:** captured for P-220.x routing (diagnostic emphasis)

### EN

**Heading:** Which skill feels most solid?
**Helper:** Honest answers help us calibrate the diagnostic. There's no wrong choice.
**Options:**
- Speaking — I can hold conversations
- Listening — I understand more than I can say
- Reading — I read better than I write or speak
- Writing — I write more comfortably than I speak
- They all feel equally weak

### FR

**Heading:** Quelle compétence vous semble la plus solide ?
**Helper:** Vos réponses honnêtes aident à calibrer le diagnostic. Il n'y a pas de mauvaise réponse.
**Options:**
- Parler — je peux soutenir une conversation
- Écouter — je comprends plus que je ne peux dire
- Lire — je lis mieux que je n'écris ou ne parle
- Écrire — j'écris plus facilement que je ne parle
- Toutes me semblent également faibles

---

## Question 6 — Weakest skill

**Type:** single_select
**Required:** no
**Routing effect:** captured for P-220.x routing (cluster prioritization)

### EN

**Heading:** Which skill blocks you most?
**Helper:** This is the area where you feel stuck — the one you'd most want to fix.
**Options:**
- Speaking under pressure (exam-style or live conversation)
- Understanding fast or accented French
- Reading complex texts (articles, regulations, academic content)
- Writing structured arguments or essays
- Grammar accuracy across all skills
- Vocabulary depth

### FR

**Heading:** Quelle compétence vous bloque le plus ?
**Helper:** C'est le domaine où vous vous sentez coincé — celui que vous aimeriez le plus améliorer.
**Options:**
- Parler sous pression (en examen ou en direct)
- Comprendre un français rapide ou accentué
- Lire des textes complexes (articles, règlements, contenu académique)
- Rédiger des arguments structurés ou des essais
- L'exactitude grammaticale dans toutes les compétences
- La profondeur du vocabulaire

---

## Question 7 — Hours per week available

**Type:** single_select
**Required:** yes
**Routing effect:** capacity warning vs Q3 exam date

### EN

**Heading:** Realistically, how many hours per week can you commit?
**Helper:** Be honest — under-promising is better than over-promising. We'll plan around your real availability.
**Options:**
- Less than 2 hours per week
- 2 to 5 hours per week
- 5 to 10 hours per week
- More than 10 hours per week

### FR

**Heading:** Réalistement, combien d'heures par semaine pouvez-vous y consacrer ?
**Helper:** Soyez honnête — il vaut mieux sous-estimer que surestimer. Nous planifierons selon votre disponibilité réelle.
**Options:**
- Moins de 2 heures par semaine
- De 2 à 5 heures par semaine
- De 5 à 10 heures par semaine
- Plus de 10 heures par semaine

---

## Question 8 — Topics tested on

**Type:** multi_select (min 0, max 8)
**Required:** no (skip if no exam scheduled)
**Routing effect:** captured for P-220.x routing (cluster prioritization)
**Skip condition:** if Q3 = "no exam scheduled", skip Q8 entirely

### EN

**Heading:** Which topics does your exam cover?
**Helper:** Most exams test these eight standard themes. Pick all that apply, or skip if you're not sure.
**Options:**
- Daily life and practical situations
- Society and social issues
- Education and academic life
- Work and professional life
- Leisure and travel
- Health and well-being
- Environment and sustainability
- Culture and media

### FR

**Heading:** Quels sujets votre examen couvre-t-il ?
**Helper:** La plupart des examens testent ces huit thèmes standards. Cochez tous ceux qui s'appliquent, ou passez si vous n'êtes pas sûr.
**Options:**
- Vie quotidienne et situations pratiques
- Société et questions sociales
- Éducation et vie scolaire
- Travail et vie professionnelle
- Loisirs et voyages
- Santé et bien-être
- Environnement et développement durable
- Culture et médias

**Slug mapping** (note for BE):
- `vie_quotidienne`, `societe`, `education`, `travail`, `loisirs_voyages`, `sante`, `environnement`, `culture_medias`

---

## Question 9 — Native language

**Type:** single_select with "Other" → text input
**Required:** yes
**Routing effect:** captured for future detector calibration (no-op Phase 1)

### EN

**Heading:** What's your first language?
**Helper:** Different language backgrounds carry different patterns of error in French. Knowing yours helps us calibrate feedback over time.
**Options:**
- English
- Arabic
- Spanish
- Portuguese
- Mandarin / Chinese
- Hindi / Urdu
- Russian
- German
- Italian
- Other (please specify)

### FR

**Heading:** Quelle est votre langue maternelle ?
**Helper:** Différentes langues d'origine entraînent différents schémas d'erreur en français. Connaître la vôtre nous aide à calibrer le feedback au fil du temps.
**Options:**
- Anglais
- Arabe
- Espagnol
- Portugais
- Mandarin / Chinois
- Hindi / Ourdou
- Russe
- Allemand
- Italien
- Autre (préciser)

---

## Question 10 — Prior French exam history

**Type:** single_select
**Required:** yes
**Routing effect:** captured for P-220.x routing (credibility-of-self-assessment signal)

### EN

**Heading:** Have you taken a French exam before?
**Helper:** A recent exam result is a strong signal we can use to calibrate. Older results are still useful context.
**Options:**
- Never taken a French exam
- Yes, in the last 6 months
- Yes, in the last 12 months
- Yes, but more than a year ago

### FR

**Heading:** Avez-vous déjà passé un examen de français ?
**Helper:** Un résultat récent est un signal fort que nous pouvons utiliser pour la calibration. Les résultats plus anciens restent utiles comme contexte.
**Options:**
- Jamais passé d'examen de français
- Oui, dans les 6 derniers mois
- Oui, dans les 12 derniers mois
- Oui, mais il y a plus d'un an

---

## Question 11 — Feedback mode preference

**Type:** single_select
**Required:** yes
**Routing effect:** sets `feedback_mode_preference` column → drives default UI mode (calm vs method)

### EN

**Heading:** How much detail do you want in your feedback?
**Helper:** You can change this anytime in your settings.
**Options:**
- **Just the essentials.** Show me the one or two things to fix today, with clear next steps.
- **Full detail.** Show me everything — every error pattern, every diagnostic marker, every metric.

### FR

**Heading:** Quel niveau de détail souhaitez-vous dans le feedback ?
**Helper:** Vous pouvez modifier cela à tout moment dans vos paramètres.
**Options:**
- **L'essentiel seulement.** Montrez-moi la ou les deux choses à corriger aujourd'hui, avec les étapes suivantes claires.
- **Le détail complet.** Montrez-moi tout — chaque schéma d'erreur, chaque marqueur diagnostic, chaque métrique.

**Mode mapping** (note for BE):
- "Just the essentials" / "L'essentiel seulement" → `calm`
- "Full detail" / "Le détail complet" → `method`

---

## Final screen (after submit)

### EN

**Heading:** You're enrolled.
**Body:**
You're now on the **B1 → B2** path. Your first step is a 3-recording diagnostic so we can calibrate to your actual production — what you can do in real time, not what you know on paper.

The diagnostic takes about 12 minutes. You can do it now or come back to it later.

**Primary CTA:** Start the diagnostic
**Secondary CTA:** Save and finish later

### FR

**Heading:** Vous êtes inscrit.
**Body:**
Vous êtes maintenant sur le parcours **B1 → B2**. Votre première étape est un diagnostic en 3 enregistrements, pour que nous puissions calibrer selon votre production réelle — ce que vous savez faire en direct, pas ce que vous savez sur papier.

Le diagnostic prend environ 12 minutes. Vous pouvez le faire maintenant ou y revenir plus tard.

**Primary CTA:** Commencer le diagnostic
**Secondary CTA:** Sauvegarder et finir plus tard

---

## Waitlist screen (if Q1+Q2 don't resolve to b1_to_b2)

If a user selects A2 → B1, B2 → C1, or C1 → C2 (paths not built yet), they hit a waitlist screen instead of the diagnostic.

### EN

**Heading:** We're not ready for your level yet.
**Body:**
LeMethodic is currently focused on **B1 → B2** preparation. The path you need (**[user's selected start] → [user's selected target]**) is in development.

We'll email you the moment it launches. In the meantime, your account is saved and your responses are recorded.

**Primary CTA:** Add me to the waitlist
**Secondary CTA:** I'll try B1 → B2 instead (only if their start_level is B1 OR target_level is B2)

### FR

**Heading:** Nous ne sommes pas encore prêts pour votre niveau.
**Body:**
LeMethodic est actuellement concentré sur la préparation **B1 → B2**. Le parcours dont vous avez besoin (**[niveau de départ] → [niveau cible]**) est en développement.

Nous vous écrirons dès qu'il sera disponible. Entre-temps, votre compte est conservé et vos réponses enregistrées.

**Primary CTA:** Ajoutez-moi à la liste d'attente
**Secondary CTA:** Je vais essayer B1 → B2 à la place (uniquement si leur start_level est B1 OU target_level est B2)

---

## Capacity warning (if Q3 + Q7 mismatch)

Triggered when exam_date is < 6 weeks AND hours_per_week is "<2" or "2-5".

### EN

**Heading:** Your timeline is tight.
**Body:**
Your exam is in **[X weeks]** but you've indicated **[hours selected]**. To realistically cover the B1 → B2 path before your exam, we recommend at least **5 hours per week** of focused practice.

You can still proceed, but progress will be slower than the path is designed for.

**Primary CTA:** Adjust my hours
**Secondary CTA:** Continue anyway

### FR

**Heading:** Votre échéance est serrée.
**Body:**
Votre examen est dans **[X semaines]** mais vous avez indiqué **[heures sélectionnées]**. Pour couvrir réellement le parcours B1 → B2 avant votre examen, nous recommandons au moins **5 heures par semaine** de pratique ciblée.

Vous pouvez continuer, mais la progression sera plus lente que ce que le parcours prévoit.

**Primary CTA:** Ajuster mes heures
**Secondary CTA:** Continuer quand même

---

## Authoring notes (for Chadi review)

1. **Voice tested against the SaaS-onboarding smell test.** No "journey," no "let's," no exclamation points. Direct, factual, slightly clinical — matches LeMethodic's positioning as a tool, not a hype product.

2. **Q4 (motivation) is optional.** Many users will be uncomfortable answering "why are you doing this" up front, and forcing it lowers completion rates. Optional + "Prefer not to say" preserves the data we get from people who answer while not blocking the rest.

3. **Q5/Q6 are also optional.** The diagnostic itself reveals strengths and weaknesses; user self-report is supplementary signal, not primary data.

4. **Q8 conditional skip if no exam.** If Q3 says no exam scheduled, asking "what topics is your exam testing" makes no sense. Skip the question entirely.

5. **Q9 native language list of 10.** Selected based on global L1 distribution among likely Canadian PR applicants and TCF takers. "Other" with text input captures the rest. Phase 2 expansion (Italian audience per strategic plan) is already in the visible list — anticipates the eventual UX.

6. **Q11 framing.** This is the most important question for default UX. Two options instead of three (no middle ground). Bold first sentence makes it scannable. The decision between calm and method should feel like a real choice, not a no-brainer in either direction.

7. **Final screen is decision-shaped.** "You're enrolled" is past tense — the user has already made a commitment. The CTA is "start the diagnostic," not "next." Forces forward motion.

8. **Waitlist screen is honest, not euphemistic.** "We're not ready for your level" rather than "Your level is on our roadmap." Anglophone users have low tolerance for product-marketing-speak in onboarding flows.

9. **Capacity warning is non-blocking.** Surfacing the tension is helpful; blocking the user is patronizing. They get to decide.

10. **What's NOT here:**
    - Q12 reminder time (deferred per spec)
    - Email collection (handled at signup, not onboarding)
    - Pricing or paywall content (not part of onboarding scope)
    - Microcopy for error states (BE/FE handle 400/500 generic copy)

11. **What review should focus on:**
    - Does the FR copy feel native? I'm fluent enough to write it but you're the native authority.
    - Is the Q11 framing clear? "calm" vs "method" is internal terminology; the user-facing copy avoids those words but the underlying mode mapping is correct.
    - Are Q5 and Q6 different enough? "Strongest" and "weakest" are conceptually distinct but framed similarly — a user might fill them out symmetrically.
    - The "We're not ready for your level yet" waitlist copy could read as defensive. Alternative: "B1 → B2 is the only path we're shipping right now. Other levels are coming." Less apologetic.

---

## For BE — implementation pointers

### Question structure JSON (returned by GET /onboarding/questions)

Each question follows this shape:
```json
{
  "id": "q1_current_level",
  "order": 1,
  "type": "single_select",
  "required": true,
  "skip_condition": null,
  "heading": {"en": "...", "fr": "..."},
  "helper": {"en": "...", "fr": "..."},
  "options": [
    {
      "value": "a2",
      "label": {"en": "A2 — I can handle...", "fr": "A2 — Je gère..."}
    }
  ]
}
```

Note: heading, helper, and option labels are i18n JSONB-style {fr, en} objects. Frontend reads the user's `ui_language` preference and renders the matching string.

### Question ID slugs (for stable references in DB and code)

1. `q1_current_level`
2. `q2_target_level`
3. `q3_exam_date`
4. `q4_motivation`
5. `q5_strongest_skill`
6. `q6_weakest_skill`
7. `q7_hours_per_week`
8. `q8_topics_tested_on`
9. `q9_native_language`
10. `q10_prior_exam_history`
11. `q11_feedback_mode`

### Submission payload (POST /onboarding/submit body)

```json
{
  "q1_current_level": "b1",
  "q2_target_level": "b2",
  "q3_exam_date": "2026-08-15",
  "q3_no_exam_scheduled": false,
  "q4_motivation": "immigration",
  "q5_strongest_skill": "reading",
  "q6_weakest_skill": "speaking_under_pressure",
  "q7_hours_per_week": "5_to_10",
  "q8_topics_tested_on": ["vie_quotidienne", "societe", "travail"],
  "q9_native_language": "english",
  "q9_native_language_other": null,
  "q10_prior_exam_history": "never",
  "q11_feedback_mode": "calm"
}
```

### Response payload

```json
{
  "path_slug": "b1_to_b2",
  "persona": "acceleration",
  "redirect_to_diagnostic": true,
  "waitlist": false,
  "capacity_warning": null,
  "user_path_enrollment_id": 42
}
```

If waitlist applies:
```json
{
  "path_slug": null,
  "persona": null,
  "redirect_to_diagnostic": false,
  "waitlist": true,
  "waitlist_reason": "path_not_active",
  "fallback_path_offered": "b1_to_b2",
  "user_path_enrollment_id": null
}
```

If capacity warning fires:
```json
{
  "path_slug": "b1_to_b2",
  "persona": "cram",
  "redirect_to_diagnostic": true,
  "waitlist": false,
  "capacity_warning": {
    "weeks_to_exam": 4,
    "hours_per_week_selected": "less_than_2",
    "recommended_minimum_hours": "5_to_10"
  },
  "user_path_enrollment_id": 43
}
```
