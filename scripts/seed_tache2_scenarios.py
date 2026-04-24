"""F-049 — Seed the Tâche 2 scenario catalog with the 5 situations from
Yarden Livraison 1.

Every brief, persona, and data_targets entry below is a placeholder that
Chadi replaces before Day 7 with the authored text from the Yarden
documents. The placeholders are structurally complete so the full end-
to-end flow works today (pick scenario → brief → conversation →
analysis), but the copy will read as generic until the swap.

Placeholder markers:
    # CHADI: replace with your real brief from Yarden Livraison 1
    # CHADI: replace before Day 7
    # CHADI: validate or revise

Idempotency: runs match by ``code``. Re-running is safe; it updates the
same rows in place rather than duplicating.

Usage from project root:
    python -m scripts.seed_tache2_scenarios
"""
from __future__ import annotations

import json
import sys

from app.database import SessionLocal
from app.models.models import Tache2Scenario


# ═══════════════════════════════════════════════════════════════
# Scenario payloads — PLACEHOLDERS. Replace before Day 7.
# ═══════════════════════════════════════════════════════════════

SCENARIOS: list[dict] = [
    {
        "code": "ami_demenagement",
        "title_fr": "L'ami qui déménage",
        "title_en": "The friend who's moving",
        "title_es": "El amigo que se muda",
        # CHADI: replace with your real brief from Yarden Livraison 1, scenario 1
        "candidate_brief_fr": (
            "Un(e) ami(e) proche vient de vous annoncer qu'il/elle déménage dans une autre ville. "
            "Vous voulez en savoir plus sur les raisons, le timing, le logement, et comment vous allez "
            "rester en contact. Posez-lui des questions naturelles, sur un ton amical. L'échange doit "
            "ressembler à une vraie conversation entre amis."
        ),
        # CHADI: replace with your real brief from Yarden Livraison 1, scenario 1
        "candidate_brief_en": (
            "A close friend has just told you they're moving to another city. You want to find out "
            "more about the reasons, timing, their new place, and how you'll stay in touch. Ask "
            "them natural questions in a friendly tone. The exchange should feel like a real "
            "conversation between friends."
        ),
        # CHADI: replace with your real brief from Yarden Livraison 1, scenario 1
        "candidate_brief_es": (
            "Un(a) amigo(a) cercano(a) acaba de decirte que se muda a otra ciudad. Quieres saber "
            "más sobre las razones, el momento, la vivienda, y cómo se mantendrán en contacto. "
            "Hazle preguntas naturales en un tono amistoso. El intercambio debe sentirse como una "
            "conversación real entre amigos."
        ),
        # CHADI: replace before Day 7
        "examiner_persona": (
            "You are Alex, a close friend of the candidate. You've just decided to move from your "
            "current city to another one (pick a plausible French city such as Lyon, Bordeaux or "
            "Nantes and stay consistent). You have concrete reasons (job, family, relationship, or "
            "a fresh start — pick one and stick with it). You use TU with the candidate. Your tone "
            "is warm and casual — you'd say 'ouais', 'genre', 'tu vois' — but not caricature. Keep "
            "answers short and conversational (1-2 sentences). Never volunteer information the "
            "candidate didn't ask for."
        ),
        # CHADI: validate or revise
        "data_targets": [
            "ville de destination",
            "raison du déménagement",
            "date prévue",
            "type de logement",
            "plan pour rester en contact",
        ],
        "register": "informel",
        "difficulty": "A2_B1",
        "seeded_from": "yarden_doc_livraison_1",
    },
    {
        "code": "agence_voyages",
        "title_fr": "L'agence de voyages",
        "title_en": "The travel agency",
        "title_es": "La agencia de viajes",
        # CHADI: replace with your real brief from Yarden Livraison 1, scenario 2
        "candidate_brief_fr": (
            "Vous entrez dans une agence de voyages à Paris pour organiser des vacances d'une "
            "semaine. Vous n'avez pas de destination précise en tête. Votre budget est limité et "
            "vous voyagez avec votre famille. Posez des questions à l'agent(e) pour comparer les "
            "options et choisir le voyage qui vous convient. Registre formel."
        ),
        # CHADI: replace with your real brief from Yarden Livraison 1, scenario 2
        "candidate_brief_en": (
            "You walk into a travel agency in Paris to plan a week-long holiday. You don't have a "
            "specific destination in mind. Your budget is tight and you're travelling with your "
            "family. Ask the agent questions to compare options and pick a trip that fits. Formal "
            "register."
        ),
        # CHADI: replace with your real brief from Yarden Livraison 1, scenario 2
        "candidate_brief_es": (
            "Entras en una agencia de viajes en París para planear unas vacaciones de una semana. "
            "No tienes un destino específico en mente. Tu presupuesto es limitado y viajas con tu "
            "familia. Haz preguntas al agente para comparar opciones y elegir el viaje que más te "
            "convenga. Registro formal."
        ),
        # CHADI: replace before Day 7
        "examiner_persona": (
            "You are a French travel agent at a high-street agency in Paris. You VOUS the client. "
            "Your tone is professional and friendly but not effusive. You have a catalog of 3-4 "
            "plausible destinations across budget levels (improvise consistent prices, durations, "
            "types of accommodation, and included activities). Keep answers factual and short — "
            "1-2 sentences max. Never upsell; never volunteer a package the client didn't ask about."
        ),
        # CHADI: validate or revise
        "data_targets": [
            "destinations disponibles",
            "prix",
            "durée du séjour",
            "type d'hébergement",
            "activités incluses",
            "modalités de paiement",
        ],
        "register": "formel",
        "difficulty": "A2_B1",
        "seeded_from": "yarden_doc_livraison_1",
    },
    {
        "code": "bibliotheque",
        "title_fr": "La bibliothèque",
        "title_en": "The library",
        "title_es": "La biblioteca",
        # CHADI: replace with your real brief from Yarden Livraison 1, scenario 3
        "candidate_brief_fr": (
            "Vous êtes nouveau/nouvelle dans une ville française et vous voulez vous inscrire à la "
            "bibliothèque municipale. Vous ne connaissez pas encore les règles (inscription, prêt, "
            "horaires, services). Demandez à l'employé(e) les informations dont vous avez besoin. "
            "Registre semi-formel."
        ),
        # CHADI: replace with your real brief from Yarden Livraison 1, scenario 3
        "candidate_brief_en": (
            "You're new to a French town and want to sign up at the city library. You don't know "
            "the rules yet (registration, borrowing, opening hours, services). Ask the staff "
            "member for the information you need. Semi-formal register."
        ),
        # CHADI: replace with your real brief from Yarden Livraison 1, scenario 3
        "candidate_brief_es": (
            "Eres nuevo(a) en una ciudad francesa y quieres inscribirte en la biblioteca "
            "municipal. Aún no conoces las reglas (inscripción, préstamo, horarios, servicios). "
            "Pregunta a la persona del mostrador lo que necesitas saber. Registro semi-formal."
        ),
        # CHADI: replace before Day 7
        "examiner_persona": (
            "You are a French public librarian at the information desk. You VOUS the visitor (semi-"
            "formel: polite but not stiff). You know the library's rules: registration requires "
            "proof of address, the annual fee is modest, borrowing limits are reasonable, opening "
            "hours run Tuesday through Saturday. Improvise plausible specifics and stay consistent. "
            "Short, factual answers. Never hand over a pamphlet of information up front."
        ),
        # CHADI: validate or revise
        "data_targets": [
            "documents requis pour l'inscription",
            "coût de l'abonnement",
            "durée du prêt",
            "nombre de livres empruntables",
            "horaires d'ouverture",
            "services numériques disponibles",
        ],
        "register": "semi_formel",
        "difficulty": "A2_B1",
        "seeded_from": "yarden_doc_livraison_1",
    },
    {
        "code": "nouveau_collegue_quebecois",
        "title_fr": "Le nouveau collègue québécois",
        "title_en": "The new Quebecois colleague",
        "title_es": "El nuevo colega quebequense",
        # CHADI: replace with your real brief from Yarden Livraison 1, scenario 4
        "candidate_brief_fr": (
            "Un nouveau collègue vient d'arriver dans votre bureau. Il est québécois et a "
            "déménagé au Canada depuis peu pour un poste similaire au vôtre. Vous voulez faire "
            "connaissance pendant la pause café : parcours, vie au Québec, différences de "
            "culture de travail, vie personnelle. Registre informel — c'est un collègue."
        ),
        # CHADI: replace with your real brief from Yarden Livraison 1, scenario 4
        "candidate_brief_en": (
            "A new colleague has just joined your office. He's from Quebec and recently moved to "
            "Canada for a role similar to yours. You want to get to know him over coffee: his "
            "background, life in Quebec, work-culture differences, personal life. Informal "
            "register — he's a peer."
        ),
        # CHADI: replace with your real brief from Yarden Livraison 1, scenario 4
        "candidate_brief_es": (
            "Un nuevo colega acaba de llegar a tu oficina. Es quebequense y se mudó recientemente "
            "a Canadá para un puesto similar al tuyo. Quieres conocerlo durante el café: su "
            "trayectoria, la vida en Quebec, diferencias culturales en el trabajo, vida personal. "
            "Registro informal — es un colega."
        ),
        # CHADI: replace before Day 7
        "examiner_persona": (
            "You are Mathieu, a Québécois software engineer in his early 30s who just moved to "
            "the candidate's company from Montreal. You TU the candidate (informal, Quebec-style). "
            "You can drop light québécismes ('là', 'pantoute', 'tiguidou') but stay understandable "
            "to a non-Quebec speaker. You have a plausible backstory: grew up in the Laurentides, "
            "studied at l'Université de Montréal, worked at a tech company there for 4 years "
            "before this move. Family and hobbies: improvise, stay consistent. Short answers, "
            "never volunteer chunks."
        ),
        # CHADI: validate or revise
        "data_targets": [
            "parcours professionnel",
            "raison du déménagement",
            "différences travail Canada / Québec",
            "vie personnelle / famille",
            "loisirs ou hobbies",
            "expérience de l'arrivée au pays",
        ],
        "register": "informel",
        "difficulty": "B1_B2",
        "seeded_from": "yarden_doc_livraison_1",
    },
    {
        "code": "agence_immobiliere_canada",
        "title_fr": "L'agence immobilière au Canada",
        "title_en": "The real estate agency in Canada",
        "title_es": "La inmobiliaria en Canadá",
        # CHADI: replace with your real brief from Yarden Livraison 1, scenario 5
        "candidate_brief_fr": (
            "Vous préparez votre installation au Canada et vous avez rendez-vous avec un(e) "
            "agent(e) immobilier(ère) à Montréal pour trouver un appartement en location. Vous "
            "voulez comprendre le marché, les quartiers, les coûts réels (loyer + charges + "
            "taxes), les modalités de bail et les pièges à éviter pour un nouvel arrivant. "
            "Registre formel."
        ),
        # CHADI: replace with your real brief from Yarden Livraison 1, scenario 5
        "candidate_brief_en": (
            "You're preparing to move to Canada and you have an appointment with a real estate "
            "agent in Montreal to find a rental apartment. You want to understand the market, "
            "the neighbourhoods, the true costs (rent + utilities + taxes), lease terms, and "
            "newcomer pitfalls. Formal register."
        ),
        # CHADI: replace with your real brief from Yarden Livraison 1, scenario 5
        "candidate_brief_es": (
            "Preparas tu mudanza a Canadá y tienes una cita con un(a) agente inmobiliario(a) en "
            "Montreal para encontrar un apartamento en alquiler. Quieres entender el mercado, "
            "los barrios, los costes reales (alquiler + gastos + impuestos), las condiciones del "
            "contrato, y los errores típicos del recién llegado. Registro formal."
        ),
        # CHADI: replace before Day 7
        "examiner_persona": (
            "You are a real estate agent in Montreal specializing in newcomer rentals. You VOUS "
            "the client. Your tone is professional, patient, and precise — you deal with "
            "immigrants constantly and know the questions they forget to ask. You know the "
            "landscape: 3-4 neighbourhoods (Plateau, Rosemont, Villeray, Côte-des-Neiges), "
            "plausible rental ranges for a 3½ or 4½ in 2026 CAD, standard Québec lease terms "
            "(bail de 12 mois, Régie du logement, garantie de loyer pratices), and newcomer "
            "pitfalls (credit check substitutes, guarantors, Hydro contract timing). Factual, "
            "one-two sentences. Never give a lecture."
        ),
        # CHADI: validate or revise
        "data_targets": [
            "quartiers recommandés pour un nouvel arrivant",
            "fourchette de loyer pour un 3½ ou 4½",
            "charges comprises / exclues (Hydro, chauffage, internet)",
            "durée standard du bail",
            "garanties exigées (dossier de crédit, garant)",
            "taxe scolaire / taxes municipales",
            "pièges fréquents pour les nouveaux arrivants",
        ],
        "register": "formel",
        "difficulty": "B1_B2",
        "seeded_from": "yarden_doc_livraison_1",
    },
]


def _apply_row(session, payload: dict) -> str:
    """Upsert by code. Returns 'inserted' or 'updated'."""
    existing = (
        session.query(Tache2Scenario)
        .filter(Tache2Scenario.code == payload["code"])
        .first()
    )
    fields = {
        "title_fr": payload["title_fr"],
        "title_en": payload["title_en"],
        "title_es": payload["title_es"],
        "candidate_brief_fr": payload["candidate_brief_fr"],
        "candidate_brief_en": payload["candidate_brief_en"],
        "candidate_brief_es": payload["candidate_brief_es"],
        "examiner_persona": payload["examiner_persona"],
        "data_targets": json.dumps(payload["data_targets"], ensure_ascii=False),
        "register": payload["register"],
        "difficulty": payload["difficulty"],
        "seeded_from": payload["seeded_from"],
        "is_active": True,
    }
    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
        return "updated"
    session.add(Tache2Scenario(code=payload["code"], **fields))
    return "inserted"


def main() -> int:
    session = SessionLocal()
    try:
        counts = {"inserted": 0, "updated": 0}
        for payload in SCENARIOS:
            counts[_apply_row(session, payload)] += 1
        session.commit()
        print(
            f"Seeded Tâche 2 scenarios: "
            f"{counts['inserted']} inserted, {counts['updated']} updated. "
            f"(Placeholders — Chadi replaces before Day 7.)"
        )
        return 0
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
