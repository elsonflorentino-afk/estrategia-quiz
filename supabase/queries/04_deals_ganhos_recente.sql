-- ============================================================
-- DEALS GANHOS — Últimos 30 dias
-- ============================================================

SELECT
  closed_at::DATE AS data_fechamento,
  name AS nome,
  contact_email,
  amount_total AS valor,
  pipeline_name,
  owner_name,
  EXTRACT(DAY FROM closed_at - crm_created_at)::INT AS dias_do_lead_ao_ganho
FROM deals
WHERE deal_status = 'won'
  AND closed_at >= NOW() - INTERVAL '30 days'
ORDER BY closed_at DESC;
