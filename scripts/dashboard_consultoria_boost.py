#!/usr/bin/env python3
"""
Dashboard C4 — Advisory/Consultoria Boost Research
Campanha completa: Awareness → Consideração → Conversão

Rodar: python3 dashboard_consultoria_boost.py
"""

import requests
import json
import os
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURAÇÃO
# ─────────────────────────────────────────────

ACCESS_TOKEN  = os.environ.get("META_ACCESS_TOKEN", "")
API           = "https://graph.facebook.com/v21.0"

BUDGET_MENSAL = 40000  # R$40.000/mês
CPL_OK        = 50.0
CPL_ATENCAO   = 60.0
CPL_CORTE     = 75.0

CTR_FEED_OK   = 1.5   # %
CTR_REEL_OK   = 2.5   # %
FREQ_OK       = 2.5
FREQ_ATENCAO  = 3.0
FREQ_CORTE    = 4.0

# Campanhas C4
CAMPANHAS = {
    "120245572094120651":  {"nome": "AWARENESS",       "funil": "Topo",  "budget_pct": 20, "budget": 8000},
    "120245573637600651":  {"nome": "CONSIDERAÇÃO",    "funil": "Meio",  "budget_pct": 39, "budget": 15600},
    "120245573868070651":  {"nome": "CONVERSÃO LP",    "funil": "Fundo", "budget_pct": 36, "budget": 14400},
    "120245573954880651":  {"nome": "CONVERSÃO FORM",  "funil": "Fundo", "budget_pct": 5,  "budget": 2000},
}

# Vídeos para hook rate
VIDEOS = {
    "1857461861625526": {"nome": "V1", "angulo": "Reframe método",      "hook": "Cripto não é sorte"},
    "1476013884052839": {"nome": "V2", "angulo": "Qualificação + prova","hook": "Já tem 100k reais?"},
    "2447022672410844": {"nome": "V3", "angulo": "Proteção + renda",    "hook": "Stablecoins + BTC"},
    "1646738023127708": {"nome": "V4", "angulo": "Apresentação serviço","hook": "Sabe tudo que faz?"},
    "2734100470297743": {"nome": "V5", "angulo": "Qualificação v2",     "hook": "100k em cripto?"},
    "975273124837816":  {"nome": "V6", "angulo": "Espelho trad",        "hook": "Você entende ações..."},
    "1240836711571444": {"nome": "V7", "angulo": "Dor sem processo",    "hook": "Sem processo = refém"},
}

# ─────────────────────────────────────────────
# FETCH
# ─────────────────────────────────────────────

def fetch_insights(obj_id, level="campaign"):
    r = requests.get(f"{API}/{obj_id}/insights", params={
        "fields": "spend,impressions,clicks,ctr,actions,cost_per_action_type,reach,frequency,video_thruplay_watched_actions,video_p25_watched_actions,video_p50_watched_actions",
        "date_preset": "maximum",
        "access_token": ACCESS_TOKEN,
    }, timeout=15)
    data = r.json().get("data", [])
    return data[0] if data else {}

def fetch_adsets(campaign_id):
    r = requests.get(f"{API}/{campaign_id}/adsets", params={
        "fields": "id,name,status,daily_budget,bid_amount,optimization_goal",
        "access_token": ACCESS_TOKEN,
    }, timeout=15)
    return r.json().get("data", [])

def fetch_adset_insights(adset_id):
    r = requests.get(f"{API}/{adset_id}/insights", params={
        "fields": "spend,impressions,clicks,ctr,actions,cost_per_action_type,reach,frequency",
        "date_preset": "maximum",
        "access_token": ACCESS_TOKEN,
    }, timeout=15)
    data = r.json().get("data", [])
    return data[0] if data else {}

def get_leads(ins):
    for a in ins.get("actions", []):
        if a["action_type"] in ("lead", "onsite_conversion.lead_grouped", "leadgen_other"):
            return int(float(a.get("value", 0)))
    return 0

def get_cpl(ins):
    for a in ins.get("cost_per_action_type", []):
        if a["action_type"] in ("lead", "onsite_conversion.lead_grouped", "leadgen_other"):
            return float(a.get("value", 0))
    return 0.0

def get_hook_rate(ins):
    """Hook rate = video_p25_watched / impressions * 100"""
    impressions = float(ins.get("impressions", 0))
    if impressions == 0:
        return 0.0
    for a in ins.get("video_p25_watched_actions", []):
        return round(float(a.get("value", 0)) / impressions * 100, 1)
    return 0.0

def safe_float(val, default=0.0):
    try:
        return float(val)
    except:
        return default

# ─────────────────────────────────────────────
# BUILD
# ─────────────────────────────────────────────

def build_data():
    print("Buscando dados da Meta API...")

    campanhas_data = []
    total_spend = total_leads = total_clicks = total_impressions = 0

    for camp_id, meta in CAMPANHAS.items():
        ins = fetch_insights(camp_id)
        spend  = safe_float(ins.get("spend", 0))
        leads  = get_leads(ins)
        cpl    = get_cpl(ins)
        clicks = safe_float(ins.get("clicks", 0))
        impr   = safe_float(ins.get("impressions", 0))
        ctr    = safe_float(ins.get("ctr", 0))
        freq   = safe_float(ins.get("frequency", 0))

        print(f"  → {meta['nome']}: R${spend:.2f} | {leads} leads | CPL R${cpl:.2f} | freq {freq:.2f}")

        # Busca adsets da campanha
        adsets_raw = fetch_adsets(camp_id)
        adsets = []
        for ads in adsets_raw:
            ads_ins = fetch_adset_insights(ads["id"])
            ads_spend  = safe_float(ads_ins.get("spend", 0))
            ads_leads  = get_leads(ads_ins)
            ads_cpl    = get_cpl(ads_ins)
            ads_clicks = safe_float(ads_ins.get("clicks", 0))
            ads_ctr    = safe_float(ads_ins.get("ctr", 0))
            ads_freq   = safe_float(ads_ins.get("frequency", 0))
            ads_impr   = safe_float(ads_ins.get("impressions", 0))
            hook       = get_hook_rate(ads_ins)

            adsets.append({
                "id":     ads["id"],
                "name":   ads.get("name", ""),
                "status": ads.get("status", ""),
                "spend":  ads_spend,
                "leads":  ads_leads,
                "cpl":    ads_cpl,
                "clicks": int(ads_clicks),
                "impr":   int(ads_impr),
                "ctr":    round(ads_ctr, 2) if ads_ctr < 1 else round(ads_ctr * 100, 2),
                "freq":   round(ads_freq, 2),
                "hook":   hook,
            })

        total_spend      += spend
        total_leads      += leads
        total_clicks     += clicks
        total_impressions+= impr

        campanhas_data.append({
            "id":      camp_id,
            "nome":    meta["nome"],
            "funil":   meta["funil"],
            "budget":  meta["budget"],
            "budget_pct": meta["budget_pct"],
            "spend":   spend,
            "leads":   leads,
            "cpl":     cpl,
            "clicks":  int(clicks),
            "impr":    int(impr),
            "ctr":     round(ctr, 2) if ctr < 1 else round(ctr * 100, 2),
            "freq":    round(freq, 2),
            "adsets":  adsets,
        })

    total_cpl = total_spend / total_leads if total_leads > 0 else 0

    return {
        "timestamp":    datetime.now().strftime("%d/%m/%Y %H:%M"),
        "campanhas":    campanhas_data,
        "total": {
            "spend":       total_spend,
            "leads":       total_leads,
            "cpl":         total_cpl,
            "clicks":      int(total_clicks),
            "impressions": int(total_impressions),
            "budget_pct":  round((total_spend / BUDGET_MENSAL) * 100, 1),
        },
    }

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def brl(val):
    return f"R${val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def cpl_class(cpl):
    if cpl == 0:          return "neutral"
    if cpl <= CPL_OK:     return "ok"
    if cpl <= CPL_ATENCAO:return "warn"
    return "danger"

def ctr_class(ctr, tipo="feed"):
    target = CTR_REEL_OK if tipo == "reel" else CTR_FEED_OK
    if ctr == 0:          return "neutral"
    if ctr >= target:     return "ok"
    if ctr >= target*0.7: return "warn"
    return "danger"

def freq_class(freq):
    if freq == 0:              return "neutral"
    if freq <= FREQ_OK:        return "ok"
    if freq <= FREQ_ATENCAO:   return "warn"
    return "danger"

def hook_class(hook):
    if hook == 0:   return "neutral"
    if hook >= 28:  return "ok"
    if hook >= 20:  return "warn"
    return "danger"

def funil_color(funil):
    return {"Topo": "#4a9de0", "Meio": "#f0a030", "Fundo": "#4caf7d"}.get(funil, "#555")

# ─────────────────────────────────────────────
# HTML
# ─────────────────────────────────────────────

def generate_html(d):
    total = d["total"]
    ts    = d["timestamp"]
    no_data = total["spend"] == 0

    # Alertas
    alerts = []
    for c in d["campanhas"]:
        if c["cpl"] > CPL_CORTE and c["cpl"] > 0:
            alerts.append(f"🔴 {c['nome']}: CPL {brl(c['cpl'])} — ACIMA DO CORTE ({brl(CPL_CORTE)}) → considerar pausar conjuntos")
        elif c["cpl"] > CPL_ATENCAO and c["cpl"] > 0:
            alerts.append(f"⚠️ {c['nome']}: CPL {brl(c['cpl'])} — em atenção (acima de {brl(CPL_ATENCAO)})")
        if c["freq"] > FREQ_CORTE and c["freq"] > 0:
            alerts.append(f"🔴 {c['nome']}: Frequência {c['freq']} — fadiga de criativo ativa")
        elif c["freq"] > FREQ_ATENCAO and c["freq"] > 0:
            alerts.append(f"⚠️ {c['nome']}: Frequência {c['freq']} — monitorar fadiga")
        for ads in c["adsets"]:
            if ads["cpl"] > CPL_CORTE and ads["cpl"] > 0:
                alerts.append(f"🔴 Conjunto '{ads['name']}': CPL {brl(ads['cpl'])} → pausar após 48h")

    if total["budget_pct"] >= 80:
        alerts.append(f"🔴 Budget {total['budget_pct']}% consumido — atenção ao limite mensal")

    alerts_html = ""
    if alerts:
        items = "".join(f'<div class="alert-item">{a}</div>' for a in alerts)
        alerts_html = f'<div class="alerts-box">{items}</div>'
    else:
        alerts_html = '<div class="alerts-box ok-box">✅ Tudo dentro dos parâmetros — nenhum alerta ativo</div>'

    # Cards de campanha
    camp_cards = ""
    for c in d["campanhas"]:
        spend_pct = round((c["spend"] / c["budget"]) * 100, 1) if c["budget"] > 0 else 0
        cpl_c  = cpl_class(c["cpl"])
        freq_c = freq_class(c["freq"])
        fc     = funil_color(c["funil"])

        # Adsets rows
        adset_rows = ""
        for ads in c["adsets"]:
            status_dot = "🟢" if ads["status"] == "ACTIVE" else "⏸"
            adset_rows += f"""
            <tr>
              <td>{status_dot} {ads['name'][:40]}</td>
              <td>{brl(ads['spend'])}</td>
              <td>{ads['leads']}</td>
              <td class="cpl-cell {cpl_class(ads['cpl'])}">{brl(ads['cpl']) if ads['cpl'] > 0 else '—'}</td>
              <td class="{ctr_class(ads['ctr'])}">{ads['ctr']}%</td>
              <td class="{freq_class(ads['freq'])}">{ads['freq'] if ads['freq'] > 0 else '—'}</td>
              <td class="{hook_class(ads['hook'])}">{ads['hook']}% {'⚠️' if 0 < ads['hook'] < 20 else ''}</td>
            </tr>"""

        camp_cards += f"""
        <div class="camp-card">
          <div class="camp-header">
            <div>
              <span class="funil-badge" style="background:{fc}20;color:{fc};">{c['funil']}</span>
              <span class="camp-name">{c['nome']}</span>
            </div>
            <div class="camp-budget-info">{brl(c['budget'])}/mês · {c['budget_pct']}% do total</div>
          </div>

          <div class="camp-kpis">
            <div class="ckpi">
              <div class="ckpi-label">Gasto</div>
              <div class="ckpi-val">{brl(c['spend'])}</div>
              <div class="ckpi-sub">de {brl(c['budget'])} · {spend_pct}%</div>
              <div class="mini-bar-wrap"><div class="mini-bar" style="width:{min(spend_pct,100)}%;background:{fc};"></div></div>
            </div>
            <div class="ckpi">
              <div class="ckpi-label">Leads</div>
              <div class="ckpi-val">{c['leads']}</div>
              <div class="ckpi-sub">{c['clicks']:,} cliques</div>
            </div>
            <div class="ckpi {'ckpi-accent' if 0 < c['cpl'] <= CPL_OK else ''}">
              <div class="ckpi-label">CPL</div>
              <div class="ckpi-val {cpl_c}">{brl(c['cpl']) if c['cpl'] > 0 else '—'}</div>
              <div class="ckpi-sub">meta: {brl(CPL_OK)}</div>
            </div>
            <div class="ckpi">
              <div class="ckpi-label">CTR</div>
              <div class="ckpi-val {ctr_class(c['ctr'])}">{c['ctr']}%</div>
              <div class="ckpi-sub">meta feed: {CTR_FEED_OK}%</div>
            </div>
            <div class="ckpi">
              <div class="ckpi-label">Frequência</div>
              <div class="ckpi-val {freq_c}">{c['freq'] if c['freq'] > 0 else '—'}</div>
              <div class="ckpi-sub">corte: {FREQ_CORTE}</div>
            </div>
          </div>

          {'<div class="no-adset-data">Sem dados de conjuntos ainda</div>' if not c["adsets"] else f"""
          <div class="adset-table-wrap">
            <table class="adset-table">
              <thead>
                <tr><th>Conjunto</th><th>Gasto</th><th>Leads</th><th>CPL</th><th>CTR</th><th>Freq</th><th>Hook Rate</th></tr>
              </thead>
              <tbody>{adset_rows}</tbody>
            </table>
          </div>"""}
        </div>"""

    # Semáforo de benchmarks
    semaforo_items = [
        ("CPL Meta", brl(CPL_OK), brl(CPL_ATENCAO), brl(CPL_CORTE), brl(total["cpl"]) if total["cpl"] > 0 else "—", cpl_class(total["cpl"])),
        ("CTR Feed", f"{CTR_FEED_OK}%", "1.0%", "<0.8%", f"{total.get('ctr', 0):.2f}%", "neutral"),
        ("CTR Reels", f"{CTR_REEL_OK}%", "1.5%", "<1.0%", "—", "neutral"),
        ("Frequência", f"<{FREQ_OK}", f"<{FREQ_ATENCAO}", f">{FREQ_CORTE}", "—", "neutral"),
        ("Hook Rate", ">28%", ">20%", "<15%", "—", "neutral"),
    ]

    sem_rows = ""
    for label, ok, warn, danger, atual, cls in semaforo_items:
        sem_rows += f"""
        <tr>
          <td style="color:#aaa;">{label}</td>
          <td style="color:#4caf7d;">{ok}</td>
          <td style="color:#f0a030;">{warn}</td>
          <td style="color:#e05555;">{danger}</td>
          <td class="cpl-cell {cls}" style="font-weight:700;">{atual}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Dashboard Advisory C4 — Boost Research</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #0a0a0a; color: #ccc; font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 14px; }}

  .header {{ background: #111; border-bottom: 1px solid #1e1e1e; padding: 24px 32px; display: flex; justify-content: space-between; align-items: center; }}
  .header h1 {{ font-size: 18px; font-weight: 700; color: #fff; }}
  .header .sub {{ font-size: 12px; color: #555; margin-top: 4px; }}
  .ts {{ font-size: 12px; color: #444; }}
  .container {{ padding: 32px; max-width: 1300px; margin: 0 auto; }}
  .section-title {{ font-size: 11px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: #444; margin-bottom: 16px; }}

  /* KPIs globais */
  .kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; margin-bottom: 32px; }}
  .kpi {{ background: #111; border: 1px solid #1e1e1e; border-radius: 6px; padding: 20px; }}
  .kpi .label {{ font-size: 11px; color: #555; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 8px; }}
  .kpi .value {{ font-size: 26px; font-weight: 700; color: #fff; }}
  .kpi .sub {{ font-size: 12px; color: #444; margin-top: 4px; }}
  .kpi.accent {{ border-color: #00bfa6; }}
  .kpi.accent .value {{ color: #00bfa6; }}

  /* Barra budget */
  .budget-bar-wrap {{ background: #1a1a1a; border-radius: 4px; height: 6px; margin-top: 8px; overflow: hidden; }}
  .budget-bar {{ height: 100%; background: #00bfa6; border-radius: 4px; }}

  /* Alertas */
  .alerts-box {{ background: #1a1010; border: 1px solid #3a1e1e; border-radius: 6px; padding: 16px 20px; margin-bottom: 32px; }}
  .alerts-box.ok-box {{ background: #0d1a12; border-color: #1e3a25; color: #4caf7d; }}
  .alert-item {{ color: #e88; font-size: 13px; padding: 5px 0; border-bottom: 1px solid #2a1a1a; }}
  .alert-item:last-child {{ border-bottom: none; }}

  /* Cards de campanha */
  .camp-card {{ background: #111; border: 1px solid #1e1e1e; border-radius: 8px; padding: 24px; margin-bottom: 24px; }}
  .camp-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }}
  .camp-name {{ font-size: 16px; font-weight: 700; color: #fff; margin-left: 10px; }}
  .camp-budget-info {{ font-size: 12px; color: #444; }}
  .funil-badge {{ font-size: 10px; font-weight: 700; padding: 3px 10px; border-radius: 3px; letter-spacing: 0.08em; text-transform: uppercase; }}

  .camp-kpis {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 20px; }}
  .ckpi {{ background: #161616; border-radius: 4px; padding: 14px; }}
  .ckpi-label {{ font-size: 10px; color: #555; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 6px; }}
  .ckpi-val {{ font-size: 20px; font-weight: 700; color: #fff; }}
  .ckpi-sub {{ font-size: 11px; color: #444; margin-top: 4px; }}
  .mini-bar-wrap {{ background: #222; border-radius: 2px; height: 3px; margin-top: 8px; }}
  .mini-bar {{ height: 100%; border-radius: 2px; }}

  /* Status cores inline */
  .ok      {{ color: #4caf7d; }}
  .warn    {{ color: #f0a030; }}
  .danger  {{ color: #e05555; }}
  .neutral {{ color: #555; }}

  /* Tabelas adsets */
  .adset-table-wrap {{ overflow-x: auto; border-radius: 4px; border: 1px solid #1a1a1a; }}
  .adset-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  .adset-table th {{ background: #161616; color: #444; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; padding: 10px 14px; text-align: left; }}
  .adset-table td {{ padding: 10px 14px; border-top: 1px solid #1a1a1a; color: #aaa; }}
  .adset-table tr:hover td {{ background: #141414; }}
  .cpl-cell {{ font-weight: 700; }}
  .no-adset-data {{ text-align: center; padding: 24px; color: #333; font-size: 13px; }}

  /* Semáforo */
  .sem-table {{ width: 100%; border-collapse: collapse; }}
  .sem-table th {{ background: #161616; color: #444; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; padding: 10px 14px; text-align: left; }}
  .sem-table td {{ padding: 10px 14px; border-top: 1px solid #1a1a1a; }}

  /* Funil visual */
  .funil-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 32px; }}
  .funil-step {{ background: #111; border: 1px solid #1e1e1e; border-radius: 6px; padding: 16px; text-align: center; }}
  .funil-step .pct {{ font-size: 24px; font-weight: 700; color: #fff; }}
  .funil-step .label {{ font-size: 11px; color: #555; text-transform: uppercase; letter-spacing: 0.08em; margin-top: 4px; }}
  .funil-step .budget-info {{ font-size: 13px; color: #aaa; margin-top: 8px; }}

  .refresh-btn {{ background: #00bfa6; color: #000; border: none; padding: 8px 20px; border-radius: 4px; font-size: 13px; font-weight: 700; cursor: pointer; }}

  @media (max-width: 768px) {{
    .camp-kpis {{ grid-template-columns: repeat(2, 1fr); }}
    .funil-grid {{ grid-template-columns: repeat(2, 1fr); }}
  }}
</style>
</head>
<body>

<div class="header">
  <div>
    <div style="font-size:11px;font-weight:700;letter-spacing:0.14em;color:#00bfa6;text-transform:uppercase;margin-bottom:6px;">BOOST RESEARCH</div>
    <h1>Dashboard — Advisory C4 | Março 2026</h1>
    <div class="sub">4 campanhas · 15 conjuntos · Budget R$40.000/mês · CPL meta R$50</div>
  </div>
  <div style="text-align:right;">
    <div class="ts">Atualizado: {ts}</div>
    <div style="margin-top:8px;"><button class="refresh-btn" onclick="location.reload()">↻ Atualizar</button></div>
  </div>
</div>

<div class="container">

  {"<div style='text-align:center;padding:60px;color:#333;'><h2 style='color:#444;margin-bottom:8px;'>📊 Campanha ainda sem dados</h2><p>Ative as campanhas no Gerenciador de Anúncios para começar a ver métricas.</p></div>" if no_data else ""}

  <!-- KPIs Globais -->
  <div class="section-title">Visão Geral — Todas as Campanhas</div>
  <div class="kpis">
    <div class="kpi accent">
      <div class="label">Gasto Total</div>
      <div class="value">{brl(total['spend'])}</div>
      <div class="sub">de {brl(BUDGET_MENSAL)} · {total['budget_pct']}%</div>
      <div class="budget-bar-wrap"><div class="budget-bar" style="width:{min(total['budget_pct'],100)}%"></div></div>
    </div>
    <div class="kpi">
      <div class="label">Leads Totais</div>
      <div class="value">{total['leads']}</div>
      <div class="sub">meta: 615–800/mês</div>
    </div>
    <div class="kpi">
      <div class="label">CPL Médio</div>
      <div class="value {cpl_class(total['cpl'])}">{brl(total['cpl']) if total['cpl'] > 0 else '—'}</div>
      <div class="sub">meta: {brl(CPL_OK)} · corte: {brl(CPL_CORTE)}</div>
    </div>
    <div class="kpi">
      <div class="label">Cliques</div>
      <div class="value">{total['clicks']:,}</div>
      <div class="sub">{total['impressions']:,} impressões</div>
    </div>
    <div class="kpi">
      <div class="label">Budget Restante</div>
      <div class="value">{brl(BUDGET_MENSAL - total['spend'])}</div>
      <div class="sub">{round(100 - total['budget_pct'], 1)}% disponível</div>
    </div>
  </div>

  <!-- Alertas -->
  <div class="section-title">Alertas</div>
  {alerts_html}

  <!-- Distribuição de funil -->
  <div class="section-title">Distribuição de Budget por Funil</div>
  <div class="funil-grid">
    <div class="funil-step">
      <div class="pct" style="color:#4a9de0;">20%</div>
      <div class="label">Awareness</div>
      <div class="budget-info">R$8.000/mês<br><small style="color:#444;">CPM · Hook Rate</small></div>
    </div>
    <div class="funil-step">
      <div class="pct" style="color:#f0a030;">39%</div>
      <div class="label">Consideração</div>
      <div class="budget-info">R$15.600/mês<br><small style="color:#444;">CPL R$80–200</small></div>
    </div>
    <div class="funil-step">
      <div class="pct" style="color:#4caf7d;">36%</div>
      <div class="label">Conversão LP</div>
      <div class="budget-info">R$14.400/mês<br><small style="color:#444;">CPL R$50–150</small></div>
    </div>
    <div class="funil-step">
      <div class="pct" style="color:#4caf7d;">5%</div>
      <div class="label">Conversão Form</div>
      <div class="budget-info">R$2.000/mês<br><small style="color:#444;">A/B test</small></div>
    </div>
  </div>

  <!-- Campanhas -->
  <div class="section-title">Por Campanha</div>
  {camp_cards}

  <!-- Semáforo de Benchmarks -->
  <div class="section-title">Semáforo de Benchmarks</div>
  <div style="background:#111;border:1px solid #1e1e1e;border-radius:6px;overflow:hidden;margin-bottom:32px;">
    <table class="sem-table">
      <thead>
        <tr>
          <th>Métrica</th>
          <th style="color:#4caf7d;">🟢 OK</th>
          <th style="color:#f0a030;">🟡 Atenção</th>
          <th style="color:#e05555;">🔴 Pausar</th>
          <th>Atual</th>
        </tr>
      </thead>
      <tbody>{sem_rows}</tbody>
    </table>
  </div>

  <!-- Regras de decisão Tati -->
  <div class="section-title">Regras de Decisão (@tati)</div>
  <div style="background:#111;border:1px solid #1e1e1e;border-radius:6px;padding:20px 24px;margin-bottom:32px;">
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;">
      <div style="padding:12px;background:#161616;border-radius:4px;">
        <div style="font-size:10px;color:#555;margin-bottom:6px;text-transform:uppercase;">8 horas</div>
        <div style="color:#aaa;font-size:13px;">Revisar CPM + Hook Rate<br>Ajustar placement</div>
      </div>
      <div style="padding:12px;background:#161616;border-radius:4px;">
        <div style="font-size:10px;color:#555;margin-bottom:6px;text-transform:uppercase;">24 horas</div>
        <div style="color:#aaa;font-size:13px;">CPL preliminar<br>Avaliar copy + público</div>
      </div>
      <div style="padding:12px;background:#161616;border-radius:4px;">
        <div style="font-size:10px;color:#555;margin-bottom:6px;text-transform:uppercase;">48 horas</div>
        <div style="color:#aaa;font-size:13px;">CPL consolidado<br>Escalar · manter · pausar</div>
      </div>
      <div style="padding:12px;background:#161616;border-radius:4px;">
        <div style="font-size:10px;color:#f0a030;margin-bottom:6px;text-transform:uppercase;">CPL > R$75 (48h)</div>
        <div style="color:#e05555;font-size:13px;font-weight:600;">⛔ Pausar conjunto</div>
      </div>
      <div style="padding:12px;background:#161616;border-radius:4px;">
        <div style="font-size:10px;color:#555;margin-bottom:6px;text-transform:uppercase;">Semanal</div>
        <div style="color:#aaa;font-size:13px;">Relatório completo<br>Redistribuir budget</div>
      </div>
    </div>
  </div>

  <!-- Vídeos -->
  <div class="section-title">Vídeos — Referência de Hook</div>
  <div style="background:#111;border:1px solid #1e1e1e;border-radius:6px;overflow:hidden;margin-bottom:32px;">
    <table style="width:100%;border-collapse:collapse;">
      <thead>
        <tr>
          <th style="background:#161616;color:#444;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;padding:10px 14px;text-align:left;">ID</th>
          <th style="background:#161616;color:#444;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;padding:10px 14px;text-align:left;">Ângulo</th>
          <th style="background:#161616;color:#444;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;padding:10px 14px;text-align:left;">Hook</th>
          <th style="background:#161616;color:#444;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;padding:10px 14px;text-align:left;">Meta ID</th>
        </tr>
      </thead>
      <tbody>
        {"".join(f'<tr><td style="padding:10px 14px;border-top:1px solid #1a1a1a;color:#aaa;font-weight:700;">{v["nome"]}</td><td style="padding:10px 14px;border-top:1px solid #1a1a1a;color:#aaa;">{v["angulo"]}</td><td style="padding:10px 14px;border-top:1px solid #1a1a1a;color:#555;font-style:italic;">"{v["hook"]}"</td><td style="padding:10px 14px;border-top:1px solid #1a1a1a;color:#333;font-size:12px;">{vid_id}</td></tr>' for vid_id, v in VIDEOS.items())}
      </tbody>
    </table>
  </div>

</div>
</body>
</html>"""

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("\n" + "="*55)
    print("  Dashboard Advisory C4 — Boost Research")
    print("="*55 + "\n")

    data = build_data()
    html = generate_html(data)

    output = "dashboard_consultoria_boost.html"
    with open(output, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n✅ Dashboard gerado: {output}")

if __name__ == "__main__":
    main()
