-- The 427 rows are ISCO-08 occupation codes, not workers. These summaries are
-- unweighted code counts and must not be interpreted as employment shares.
CREATE VIEW occupation_profile AS
SELECT exposure_group,
       COUNT(*) AS occupation_count,
       ROUND(AVG(mean_score), 3) AS unweighted_mean_score,
       MIN(mean_score) AS min_score,
       MAX(mean_score) AS max_score
FROM occupations
GROUP BY exposure_group;

-- This view checks the four exposed groups against the 112 cited in the brief.
CREATE VIEW exposure_reconciliation AS
SELECT SUM(CASE WHEN exposure_group LIKE 'gradient_%' THEN 1 ELSE 0 END) AS exposed_codes,
       COUNT(*) AS all_codes
FROM occupations;

-- Reproduces the six editorial examples from the complete Annex A1 extract.
CREATE VIEW story_occupations AS
SELECT s.display_order, o.isco08_code, s.label_vi, o.occupation_name_en,
       o.exposure_group, o.mean_score, o.sd_score, o.source_page, s.color
FROM selected_occupations AS s
JOIN occupations AS o USING (isco08_code)
ORDER BY s.display_order;

-- Independent cross-check: aggregate the paper-linked ISCO task scores, then
-- compare with the mean printed in Annex A1. The comparison exposes source
-- differences; it does not silently replace the published annex value.
CREATE VIEW task_score_reconciliation AS
SELECT o.isco08_code,
       o.occupation_name_en,
       o.exposure_group,
       COUNT(t.task_order) AS task_rows,
       o.mean_score AS annex_mean_score,
       ROUND(AVG(t.task_score), 4) AS task_mean_score,
       ROUND(ABS(o.mean_score - AVG(t.task_score)), 4) AS absolute_gap
FROM occupations AS o
LEFT JOIN tasks AS t USING (isco08_code)
GROUP BY o.isco08_code;
