# F-312.0 — RAG Licensing Decision Memo

**Date drafted:** 2026-05-12
**Drafted by:** BE Claude Code (research pass)
**Sign-off status:** **Awaiting Chadi.** This memo is a research summary, not legal advice. Final go/no-go on Path A (license + redistribute) requires either Chadi's direct judgment call or a French-copyright lawyer's formal opinion.
**Gates:** F-312 (RAG retrieval layer) + F-321 (Le Vocabulaire OQLF Phase 1 seed).

---

## Question

Can Le Méthodic ingest content from (a) the OQLF *Banque de dépannage linguistique* (BDL) and (b) the Académie française "Dire, ne pas dire" column, and redistribute that content as in-prompt RAG context for a commercial subscription product?

---

## Source-by-source findings

### Source 1 — OQLF / Banque de dépannage linguistique (BDL)

**Canonical URL:** `https://vitrinelinguistique.oqlf.gouv.qc.ca/banque-de-depannage-linguistique` (BDL is now consolidated into the Vitrine linguistique alongside the GDT).

**Governing terms:** OQLF no longer publishes a standalone `conditions_utilisation.html` (the URL referenced in the original strategic doc returns HTTP 404). The OQLF footer points to the Government of Quebec's umbrella copyright page at `https://www.quebec.ca/droit-auteur`. That page governs all `.gouv.qc.ca` content — including OQLF and the BDL.

**Five questions:**

| Q | Finding |
|---|---|
| **(1) License type** | **"Tous droits réservés."** No Creative Commons, no public-domain designation. Quote: *"Le gouvernement du Québec détient les droits exclusifs de propriété intellectuelle sur tous les documents..."* |
| **(2) Scraping permitted?** | Not addressed explicitly. Default under "tous droits réservés" is **NO**. |
| **(3) Redistribution permitted?** | **NO — explicitly prohibited.** Quote: *"Il est interdit de reproduire, télécharger, stocker, traduire, adapter, publier ou représenter..."* Reproduction and redistribution require **prior written authorization**. |
| **(4) Attribution requirements** | Not specified in the umbrella policy. Specific terms negotiated case-by-case at the authorization stage. |
| **(5) Commercial use** | Not separately addressed. The blanket prohibition covers all uses (commercial or not) without prior written authorization. |

**Authorization channel:** `droitdauteur@mcc.gouv.qc.ca` (Ministère de la Culture et des Communications, Mon–Fri 08:00–16:00).

**Open-data alternative noted but unverified:** The Government of Quebec runs `donneesquebec.ca` and some OQLF resources (notably the GDT in raw-data form) have historically been published there under more permissive terms. The BDL specifically appears NOT to have a downloadable open-data export at the time of this memo. To be confirmed if Chadi wants to pursue this angle — search `donneesquebec.ca` for "BDL" or "Office québécois de la langue française."

### Source 2 — Académie française "Dire, ne pas dire"

**Canonical URL:** `https://www.academie-francaise.fr/dire-ne-pas-dire` (under the umbrella `academie-francaise.fr`).

**Governing terms:** `https://www.academie-francaise.fr/mentions-legales`.

**Five questions:**

| Q | Finding |
|---|---|
| **(1) License type** | **Proprietary, all rights reserved.** Quote: *"Le présent site est la propriété de l'Académie française."* All texts, drawings, images, and integrated works belong to the Académie or to authorized third parties. |
| **(2) Scraping permitted?** | Not addressed explicitly. Default under proprietary terms is **NO**. |
| **(3) Redistribution permitted?** | **NO — explicitly prohibited for digital reproduction.** Quote: *"La reproduction de tout ou partie de ce site sur un support électronique quel qu'il soit est formellement interdite sauf autorisation expresse"* ("strictly forbidden unless expressly authorized"). |
| **(4) Attribution requirements** | Required *only* for the narrow educational exception (see below). General reproduction requires a license, not just attribution. |
| **(5) Commercial use** | **Explicitly excluded.** Personal-use reproduction is permitted *"sous réserve qu'elle soit strictement réservée à un usage personnel"*, with commercial and advertising purposes excluded. The educational exception requires (a) free distribution, (b) no modifications, (c) citation linking to academie-francaise.fr, (d) paper reproduction only — none of which fit a paid AI-prompt-context use case. |

**Authorization channel:** `contact@academie-francaise.fr` (or postal address listed on the page).

**No "Dire, ne pas dire" exception:** the legal notices do not carve the column out from the general copyright regime. It falls under the general all-rights-reserved umbrella.

---

## Le Méthodic's intended use vs. terms

| Intended use | OQLF/BDL | Académie française |
|---|---|---|
| Scrape entries into Postgres | Prohibited (default under "tous droits réservés") | Prohibited (digital reproduction "formellement interdite") |
| Inject scraped text into Claude prompt context | Prohibited (redistribution clause) | Prohibited (digital reproduction clause) |
| Display source citation + URL on diagnostic results | Likely fair use (short citation + attribution + link) — **but not unilaterally; depends on length and substantiality** | Likely fair use under same caveats |
| Charge users for a SaaS that internally uses this content | Cuts against "personal use only" (Académie) and "no authorization" (OQLF) | Explicit exclusion of commercial purposes |

**Bottom line:** Both sources prohibit our default RAG implementation (scrape → store → inject into prompt context for a paid product) unless we first obtain written authorization.

---

## Three paths (per F-312.0 decision matrix)

### Path A — License + redistribute (full F-312 as originally scoped)

- File written authorization requests with both `droitdauteur@mcc.gouv.qc.ca` (Quebec) and `contact@academie-francaise.fr` (Académie).
- Articulate the use case clearly: educational French-learning SaaS, attribution prominently displayed, content not modified, X requests/day at expected scale.
- Negotiate terms (license fee, attribution format, audit rights, term).
- Outcome: 2-12 weeks, possibly never. Académie française is historically conservative on commercial licensing; OQLF Quebec ministry path is process-heavy.
- **Risk if pursued:** burn calendar weeks waiting for a "no."

### Path B — Fair-use snippet + link-only citation

- Do NOT store source text in Postgres beyond minimal metadata (error pattern, error type, URL, snippet ≤30 words).
- Do NOT inject full source text into Claude prompts. Instead, the diagnostic call uses its own knowledge; the FE renders a citation linking to the source URL after the fact.
- Acts like a footnote, not a corpus.
- **Risk:** narrow margin. French/Quebec "courte citation" exception (Berne Convention art. 10) requires (i) the citation is short, (ii) the citing work is itself protected and original, (iii) attribution is given, (iv) the citation is for criticism, illustration, or analysis — not as a substitute for the source. A paid AI-prompt-context use is plausibly within this if implemented strictly (≤30 word excerpts, never the substantive correction prose, always with link). But not bulletproof — a single C&D forces emergency removal.
- **Loses the moat advantage:** the credibility claim ("according to the OQLF, this is an anglicism") downgrades to "see also [link]." That's not nothing, but it's less than originally scoped.

### Path C — Curated CC corpus + Chadi authoring

- Drop OQLF and Académie as ingestion sources.
- Build the corpus from genuinely permissive sources: Wiktionary FR (CC BY-SA), Tatoeba (CC BY 2.0), OpenSubtitles parallel corpora (CC BY-NC if non-commercial-only fits; check), Chadi-authored content from 7,000+ hours of tutoring.
- Trade-off: more authoring effort up-front, full ownership, zero legal exposure, and Chadi's content carries its own credibility (the methodology IS the moat, not a third-party authority).
- Path C makes Le Méthodic's RAG layer **Chadi's voice + Chadi's corpus**, which is arguably more on-brand than OQLF/Académie quotations would be.

---

## Recommendation

**Ship Path C for soft beta. Pursue Path A in parallel as low-priority background work.**

Rationale:
1. **Soft beta cannot afford Path A's calendar uncertainty.** F-312 + F-321 are filed as Launch priority; waiting 2-12 weeks for two separate authorization processes blocks the entire Le Vocabulaire OQLF seed (F-321) and the diagnostic RAG layer (F-312). Path C unblocks both immediately.
2. **Path B's legal margin is too thin for a product that wants to grow.** Le Méthodic at 5,000+ Y1 users + visible commercial product makes a tempting C&D target. The "we're just citing snippets" defense holds at 50 users, gets weaker at 5,000, and is risky enough at 50,000 that we'd be rebuilding the corpus anyway.
3. **Chadi's authored content IS the moat.** The strategic frame in CLAUDE.md says it explicitly: "the competitive edge is the 4-layer [now 5-couche] diagnostic framework built from 7,000+ hours of tutoring." Building the corpus from authoritative third parties dilutes that frame slightly. Building it from Chadi's own catalog of L1-interference patterns (which is what 7,000+ hours produces) reinforces it.
4. **Path A as background:** still worth pursuing because if either authorization comes back positive, the corpus becomes richer. But neither is allowed to gate launch.

### Consequences of Path C for F-312 + F-321

- **F-312 rescoped:** `linguistic_corpus` schema stays (source column becomes `chadi_authored | wiktionary_fr | tatoeba | opensubtitles | curated`). The retrieval + injection layer is unchanged. Citation format changes: instead of "according to the OQLF," output reads "Le Méthodic methodology library."
- **F-321 rescoped:** "OQLF Phase 1 seed (3 topic sets, 500-800 entries)" becomes "Chadi-authored Phase 1 seed (3 topic sets, 500-800 entries) — Chadi authors directly into the corpus over the course of [duration TBD by Chadi]." Effort shifts from BE-engineering scraping to Chadi-content-authoring. BE work is lighter (no scrape/normalize pipeline) but Chadi's content load is heavier.
- **Sub-ticket needed:** F-312.1 — "Path A authorization requests" (low-priority, parallel track, asynchronous). File this if Chadi wants to keep that door open.

---

## What to commit next (gated on Chadi's go-ahead)

If Chadi accepts Path C:
1. Update F-312 body → rescope to curated CC + Chadi-authored corpus.
2. Update F-321 body → rescope to Chadi-authored Phase 1 seed.
3. File F-312.1 → parallel-track authorization requests (low priority, no launch gate).
4. F-312.0 status → "Decision Path C, signed off 2026-05-XX, awaiting Chadi authoring kickoff."

If Chadi wants Path A pursued first:
1. F-312.0 status → "Path A pursued; awaiting written authorization from OQLF (droitdauteur@mcc.gouv.qc.ca) + Académie (contact@academie-francaise.fr)."
2. F-312 + F-321 → moved to "Blocked on F-312.0 authorization outcome."
3. Accept calendar slip — currently no estimate on response time from either body.

If Chadi wants Path B (fair-use snippet):
1. F-312.0 status → "Path B selected — accept legal exposure, document in deliverable."
2. F-312 rescoped: 30-word-max excerpt cap enforced in ingest pipeline, citation-link-only on every entry, no full-text storage of source content.
3. **Strongly recommend Chadi get a French-copyright lawyer to validate Path B specifically before committing schema work.** This is the path most likely to surface as legal exposure later.

---

## Open items for Chadi sign-off

1. **Pick a path.** A / B / C — none of the above is "default safe."
2. **If Path A or B: legal sign-off.** Memo author (BE Claude) is not a lawyer; French/Quebec copyright nuance exceeds research-pass confidence.
3. **If Path C: confirm Chadi-authored corpus scope.** What 3 topic sets? What entry-count target? What's the authoring cadence? F-321 body needs concrete numbers post-decision.

---

*End of memo. Source URLs cited inline. No further BE schema work on F-312 / F-321 until Chadi signs off on one of the three paths above.*
