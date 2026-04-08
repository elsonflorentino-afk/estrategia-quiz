-- ============================================================
-- DEALS STUCK — Deals parados sem atualização há > N dias
-- ============================================================
-- Ajusta o INTERVAL conforme necessário
-- Foca nos abertos (deals perdidos/ganhos não importam)

SELECT
  stage_name,
  name AS nome_deal,
  contact_email,
  owner_name,
  amount_total,
  crm_updated_at,
  EXTRACT(DAY FROM NOW() - crm_updated_at)::INT AS dias_parado,
  pipeline_name
FROM deals
WHERE deal_status = 'open'
  AND crm_updated_at < NOW() - INTERVAL '7 days'
ORDER BY dias_parado DESC, amount_total DESC NULLS LAST
LIMIT 100;
