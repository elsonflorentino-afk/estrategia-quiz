-- ============================================================
-- ANÁLISE 4 CAMPANHAS — Perfil + CPL (Abr 2026)
-- ============================================================
-- Campanhas analisadas:
--   1. [BR][BOOST][C5-ANDROMEDA-V2][CBO][CONVERSAO-LP][Abr2026]
--   2. [BR][BOOST][C5-ANDROMEDA][CBO][CONVERSAO-LP][Abr2026]
--   3. [BR][BOOST][CONVERSAO][CBO][C4][Mar2026]
--   4. [BR][BOOST][CONSIDERACAO][CBO][C4][Mar2026]
--
-- OBS: CPL real precisa cruzar com spend do Meta (não está no Supabase).
--      Esta query devolve só contagens — rode o script Python junto pra ter CPL.

WITH campanhas AS (
  SELECT unnest(ARRAY[
    '[BR][BOOST][C5-ANDROMEDA-V2][CBO][CONVERSAO-LP][Abr2026]',
    '[BR][BOOST][C5-ANDROMEDA][CBO][CONVERSAO-LP][Abr2026]',
    '[BR][BOOST][CONVERSAO][CBO][C4][Mar2026]',
    '[BR][BOOST][CONSIDERACAO][CBO][C4][Mar2026]'
  ]) AS nome
),
leads_filtrados AS (
  SELECT l.*
  FROM leads l
  WHERE l.first_campaign IN (SELECT nome FROM campanhas)
)

-- ====================================================
-- BLOCO 1 — Resumo geral por campanha
-- ====================================================
SELECT
  '1-RESUMO' AS bloco,
  first_campaign AS campanha,
  COUNT(*) AS total_leads,
  COUNT(*) FILTER (WHERE is_qualified) AS qualificados,
  ROUND(
    COUNT(*) FILTER (WHERE is_qualified)::NUMERIC
    / NULLIF(COUNT(*), 0) * 100, 1
  ) AS taxa_qualif_pct,
  COUNT(*) FILTER (WHERE patrimonio_cripto_min_k >= 100) AS leads_100k_plus,
  ROUND(AVG(score), 1) AS score_medio,
  COUNT(*) FILTER (WHERE crm_deal_status = 'won') AS deals_ganhos,
  COUNT(*) FILTER (WHERE crm_deal_status = 'lost') AS deals_perdidos,
  COUNT(*) FILTER (WHERE crm_deal_status IS NULL OR crm_deal_status = 'open') AS deals_abertos,
  MIN(created_at)::date AS primeiro_lead,
  MAX(created_at)::date AS ultimo_lead
FROM leads_filtrados
GROUP BY first_campaign
ORDER BY total_leads DESC;


-- ====================================================
-- BLOCO 2 — Perfil por faixa de patrimônio cripto
-- ====================================================
SELECT
  '2-PERFIL-CRIPTO' AS bloco,
  first_campaign AS campanha,
  CASE
    WHEN patrimonio_cripto_min_k >= 500 THEN '01 — ≥R$500k'
    WHEN patrimonio_cripto_min_k >= 200 THEN '02 — R$200-500k'
    WHEN patrimonio_cripto_min_k >= 100 THEN '03 — R$100-200k'
    WHEN patrimonio_cripto_min_k >= 50  THEN '04 — R$50-100k'
    WHEN patrimonio_cripto_min_k >= 10  THEN '05 — R$10-50k'
    WHEN patrimonio_cripto_min_k >= 1   THEN '06 — <R$10k'
    ELSE '07 — Não respondeu'
  END AS faixa,
  COUNT(*) AS leads,
  ROUND(
    COUNT(*)::NUMERIC
    / SUM(COUNT(*)) OVER (PARTITION BY first_campaign) * 100, 1
  ) AS pct_da_campanha
FROM leads_filtrados
GROUP BY first_campaign, faixa
ORDER BY first_campaign, faixa;


-- ====================================================
-- BLOCO 3 — Perfil tradicional (pra cruzar com cripto)
-- ====================================================
SELECT
  '3-PERFIL-TRAD' AS bloco,
  first_campaign AS campanha,
  CASE
    WHEN patrimonio_tradicional_min_k >= 500 THEN '01 — ≥R$500k'
    WHEN patrimonio_tradicional_min_k >= 200 THEN '02 — R$200-500k'
    WHEN patrimonio_tradicional_min_k >= 100 THEN '03 — R$100-200k'
    WHEN patrimonio_tradicional_min_k >= 50  THEN '04 — R$50-100k'
    WHEN patrimonio_tradicional_min_k >= 10  THEN '05 — R$10-50k'
    WHEN patrimonio_tradicional_min_k >= 1   THEN '06 — <R$10k'
    ELSE '07 — Não respondeu'
  END AS faixa,
  COUNT(*) AS leads
FROM leads_filtrados
GROUP BY first_campaign, faixa
ORDER BY first_campaign, faixa;


-- ====================================================
-- BLOCO 4 — Por conjunto (first_term = adset)
-- ====================================================
SELECT
  '4-POR-ADSET' AS bloco,
  first_campaign AS campanha,
  COALESCE(first_term, '(sem adset)') AS adset,
  COUNT(*) AS leads,
  COUNT(*) FILTER (WHERE is_qualified) AS qualif,
  COUNT(*) FILTER (WHERE patrimonio_cripto_min_k >= 100) AS leads_100k_plus
FROM leads_filtrados
GROUP BY first_campaign, first_term
ORDER BY first_campaign, leads DESC;


-- ====================================================
-- BLOCO 5 — Top criativos (first_content = ad name)
-- ====================================================
SELECT
  '5-POR-CRIATIVO' AS bloco,
  first_campaign AS campanha,
  COALESCE(first_content, '(sem criativo)') AS criativo,
  COUNT(*) AS leads,
  COUNT(*) FILTER (WHERE is_qualified) AS qualif,
  COUNT(*) FILTER (WHERE patrimonio_cripto_min_k >= 100) AS leads_100k_plus
FROM leads_filtrados
GROUP BY first_campaign, first_content
ORDER BY first_campaign, leads DESC;
