-- ============================================================
-- ATRIBUIÇÃO META × CRM — Leads e deals por campanha
-- ============================================================
-- Cruza first_campaign (UTM do Meta) com deals no CRM

SELECT
  COALESCE(l.first_campaign, '(sem atribuição)') AS campanha,
  COUNT(DISTINCT l.id) AS total_leads,
  COUNT(DISTINCT l.id) FILTER (WHERE l.is_qualified) AS leads_qualificados,
  COUNT(DISTINCT d.id) AS total_deals,
  COUNT(DISTINCT d.id) FILTER (WHERE d.deal_status = 'won') AS deals_ganhos,
  COUNT(DISTINCT d.id) FILTER (WHERE d.deal_status = 'lost') AS deals_perdidos,
  COALESCE(SUM(d.amount_total) FILTER (WHERE d.deal_status = 'won'), 0) AS receita,
  ROUND(
    COUNT(DISTINCT d.id) FILTER (WHERE d.deal_status = 'won')::NUMERIC
    / NULLIF(COUNT(DISTINCT l.id), 0) * 100, 2
  ) AS taxa_lead_para_ganho_pct
FROM leads l
LEFT JOIN deals d ON d.lead_id = l.id
GROUP BY l.first_campaign
ORDER BY total_leads DESC;
