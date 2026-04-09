"""
fetch_rd.py
Puxa leads qualificados do RD Station via OAuth2.
Access token expira em 24h — renovado automaticamente via refresh_token.
"""
import json, urllib.request, urllib.parse, ssl, os, sys

RD_CLIENT_ID     = os.environ.get('RD_CLIENT_ID',     '')
RD_CLIENT_SECRET = os.environ.get('RD_CLIENT_SECRET', '')
RD_REFRESH_TOKEN = os.environ.get('RD_REFRESH_TOKEN', '')
if not all([RD_CLIENT_ID, RD_CLIENT_SECRET, RD_REFRESH_TOKEN]):
    raise SystemExit('ERRO: defina RD_CLIENT_ID, RD_CLIENT_SECRET e RD_REFRESH_TOKEN no ambiente')
BASE = 'https://api.rd.services'

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def get_access_token():
    """Renova access token via refresh_token."""
    payload = json.dumps({
        'client_id':     RD_CLIENT_ID,
        'client_secret': RD_CLIENT_SECRET,
        'refresh_token': RD_REFRESH_TOKEN
    }).encode()
    req = urllib.request.Request(
        f'{BASE}/auth/token',
        data=payload,
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
        data = json.loads(r.read())
        token = data.get('access_token')
        if not token:
            raise Exception(f'Token não retornado: {data}')
        print(f'  RD token renovado OK')
        return token

def rd_get(path, token, params={}):
    """GET na API RD Station."""
    qs = urllib.parse.urlencode(params)
    url = f'{BASE}{path}{"?" + qs if qs else ""}'
    req = urllib.request.Request(url, headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    })
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=20) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f'  RD API err {path}: {e}', file=sys.stderr)
        return {}

def fetch_contacts_by_event(token, event_identifier, max_pages=10):
    """Busca todos os contatos que tiveram um evento de conversão específico."""
    contacts = []
    page = 1
    while page <= max_pages:
        r = rd_get('/platform/contacts', token, {
            'event_type':       'CONVERSION',
            'event_identifier': event_identifier,
            'page':             page,
            'page_size':        50
        })
        items = r.get('contacts', [])
        if not items:
            break
        contacts.extend(items)
        total = r.get('total', 0)
        if len(contacts) >= total:
            break
        page += 1
    return contacts

def extract_cf(contact, field):
    """Extrai campo personalizado (cf_) do contato."""
    for cf in contact.get('cf', []) or []:
        if cf.get('custom_field', {}).get('api_identifier') == field:
            return cf.get('value', '')
    return ''

def analyze_qualification(contacts):
    """Analisa qualificação dos leads da LP."""
    total = len(contacts)
    investe_cripto   = sum(1 for c in contacts if extract_cf(c, 'cf_voce_ja_possui_investimentos_em_bitcoin_cripto') == 'sim')
    nao_cripto       = sum(1 for c in contacts if extract_cf(c, 'cf_voce_ja_possui_investimentos_em_bitcoin_cripto') == 'não')
    investe_trad     = sum(1 for c in contacts if extract_cf(c, 'cf_voce_ja_investe_no_mercado_tradicional_tesouro_cdi_a') == 'sim')

    # Patrimônio cripto (faixas)
    pat_cripto_field = 'cf_que_otimo_agora_preciso_entender_qual_seu_patrimonio_ho'
    pat_cripto = {}
    for c in contacts:
        v = extract_cf(c, pat_cripto_field)
        if v:
            pat_cripto[v] = pat_cripto.get(v, 0) + 1

    # Patrimônio tradicional (faixas)
    pat_trad_field = 'cf_qual_seu_patrimonio_investido_no_mercado_tradicional'
    pat_trad = {}
    for c in contacts:
        v = extract_cf(c, pat_trad_field)
        if v:
            pat_trad[v] = pat_trad.get(v, 0) + 1

    # Qualificados cripto ≥ R$50k
    qualif_cripto = sum(v for k, v in pat_cripto.items()
                        if any(x in k for x in ['50', '200', '500', '800']))

    # Qualificados tradicional ≥ R$50k
    qualif_trad = sum(v for k, v in pat_trad.items()
                      if any(x in k for x in ['50', '200', '500', '800']))

    return {
        'total':           total,
        'investe_cripto':  investe_cripto,
        'nao_cripto':      nao_cripto,
        'investe_trad':    investe_trad,
        'pat_cripto':      dict(sorted(pat_cripto.items())),
        'pat_trad':        dict(sorted(pat_trad.items())),
        'qualif_cripto':   qualif_cripto,
        'qualif_trad':     qualif_trad,
        'pct_qualif':      round(qualif_cripto / investe_cripto * 100, 1) if investe_cripto else 0,
    }

if __name__ == '__main__':
    print('Renovando token RD Station...')
    token = get_access_token()

    print('Buscando leads lp_mentoria_boost...')
    c4_contacts = fetch_contacts_by_event(token, 'lp_mentoria_boost')
    print(f'  {len(c4_contacts)} leads')

    print('Buscando leads lp_ir_cripto...')
    ir_contacts = fetch_contacts_by_event(token, 'lp_ir_cripto')
    print(f'  {len(ir_contacts)} leads')

    print('Analisando qualificação...')
    c4_qual = analyze_qualification(c4_contacts)
    ir_qual = analyze_qualification(ir_contacts)

    print(f'  LP C4: {c4_qual["investe_cripto"]} investem cripto | {c4_qual["qualif_cripto"]} qualif ≥R$50k ({c4_qual["pct_qualif"]}%)')
    print(f'  IR Cripto: {ir_qual["total"]} leads')

    data = {
        'lp_mentoria_boost': {'contacts': len(c4_contacts), 'qualification': c4_qual},
        'lp_ir_cripto':      {'contacts': len(ir_contacts), 'qualification': ir_qual},
    }
    with open('/tmp/rd_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print('\nSalvo em /tmp/rd_data.json')
