-- ============================================================
-- PIPELINES RESUMO — Performance de cada pipeline
-- ============================================================

SELECT
  pipeline_name,
  COUNT(*) AS total_deals,
  COUNT(*) FILTER (WHERE deal_status = 'open') AS abertos,
  COUNT(*) FILTER (WHERE deal_status = 'won') AS ganhos,
  COUNT(*) FILTER (WHERE deal_status = 'lost') AS perdidos,
  ROUND(
    COUNT(*) FILTER (WHERE deal_status = 'won')::NUMERIC
    / NULLIF(COUNT(*), 0) * 100, 2
  ) AS taxa_conversao_pct,
  COALESCE(SUM(amount_total) FILTER (WHERE deal_status = 'won'), 0) AS receita_total,
  COALESCE(AVG(amount_total) FILTER (WHERE deal_status = 'won' AND amount_total > 0), 0) AS ticket_medio
FROM deals
GROUP BY pipeline_name
ORDER BY total_deals DESC;
