-- ============================================================
-- RECEITA POR SEMANA — Últimos 12 meses
-- ============================================================

SELECT
  DATE_TRUNC('week', closed_at)::DATE AS semana,
  COUNT(*) AS deals_ganhos,
  SUM(amount_total) AS receita,
  AVG(amount_total) FILTER (WHERE amount_total > 0) AS ticket_medio
FROM deals
WHERE deal_status = 'won'
  AND closed_at >= NOW() - INTERVAL '12 months'
GROUP BY semana
ORDER BY semana DESC;
