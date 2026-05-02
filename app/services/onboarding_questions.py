"""P-220 — onboarding questionnaire content (FR + EN copy).

Source of truth: docs/P-220-onboarding-questionnaire-copy.md. When the
copy doc is revised, update this file in lockstep — the doc is the
human-authored source, this module is the FE-rendered canonical form.

Each entry maps to one question slug (q1_current_level .. q11_feedback_mode)
and yields an OnboardingQuestion when wrapped by build_questions().
"""
from __future__ import annotations

from typing import List

from app.schemas.onboarding import (
    I18n,
    OnboardingQuestion,
    OnboardingQuestionOption,
)


def _opt(value: str, en: str, fr: str) -> OnboardingQuestionOption:
    return OnboardingQuestionOption(value=value, label=I18n(en=en, fr=fr))


def build_questions() -> List[OnboardingQuestion]:
    """Return the 11 questions in canonical order. Pure (no I/O)."""
    return [
        # ── Q1 — Current French level ────────────────────────────
        OnboardingQuestion(
            id="q1_current_level",
            order=1,
            type="single_select",
            required=True,
            heading=I18n(
                en="Where are you with French right now?",
                fr="Où en êtes-vous en français aujourd'hui ?",
            ),
            helper=I18n(
                en="This sets your starting point. If you're not sure, that's fine — "
                "pick the closest match and we'll calibrate from your first recordings.",
                fr="Ceci définit votre point de départ. Si vous hésitez, choisissez "
                "le niveau le plus proche — nous ajusterons à partir de vos premiers "
                "enregistrements.",
            ),
            options=[
                _opt("a2",
                     "A2 — I can handle short, simple conversations on familiar topics",
                     "A2 — Je gère des conversations simples sur des sujets familiers"),
                _opt("b1",
                     "B1 — I can describe experiences, opinions, and follow most slow conversations",
                     "B1 — Je peux décrire des expériences, des opinions, et suivre la plupart des échanges"),
                _opt("b2",
                     "B2 — I can express myself fluently and discuss most topics with confidence",
                     "B2 — Je m'exprime avec aisance et peux discuter de la plupart des sujets avec confiance"),
                _opt("c1",
                     "C1 — I'm comfortable in nearly any situation but want to refine",
                     "C1 — Je suis à l'aise dans presque toutes les situations mais je veux affiner"),
                _opt("not_sure", "Not sure", "Je ne sais pas"),
            ],
        ),

        # ── Q2 — Target level ─────────────────────────────────────
        OnboardingQuestion(
            id="q2_target_level",
            order=2,
            type="single_select",
            required=True,
            heading=I18n(
                en="What level do you need to reach?",
                fr="Quel niveau devez-vous atteindre ?",
            ),
            helper=I18n(
                en="For most immigration and academic applications, B2 is the threshold. "
                "Pick the level required by your goal.",
                fr="Pour la plupart des demandes d'immigration et d'admission, B2 est "
                "le seuil. Choisissez le niveau requis par votre objectif.",
            ),
            options=[
                _opt("b1",
                     "B1 — Required for some work permits and basic certifications",
                     "B1 — Requis pour certains permis de travail et certifications de base"),
                _opt("b2",
                     "B2 — Required for Express Entry, most universities, professional credentials",
                     "B2 — Requis pour Entrée Express, la plupart des universités, les titres professionnels"),
                _opt("c1",
                     "C1 — Required for advanced academic admission or specialized professions",
                     "C1 — Requis pour les admissions universitaires avancées ou certains métiers"),
                _opt("c2",
                     "C2 — Native-equivalent mastery",
                     "C2 — Maîtrise équivalente au natif"),
                _opt("not_sure",
                     "I don't know what level I need",
                     "Je ne sais pas quel niveau je dois atteindre"),
            ],
        ),

        # ── Q3 — Exam date ────────────────────────────────────────
        OnboardingQuestion(
            id="q3_exam_date",
            order=3,
            type="date_input",
            required=True,
            heading=I18n(
                en="When is your exam scheduled?",
                fr="Quand est votre examen ?",
            ),
            helper=I18n(
                en="Your timeline shapes how we sequence your work. Pick a date or "
                "tell us no exam is scheduled.",
                fr="Votre échéance détermine la cadence de votre préparation. "
                "Indiquez la date ou précisez qu'aucun examen n'est prévu.",
            ),
            # FE date picker constraints + the no-exam toggle live in the FE.
            # No options here — type=date_input — but we surface the toggle copy
            # via skip_condition so the FE can render it consistently.
            skip_condition={
                "no_exam_toggle_label": {
                    "en": "No exam scheduled — I'm preparing without a deadline",
                    "fr": "Aucun examen prévu — je me prépare sans échéance",
                },
                "min_offset_days": 0,
                "max_offset_days": 540,   # ~18 months
            },
            options=None,
        ),

        # ── Q4 — Motivation ───────────────────────────────────────
        OnboardingQuestion(
            id="q4_motivation",
            order=4,
            type="single_select",
            required=False,
            heading=I18n(
                en="What's driving this?",
                fr="Qu'est-ce qui vous motive ?",
            ),
            helper=I18n(
                en="Your reason shapes which topics we prioritize. We won't share "
                "this — it's just for tailoring your work.",
                fr="Votre raison oriente les sujets que nous priorisons. Cette "
                "information reste confidentielle — elle sert uniquement à personnaliser "
                "votre préparation.",
            ),
            options=[
                _opt("immigration",
                     "Immigration to Canada or another francophone country",
                     "Immigration au Canada ou dans un pays francophone"),
                _opt("professional",
                     "Professional credential or job requirement",
                     "Titre professionnel ou exigence d'emploi"),
                _opt("studies",
                     "University admission or studies",
                     "Admission universitaire ou études"),
                _opt("personal",
                     "Personal interest or family connection",
                     "Intérêt personnel ou attaches familiales"),
                _opt("prefer_not_to_say",
                     "Other / Prefer not to say",
                     "Autre / Préfère ne pas répondre"),
            ],
        ),

        # ── Q5 — Strongest skill ──────────────────────────────────
        OnboardingQuestion(
            id="q5_strongest_skill",
            order=5,
            type="single_select",
            required=False,
            heading=I18n(
                en="Which skill feels most solid?",
                fr="Quelle compétence vous semble la plus solide ?",
            ),
            helper=I18n(
                en="Honest answers help us calibrate the diagnostic. There's no wrong choice.",
                fr="Vos réponses honnêtes aident à calibrer le diagnostic. Il n'y a "
                "pas de mauvaise réponse.",
            ),
            options=[
                _opt("speaking",
                     "Speaking — I can hold conversations",
                     "Parler — je peux soutenir une conversation"),
                _opt("listening",
                     "Listening — I understand more than I can say",
                     "Écouter — je comprends plus que je ne peux dire"),
                _opt("reading",
                     "Reading — I read better than I write or speak",
                     "Lire — je lis mieux que je n'écris ou ne parle"),
                _opt("writing",
                     "Writing — I write more comfortably than I speak",
                     "Écrire — j'écris plus facilement que je ne parle"),
                _opt("all_equally_weak",
                     "They all feel equally weak",
                     "Toutes me semblent également faibles"),
            ],
        ),

        # ── Q6 — Weakest skill (blocker types) ────────────────────
        OnboardingQuestion(
            id="q6_weakest_skill",
            order=6,
            type="single_select",
            required=False,
            heading=I18n(
                en="Which skill blocks you most?",
                fr="Quelle compétence vous bloque le plus ?",
            ),
            helper=I18n(
                en="This is the area where you feel stuck — the one you'd most want to fix.",
                fr="C'est le domaine où vous vous sentez coincé — celui que vous "
                "aimeriez le plus améliorer.",
            ),
            options=[
                _opt("speaking_under_pressure",
                     "Speaking under pressure (exam-style or live conversation)",
                     "Parler sous pression (en examen ou en direct)"),
                _opt("listening_fast",
                     "Understanding fast or accented French",
                     "Comprendre un français rapide ou accentué"),
                _opt("reading_complex",
                     "Reading complex texts (articles, regulations, academic content)",
                     "Lire des textes complexes (articles, règlements, contenu académique)"),
                _opt("writing_essays",
                     "Writing structured arguments or essays",
                     "Rédiger des arguments structurés ou des essais"),
                _opt("grammar_accuracy",
                     "Grammar accuracy across all skills",
                     "L'exactitude grammaticale dans toutes les compétences"),
                _opt("vocabulary_depth",
                     "Vocabulary depth",
                     "La profondeur du vocabulaire"),
            ],
        ),

        # ── Q7 — Hours per week ───────────────────────────────────
        OnboardingQuestion(
            id="q7_hours_per_week",
            order=7,
            type="single_select",
            required=True,
            heading=I18n(
                en="Realistically, how many hours per week can you commit?",
                fr="Réalistement, combien d'heures par semaine pouvez-vous y consacrer ?",
            ),
            helper=I18n(
                en="Be honest — under-promising is better than over-promising. "
                "We'll plan around your real availability.",
                fr="Soyez honnête — il vaut mieux sous-estimer que surestimer. "
                "Nous planifierons selon votre disponibilité réelle.",
            ),
            options=[
                _opt("less_than_2",
                     "Less than 2 hours per week",
                     "Moins de 2 heures par semaine"),
                _opt("2_to_5",
                     "2 to 5 hours per week",
                     "De 2 à 5 heures par semaine"),
                _opt("5_to_10",
                     "5 to 10 hours per week",
                     "De 5 à 10 heures par semaine"),
                _opt("more_than_10",
                     "More than 10 hours per week",
                     "Plus de 10 heures par semaine"),
            ],
        ),

        # ── Q8 — Topics tested on (multi-select) ──────────────────
        OnboardingQuestion(
            id="q8_topics_tested_on",
            order=8,
            type="multi_select",
            required=False,
            skip_condition={"skip_when": "q3_no_exam_scheduled"},
            heading=I18n(
                en="Which topics does your exam cover?",
                fr="Quels sujets votre examen couvre-t-il ?",
            ),
            helper=I18n(
                en="Most exams test these eight standard themes. Pick all that apply, "
                "or skip if you're not sure.",
                fr="La plupart des examens testent ces huit thèmes standards. Cochez "
                "tous ceux qui s'appliquent, ou passez si vous n'êtes pas sûr.",
            ),
            options=[
                _opt("vie_quotidienne",
                     "Daily life and practical situations",
                     "Vie quotidienne et situations pratiques"),
                _opt("societe",
                     "Society and social issues",
                     "Société et questions sociales"),
                _opt("education",
                     "Education and academic life",
                     "Éducation et vie scolaire"),
                _opt("travail",
                     "Work and professional life",
                     "Travail et vie professionnelle"),
                _opt("loisirs_voyages",
                     "Leisure and travel",
                     "Loisirs et voyages"),
                _opt("sante",
                     "Health and well-being",
                     "Santé et bien-être"),
                _opt("environnement",
                     "Environment and sustainability",
                     "Environnement et développement durable"),
                _opt("culture_medias",
                     "Culture and media",
                     "Culture et médias"),
            ],
        ),

        # ── Q9 — Native language (with "Other" free-text) ─────────
        OnboardingQuestion(
            id="q9_native_language",
            order=9,
            type="single_select",
            required=True,
            skip_condition={"other_freetext_field": "q9_native_language_other"},
            heading=I18n(
                en="What's your first language?",
                fr="Quelle est votre langue maternelle ?",
            ),
            helper=I18n(
                en="Different language backgrounds carry different patterns of error "
                "in French. Knowing yours helps us calibrate feedback over time.",
                fr="Différentes langues d'origine entraînent différents schémas "
                "d'erreur en français. Connaître la vôtre nous aide à calibrer le "
                "feedback au fil du temps.",
            ),
            options=[
                _opt("english", "English", "Anglais"),
                _opt("arabic", "Arabic", "Arabe"),
                _opt("spanish", "Spanish", "Espagnol"),
                _opt("portuguese", "Portuguese", "Portugais"),
                _opt("mandarin", "Mandarin / Chinese", "Mandarin / Chinois"),
                _opt("hindi", "Hindi / Urdu", "Hindi / Ourdou"),
                _opt("russian", "Russian", "Russe"),
                _opt("german", "German", "Allemand"),
                _opt("italian", "Italian", "Italien"),
                _opt("other", "Other (please specify)", "Autre (préciser)"),
            ],
        ),

        # ── Q10 — Prior French exam history ───────────────────────
        OnboardingQuestion(
            id="q10_prior_exam_history",
            order=10,
            type="single_select",
            required=True,
            heading=I18n(
                en="Have you taken a French exam before?",
                fr="Avez-vous déjà passé un examen de français ?",
            ),
            helper=I18n(
                en="A recent exam result is a strong signal we can use to calibrate. "
                "Older results are still useful context.",
                fr="Un résultat récent est un signal fort que nous pouvons utiliser "
                "pour la calibration. Les résultats plus anciens restent utiles "
                "comme contexte.",
            ),
            options=[
                _opt("never",
                     "Never taken a French exam",
                     "Jamais passé d'examen de français"),
                _opt("recent_6mo",
                     "Yes, in the last 6 months",
                     "Oui, dans les 6 derniers mois"),
                _opt("recent_12mo",
                     "Yes, in the last 12 months",
                     "Oui, dans les 12 derniers mois"),
                _opt("older",
                     "Yes, but more than a year ago",
                     "Oui, mais il y a plus d'un an"),
            ],
        ),

        # ── Q11 — Feedback mode preference ────────────────────────
        OnboardingQuestion(
            id="q11_feedback_mode",
            order=11,
            type="single_select",
            required=True,
            heading=I18n(
                en="How much detail do you want in your feedback?",
                fr="Quel niveau de détail souhaitez-vous dans le feedback ?",
            ),
            helper=I18n(
                en="You can change this anytime in your settings.",
                fr="Vous pouvez modifier cela à tout moment dans vos paramètres.",
            ),
            options=[
                _opt("calm",
                     "Just the essentials. Show me the one or two things to fix today, "
                     "with clear next steps.",
                     "L'essentiel seulement. Montrez-moi la ou les deux choses à "
                     "corriger aujourd'hui, avec les étapes suivantes claires."),
                _opt("method",
                     "Full detail. Show me everything — every error pattern, every "
                     "diagnostic marker, every metric.",
                     "Le détail complet. Montrez-moi tout — chaque schéma d'erreur, "
                     "chaque marqueur diagnostic, chaque métrique."),
            ],
        ),
    ]
