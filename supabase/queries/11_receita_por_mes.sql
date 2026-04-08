-- ============================================================
-- RECEITA POR MÊS — Consolidado
-- ============================================================

SELECT
  TO_CHAR(closed_at, 'YYYY-MM') AS mes,
  COUNT(*) AS deals_ganhos,
  SUM(amount_total) AS receita,
  ROUND(AVG(amount_total) FILTER (WHERE amount_total > 0), 2) AS ticket_medio,
  COUNT(DISTINCT lead_id) AS leads_unicos
FROM deals
WHERE deal_status = 'won'
  AND closed_at IS NOT NULL
GROUP BY mes
ORDER BY mes DESC;
