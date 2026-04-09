"""
fetch_meta.py
Puxa todos os dados da API Meta Ads para o dashboard semanal.
Token vitalício — sem refresh necessário.
"""
import json, urllib.request, urllib.parse, ssl, sys, os
from datetime import datetime, timedelta

TOKEN = os.environ.get('META_ACCESS_TOKEN') or os.environ.get('META_TOKEN') or ''
if not TOKEN:
    raise SystemExit('ERRO: defina META_ACCESS_TOKEN (ou META_TOKEN) no ambiente')
ACCOUNT = 'act_844208497068966'
BASE    = 'https://graph.facebook.com/v19.0'

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def api(path, params={}):
    params['access_token'] = TOKEN
    url = f'{BASE}{path}?{urllib.parse.urlencode(params)}'
    try:
        with urllib.request.urlopen(url, context=ctx, timeout=30) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f'  API err {path}: {e}', file=sys.stderr)
        return {}

def get_actions(actions, key):
    for a in (actions or []):
        if a.get('action_type') == key:
            return int(float(a.get('value', 0)))
    return 0

def fetch_campaigns(date_preset='this_month'):
    """Insights por campanha no mês atual."""
    fields = 'campaign_id,campaign_name,spend,impressions,clicks,ctr,actions,date_start,date_stop'
    r = api(f'/{ACCOUNT}/insights', {
        'level': 'campaign',
        'fields': fields,
        'date_preset': date_preset,
        'limit': 100
    })
    campaigns = []
    for c in r.get('data', []):
        actions = c.get('actions', [])
        leads = get_actions(actions, 'onsite_conversion.lead_grouped') or get_actions(actions, 'lead')
        campaigns.append({
            'id':          c.get('campaign_id', ''),
            'name':        c.get('campaign_name', ''),
            'spend':       float(c.get('spend', 0)),
            'impressions': int(c.get('impressions', 0)),
            'clicks':      int(c.get('clicks', 0)),
            'ctr':         float(c.get('ctr', 0)),
            'leads':       leads,
            'cpl':         round(float(c.get('spend', 0)) / leads, 2) if leads else 0,
            'date_start':  c.get('date_start', ''),
            'date_stop':   c.get('date_stop', ''),
        })
    return campaigns

def fetch_ads(date_preset='this_month'):
    """Insights por ad (criativo) no mês atual."""
    fields = 'ad_id,ad_name,campaign_name,adset_name,spend,impressions,clicks,ctr,actions'
    r = api(f'/{ACCOUNT}/insights', {
        'level': 'ad',
        'fields': fields,
        'date_preset': date_preset,
        'limit': 200
    })
    ads = []
    for a in r.get('data', []):
        actions = a.get('actions', [])
        leads = get_actions(actions, 'onsite_conversion.lead_grouped') or get_actions(actions, 'lead')
        if float(a.get('spend', 0)) < 1:
            continue
        ads.append({
            'id':           a.get('ad_id', ''),
            'name':         a.get('ad_name', ''),
            'campaign':     a.get('campaign_name', ''),
            'adset':        a.get('adset_name', ''),
            'spend':        float(a.get('spend', 0)),
            'impressions':  int(a.get('impressions', 0)),
            'clicks':       int(a.get('clicks', 0)),
            'ctr':          float(a.get('ctr', 0)),
            'leads':        leads,
            'cpl':          round(float(a.get('spend', 0)) / leads, 2) if leads else 0,
        })
    ads.sort(key=lambda x: x['leads'], reverse=True)
    return ads

def fetch_weekly(year=None, month=None):
    """Breakdown semanal do mês."""
    now = datetime.now()
    year  = year  or now.year
    month = month or now.month

    from calendar import monthrange
    first_day = datetime(year, month, 1)
    last_day  = datetime(year, month, monthrange(year, month)[1])

    r = api(f'/{ACCOUNT}/insights', {
        'level':          'account',
        'fields':         'spend,impressions,clicks,ctr,actions',
        'time_increment': 7,
        'time_range':     json.dumps({'since': first_day.strftime('%Y-%m-%d'),
                                      'until': last_day.strftime('%Y-%m-%d')}),
        'limit':          10
    })
    weeks = []
    for w in r.get('data', []):
        actions = w.get('actions', [])
        leads   = get_actions(actions, 'onsite_conversion.lead_grouped') or get_actions(actions, 'lead')
        spend   = float(w.get('spend', 0))
        weeks.append({
            'date_start':  w.get('date_start', ''),
            'date_stop':   w.get('date_stop',  ''),
            'spend':       spend,
            'impressions': int(w.get('impressions', 0)),
            'clicks':      int(w.get('clicks', 0)),
            'ctr':         float(w.get('ctr', 0)),
            'leads':       leads,
            'cpl':         round(spend / leads, 2) if leads else 0,
        })
    return weeks

def fetch_creative_thumb(ad_id):
    """Busca imagem em alta resolução de um ad. Tenta múltiplos campos."""
    import base64

    # Pega o creative_id
    r = api(f'/{ad_id}', {'fields': 'creative'})
    cid = r.get('creative', {}).get('id')
    if not cid:
        return None

    # Tenta campos em ordem de qualidade decrescente
    r2 = api(f'/{cid}', {
        'fields': 'image_url,thumbnail_url,object_story_spec'
    })

    # 1. image_url — imagem original em alta resolução
    url = r2.get('image_url')

    # 2. object_story_spec — link, video ou carrossel
    if not url:
        spec = r2.get('object_story_spec', {})
        link_data = spec.get('link_data', {})
        url = (link_data.get('picture') or
               spec.get('video_data', {}).get('image_url') or
               spec.get('photo_data', {}).get('url'))
        # Carrossel: pega image_hash do primeiro card e busca URL
        if not url:
            children = link_data.get('child_attachments', [])
            if children:
                img_hash = children[0].get('image_hash')
                if img_hash:
                    r3 = api(f'/{ACCOUNT}/adimages', {
                        'hashes': f'["{img_hash}"]',
                        'fields': 'url'
                    })
                    imgs = r3.get('data', [])
                    if imgs:
                        url = imgs[0].get('url')

    # 3. thumbnail_url — fallback menor
    if not url:
        url = r2.get('thumbnail_url')

    if not url:
        return None

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ctx, timeout=12) as resp:
            data = resp.read()
            ct   = resp.headers.get('Content-Type', 'image/jpeg').split(';')[0]
            return f'data:{ct};base64,{base64.b64encode(data).decode()}'
    except:
        return None

# ─── Agrupamento de campanhas ─────────────────────────────────
GRUPOS = [
    ('Reels',        lambda n: ('MORNO' in n or 'QUENTE' in n) and ('REEL' in n or 'MANUAL' in n)),
    ('Criativos',    lambda n: 'TEST' in n and 'CRIATIV' in n),
    ('Awareness',    lambda n: 'AWARENESS' in n),
    ('Captação',     lambda n: 'CAPTACAO' in n or 'CONSIDERACAO' in n or 'CONVERSAO' in n),
    ('IR Cripto',    lambda n: 'IR' in n and 'CRIPTO' in n),
    ('Posts',        lambda n: 'POST' in n or 'IMPULS' in n or 'CONTENT' in n),
]

def group_campaigns(campaigns):
    """Agrupa campanhas e soma métricas."""
    groups = {g: {'spend': 0, 'leads': 0, 'impressions': 0, 'clicks': 0}
              for g, _ in GRUPOS}
    groups['Outros'] = {'spend': 0, 'leads': 0, 'impressions': 0, 'clicks': 0}

    for c in campaigns:
        name = c['name'].upper()
        matched = False
        for gname, fn in GRUPOS:
            if fn(name):
                groups[gname]['spend']       += c['spend']
                groups[gname]['leads']       += c['leads']
                groups[gname]['impressions'] += c['impressions']
                groups[gname]['clicks']      += c['clicks']
                matched = True
                break
        if not matched:
            groups['Outros']['spend']       += c['spend']
            groups['Outros']['leads']       += c['leads']
            groups['Outros']['impressions'] += c['impressions']
            groups['Outros']['clicks']      += c['clicks']

    result = []
    for gname, _ in GRUPOS + [('Outros', None)]:
        g = groups[gname]
        if g['spend'] > 0 or g['leads'] > 0:
            result.append({
                'group':       gname,
                'spend':       round(g['spend'], 2),
                'leads':       g['leads'],
                'impressions': g['impressions'],
                'clicks':      g['clicks'],
                'cpl':         round(g['spend'] / g['leads'], 2) if g['leads'] else 0,
            })
    return result

if __name__ == '__main__':
    print('Buscando campanhas...')
    campaigns = fetch_campaigns()
    print(f'  {len(campaigns)} campanhas')

    print('Buscando ads...')
    ads = fetch_ads()
    print(f'  {len(ads)} ads com gasto > R$1')

    print('Buscando breakdown semanal...')
    weeks = fetch_weekly()
    print(f'  {len(weeks)} semanas')

    print('Agrupando campanhas...')
    groups = group_campaigns(campaigns)
    for g in groups:
        print(f"  {g['group']}: R${g['spend']:,.0f} | {g['leads']} leads | R${g['cpl']}/lead")

    data = {'campaigns': campaigns, 'ads': ads, 'weeks': weeks, 'groups': groups}
    with open('/tmp/meta_data.json', 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print('\nSalvo em /tmp/meta_data.json')

    print('Buscando thumbnails dos criativos...')
    thumbs = {}
    for a in ads[:20]:
        t = fetch_creative_thumb(a['id'])
        if t:
            thumbs[a['id']] = t
            print(f"  ✅ {a['name'][:40]}")
        else:
            print(f"  — sem thumb: {a['name'][:40]}")
    with open('/tmp/thumbs.json', 'w') as f:
        json.dump(thumbs, f)
    print(f'  {len(thumbs)} thumbnails salvos em /tmp/thumbs.json')
