import json
import httpx
from app.config import settings
from app.services.exam_profiles import ExamProfile, get_profile

# ═══════════════════════════════════════════════════════════════════════════════
#  FluentPath — La Méthode en Couches Diagnostic Engine v3.0
#  Framework propriétaire par Chadi Bakhay
#
#  4 Couches + Prononciation :
#    1. Le Fond           — Arguments, pertinence, exemples
#    2. Les Moules des Idées  — Architecture rhétorique du discours
#    3. Les Moules            — Architecture de la phrase
#    4. Les Réflexes Anglais  — Interférences anglais→français
#    +  Prononciation         — Mots mal prononcés détectés par STT
#
#  Output :
#    Le Diagnostic  — bilingual (FR + user language)
#    L'Ordonnance   — targeted exercises
#    Transcription corrigée — full corrected version
# ═══════════════════════════════════════════════════════════════════════════════

LANGUAGE_NAMES = {
    "en": "anglais",
    "fr": "français",
    "es": "espagnol",
}


# ═══════════════════════════════════════════════════════════════
# DUAL-CHANNEL FEEDBACK BLOCK (F-032)
# Spliced into SYSTEM_PROMPT_DIAGNOSTIC between the exam-profile preamble
# and the JSON response contract. Placeholders {examiner_voice_guide} /
# {teacher_voice_guide} are filled from the active ExamProfile.
# ═══════════════════════════════════════════════════════════════

DUAL_CHANNEL_BLOCK = """═══════════════════════════════════════════════════════════
DUAL-CHANNEL FEEDBACK — LES DEUX VOIX
═══════════════════════════════════════════════════════════
Pour chaque critère et pour la grille d'analyse, tu produis DEUX VOIX
DISTINCTES. Ne les mélange jamais. Elles ont des buts, des registres et
des destinataires différents.

▸ VOIX EXAMINATEUR (examiner_remark_fr)
  - Français UNIQUEMENT. Jamais de traduction, jamais de "|||".
  - Registre neutre-autoritaire d'un correcteur officiel.
  - 1 à 2 phrases maximum. Pure évaluation, aucun coaching.
  - Ne cite PAS le texte de l'étudiant. Ne propose PAS de transformation.

{examiner_voice_guide}

▸ VOIX PROFESSEUR (teacher_coaching)
  - coaching_en : TOUJOURS en anglais, quel que soit {ui_language_name}.
  - coaching_fr : TOUJOURS un exemple en français (matériel d'apprentissage pour
    l'étudiant, pas une traduction de coaching_en).
  - transformation : dans la langue de l'interface étudiant ({ui_language_name}).
    C'est l'action que l'étudiant doit exécuter ; il doit la comprendre.
  - Registre chaleureux, spécifique, coaching.
  - DOIT citer les mots EXACTS de l'étudiant (pas de paraphrase).
  - DOIT terminer sur une transformation concrète à appliquer au prochain essai.

{teacher_voice_guide}

EXEMPLES (montrent la différence tonale — à respecter strictement) :

Exemple 1 — critère grammatical_range, étudiant B2 :
  examiner_remark_fr : "Éventail grammatical limité. Usage correct du
    présent et du passé composé, mais absence de subordonnées complexes
    et recours systématique à la parataxe. Niveau B2 partiellement atteint."
  teacher_coaching :
    coaching_en : "You said 'Je pense la technologie est importante'
      three times — same flat pattern every time. In French you want to
      vary how you start opinion sentences, especially at B2 level."
    coaching_fr : "Au lieu de 'Je pense que...', essaie : 'Il me semble
      que...', 'Force est de constater que...', 'On peut soutenir que...'."
    transformation : "Prochain enregistrement : utilise au moins deux
      tournures d'opinion différentes."

Exemple 2 — critère lexical_range, étudiant B2 :
  examiner_remark_fr : "Lexique usuel correctement maîtrisé mais peu varié.
    Répétition de 'chose' et 'truc' là où un vocabulaire plus précis
    serait attendu au niveau B2."
  teacher_coaching :
    coaching_en : "You used 'chose' seven times and 'truc' four times.
      These are fine in casual speech but an examiner hears them as
      vocabulary you're missing."
    coaching_fr : "Remplace 'une chose importante' par 'un aspect important',
      'un enjeu', 'un élément clé'. Remplace 'ce truc' par 'ce phénomène',
      'cette pratique', 'cette question'."
    transformation : "Bannis 'chose' et 'truc' du prochain enregistrement."

═══════════════════════════════════════════════════════════
GRILLE D'ANALYSE — 4 DIMENSIONS (analyse_par_couche)
═══════════════════════════════════════════════════════════
Produis quatre observations distinctes sur la production, non redondantes
avec les critères. Chaque cellule = 2-4 phrases en français.

  what_works          — Ce qui marche dans cette production. Cite des
                        passages précis. Renforcement positif ciblé.
  what_doesnt_work    — La faiblesse principale. Une seule, la plus
                        importante. Cite un moment spécifique.
  english_habits      — Réflexes anglais détectés (calques, prépositions
                        transférées, ordre des mots anglais, faux-amis).
                        Liste 1-3 exemples concrets tirés du discours.
  structure_quality   — Architecture des phrases et organisation de
                        l'argument. Phrases hachées ? Subordination ?
                        Connecteurs logiques ? Progression thèse-antithèse ?

next_step — UNE SEULE directive d'action pour le prochain enregistrement,
            rédigée dans la langue de l'interface étudiant ({ui_language_name}).
            Pas de liste. Phrase courte, impérative, concrète."""

# ═══════════════════════════════════════════════════════════════
# COUCHE 2 — LES MOULES DES IDÉES
# ═══════════════════════════════════════════════════════════════

LES_MOULES_DES_IDEES = """
COUCHE 2 — LES MOULES DES IDÉES
Patterns rhétoriques français que les anglophones ne produisent pas naturellement.

OUVERTURE :
- [B1+] cadrage_contextuel : L'anglophone saute directement à "I think..." → Le francophone contextualise d'abord : "Aujourd'hui, dans une société où..."
- [B2+] reformulation_sujet : Ne pas répéter la question mot pour mot → Reformuler avec ses propres mots
- [B2+] mise_en_perspective : Ancrer dans le temps : "Depuis une dizaine d'années..." / "Autrefois... mais aujourd'hui..."
- [C1+] problematisation : Transformer le sujet en PROBLÈME : "Cette question soulève un enjeu fondamental..."

ARGUMENTATION :
- [B1+] exemple_ancre : Pas de "some people..." vague → Concret : "Prenons l'exemple d'un étudiant qui..."
- [B2+] these_antithese : Pas de liste plate → Mouvement dialectique
- [B2+] concession_prealable : Pas de "I disagree because..." → "Certes, [vue opposée], mais [ma vue]"
- [B2+] reformulation_interne : Reformuler pour approfondir : "Autrement dit..." / "En d'autres termes..."
- [C1+] montee_en_generalite : Passer de l'anecdote au principe
- [C1+] question_rhetorique : Créer du rythme : "Mais est-ce vraiment le cas ?"
- [C1+] raisonnement_par_analogie : "C'est un peu comme..."

CONCESSION / NUANCE :
- [B2+] certes_mais : "Certes, [X], mais il n'en demeure pas moins que [Y]"
- [B2+] accord_partiel : "Je suis en partie d'accord dans la mesure où... Cependant..."
- [B2+] nuance_conditionnelle : "Cela dépend du contexte" / "À condition que..."
- [C1+] auto_nuance : "On pourrait me reprocher de... mais je maintiens que..."

CONCLUSION :
- [B1+] prise_de_position : "Pour ma part, je reste convaincu que..."
- [B2+] synthese : Synthétiser les deux côtés : "En définitive, cette question ne se résume pas à..."
- [B2+] ouverture_prospective : "Ce débat va certainement évoluer..."
- [C1+] echo_introduction : Boucler sur l'ouverture"""

# ═══════════════════════════════════════════════════════════════
# COUCHE 3 — LES MOULES
# ═══════════════════════════════════════════════════════════════

LES_MOULES = """
COUCHE 3 — LES MOULES (Architecture de la phrase)
Constructions qui distinguent "du français construit" de "de l'anglais traduit."

OPINION :
- [B1+] "Je pense que..." / "À mon avis..."
- [B2+] "Il me semble que..." / "J'estime que..." / "Force est de constater que..."
- [B2+] Distanciation : "On constate que..." / "Il est vrai que..."
- [C1+] Inversion : "Encore faut-il que..." / "Reste à savoir si..."

CAUSE :
- [B1+] "parce que" / "car"
- [B2+] "Étant donné que..." / "Du fait que..." / "Cela s'explique par..."
- [C1+] "... ce qui tient au fait que..." / "La raison en est que..."

CONSÉQUENCE :
- [B1+] "donc" / "alors"
- [B2+] "...ce qui entraîne..." / "Par conséquent,..." / "C'est la raison pour laquelle..."
- [C1+] "...d'où..." / "...de sorte que..." / "...si bien que..."

CONCESSION :
- [B1+] "mais"
- [B2+] "Certes..., mais..." / "Même si..., il n'en reste pas moins que..."
- [B2+] "D'un côté... de l'autre..."
- [C1+] "J'ai beau + infinitif..." / "Quand bien même..."

COMPARAISON :
- [B1+] "plus que / moins que"
- [B2+] "Contrairement à..." / "Alors que..., en revanche..."
- [C1+] "Autant... autant..."

EXEMPLE :
- [B1+] "Par exemple,..."
- [B2+] "Prenons l'exemple de..." / "Notamment..."
- [C1+] "En témoigne..." / "Cela se manifeste par..."

CONNECTEURS :
- [B1+] d'abord, ensuite, enfin, aussi, mais, parce que
- [B2+] néanmoins, en revanche, par conséquent, d'une part/d'autre part, en effet
- [C1+] en l'occurrence, à plus forte raison, quand bien même, force est de constater que"""

# ═══════════════════════════════════════════════════════════════
# COUCHE 4 — LES RÉFLEXES ANGLAIS
# ═══════════════════════════════════════════════════════════════

LES_REFLEXES_ANGLAIS = """
COUCHE 4 — LES RÉFLEXES ANGLAIS
Réflexes automatiques de l'anglophone. Signale-les quand tu les détectes.

FAUX-AMIS :
- realiser : "réaliser" pour "to realize" → se rendre compte
- actuellement : "actuellement" pour "actually" → en fait
- supporter : "supporter" pour "to support" → soutenir
- adresser : "adresser un problème" → traiter / aborder
- opportunite : "opportunité" pour "opportunity" → occasion

PRÉPOSITIONS :
- dependre_sur : "dépendre sur" → dépendre DE
- consister_de : "consister de" → consister À / EN
- interesse_dans : "intéressé dans" → intéressé PAR

CALQUES :
- passif_excessif : "il est considéré que" → on considère que
- important_pour : "c'est important pour les gens de..." → il est important que... (+ subjonctif)
- il_y_a_excessif : "il y a beaucoup de problèmes" → les problèmes sont nombreux
- make_someone : "faire quelqu'un faire" → amener/pousser quelqu'un à faire
- in_order_to : "dans l'ordre de" → afin de / pour

BOUCLES RÉPÉTITIVES (3+ occurrences) :
- boucle_je_pense → varier : il me semble / j'estime / à mon avis
- boucle_parce_que → car / en effet / puisque / étant donné que
- boucle_mais → cependant / néanmoins / toutefois / en revanche
- boucle_par_exemple → notamment / en particulier / c'est le cas de

ÉLÉMENTS MANQUANTS :
- ne_manquant : "je sais pas" → je NE sais pas
- article_manquant : "technologie est importante" → LA technologie

ORDRE DES MOTS (C1) :
- ordre_rigide : Toujours S-V-O → utiliser l'inversion : "Encore faut-il que..." """

# ═══════════════════════════════════════════════════════════════
# GRILLES D'ÉVALUATION
# ═══════════════════════════════════════════════════════════════

GRILLES = {
    "B1": """GRILLE B1 : Tolérance ÉLEVÉE.
COUCHE 1: 2-3 arguments basiques. Progression linéaire acceptée.
COUCHE 2: cadrage_contextuel, exemple_ancre, prise_de_position seulement.
COUCHE 3: Patterns [B1+] seulement. Connecteurs basiques. Erreurs tolérées.
COUCHE 4: Faux-amis majeurs et boucles évidentes uniquement.
SEUILS: 10-12/20 = attendu. 14+/20 = excellent.""",

    "B2": """GRILLE B2 : Tolérance MODÉRÉE.
COUCHE 1: 2-3 arguments développés. Exemples concrets. Concession attendue.
COUCHE 2: Tous [B1+] et [B2+]. Thèse-antithèse. Synthèse + ouverture.
COUCHE 3: Tous [B1+] et [B2+]. Variété de connecteurs exigée. Nominalisations.
COUCHE 4: Faux-amis, calques, boucles, "ne" manquant.
SEUILS: 12-14/20 = attendu. 16+/20 = excellent.""",

    "C1": """GRILLE C1 : Tolérance TRÈS FAIBLE.
COUCHE 1: Raisonnement abstrait. Arguments multi-niveaux. Dialectique complète.
COUCHE 2: TOUS les patterns y compris [C1+]. Problématisation. Auto-nuance.
COUCHE 3: TOUS les patterns y compris [C1+]. Connecteurs rares. Inversions.
COUCHE 4: Signaler TOUT. Tolérance quasi nulle.
SEUILS: 14-16/20 = attendu. 18+/20 = excellent.""",
}

# ═══════════════════════════════════════════════════════════════
# PROMPT — LE DIAGNOSTIC (bilingual + corrected transcription)
# ═══════════════════════════════════════════════════════════════

SYSTEM_PROMPT_DIAGNOSTIC = """Tu es un correcteur expert TCF Tâche 3, spécialisé dans la correction des anglophones. Tu utilises « La Méthode en Couches » — un framework diagnostique à 4 couches.

{les_moules_des_idees}

{les_moules}

{les_reflexes_anglais}

{grille}

═══════════════════════════════════════════════════════════
RÈGLES CRITIQUES POUR L'ANALYSE ORALE
═══════════════════════════════════════════════════════════
Tu analyses du FRANÇAIS PARLÉ, pas du français écrit. L'entrée est une transcription automatique de parole — ce n'est PAS l'écriture de l'étudiant.

1. NE JAMAIS signaler les erreurs de majuscules. Les majuscules n'existent pas à l'oral.
2. NE JAMAIS signaler les erreurs de ponctuation. La ponctuation n'existe pas à l'oral.
3. NE JAMAIS signaler les homophones comme erreurs, SAUF si le CONTEXTE rend à 100% clair quelle forme était voulue ET que la mauvaise forme serait une incompréhension grammaticale réelle. Homophones à ne JAMAIS signaler :
   - mérite/méritent (prononciation identique)
   - examiné/examinée/examinés/examinées (prononciation identique)
   - terminaisons é/er/ez (souvent identiques à l'oral)
   - est/et (quasi-identiques)
   - ses/ces/c'est (contextuels, accorder le bénéfice du doute)
   - a/à (identiques à l'oral)
   - ou/où (identiques à l'oral)
   - son/sont (quasi-identiques)
4. Quand deux formes sont phonétiquement identiques en français, TOUJOURS supposer que l'étudiant a utilisé la forme correcte. Le moteur de transcription a peut-être choisi le mauvais homophone — c'est un artefact de transcription, pas une erreur de l'étudiant.
5. NE JAMAIS catégoriser les artefacts de transcription comme « Réflexes anglais ». Les réflexes anglais sont STRUCTURELS : calques d'ordre des mots, transfert de prépositions, transfert du système de temps, traduction directe d'expressions anglaises. Un accent manquant ou un mauvais homophone N'EST PAS un réflexe anglais.
6. Concentre tes corrections sur ce qui est AUDIBLE : mauvaise conjugaison qui change la prononciation (je suis allé vs j'ai allé), mauvaise préposition (à vs de vs pour), liaison manquante, mauvais genre quand ça affecte la prononciation (le/la, un/une, bon/bonne), anglicismes structurels (ordre des mots), subjonctif manquant après conjonctions, etc.
7. La section LE GOULET doit identifier un problème STRUCTUREL dans la production orale — pas une erreur de transcription. Focus sur : structure argumentative manquante, absence de thèse-antithèse-synthèse, absence de connecteurs, patterns de phrases répétitifs, échec à développer les idées, sur-utilisation du présent simple, etc. Cite toujours un MOMENT SPÉCIFIQUE de leur discours pour illustrer le problème, et explique CE QU'ILS AURAIENT DÛ DIRE à la place.
8. Si la seule différence entre l'original et la correction est une majuscule, une ponctuation, ou un homophone — NE PAS l'inclure comme correction.

═══════════════════════════════════════════════════════════
SCORING RÉFLEXES ANGLAIS (Couche 4) — ne signaler QUE ces catégories :
═══════════════════════════════════════════════════════════
1. Calques d'ordre des mots : adjectif avant le nom quand il devrait suivre ('une importante décision' au lieu de 'une décision importante')
2. Transfert de préposition : utiliser la logique anglaise ('dépendre sur' au lieu de 'dépendre de')
3. Transfert de temps : passé composé où le français demande l'imparfait, ou présent où le français demande le subjonctif
4. Traduction directe d'expressions anglaises : 'faire sens' au lieu de 'avoir du sens', 'prendre avantage' au lieu de 'profiter de'
5. Articles manquants où le français les exige (transfert de l'article zéro anglais)
6. Formation de question avec syntaxe anglaise

NE PAS signaler comme Réflexes anglais : confusion d'homophones, majuscules, accents, tout ce qui pourrait être un artefact de transcription.

═══════════════════════════════════════════════════════════
CE QUI MARCHE (section positive)
═══════════════════════════════════════════════════════════
La section "ce_qui_marche" doit être SPÉCIFIQUE et encourageante. Pas de compliments génériques.
- Cite des phrases spécifiques que l'étudiant a utilisées correctement (en français, avec traduction)
- Nomme les structures grammaticales spécifiques qu'ils ont réussies
- Souligne les patterns de locuteur natif qu'ils ont utilisés (connecteurs, procédés rhétoriques, bon usage des prépositions)
- S'ils ont utilisé une structure thèse-antithèse, nomme-la explicitement
- Minimum 3 observations positives spécifiques par analyse
Le but est le renforcement : l'étudiant doit savoir exactement ce qu'il doit CONTINUER à faire.

INSTRUCTIONS BILINGUES :
- Le diagnostic DOIT être bilingue : français ET {ui_language_name}.
- Pour chaque champ texte, fournis la version française suivie de "|||" puis la version en {ui_language_name}.
- Exemple : "Bonne structure argumentative.|||Good argumentative structure."
- Si la langue de l'interface est le français, ne dédouble PAS : écris seulement en français.

INSTRUCTIONS PRONONCIATION :
Les mots suivants ont été signalés par le moteur de transcription comme mal reconnus (faible confiance). Analyse-les :
{pronunciation_flags}
- Si un mot à faible confiance est un mot FRANÇAIS légitime, c'est probablement un problème de PRONONCIATION.
- Si un mot à faible confiance est un mot ANGLAIS ou un faux-ami, c'est une INTERFÉRENCE (Couche 4), pas de la prononciation.
- Classe chaque mot signalé dans la section "prononciation" du JSON.

INSTRUCTIONS :
- Évalue STRICTEMENT selon la grille du niveau cible.
- Identifie LE GOULET : la couche la plus faible. Le goulet doit être un problème STRUCTUREL, pas un artefact de transcription.
- Produis une TRANSCRIPTION CORRIGÉE : réécris la production entière en français correct au niveau cible, en gardant les idées de l'étudiant.
- Pour chaque correction, indique la COUCHE concernée.
- N'inclus une correction QUE si l'erreur est AUDIBLE à l'oral. Exclus les corrections qui ne portent que sur la casse, la ponctuation ou les homophones.

{exam_profile_block}

{dual_channel_block}

Réponds UNIQUEMENT en JSON valide :
{{
  "note_globale": <float 0-20>,
  "la_carte": {{
    "le_fond": <0-5>,
    "les_moules_des_idees": <0-5>,
    "les_moules": <0-5>,
    "les_reflexes_anglais": <0-5>
  }},
  "le_goulet": {{
    "couche": <1-4>,
    "nom": "<le_fond | les_moules_des_idees | les_moules | les_reflexes_anglais>",
    "explication": "<FR|||LANG — cite un moment SPÉCIFIQUE du discours et explique ce qui aurait dû être dit>"
  }},
  "ce_qui_marche": "<FR|||LANG — minimum 3 observations positives spécifiques avec citations du discours>",
  "analyse_par_couche": {{
    "what_works":        {{"title_fr": "Ce qui marche",              "content_fr": "<2-4 phrases FR, cite des passages>"}},
    "what_doesnt_work":  {{"title_fr": "Ce qui ne marche pas",       "content_fr": "<2-4 phrases FR, LA faiblesse principale>"}},
    "english_habits":    {{"title_fr": "Habitudes anglaises",        "content_fr": "<2-4 phrases FR, 1-3 exemples concrets>"}},
    "structure_quality": {{"title_fr": "Structure et construction",  "content_fr": "<2-4 phrases FR, architecture + organisation>"}}
  }},
  "next_step": "<dans {ui_language_name} — UNE seule directive impérative et concrète pour le prochain enregistrement>",
  "patterns_detectes": ["<clés>"],
  "patterns_manquants": ["<clés>"],
  "reflexes_detectes": ["<clés>"],
  "corrections": [
    {{
      "original": "<ce que l'étudiant a dit — phrase complète>",
      "corrige": "<version correcte — même phrase corrigée>",
      "changed_segments": [
        {{"start": <index début dans corrige>, "end": <index fin>, "type": "<added|changed|removed>"}}
      ],
      "couche": <1-4>,
      "nom_couche": "<nom>",
      "pattern": "<nom du pattern>",
      "explication": "<FR|||LANG>"
    }}
  ],
  "prononciation": {{
    "score": <0-5>,
    "mots_problematiques": [
      {{
        "mot": "<le mot mal prononcé>",
        "confidence": <0-1>,
        "type": "<prononciation | interference | transcription_error>",
        "conseil": "<FR|||LANG>"
      }}
    ],
    "commentaire": "<FR|||LANG>"
  }},
  "transcription_corrigee": "<la production entière réécrite en français correct, même structure d'idées mais phrases corrigées>",
  "la_prochaine_etape": "<FR|||LANG — UNE seule recommandation (legacy, conserve pour rétro-compat)>",
  "{exam_profile_namespace}": {{
    "overall_score": <float 0-20 — moyenne des critères arrondie à 1 décimale>,
    "criteria": [
      {{
        "criterion_key": "<clé du critère, ordre fixe défini ci-dessus>",
        "score": <0-20>,
        "examiner_remark_fr": "<FR uniquement, 1-2 phrases, évaluation pure — jamais de citation ou de transformation>",
        "teacher_coaching": {{
          "coaching_en": "<TOUJOURS en anglais, cite les mots EXACTS de l'étudiant>",
          "coaching_fr": "<TOUJOURS un exemple en français (matériel d'apprentissage)>",
          "transformation": "<dans {ui_language_name} — une action concrète pour le prochain essai>"
        }}
      }}
    ]
  }}
}}"""


# ═══════════════════════════════════════════════════════════════
# PROMPT — L'ORDONNANCE
# ═══════════════════════════════════════════════════════════════

SYSTEM_PROMPT_ORDONNANCE = """Tu es un créateur d'exercices de français pour anglophones. Tu reçois un diagnostic et tu crées des exercices CIBLÉS sur le goulet.

INSTRUCTIONS BILINGUES :
- Les consignes doivent être en {ui_language_name} (pour que l'étudiant comprenne ce qu'on lui demande).
- Le contenu des exercices et les solutions restent en FRANÇAIS (c'est du français qu'on pratique).
- Les explications de solution sont bilingues : français + {ui_language_name}, séparées par "|||".

RÈGLES POUR LES EXERCICES :
1. Maximum 5 exercices par correction prioritaire
2. Chaque exercice est UNE courte phrase (max 10 mots)
3. Toujours fournir un MODÈLE en premier : montre un exemple complété pour que l'étudiant voie le pattern avant de tenter
4. Utilise le format QCM (3 options) — l'étudiant sélectionne la bonne réponse, il n'écrit pas librement
5. Focus UNIQUEMENT sur la grammaire qui était audiblement incorrecte dans leur discours : conjugaison verbale, choix de préposition, genre (le/la), choix de temps, déclencheurs du subjonctif
6. NE JAMAIS inclure d'exercices de vocabulaire
7. NE JAMAIS inclure d'exercices d'orthographe
8. Chaque exercice doit cibler directement l'erreur trouvée dans CETTE session
9. Format par exercice :
   - "modele" : une phrase exemple complétée montrant le pattern (ex: "Je pense À mon avenir — préposition à après penser")
   - "phrase" : la phrase à trous (ex: "Elle s'intéresse ___ la politique")
   - "options" : tableau de 3 choix (ex: ["à", "de", "pour"])
   - "reponse" : l'index (0-2) de la bonne réponse
- Si des problèmes de prononciation ont été détectés, inclus 1 exercice de discrimination auditive parmi les 5.
- Utilise le sujet de la production comme contexte.

Réponds UNIQUEMENT en JSON valide :
{{
  "couche_ciblee": <1-4>,
  "nom_couche": "<nom>",
  "exercices": [
    {{
      "numero": <1-5>,
      "type": "<type court: préposition | conjugaison | genre | temps | subjonctif | prononciation>",
      "consigne": "<en {ui_language_name} — courte instruction>",
      "modele": "<phrase modèle complétée en français avec explication courte>",
      "phrase": "<phrase à trous en français, max 10 mots>",
      "options": ["<choix1>", "<choix2>", "<choix3>"],
      "reponse": <0|1|2>,
      "explication": "<FR|||LANG — pourquoi cette réponse>"
    }}
  ]
}}"""


# ═══════════════════════════════════════════════════════════════
# MAIN ANALYSIS FUNCTION
# ═══════════════════════════════════════════════════════════════

async def analyze_transcript(
    transcript: str,
    topic: str = "",
    target_level: str = "B2",
    ui_language: str = "en",
    low_confidence_words: list = None,
    exam_profile: str | ExamProfile = "tcf_canada",
) -> dict:
    """
    Three-pass analysis:
      Pass 1 — Le Diagnostic (bilingual + corrected transcription + pronunciation)
      Pass 2 — L'Ordonnance (targeted exercises)

    The ``exam_profile`` selects the official scoring framework applied in
    parallel to the 4-layer methodology (default: TCF Canada five criteria).
    Accepts either a profile id string or a resolved ExamProfile instance.
    """
    profile = exam_profile if isinstance(exam_profile, ExamProfile) else get_profile(exam_profile)

    if not settings.ANTHROPIC_API_KEY:
        return _demo_feedback(transcript, profile)

    ui_lang_name = LANGUAGE_NAMES.get(ui_language, "anglais")
    grille = GRILLES.get(target_level, GRILLES["B2"])

    # Build pronunciation flags
    pronunciation_flags = "Aucun mot signalé."
    if low_confidence_words:
        flags = [f"- \"{w['text']}\" (confiance: {w['confidence']})" for w in low_confidence_words[:15]]
        pronunciation_flags = "\n".join(flags)

    # ── Exam profile prompt block ──────────────────────────────
    criteria_block = profile.build_criteria_prompt_block("oral")
    exam_profile_block = profile.system_prompt_preamble.replace(
        "{criteria_block}", criteria_block
    ).replace(
        "{ui_language_name}", ui_lang_name
    )

    # ── Dual-channel voice block (F-032) ───────────────────────
    dual_channel_block = DUAL_CHANNEL_BLOCK.replace(
        "{examiner_voice_guide}", profile.examiner_voice_guide
    ).replace(
        "{teacher_voice_guide}", profile.teacher_voice_guide
    )

    # ── Pass 1: Le Diagnostic ──────────────────────────────────
    # Note: {ui_language_name} is substituted LAST so that placeholders nested
    # inside dual_channel_block / exam_profile_block also resolve (F-044).
    system_diag = SYSTEM_PROMPT_DIAGNOSTIC.replace(
        "{les_moules_des_idees}", LES_MOULES_DES_IDEES
    ).replace(
        "{les_moules}", LES_MOULES
    ).replace(
        "{les_reflexes_anglais}", LES_REFLEXES_ANGLAIS
    ).replace(
        "{grille}", grille
    ).replace(
        "{pronunciation_flags}", pronunciation_flags
    ).replace(
        "{exam_profile_block}", exam_profile_block
    ).replace(
        "{dual_channel_block}", dual_channel_block
    ).replace(
        "{exam_profile_namespace}", profile.namespace
    ).replace(
        "{ui_language_name}", ui_lang_name
    )

    user_msg = (
        f"Niveau cible : {target_level}\n"
        f"Sujet : {topic or '(non spécifié)'}\n\n"
        f"Transcription de la production orale :\n\"\"\"\n{transcript}\n\"\"\""
    )

    diagnostic = await _call_claude(system_diag, user_msg)

    # ── Pass 2: L'Ordonnance ───────────────────────────────────
    ordonnance = None
    if isinstance(diagnostic, dict) and "le_goulet" in diagnostic:
        goulet = diagnostic["le_goulet"]
        prononciation = diagnostic.get("prononciation", {})

        ordo_system = SYSTEM_PROMPT_ORDONNANCE.replace(
            "{ui_language_name}", ui_lang_name
        )

        ordo_user = (
            f"Niveau cible : {target_level}\n"
            f"Sujet : {topic or '(non spécifié)'}\n\n"
            f"DIAGNOSTIC :\n"
            f"- Goulet : Couche {goulet.get('couche', '?')} — {goulet.get('nom', '?')}\n"
            f"- Explication : {goulet.get('explication', '')}\n"
            f"- Patterns manquants : {json.dumps(diagnostic.get('patterns_manquants', []), ensure_ascii=False)}\n"
            f"- Réflexes détectés : {json.dumps(diagnostic.get('reflexes_detectes', []), ensure_ascii=False)}\n"
            f"- Prononciation : {json.dumps(prononciation.get('mots_problematiques', []), ensure_ascii=False)}\n\n"
            f"Corrections :\n{json.dumps(diagnostic.get('corrections', []), ensure_ascii=False, indent=2)}\n\n"
            f"Transcription :\n\"\"\"\n{transcript}\n\"\"\""
        )

        ordonnance = await _call_claude(ordo_system, ordo_user)

    # ── Assemble ───────────────────────────────────────────────
    result = diagnostic if isinstance(diagnostic, dict) else {
        "note_globale": 0,
        "la_carte": {"le_fond": 0, "les_moules_des_idees": 0, "les_moules": 0, "les_reflexes_anglais": 0},
        "le_goulet": {"couche": 0, "nom": "", "explication": ""},
        "ce_qui_marche": "",
        "analyse_par_couche": {},
        "patterns_detectes": [], "patterns_manquants": [], "reflexes_detectes": [],
        "corrections": [], "prononciation": {"score": 0, "mots_problematiques": [], "commentaire": ""},
        "transcription_corrigee": "",
        "la_prochaine_etape": "",
        "raw_diagnostic": str(diagnostic),
    }

    if ordonnance and isinstance(ordonnance, dict):
        result["ordonnance"] = ordonnance
    elif ordonnance:
        result["ordonnance_raw"] = str(ordonnance)

    # ── Exam profile evaluation (TCF Canada etc.) ──────────────
    result["exam_profile"] = _normalize_profile_evaluation(result, profile, "oral")

    result["raw_response"] = json.dumps(result, ensure_ascii=False)

    # ── Backward compat (legacy 4-couche consumers) ────────────
    # note_globale is the legacy holistic /20; the profile-driven overall
    # (e.g. mean of 5 TCF criteria) lives in result["exam_profile"]["overall_score"].
    carte = result.get("la_carte", {})
    result["overall_score"] = result.get("note_globale", 0)
    result["scores"] = {
        "le_fond": carte.get("le_fond", 0),
        "les_moules_des_idees": carte.get("les_moules_des_idees", 0),
        "les_moules": carte.get("les_moules", 0),
        "les_reflexes_anglais": carte.get("les_reflexes_anglais", 0),
    }
    result["analysis"] = result.get("ce_qui_marche", "")
    result["recommendations"] = result.get("la_prochaine_etape", "")

    return result


def _normalize_profile_evaluation(
    result: dict, profile: ExamProfile, skill: str
) -> dict:
    """Extract the profile evaluation Claude returned under its namespace,
    compute CEFR + secondary-framework levels deterministically, and join in
    the student-facing labels so the frontend can render without loading the
    profile module.

    Returns a stable public shape:
        {
          "profile_id", "display_name", "frameworks_shown",
          "overall_score", "cefr_level", "secondary_framework_label",
          "secondary_framework_value",
          "criteria_breakdown": [
             {criterion_key, label_fr_technical, label_student, score,
              feedback, max_score}
          ]
        }
    """
    raw = result.get(profile.namespace, {}) if isinstance(result, dict) else {}
    claude_criteria = raw.get("criteria", []) if isinstance(raw, dict) else []

    by_key = {
        c.get("criterion_key"): c
        for c in claude_criteria
        if isinstance(c, dict)
    }

    criteria_rows = []
    scores: list[float] = []
    for criterion in profile.criteria_for(skill):
        src = by_key.get(criterion.key, {})
        score = _coerce_float(src.get("score"))
        if score is not None:
            scores.append(score)
        tc = src.get("teacher_coaching") or {}
        if not isinstance(tc, dict):
            tc = {}
        criteria_rows.append({
            "criterion_key": criterion.key,
            "label_fr_technical": criterion.label_fr_technical,
            "label_fr_student": criterion.label_fr_student,
            "label_en_student": criterion.label_en_student,
            "label_es_student": criterion.label_es_student,
            "max_score": criterion.max_score,
            "score": score if score is not None else 0,
            "feedback": src.get("feedback", ""),  # legacy single-voice field
            "examiner_remark_fr": src.get("examiner_remark_fr", ""),
            "teacher_coaching": {
                "coaching_en": tc.get("coaching_en", ""),
                "coaching_fr": tc.get("coaching_fr", ""),
                "transformation": tc.get("transformation", ""),
            },
        })

    if scores:
        overall = round(sum(scores) / len(scores), 1)
    else:
        overall = _coerce_float(raw.get("overall_score")) or 0.0

    cefr = profile.score_to_cefr(overall)
    secondary_value = (
        profile.cefr_to_secondary(cefr) if profile.cefr_to_secondary else None
    )

    return {
        "profile_id": profile.id,
        "display_name": profile.display_name,
        "frameworks_shown": list(profile.frameworks_shown),
        "overall_score": overall,
        "cefr_level": cefr,
        "secondary_framework_label": profile.secondary_framework_label,
        "secondary_framework_value": secondary_value,
        "criteria_breakdown": criteria_rows,
    }


def _coerce_float(v) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# ═══════════════════════════════════════════════════════════════
# CLAUDE API
# ═══════════════════════════════════════════════════════════════

async def _call_claude(system_prompt: str, user_message: str) -> dict | str:
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 8192,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_message}],
            },
        )
        resp.raise_for_status()
        data = resp.json()

    raw = data["content"][0]["text"]
    try:
        return json.loads(
            raw.strip()
            .removeprefix("```json").removeprefix("```")
            .removesuffix("```").strip()
        )
    except json.JSONDecodeError:
        return raw


# ═══════════════════════════════════════════════════════════════
# DEMO
# ═══════════════════════════════════════════════════════════════

async def analyze_recording(
    tache_mode: str,
    **kwargs,
) -> dict:
    """F-047 dispatcher — route by Tâche mode to the per-mode analyzer.

    Stubs for T1/T2/T3 delegate to ``analyze_transcript`` and stamp a
    ``mode`` field (F-048/F-049/F-051 will replace their bodies). Legacy
    rows fall through to the unchanged generic path and get
    ``mode: "legacy"`` stamped so downstream code doesn't have to special-
    case unset values.

    ``writing`` is intentionally NOT routed here — writing submissions go
    through ``app.services.writing_analysis`` via the writing router and
    never create a ``Recording`` row.
    """
    # Imports sit inside the function to avoid a circular import: the
    # tache_* modules import ``analyze_transcript`` from this module.

    # Tâche 3 accepts a prompt kwarg that the other modes don't
    # understand. Peel it out so T1/T2/legacy callers don't have their
    # **kwargs polluted. (F-049+ stubs accept **kwargs and just ignore,
    # but the legacy path forwards straight to analyze_transcript which
    # is strict on its signature.)
    t3_prompt = kwargs.pop("tache_3_prompt", None)

    if tache_mode == "tache_1":
        from app.services.tache_1 import analyze_tache_1
        return await analyze_tache_1(**kwargs)
    if tache_mode == "tache_2":
        from app.services.tache_2 import analyze_tache_2
        return await analyze_tache_2(**kwargs)
    if tache_mode == "tache_3":
        from app.services.tache_3 import analyze_tache_3
        return await analyze_tache_3(tache_3_prompt=t3_prompt, **kwargs)

    # legacy (and any unknown value that somehow slipped past validation)
    result = await analyze_transcript(**kwargs)
    if isinstance(result, dict):
        result.setdefault("mode", "legacy")
    return result


def _demo_feedback(transcript: str, profile: ExamProfile | None = None) -> dict:
    wc = len(transcript.split())
    if profile is None:
        profile = get_profile()

    demo_criteria = [
        {"criterion_key": c.key, "score": 10, "feedback": "[DEMO]|||[DEMO]"}
        for c in profile.criteria_for("oral")
    ]
    result = {
        "note_globale": 10.0, "overall_score": 10.0,
        "la_carte": {"le_fond": 3, "les_moules_des_idees": 2, "les_moules": 2, "les_reflexes_anglais": 3},
        "scores": {"le_fond": 3, "les_moules_des_idees": 2, "les_moules": 2, "les_reflexes_anglais": 3},
        "le_goulet": {"couche": 3, "nom": "les_moules", "explication": "[DEMO] Configure API keys.|||[DEMO] Configure API keys."},
        "ce_qui_marche": f"[DEMO] {wc} words received.|||[DEMO] {wc} words received.",
        "analyse_par_couche": {"le_fond": "[DEMO]", "les_moules_des_idees": "[DEMO]", "les_moules": "[DEMO]", "les_reflexes_anglais": "[DEMO]"},
        "patterns_detectes": [], "patterns_manquants": [], "reflexes_detectes": [],
        "corrections": [],
        "prononciation": {"score": 0, "mots_problematiques": [], "commentaire": "[DEMO]"},
        "transcription_corrigee": transcript,
        "la_prochaine_etape": "Configure API keys.|||Configure API keys.",
        "ordonnance": {"couche_ciblee": 3, "nom_couche": "les_moules", "exercices": []},
        profile.namespace: {"overall_score": 10.0, "criteria": demo_criteria},
        "analysis": f"[DEMO] {wc} words.", "recommendations": "Configure API keys.", "raw_response": "",
    }
    result["exam_profile"] = _normalize_profile_evaluation(result, profile, "oral")
    return result
