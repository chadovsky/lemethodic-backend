# Le Méthodic data layer — Step 0 scaffolding

This is the orchestration infrastructure for building the unified data asset described in `LEMETHODIC_BACKLOG_V2.md`. After running the pipeline end-to-end, you have a Postgres database containing the chunk-based foundation of Le Méthodic.

## Folder layout

```
data-layer/
├── Makefile                  # Entry point: `make foundation` runs everything
├── requirements.txt          # Python dependencies
├── config.example.yml        # Copy to config.yml and edit
├── .gitignore
├── sql/
│   ├── 001_schema.sql        # Tables, indices, constraints
│   ├── 002_merge.sql         # Cross-source merge query
│   └── 003_views.sql         # Reporting views
├── prompts/
│   ├── topic_classification.txt
│   ├── quebec_variant.txt
│   ├── register.txt
│   └── example_generation.txt
└── scripts/
    ├── common.py             # Shared utilities (DB, upsert, normalization)
    ├── setup.py              # Environment + model setup
    ├── decide.py             # Interactive decisions for [DECIDE-*] forks
    ├── merge.py              # Runs sql/002_merge.sql
    ├── dedupe.py             # Near-duplicate collapsing
    ├── enrich.py             # LLM batch enrichment over chunks
    ├── vectorize.py          # Embeddings + Piper audio + CDN upload
    ├── review_queue.py       # Generates spot-check spreadsheet
    ├── license_audit.py      # Per-source license report
    └── ingest/
        ├── base.py           # Ingestion framework + upsert helper
        ├── universal_cefr.py # FULL template (use as model for the others)
        ├── lexique3.py       # FULL implementation
        ├── parseme.py        # Skeleton — TODOs marked
        ├── collfren.py       # Skeleton — TODOs marked
        ├── dbnary.py         # Skeleton — TODOs marked
        ├── anki.py           # Skeleton — TODOs marked
        └── tatoeba.py        # Skeleton — TODOs marked
```

## Quick start

```bash
# 1. Drop this folder into tcf-oral-tool/data-layer/
# 2. Configure
cp config.example.yml config.yml
# (edit config.yml with your DB connection string and other settings)

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment (creates folders, pulls models, tests connection)
make setup

# 5. Apply schema
make schema

# 6. Answer the [DECIDE-*] questions once
make decide

# 7. Run the full foundation pipeline (mostly unattended)
make foundation

# Or run individual stages:
make ingest        # ~12h compute
make enrich        # 1 day GPU or 1 week CPU
make vectorize     # ~24h compute

# 8. Spot-check 500 chunks (active human work, ~6 hours)
make review-queue

# 9. License audit (active human work, ~2 hours)
make license-audit
```

## What each Make target does

| Target | What it does | Duration |
|---|---|---|
| `make setup` | Install deps, pull spaCy + Whisper + LLM models, validate config | ~30 min |
| `make schema` | Apply `sql/001_schema.sql` to create tables | ~1 min |
| `make decide` | Interactive prompts; writes config.yml decisions | ~30 min |
| `make ingest` | Download + ingest all 7 sources | ~12 h |
| `make merge` | Run cross-source merge SQL | ~5 min |
| `make dedupe` | Run near-duplicate collapsing | ~10 min |
| `make enrich` | LLM batch enrichment over all chunks | 1 d–1 wk |
| `make vectorize` | Embeddings + audio + CDN upload | ~24 h |
| `make review-queue` | Generate 500-chunk validation spreadsheet | ~5 min |
| `make license-audit` | Generate per-source audit report | ~1 min |
| `make foundation` | Runs ingest → merge → dedupe → enrich → vectorize | 3–5 days |
| `make clean` | Remove raw download cache (keeps DB) | Instant |
| `make nuke` | Drop all chunk data (DESTRUCTIVE) | Instant |

## What you'll fill in

The fully-implemented files (`universal_cefr.py`, `lexique3.py`, `common.py`, `enrich.py`, `vectorize.py`, etc.) are runnable as-is once config is set. The skeleton ingestion scripts (`parseme.py`, `collfren.py`, `dbnary.py`, `anki.py`, `tatoeba.py`) have TODO blocks marking where source-specific parsing logic goes. Each skeleton documents the source format and expected fields.

## Configuration

All decisions live in `config.yml` (copy from `config.example.yml`). Key fields:

- `db.connection_string` — Postgres connection
- `data.raw_dir` — where downloaded source files live
- `llm.provider` — `ollama` or `vllm`
- `llm.model` — `qwen2.5:7b-instruct` (recommended start) or `mistral-small:24b`
- `tts.voice_fr` — Piper voice for French audio
- `cdn.provider` — `r2` (Cloudflare) or `s3` (AWS) or `none` (local only)
- `triangulation.min_sources` — `1` for loose, `2` for strict core library

## Logging

All scripts log to `data-layer/logs/<stage>_<timestamp>.log`. Failures append to `data-layer/logs/errors.log` for easy debugging.

## Idempotency

Every script is safe to re-run. Ingestion uses `ON CONFLICT DO UPDATE` based on `normalized_surface`. Enrichment skips chunks already enriched (tracked in `chunks.enrichment_completed_at`). Vectorize skips chunks already embedded.

## Resuming after failure

If a script fails midway, re-running it picks up where it left off. Check logs for the failure point. Most failures are recoverable (network blip, OOM, etc.).

## When to ask for help

- A source's format is more complex than the skeleton anticipates
- Quality validation reveals systemic issues with one source
- You want to extend to a sixth language or sixth source
- You hit a [DECIDE-*] point and want a recommendation

This scaffolding is intentionally minimal. Add complexity as you learn what your data actually looks like.
