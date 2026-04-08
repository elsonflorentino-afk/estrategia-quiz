-- ============================================================
-- REFRESH VIEWS — Atualiza todas as materialized views
-- ============================================================
-- Rodar manualmente ou via cron sempre que os dados mudarem significativamente

REFRESH MATERIALIZED VIEW v_lead_journey;
REFRESH MATERIALIZED VIEW v_creative_performance;
REFRESH MATERIALIZED VIEW v_funil_completo;
REFRESH MATERIALIZED VIEW v_creative_crm_performance;

-- Confirmar
SELECT 'v_lead_journey' AS view_name, COUNT(*) AS rows FROM v_lead_journey
UNION ALL
SELECT 'v_creative_performance', COUNT(*) FROM v_creative_performance
UNION ALL
SELECT 'v_funil_completo', COUNT(*) FROM v_funil_completo
UNION ALL
SELECT 'v_creative_crm_performance', COUNT(*) FROM v_creative_crm_performance;
