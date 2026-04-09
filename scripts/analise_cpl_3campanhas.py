"""
analise_cpl_3campanhas.py
Cruza spend do Meta Ads com leads do Supabase pra calcular CPL real
das 3 campanhas analisadas (C4 CONVERSAO, C4 CONSIDERACAO, C5 ANDROMEDA).
"""
import requests, json
from collections import defaultdict

import os
META_TOKEN = os.environ.get("META_TOKEN", "")
META_ACCOUNT = os.environ.get("META_ACCOUNT", "act_844208497068966")
META_BASE = "https://graph.facebook.com/v19.0"

SB = "https://dvvfnrdvhkjfovhfqiow.supabase.co"
SB_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
if not META_TOKEN or not SB_KEY:
    raise SystemExit("defina META_TOKEN e SUPABASE_SERVICE_ROLE_KEY no ambiente")
SB_H = {"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}"}

# Períodos: o range dos leads no Supabase é 28/fev → 09/abr
TIME_RANGE = {"since": "2026-02-28", "until": "2026-04-09"}

# Grupos: nome lógico → padrões pra matching no Meta (ILIKE) e UTM no RD
GRUPOS = {
    "C4 CONVERSAO (LP)": {
        "name_contains": ["CONVERSAO][CBO][C4][MAR2026"],
        "name_excludes": ["FORM"],
        "utm_campaign": "[BR][BOOST][CONVERSAO][CBO][C4][Mar2026]",
    },
    "C4 CONSIDERACAO": {
        "name_contains": ["CONSIDERACAO][CBO][C4][MAR2026"],
        "name_excludes": ["FORM"],
        "utm_campaign": "[BR][BOOST][CONSIDERACAO][CBO][C4][Mar2026]",
    },
    "C5 ANDROMEDA (V1+V2 agregadas)": {
        "name_contains": ["C5-ANDROMEDA"],
        "name_excludes": [],
        "utm_campaign": "c5-andromeda-abr2026",
    },
}

# Cache do fetch all
_ALL_CAMPAIGNS_CACHE = None

def meta_get_all_campaigns():
    """Busca TODAS as campanhas do account (com paginação)."""
    global _ALL_CAMPAIGNS_CACHE
    if _ALL_CAMPAIGNS_CACHE is not None:
        return _ALL_CAMPAIGNS_CACHE
    all_camps = []
    url = f"{META_BASE}/{META_ACCOUNT}/campaigns"
    params = {
        "access_token": META_TOKEN,
        "fields": "id,name,status,objective",
        "limit": 200,
    }
    while url:
        r = requests.get(url, params=params, timeout=30)
        data = r.json()
        all_camps.extend(data.get("data", []))
        paging = data.get("paging", {})
        url = paging.get("next")
        params = None  # next url já tem tudo
    _ALL_CAMPAIGNS_CACHE = all_camps
    return all_camps


def meta_get_campaigns_matching(name_contains, name_excludes=None):
    """Filtra campanhas cujo nome contém TODOS os termos e não contém nenhum dos excludes."""
    camps = meta_get_all_campaigns()
    terms = [t.upper() for t in name_contains]
    excludes = [t.upper() for t in (name_excludes or [])]
    out = []
    for c in camps:
        n = c["name"].upper()
        if not all(t in n for t in terms):
            continue
        if any(t in n for t in excludes):
            continue
        out.append(c)
    return out


def meta_get_spend(campaign_ids):
    """Spend + impressions + clicks + ações do Meta no time_range."""
    if not campaign_ids:
        return None
    total = {"spend": 0.0, "impressions": 0, "clicks": 0, "leads_meta": 0, "reach": 0}
    for cid in campaign_ids:
        r = requests.get(f"{META_BASE}/{cid}/insights", params={
            "access_token": META_TOKEN,
            "time_range": json.dumps(TIME_RANGE),
            "fields": "spend,impressions,clicks,reach,actions",
            "level": "campaign"
        })
        data = r.json().get("data", [])
        if not data:
            continue
        d = data[0]
        total["spend"]       += float(d.get("spend", 0))
        total["impressions"] += int(d.get("impressions", 0))
        total["clicks"]      += int(d.get("clicks", 0))
        total["reach"]       += int(d.get("reach", 0))
        for a in d.get("actions", []) or []:
            if a.get("action_type") in ("lead", "onsite_conversion.lead_grouped"):
                total["leads_meta"] += int(a.get("value", 0))
    return total


def supabase_leads_stats(utm_campaign):
    """Conta leads do Supabase por qualidade pra esse UTM."""
    r = requests.get(f"{SB}/rest/v1/leads", params={
        "select": "is_qualified,patrimonio_cripto_min_k,patrimonio_tradicional_min_k,investe_cripto",
        "first_campaign": f"eq.{utm_campaign}",
        "limit": 2000
    }, headers=SB_H)
    leads = r.json()
    total = len(leads)
    qualif = sum(1 for l in leads if l.get("is_qualified"))
    cripto_100k = sum(1 for l in leads if (l.get("patrimonio_cripto_min_k") or 0) >= 100)
    cripto_50k_plus = sum(1 for l in leads if (l.get("patrimonio_cripto_min_k") or 0) >= 50)
    investe_cripto = sum(1 for l in leads if l.get("investe_cripto") is True)
    return {
        "total": total,
        "qualificados": qualif,
        "cripto_100k_plus": cripto_100k,
        "cripto_50k_plus": cripto_50k_plus,
        "investe_cripto": investe_cripto,
    }


def fmt(v, decimals=2):
    if v is None or v == 0:
        return "—"
    return f"R$ {v:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def main():
    print(f"\n{'='*78}")
    print(f"  ANÁLISE CPL REAL — 3 CAMPANHAS")
    print(f"  Período: {TIME_RANGE['since']} → {TIME_RANGE['until']}")
    print(f"{'='*78}")

    resultados = {}

    print("Buscando todas as campanhas do Meta account...")
    all_camps = meta_get_all_campaigns()
    print(f"Total de campanhas no account: {len(all_camps)}")

    for nome, cfg in GRUPOS.items():
        print(f"\n→ {nome}")
        # 1) Encontra campanhas no Meta
        camps = meta_get_campaigns_matching(cfg["name_contains"], cfg.get("name_excludes"))
        if not camps:
            print(f"  ⚠️  Nenhuma campanha encontrada no Meta com os filtros")
            resultados[nome] = None
            continue
        print(f"  Meta campanhas encontradas ({len(camps)}):")
        for c in camps:
            print(f"    - [{c['status'][:6]}] {c['name']}  (id={c['id']})")

        # 2) Pega spend
        spend_data = meta_get_spend([c["id"] for c in camps])
        # 3) Pega leads do Supabase
        leads = supabase_leads_stats(cfg["utm_campaign"])

        resultados[nome] = {
            "meta_campaigns": camps,
            "spend": spend_data,
            "leads": leads,
        }

    # ====== SUMÁRIO FINAL ======
    print(f"\n{'='*78}")
    print(f"  SUMÁRIO — CPL REAL vs QUALIDADE")
    print(f"{'='*78}\n")

    header = f"{'Campanha':<32} {'Spend':>14} {'Leads':>7} {'Qualif':>7} {'100k+':>7}"
    print(header)
    print(f"{'CPL real':>40} {'CPL qualif':>14} {'CPA 100k+':>14}")
    print("-" * 78)

    for nome, r in resultados.items():
        if not r or not r["spend"]:
            print(f"{nome:<32} sem dados Meta")
            continue
        s = r["spend"]["spend"]
        l = r["leads"]["total"]
        q = r["leads"]["qualificados"]
        k = r["leads"]["cripto_100k_plus"]
        cpl     = s/l if l else None
        cpl_q   = s/q if q else None
        cpa_100 = s/k if k else None

        print(f"\n{nome}")
        print(f"  Spend:              {fmt(s)}")
        print(f"  Impressões:         {r['spend']['impressions']:,}".replace(",", "."))
        print(f"  Cliques:            {r['spend']['clicks']:,}".replace(",", "."))
        print(f"  Meta reportou (Lead): {r['spend']['leads_meta']}")
        print(f"  RD recebeu (com UTM): {l}")
        if r['spend']['leads_meta'] and l:
            perda = (1 - l/r['spend']['leads_meta']) * 100
            print(f"  PERDA de atribuição: {perda:.0f}% (Meta - RD)")
        print(f"  CPL real (RD):       {fmt(cpl)}")
        print(f"  CPL qualif (≥R$50k): {fmt(cpl_q)}")
        print(f"  CPA por lead 100k+:  {fmt(cpa_100)}")

    # Salvar JSON pra reuso
    with open("/tmp/analise_cpl_3campanhas.json", "w") as f:
        json.dump({
            k: {
                "spend": v["spend"] if v else None,
                "leads": v["leads"] if v else None,
                "meta_campaigns": [{"id": c["id"], "name": c["name"], "status": c["status"]}
                                   for c in (v["meta_campaigns"] if v else [])]
            } for k, v in resultados.items()
        }, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Resultado bruto salvo em /tmp/analise_cpl_3campanhas.json")


if __name__ == "__main__":
    main()
