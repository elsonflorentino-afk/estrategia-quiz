"""
generate_dashboard.py
Gera o HTML completo do dashboard a partir dos dados da API.
Auto-gera narrativas com base nas variações semana a semana.
"""
import json, os, sys
from datetime import datetime

# ─── Narrativas automáticas ───────────────────────────────────

def fmt_brl(v):
    return f'R${v:,.0f}'.replace(',', '.')

def pct_change(now, before):
    if not before:
        return None
    return round((now - before) / before * 100, 1)

def narrative_week(weeks):
    """Gera texto de análise para cada semana."""
    texts = []
    for i, w in enumerate(weeks):
        d_start = w['date_start']
        d_stop  = w['date_stop']
        leads   = w['leads']
        spend   = w['spend']
        cpl     = w['cpl']

        if i == 0:
            texts.append(f'Primeira semana do mês. <strong>{leads} leads</strong> captados · {fmt_brl(spend)} investidos · CPL {fmt_brl(cpl)}.')
        else:
            prev  = weeks[i-1]
            d_cpl = pct_change(cpl, prev['cpl'])
            d_leads = pct_change(leads, prev['leads'])

            cpl_txt = ''
            if d_cpl is not None:
                if d_cpl <= -10:
                    cpl_txt = f'CPL <strong style="color:#1dd1a1">caiu {abs(d_cpl):.0f}%</strong> vs semana anterior ({fmt_brl(cpl)})'
                elif d_cpl >= 10:
                    cpl_txt = f'CPL <strong style="color:#f59e0b">subiu {d_cpl:.0f}%</strong> vs semana anterior ({fmt_brl(cpl)})'
                else:
                    cpl_txt = f'CPL estável em {fmt_brl(cpl)}'

            lead_txt = ''
            if d_leads is not None:
                if d_leads >= 10:
                    lead_txt = f'<strong style="color:#1dd1a1">{leads} leads (+{d_leads:.0f}%)</strong>'
                elif d_leads <= -10:
                    lead_txt = f'<strong style="color:#f59e0b">{leads} leads ({d_leads:.0f}%)</strong>'
                else:
                    lead_txt = f'<strong>{leads} leads</strong>'
            else:
                lead_txt = f'<strong>{leads} leads</strong>'

            texts.append(f'{lead_txt} captados · {fmt_brl(spend)} investidos · {cpl_txt}.')
    return texts

def narrative_top_creative(ads, prev_ads=None):
    """Analisa mudanças no top criativo."""
    if not ads:
        return 'Sem dados de criativos disponíveis.'
    top = ads[0]
    text = f'Melhor criativo: <strong>{top["name"][:50]}</strong> com {top["leads"]} leads e CPL {fmt_brl(top["cpl"])}.'
    if prev_ads and ads[0]['id'] != prev_ads[0]['id']:
        text += ' Houve mudança no criativo líder em relação à semana anterior.'
    return text

# ─── Geração do HTML ─────────────────────────────────────────

def build_kpi(label, value, sub, cls=''):
    return f'<div class="kpi {cls}"><div class="kl">{label}</div><div class="kv">{value}</div><div class="ks">{sub}</div></div>'

def build_group_table(groups, total_spend, total_leads):
    rows = ''
    for g in groups:
        cpl_color = ''
        if g['cpl'] and g['leads']:
            if g['cpl'] <= 40:   cpl_color = 'style="color:var(--teal)"'
            elif g['cpl'] <= 80: cpl_color = 'style="color:var(--yellow)"'
            else:                cpl_color = 'style="color:var(--red)"'
        leads_td = f'<td class="nr">{g["leads"] if g["leads"] else "—"}</td>'
        cpl_td   = f'<td class="nr" {cpl_color}>{fmt_brl(g["cpl"]) if g["leads"] else "—"}</td>'
        rows += f'''<tr>
          <td>{g["group"]}</td>
          <td class="nr">{fmt_brl(g["spend"])}</td>
          {leads_td}
          {cpl_td}
        </tr>'''

    total_cpl = round(total_spend / total_leads, 0) if total_leads else 0
    rows += f'''<tr style="font-weight:700;border-top:1px solid var(--border)">
          <td>TOTAL</td>
          <td class="nr">{fmt_brl(total_spend)}</td>
          <td class="nr">{total_leads}</td>
          <td class="nr">{fmt_brl(total_cpl)}</td>
        </tr>'''
    return f'''<table>
      <thead><tr><th>Grupo</th><th class="nr">Investimento</th><th class="nr">Leads</th><th class="nr">CPL</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>'''

def build_weekly_table(weeks, narratives):
    rows = ''
    for i, (w, narr) in enumerate(zip(weeks, narratives)):
        d_s = datetime.strptime(w['date_start'], '%Y-%m-%d').strftime('%d/%m')
        d_e = datetime.strptime(w['date_stop'],  '%Y-%m-%d').strftime('%d/%m')
        lead_color = 'g' if w['leads'] > 0 else ''
        rows += f'''<tr>
          <td><strong>S{i+1}</strong> · {d_s}–{d_e}</td>
          <td class="nr">{fmt_brl(w["spend"])}</td>
          <td class="nr">{w["impressions"]:,}</td>
          <td class="nr">{w["clicks"]:,}</td>
          <td class="nr {lead_color}" style="font-size:15px;font-weight:700">{w["leads"]}</td>
          <td class="nr">{w["ctr"]:.1f}%</td>
          <td class="nr">{fmt_brl(w["cpl"]) if w["leads"] else "—"}</td>
          <td style="font-size:11px">{narr}</td>
        </tr>'''
    return f'''<table>
      <thead><tr>
        <th>Semana</th><th class="nr">Investimento</th><th class="nr">Impressões</th>
        <th class="nr">Cliques</th><th class="nr">Leads</th><th class="nr">CTR</th>
        <th class="nr">CPL</th><th>Análise</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>'''

def build_top_ads(ads, thumbs, limit=10):
    cards = ''
    for ad in ads[:limit]:
        thumb = thumbs.get(ad['id'], '')
        img_html = (f'<img src="{thumb}" alt="" style="width:100%;height:auto;display:block">' if thumb else '<div class="cimg-ph">🎬</div>')
        cpl_color = '#1dd1a1' if ad['cpl'] <= 40 else ('#f59e0b' if ad['cpl'] <= 80 else '#ef4444')
        cards += f'''<div class="ccard">
  <div class="cimg-wrap">{img_html}</div>
  <div class="cbody">
    <div class="cname">{ad["name"][:70]}</div>
    <div class="cstats">
      <div class="cst"><div class="cst-l">Leads</div><div class="cst-v" style="color:#1dd1a1">{ad["leads"]}</div></div>
      <div class="cst"><div class="cst-l">CPL</div><div class="cst-v" style="color:{cpl_color}">{fmt_brl(ad["cpl"])}</div></div>
      <div class="cst"><div class="cst-l">Gasto</div><div class="cst-v">{fmt_brl(ad["spend"])}</div></div>
    </div>
    <div style="font-size:10px;color:var(--text3);margin-top:6px">CTR {ad["ctr"]:.1f}% · {ad.get("campaign","")[:30]}</div>
  </div>
</div>'''
    return f'<div class="gallery">{cards}</div>'

def build_qual_bar(qual):
    """Barra de patrimônio cripto."""
    fields = qual.get('pat_cripto', {})
    if not fields:
        return '<p style="color:var(--text3);font-size:12px">Sem dados de qualificação disponíveis.</p>'

    total = sum(fields.values())
    rows = ''
    colors = ['#ef4444','#f59e0b','#1dd1a1','#3b82f6','#8b5cf6']
    for i, (label, count) in enumerate(fields.items()):
        pct = round(count / total * 100) if total else 0
        color = colors[i % len(colors)]
        rows += f'''<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
          <div style="flex:0 0 120px;font-size:11px;color:var(--text2)">{label}</div>
          <div style="flex:1;background:var(--bg2);border-radius:3px;height:18px">
            <div style="width:{pct}%;background:{color};height:100%;border-radius:3px;display:flex;align-items:center;padding-left:6px;font-size:11px;font-weight:700;color:#000;min-width:24px">{count}</div>
          </div>
          <div style="flex:0 0 36px;font-size:11px;color:var(--text3);text-align:right">{pct}%</div>
        </div>'''
    return rows

def generate(meta, rd, thumbs, month_name, year):
    """Gera o HTML completo."""
    campaigns = meta.get('campaigns', [])
    ads       = meta.get('ads', [])
    weeks     = meta.get('weeks', [])
    groups    = meta.get('groups', [])

    total_spend  = sum(c['spend'] for c in campaigns)
    total_leads  = sum(c['leads'] for c in campaigns)
    total_cpl    = round(total_spend / total_leads, 0) if total_leads else 0
    total_impr   = sum(c['impressions'] for c in campaigns)
    total_clicks = sum(c['clicks'] for c in campaigns)
    total_ctr    = round(total_clicks / total_impr * 100, 1) if total_impr else 0

    # Leads LP
    lp_c4 = rd.get('lp_mentoria_boost', {}).get('contacts', 0)
    lp_ir = rd.get('lp_ir_cripto', {}).get('contacts', 0)
    total_leads_all = total_leads  # Meta já inclui leads de form; LP são adicionais
    c4_qual = rd.get('lp_mentoria_boost', {}).get('qualification', {})
    ir_qual = rd.get('lp_ir_cripto', {}).get('qualification', {})

    # Narrativas semanais
    week_narrs = narrative_week(weeks)
    top_ad_narr = narrative_top_creative(ads)

    now_str = datetime.now().strftime('%d/%m/%Y às %H:%M')

    group_table   = build_group_table(groups, total_spend, total_leads)
    weekly_table  = build_weekly_table(weeks, week_narrs)
    top_ads_html  = build_top_ads(ads, thumbs)
    qual_bar_html = build_qual_bar(c4_qual)

    # Sparkline de leads por semana (Unicode)
    spark_vals = [w['leads'] for w in weeks]
    max_v = max(spark_vals) if spark_vals else 1
    bars  = '▁▂▃▄▅▆▇█'
    spark = ''.join(bars[min(int(v / max_v * 7), 7)] for v in spark_vals)

    html = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Dashboard {month_name} {year} — Boost Research</title>
<style>
:root{{
  --bg0:#0a0a0a;--bg1:#141414;--bg2:#1c1c1c;--bg3:#242424;
  --text1:#f0f0f0;--text2:#a0a0a0;--text3:#666;
  --border:rgba(255,255,255,.08);
  --teal:#1dd1a1;--yellow:#f59e0b;--blue:#3b82f6;
  --red:#ef4444;--green:#10b981;--accent:#8b5cf6;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg0);color:var(--text1);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-size:13px;line-height:1.5}}
nav{{background:var(--bg1);border-bottom:1px solid var(--border);padding:0 20px;display:flex;gap:4px;overflow-x:auto;position:sticky;top:0;z-index:100}}
.tb{{background:none;border:none;color:var(--text2);padding:14px 16px;cursor:pointer;border-bottom:2px solid transparent;white-space:nowrap;font-size:13px;transition:.2s}}
.tb:hover{{color:var(--text1)}}
.tb.on{{color:var(--teal);border-bottom-color:var(--teal)}}
.page{{display:none;padding:20px;max-width:1200px;margin:0 auto}}
.page.on{{display:block}}
header{{background:var(--bg1);border-bottom:1px solid var(--border);padding:16px 24px;display:flex;align-items:center;justify-content:space-between}}
.logo{{font-size:18px;font-weight:700;color:var(--teal)}}
.subtitle{{font-size:12px;color:var(--text3)}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:20px}}
.kpi{{background:var(--bg1);border:1px solid var(--border);border-radius:10px;padding:14px 16px}}
.kpi.ak{{border-color:rgba(247,147,26,.3);background:rgba(247,147,26,.05)}}
.kpi.gk{{border-color:rgba(29,209,161,.3);background:rgba(29,209,161,.05)}}
.kpi.bk{{border-color:rgba(59,130,246,.3);background:rgba(59,130,246,.05)}}
.kl{{font-size:11px;color:var(--text3);text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px}}
.kv{{font-size:26px;font-weight:700;line-height:1}}
.ks{{font-size:11px;color:var(--text2);margin-top:3px}}
.box{{background:var(--bg1);border:1px solid var(--border);border-radius:10px;padding:16px;margin-bottom:16px}}
.bx-title{{font-size:13px;font-weight:600;margin-bottom:12px;color:var(--text1)}}
.bx-title small{{font-weight:400;color:var(--text3);font-size:11px}}
.g2{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px}}
table{{width:100%;border-collapse:collapse}}
th{{text-align:left;color:var(--text3);font-size:11px;text-transform:uppercase;letter-spacing:.05em;padding:6px 8px;border-bottom:1px solid var(--border)}}
td{{padding:8px;border-bottom:1px solid rgba(255,255,255,.04);font-size:12px}}
tr:last-child td{{border-bottom:none}}
tr:hover td{{background:rgba(255,255,255,.02)}}
.nr{{text-align:right}}
.g{{color:var(--teal)}}
.w{{color:var(--yellow)}}
.r{{color:var(--red)}}
.grp-hdr{{font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:var(--text3);padding:12px 0 8px;border-bottom:1px solid var(--border);margin-bottom:12px}}
.ins{{padding:10px 12px;border-radius:6px;font-size:12px;margin-top:8px}}
.ins-g{{background:rgba(29,209,161,.08);border-left:3px solid var(--teal)}}
.ins-b{{background:rgba(59,130,246,.08);border-left:3px solid var(--blue)}}
.ins-o{{background:rgba(247,147,26,.08);border-left:3px solid var(--yellow)}}
.mv{{display:flex;gap:12px;padding:12px 0;border-left:3px solid var(--teal);padding-left:14px;margin-bottom:8px}}
.mv-w{{flex:0 0 60px;font-size:11px;font-weight:700;color:var(--teal)}}
.updated{{font-size:10px;color:var(--text3);text-align:right;margin-top:8px}}
.gallery{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px}}
.ccard{{background:var(--bg3);border:1px solid var(--border);border-radius:10px;overflow:hidden;transition:border-color .2s,transform .15s}}
.ccard:hover{{border-color:var(--accent);transform:translateY(-2px)}}
.cimg-wrap{{width:100%;overflow:hidden;background:#111}}
.cimg-ph{{font-size:30px;color:var(--text2)}}
.cbody{{padding:11px}}
.cname{{font-size:10px;color:var(--text2);margin-bottom:9px;font-family:monospace;line-height:1.4;min-height:28px}}
.cstats{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:5px}}
.cst{{background:var(--bg2);border-radius:5px;padding:6px 4px;text-align:center}}
.cst-l{{font-size:9px;color:var(--text2);text-transform:uppercase;letter-spacing:.3px}}
.cst-v{{font-size:13px;font-weight:700;margin-top:2px}}
@media(max-width:640px){{.g2{{grid-template-columns:1fr}}.kpis{{grid-template-columns:1fr 1fr}}}}
</style>
</head>
<body>

<header>
  <div>
    <div class="logo">Boost Research</div>
    <div class="subtitle">Dashboard de Performance · {month_name} {year}</div>
  </div>
  <div style="font-size:11px;color:var(--text3);text-align:right">
    Atualizado automaticamente<br>{now_str}
  </div>
</header>

<nav>
  <button class="tb on" onclick="go('geral',this)">📊 Resumo Geral</button>
  <button class="tb" onclick="go('semana',this)">📅 Evolução Semanal</button>
  <button class="tb" onclick="go('criativos',this)">🎨 Criativos</button>
  <button class="tb" onclick="go('leads',this)">👥 Perfil dos Leads</button>
</nav>

<!-- ── GERAL ─────────────────────────────────────────────── -->
<div id="p-geral" class="page on">

  <div class="kpis">
    {build_kpi('Investimento', fmt_brl(total_spend), f'{month_name} {year} · todas as campanhas', 'ak')}
    {build_kpi('Impressões', f'{total_impr:,}', 'Total de visualizações', '')}
    {build_kpi('Cliques', f'{total_clicks:,}', f'CTR médio {total_ctr}%', '')}
    {build_kpi('Leads Meta', total_leads, 'Form + LP via campanhas', 'gk')}
    {build_kpi('Leads LP C4', lp_c4, 'Qualificados via LP Análise', 'bk')}
    {build_kpi('Leads LP IR', lp_ir, 'LP IR Cripto 2026', '')}
    {build_kpi('CPL Médio', fmt_brl(total_cpl), 'Custo por lead · Meta Ads', 'ak')}
  </div>

  <div class="box">
    <div class="bx-title">💰 Investimento e Leads por Grupo de Campanha</div>
    {group_table}
  </div>

  <div class="box">
    <div class="bx-title">📈 Tendência de Leads por Semana</div>
    <div style="font-size:28px;letter-spacing:4px;color:var(--teal);margin:8px 0">{spark}</div>
    <div style="font-size:11px;color:var(--text3)">Cada símbolo = 1 semana · escala relativa ao pico do mês</div>
  </div>

  <p class="updated">Dados via Meta Ads API v19.0 · Gerado automaticamente em {now_str}</p>
</div>

<!-- ── SEMANA ─────────────────────────────────────────────── -->
<div id="p-semana" class="page">

  <div class="kpis">
    {build_kpi('Investimento', fmt_brl(total_spend), f'{month_name} {year}', 'ak')}
    {build_kpi('Total de Leads', total_leads, 'Meta Ads · mês completo', 'gk')}
    {build_kpi('CPL Médio', fmt_brl(total_cpl), 'Custo por lead', 'bk')}
    {build_kpi('CTR Médio', f'{total_ctr}%', 'Taxa de cliques geral', '')}
  </div>

  <div class="box">
    <div class="bx-title">📅 Métricas Semanais — Análise Automática</div>
    <div style="overflow-x:auto">{weekly_table}</div>
    <p style="font-size:10px;color:var(--text3);margin-top:8px">
      * Variações calculadas automaticamente semana a semana · Fonte: Meta Ads API
    </p>
  </div>
</div>

<!-- ── CRIATIVOS ──────────────────────────────────────────── -->
<div id="p-criativos" class="page">

  <div class="kpis">
    {build_kpi('Total Criativos Ativos', len([a for a in ads if a["spend"]>0]), 'com investimento no mês', '')}
    {build_kpi('Melhor CPL', fmt_brl(min((a["cpl"] for a in ads if a["leads"]), default=0)), 'menor custo por lead', 'gk')}
    {build_kpi('Líder em Leads', ads[0]["leads"] if ads else 0, ads[0]["name"][:30] if ads else '', 'ak')}
  </div>

  <div class="box">
    <div class="bx-title">🏆 Top Criativos — Leads e CPL</div>
    <div class="ins ins-b" style="margin-bottom:12px">💡 {top_ad_narr}</div>
    {top_ads_html}
  </div>

  <div class="box">
    <div class="bx-title">📊 Ranking Completo</div>
    <table>
      <thead><tr>
        <th>#</th><th>Criativo</th><th>Campanha</th>
        <th class="nr">Spend</th><th class="nr">Leads</th>
        <th class="nr">CPL</th><th class="nr">CTR</th>
      </tr></thead>
      <tbody>
        {''.join(f"""<tr>
          <td style="color:var(--text3)">{i+1}</td>
          <td style="font-size:11px;max-width:200px;word-break:break-word">{a["name"][:60]}</td>
          <td style="font-size:10px;color:var(--text3)">{a["campaign"][:30]}</td>
          <td class="nr">{fmt_brl(a["spend"])}</td>
          <td class="nr g">{a["leads"]}</td>
          <td class="nr" style="color:{'#1dd1a1' if a['cpl']<=40 else '#f59e0b' if a['cpl']<=80 else '#ef4444'}">{fmt_brl(a["cpl"]) if a["leads"] else "—"}</td>
          <td class="nr">{a["ctr"]:.1f}%</td>
        </tr>""" for i, a in enumerate(ads[:20]))}
      </tbody>
    </table>
  </div>
</div>

<!-- ── LEADS ──────────────────────────────────────────────── -->
<div id="p-leads" class="page">

  <div class="kpis">
    {build_kpi('Leads Meta (Form)', total_leads, 'via formulário instantâneo', 'ak')}
    {build_kpi('Leads LP Análise', lp_c4, 'lp_mentoria_boost · qualif. completa', 'gk')}
    {build_kpi('Leads LP IR Cripto', lp_ir, 'lp_ir_cripto · qualif. completa', 'bk')}
    {build_kpi('Qualificados ≥R$50k', c4_qual.get("qualif_cripto",0), f'{c4_qual.get("pct_qualif",0)}% dos que investem em cripto', 'gk')}
  </div>

  <div class="g2">
    <div class="box">
      <div class="bx-title">₿ Patrimônio em Cripto — LP Análise <small>{c4_qual.get("investe_cripto",0)} que investem em cripto · campo condicional obrigatório</small></div>
      {qual_bar_html}
      <p style="font-size:10px;color:var(--text2);margin-top:10px">
        📌 Campo só exibido para quem responde "sim" que investe em cripto · todos os campos exibidos são obrigatórios
      </p>
    </div>
    <div class="box">
      <div class="bx-title">📊 Resumo de Qualificação — LP C4</div>
      <div style="margin-top:8px">
        {''.join(f"""<div style="display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid var(--border)">
          <span style="color:var(--text2)">{label}</span>
          <span style="color:var(--text1);font-weight:600">{val}</span>
        </div>""" for label, val in [
          ('Total leads LP C4', lp_c4),
          ('Investem em cripto', c4_qual.get('investe_cripto', 0)),
          ('Não investem em cripto', c4_qual.get('nao_cripto', 0)),
          ('Investem no tradicional', c4_qual.get('investe_trad', 0)),
          (f'Qualificados ≥R$50k cripto', c4_qual.get('qualif_cripto', 0)),
          (f'Qualificados ≥R$50k trad', c4_qual.get('qualif_trad', 0)),
        ])}
      </div>
    </div>
  </div>

</div>

<script>
function go(name, btn) {{
  document.querySelectorAll('.page').forEach(p => p.classList.remove('on'));
  document.querySelectorAll('.tb').forEach(b => b.classList.remove('on'));
  document.getElementById('p-' + name).classList.add('on');
  btn.classList.add('on');
}}
</script>
</body>
</html>'''

    return html

if __name__ == '__main__':
    with open('/tmp/meta_data.json') as f:
        meta = json.load(f)
    with open('/tmp/rd_data.json') as f:
        rd = json.load(f)

    # Thumbnails opcionais
    thumbs = {}
    if os.path.exists('/tmp/thumbs.json'):
        with open('/tmp/thumbs.json') as f:
            thumbs = json.load(f)

    now = datetime.now()
    months_pt = ['','Janeiro','Fevereiro','Março','Abril','Maio','Junho',
                 'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']

    # run_pipeline.py pode passar mês/ano via env
    month_env = os.environ.get('DASHBOARD_MONTH', '').capitalize()
    month_name = month_env if month_env else months_pt[now.month]
    year = int(os.environ.get('DASHBOARD_YEAR', now.year))

    html = generate(meta, rd, thumbs, month_name, year)

    # Caminho de saída: env var (pipeline) ou /tmp (standalone)
    out = os.environ.get('DASHBOARD_OUTPUT',
          f'/tmp/relatorio_{month_name.lower()}_{year}_boost.html')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'Dashboard gerado: {out} ({len(html):,} bytes)')
