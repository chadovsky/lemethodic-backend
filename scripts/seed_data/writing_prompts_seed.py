"""LeMethodic — Writing Prompts Seed Pack v1
==========================================

Starter pack of 14 ORIGINAL writing prompts for the F-224 writing surface.
All prompts authored fresh; format conventions follow TCF Canada / standard
TCF Expression Écrite Tâche 1/2/3 specs. Topics distributed across 8 themes
to enable future filtering by user weakness.

Distribution:
    - Tâche 1 (B1, message): 6 prompts
    - Tâche 2 (B1, account/article): 4 prompts
    - Tâche 2 (B2, account/article): 1 prompt
    - Tâche 3 (B2, argumentative w/ 2 documents): 3 prompts

    Total: 14 prompts (10 B1 + 4 B2 = ~71% B1, close to target 80/20 mix)

Topics covered: travel, work, family, education, health, technology,
                environment, society

Usage:
    from scripts.seed_writing_prompts import seed_from_data
    from scripts.seed_data.writing_prompts_seed import WRITING_PROMPTS_SEED

    seed_from_data(WRITING_PROMPTS_SEED)

Or invoke the BE seeding command:
    python -m scripts.seed_writing_prompts
"""

WRITING_PROMPTS_SEED = [
    # ──────────────────────────────────────────────────────────────────
    # TÂCHE 1 — B1 — Personal message (60-120 words, ~10 min)
    # ──────────────────────────────────────────────────────────────────
    {
        "tache_level": 1,
        "target_level": "B1",
        "title_fr": "Voyage à Lyon",
        "prompt_fr": (
            "Vous prévoyez de visiter Lyon le mois prochain. "
            "Vous écrivez un courriel à un(e) ami(e) qui habite dans cette ville "
            "pour lui annoncer votre venue. Précisez les dates de votre séjour, "
            "les activités que vous aimeriez faire ensemble, et demandez-lui "
            "des conseils sur les restaurants à essayer."
        ),
        "prompt_en": (
            "You're planning to visit Lyon next month. Write an email to a friend "
            "who lives there announcing your visit. Include the dates of your "
            "stay, activities you'd like to do together, and ask for restaurant "
            "recommendations."
        ),
        "min_words": 60,
        "max_words": 120,
        "time_limit_min": 10,
        "topic_tag": "travel",
    },
    {
        "tache_level": 1,
        "target_level": "B1",
        "title_fr": "Demande de congé",
        "prompt_fr": (
            "Vous travaillez dans une entreprise depuis deux ans. Vous écrivez "
            "un courriel à votre supérieur pour demander une semaine de congé "
            "en juillet. Expliquez les raisons de votre demande, proposez une "
            "organisation pour que votre absence ne perturbe pas le travail de "
            "l'équipe, et remerciez-le par avance."
        ),
        "prompt_en": (
            "You've worked at a company for two years. Write an email to your "
            "manager requesting a week of vacation in July. Explain your reasons, "
            "propose how to organize your absence so it doesn't disrupt the team, "
            "and thank them in advance."
        ),
        "min_words": 60,
        "max_words": 120,
        "time_limit_min": 10,
        "topic_tag": "work",
    },
    {
        "tache_level": 1,
        "target_level": "B1",
        "title_fr": "Annonce d'un déménagement",
        "prompt_fr": (
            "Vous avez décidé de déménager dans une autre ville pour des raisons "
            "professionnelles. Vous écrivez un message à un membre de votre "
            "famille pour lui annoncer la nouvelle. Expliquez les raisons de ce "
            "changement, parlez de votre nouvelle situation, et proposez un "
            "moment pour vous voir avant le départ."
        ),
        "prompt_en": (
            "You've decided to move to another city for work reasons. Write a "
            "message to a family member announcing the news. Explain the reasons, "
            "describe your new situation, and propose a time to meet before "
            "you leave."
        ),
        "min_words": 60,
        "max_words": 120,
        "time_limit_min": 10,
        "topic_tag": "family",
    },
    {
        "tache_level": 1,
        "target_level": "B1",
        "title_fr": "Inscription à une formation",
        "prompt_fr": (
            "Vous avez trouvé une formation qui vous intéresse beaucoup. Vous "
            "écrivez un courriel au responsable du programme pour demander des "
            "informations supplémentaires (durée, prix, contenu, dates). "
            "Présentez-vous brièvement, expliquez pourquoi cette formation vous "
            "intéresse, et demandez comment vous inscrire."
        ),
        "prompt_en": (
            "You've found a training program you're very interested in. Write "
            "an email to the program coordinator asking for more information "
            "(duration, price, content, dates). Briefly introduce yourself, "
            "explain why the program interests you, and ask how to register."
        ),
        "min_words": 60,
        "max_words": 120,
        "time_limit_min": 10,
        "topic_tag": "education",
    },
    {
        "tache_level": 1,
        "target_level": "B1",
        "title_fr": "Annulation de rendez-vous",
        "prompt_fr": (
            "Vous aviez un rendez-vous important avec un médecin spécialiste "
            "cette semaine, mais vous ne pouvez plus y aller. Vous écrivez un "
            "courriel au cabinet médical pour annuler. Expliquez la raison de "
            "votre annulation, présentez vos excuses, et demandez à reprendre "
            "rendez-vous à une date plus tardive."
        ),
        "prompt_en": (
            "You had an important specialist appointment this week, but can no "
            "longer attend. Write an email to the medical office to cancel. "
            "Explain why, apologize, and ask to reschedule for a later date."
        ),
        "min_words": 60,
        "max_words": 120,
        "time_limit_min": 10,
        "topic_tag": "health",
    },
    {
        "tache_level": 1,
        "target_level": "B1",
        "title_fr": "Problème avec un appareil",
        "prompt_fr": (
            "Vous avez acheté un téléphone portable il y a deux semaines, mais "
            "il ne fonctionne pas correctement. Vous écrivez un courriel au "
            "service client du magasin pour expliquer le problème. Décrivez les "
            "défauts que vous avez constatés, mentionnez la date d'achat, et "
            "demandez un remboursement ou un remplacement."
        ),
        "prompt_en": (
            "You bought a phone two weeks ago, but it isn't working properly. "
            "Write an email to customer service explaining the problem. Describe "
            "the defects you've noticed, mention the purchase date, and request "
            "a refund or replacement."
        ),
        "min_words": 60,
        "max_words": 120,
        "time_limit_min": 10,
        "topic_tag": "technology",
    },

    # ──────────────────────────────────────────────────────────────────
    # TÂCHE 2 — B1 — Account / article / structured email
    # (60-120 words, ~10 min)
    # ──────────────────────────────────────────────────────────────────
    {
        "tache_level": 2,
        "target_level": "B1",
        "title_fr": "Mon premier emploi",
        "prompt_fr": (
            "Vous racontez votre première expérience professionnelle dans un "
            "article pour un site internet d'orientation pour étudiants. "
            "Décrivez le poste que vous avez occupé, les compétences que vous "
            "avez développées, les difficultés que vous avez rencontrées, et "
            "ce que cette expérience vous a appris."
        ),
        "prompt_en": (
            "Recount your first professional experience in an article for a "
            "student career-guidance website. Describe the position you held, "
            "skills you developed, difficulties you encountered, and what the "
            "experience taught you."
        ),
        "min_words": 60,
        "max_words": 120,
        "time_limit_min": 10,
        "topic_tag": "work",
    },
    {
        "tache_level": 2,
        "target_level": "B1",
        "title_fr": "Une fête en famille",
        "prompt_fr": (
            "Vous écrivez un compte-rendu pour un blog familial sur une fête "
            "de famille à laquelle vous avez participé récemment. Décrivez "
            "l'événement (occasion, lieu, personnes présentes), racontez un "
            "moment particulièrement marquant, et expliquez pourquoi cette "
            "journée restera dans votre mémoire."
        ),
        "prompt_en": (
            "Write a blog post for a family blog about a recent family "
            "celebration you attended. Describe the event (occasion, venue, "
            "people present), recount one particularly memorable moment, and "
            "explain why the day will stay with you."
        ),
        "min_words": 60,
        "max_words": 120,
        "time_limit_min": 10,
        "topic_tag": "family",
    },
    {
        "tache_level": 2,
        "target_level": "B1",
        "title_fr": "Mes habitudes écologiques",
        "prompt_fr": (
            "Un magazine local vous invite à partager vos habitudes pour "
            "protéger l'environnement. Rédigez un texte court qui présente "
            "trois ou quatre actions concrètes que vous faites dans votre vie "
            "quotidienne. Expliquez ce qui vous a motivé à les adopter et leur "
            "impact dans votre quotidien."
        ),
        "prompt_en": (
            "A local magazine invites you to share your eco-friendly habits. "
            "Write a short text presenting three or four concrete actions you "
            "take in your daily life. Explain what motivated you to adopt them "
            "and their impact on your everyday."
        ),
        "min_words": 60,
        "max_words": 120,
        "time_limit_min": 10,
        "topic_tag": "environment",
    },
    {
        "tache_level": 2,
        "target_level": "B1",
        "title_fr": "Une expérience de bénévolat",
        "prompt_fr": (
            "Vous avez participé à une activité de bénévolat dans votre "
            "communauté. Vous rédigez un article pour le journal local pour "
            "encourager d'autres personnes à s'engager. Décrivez l'activité "
            "(où, quand, avec qui), expliquez ce que vous avez fait "
            "concrètement, et partagez ce que cette expérience vous a apporté "
            "personnellement."
        ),
        "prompt_en": (
            "You took part in a volunteer activity in your community. Write "
            "an article for the local newspaper to encourage others to get "
            "involved. Describe the activity (where, when, with whom), explain "
            "what you actually did, and share what the experience brought you "
            "personally."
        ),
        "min_words": 60,
        "max_words": 120,
        "time_limit_min": 10,
        "topic_tag": "society",
    },

    # ──────────────────────────────────────────────────────────────────
    # TÂCHE 2 — B2 — Account / article (more complex, 120-180 words)
    # ──────────────────────────────────────────────────────────────────
    {
        "tache_level": 2,
        "target_level": "B2",
        "title_fr": "L'apprentissage à l'étranger",
        "prompt_fr": (
            "Vous avez vécu une expérience d'études ou de formation à "
            "l'étranger. Vous rédigez un article pour un magazine spécialisé "
            "en éducation internationale. Présentez le contexte de votre "
            "séjour (pays, durée, type de programme), décrivez les principaux "
            "défis culturels et académiques que vous avez rencontrés, "
            "expliquez comment vous les avez surmontés, et concluez en "
            "analysant les bénéfices durables de cette expérience sur votre "
            "parcours personnel et professionnel."
        ),
        "prompt_en": (
            "You've had a study or training experience abroad. Write an "
            "article for a magazine specializing in international education. "
            "Present the context of your stay (country, duration, program "
            "type), describe the main cultural and academic challenges you "
            "encountered, explain how you overcame them, and conclude by "
            "analyzing the lasting benefits of the experience on your personal "
            "and professional trajectory."
        ),
        "min_words": 120,
        "max_words": 180,
        "time_limit_min": 12,
        "topic_tag": "education",
    },

    # ──────────────────────────────────────────────────────────────────
    # TÂCHE 3 — B2 — Argumentative essay comparing 2 documents
    # (120-180 words, ~15 min — TCF Canada Tâche 3 format)
    # ──────────────────────────────────────────────────────────────────
    {
        "tache_level": 3,
        "target_level": "B2",
        "title_fr": "Le télétravail au quotidien",
        "prompt_fr": (
            "Deux personnes expriment leur point de vue sur le télétravail.\n\n"
            "**Document A — Mme Dupont, cadre :**\n"
            "« Le télétravail a transformé ma vie professionnelle. Je gagne "
            "plus de deux heures par jour en évitant les transports, je suis "
            "plus productive sans les interruptions du bureau, et je peux "
            "mieux concilier ma vie familiale et mon travail. C'est un "
            "véritable progrès social. »\n\n"
            "**Document B — M. Martin, chef d'équipe :**\n"
            "« Le télétravail isole les salariés et fragilise les liens dans "
            "les équipes. La frontière entre vie privée et travail disparaît, "
            "on travaille plus longtemps sans s'en rendre compte, et la "
            "créativité collective qui naît des échanges spontanés au bureau "
            "s'est éteinte. »\n\n"
            "Rédigez un article qui présente d'abord les deux points de vue, "
            "puis exposez votre propre opinion en l'argumentant."
        ),
        "prompt_en": (
            "Two perspectives on remote work. Document A (a manager) argues "
            "remote work transformed her professional life: saved commute time, "
            "higher productivity, better family-work balance — a real social "
            "advance. Document B (a team lead) argues remote work isolates "
            "employees, blurs the work/life boundary, encourages overworking, "
            "and kills the spontaneous creativity of office exchanges. Write "
            "a 120-180 word article: present both views, then argue your own "
            "position."
        ),
        "min_words": 120,
        "max_words": 180,
        "time_limit_min": 15,
        "topic_tag": "technology",
    },
    {
        "tache_level": 3,
        "target_level": "B2",
        "title_fr": "Voiture individuelle ou transports en commun",
        "prompt_fr": (
            "Deux opinions sur la mobilité urbaine.\n\n"
            "**Document A — M. Leblanc, automobiliste :**\n"
            "« La voiture individuelle reste le moyen de transport le plus "
            "pratique. Elle offre une liberté totale dans le choix des horaires "
            "et des trajets, transporte facilement enfants et bagages, et "
            "permet d'atteindre des zones mal desservies par les transports "
            "publics. Limiter son usage punirait les familles. »\n\n"
            "**Document B — Mme Roy, urbaniste :**\n"
            "« La voiture individuelle pollue, congestionne les villes et "
            "coûte cher en infrastructures. Investir massivement dans les "
            "transports en commun réduirait les émissions, démocratiserait la "
            "mobilité, et rendrait les villes plus agréables. C'est une "
            "question de priorités collectives. »\n\n"
            "Rédigez un article qui présente les deux points de vue, puis "
            "donnez votre position argumentée."
        ),
        "prompt_en": (
            "Two opinions on urban mobility. Document A (a driver) argues "
            "individual cars remain the most practical transport: total freedom "
            "of schedule and route, easy with kids and luggage, reaches areas "
            "poorly served by public transit; limiting them would punish "
            "families. Document B (an urban planner) argues cars pollute, "
            "congest cities, and cost taxpayers in infrastructure; investing "
            "in public transit would cut emissions, democratize mobility, and "
            "improve city life — a question of collective priorities. Write "
            "a 120-180 word article: present both views, then argue your own."
        ),
        "min_words": 120,
        "max_words": 180,
        "time_limit_min": 15,
        "topic_tag": "environment",
    },
    {
        "tache_level": 3,
        "target_level": "B2",
        "title_fr": "Médecines alternatives et médecine conventionnelle",
        "prompt_fr": (
            "Deux points de vue sur les approches de santé.\n\n"
            "**Document A — Dr Gauthier, médecin généraliste :**\n"
            "« La médecine conventionnelle, fondée sur la recherche "
            "scientifique et les essais cliniques, reste la seule approche "
            "fiable pour traiter les maladies. Les médecines alternatives "
            "manquent de preuves solides et peuvent retarder des soins "
            "essentiels, avec des conséquences graves pour les patients. »\n\n"
            "**Document B — Mme Tremblay, naturopathe :**\n"
            "« Les médecines alternatives complètent utilement la médecine "
            "conventionnelle. Elles s'attaquent aux causes profondes plutôt "
            "qu'aux symptômes, prennent en compte la personne dans sa "
            "globalité, et privilégient la prévention. Elles répondent à un "
            "besoin réel des patients d'être écoutés et accompagnés. »\n\n"
            "Rédigez un article qui présente les deux points de vue, puis "
            "exposez et argumentez votre opinion."
        ),
        "prompt_en": (
            "Two views on health approaches. Document A (a general "
            "practitioner) argues conventional medicine — grounded in "
            "scientific research and clinical trials — is the only reliable "
            "approach; alternative medicines lack solid evidence and can delay "
            "essential care with serious consequences. Document B (a "
            "naturopath) argues alternative medicines usefully complement "
            "conventional care: they address root causes rather than symptoms, "
            "treat the whole person, prioritize prevention, and meet a real "
            "patient need to be heard and supported. Write a 120-180 word "
            "article: present both views, then argue your own position."
        ),
        "min_words": 120,
        "max_words": 180,
        "time_limit_min": 15,
        "topic_tag": "health",
    },
]


# Quick sanity check on counts and distribution
if __name__ == "__main__":
    from collections import Counter

    print(f"Total prompts: {len(WRITING_PROMPTS_SEED)}")
    print(f"By tâche: {Counter(p['tache_level'] for p in WRITING_PROMPTS_SEED)}")
    print(f"By level: {Counter(p['target_level'] for p in WRITING_PROMPTS_SEED)}")
    print(f"By topic: {Counter(p['topic_tag'] for p in WRITING_PROMPTS_SEED)}")
