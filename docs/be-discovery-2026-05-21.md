# BE Discovery — 2026-05-21

## Writing-vs-Oral couche mismatch

The writing analysis engine (`app/services/writing_analysis.py`) emits the full 5-couche surface (Le Fond, Les Moules des Idées, Les Moules, Les Réflexes Anglais, La Voix) as of V-016a (2026-05-12), while the oral analysis engine (`app/services/analysis.py`) still emits only 4 couches — La Voix is not yet wired on the oral path. This means a user submitting writing receives a Voix score on La Carte, but a user submitting an oral response does not, and the two diagnostic surfaces are not symmetrical. The gap is already acknowledged in `CLAUDE.md` (Tech Stack section: "writing path on the full 5 couches as of V-016a; oral path on 4 couches until V-009.be lifts La Voix") and is queued under V-009.be. No fix attempted in this session — captured here so it gets absorbed as an entry in PRD Section 5 (AI Infrastructure) when planning for AI work opens, likely scoped against V-009.be.
