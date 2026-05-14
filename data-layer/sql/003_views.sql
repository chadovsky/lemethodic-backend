-- =============================================================
-- Reporting views for the quality dashboard (Stage F9.5)
-- =============================================================

CREATE OR REPLACE VIEW v_quality_summary AS
SELECT
    COUNT(*) AS total_chunks,
    COUNT(*) FILTER (WHERE confidence_tier = 'core') AS core_library,
    COUNT(*) FILTER (WHERE cefr_level IS NOT NULL) AS cefr_tagged,
    COUNT(*) FILTER (WHERE surface_en IS NOT NULL) AS translated,
    COUNT(*) FILTER (WHERE audio_url IS NOT NULL) AS with_audio,
    COUNT(*) FILTER (WHERE embedding IS NOT NULL) AS embedded,
    COUNT(*) FILTER (WHERE enrichment_completed_at IS NOT NULL) AS enriched,
    COUNT(*) FILTER (WHERE is_quebec_specific) AS quebec_specific,
    COUNT(*) FILTER (WHERE array_length(topic_codes, 1) > 0) AS topic_tagged
FROM chunks;

CREATE OR REPLACE VIEW v_cefr_distribution AS
SELECT
    cefr_level,
    COUNT(*) AS chunk_count,
    COUNT(*) FILTER (WHERE confidence_tier = 'core') AS core_count
FROM chunks
WHERE cefr_level IS NOT NULL
GROUP BY cefr_level
ORDER BY cefr_level;

CREATE OR REPLACE VIEW v_source_coverage AS
SELECT
    source_name,
    COUNT(DISTINCT chunk_id) AS chunks_contributed,
    MAX(ingested_at) AS last_ingestion
FROM chunk_sources
GROUP BY source_name
ORDER BY chunks_contributed DESC;

CREATE OR REPLACE VIEW v_topic_distribution AS
SELECT
    exam,
    topic_code,
    COUNT(DISTINCT chunk_id) AS chunk_count
FROM chunk_topics
GROUP BY exam, topic_code
ORDER BY exam, chunk_count DESC;

CREATE OR REPLACE VIEW v_provenance_per_chunk AS
SELECT
    c.id,
    c.surface_fr,
    c.confidence_tier,
    c.cefr_level,
    array_agg(cs.source_name ORDER BY cs.source_name) AS sources,
    COUNT(cs.source_name) AS source_count
FROM chunks c
LEFT JOIN chunk_sources cs ON cs.chunk_id = c.id
GROUP BY c.id, c.surface_fr, c.confidence_tier, c.cefr_level;
