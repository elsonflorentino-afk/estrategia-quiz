-- ============================================================
-- LEADS QUALIFICADOS POR ESTÁGIO — Onde estão os ≥R$100k?
-- ============================================================
-- Identifica rapidamente leads quentes travados no funil

SELECT
  l.email,
  l.name,
  l.patrimonio_cripto,
  l.patrimonio_cripto_min_k,
  l.score,
  l.score_tier,
  l.crm_current_stage,
  l.crm_pipeline,
  l.crm_total_value,
  l.first_campaign AS campanha_origem,
  l.created_at::DATE AS criado_em
FROM leads l
WHERE l.patrimonio_cripto_min_k >= 100
  AND (l.crm_deal_status = 'open' OR l.crm_deal_status IS NULL)
ORDER BY l.patrimonio_cripto_min_k DESC, l.score DESC;
