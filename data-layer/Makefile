# Le Méthodic data-layer Makefile
# Run `make help` for the list of targets.

.PHONY: help setup schema decide ingest merge dedupe enrich vectorize \
        review-queue license-audit foundation clean nuke \
        ingest-universal-cefr ingest-lexique3 ingest-parseme \
        ingest-collfren ingest-dbnary ingest-anki ingest-tatoeba

PYTHON := python
SCRIPTS := scripts
CONFIG := config.yml

help:
	@echo "Le Méthodic data layer — make targets"
	@echo ""
	@echo "  setup           Install models and validate environment"
	@echo "  schema          Apply DB schema (sql/001_schema.sql)"
	@echo "  decide          Interactive decision prompts -> config.yml"
	@echo ""
	@echo "  ingest          Run all 7 source ingestions"
	@echo "  ingest-<source> Run a single source (universal-cefr, lexique3, ...)"
	@echo ""
	@echo "  merge           Apply sql/002_merge.sql"
	@echo "  dedupe          Run near-duplicate collapsing"
	@echo "  enrich          LLM enrichment (long-running)"
	@echo "  vectorize       Embeddings + Piper audio + CDN upload"
	@echo ""
	@echo "  review-queue    Generate validation spreadsheet"
	@echo "  license-audit   Generate license audit report"
	@echo ""
	@echo "  foundation      Run ingest -> merge -> dedupe -> enrich -> vectorize"
	@echo ""
	@echo "  clean           Remove raw download cache"
	@echo "  nuke            DROP all chunk data (destructive)"

setup:
	$(PYTHON) $(SCRIPTS)/setup.py --config $(CONFIG)

schema:
	$(PYTHON) -c "from scripts.common import apply_sql; apply_sql('sql/001_schema.sql')"

decide:
	$(PYTHON) $(SCRIPTS)/decide.py --config $(CONFIG)

# Individual ingestion targets
ingest-universal-cefr:
	$(PYTHON) -m scripts.ingest.universal_cefr --config $(CONFIG)

ingest-lexique3:
	$(PYTHON) -m scripts.ingest.lexique3 --config $(CONFIG)

ingest-parseme:
	$(PYTHON) -m scripts.ingest.parseme --config $(CONFIG)

ingest-collfren:
	$(PYTHON) -m scripts.ingest.collfren --config $(CONFIG)

ingest-dbnary:
	$(PYTHON) -m scripts.ingest.dbnary --config $(CONFIG)

ingest-anki:
	$(PYTHON) -m scripts.ingest.anki --config $(CONFIG)

ingest-tatoeba:
	$(PYTHON) -m scripts.ingest.tatoeba --config $(CONFIG)

# Run all ingestions in order. UniversalCEFR + Lexique3 first because
# they seed the largest number of chunks; later sources enrich existing rows.
ingest: ingest-universal-cefr ingest-lexique3 ingest-parseme \
        ingest-collfren ingest-dbnary ingest-anki ingest-tatoeba
	@echo "[ingest] All sources complete."

merge:
	$(PYTHON) $(SCRIPTS)/merge.py --config $(CONFIG)

dedupe:
	$(PYTHON) $(SCRIPTS)/dedupe.py --config $(CONFIG)

enrich:
	$(PYTHON) $(SCRIPTS)/enrich.py --config $(CONFIG)

vectorize:
	$(PYTHON) $(SCRIPTS)/vectorize.py --config $(CONFIG)

review-queue:
	$(PYTHON) $(SCRIPTS)/review_queue.py --config $(CONFIG)

license-audit:
	$(PYTHON) $(SCRIPTS)/license_audit.py --config $(CONFIG)

# Full foundation pipeline. Each stage depends on the previous.
foundation: ingest merge dedupe enrich vectorize
	@echo "[foundation] Pipeline complete. Run 'make review-queue' next."

clean:
	rm -rf raw/* processed/*
	@echo "[clean] Raw and processed caches removed. DB untouched."

nuke:
	@echo "[nuke] This will DROP all chunk data. Press Ctrl-C to abort."
	@sleep 5
	$(PYTHON) -c "from scripts.common import nuke_data; nuke_data()"
