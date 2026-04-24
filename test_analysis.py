"""
Test script — sends a sample transcription through the analysis pipeline
and verifies the response follows the new rules.

Usage: python test_analysis.py
"""
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.services.analysis import analyze_transcript


SAMPLE_TRANSCRIPT = """
alors je pense que la technologie a beaucoup changé notre vie quotidienne
par exemple maintenant on peut travailler de la maison et je pense que
c'est très important pour les gens parce que ça leur permet d'avoir
plus de temps avec leur famille mais en même temps je pense que
il y a des problèmes avec la technologie parce que les gens sont
trop dépendant sur leurs téléphones et ils ne peuvent pas déconnecter
donc je pense que c'est important de trouver un bon balance entre
la technologie et la vie réelle
"""

SAMPLE_TOPIC = "La technologie a-t-elle amélioré notre qualité de vie ?"


async def main():
    print("=" * 60)
    print("FluentPath Analysis Pipeline Test")
    print("=" * 60)

    from app.config import settings
    if not settings.ANTHROPIC_API_KEY:
        print("\n[SKIP] No ANTHROPIC_API_KEY set — running demo mode only")
        result = await analyze_transcript(
            transcript=SAMPLE_TRANSCRIPT.strip(),
            topic=SAMPLE_TOPIC,
            target_level="B2",
            ui_language="en",
        )
        print("\n[DEMO] Response keys:", list(result.keys()))
        print("[DEMO] Score:", result.get("note_globale"))
        return

    print(f"\nAPI Key: {'*' * 8}...{settings.ANTHROPIC_API_KEY[-6:]}")
    print(f"Transcript: {len(SAMPLE_TRANSCRIPT.split())} words")
    print(f"Topic: {SAMPLE_TOPIC}")
    print(f"Level: B2")
    print("\nSending to Claude API...")

    result = await analyze_transcript(
        transcript=SAMPLE_TRANSCRIPT.strip(),
        topic=SAMPLE_TOPIC,
        target_level="B2",
        ui_language="en",
        low_confidence_words=[
            {"text": "dépendant", "confidence": 0.52},
            {"text": "balance", "confidence": 0.61},
        ],
    )

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    # Check structure
    print(f"\n1. Score: {result.get('note_globale', 'MISSING')}/20")

    carte = result.get("la_carte", {})
    print(f"2. La Carte:")
    for k, v in carte.items():
        print(f"   - {k}: {v}/5")

    goulet = result.get("le_goulet", {})
    print(f"3. Goulet: Couche {goulet.get('couche')} — {goulet.get('nom')}")
    print(f"   → {goulet.get('explication', '')[:120]}...")

    print(f"4. Ce qui marche (first 200 chars):")
    print(f"   {result.get('ce_qui_marche', '')[:200]}")

    # Verify corrections
    corrections = result.get("corrections", [])
    print(f"\n5. Corrections ({len(corrections)}):")
    homophone_flags = 0
    for c in corrections:
        has_segments = "changed_segments" in c
        print(f"   [{c.get('nom_couche')}] {c.get('original', '')[:60]}")
        print(f"     → {c.get('corrige', '')[:60]}")
        print(f"     has changed_segments: {has_segments}")
        # Check for homophone-only corrections
        orig = c.get("original", "").lower().replace(" ", "")
        fix = c.get("corrige", "").lower().replace(" ", "")
        if orig == fix:
            homophone_flags += 1
            print(f"     ⚠️ HOMOPHONE-ONLY CORRECTION (should be filtered)")

    if homophone_flags:
        print(f"\n   ⚠️ {homophone_flags} homophone-only corrections found — these should be filtered out!")
    else:
        print(f"\n   ✓ No homophone-only corrections — rule working correctly")

    # Check English Habits
    reflexes = result.get("reflexes_detectes", [])
    print(f"\n6. English Habits detected: {reflexes}")

    # Check ordonnance format
    ordo = result.get("ordonnance", {})
    exs = ordo.get("exercices", [])
    print(f"\n7. Exercises ({len(exs)}):")
    for ex in exs[:3]:
        print(f"   #{ex.get('numero')} [{ex.get('type')}]")
        if "options" in ex:
            print(f"     Model: {ex.get('modele', 'MISSING')[:60]}")
            print(f"     Phrase: {ex.get('phrase', 'MISSING')}")
            print(f"     Options: {ex.get('options')}")
            print(f"     ✓ Multiple-choice format")
        else:
            print(f"     ⚠️ Missing options — old format?")

    # Check pronunciation
    pronon = result.get("prononciation", {})
    print(f"\n8. Pronunciation score: {pronon.get('score', 'MISSING')}/5")
    for w in pronon.get("mots_problematiques", []):
        print(f"   - {w.get('mot')} ({w.get('type')}) conf={w.get('confidence')}")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
