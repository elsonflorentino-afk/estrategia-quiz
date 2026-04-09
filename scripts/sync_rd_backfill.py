"""
sync_rd_backfill.py — Backfill histórico completo RD Station → Supabase.

Roda localmente (não tem WORKER_LIMIT do Supabase Free tier).
Usa a segmentação "Todos os contatos" (ID 19272914) pra paginar TUDO.

Uso:
    export SUPABASE_SERVICE_ROLE_KEY="sb_secret_..."
    python3 sync_rd_backfill.py                      # backfill completo (default)
    python3 sync_rd_backfill.py --days 90            # só últimos 90 dias
    python3 sync_rd_backfill.py --dry-run            # só conta, não grava
    python3 sync_rd_backfill.py --max 500            # limita pra teste

Precisa de: requests, python-dateutil (ou só datetime built-in).
"""
import os
import re
import sys
import time
import json
import argparse
from datetime import datetime, timezone, timedelta

try:
    import requests
except ImportError:
    print("ERRO: instale requests → pip3 install requests")
    sys.exit(1)

# ===== Config =====
RD_CLIENT_ID     = os.environ.get('RD_CLIENT_ID',     '')
RD_CLIENT_SECRET = os.environ.get('RD_CLIENT_SECRET', '')
RD_REFRESH_TOKEN = os.environ.get('RD_REFRESH_TOKEN', '')
RD_BASE = 'https://api.rd.services'
SEGMENT_ID = '19272914'  # "Todos os contatos"

SUPABASE_URL = 'https://dvvfnrdvhkjfovhfqiow.supabase.co'
SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')

PAGE_SIZE = 125
RATE_LIMIT_MS = 120  # ms entre requests RD

# Custom fields
CF_PAT_CRIPTO = 'cf_que_otimo_agora_preciso_entender_qual_seu_patrimonio_ho'
CF_PAT_TRAD   = 'cf_qual_seu_patrimonio_investido_no_mercado_tradicional'
CF_INV_CRIPTO = 'cf_voce_ja_possui_investimentos_em_bitcoin_cripto'
# Nome REAL do field no RD Station (confirmado via GET /contacts/{uuid} em 09/abr/2026).
# Ignora o nome que a LP tenta enviar — o RD armazena com esse nome aqui.
# Fallbacks pra histórico de leads de outras LPs/forms.
CF_INV_TRAD         = 'cf_e_voce_possui_investimentos_no_mercado_tradicional_teso'
CF_INV_TRAD_LEGACY1 = 'cf_voce_ja_investe_no_mercado_tradicional_tesouro_cdi_a'
CF_INV_TRAD_LEGACY2 = 'cf_voce_investe_no_mercado_tradicional'
CF_UTM_SOURCE   = 'cf_utm_source'
CF_UTM_MEDIUM   = 'cf_utm_medium'
CF_UTM_CAMPAIGN = 'cf_utm_campaign'
CF_UTM_CONTENT  = 'cf_utm_content'
CF_UTM_TERM     = 'cf_utm_term'


# ===== RD Station =====
def rd_token():
    r = requests.post(f'{RD_BASE}/auth/token', json={
        'client_id': RD_CLIENT_ID,
        'client_secret': RD_CLIENT_SECRET,
        'refresh_token': RD_REFRESH_TOKEN
    }, timeout=15)
    r.raise_for_status()
    t = r.json().get('access_token')
    if not t:
        raise RuntimeError(f'Sem token: {r.json()}')
    return t


def rd_get(path, token, params=None, max_retries=3):
    url = f'{RD_BASE}{path}'
    for attempt in range(max_retries):
        try:
            r = requests.get(url, params=params or {}, headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }, timeout=30)
            if r.status_code == 429:
                time.sleep(2 + attempt * 2)
                continue
            if r.status_code == 401:
                return None  # token expirou, caller renova
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                print(f'  ! erro {path}: {e}', file=sys.stderr)
                return {}
            time.sleep(1 + attempt)
    return {}


def iter_contacts(token_ref, cutoff_date=None, max_contacts=None):
    """Gera contatos da segmentação paginando 125/página. Inclui created_at."""
    page = 1
    seen = 0
    while True:
        data = rd_get(f'/platform/segmentations/{SEGMENT_ID}/contacts', token_ref[0], {
            'page': page,
            'page_size': PAGE_SIZE
        })
        if data is None:  # 401
            token_ref[0] = rd_token()
            continue
        contacts = (data or {}).get('contacts', [])
        if not contacts:
            return
        for c in contacts:
            # Filtra por data se cutoff definido
            created = c.get('created_at') or c.get('last_conversion_date')
            if cutoff_date and created:
                try:
                    dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    if dt < cutoff_date:
                        continue
                except Exception:
                    pass
            yield c
            seen += 1
            if max_contacts and seen >= max_contacts:
                return
        page += 1
        time.sleep(RATE_LIMIT_MS / 1000)


def get_contact_detail(uuid, token_ref):
    d = rd_get(f'/platform/contacts/{uuid}', token_ref[0])
    if d is None:
        token_ref[0] = rd_token()
        d = rd_get(f'/platform/contacts/{uuid}', token_ref[0])
    return d or {}


def extract_cf(contact, field):
    for cf in (contact.get('cf') or []):
        if (cf.get('custom_field') or {}).get('api_identifier') == field:
            return cf.get('value') or ''
    # Também tenta no formato direto
    return contact.get(field) or ''


# ===== Parsing =====
def parse_patrimonio_to_k(txt):
    """Converte '$Entre R$ 50 mil a R$ 200 mil' → 50 (piso em milhares)."""
    if not txt:
        return None
    s = str(txt).lower().replace('.', '').replace(',', '.')

    # "acima de" ou "5oo mil+"
    if 'acima' in s or 'mais de' in s:
        nums = re.findall(r'(\d+(?:\.\d+)?)', s)
        if nums:
            n = float(nums[0])
            # "acima de 1 milhão" → 1000
            if 'milh' in s or 'mi' in s:
                return n * 1000
            return n

    # "até"
    if 'até' in s or 'menos' in s:
        return 1  # faixa < R$10k

    # "entre X e Y" → pega X (piso)
    nums = re.findall(r'(\d+(?:\.\d+)?)', s)
    if not nums:
        return None
    n = float(nums[0])

    # Se tem "milh" (milhões) no contexto do primeiro número
    if 'milh' in s and n < 10:
        return n * 1000
    return n


def parse_yes_no(txt):
    if not txt:
        return None
    s = str(txt).lower()
    if s in ('sim', 'yes', 'true', '1'):
        return True
    if s in ('não', 'nao', 'no', 'false', '0'):
        return False
    return None


def patrimonio_min_k(pat_cripto_k, pat_trad_k):
    """Maior dos dois pra flag is_qualified."""
    a = pat_cripto_k or 0
    b = pat_trad_k or 0
    return max(a, b)


def map_contact_to_lead(list_contact, detail):
    """Mescla list + detail em um row pra upsert."""
    email = detail.get('email') or list_contact.get('email')
    if not email:
        return None

    pat_cripto_raw = extract_cf(detail, CF_PAT_CRIPTO)
    pat_trad_raw   = extract_cf(detail, CF_PAT_TRAD)
    pat_cripto_k = parse_patrimonio_to_k(pat_cripto_raw)
    pat_trad_k   = parse_patrimonio_to_k(pat_trad_raw)

    # investe_tradicional: tenta nome atual do RD, cai pros legacy
    inv_trad_raw = (extract_cf(detail, CF_INV_TRAD)
                    or extract_cf(detail, CF_INV_TRAD_LEGACY1)
                    or extract_cf(detail, CF_INV_TRAD_LEGACY2))

    maior = patrimonio_min_k(pat_cripto_k, pat_trad_k)
    is_qualified = maior >= 50  # ≥R$50k

    # created_at vem do list (detail não tem)
    created = list_contact.get('created_at') or list_contact.get('last_conversion_date')

    return {
        'rd_uuid': detail.get('uuid') or list_contact.get('uuid'),
        'email': email.lower().strip(),
        'name': detail.get('name') or list_contact.get('name'),
        'phone': detail.get('personal_phone') or detail.get('mobile_phone'),
        'investe_cripto': parse_yes_no(extract_cf(detail, CF_INV_CRIPTO)),
        'patrimonio_cripto': pat_cripto_raw or None,
        'patrimonio_cripto_min_k': pat_cripto_k,
        'investe_tradicional': parse_yes_no(inv_trad_raw),
        'patrimonio_tradicional': pat_trad_raw or None,
        'patrimonio_tradicional_min_k': pat_trad_k,
        'first_source':   extract_cf(detail, CF_UTM_SOURCE)   or None,
        'first_medium':   extract_cf(detail, CF_UTM_MEDIUM)   or None,
        'first_campaign': extract_cf(detail, CF_UTM_CAMPAIGN) or None,
        'first_content':  extract_cf(detail, CF_UTM_CONTENT)  or None,
        'first_term':     extract_cf(detail, CF_UTM_TERM)     or None,
        'last_activity_at': list_contact.get('last_conversion_date') or created,
        'is_qualified': is_qualified,
        'created_at': created,
    }


# ===== Supabase =====
def supabase_upsert_batch(rows):
    """Upsert em batch via PostgREST. onConflict=email.
    IMPORTANTE: PostgREST exige que todas as rows tenham EXATAMENTE as mesmas keys.
    Por isso mantemos todas as keys, mesmo com None (vira null no JSON).
    """
    if not rows:
        return 0
    # Coleta todas as keys possíveis
    all_keys = set()
    for r in rows:
        all_keys.update(r.keys())
    # Normaliza todas as rows pra ter as mesmas keys
    clean = [{k: r.get(k) for k in all_keys} for r in rows]
    resp = requests.post(
        f'{SUPABASE_URL}/rest/v1/leads',
        headers={
            'apikey': SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}',
            'Content-Type': 'application/json',
            'Prefer': 'resolution=merge-duplicates,return=minimal',
        },
        params={'on_conflict': 'email'},
        data=json.dumps(clean),
        timeout=60,
    )
    if resp.status_code >= 300:
        print(f'  ! Supabase err {resp.status_code}: {resp.text[:300]}', file=sys.stderr)
        return 0
    return len(clean)


# ===== Main =====
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=None, help='últimos N dias (default: tudo)')
    ap.add_argument('--max', type=int, default=None, help='limite de contatos (teste)')
    ap.add_argument('--dry-run', action='store_true', help='não grava no Supabase')
    ap.add_argument('--batch', type=int, default=25, help='tamanho do batch upsert')
    args = ap.parse_args()

    if not args.dry_run and not SUPABASE_KEY:
        print('ERRO: defina SUPABASE_SERVICE_ROLE_KEY no ambiente')
        print('  export SUPABASE_SERVICE_ROLE_KEY="sb_secret_..."')
        sys.exit(1)

    cutoff = None
    if args.days:
        cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
        print(f'Backfill a partir de {cutoff.date()} ({args.days} dias)')
    else:
        print('Backfill COMPLETO (todos os contatos da segmentação)')

    if args.dry_run:
        print('🧪 DRY RUN — não grava no Supabase')

    print('Renovando token RD...')
    token_ref = [rd_token()]

    total = 0
    upserted = 0
    batch = []
    start = time.time()
    sem_email = 0
    sem_utm = 0

    for list_c in iter_contacts(token_ref, cutoff_date=cutoff, max_contacts=args.max):
        uuid = list_c.get('uuid')
        if not uuid:
            continue

        detail = get_contact_detail(uuid, token_ref)
        row = map_contact_to_lead(list_c, detail)
        total += 1

        if not row:
            sem_email += 1
        else:
            if not row.get('first_campaign'):
                sem_utm += 1
            batch.append(row)

        if len(batch) >= args.batch:
            if not args.dry_run:
                upserted += supabase_upsert_batch(batch)
            batch = []

        if total % 25 == 0:
            elapsed = time.time() - start
            rate = total / elapsed if elapsed > 0 else 0
            print(f'  [{total:5d}] upsert={upserted} sem_utm={sem_utm} sem_email={sem_email} | {rate:.1f}/s')

        time.sleep(RATE_LIMIT_MS / 1000)

    # flush final
    if batch and not args.dry_run:
        upserted += supabase_upsert_batch(batch)

    dur = time.time() - start
    print('\n' + '=' * 60)
    print(f'Total processado:  {total}')
    print(f'Upserts ok:        {upserted}')
    print(f'Sem email:         {sem_email}')
    print(f'Com UTM campaign:  {total - sem_utm}')
    print(f'Sem UTM campaign:  {sem_utm}')
    print(f'Duração:           {dur:.1f}s ({total/dur:.1f}/s)' if dur else '-')


if __name__ == '__main__':
    main()
