"""
Análise detalhada dos 3 ads ACTIVE vencedores das C4.
"""
import requests, json, os
META_TOKEN = os.environ.get("META_TOKEN", "")
BASE = "https://graph.facebook.com/v19.0"
if not META_TOKEN:
    raise SystemExit("defina META_TOKEN no ambiente")
TIME = {"since":"2026-02-28","until":"2026-04-09"}

# Alvos: ads ACTIVE das C4
TARGETS = [
    ("C4 CONVERSAO — AF-CRIPTO FEED (principal)",   "120245573875380651"),
    ("C4 CONVERSAO — BOOST-BROAD CARROSSEL",        "120245573894320651"),
    ("C4 CONSIDERACAO — AF-CRIPTO STORY",           "120245573646250651"),
]

def get(path, **params):
    params["access_token"] = META_TOKEN
    return requests.get(f"{BASE}/{path}", params=params, timeout=30).json()

def fmt_brl(v):
    try: return f"R$ {float(v):,.2f}".replace(",","X").replace(".",",").replace("X",".")
    except: return str(v)

def show_list(label, items, limit=10):
    if not items: return
    print(f"    {label}: {len(items)}")
    for it in items[:limit]:
        name = it.get("name") or it.get("id","?")
        print(f"      - {name}")

def main():
    for label, ad_id in TARGETS:
        print(f"\n\n{'#'*80}")
        print(f"  🎯 {label}")
        print(f"{'#'*80}")

        ad = get(ad_id, fields="id,name,effective_status,adset_id,creative{id,name}")
        print(f"  Nome: {ad.get('name')}")
        print(f"  Status: {ad.get('effective_status')}")
        print(f"  Ad ID: {ad_id}")

        # --- ADSET ---
        adset_id = ad["adset_id"]
        adset = get(adset_id, fields=(
            "id,name,status,optimization_goal,billing_event,bid_strategy,"
            "daily_budget,lifetime_budget,start_time,targeting,promoted_object,"
            "attribution_spec,destination_type"))
        print(f"\n  ━━ ADSET ━━")
        print(f"  {adset.get('name')}")
        print(f"    Otimização:  {adset.get('optimization_goal')}")
        print(f"    Billing:     {adset.get('billing_event')}")
        print(f"    Bid:         {adset.get('bid_strategy')}")
        print(f"    Destination: {adset.get('destination_type')}")
        if adset.get("daily_budget"):
            print(f"    Budget/dia:  {fmt_brl(int(adset['daily_budget'])/100)}")
        if adset.get("lifetime_budget"):
            print(f"    Budget total:{fmt_brl(int(adset['lifetime_budget'])/100)}")

        t = adset.get("targeting", {}) or {}
        print(f"\n  ━━ TARGETING ━━")
        print(f"    Idade:   {t.get('age_min','?')}-{t.get('age_max','?')}")
        g = t.get('genders')
        print(f"    Gênero:  {'todos' if not g else g}")
        geo = t.get("geo_locations", {}) or {}
        print(f"    Países:  {geo.get('countries',[])}")
        if geo.get("regions"):    print(f"    Regiões: {len(geo['regions'])}")
        if geo.get("cities"):     print(f"    Cidades: {len(geo['cities'])}")
        loc_types = t.get("geo_locations", {}).get("location_types") or []
        if loc_types: print(f"    Location types: {loc_types}")

        # interests / behaviors (raiz)
        show_list("Interests (raiz)", t.get("interests") or [])
        show_list("Behaviors (raiz)", t.get("behaviors") or [])

        # flexible_spec
        flex = t.get("flexible_spec") or []
        if flex:
            print(f"    Flexible specs ({len(flex)}):")
            for i, fs in enumerate(flex):
                if fs.get("interests"):  print(f"      [{i}] interests: {[x['name'] for x in fs['interests']]}")
                if fs.get("behaviors"):  print(f"      [{i}] behaviors: {[x['name'] for x in fs['behaviors']]}")
                if fs.get("work_positions"): print(f"      [{i}] work: {[x['name'] for x in fs['work_positions']]}")
                if fs.get("income"):     print(f"      [{i}] income: {[x['name'] for x in fs['income']]}")

        # audiences
        show_list("Custom audiences",          t.get("custom_audiences") or [])
        show_list("Excluded custom audiences", t.get("excluded_custom_audiences") or [])

        # placements
        pp = t.get("publisher_platforms") or []
        if pp:
            print(f"    Platforms: {pp}")
        if t.get("facebook_positions"):  print(f"    FB positions: {t['facebook_positions']}")
        if t.get("instagram_positions"): print(f"    IG positions: {t['instagram_positions']}")
        if t.get("messenger_positions"): print(f"    Messenger positions: {t['messenger_positions']}")
        if t.get("device_platforms"):    print(f"    Devices: {t['device_platforms']}")

        # promoted object (pixel, event)
        po = adset.get("promoted_object") or {}
        if po:
            print(f"    Promoted object: {po}")

        # --- CREATIVE ---
        cre_id = (ad.get("creative") or {}).get("id")
        if cre_id:
            cre = get(cre_id, fields=(
                "id,name,object_type,object_story_spec,asset_feed_spec,"
                "thumbnail_url,image_url,video_id,effective_object_story_id,url_tags"))
            print(f"\n  ━━ CREATIVE ━━")
            print(f"  {cre.get('name','(sem nome)')}")
            print(f"    Tipo: {cre.get('object_type')}")
            if cre.get("url_tags"): print(f"    URL tags: {cre['url_tags']}")
            if cre.get("thumbnail_url"): print(f"    Thumbnail: {cre['thumbnail_url']}")

            oss = cre.get("object_story_spec") or {}
            link_data  = oss.get("link_data") or {}
            video_data = oss.get("video_data") or {}

            if link_data:
                print(f"\n  📝 COPY:")
                if link_data.get("name"):        print(f"    ┌ Headline:")
                if link_data.get("name"):        print(f"    │  {link_data['name']}")
                if link_data.get("description"): print(f"    ├ Description:")
                if link_data.get("description"): print(f"    │  {link_data['description']}")
                if link_data.get("message"):
                    print(f"    ├ Primary text:")
                    for line in link_data["message"].split("\n"):
                        print(f"    │  {line}")
                cta = (link_data.get("call_to_action") or {})
                print(f"    ├ CTA: {cta.get('type','')}")
                print(f"    └ Link: {link_data.get('link','')}")
                if link_data.get("picture"):
                    print(f"\n    🖼️  Imagem: {link_data['picture']}")

                childs = link_data.get("child_attachments") or []
                if childs:
                    print(f"\n  🎠 CARROSSEL ({len(childs)} cards):")
                    for i, c in enumerate(childs, 1):
                        print(f"    ┌ Card {i}")
                        if c.get("name"):        print(f"    │  Título: {c['name']}")
                        if c.get("description"): print(f"    │  Desc:   {c['description']}")
                        if c.get("link"):        print(f"    │  Link:   {c['link']}")
                        if c.get("picture"):     print(f"    │  Img:    {c['picture']}")
                        print(f"    └")

            if video_data:
                print(f"\n  🎬 VIDEO COPY:")
                if video_data.get("title"):   print(f"    Title:   {video_data['title']}")
                if video_data.get("message"):
                    print(f"    Primary text:")
                    for line in video_data["message"].split("\n"):
                        print(f"      {line}")
                cta = (video_data.get("call_to_action") or {})
                print(f"    CTA:     {cta.get('type','')}")
                if video_data.get("video_id"): print(f"    Video ID: {video_data['video_id']}")

            # asset_feed_spec (Advantage+ creative)
            afs = cre.get("asset_feed_spec") or {}
            if afs:
                print(f"\n  🔀 ASSET FEED SPEC (Advantage+):")
                titles = afs.get("titles", [])
                bodies = afs.get("bodies", [])
                descs  = afs.get("descriptions", [])
                if titles:
                    print(f"    Titles ({len(titles)}):")
                    for t_ in titles[:6]:
                        print(f"      • {t_.get('text','')}")
                if bodies:
                    print(f"    Bodies ({len(bodies)}):")
                    for b in bodies[:6]:
                        txt = b.get('text','').replace('\n',' ')[:200]
                        print(f"      • {txt}")
                if descs:
                    print(f"    Descriptions ({len(descs)}):")
                    for d in descs[:6]:
                        print(f"      • {d.get('text','')}")
                if afs.get("images"): print(f"    Images: {len(afs['images'])}")
                if afs.get("videos"): print(f"    Videos: {len(afs['videos'])}")

        # --- PERFORMANCE ---
        ins = get(f"{ad_id}/insights",
                  time_range=json.dumps(TIME),
                  fields="spend,impressions,reach,clicks,ctr,cpc,cpm,actions,frequency",
                  level="ad")
        if ins.get("data"):
            d = ins["data"][0]
            print(f"\n  ━━ PERFORMANCE (28/fev → 09/abr) ━━")
            print(f"    Spend:       {fmt_brl(d.get('spend',0))}")
            print(f"    Impressões:  {int(d.get('impressions',0)):,}".replace(",","."))
            print(f"    Alcance:     {int(d.get('reach',0)):,}".replace(",","."))
            print(f"    Frequência:  {float(d.get('frequency',0)):.2f}")
            print(f"    Cliques:     {int(d.get('clicks',0)):,}".replace(",","."))
            print(f"    CTR:         {float(d.get('ctr',0)):.2f}%")
            print(f"    CPC:         {fmt_brl(d.get('cpc',0))}")
            print(f"    CPM:         {fmt_brl(d.get('cpm',0))}")
            for a in (d.get("actions") or []):
                at = a.get("action_type")
                if at in ("lead","onsite_conversion.lead_grouped","landing_page_view","link_click"):
                    print(f"    {at}: {a.get('value')}")

if __name__ == "__main__":
    main()
