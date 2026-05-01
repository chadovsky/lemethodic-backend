# DECISIONS.md

A log of architectural and product decisions made in FluentPath, written at the moment of the decision. Not backfilled from memory.

---

## April 27, 2026 — Le Raccourci → L'École rename

**Decision:** Curriculum surface renamed from "Le Raccourci" to "L'École." Tables, API routes, frontend routes, components, and copy all migrate. Progress data preserved by F-086 and wiped by F-087 (0 lesson completions, 1 quiz attempt across 5 test users at decision time — no real user investment to lose).

**Atomicity:** No exceptions. Every "raccourci" identifier in active code becomes "ecole." Historical entries in BACKLOG.md preserved verbatim with a header note. The RaccourciReveal onboarding component renames to EcoleReveal alongside everything else.

**Backward compat:** None. Hard cut. Only one frontend consumer of the affected surfaces.

---

## April 27, 2026 — Couches → TCF criteria relabel (F-088)

**Decision:** Frontend dimension labels relabeled from internal pedagogical names (Le Fond / Les Moules des Idées / Les Moules / Les Réflexes Anglais) to TCF criteria (Étendue / Cohérence / Correction / Aisance). Backend dimensions and scoring unchanged.

**Honesty flag:** "Réflexes Anglais → Aisance" is correlated but not faithful. Réflexes Anglais measures L1-interference (calques, missing *ne*, English word order). Aisance in TCF measures fluidity (rate, hesitations, smoothness). A student can score perfectly on one and badly on the other. The relabel ships now for sprint speed; F-090 (post-launch) does the proper backend refactor with a true Aisance dimension based on F-038 fluency layer signals.

**Methodology preservation:** The About page and methodology copy retain "La Méthode en Couches" with the four internal names. Only score labels change.

**Implementation note:** Backend hard-cut: `/api/recordings/{id}` (and the `/history` companion) replaced the `la_carte` dict with a `couches` array carrying `{key, display_label_en, display_label_fr, score}` per entry. The legacy admin template at `app/templates/index.html` migrated alongside — it still surfaces internal pedagogical names for its audience (internal tools per F5), but reads them via `coucheLabel(key)` against the new array shape. Two consumers, one API shape — see F-088 commit message for the audit. (F-088 originally used `internal_key`; F-110.1 + F-110.2 reconciled the field name to `key`.)
