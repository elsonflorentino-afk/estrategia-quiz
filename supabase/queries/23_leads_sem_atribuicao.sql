-- ============================================================
-- LEADS SEM ATRIBUIÇÃO — Diagnóstico do tracking
-- ============================================================
-- Quantos leads/deals estão entrando sem UTM?
-- Se esse número for alto, o tracking está quebrado

SELECT
  CASE
    WHEN l.first_campaign IS NOT NULL THEN 'COM atribuição'
    ELSE 'SEM atribuição'
  END AS status_utm,
  COUNT(DISTINCT l.id) AS leads,
  COUNT(DISTINCT l.id) FILTER (WHERE l.is_qualified) AS qualificados_50k,
  COUNT(DISTINCT d.id) AS deals_no_crm,
  COUNT(DISTINCT d.id) FILTER (WHERE d.deal_status = 'won') AS deals_ganhos,
  COALESCE(SUM(d.amount_total) FILTER (WHERE d.deal_status = 'won'), 0) AS receita
FROM leads l
LEFT JOIN deals d ON d.lead_id = l.id
GROUP BY status_utm
ORDER BY leads DESC;
