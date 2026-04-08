# Biblioteca de Queries SQL — boost-intelligence

Queries prontas pra colar no **SQL Editor** do Supabase (https://supabase.com/dashboard/project/dvvfnrdvhkjfovhfqiow/sql/new).

## Como usar

### Opção 1: Copy/paste
Abre o arquivo .sql → copia → cola no SQL Editor → **Run**.

### Opção 2: Salvar como Snippet no Supabase
No SQL Editor, após colar uma query, clica em **Save** (ou ícone de disquete) → dá um nome → fica salva na aba "Private" ou "Shared" no menu lateral.

### Opção 3: Rodar via linha de comando
```bash
# Requer: SUPABASE_SERVICE_ROLE_KEY exportada
./scripts/run_query.sh supabase/queries/funil-atual.sql
```

## Índice de queries

### 📊 Funil & Pipeline
| Arquivo | Descrição |
|---|---|
| `01_funil_atual.sql` | Foto do funil agora (deals por estágio) |
| `02_pipelines_resumo.sql` | Resumo de cada pipeline (total, abertos, ganhos, perdidos) |
| `03_deals_stuck.sql` | Deals parados há mais de N dias sem mudança de estágio |
| `04_deals_ganhos_recente.sql` | Últimos 30 dias de deals ganhos |
| `05_top_deals_abertos.sql` | Top 20 deals abertos por valor |

### 💰 Receita & Conversão
| Arquivo | Descrição |
|---|---|
| `10_receita_por_semana.sql` | Receita fechada por semana (últimos 12 meses) |
| `11_receita_por_mes.sql` | Receita mensal consolidada |
| `12_taxa_conversao_por_estagio.sql` | Taxa de avanço entre estágios |
| `13_ticket_medio_evolucao.sql` | Evolução do ticket médio mês a mês |

### 🎯 Atribuição Meta Ads × CRM
| Arquivo | Descrição |
|---|---|
| `20_atribuicao_campanha.sql` | Leads × deals por campanha Meta |
| `21_creatives_que_convertem.sql` | Ad creatives que geraram deals fechados |
| `22_cac_por_campanha.sql` | Custo por deal ganho por campanha (precisa tabela ads) |
| `23_leads_sem_atribuicao.sql` | Leads sem UTM que viraram deals |

### 👤 Perfil & Qualificação
| Arquivo | Descrição |
|---|---|
| `30_perfil_patrimonio.sql` | Distribuição de leads por faixa de patrimônio |
| `31_leads_qualificados_por_estagio.sql` | Onde estão os leads ≥R$100k no funil |
| `32_conversao_por_patrimonio.sql` | Taxa de fechamento por faixa de patrimônio |

### ⚙️ Operacional
| Arquivo | Descrição |
|---|---|
| `90_refresh_views.sql` | Refrescar todas as materialized views |
| `91_sync_status.sql` | Status do sync (quando foi o último) |
| `92_limpeza_duplicados.sql` | Detectar e tratar possíveis duplicados |
| `99_schema_info.sql` | Inspecionar schema do banco |

## Convenções

- **SELECT only** por padrão — queries que modificam dados têm `-- WRITE:` no topo
- **Nomes em português** pra facilitar leitura do time
- **Comentários** explicando o "por que" da query, não só o "o que"
- **Parâmetros** como variáveis no topo (ex: `DATA_INICIAL := '2026-03-01'`)
