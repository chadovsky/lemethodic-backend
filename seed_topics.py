"""Run once to seed TCF topics: py seed_topics.py"""
from app.database import SessionLocal, engine, Base
from app.models.models import TestTopic

Base.metadata.create_all(bind=engine)
db = SessionLocal()

TOPICS = [
    # TECHNOLOGIE
    ("Les réseaux sociaux rendent-ils les gens plus solitaires ?", "Technologie", "Réseaux sociaux"),
    ("Faut-il interdire les téléphones portables dans les écoles ?", "Technologie", "Téléphones"),
    ("L'intelligence artificielle va-t-elle remplacer les emplois humains ?", "Technologie", "Intelligence artificielle"),
    ("Internet a-t-il amélioré la qualité de l'information ?", "Technologie", "Internet"),
    ("Les jeux vidéo ont-ils une influence négative sur les jeunes ?", "Technologie", "Jeux vidéo"),
    ("Le télétravail est-il bénéfique pour les employés ?", "Technologie", "Télétravail"),
    ("Les robots devraient-ils remplacer les humains dans les tâches dangereuses ?", "Technologie", "Robotique"),
    ("La dépendance aux écrans est-elle un problème de santé publique ?", "Technologie", "Écrans"),
    ("Les achats en ligne menacent-ils le commerce traditionnel ?", "Technologie", "Commerce en ligne"),
    ("Peut-on faire confiance aux informations trouvées sur Internet ?", "Technologie", "Fiabilité de l'information"),
    ("Les nouvelles technologies creusent-elles les inégalités sociales ?", "Technologie", "Inégalités numériques"),
    ("Faut-il réglementer l'usage des drones dans l'espace public ?", "Technologie", "Drones"),

    # SANTÉ
    ("Faut-il interdire la publicité pour la malbouffe ?", "Santé", "Alimentation"),
    ("Le sport devrait-il être obligatoire à l'école ?", "Santé", "Sport"),
    ("La médecine traditionnelle a-t-elle encore sa place aujourd'hui ?", "Santé", "Médecine traditionnelle"),
    ("Faut-il rendre la vaccination obligatoire ?", "Santé", "Vaccination"),
    ("Le stress au travail est-il inévitable ?", "Santé", "Stress"),
    ("Les régimes alimentaires à la mode sont-ils dangereux ?", "Santé", "Régimes"),
    ("Devrait-on interdire la vente de tabac ?", "Santé", "Tabac"),
    ("La santé mentale est-elle suffisamment prise en compte dans nos sociétés ?", "Santé", "Santé mentale"),
    ("L'automédication est-elle un danger pour la santé publique ?", "Santé", "Automédication"),
    ("Les fast-foods devraient-ils être interdits à proximité des écoles ?", "Santé", "Restauration rapide"),
    ("Le bien-être au travail devrait-il être une obligation légale ?", "Santé", "Bien-être"),
    ("La chirurgie esthétique est-elle un choix personnel ou un problème de société ?", "Santé", "Chirurgie esthétique"),

    # ÉDUCATION
    ("L'université devrait-elle être gratuite pour tous ?", "Éducation", "Coût des études"),
    ("Les notes sont-elles un bon moyen d'évaluer les élèves ?", "Éducation", "Évaluation"),
    ("L'apprentissage des langues étrangères devrait-il commencer dès la maternelle ?", "Éducation", "Langues"),
    ("Les devoirs à la maison sont-ils utiles ?", "Éducation", "Devoirs"),
    ("Faut-il enseigner le codage informatique dès l'école primaire ?", "Éducation", "Numérique"),
    ("L'éducation en ligne peut-elle remplacer l'école traditionnelle ?", "Éducation", "Éducation en ligne"),
    ("Les uniformes scolaires favorisent-ils l'égalité entre les élèves ?", "Éducation", "Uniformes"),
    ("Le redoublement est-il une solution efficace ?", "Éducation", "Redoublement"),
    ("Les études supérieures garantissent-elles un bon emploi ?", "Éducation", "Emploi"),
    ("L'éducation artistique est-elle aussi importante que les matières scientifiques ?", "Éducation", "Arts"),
    ("Les parents devraient-ils avoir le droit de faire l'école à la maison ?", "Éducation", "École à la maison"),
    ("La mixité sociale dans les écoles est-elle réalisable ?", "Éducation", "Mixité"),

    # ENVIRONNEMENT
    ("Le réchauffement climatique est-il la plus grande menace pour l'humanité ?", "Environnement", "Climat"),
    ("Faut-il interdire les voitures dans les centres-villes ?", "Environnement", "Transport"),
    ("Le nucléaire est-il une énergie d'avenir ?", "Environnement", "Énergie nucléaire"),
    ("Les individus peuvent-ils vraiment changer le monde par leurs habitudes de consommation ?", "Environnement", "Consommation responsable"),
    ("Faut-il imposer une taxe carbone aux entreprises polluantes ?", "Environnement", "Taxe carbone"),
    ("Le tri sélectif est-il suffisant pour résoudre le problème des déchets ?", "Environnement", "Déchets"),
    ("Devrait-on interdire les emballages plastiques ?", "Environnement", "Plastique"),
    ("Les pays riches ont-ils une responsabilité particulière face au changement climatique ?", "Environnement", "Responsabilité"),
    ("L'agriculture biologique peut-elle nourrir toute la planète ?", "Environnement", "Agriculture"),
    ("Faut-il limiter les voyages en avion pour protéger l'environnement ?", "Environnement", "Aviation"),
    ("Les villes du futur seront-elles plus écologiques ?", "Environnement", "Urbanisme"),
    ("La déforestation peut-elle être stoppée ?", "Environnement", "Forêts"),

    # SOCIÉTÉ
    ("L'égalité hommes-femmes est-elle atteinte dans votre pays ?", "Société", "Égalité des genres"),
    ("Le bénévolat devrait-il être obligatoire ?", "Société", "Bénévolat"),
    ("La peine de mort est-elle justifiable ?", "Société", "Justice"),
    ("L'immigration est-elle une chance ou un problème pour les pays d'accueil ?", "Société", "Immigration"),
    ("La liberté d'expression a-t-elle des limites ?", "Société", "Liberté d'expression"),
    ("Le mariage est-il encore une institution pertinente ?", "Société", "Mariage"),
    ("Les personnes âgées sont-elles suffisamment respectées dans nos sociétés ?", "Société", "Personnes âgées"),
    ("La pauvreté est-elle une fatalité ?", "Société", "Pauvreté"),
    ("Les médias influencent-ils trop l'opinion publique ?", "Société", "Médias"),
    ("Le vote devrait-il être obligatoire ?", "Société", "Vote"),
    ("La solidarité entre générations est-elle en déclin ?", "Société", "Solidarité"),
    ("Les inégalités de revenus sont-elles acceptables dans une démocratie ?", "Société", "Inégalités"),

    # CULTURE & LOISIRS
    ("La lecture est-elle menacée par les écrans ?", "Culture & Loisirs", "Lecture"),
    ("Le tourisme de masse détruit-il les sites qu'il prétend célébrer ?", "Culture & Loisirs", "Tourisme"),
    ("Les musées devraient-ils être gratuits ?", "Culture & Loisirs", "Musées"),
    ("La mode influence-t-elle trop le comportement des jeunes ?", "Culture & Loisirs", "Mode"),
    ("Les films et séries reflètent-ils la réalité sociale ?", "Culture & Loisirs", "Cinéma"),
    ("Le sport professionnel est-il trop commercialisé ?", "Culture & Loisirs", "Sport professionnel"),
    ("Les festivals culturels contribuent-ils au développement local ?", "Culture & Loisirs", "Festivals"),
    ("La gastronomie fait-elle partie de l'identité culturelle d'un pays ?", "Culture & Loisirs", "Gastronomie"),
    ("Les loisirs créatifs sont-ils importants pour l'épanouissement personnel ?", "Culture & Loisirs", "Loisirs créatifs"),
    ("La musique traditionnelle a-t-elle encore un avenir ?", "Culture & Loisirs", "Musique"),
    ("Le patrimoine architectural doit-il être préservé à tout prix ?", "Culture & Loisirs", "Patrimoine"),
    ("Les voyages forment-ils vraiment la jeunesse ?", "Culture & Loisirs", "Voyages"),

    # TRAVAIL & ÉCONOMIE
    ("Le salaire minimum devrait-il être augmenté ?", "Travail & Économie", "Salaire"),
    ("L'entrepreneuriat est-il accessible à tous ?", "Travail & Économie", "Entrepreneuriat"),
    ("La semaine de quatre jours est-elle réaliste ?", "Travail & Économie", "Organisation du travail"),
    ("Les stages non rémunérés sont-ils acceptables ?", "Travail & Économie", "Stages"),
    ("La mondialisation profite-t-elle à tout le monde ?", "Travail & Économie", "Mondialisation"),
    ("Faut-il un revenu universel ?", "Travail & Économie", "Revenu universel"),
    ("Les syndicats ont-ils encore un rôle à jouer ?", "Travail & Économie", "Syndicats"),
    ("Le commerce équitable change-t-il vraiment les choses ?", "Travail & Économie", "Commerce équitable"),
    ("La publicité est-elle un art ou une manipulation ?", "Travail & Économie", "Publicité"),
    ("Les métiers manuels sont-ils suffisamment valorisés ?", "Travail & Économie", "Métiers manuels"),
    ("La retraite à 65 ans est-elle encore adaptée ?", "Travail & Économie", "Retraite"),
    ("Le bonheur au travail est-il une utopie ?", "Travail & Économie", "Bonheur au travail"),
]

count = 0
for title, theme, sous_theme in TOPICS:
    existing = db.query(TestTopic).filter(TestTopic.title == title).first()
    if not existing:
        topic = TestTopic(title=title, theme=theme, sous_theme=sous_theme)
        db.add(topic)
        count += 1

db.commit()
print(f"Seeded {count} new topics ({len(TOPICS)} total in catalog)")
print(f"Themes: {len(set(t[1] for t in TOPICS))}")
