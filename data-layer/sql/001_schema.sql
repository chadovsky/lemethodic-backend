-- =============================================================
-- Le Méthodic data layer — schema v1
-- Apply with: make schema
-- =============================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- chunks: the core lexical/phrasal entries
-- ============================================================
CREATE TABLE IF NOT EXISTS chunks (
    id BIGSERIAL PRIMARY KEY,

    -- Surface forms
    surface_fr TEXT NOT NULL,                  -- as written
    normalized_surface TEXT NOT NULL UNIQUE,   -- lowercased, stripped, normalized
    lemma_fr TEXT,                             -- canonical form
    surface_en TEXT,                           -- English equivalent
    language CHAR(2) NOT NULL DEFAULT 'fr',    -- ISO 639-1

    -- Linguistic features
    chunk_type TEXT,                           -- idiom | light_verb | collocation | fixed_expression | word
    pos_pattern TEXT,                          -- e.g. "VERB+NOUN", "ADJ+NOUN"
    register TEXT,                             -- formal | neutral | informal | colloquial | vulgar

    -- Difficulty + frequency
    cefr_level TEXT,                           -- A1 | A2 | B1 | B2 | C1 | C2
    frequency_subtitles REAL,
    frequency_books REAL,
    frequency_web REAL,

    -- Regional variants
    is_quebec_specific BOOLEAN NOT NULL DEFAULT FALSE,
    quebec_variant TEXT,                       -- alternate form used in Quebec, if any

    -- Topic mapping (denormalized for fast filtering; see chunk_topics for full)
    topic_codes TEXT[] DEFAULT '{}',           -- e.g. ['tcf.logement', 'delf.b2.travail']

    -- Quality / provenance
    confidence_tier TEXT NOT NULL DEFAULT 'experimental',  -- core | extended | experimental
    enrichment_completed_at TIMESTAMPTZ,       -- null = needs enrichment

    -- Embeddings
    embedding vector(384),                     -- intfloat/multilingual-e5-small

    -- Audio
    audio_url TEXT,                            -- CDN URL after vectorize

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chunks_normalized ON chunks(normalized_surface);
CREATE INDEX IF NOT EXISTS idx_chunks_lang ON chunks(language);
CREATE INDEX IF NOT EXISTS idx_chunks_cefr ON chunks(cefr_level);
CREATE INDEX IF NOT EXISTS idx_chunks_type ON chunks(chunk_type);
CREATE INDEX IF NOT EXISTS idx_chunks_tier ON chunks(confidence_tier);
CREATE INDEX IF NOT EXISTS idx_chunks_quebec ON chunks(is_quebec_specific) WHERE is_quebec_specific = TRUE;
CREATE INDEX IF NOT EXISTS idx_chunks_topics ON chunks USING GIN(topic_codes);
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks USING ivfflat(embedding vector_cosine_ops);

-- ============================================================
-- chunk_examples: example sentences attached to chunks
-- ============================================================
CREATE TABLE IF NOT EXISTS chunk_examples (
    id BIGSERIAL PRIMARY KEY,
    chunk_id BIGINT NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
    example_fr TEXT NOT NULL,
    example_en TEXT,
    cefr_level TEXT,
    source_name TEXT NOT NULL,            -- 'Tatoeba' | 'OpenSubtitles' | 'DBnary' | 'generated'
    audio_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_examples_chunk ON chunk_examples(chunk_id);
CREATE INDEX IF NOT EXISTS idx_examples_source ON chunk_examples(source_name);
CREATE INDEX IF NOT EXISTS idx_examples_cefr ON chunk_examples(cefr_level);

-- ============================================================
-- chunk_topics: many-to-many between chunks and exam topics
-- ============================================================
CREATE TABLE IF NOT EXISTS chunk_topics (
    id BIGSERIAL PRIMARY KEY,
    chunk_id BIGINT NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
    topic_code TEXT NOT NULL,             -- 'tcf.logement', 'delf.b2.environnement', etc.
    exam TEXT NOT NULL,                   -- 'TCF' | 'TEF' | 'DELF' | 'naturalisation'
    confidence REAL,                      -- 0.0–1.0
    source TEXT NOT NULL DEFAULT 'llm_enrichment',  -- 'llm_enrichment' | 'manual'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(chunk_id, topic_code, exam)
);

CREATE INDEX IF NOT EXISTS idx_chunk_topics_chunk ON chunk_topics(chunk_id);
CREATE INDEX IF NOT EXISTS idx_chunk_topics_topic ON chunk_topics(topic_code);
CREATE INDEX IF NOT EXISTS idx_chunk_topics_exam ON chunk_topics(exam);

-- ============================================================
-- chunk_sources: per-chunk provenance from each contributing source
-- ============================================================
CREATE TABLE IF NOT EXISTS chunk_sources (
    id BIGSERIAL PRIMARY KEY,
    chunk_id BIGINT NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
    source_name TEXT NOT NULL,            -- 'PARSEME' | 'Lexique3' | 'FLELex' | etc.
    source_version TEXT,                  -- e.g. '3.83' for Lexique
    source_license TEXT,                  -- 'CC-BY-SA', 'CC-BY', 'Apache 2.0', etc.
    contributed_fields TEXT[],            -- which fields this source contributed
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(chunk_id, source_name)
);

CREATE INDEX IF NOT EXISTS idx_chunk_sources_chunk ON chunk_sources(chunk_id);
CREATE INDEX IF NOT EXISTS idx_chunk_sources_name ON chunk_sources(source_name);

-- ============================================================
-- enrichment_log: tracks LLM enrichment attempts for resumability
-- ============================================================
CREATE TABLE IF NOT EXISTS enrichment_log (
    id BIGSERIAL PRIMARY KEY,
    chunk_id BIGINT NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
    enrichment_type TEXT NOT NULL,        -- 'topic' | 'quebec_variant' | 'register' | 'examples'
    status TEXT NOT NULL,                 -- 'success' | 'failure' | 'retry'
    error_message TEXT,
    model_used TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(chunk_id, enrichment_type)
);

CREATE INDEX IF NOT EXISTS idx_enrichment_log_chunk ON enrichment_log(chunk_id);
CREATE INDEX IF NOT EXISTS idx_enrichment_log_status ON enrichment_log(status);

-- ============================================================
-- Trigger to maintain updated_at on chunks
-- ============================================================
CREATE OR REPLACE FUNCTION trg_set_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS set_updated_at ON chunks;
CREATE TRIGGER set_updated_at
    BEFORE UPDATE ON chunks
    FOR EACH ROW
    EXECUTE FUNCTION trg_set_updated_at();
