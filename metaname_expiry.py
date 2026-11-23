"""Read-only Metaname expiry lookup using domain_names."""
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import time
from urllib.request import Request, urlopen

API_URL = os.environ.get('METANAME_API_URL', 'https://metaname.net/api/1.1')
CACHE_SECONDS = 24 * 3600
DATA_DIR = Path(os.environ.get('DATA_DIR', '/data'))
CACHE_FILE = DATA_DIR / 'metaname-expiry-cache.json'
LOCK_FILE = DATA_DIR / 'metaname-expiry-cache.lock'
MAX_RESPONSE = 4 * 1024 * 1024


def configured():
    return bool(os.environ.get('METANAME_REFERENCE', '').strip() and
                os.environ.get('METANAME_API_KEY', '').strip())


def _parse_expiry(value):
    """Preserve Metaname's NZ calendar date as a date-only UTC value."""
    text = str(value or '').strip()
    if not text:
        return None
    day = datetime.fromisoformat(text.replace('Z', '+00:00')).date()
    return datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc).timestamp()


def _read_cache(now):
    try:
        data = json.loads(CACHE_FILE.read_text())
        if now - float(data.get('fetched_at', 0)) <= CACHE_SECONDS:
            domains = data.get('domains')
            if isinstance(domains, dict):
                return domains
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        pass
    return None


def _fetch(now):
    reference = os.environ.get('METANAME_REFERENCE', '').strip()
    api_key = os.environ.get('METANAME_API_KEY', '').strip()
    payload = json.dumps({
        'jsonrpc': '2.0', 'id': 'domain-monitor',
        'method': 'domain_names', 'params': [reference, api_key],
    }).encode('utf-8')
    request = Request(API_URL, data=payload, headers={
        'Content-Type': 'application/json',
        'User-Agent': 'Domain-Monitor/1.9.0',
    }, method='POST')
    with urlopen(request, timeout=30) as response:
        raw = response.read(MAX_RESPONSE + 1)
    if len(raw) > MAX_RESPONSE:
        raise ValueError('Metaname response exceeded size limit')
    reply = json.loads(raw.decode('utf-8'))
    if reply.get('error'):
        error = reply['error']
        raise ValueError('Metaname API error ' + str(error.get('code', 'unknown')))
    rows = reply.get('result')
    if not isinstance(rows, list):
        raise ValueError('Unexpected Metaname response')
    domains = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get('name') or '').strip().rstrip('.').lower()
        expiry = _parse_expiry(row.get('when_paid_up_to'))
        if name and expiry is not None:
            domains[name] = expiry
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = CACHE_FILE.with_suffix('.tmp')
    temporary.write_text(json.dumps({'fetched_at': now, 'domains': domains}, sort_keys=True))
    os.chmod(temporary, 0o600)
    temporary.replace(CACHE_FILE)
    return domains


def domains(now=None):
    if not configured():
        return None
    now = time.time() if now is None else now
    cached = _read_cache(now)
    if cached is not None:
        return cached
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_FILE.open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        cached = _read_cache(now)
        return cached if cached is not None else _fetch(now)


def lookup(registration_domain, now=None):
    if not configured():
        return None
    now = time.time() if now is None else now
    try:
        expiry = domains(now).get(str(registration_domain).rstrip('.').lower())
    except Exception:
        return None
    if expiry is None:
        return None
    return {
        'status': 'ok', 'checked_at': now, 'expires_at': expiry,
        'days_remaining': int((expiry - now) // 86400),
        'source': 'Metaname', 'registration_domain': registration_domain,
    }
