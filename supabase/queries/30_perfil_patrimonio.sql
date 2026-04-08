-- ============================================================
-- PERFIL DE PATRIMÔNIO — Distribuição dos leads
-- ============================================================

SELECT
  CASE
    WHEN patrimonio_cripto_min_k >= 1000 THEN '01 — ≥R$1M'
    WHEN patrimonio_cripto_min_k >= 500 THEN '02 — R$500k-1M'
    WHEN patrimonio_cripto_min_k >= 200 THEN '03 — R$200-500k'
    WHEN patrimonio_cripto_min_k >= 100 THEN '04 — R$100-200k'
    WHEN patrimonio_cripto_min_k >= 50 THEN '05 — R$50-100k'
    WHEN patrimonio_cripto_min_k >= 10 THEN '06 — R$10-50k'
    WHEN patrimonio_cripto_min_k >= 1 THEN '07 — <R$10k'
    ELSE '08 — Não respondeu'
  END AS faixa_patrimonio_cripto,
  COUNT(*) AS total_leads,
  COUNT(*) FILTER (WHERE crm_deal_status = 'won') AS ganhos,
  COUNT(*) FILTER (WHERE crm_deal_status = 'lost') AS perdidos,
  ROUND(AVG(score), 1) AS score_medio
FROM leads
GROUP BY faixa_patrimonio_cripto
ORDER BY faixa_patrimonio_cripto;
