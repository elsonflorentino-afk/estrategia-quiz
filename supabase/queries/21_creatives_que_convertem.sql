-- ============================================================
-- CREATIVES QUE CONVERTEM — Meta × deals ganhos
-- ============================================================
-- Qual nome de criativo (first_content = ad_name) gerou os leads
-- que viraram vendas no CRM

SELECT
  COALESCE(l.first_content, '(sem UTM content)') AS creative,
  COALESCE(l.first_campaign, '(sem campanha)') AS campanha,
  COUNT(DISTINCT l.id) AS leads_gerados,
  COUNT(DISTINCT d.id) FILTER (WHERE d.deal_status = 'won') AS deals_fechados,
  SUM(d.amount_total) FILTER (WHERE d.deal_status = 'won') AS receita,
  COUNT(DISTINCT d.id) FILTER (WHERE d.deal_status = 'lost') AS deals_perdidos,
  COUNT(DISTINCT l.id) FILTER (WHERE l.is_qualified) AS qualificados_50k
FROM leads l
LEFT JOIN deals d ON d.lead_id = l.id
WHERE l.first_content IS NOT NULL
GROUP BY l.first_content, l.first_campaign
HAVING COUNT(DISTINCT l.id) >= 1
ORDER BY deals_fechados DESC NULLS LAST, receita DESC NULLS LAST;
