-- ============================================================
-- SCHEMA INFO — Inspeciona estrutura do banco
-- ============================================================

-- Lista todas as tabelas e contagem de rows
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Lista colunas de uma tabela específica (muda 'deals' pelo nome)
-- SELECT column_name, data_type, is_nullable, column_default
-- FROM information_schema.columns
-- WHERE table_name = 'deals' AND table_schema = 'public'
-- ORDER BY ordinal_position;

-- Lista funções (incluindo triggers)
-- SELECT proname, prorettype::regtype, pg_get_function_result(oid)
-- FROM pg_proc WHERE pronamespace = 'public'::regnamespace;
