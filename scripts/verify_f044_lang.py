"""F-044 verification: call Claude with ui_language=fr to confirm next_step,
transformation, and (writing) explanation fields are generated in French.
"""
import asyncio, json, sys
from app.services.analysis import analyze_transcript
from app.services.writing_analysis import analyze_writing

TEST_TRANSCRIPT = (
    "Je pense que la technologie est une chose importante. Je pense que les "
    "gens dépendent sur leurs téléphones. Par exemple, ma mère elle utilise "
    "son téléphone tous les jours. C'est une chose qui est très utile."
)
TEST_TOPIC = "Pensez-vous que la technologie a plus d'effets positifs ou négatifs ?"

TEST_WRITING = (
    "Je pense que les réseaux sociaux ont beaucoup changé notre vie. Ils "
    "sont une chose importante pour les jeunes. Par exemple, ma soeur elle "
    "utilise Instagram tous les jours. Mais il y a aussi des problèmes. Les "
    "gens passent trop de temps sur les écrans et ça dépend sur comment ils "
    "organisent leur journée. En conclusion, je pense que les réseaux sociaux "
    "ont des bons et des mauvais côtés."
)


async def main() -> int:
    lang = sys.argv[1] if len(sys.argv) > 1 else "fr"
    skill = sys.argv[2] if len(sys.argv) > 2 else "oral"
    print(f"=== calling Claude with ui_language={lang}, skill={skill} ===", file=sys.stderr)
    if skill == "writing":
        result = await analyze_writing(
            student_text=TEST_WRITING,
            prompt_text=TEST_TOPIC,
            prompt_type="essay",
            target_level="B2",
            ui_language=lang,
            exam_profile="tcf_canada",
        )
    else:
        result = await analyze_transcript(
            transcript=TEST_TRANSCRIPT,
            topic=TEST_TOPIC,
            target_level="B2",
            ui_language=lang,
            low_confidence_words=[],
            exam_profile="tcf_canada",
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
