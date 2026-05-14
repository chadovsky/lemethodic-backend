"""
Generate a synthetic PARSEME-format .cupt fixture for parser validation.

The real PARSEME French corpus is hosted on GitLab and currently requires
authentication for cloning, so this fixture stands in for end-to-end testing
of scripts/ingest/parseme.py until ops re-runs ingest with credentials.

Output mimics PARSEME 1.3 conventions: CoNLL-U columns + an MWE annotation
in column 11. Exercises every shape the parser must handle:
  - Contiguous MWEs (head + immediately-following continuation)
  - Discontinuous MWEs (continuation tokens with intervening '*' tokens)
  - Multiple MWEs in a single sentence (independent ids)
  - Overlapping MWE annotations on the same token (';' separator)
  - Multi-word token ranges ('1-2') and empty nodes ('1.1') that must be skipped
  - Comment lines and blank-line sentence separators
  - All 8 MWE types from the parser's MWE_TYPE_MAP
"""

from __future__ import annotations

import random
from pathlib import Path

# A pool of (head, continuation_tokens, lemma_head, lemma_continuations, type)
# entries, hand-built to be representative of real French verbal MWEs. The
# parser concatenates surface forms in sentence order, so each pattern below
# yields a recognizable canonical chunk.
def _conjugations(infinitive: str) -> list[str]:
    """
    Return a handful of present + passé-composé + imparfait forms so a single
    MWE pattern can surface as several distinct chunks after dedup. The forms
    are deliberately approximate — the parser doesn't lemmatize, it only joins
    surface tokens, so any plausible-looking inflection works for fixture
    purposes.
    """
    stem = infinitive[:-2] if infinitive.endswith(("er", "ir", "re")) else infinitive
    return [
        infinitive,
        stem + "e",
        stem + "es",
        stem + "ait",
        stem + "aient",
        "a " + (stem + "é" if infinitive.endswith("er") else infinitive),
    ]


_BASE_PATTERNS = [
    # (head_infinitive, [continuations], [cont_lemmas], type)
    ("prendre", ["en", "compte"], ["en", "compte"], "LVC.full"),
    ("faire", ["face", "à"], ["face", "à"], "LVC.full"),
    ("faire", ["partie"], ["partie"], "LVC.full"),
    ("tenir", ["compte"], ["compte"], "LVC.full"),
    ("avoir", ["lieu"], ["lieu"], "LVC.full"),
    ("donner", ["lieu"], ["lieu"], "LVC.cause"),
    ("mettre", ["en", "place"], ["en", "place"], "LVC.full"),
    ("mettre", ["en", "œuvre"], ["en", "œuvre"], "LVC.full"),
    ("mettre", ["fin"], ["fin"], "LVC.cause"),
    ("rendre", ["compte"], ["compte"], "LVC.full"),
    ("rendre", ["hommage"], ["hommage"], "LVC.full"),
    ("porter", ["plainte"], ["plainte"], "LVC.full"),
    ("porter", ["secours"], ["secours"], "LVC.full"),
    ("porter", ["atteinte"], ["atteinte"], "LVC.full"),
    ("apporter", ["soutien"], ["soutien"], "LVC.full"),
    ("livrer", ["bataille"], ["bataille"], "LVC.full"),
    ("subir", ["pression"], ["pression"], "LVC.full"),
    ("exercer", ["pression"], ["pression"], "LVC.full"),
    ("se", ["rendre", "compte"], ["rendre", "compte"], "VID"),
    ("se", ["demander"], ["demander"], "IRV"),
    ("se", ["souvenir"], ["souvenir"], "IRV"),
    ("se", ["plaindre"], ["plaindre"], "IRV"),
    ("se", ["méfier"], ["méfier"], "IRV"),
    ("se", ["taire"], ["taire"], "IRV"),
    ("se", ["évanouir"], ["évanouir"], "IRV"),
    ("se", ["enfuir"], ["enfuir"], "IRV"),
    ("se", ["repentir"], ["repentir"], "IRV"),
    ("casser", ["les", "pieds"], ["le", "pied"], "VID"),
    ("avoir", ["le", "cafard"], ["le", "cafard"], "VID"),
    ("tomber", ["dans", "les", "pommes"], ["dans", "le", "pomme"], "VID"),
    ("battre", ["la", "campagne"], ["le", "campagne"], "VID"),
    ("perdre", ["la", "tête"], ["le", "tête"], "VID"),
    ("monter", ["sur", "ses", "grands", "chevaux"], ["sur", "son", "grand", "cheval"], "VID"),
    ("couper", ["les", "ponts"], ["le", "pont"], "VID"),
    ("avaler", ["la", "pilule"], ["le", "pilule"], "VID"),
    ("brûler", ["la", "chandelle"], ["le", "chandelle"], "VID"),
    ("jeter", ["l'", "éponge"], ["le", "éponge"], "VID"),
    ("prendre", ["la", "mouche"], ["le", "mouche"], "VID"),
    ("rendre", ["l'", "âme"], ["le", "âme"], "VID"),
    ("tirer", ["son", "épingle", "du", "jeu"], ["son", "épingle", "de", "jeu"], "VID"),
    ("manger", ["à", "sa", "faim"], ["à", "son", "faim"], "MVC"),
    ("vivre", ["d'", "amour"], ["de", "amour"], "MVC"),
    ("dormir", ["à", "poings", "fermés"], ["à", "poing", "fermé"], "MVC"),
    ("travailler", ["d'", "arrache-pied"], ["de", "arrache-pied"], "IAV"),
    ("agir", ["à", "tort"], ["à", "tort"], "IAV"),
    ("parler", ["à", "tort", "et", "à", "travers"], ["à", "tort", "et", "à", "travers"], "IAV"),
    ("revenir", ["sur"], ["sur"], "VPC.full"),
    ("tomber", ["sur"], ["sur"], "VPC.semi"),
    ("passer", ["par"], ["par"], "VPC.semi"),
    ("descendre", ["de"], ["de"], "VPC.semi"),
    ("partir", ["pour"], ["pour"], "VPC.semi"),
]


MWE_PATTERNS = []
for _inf, _cont, _cont_lem, _type in _BASE_PATTERNS:
    if _inf == "se":
        # Reflexive: only one surface — the clitic doesn't conjugate the same way.
        MWE_PATTERNS.append((_inf, _cont, _inf, _cont_lem, _type))
        continue
    for _form in _conjugations(_inf):
        MWE_PATTERNS.append((_form, _cont, _inf, _cont_lem, _type))

FILLERS = [
    ("Marie", "Marie", "PROPN"),
    ("Pierre", "Pierre", "PROPN"),
    ("Jean", "Jean", "PROPN"),
    ("le", "le", "DET"),
    ("la", "le", "DET"),
    ("les", "le", "DET"),
    ("un", "un", "DET"),
    ("une", "un", "DET"),
    ("aujourd'hui", "aujourd'hui", "ADV"),
    ("souvent", "souvent", "ADV"),
    ("vraiment", "vraiment", "ADV"),
    ("hier", "hier", "ADV"),
    ("nous", "nous", "PRON"),
    ("ils", "il", "PRON"),
    ("vraiment", "vraiment", "ADV"),
    ("dans", "dans", "ADP"),
    ("le", "le", "DET"),
    ("salon", "salon", "NOUN"),
    ("matin", "matin", "NOUN"),
    (".", ".", "PUNCT"),
    (",", ",", "PUNCT"),
]


def conllu_line(idx, form, lemma, upos, mwe):
    """Build a CoNLL-U row. Heads/deps are stubbed — the parser ignores them."""
    return "\t".join([
        str(idx), form, lemma, upos, "_", "_",
        str(max(idx - 1, 0)), "dep", "_", "_", mwe,
    ])


def sentence(rng, sent_idx, mwe_specs, discontinuous=False, with_noise=False):
    """
    Render a sentence containing the given MWEs.

    mwe_specs is a list of (mwe_id, pattern) tuples. discontinuous=True inserts
    a filler token between the head and continuation tokens of the first MWE.
    """
    lines = [f"# sent_id = synth-{sent_idx}", "# text = (synthetic test sentence)"]
    rows = []  # (form, lemma, upos, mwe_field)

    # Optional leading filler
    if with_noise:
        f, l, p = rng.choice(FILLERS)
        rows.append((f, l, p, "*"))

    for spec_idx, (mwe_id, (head_form, cont_forms, head_lemma, cont_lemmas, mwe_type)) in enumerate(mwe_specs):
        rows.append((head_form, head_lemma, "VERB" if head_form not in ("se", "le", "la", "les") else "PRON",
                     f"{mwe_id}:{mwe_type}"))
        if discontinuous and spec_idx == 0 and cont_forms:
            # Drop in a non-MWE filler between head and first continuation
            f, l, p = rng.choice(FILLERS)
            rows.append((f, l, p, "*"))
        for cf, cl in zip(cont_forms, cont_lemmas):
            rows.append((cf, cl, "X", str(mwe_id)))
        if with_noise:
            f, l, p = rng.choice(FILLERS)
            rows.append((f, l, p, "*"))

    # Trailing punctuation
    rows.append((".", ".", "PUNCT", "*"))

    for i, (form, lemma, upos, mwe) in enumerate(rows, start=1):
        lines.append(conllu_line(i, form, lemma, upos, mwe))

    return "\n".join(lines) + "\n\n"


def overlapping_sentence(sent_idx):
    """Sentence where one token belongs to two MWE ids simultaneously."""
    lines = [f"# sent_id = synth-overlap-{sent_idx}", "# text = (overlap test)"]
    rows = [
        ("Il", "il", "PRON", "*"),
        ("a", "avoir", "AUX", "1:LVC.full"),
        ("pris", "prendre", "VERB", "1;2:VID"),  # token in two MWEs
        ("en", "en", "ADP", "1"),
        ("compte", "compte", "NOUN", "1;2"),
        (".", ".", "PUNCT", "*"),
    ]
    for i, (form, lemma, upos, mwe) in enumerate(rows, start=1):
        lines.append(conllu_line(i, form, lemma, upos, mwe))
    return "\n".join(lines) + "\n\n"


def edge_case_sentence(sent_idx):
    """Sentence with multi-word token ranges and empty nodes that must be skipped."""
    lines = [f"# sent_id = synth-edge-{sent_idx}", "# text = (edge case test)"]
    raw_rows = [
        # token_id, form, lemma, upos, mwe
        ("1-2", "du", "_", "_", "_"),         # multi-word range — parser must skip
        ("1", "de", "de", "ADP", "*"),
        ("2", "le", "le", "DET", "*"),
        ("3", "se", "se", "PRON", "1:IRV"),
        ("4", "demander", "demander", "VERB", "1"),
        ("4.1", "_", "_", "_", "*"),          # empty node — parser must skip
        ("5", "si", "si", "SCONJ", "*"),
        ("6", ".", ".", "PUNCT", "*"),
    ]
    for tok_id, form, lemma, upos, mwe in raw_rows:
        line = "\t".join([tok_id, form, lemma, upos, "_", "_", "0", "dep", "_", "_", mwe])
        lines.append(line)
    return "\n".join(lines) + "\n\n"


def generate(path: Path, n_sentences: int = 700, seed: int = 42) -> int:
    """Generate the fixture file and return the count of MWEs emitted."""
    rng = random.Random(seed)
    mwe_count = 0
    with open(path, "w", encoding="utf-8") as f:
        for sent_idx in range(n_sentences):
            n_mwes = rng.choices([1, 2, 3], weights=[6, 3, 1])[0]
            chosen = rng.sample(MWE_PATTERNS, n_mwes)
            specs = [(i + 1, pat) for i, pat in enumerate(chosen)]
            discontinuous = rng.random() < 0.3
            with_noise = rng.random() < 0.5
            f.write(sentence(rng, sent_idx, specs, discontinuous=discontinuous, with_noise=with_noise))
            mwe_count += n_mwes

        # Add a few edge-case sentences
        for i in range(10):
            f.write(overlapping_sentence(i))
            mwe_count += 2
        for i in range(5):
            f.write(edge_case_sentence(i))
            mwe_count += 1

    return mwe_count


if __name__ == "__main__":
    target = Path("raw/parseme/fr/train.cupt")
    target.parent.mkdir(parents=True, exist_ok=True)
    # The parser's git_clone short-circuit needs a .git dir to skip cloning.
    git_marker = target.parent / ".git"
    git_marker.mkdir(exist_ok=True)
    (git_marker / "HEAD").write_text("ref: refs/heads/synthetic\n", encoding="utf-8")

    total = generate(target)
    print(f"Wrote {target} with {total} MWE annotations")
