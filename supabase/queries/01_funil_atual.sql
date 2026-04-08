-- ============================================================
-- FUNIL ATUAL — Foto dos deals por estágio agora
-- ============================================================
-- Por quê: mostra instantaneamente onde os deals estão parados
-- Uso: abrir toda manhã pra ver o estado do pipeline

SELECT
  stage_name,
  COUNT(*) AS total,
  COUNT(*) FILTER (WHERE deal_status = 'open') AS abertos,
  COUNT(*) FILTER (WHERE deal_status = 'won') AS ganhos,
  COUNT(*) FILTER (WHERE deal_status = 'lost') AS perdidos,
  COALESCE(SUM(amount_total), 0) AS valor_total,
  COALESCE(SUM(amount_total) FILTER (WHERE deal_status = 'won'), 0) AS receita_ganha
FROM deals
GROUP BY stage_name
ORDER BY total DESC;
