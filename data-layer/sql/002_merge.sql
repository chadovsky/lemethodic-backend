-- =============================================================
-- Cross-source merge — runs after `make ingest`
-- =============================================================
-- Idempotent: re-running produces the same result.

-- Recompute confidence_tier based on number of contributing sources
UPDATE chunks c
SET confidence_tier = CASE
    WHEN src.source_count >= 2 THEN 'core'
    WHEN src.source_count = 1 THEN 'extended'
    ELSE 'experimental'
END
FROM (
    SELECT chunk_id, COUNT(DISTINCT source_name) AS source_count
    FROM chunk_sources
    GROUP BY chunk_id
) src
WHERE c.id = src.chunk_id;

-- Surface diagnostics
SELECT
    confidence_tier,
    COUNT(*) AS chunk_count,
    COUNT(*) FILTER (WHERE cefr_level IS NOT NULL) AS with_cefr,
    COUNT(*) FILTER (WHERE chunk_type IS NOT NULL) AS with_type,
    COUNT(*) FILTER (WHERE surface_en IS NOT NULL) AS with_translation,
    COUNT(*) FILTER (WHERE is_quebec_specific) AS quebec_variants
FROM chunks
GROUP BY confidence_tier
ORDER BY confidence_tier;
