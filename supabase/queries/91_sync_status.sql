-- ============================================================
-- SYNC STATUS — Quando foi o último sync e saúde dos dados
-- ============================================================

SELECT
  'deals' AS tabela,
  COUNT(*) AS total_rows,
  MAX(synced_at) AS ultimo_sync,
  MAX(crm_updated_at) AS crm_update_mais_recente,
  COUNT(*) FILTER (WHERE lead_id IS NOT NULL) AS com_lead_linkado,
  COUNT(*) FILTER (WHERE lead_id IS NULL) AS sem_link
FROM deals
UNION ALL
SELECT
  'leads',
  COUNT(*),
  MAX(updated_at),
  MAX(last_activity_at),
  COUNT(*) FILTER (WHERE crm_current_stage IS NOT NULL),
  COUNT(*) FILTER (WHERE crm_current_stage IS NULL)
FROM leads;
