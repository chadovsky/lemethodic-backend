"""F-032 verification harness — hit the real Claude API and dump the raw
response so we can judge whether examiner and teacher voices are distinct.

Not a UI test. Calls analyze_transcript() directly with a canned B2
anglophone transcript containing the typical failure modes the dual-
channel prompt is supposed to catch (je-pense loop, chose/truc fillers,
preposition calques, flat SVO, no subordination).
"""
import asyncio
import json
import sys

from app.services.analysis import analyze_transcript

# Deliberately laden with anglophone weak points Claude should catch:
# - "je pense que" repeated 4+ times (boucle_je_pense)
# - "chose" / "truc" used as filler nouns (lexical_range red flag)
# - "dépendent sur" (English preposition transfer)
# - Flat SVO, no subordination, no thèse-antithèse
# - "c'est ... qui" overuse
TEST_TRANSCRIPT = (
    "Je pense que la technologie est une chose importante dans notre "
    "société. Je pense que les gens dépendent sur leurs téléphones tous "
    "les jours. Par exemple, ma mère elle utilise son téléphone pour "
    "parler avec la famille. C'est un truc qui est très utile. Mais je "
    "pense aussi que la technologie a beaucoup de problèmes. Les enfants "
    "passent beaucoup de temps sur les écrans. C'est une chose qui "
    "m'inquiète. En conclusion, je pense que la technologie c'est bon "
    "mais il faut être prudent."
)

TEST_TOPIC = (
    "Pensez-vous que la technologie a plus d'effets positifs ou négatifs "
    "sur la société moderne ? Justifiez votre position."
)


async def main() -> int:
    print("Calling analyze_transcript with B2 test input...", file=sys.stderr)
    result = await analyze_transcript(
        transcript=TEST_TRANSCRIPT,
        topic=TEST_TOPIC,
        target_level="B2",
        ui_language="en",
        low_confidence_words=[],
        exam_profile="tcf_canada",
    )
    # Full dump (raw_response) + focused dual-channel view for review
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
