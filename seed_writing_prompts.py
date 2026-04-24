"""Run once to seed writing prompts: python seed_writing_prompts.py"""
from app.database import SessionLocal, engine, Base
from app.models.models import User, Recording, Feedback, TestTopic  # load all models first
from app.models.writing import WritingPrompt, WritingSubmission

Base.metadata.create_all(bind=engine)
db = SessionLocal()

PROMPTS = [
    # ── B1 (4 prompts) ────────────────────────────────────────────
    {
        "level": "B1",
        "theme": "Vie quotidienne",
        "prompt_type": "formal_letter",
        "prompt_text": "Vous avez commande un produit en ligne mais vous avez recu le mauvais article. Ecrivez une lettre au service client pour expliquer le probleme et demander un echange ou un remboursement. (160-180 mots)",
        "min_words": 160,
        "max_words": 180,
        "time_limit_minutes": 30,
    },
    {
        "level": "B1",
        "theme": "Education",
        "prompt_type": "essay",
        "prompt_text": "Un magazine pour jeunes vous demande d'ecrire un article sur les avantages et les inconvenients des cours en ligne. Donnez votre opinion avec des exemples concrets. (160-180 mots)",
        "min_words": 160,
        "max_words": 180,
        "time_limit_minutes": 30,
    },
    {
        "level": "B1",
        "theme": "Societe",
        "prompt_type": "argumentative",
        "prompt_text": "Pensez-vous que les transports en commun devraient etre gratuits pour tout le monde ? Justifiez votre point de vue avec des arguments et des exemples. (160-180 mots)",
        "min_words": 160,
        "max_words": 180,
        "time_limit_minutes": 30,
    },
    {
        "level": "B1",
        "theme": "Travail",
        "prompt_type": "formal_letter",
        "prompt_text": "Vous souhaitez faire un stage dans une entreprise francophone. Ecrivez une lettre de motivation dans laquelle vous vous presentez, expliquez vos competences et votre motivation. (160-180 mots)",
        "min_words": 160,
        "max_words": 180,
        "time_limit_minutes": 30,
    },

    # ── B2 (4 prompts) ────────────────────────────────────────────
    {
        "level": "B2",
        "theme": "Technologie",
        "prompt_type": "argumentative",
        "prompt_text": "L'intelligence artificielle represente-t-elle une menace ou une opportunite pour le marche du travail ? Presentez les deux points de vue et donnez votre opinion personnelle argumentee. (250-300 mots)",
        "min_words": 250,
        "max_words": 300,
        "time_limit_minutes": 45,
    },
    {
        "level": "B2",
        "theme": "Environnement",
        "prompt_type": "formal_letter",
        "prompt_text": "En tant que resident de votre quartier, ecrivez une lettre au maire pour proposer des mesures concretes afin de reduire la pollution et ameliorer la qualite de vie. Structurez votre lettre de maniere formelle. (250-300 mots)",
        "min_words": 250,
        "max_words": 300,
        "time_limit_minutes": 45,
    },
    {
        "level": "B2",
        "theme": "Culture",
        "prompt_type": "essay",
        "prompt_text": "Les reseaux sociaux ont-ils transforme notre rapport a la culture et a l'art ? Analysez les effets positifs et negatifs de cette evolution en vous appuyant sur des exemples precis. (250-300 mots)",
        "min_words": 250,
        "max_words": 300,
        "time_limit_minutes": 45,
    },
    {
        "level": "B2",
        "theme": "Societe",
        "prompt_type": "argumentative",
        "prompt_text": "Le teletravail devrait-il devenir la norme dans les entreprises ? Discutez les avantages et les limites de ce mode de travail en prenant position de maniere argumentee. (250-300 mots)",
        "min_words": 250,
        "max_words": 300,
        "time_limit_minutes": 45,
    },

    # ── B1 (3 new prompts) ─────────────────────────────────────────
    {
        "level": "B1",
        "theme": "Société",
        "prompt_type": "opinion_essay",
        "prompt_text": "L'argent fait-il le bonheur ? Qu'en pensez-vous ?",
        "min_words": 150,
        "max_words": 200,
        "time_limit_minutes": 30,
    },
    {
        "level": "B1",
        "theme": "Technologie",
        "prompt_type": "argumentative",
        "prompt_text": "Les enfants passent-ils trop de temps devant les écrans ?",
        "min_words": 150,
        "max_words": 200,
        "time_limit_minutes": 30,
    },
    {
        "level": "B1",
        "theme": "Santé",
        "prompt_type": "argumentative",
        "prompt_text": "Comment inciter les gens à faire davantage de sport ?",
        "min_words": 150,
        "max_words": 200,
        "time_limit_minutes": 30,
    },

    # ── B2 (3 new prompts) ─────────────────────────────────────────
    {
        "level": "B2",
        "theme": "Technologie",
        "prompt_type": "argumentative",
        "prompt_text": "Les réseaux sociaux rendent-ils les gens solitaires, ou permettent-ils de créer des liens ?",
        "min_words": 200,
        "max_words": 250,
        "time_limit_minutes": 45,
    },
    {
        "level": "B2",
        "theme": "Société",
        "prompt_type": "argumentative",
        "prompt_text": "Vivre en ville est plus stressant qu'à la campagne. Êtes-vous d'accord ?",
        "min_words": 200,
        "max_words": 250,
        "time_limit_minutes": 45,
    },
    {
        "level": "B2",
        "theme": "Technologie",
        "prompt_type": "argumentative",
        "prompt_text": "Peut-on vivre sans technologie ?",
        "min_words": 200,
        "max_words": 250,
        "time_limit_minutes": 45,
    },

    # ── C1 (4 prompts) ────────────────────────────────────────────
    {
        "level": "C1",
        "theme": "Societe",
        "prompt_type": "argumentative",
        "prompt_text": "Dans quelle mesure la liberte d'expression doit-elle etre limitee dans une democratie ? Appuyez votre reflexion sur des exemples precis et proposez une synthese nuancee de la question. (350-400 mots)",
        "min_words": 350,
        "max_words": 400,
        "time_limit_minutes": 60,
    },
    {
        "level": "C1",
        "theme": "Education",
        "prompt_type": "essay",
        "prompt_text": "Le systeme educatif actuel prepare-t-il adequatement les jeunes aux defis du XXIe siecle ? Analysez les forces et les faiblesses du modele educatif et proposez des pistes de reforme argumentees. (350-400 mots)",
        "min_words": 350,
        "max_words": 400,
        "time_limit_minutes": 60,
    },
    {
        "level": "C1",
        "theme": "Environnement",
        "prompt_type": "formal_letter",
        "prompt_text": "En tant que representant d'une association ecologiste, redigez une lettre ouverte a la presse dans laquelle vous denoncez l'inaction des gouvernements face au changement climatique et proposez un programme d'action concret. (350-400 mots)",
        "min_words": 350,
        "max_words": 400,
        "time_limit_minutes": 60,
    },
    {
        "level": "C1",
        "theme": "Technologie",
        "prompt_type": "essay",
        "prompt_text": "La surveillance numerique est-elle compatible avec les valeurs democratiques ? A travers une analyse des enjeux ethiques, politiques et sociaux, developpez une argumentation structuree sur cette question. (350-400 mots)",
        "min_words": 350,
        "max_words": 400,
        "time_limit_minutes": 60,
    },
]


if __name__ == "__main__":
    added = 0
    for p in PROMPTS:
        exists = db.query(WritingPrompt).filter(
            WritingPrompt.prompt_text == p["prompt_text"]
        ).first()
        if not exists:
            db.add(WritingPrompt(**p))
            added += 1
    db.commit()
    total = db.query(WritingPrompt).count()
    print(f"Added {added} new writing prompts. Total: {total}")

    # Report per level
    for level in ["B1", "B2", "C1"]:
        count = db.query(WritingPrompt).filter(WritingPrompt.level == level).count()
        print(f"  {level}: {count} prompts")
    db.close()
