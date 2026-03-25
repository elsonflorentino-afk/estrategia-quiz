#!/usr/bin/env python3
"""
Dashboard IR Cripto 2026 — Meta Ads
Gera um HTML com métricas em tempo real da campanha.

Rodar: python3 dashboard_ir_cripto.py
Abre automaticamente no browser.
"""

import requests
import json
import os
import os
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURAÇÃO
# ─────────────────────────────────────────────

ACCESS_TOKEN  = os.environ.get("META_ACCESS_TOKEN", "")
CAMPAIGN_ID  = "120245737303650651"
API          = "https://graph.facebook.com/v21.0"
BID_CAP      = 10.0   # R$10 — alerta se CPL passar disso
BUDGET_TOTAL = 10000  # R$10.000

ADSETS = {
    "120245737938850651": {"name": "CJ1-FORM", "approach": "FORM", "publico": "Frio"},
    "120245737939420651": {"name": "CJ2-FORM", "approach": "FORM", "publico": "LAL"},
    "120245737939810651": {"name": "CJ3-FORM", "approach": "FORM", "publico": "Retargeting"},
    "120245737356160651": {"name": "CJ1-LP",   "approach": "LP",   "publico": "Frio"},
    "120245737356610651": {"name": "CJ2-LP",   "approach": "LP",   "publico": "LAL"},
    "120245737357640651": {"name": "CJ3-LP",   "approach": "LP",   "publico": "Retargeting"},
}

# ─────────────────────────────────────────────
# FETCH DE DADOS
# ─────────────────────────────────────────────

def fetch_campaign():
    r = requests.get(f"{API}/{CAMPAIGN_ID}/insights", params={
        "fields": "spend,impressions,clicks,ctr,actions,cost_per_action_type,reach",
        "date_preset": "maximum",
        "access_token": ACCESS_TOKEN,
    }, timeout=15)
    data = r.json().get("data", [])
    return data[0] if data else {}

def fetch_adset(adset_id):
    r = requests.get(f"{API}/{adset_id}/insights", params={
        "fields": "spend,impressions,clicks,ctr,actions,cost_per_action_type,reach",
        "date_preset": "maximum",
        "access_token": ACCESS_TOKEN,
    }, timeout=15)
    data = r.json().get("data", [])
    return data[0] if data else {}

def get_leads(insights):
    actions = insights.get("actions", [])
    for a in actions:
        if a["action_type"] in ("lead", "onsite_conversion.lead_grouped", "leadgen_other"):
            return int(a.get("value", 0))
    return 0

def get_cpl(insights):
    cpa = insights.get("cost_per_action_type", [])
    for a in cpa:
        if a["action_type"] in ("lead", "onsite_conversion.lead_grouped", "leadgen_other"):
            return float(a.get("value", 0))
    return 0.0

def safe_float(val, default=0.0):
    try:
        return float(val)
    except:
        return default

# ─────────────────────────────────────────────
# BUILD DOS DADOS
# ─────────────────────────────────────────────

def build_data():
    print("Buscando dados da Meta API...")
    campaign = fetch_campaign()

    adsets_data = []
    for adset_id, meta in ADSETS.items():
        ins = fetch_adset(adset_id)
        leads = get_leads(ins)
        cpl   = get_cpl(ins)
        spend = safe_float(ins.get("spend", 0))
        clicks= safe_float(ins.get("clicks", 0))
        impr  = safe_float(ins.get("impressions", 0))
        ctr   = safe_float(ins.get("ctr", 0))

        adsets_data.append({
            "id":       adset_id,
            "name":     meta["name"],
            "approach": meta["approach"],
            "publico":  meta["publico"],
            "spend":    spend,
            "leads":    leads,
            "cpl":      cpl,
            "clicks":   int(clicks),
            "impressions": int(impr),
            "ctr":      round(ctr * 100, 2) if ctr > 1 else round(ctr, 2),
        })
        print(f"  → {meta['name']}: R${spend:.2f} spend | {leads} leads | CPL R${cpl:.2f}")

    # Totais por approach
    form_data = [a for a in adsets_data if a["approach"] == "FORM"]
    lp_data   = [a for a in adsets_data if a["approach"] == "LP"]

    def totals(lst):
        spend  = sum(a["spend"]  for a in lst)
        leads  = sum(a["leads"]  for a in lst)
        clicks = sum(a["clicks"] for a in lst)
        cpl    = spend / leads if leads > 0 else 0
        return {"spend": spend, "leads": leads, "clicks": clicks, "cpl": cpl}

    camp_spend  = safe_float(campaign.get("spend", 0))
    camp_leads  = get_leads(campaign)
    camp_cpl    = get_cpl(campaign)
    camp_clicks = safe_float(campaign.get("clicks", 0))
    camp_impr   = safe_float(campaign.get("impressions", 0))

    return {
        "timestamp":  datetime.now().strftime("%d/%m/%Y %H:%M"),
        "campaign":   {"spend": camp_spend, "leads": camp_leads, "cpl": camp_cpl,
                       "clicks": int(camp_clicks), "impressions": int(camp_impr),
                       "budget_pct": round((camp_spend / BUDGET_TOTAL) * 100, 1)},
        "form":       totals(form_data),
        "lp":         totals(lp_data),
        "adsets":     adsets_data,
    }

# ─────────────────────────────────────────────
# GERAÇÃO DO HTML
# ─────────────────────────────────────────────

def brl(val):
    return f"R${val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def alert_class(cpl):
    if cpl == 0:    return "neutral"
    if cpl <= 10:   return "ok"
    if cpl <= 15:   return "warn"
    return "danger"

def winner_badge(form_val, lp_val, lower_is_better=True):
    if form_val == 0 and lp_val == 0: return "", ""
    if form_val == 0: return "", "🏆"
    if lp_val == 0:   return "🏆", ""
    if lower_is_better:
        return ("🏆", "") if form_val < lp_val else ("", "🏆")
    else:
        return ("🏆", "") if form_val > lp_val else ("", "🏆")

def generate_html(d):
    c    = d["campaign"]
    form = d["form"]
    lp   = d["lp"]
    ts   = d["timestamp"]

    # Vencedor CPL
    wf_cpl, wl_cpl = winner_badge(form["cpl"], lp["cpl"], lower_is_better=True)
    wf_leads, wl_leads = winner_badge(form["leads"], lp["leads"], lower_is_better=False)

    # Alertas
    alerts = []
    if c["cpl"] > BID_CAP and c["cpl"] > 0:
        alerts.append(f"⚠️ CPL geral {brl(c['cpl'])} acima do bid cap ({brl(BID_CAP)})")
    if form["cpl"] > BID_CAP and form["cpl"] > 0:
        alerts.append(f"⚠️ CPL FORM {brl(form['cpl'])} acima do bid cap")
    if lp["cpl"] > BID_CAP and lp["cpl"] > 0:
        alerts.append(f"⚠️ CPL LP {brl(lp['cpl'])} acima do bid cap")
    if c["budget_pct"] >= 80:
        alerts.append(f"🔴 Budget {c['budget_pct']}% consumido — atenção ao limite")
    if form["leads"] > 0 and lp["leads"] > 0:
        diff = abs(form["cpl"] - lp["cpl"]) / max(form["cpl"], lp["cpl"]) * 100
        if diff >= 20:
            winner = "FORM" if form["cpl"] < lp["cpl"] else "LP"
            alerts.append(f"📊 Diferença de CPL >20% — considerar escalar approach {winner}")

    alerts_html = ""
    if alerts:
        items = "".join(f'<div class="alert-item">{a}</div>' for a in alerts)
        alerts_html = f'<div class="alerts-box">{items}</div>'
    else:
        alerts_html = '<div class="alerts-box ok-box">✅ Tudo dentro dos parâmetros — nenhum alerta ativo</div>'

    # Rows dos adsets
    rows = ""
    for a in d["adsets"]:
        ac   = alert_class(a["cpl"])
        cpl_str = brl(a["cpl"]) if a["cpl"] > 0 else "—"
        app_badge = f'<span class="badge badge-{"form" if a["approach"]=="FORM" else "lp"}">{a["approach"]}</span>'
        rows += f"""
        <tr>
          <td>{a["name"]}</td>
          <td>{app_badge}</td>
          <td>{a["publico"]}</td>
          <td>{brl(a["spend"])}</td>
          <td>{a["leads"]}</td>
          <td class="cpl-cell {ac}">{cpl_str}</td>
          <td>{a["clicks"]:,}</td>
          <td>{a["ctr"]}%</td>
        </tr>"""

    no_data = c["spend"] == 0

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Dashboard IR Cripto 2026 — Boost Research</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #0a0a0a; color: #ccc; font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 14px; }}
  .header {{ background: #111; border-bottom: 1px solid #1e1e1e; padding: 24px 32px; display: flex; justify-content: space-between; align-items: center; }}
  .header h1 {{ font-size: 18px; font-weight: 700; color: #fff; }}
  .header .sub {{ font-size: 12px; color: #555; margin-top: 4px; }}
  .ts {{ font-size: 12px; color: #444; }}
  .container {{ padding: 32px; max-width: 1200px; margin: 0 auto; }}
  .section-title {{ font-size: 11px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: #444; margin-bottom: 16px; }}

  /* KPIs */
  .kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; margin-bottom: 32px; }}
  .kpi {{ background: #111; border: 1px solid #1e1e1e; border-radius: 6px; padding: 20px; }}
  .kpi .label {{ font-size: 11px; color: #555; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 8px; }}
  .kpi .value {{ font-size: 26px; font-weight: 700; color: #fff; }}
  .kpi .sub {{ font-size: 12px; color: #444; margin-top: 4px; }}
  .kpi.accent {{ border-color: #00bfa6; }}
  .kpi.accent .value {{ color: #00bfa6; }}

  /* A/B */
  .ab-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 32px; }}
  .ab-card {{ background: #111; border: 1px solid #1e1e1e; border-radius: 6px; padding: 24px; }}
  .ab-card h3 {{ font-size: 13px; font-weight: 700; color: #fff; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }}
  .ab-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #1a1a1a; }}
  .ab-row:last-child {{ border-bottom: none; }}
  .ab-label {{ color: #555; font-size: 13px; }}
  .ab-val {{ font-weight: 600; color: #fff; }}
  .ab-val.winner {{ color: #00bfa6; }}

  /* Alertas */
  .alerts-box {{ background: #1a1010; border: 1px solid #3a1e1e; border-radius: 6px; padding: 16px 20px; margin-bottom: 32px; }}
  .alerts-box.ok-box {{ background: #0d1a12; border-color: #1e3a25; color: #4caf7d; }}
  .alert-item {{ color: #e88; font-size: 13px; padding: 4px 0; }}

  /* Tabela */
  .table-wrap {{ background: #111; border: 1px solid #1e1e1e; border-radius: 6px; overflow: hidden; margin-bottom: 32px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ background: #161616; color: #444; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; padding: 12px 16px; text-align: left; }}
  td {{ padding: 12px 16px; border-top: 1px solid #1a1a1a; color: #aaa; }}
  tr:hover td {{ background: #141414; }}
  .cpl-cell {{ font-weight: 700; }}
  .cpl-cell.ok      {{ color: #4caf7d; }}
  .cpl-cell.warn    {{ color: #f0a030; }}
  .cpl-cell.danger  {{ color: #e05555; }}
  .cpl-cell.neutral {{ color: #555; }}

  .badge {{ font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 3px; text-transform: uppercase; letter-spacing: 0.06em; }}
  .badge-form {{ background: #1a2a3a; color: #4a9de0; }}
  .badge-lp   {{ background: #1a2a1a; color: #4caf7d; }}

  /* Budget bar */
  .budget-bar-wrap {{ background: #1a1a1a; border-radius: 4px; height: 6px; margin-top: 8px; overflow: hidden; }}
  .budget-bar {{ height: 100%; background: #00bfa6; border-radius: 4px; transition: width 0.3s; }}

  .no-data {{ text-align: center; padding: 60px; color: #333; }}
  .no-data h2 {{ font-size: 20px; color: #444; margin-bottom: 8px; }}

  .refresh-btn {{ background: #00bfa6; color: #000; border: none; padding: 8px 20px; border-radius: 4px; font-size: 13px; font-weight: 700; cursor: pointer; }}
  .refresh-btn:hover {{ background: #00d4b8; }}
</style>
</head>
<body>

<div class="header">
  <div>
    <div style="font-size:11px;font-weight:700;letter-spacing:0.14em;color:#00bfa6;text-transform:uppercase;margin-bottom:6px;">BOOST RESEARCH</div>
    <h1>Dashboard — IR Cripto 2026</h1>
    <div class="sub">Campanha ID: {CAMPAIGN_ID} · A/B Test: Formulário vs Landing Page</div>
  </div>
  <div style="text-align:right;">
    <div class="ts">Atualizado: {ts}</div>
    <div style="margin-top:8px;"><button class="refresh-btn" onclick="location.reload()">↻ Atualizar</button></div>
  </div>
</div>

<div class="container">

  {"<!-- NO DATA --><div class='no-data'><h2>📊 Campanha ainda sem dados</h2><p>Ative a campanha no Gerenciador de Anúncios para começar a ver métricas aqui.</p></div>" if no_data else ""}

  <!-- KPIs gerais -->
  <div class="section-title">Campanha Geral</div>
  <div class="kpis">
    <div class="kpi accent">
      <div class="label">Gasto Total</div>
      <div class="value">{brl(c["spend"])}</div>
      <div class="sub">de {brl(BUDGET_TOTAL)} · {c["budget_pct"]}%</div>
      <div class="budget-bar-wrap"><div class="budget-bar" style="width:{min(c["budget_pct"],100)}%"></div></div>
    </div>
    <div class="kpi">
      <div class="label">Leads Totais</div>
      <div class="value">{c["leads"]}</div>
      <div class="sub">FORM + LP</div>
    </div>
    <div class="kpi {'accent' if 0 < c["cpl"] <= BID_CAP else ''}">
      <div class="label">CPL Geral</div>
      <div class="value">{brl(c["cpl"]) if c["cpl"] > 0 else "—"}</div>
      <div class="sub">Bid cap: {brl(BID_CAP)}</div>
    </div>
    <div class="kpi">
      <div class="label">Cliques</div>
      <div class="value">{c["clicks"]:,}</div>
      <div class="sub">{c["impressions"]:,} impressões</div>
    </div>
    <div class="kpi">
      <div class="label">Budget Restante</div>
      <div class="value">{brl(BUDGET_TOTAL - c["spend"])}</div>
      <div class="sub">{100 - c["budget_pct"]}% disponível</div>
    </div>
  </div>

  <!-- Alertas -->
  <div class="section-title">Alertas</div>
  {alerts_html}

  <!-- A/B Comparison -->
  <div class="section-title">A/B Test — Formulário vs Landing Page</div>
  <div class="ab-grid">
    <div class="ab-card">
      <h3><span class="badge badge-form">FORM</span> Formulário Instantâneo</h3>
      <div class="ab-row"><span class="ab-label">Gasto</span><span class="ab-val">{brl(form["spend"])}</span></div>
      <div class="ab-row"><span class="ab-label">Leads</span><span class="ab-val {'winner' if wf_leads else ''}">{form["leads"]} {wf_leads}</span></div>
      <div class="ab-row"><span class="ab-label">CPL</span><span class="ab-val {'winner' if wf_cpl else ''}">{brl(form["cpl"]) if form["cpl"] > 0 else "—"} {wf_cpl}</span></div>
      <div class="ab-row"><span class="ab-label">Cliques</span><span class="ab-val">{form["clicks"]:,}</span></div>
    </div>
    <div class="ab-card">
      <h3><span class="badge badge-lp">LP</span> Landing Page</h3>
      <div class="ab-row"><span class="ab-label">Gasto</span><span class="ab-val">{brl(lp["spend"])}</span></div>
      <div class="ab-row"><span class="ab-label">Leads</span><span class="ab-val {'winner' if wl_leads else ''}">{lp["leads"]} {wl_leads}</span></div>
      <div class="ab-row"><span class="ab-label">CPL</span><span class="ab-val {'winner' if wl_cpl else ''}">{brl(lp["cpl"]) if lp["cpl"] > 0 else "—"} {wl_cpl}</span></div>
      <div class="ab-row"><span class="ab-label">Cliques</span><span class="ab-val">{lp["clicks"]:,}</span></div>
    </div>
  </div>

  <!-- Tabela por conjunto -->
  <div class="section-title">Por Conjunto de Anúncios</div>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Conjunto</th>
          <th>Approach</th>
          <th>Público</th>
          <th>Gasto</th>
          <th>Leads</th>
          <th>CPL</th>
          <th>Cliques</th>
          <th>CTR</th>
        </tr>
      </thead>
      <tbody>
        {rows}
      </tbody>
    </table>
  </div>

  <!-- Legenda CPL -->
  <div style="display:flex;gap:24px;font-size:12px;color:#444;margin-bottom:32px;">
    <span><span style="color:#4caf7d;">●</span> CPL ≤ R$10 (ok)</span>
    <span><span style="color:#f0a030;">●</span> CPL R$10–R$15 (atenção)</span>
    <span><span style="color:#e05555;">●</span> CPL > R$15 (acima do bid cap)</span>
    <span><span style="color:#555;">●</span> Sem dados</span>
  </div>

  <!-- Regras de decisão -->
  <div class="section-title">Regras de Decisão A/B</div>
  <div style="background:#111;border:1px solid #1e1e1e;border-radius:6px;padding:20px 24px;">
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
      <div style="padding:12px;background:#161616;border-radius:4px;">
        <div style="font-size:11px;color:#555;margin-bottom:6px;">FORM CPL menor >20%</div>
        <div style="color:#aaa;font-size:13px;">Escalar FORM → 70% do budget</div>
      </div>
      <div style="padding:12px;background:#161616;border-radius:4px;">
        <div style="font-size:11px;color:#555;margin-bottom:6px;">LP CPL menor >20%</div>
        <div style="color:#aaa;font-size:13px;">Escalar LP → 70% do budget</div>
      </div>
      <div style="padding:12px;background:#161616;border-radius:4px;">
        <div style="font-size:11px;color:#555;margin-bottom:6px;">Diferença &lt; 20%</div>
        <div style="color:#aaa;font-size:13px;">Manter 50/50 · analisar qualidade</div>
      </div>
      <div style="padding:12px;background:#161616;border-radius:4px;">
        <div style="font-size:11px;color:#555;margin-bottom:6px;">Leads insuficientes (&lt;20/approach)</div>
        <div style="color:#aaa;font-size:13px;">Aguardar mais dados</div>
      </div>
    </div>
  </div>

</div>
</body>
</html>"""

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("\n" + "="*50)
    print("  Dashboard IR Cripto 2026 — Boost Research")
    print("="*50 + "\n")

    data = build_data()

    html = generate_html(data)
    output = "dashboard_ir_cripto.html"
    with open(output, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n✅ Dashboard gerado: {output}")

if __name__ == "__main__":
    main()
