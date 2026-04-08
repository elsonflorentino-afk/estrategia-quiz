#!/usr/bin/env python3
"""
sync_meta_ads.py — Sincroniza campanhas + ads + insights do Meta Ads → Supabase.

Env vars:
  META_ACCESS_TOKEN
  META_AD_ACCOUNT_ID   (ex: act_844208497068966)
  SUPABASE_URL
  SUPABASE_SERVICE_ROLE_KEY

Uso:
  --days N         janela de insights (default: 30)
  --only-active    só campanhas ativas (default: todas)
"""
import os
import sys
import json
import time
import argparse
from datetime import datetime, timedelta, timezone
import requests

META_TOKEN = os.environ.get("META_ACCESS_TOKEN")
# Ad account ID fixo da Boost Research (não expira)
META_ACCOUNT = os.environ.get("META_AD_ACCOUNT_ID", "act_844208497068966")
SB_URL = os.environ.get("SUPABASE_URL")
SB_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not all([META_TOKEN, SB_URL, SB_KEY]):
    print("ERROR: env vars missing")
    print(f"  META_ACCESS_TOKEN={'ok' if META_TOKEN else 'MISSING'}")
    print(f"  SUPABASE_URL={'ok' if SB_URL else 'MISSING'}")
    print(f"  SUPABASE_SERVICE_ROLE_KEY={'ok' if SB_KEY else 'MISSING'}")
    sys.exit(1)

META_BASE = "https://graph.facebook.com/v19.0"
HEADERS_SB = {
    "apikey": SB_KEY,
    "Authorization": f"Bearer {SB_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates,return=minimal",
}


def meta_get(path, params=None):
    params = params or {}
    params["access_token"] = META_TOKEN
    r = requests.get(f"{META_BASE}/{path}", params=params, timeout=60)
    if r.status_code != 200:
        raise Exception(f"Meta API error {r.status_code}: {r.text[:300]}")
    return r.json()


def meta_get_paginated(path, params=None, max_pages=50):
    """Pagina usando 'after' cursor."""
    params = params or {}
    results = []
    url = None
    for _ in range(max_pages):
        if url is None:
            data = meta_get(path, params)
        else:
            r = requests.get(url, timeout=60)
            if r.status_code != 200:
                break
            data = r.json()
        results.extend(data.get("data", []))
        url = (data.get("paging") or {}).get("next")
        if not url:
            break
    return results


def sb_upsert(table, rows):
    if not rows:
        return 0, 0
    try:
        r = requests.post(
            f"{SB_URL}/rest/v1/{table}",
            headers=HEADERS_SB,
            json=rows,
            timeout=60,
        )
        if r.status_code in (200, 201):
            return len(rows), 0
        print(f"  UPSERT {table} ERROR {r.status_code}: {r.text[:300]}")
        return 0, len(rows)
    except Exception as e:
        print(f"  UPSERT {table} EXCEPTION: {e}")
        return 0, len(rows)


def build_campaign_row(c, insights):
    return {
        "id": c.get("id"),
        "name": c.get("name"),
        "status": c.get("status"),
        "objective": c.get("objective"),
        "daily_budget": float(c.get("daily_budget") or 0) / 100 if c.get("daily_budget") else None,
        "lifetime_budget": float(c.get("lifetime_budget") or 0) / 100 if c.get("lifetime_budget") else None,
        "start_date": (c.get("start_time") or "")[:10] or None,
        "total_spend": float(insights.get("spend") or 0),
        "total_impressions": int(insights.get("impressions") or 0),
        "total_clicks": int(insights.get("clicks") or 0),
        "total_leads_meta": extract_leads(insights.get("actions") or []),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def extract_leads(actions):
    """Extrai leads priorizando lead_grouped > lead > fb_pixel_lead > complete_registration."""
    if not actions:
        return 0
    d = {a.get("action_type"): int(a.get("value") or 0) for a in actions}
    return (
        d.get("onsite_conversion.lead_grouped")
        or d.get("lead")
        or d.get("offsite_conversion.fb_pixel_lead")
        or d.get("complete_registration")
        or 0
    )


def build_ad_row(ad, insights, campaign_id):
    spend = float(insights.get("spend") or 0)
    impressions = int(insights.get("impressions") or 0)
    clicks = int(insights.get("clicks") or 0)
    leads = extract_leads(insights.get("actions") or [])

    return {
        "id": ad.get("id"),
        "campaign_id": campaign_id,
        "adset_id": ad.get("adset_id"),
        "name": ad.get("name"),
        "creative_id": (ad.get("creative") or {}).get("id"),
        "status": ad.get("effective_status"),
        "spend_30d": spend,
        "impressions_30d": impressions,
        "clicks_30d": clicks,
        "leads_30d": leads,
        "cpl_30d": spend / leads if leads > 0 else None,
        "ctr_30d": float(insights.get("ctr") or 0),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


LEAD_OBJECTIVES = {
    "OUTCOME_LEADS",
    "LEAD_GENERATION",
    "CONVERSIONS",
    "OUTCOME_SALES",
    "OUTCOME_TRAFFIC",  # LP de captação
}


def is_relevant_campaign(c):
    """Filtra apenas campanhas relevantes pra análise de CAC."""
    objective = c.get("objective", "")
    name = c.get("name", "")

    # Descarta posts impulsionados automáticos
    if name.startswith("Post do Instagram") or name.startswith("Post do Facebook"):
        return False

    # Aceita campanhas com objective de lead
    if objective in LEAD_OBJECTIVES:
        return True

    # Aceita campanhas com naming pattern Boost (prefixo [BR] ou [BOOST])
    if name.startswith("[BR]") or "[BOOST]" in name:
        return True

    return False


def sync_campaigns(days, only_active):
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    until = datetime.now().strftime("%Y-%m-%d")
    time_range = json.dumps({"since": since, "until": until})

    # Lista campanhas
    params = {
        "fields": "id,name,status,effective_status,objective,daily_budget,lifetime_budget,start_time",
        "limit": 100,
    }
    if only_active:
        params["effective_status"] = json.dumps(["ACTIVE"])

    all_campaigns = meta_get_paginated(f"{META_ACCOUNT}/campaigns", params)
    print(f"📊 Campaigns raw: {len(all_campaigns)}")

    # Filtra só relevantes
    campaigns = [c for c in all_campaigns if is_relevant_campaign(c)]
    print(f"📊 Campaigns relevantes (lead/conversão/tagged BR|BOOST): {len(campaigns)}")
    print(f"📊 Filtradas fora: {len(all_campaigns) - len(campaigns)}")

    camp_rows = []
    ad_rows = []

    for i, c in enumerate(campaigns, 1):
        cid = c.get("id")
        cname = c.get("name", "")[:60]
        print(f"  [{i}/{len(campaigns)}] {cid} | {cname}")

        # Insights da campanha no período
        try:
            insights_data = meta_get(f"{cid}/insights", {
                "fields": "spend,impressions,clicks,actions",
                "time_range": time_range,
                "level": "campaign",
            })
            insights = (insights_data.get("data") or [{}])[0]
        except Exception as e:
            print(f"    ⚠ insights error: {e}")
            insights = {}

        camp_rows.append(build_campaign_row(c, insights))

        # Ads da campanha
        try:
            ads = meta_get_paginated(f"{cid}/ads", {
                "fields": "id,name,adset_id,creative,effective_status",
                "limit": 100,
            }, max_pages=20)
        except Exception as e:
            print(f"    ⚠ ads list error: {e}")
            ads = []

        # Insights por ad (batch via insights level=ad)
        if ads:
            try:
                ad_insights_data = meta_get(f"{cid}/insights", {
                    "fields": "ad_id,spend,impressions,clicks,actions,ctr",
                    "time_range": time_range,
                    "level": "ad",
                    "limit": 500,
                })
                ad_insights_map = {row.get("ad_id"): row for row in ad_insights_data.get("data", [])}
            except Exception as e:
                print(f"    ⚠ ad insights error: {e}")
                ad_insights_map = {}

            for ad in ads:
                aid = ad.get("id")
                ai = ad_insights_map.get(aid, {})
                ad_rows.append(build_ad_row(ad, ai, cid))

        time.sleep(0.15)  # rate limit Meta

    return camp_rows, ad_rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--only-active", action="store_true")
    parser.add_argument("--batch-size", type=int, default=50)
    args = parser.parse_args()

    print(f"=== sync_meta_ads.py | days={args.days} only_active={args.only_active} ===")
    print(f"[{datetime.now(timezone.utc).isoformat()}] Start")

    camp_rows, ad_rows = sync_campaigns(args.days, args.only_active)

    print()
    print(f"📤 Upserting {len(camp_rows)} campaigns...")
    c_ok = c_fail = 0
    for i in range(0, len(camp_rows), args.batch_size):
        s, f = sb_upsert("campaigns", camp_rows[i:i+args.batch_size])
        c_ok += s
        c_fail += f

    print(f"📤 Upserting {len(ad_rows)} ads...")
    a_ok = a_fail = 0
    for i in range(0, len(ad_rows), args.batch_size):
        s, f = sb_upsert("ads", ad_rows[i:i+args.batch_size])
        a_ok += s
        a_fail += f

    print()
    print("=" * 60)
    print(f"RESULT: campaigns={c_ok}/{len(camp_rows)} ads={a_ok}/{len(ad_rows)}")
    print(f"[{datetime.now(timezone.utc).isoformat()}] Done")
    print("=" * 60)

    sys.exit(1 if (c_fail + a_fail) > 0 else 0)


if __name__ == "__main__":
    main()
