"""
debug_tracking_c4.py
Investiga por que 68% dos leads das C4 perdem atribuição UTM.

Passo A: Puxa os url_tags de TODOS os ads ACTIVE das C4 CONVERSAO e CONSIDERACAO,
         verifica se cada um tem macros {{campaign.name}}, {{ad.name}} etc.

Passo B: Extrai URL de destino de cada ad e faz HEAD request pra ver redirecionamentos
         (LP pode ter redirect que corta query string).
"""
import os, re, requests
META_TOKEN = os.environ.get("META_TOKEN","")
if not META_TOKEN:
    raise SystemExit("defina META_TOKEN no ambiente")
BASE = "https://graph.facebook.com/v19.0"

CAMPS = {
    "C4 CONVERSAO":   "120245573868070651",
    "C4 CONSIDERACAO":"120245573637600651",
}

MACROS_ESPERADAS = ["{{campaign.name}}", "{{ad.name}}", "{{adset.name}}"]


def get(path, **params):
    params["access_token"] = META_TOKEN
    return requests.get(f"{BASE}/{path}", params=params, timeout=30).json()


def check_url_tags(url_tags):
    if not url_tags:
        return "VAZIO", []
    found = [m for m in MACROS_ESPERADAS if m in url_tags]
    missing = [m for m in MACROS_ESPERADAS if m not in url_tags]
    if len(found) == 3:
        return "OK", []
    if len(found) > 0:
        return "PARCIAL", missing
    return "SEM_MACROS", MACROS_ESPERADAS


def extract_destination(link_data, video_data):
    if link_data and link_data.get("link"):
        return link_data["link"]
    if video_data and video_data.get("call_to_action"):
        v = video_data["call_to_action"].get("value") or {}
        if v.get("link"):
            return v["link"]
    return None


def main():
    print("="*90)
    print("  DEBUG TRACKING C4 — investigação de perda de atribuição UTM")
    print("="*90)

    for nome, cid in CAMPS.items():
        print(f"\n\n▶ {nome} ({cid})")
        print("-"*90)

        ads = get(f"{cid}/ads",
                  fields="id,name,effective_status,creative{id,url_tags,object_story_spec,asset_feed_spec}",
                  limit=200).get("data", [])

        print(f"  Total ads: {len(ads)}")
        actives = [a for a in ads if a.get("effective_status") == "ACTIVE"]
        print(f"  Ads ACTIVE: {len(actives)}\n")

        if not actives:
            continue

        stats = {"OK": 0, "PARCIAL": 0, "SEM_MACROS": 0, "VAZIO": 0}
        problemas = []

        for ad in actives:
            cre = ad.get("creative") or {}
            url_tags = cre.get("url_tags") or ""
            oss = cre.get("object_story_spec") or {}
            link_data = oss.get("link_data") or {}
            video_data = oss.get("video_data") or {}
            destination = extract_destination(link_data, video_data)
            status_tag, missing = check_url_tags(url_tags)
            stats[status_tag] += 1

            # Checa também se o destination URL já tem UTMs
            dest_has_utm = destination and ("utm_" in destination or "{{" in destination)

            if status_tag != "OK" and not dest_has_utm:
                problemas.append({
                    "id": ad["id"],
                    "name": ad["name"],
                    "status_tag": status_tag,
                    "missing": missing,
                    "url_tags": url_tags,
                    "destination": destination or "(sem destination)",
                })

        print(f"  url_tags OK (3 macros):        {stats['OK']}")
        print(f"  url_tags PARCIAL (1-2 macros): {stats['PARCIAL']}")
        print(f"  url_tags SEM macros:           {stats['SEM_MACROS']}")
        print(f"  url_tags VAZIO:                {stats['VAZIO']}")

        if problemas:
            print(f"\n  ⚠️ {len(problemas)} ads com problema:")
            for p in problemas[:20]:
                print(f"\n    • {p['name']}  (id={p['id']})")
                print(f"      status:      {p['status_tag']}")
                if p['missing']:
                    print(f"      faltando:    {p['missing']}")
                print(f"      url_tags:    {p['url_tags'][:100] or '(vazio)'}")
                print(f"      destination: {p['destination'][:100]}")
        else:
            print(f"\n  ✅ Todos os ads ACTIVE têm url_tags OK")

        # Também mostra um exemplo de URL completa que será chamada
        if actives:
            first = actives[0]
            cre = first.get("creative") or {}
            oss = cre.get("object_story_spec") or {}
            link_data = oss.get("link_data") or {}
            dest = link_data.get("link", "")
            tags = cre.get("url_tags", "")
            print(f"\n  📎 Exemplo de URL completa (ad: {first['name'][:40]}):")
            if "?" in dest:
                full = f"{dest}&{tags}" if tags else dest
            else:
                full = f"{dest}?{tags}" if tags else dest
            print(f"     {full[:200]}")


if __name__ == "__main__":
    main()
