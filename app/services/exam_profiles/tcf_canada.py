"""
TCF Canada exam profile — France Éducation International's five-criterion
framework, used by IRCC for Canadian immigration points.
"""
from app.services.scoring_maps import cefr_from_score, clb_from_cefr
from app.services.exam_profiles.base import Criterion, ExamProfile


_TASK_RESPONSE = Criterion(
    key="task_response",
    label_fr_technical="Adéquation à la tâche",
    label_fr_student="Adéquation à la tâche",
    label_en_student="Task response",
    label_es_student="Respuesta a la tarea",
    prompt_guidance=(
        "Le candidat répond-il précisément à la question ? Reste-t-il dans le "
        "sujet ? Développe-t-il une position argumentée avec une longueur "
        "adaptée ? Les examinateurs pénalisent le hors-sujet, la paraphrase "
        "de la consigne sans développement, et les réponses trop courtes."
    ),
)

_LEXICAL_RANGE = Criterion(
    key="lexical_range",
    label_fr_technical="Étendue lexicale",
    label_fr_student="Vocabulaire",
    label_en_student="Vocabulary",
    label_es_student="Vocabulario",
    prompt_guidance=(
        "Variété et précision du vocabulaire. Mots justes vs. approximations. "
        "Collocations naturelles. Registre adapté à la situation. Les "
        "examinateurs récompensent la richesse et la précision, pénalisent "
        "les répétitions et les mots approximatifs."
    ),
)

_GRAMMATICAL_RANGE = Criterion(
    key="grammatical_range",
    label_fr_technical="Étendue grammaticale",
    label_fr_student="Grammaire",
    label_en_student="Grammar",
    label_es_student="Gramática",
    prompt_guidance=(
        "Variété des structures (subordonnées, temps, modes, voix). "
        "Complexité syntaxique appropriée au niveau. Erreurs qui gênent la "
        "compréhension vs. erreurs mineures. Les examinateurs notent la "
        "palette grammaticale autant que la correction."
    ),
)

_PHONOLOGICAL_CONTROL = Criterion(
    key="phonological_control",
    label_fr_technical="Contrôle phonologique",
    label_fr_student="Prononciation",
    label_en_student="Pronunciation",
    label_es_student="Pronunciación",
    prompt_guidance=(
        "Prononciation intelligible. Liaisons obligatoires respectées. Rythme "
        "et intonation françaises. Un accent étranger est toléré tant qu'il "
        "n'entrave pas la compréhension. Les examinateurs pénalisent les "
        "sons qui changent le sens (e.g. u/ou, é/è) et l'absence de liaisons."
    ),
)

_SPELLING_PUNCTUATION = Criterion(
    key="spelling_punctuation",
    label_fr_technical="Orthographe et ponctuation",
    label_fr_student="Orthographe et ponctuation",
    label_en_student="Spelling and punctuation",
    label_es_student="Ortografía y puntuación",
    prompt_guidance=(
        "Orthographe lexicale et grammaticale (accords, terminaisons verbales). "
        "Ponctuation qui structure le propos (virgules, points-virgules, "
        "deux-points). Les examinateurs tolèrent quelques coquilles mais "
        "pénalisent les erreurs systématiques d'accord et la ponctuation "
        "absente ou aberrante."
    ),
)

_COHERENCE_COHESION = Criterion(
    key="coherence_cohesion",
    label_fr_technical="Cohérence et cohésion",
    label_fr_student="Cohérence",
    label_en_student="Coherence",
    label_es_student="Coherencia",
    prompt_guidance=(
        "Organisation du propos : introduction, développement, conclusion. "
        "Connecteurs logiques (cependant, en effet, par conséquent...). "
        "Progression claire. Absence de ruptures, de répétitions parasites et "
        "de contradictions internes."
    ),
)


_TCF_EXAMINER_GUIDE = """Voix d'un correcteur agréé de France Éducation
International. Registre propre au TCF Canada :
  - « Lexique varié mais parfois imprécis »
  - « Progression claire » / « quelques ruptures de cohérence »
  - « Registre adapté à la situation »
  - « Éventail grammatical maîtrisé / restreint / limité »
  - « Manque de profondeur dans le développement »
  - « Niveau B2 atteint » / « partiellement atteint » / « non atteint »
Mentionne le niveau CEFR visé par rapport au niveau observé lorsque c'est
pertinent (« attendu au niveau B2 : ... »). Pas d'encouragements, pas de
louanges — évaluation pure, 1-2 phrases en français."""


_SYSTEM_PROMPT_PREAMBLE = """═══════════════════════════════════════════════════════════
ÉVALUATION OFFICIELLE — TCF CANADA
═══════════════════════════════════════════════════════════
En parallèle du diagnostic « Méthode en Couches », attribue un score officiel
selon les cinq critères utilisés par les examinateurs de France Éducation
International pour le TCF Canada. Chaque critère est noté de 0 à 20 indépendamment.

CRITÈRES (ordre fixe, ne pas réordonner) :

{criteria_block}

BARÈME (identique pour chaque critère) :
  0-1   = A1 non atteint / A1
  2-5   = A2
  6-9   = B1
  10-13 = B2
  14-17 = C1
  18-20 = C2

Le score global = moyenne arithmétique des cinq critères, arrondie à 1 décimale.
Ne calcule PAS le niveau CEFR ni CLB — le serveur les dérive du score.

Pour chaque critère, le feedback doit être BREF (1-2 phrases) et BILINGUE :
français suivi de "|||" puis {ui_language_name}. Cite un moment spécifique de
la production et indique ce qui a fait gagner ou perdre des points. Pas de
généralités."""


TCF_CANADA = ExamProfile(
    id="tcf_canada",
    display_name="TCF Canada",
    frameworks_shown=("raw20", "cefr", "clb"),
    criteria_oral=(
        _TASK_RESPONSE,
        _LEXICAL_RANGE,
        _GRAMMATICAL_RANGE,
        _PHONOLOGICAL_CONTROL,
        _COHERENCE_COHESION,
    ),
    criteria_writing=(
        _TASK_RESPONSE,
        _LEXICAL_RANGE,
        _GRAMMATICAL_RANGE,
        _SPELLING_PUNCTUATION,
        _COHERENCE_COHESION,
    ),
    score_to_cefr=cefr_from_score,
    cefr_to_secondary=clb_from_cefr,
    secondary_framework_label="CLB",
    system_prompt_preamble=_SYSTEM_PROMPT_PREAMBLE,
    examiner_voice_guide=_TCF_EXAMINER_GUIDE,
)
