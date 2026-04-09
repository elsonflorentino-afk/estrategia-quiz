-- ============================================================
-- VIEW pública de qualificação de leads
-- ============================================================
-- Expõe só campos agregados (sem email/telefone/nome)
-- usados pelo dashboard /painel/qualificacao/
--
-- Por que view em vez de policy direta na tabela leads:
--   - Evita expor PII (email, phone, name)
--   - Simplifica RLS (view roda com privilégios do owner)
--   - Dashboard público pode ler via publishable key
--
-- Segurança: RLS não se aplica a views por padrão no Postgres.
-- Como owner da view é o superuser, e GRANT SELECT é feito pro anon,
-- o dashboard consegue ler sem expor dados sensíveis.

DROP VIEW IF EXISTS v_leads_qualificacao;

CREATE VIEW v_leads_qualificacao AS
SELECT
  id,
  created_at,
  is_qualified,
  patrimonio_cripto_min_k,
  patrimonio_tradicional_min_k,
  first_campaign,
  first_content,
  first_term,
  first_source,
  first_medium,
  score,
  score_tier,
  funnel_stage
FROM leads;

GRANT SELECT ON v_leads_qualificacao TO anon, authenticated;

-- Validação
SELECT COUNT(*) AS total_linhas_visiveis FROM v_leads_qualificacao;
