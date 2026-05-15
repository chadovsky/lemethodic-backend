"""
Diagnostic harness for the DBnary streaming parser.

Run with: python -m tests.diagnose_dbnary <ttl_path>

Reports:
- Number of subject blocks split out by _iter_subject_blocks
- Sample blocks (first 3)
- How many blocks pass _block_is_interesting
- Parse-error count + first 3 error samples
- After-parse cache sizes (entries / forms / senses / translations)
- How many entries produce a non-None chunk and why None for the rest
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure data-layer/ is on sys.path so `scripts.*` imports resolve.
HERE = Path(__file__).resolve().parent
DATA_LAYER = HERE.parent
sys.path.insert(0, str(DATA_LAYER))

from scripts.ingest.dbnary import (  # noqa: E402
    _absorb_triple,
    _block_is_interesting,
    _build_chunk,
    _iter_subject_blocks,
    _split_prefix_preamble,
)


def diagnose(ttl_path: Path, block_sample_limit: int = 3) -> None:
    print(f"Diagnosing {ttl_path}")
    with open(ttl_path, "r", encoding="utf-8") as f:
        lines = list(f)

    print(f"Total lines read: {len(lines)}")

    prefix_block, body_iter = _split_prefix_preamble(iter(lines))
    print(f"Preamble length: {len(prefix_block)} chars")
    print("--- Preamble (first 500 chars) ---")
    print(prefix_block[:500])
    print("--- /preamble ---")

    from rdflib import Graph  # noqa: PLC0415

    forms: dict[str, str] = {}
    senses: dict[str, dict] = {}
    translations: dict[str, dict] = {}
    entries: dict[str, dict] = {}

    block_count = 0
    interesting_count = 0
    parse_errors = 0
    sample_blocks: list[str] = []
    error_samples: list[str] = []
    type_object_counter: dict[str, int] = {}

    for block_text in _iter_subject_blocks(body_iter):
        block_count += 1
        if block_count <= block_sample_limit:
            sample_blocks.append(block_text)
        if not _block_is_interesting(block_text):
            continue
        interesting_count += 1
        try:
            g = Graph()
            g.parse(data=prefix_block + block_text, format="turtle")
        except Exception as e:  # noqa: BLE001
            parse_errors += 1
            if len(error_samples) < 3:
                error_samples.append(f"{type(e).__name__}: {e}\n--- block ---\n{block_text[:500]}")
            continue

        for s, p, o in g:
            if str(p) == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type":
                k = str(o)
                type_object_counter[k] = type_object_counter.get(k, 0) + 1
            _absorb_triple(str(s), str(p), o, forms, senses, translations, entries)

    print(f"\nblocks={block_count}, interesting={interesting_count}, parse_errors={parse_errors}")
    print(f"entries={len(entries)}, forms={len(forms)}, senses={len(senses)}, translations={len(translations)}")

    print("\n--- Top 15 rdf:type objects observed ---")
    for t, n in sorted(type_object_counter.items(), key=lambda kv: -kv[1])[:15]:
        print(f"  {n:6d}  {t}")

    print("\n--- Sample blocks ---")
    for i, b in enumerate(sample_blocks):
        print(f"[BLOCK {i}]\n{b[:600]}\n")

    if error_samples:
        print("\n--- Parse error samples ---")
        for e in error_samples:
            print(e[:800])
            print("---")

    # Try to build chunks
    built = 0
    none_reasons = {"no_surface": 0}
    for entry_uri, entry in entries.items():
        chunk = _build_chunk(entry, forms, senses, translations)
        if chunk:
            built += 1
        else:
            none_reasons["no_surface"] += 1

    print(f"\nchunks_built={built} (of {len(entries)} entries)")
    print(f"none_reasons={none_reasons}")

    # Print 3 sample entries (raw)
    print("\n--- Sample entries (first 3) ---")
    for i, (uri, entry) in enumerate(list(entries.items())[:3]):
        print(f"[ENTRY {i}] uri={uri}")
        print(f"  {entry}")
        cf = entry.get("canonical_form_uri")
        if cf:
            print(f"  forms.get(canonical_form_uri) = {forms.get(cf)!r}")

    # Print 3 sample senses
    print("\n--- Sample senses (first 3) ---")
    for i, (uri, sense) in enumerate(list(senses.items())[:3]):
        print(f"[SENSE {i}] uri={uri}")
        print(f"  {sense}")

    # Print 3 sample translations
    print("\n--- Sample translations (first 3) ---")
    for i, (uri, tr) in enumerate(list(translations.items())[:3]):
        print(f"[TRANSLATION {i}] uri={uri}")
        print(f"  {tr}")

    # English translation count
    en_trs = [t for t in translations.values() if (t.get("lang") in {"en", "eng"} or t.get("lang_uri") in {"http://lexvo.org/id/iso639-3/eng", "http://lexvo.org/id/iso639-1/en"})]
    print(f"\nEnglish translations cached: {len(en_trs)}")
    if en_trs[:3]:
        for t in en_trs[:3]:
            print(f"  {t}")

    # Sample one entry with English translation resolution
    print("\n--- Resolving English translation for first 3 entries ---")
    from scripts.ingest.dbnary import _resolve_english_translation  # noqa: PLC0415
    for i, (uri, entry) in enumerate(list(entries.items())[:5]):
        result = _resolve_english_translation(entry, senses, translations)
        print(f"  [{i}] {uri} -> {result!r}")


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else (DATA_LAYER / "tests/fixtures/dbnary_slice_5k.ttl")
    diagnose(path)
