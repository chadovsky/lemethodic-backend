# DECISIONS.md

A log of architectural and product decisions made in FluentPath, written at the moment of the decision. Not backfilled from memory.

---

## April 27, 2026 — Le Raccourci → L'École rename

**Decision:** Curriculum surface renamed from "Le Raccourci" to "L'École." Tables, API routes, frontend routes, components, and copy all migrate. Progress data preserved by F-086 and wiped by F-087 (0 lesson completions, 1 quiz attempt across 5 test users at decision time — no real user investment to lose).

**Atomicity:** No exceptions. Every "raccourci" identifier in active code becomes "ecole." Historical entries in BACKLOG.md preserved verbatim with a header note. The RaccourciReveal onboarding component renames to EcoleReveal alongside everything else.

**Backward compat:** None. Hard cut. Only one frontend consumer of the affected surfaces.
