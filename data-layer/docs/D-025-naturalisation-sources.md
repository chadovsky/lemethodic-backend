# D-025 — Naturalisation Interview Content: Source Candidates

**Status:** RESEARCH COMPLETE (2026-05-15)
**Ticket type:** Research only — no ingestion. License audit (D-031) must clear each source before any download/parse work begins.
**Author:** BE
**Related tickets:** D-024 (DALF C-level), D-031 (License audit), D-020 (Run ingest pipeline)

---

## 1. Scope

The French **examen civique** became mandatory for naturalisation, first-time multi-year residence permits, and ten-year resident cards on 2026-01-01 (Décret du 15 juillet 2025; INTV2202117A as amended). The exam is a 40-question QCM drawn from a published bank of ~250 official questions across 5 themes. Beyond the QCM itself, the in-person **entretien d'assimilation** at the préfecture / consulate covers the same five themes in free-form Q&A.

Le Méthodic's naturalisation track has to teach a learner to converse — in French — about the following content categories, with examples and idiomatic phrasing a native examiner would recognise as "thinking in French":

| Category | What it covers |
|---|---|
| **Civics (instruction civique)** | Republican principles, laïcité, devise, secularism in everyday life, citizenship as duty + right |
| **French institutions** | Président de la République, Premier ministre, Assemblée, Sénat, Conseil constitutionnel, Conseil d'État, justice, collectivités |
| **Valeurs de la République** | Liberté–Égalité–Fraternité, laïcité, indivisibilité, démocratie, égalité H/F, refus des discriminations |
| **Administrative geography** | Régions, départements, communes, France d'outre-mer, métropoles, capitales régionales |
| **History** | Gaulois → Révolution → Républiques → 20th-century wars → construction européenne → Ve République; key dates + figures |
| **Vivre ensemble** | Daily-life civics: école, santé, fiscalité, services publics, culture, gastronomie, fêtes nationales, citoyenneté au quotidien |

This is **not** the TCF Canada theme set. Naturalisation content overlaps TCF themes (Société, Culture) but is denser in proper-noun knowledge (dates, names, institutions) and lighter on personal-opinion argumentation. A separate topic taxonomy is required — see §3.

---

## 2. Source Candidates

Approximate sizes are best-effort estimates from page snippets and dataset metadata; confirm before ingestion.

| # | Source name | URL | License | Content type | Approx size | Ingestion feasibility | Priority |
|---|---|---|---|---|---|---|---|
| 1 | **data.gouv.fr — Examen civique (Naturalisation) QCM** | https://www.data.gouv.fr/datasets/examen-civique-naturalisation-questions-de-connaissances-officielles-et-propositions-de-reponses | **Licence Ouverte 2.0 (Etalab)** — commercial reuse OK with attribution | Structured JSON + XLSX, 258 official questions × 5 themes with suggested answers | 91 KB JSON / 32 KB XLSX | **Trivial.** Already parsed, themed, IDed. Drop straight into `chunks` with `source='data_gouv_qcm_naturalisation'`. Caveat: the *questions* are from the Ministère; the *suggested answers* are by leqcmcivique.fr — attribution required on the latter. | **P0** |
| 2 | **data.gouv.fr — Examen civique (Carte de résident) QCM** | https://www.data.gouv.fr/datasets/examen-civique-carte-de-resident-questions-de-connaissances-officielles-et-propositions-de-reponses | **Licence Ouverte 2.0 (Etalab)** | Structured JSON + XLSX, same 5 themes, distinct question bank | Comparable to #1 | Trivial — same parser as #1, different file. ~80 % overlap in *themes* with the naturalisation set; questions differ. Useful for cross-validation and to expand QCM coverage for shared subjects. | **P0** |
| 3 | **Livret du citoyen** (annex to Arrêté du 4 février 2022, NOR INTV2202117A, as updated for 2026) | https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000045381869 ; direct PDF mirror at immigration.interieur.gouv.fr/documentation/ressources/livret-du-citoyen.html | **etalab-2.0** (Légifrance footer: "Sauf mention contraire, tous les contenus de ce site sont sous licence etalab-2.0"). The PDF is the *annex* of an arrêté published at the JORF — official text published by the State. | PDF, ~50–70 pp, prose covering the 5 themes; the canonical reference cited as the source for every QCM question | ~12 MB PDF | **Medium.** PDF → text extraction (`pdfplumber` / `pdfminer`) → section-split by chapter heading → chunk per topical paragraph. We already have a PDF-to-chunks recipe pattern in `data-layer/scripts/ingest/`. Risk: pdf layout may include diagrams / boxed callouts that need manual cleanup. | **P0** |
| 4 | **Charte des droits et devoirs du citoyen français** (annexed to Décret n° 2012-127, 30 janvier 2012) | https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000025241393 | **etalab-2.0** (Légifrance default) | PDF + HTML, ~5 pp short prose, signed by the candidate at the naturalisation ceremony | ~50 KB text | **Trivial.** Short, dense, official. One chunk per article. Perfect "Droits_et_devoirs" anchor content. | **P0** |
| 5 | **vie-publique.fr — Fiches** (DILA, Premier ministre) | https://www.vie-publique.fr/fiches | **Licence Ouverte** (page: "Utiliser nos contenus" confirms fiches + briefs + infographics are reusable under LO) | HTML, 1,100+ pedagogical fact sheets on French + EU institutions, public policies, civic literacy | ~1,100 fiches, est. 500–2,000 words each → ~1–2 M tokens | **Medium.** Each fiche has a stable URL and consistent template; would need a polite scraper (sitemap-driven, respectful rate limits) + HTML-to-text. Then theme-tag against our naturalisation taxonomy. This is the single largest *legitimate* civic-prose corpus available. | **P1** |
| 6 | **formation-civique.interieur.gouv.fr** — 222 thematic fact sheets | https://formation-civique.interieur.gouv.fr/ | **Unverified.** Site is a `.gouv.fr` domain managed by DGEF; no per-page license footer visible on home page during this research pass. Default for State-published content is etalab-2.0 unless contrary mention, but D-031 must confirm before ingestion. | HTML, 222 fact sheets keyed to the OFII civic training program (24h/4 days curriculum) | ~222 fiches, est. 300–800 words each | **Medium-easy.** Static-feeling site, scraper-friendly. **Blocked on license confirmation** — escalate to ops to email DGEF if no footer notice or terms-of-use page exists. | **P1 (blocked on D-031)** |
| 7 | **Wikipédia FR — institution / civic articles** (via `wikimedia/wikipedia` HF dataset, `20231101.fr` or fresh dump) | https://huggingface.co/datasets/wikimedia/wikipedia | **CC-BY-SA 4.0** | Structured JSONL articles | Whole FR dump ~3 M articles; *relevant subset* via category seeds ~1–5 k articles | **Easy (with filtering).** Already in HF; loader downloads in minutes. Need: a category-seed crawl (`Catégorie:Symbole_de_la_République_française`, `Catégorie:Institutions_de_la_République_française`, `Catégorie:Cinquième_République_(France)`, `Catégorie:Histoire_de_France_par_période`, `Catégorie:Politique_française`, `Catégorie:Géographie_de_la_France`) to pick the ~1–5 k articles in scope. **Caveat:** CC-BY-SA's *ShareAlike* clause means *derived works* (e.g. AI-generated summaries built on Wikipedia text) carry a viral licensing condition. D-031 must scope how we use this — verbatim chunks for retrieval/embedding vs. transformed text in model outputs. | **P1 (license scoping)** |
| 8 | **Sénat Junior** — institutions pedagogical site | http://junior.senat.fr/ | **Unverified.** Sénat default content is etalab-2.0 but the Junior site uses bespoke illustrations + may have third-party rights. | HTML, ~50–100 child-friendly pages on République / institutions / symbols | Small | **Low priority.** Tone is too child-aimed for an adult B2 learner; would need heavy rewrite. Useful only as a fallback for "Symboles_nationaux" + as a comprehension-difficulty anchor. | **P3** |
| 9 | **Élysée.fr — symbols + presidency pages** | https://www.elysee.fr/la-presidence/les-symboles-de-la-republique | **Unverified.** No explicit license footer. Élysée content historically *not* under etalab without separate consent (institutional photography rights, etc.). | HTML/PDF, official descriptions of national symbols, presidential function | Small (~20 pages of interest) | **Low.** License risk + size doesn't justify the parsing work. Wikipedia + Livret cover the same content under cleaner licensing. | **P3** |
| 10 | **INSEE — administrative geography reference data** (Code Officiel Géographique, populations légales) | https://www.insee.fr/fr/information/2666684 ; https://www.data.gouv.fr/organizations/institut-national-de-la-statistique-et-des-etudes-economiques-insee/ | **Licence Ouverte 2.0** | CSV/XLSX reference tables: 18 régions, 101 départements, ~35 k communes | Tens of MB | **Easy for the reference table itself.** **But:** raw geographic codes aren't naturalisation interview *content* — they're a lookup table. Useful only as **enrichment** (sanity-checking facts in generated examiner questions, populating drill cards like "name a département in Occitanie"). Not a chunk source per se. | **P2 (enrichment, not chunks)** |
| 11 | **INED — open population & society datasets** | https://www.ined.fr/fr/ressources_documentation/ | Mostly **Licence Ouverte** for INED's own publications | Statistical bulletins (PDF) + datasets (CSV) on French demography, immigration, family | Heterogeneous | **Off-scope.** INED produces sociological *data*, not civic prose. Could enrich the "Société_et_vivre_ensemble" topic with current statistics, but not core naturalisation content. | **P3 (out of scope for D-025)** |
| 12 | **HuggingFace — dedicated French civics dataset** | searched: "french civics" / "examen civique" / "naturalisation" | n/a | n/a | n/a | **None found.** No HF community has published a dedicated FR civic-exam corpus. The closest is `wikimedia/wikipedia` (see #7) and there are no `civic*` or `naturalisation*` datasets in the FR locale. **Implication:** we'd be the first to assemble this — modest moat. | n/a |
| 13 | **Older / public-domain civic textbooks** (e.g. early 20th-century manuels d'instruction civique scanned by Gallica/BnF) | https://gallica.bnf.fr/ | **Public domain** (works pre-1925) | Scanned + OCR'd manuels civiques | Tens of titles available | **Hard.** Pre-1925 textbooks describe the IIIe République with very different institutions (no Conseil constitutionnel, no Ve République, different territorial division — Algeria still attached, etc.). Heavy *anachronism risk* for a 2026 examen. Tone is also markedly 19th-century — wrong register for modern conversational prep. Not recommended despite clean licensing. | **P3 (won't ingest)** |
| 14 | **Open university courseware on French civics** | searched: France Université Numérique, OpenClassrooms, OERs | Mixed (CC-BY-NC / CC-BY-SA / proprietary) | MOOCs, video transcripts | Patchy | **Hard.** No single canonical OER for "instruction civique." Existing MOOCs are political-science academic, not naturalisation-pitched. Skip. | **P3 (won't ingest)** |

---

## 3. Recommended Naturalisation Topic Taxonomy

Different from the TCF Canada theme set (Vie quotidienne, Société, Éducation, Technologie, Environnement, Culture, Travail). The naturalisation taxonomy below mirrors the **5 official themes of the examen civique** as published by the Ministère de l'Intérieur, expanded to 10 codes for finer routing of prep content:

| Code | Label | Maps to exam theme | Notes |
|---|---|---|---|
| `Republique_et_laicite` | République & laïcité | T1 (Principes et valeurs) | Liberté–Égalité–Fraternité, laïcité, devise, indivisibilité |
| `Symboles_nationaux` | Symboles nationaux | T1 / T4 (Histoire & culture) | Drapeau, Marseillaise, Marianne, coq, fêtes nationales (14 juillet, 8 mai, 11 novembre) |
| `Institutions_de_la_Republique` | Institutions de la République | T2 (Système institutionnel) | Président, Premier ministre, Assemblée, Sénat, Conseil constitutionnel, Conseil d'État |
| `Pouvoirs_et_justice` | Pouvoirs & justice | T2 | Séparation des pouvoirs, ordre judiciaire / administratif, Conseil supérieur de la magistrature |
| `Histoire_de_France` | Histoire de France | T4 (Histoire, géo, culture) | Révolution, Empire, IIIe–Ve Républiques, guerres mondiales, décolonisation, construction européenne |
| `Geographie_administrative` | Géographie administrative | T4 | 18 régions, 101 départements, communes, France d'outre-mer, Hexagone, principales métropoles |
| `Droits_et_devoirs` | Droits & devoirs du citoyen | T3 (Droits et devoirs) | Charte des droits et devoirs, droits civiques, droits sociaux, devoirs (impôt, défense, jury), libertés fondamentales |
| `Societe_et_valeurs` | Société & valeurs | T3 / T5 (Vie en société) | Égalité H/F, refus des discriminations, laïcité au quotidien, lutte contre les violences |
| `Vivre_en_France` | Vivre en France | T5 (Vie en société) | École, santé, sécurité sociale, services publics, démarches administratives |
| `Culture_et_patrimoine` | Culture & patrimoine | T4 / T5 | Langue française, gastronomie, littérature canonique, patrimoine UNESCO, paysage médiatique |

**Naming convention:** ASCII, snake_case, no diacritics in code (Python identifier-friendly); diacritics preserved in the human label. Matches the convention already used in `app/models/topic.py` for TCF themes.

**Mapping to chunks:** every chunk ingested under D-025's sources should carry a `theme` field with one of these ten codes. The data.gouv.fr QCM datasets already group questions by theme — those map cleanly (T1→`Republique_et_laicite` + `Symboles_nationaux`, T2→`Institutions_de_la_Republique` + `Pouvoirs_et_justice`, T3→`Droits_et_devoirs` + `Societe_et_valeurs`, T4→`Histoire_de_France` + `Geographie_administrative` + `Culture_et_patrimoine`, T5→`Vivre_en_France` + `Societe_et_valeurs`). The Livret chapters mirror the same split.

---

## 4. Final Ingestion Sprint Plan

Pending **D-031 license audit sign-off** for each item.

### Top 3 to ingest (ranked by feasibility × value)

**Rank 1 — data.gouv.fr Examen civique (Naturalisation) QCM** [source #1]
- **Estimated effort:** ~2 hours. Single small JSON/XLSX file, schema already documented in the dataset's "À propos et Licence" tab.
- **Pipeline:** new `data-layer/scripts/ingest/data_gouv_civique.py` parser → emits chunks with `source='data_gouv_qcm_naturalisation'`, `chunk_type='exam_qa'`, `theme` from the dataset's `theme` field re-mapped to our taxonomy.
- **License blockers:** **none.** Licence Ouverte 2.0 explicitly permits commercial reuse + redistribution with attribution. Add `"Réponses suggérées par leqcmcivique.fr"` + hyperlink in the chunk's `attribution` field.
- **Pre-work:** none — file is already public, structured, themed. Can start immediately after D-031 ticks the box.

**Rank 2 — Charte des droits et devoirs du citoyen français** [source #4]
- **Estimated effort:** ~3 hours. Short, dense, official prose. PDF → text → article-level chunk.
- **Pipeline:** extends `data_gouv_civique.py` (or new `legifrance_naturalisation.py`) → emits chunks with `source='charte_droits_devoirs_2012'`, `chunk_type='official_text'`, `theme='Droits_et_devoirs'`.
- **License blockers:** **none.** Légifrance default is etalab-2.0; the décret is a JORF-published act.
- **Pre-work:** none. The text is short enough to manually verify chunking quality on the first pass.

**Rank 3 — Livret du citoyen 2026** [source #3]
- **Estimated effort:** ~1 day. PDF extraction is the long pole — ~12 MB PDF with mixed text + diagrams + boxed callouts → needs a tuned `pdfplumber` pipeline + manual spot-check of the first ~5 chapters before unattended bulk parsing.
- **Pipeline:** new `data-layer/scripts/ingest/livret_citoyen.py` → emits chunks with `source='livret_citoyen_2026'`, `chunk_type='reference_prose'`, `theme` inferred from chapter heading.
- **License blockers:** **none confirmed.** Livret is an annex to an arrêté published at the JORF; Légifrance footer covers it under etalab-2.0. D-031 should still pull a verbatim screenshot of the licensing notice to file before kickoff (this is the highest-value source — worth the extra paranoia).
- **Pre-work:** Pull the 2026-edition PDF (post-January 2026 update is the live exam reference); confirm whether DGEF has published an updated version since the original 4 février 2022 arrêté — search for amending arrêtés on Légifrance.

### Total sprint estimate: ~2 days of BE work after D-031 unblocks.

### License/copyright blockers per source

| Source | Blocker | Resolution path |
|---|---|---|
| #1, #2 (data.gouv.fr QCM) | None | Attribution string baked into chunk metadata |
| #3 (Livret du citoyen) | None confirmed; double-check etalab-2.0 footer applies to PDF annex specifically | Screenshot of Légifrance page footer + arrêté text |
| #4 (Charte) | None | Same as #3 |
| #5 (vie-publique.fr fiches) | None for the LO content; **scraping etiquette** is the real constraint (robots.txt, rate limits, conditional GET for re-runs) | Polite scraper + sitemap; defer to a Sprint 2 ingestion if Sprint 1 hits volume targets without it |
| #6 (formation-civique.interieur) | **License unclear** — no visible footer notice during this research pass | DGEF email or terms-of-use page lookup; D-031 owns this |
| #7 (Wikipedia FR) | CC-BY-SA viral ShareAlike on derived works | D-031 must decide: verbatim chunks for retrieval-only (clean) vs. transformed into model outputs (ShareAlike implications for our generated content) |

### Required pre-work (before any ingestion)
1. **D-031 license audit** confirms etalab-2.0 applies to each source, with the verbatim attribution string per source recorded in `data-layer/config.yml`.
2. **Topic-taxonomy migration** (Alembic): the existing `topics.theme` enum accepts the 7 TCF Canada themes. Naturalisation needs a separate `exam_track` discriminator + the 10 codes from §3 added to a new enum. **This is a schema change** → migration + ASK message per CLAUDE.md gate #7 protocol.
3. **Seeder for naturalisation topic stubs** so the FE has something to render once chunks land. Follow the seeder gate #7 protocol from CLAUDE.md (inline content, idempotent claim, diagnostic + rollback queries).

---

## 5. Honest "Won't Ingest" List

| Source | Why not |
|---|---|
| **Élysée.fr** | License unclear, content overlaps Wikipedia + Livret cleanly, institutional photography rights add risk for no marginal content gain. |
| **Sénat Junior** | Tone is child-pitched; adult B2 prep would need to rewrite, not reuse. Wrong register for the product. |
| **INED publications** | Sociological data is enrichment, not interview content. Naturalisation candidates aren't quizzed on demographic statistics. |
| **Gallica pre-1925 civic manuels** | Anachronism risk: pre-1925 texts describe the IIIe République, Algeria as French territory, no Conseil constitutionnel, etc. Would actively *mislead* a 2026 candidate. Clean license, wrong content. |
| **OpenClassrooms / FUN MOOCs on French civics** | No canonical OER on instruction civique; available courses are political-science academic, mis-pitched for naturalisation prep, and licensing is heterogeneous (CC-BY-NC frequently blocks commercial reuse). |
| **Préfecture-specific naturalisation guides** | Each préfecture publishes its own variant; content overlaps the Livret. Marginal gain, fragmented sourcing. Could become a Sprint 3+ enrichment if we discover regional variations in the *entretien* practice. |
| **Third-party prep sites** (prepacivique.fr, parcours-civique.fr, qcmcivique.fr, letestcivique.fr, etc.) | Proprietary commercial prep content. Even when they cite the Ministère's questions, their *prose explanations* are bespoke and copyrighted. Hard pass on scraping. The `qcmcivique.fr` answer corpus is licensed *via* the data.gouv.fr publication (source #1) — that's the legitimate path. |
| **HuggingFace dedicated civics dataset** | None exists. Confirmed — checked "french civics" / "examen civique" / "naturalisation" / "france citizenship" on the Hub. We'd be the first to publish one (small competitive moat if we eventually share back). |

---

## 6. Open Questions for Chadi

1. **Track architecture:** does naturalisation live under a new `exam_track='naturalisation'` discriminator on `topics` + `chunks`, or does it get its own table family? My recommendation: discriminator + shared `chunks` table — the analysis engine's couches apply equally regardless of exam track.
2. **Conversation drill targets:** the QCM gives us *recognition* prep; the *entretien d'assimilation* needs *production* prep ("expliquez-moi la laïcité avec vos propres mots"). Do we generate Tâche-3-style prompts on top of the 258 QCM stems, or commission Chadi-authored prompts per topic?
3. **B1 vs. B2 register split:** since the *language* threshold for naturalisation is moving to B2 (per 2026 reform), should naturalisation content default to B2 difficulty in `target_levels`, with optional B1 simplifications? Or follow the TCF model with all three (B1/B2/C1)?

These are deferrable to a kickoff conversation when the ingestion sprint is greenlit; they don't block D-031 or the topic-taxonomy migration.

---

## 7. References

- Arrêté du 4 février 2022 (Livret du citoyen): https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000045381869
- Décret n° 2012-127 (Charte des droits et devoirs): https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000025241393
- data.gouv.fr — Examen civique Naturalisation: https://www.data.gouv.fr/datasets/examen-civique-naturalisation-questions-de-connaissances-officielles-et-propositions-de-reponses
- data.gouv.fr — Examen civique Carte de résident: https://www.data.gouv.fr/datasets/examen-civique-carte-de-resident-questions-de-connaissances-officielles-et-propositions-de-reponses
- Direction générale des étrangers en France (Livret PDF): https://www.immigration.interieur.gouv.fr/documentation/ressources/livret-du-citoyen.html
- vie-publique.fr fiches: https://www.vie-publique.fr/fiches
- formation-civique.interieur.gouv.fr: https://formation-civique.interieur.gouv.fr/
- wikimedia/wikipedia (HF): https://huggingface.co/datasets/wikimedia/wikipedia
- Licence Ouverte 2.0 (Etalab): https://www.etalab.gouv.fr/wp-content/uploads/2017/04/ETALAB-Licence-Ouverte-v2.0.pdf
