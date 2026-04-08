-- ============================================================
-- TOP DEALS ABERTOS — Maiores valores em aberto
-- ============================================================
-- Priorização comercial: quais deals Zelia deve trabalhar primeiro

SELECT
  name AS nome,
  contact_email,
  amount_total AS valor,
  stage_name AS estagio,
  pipeline_name,
  EXTRACT(DAY FROM NOW() - crm_updated_at)::INT AS dias_sem_update
FROM deals
WHERE deal_status = 'open'
  AND amount_total > 0
ORDER BY amount_total DESC NULLS LAST
LIMIT 20;
