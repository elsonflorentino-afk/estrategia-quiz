#!/bin/bash
# ============================================================
# run_query.sh — Roda uma query .sql no Supabase via REST
# ============================================================
# Uso:
#   export SUPABASE_URL="https://dvvfnrdvhkjfovhfqiow.supabase.co"
#   export SUPABASE_SERVICE_ROLE_KEY="sb_secret_xpV9g..."
#   ./scripts/run_query.sh supabase/queries/01_funil_atual.sql
# ============================================================
set -e

if [ -z "$1" ]; then
  echo "Uso: $0 <arquivo.sql>"
  echo ""
  echo "Queries disponíveis:"
  ls -1 supabase/queries/*.sql 2>/dev/null | sed 's|supabase/queries/|  |'
  exit 1
fi

if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_SERVICE_ROLE_KEY" ]; then
  echo "ERROR: exporte SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY"
  exit 1
fi

FILE="$1"
if [ ! -f "$FILE" ]; then
  echo "ERROR: arquivo não encontrado: $FILE"
  exit 1
fi

# Lê o SQL e remove comentários de linha inteira
SQL=$(cat "$FILE")

# Supabase não tem endpoint genérico de "run SQL" via REST (só via pg connection)
# Então pra SELECTs simples usamos o PostgREST apontando pra tabela/view
# Pra SQLs complexos, precisa usar psql direto ou pgAdmin

echo "================================================"
echo "Arquivo: $FILE"
echo "================================================"
echo ""
echo "⚠️  PostgREST não suporta SQL arbitrário via HTTP."
echo ""
echo "Pra rodar, use uma dessas opções:"
echo ""
echo "1. Cola o conteúdo no SQL Editor do Supabase:"
echo "   https://supabase.com/dashboard/project/dvvfnrdvhkjfovhfqiow/sql/new"
echo ""
echo "2. Use psql (se tiver a DATABASE_URL):"
echo "   psql \$DATABASE_URL -f $FILE"
echo ""
echo "3. Copie o SQL abaixo:"
echo "------------------------------------------------"
cat "$FILE"
echo "------------------------------------------------"
