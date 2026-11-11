"""Cached domain registration expiry; separate from email-health status."""
from datetime import date, datetime, timezone
import json
import re
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

USER_AGENT='Domain-Monitor/0.13.2 (+https://github.com/SynMatt/domain-monitor)'
MAX_RESPONSE=1024*1024
NZ_WHOIS_HOST='whois.irs.net.nz'


def validate_manual_date(value):
    value=(value or '').strip()
    if not value:
        return ''
    try:
        parsed=date.fromisoformat(value)
    except ValueError:
        raise ValueError('Enter the manual expiry date as YYYY-MM-DD.')
    if parsed.year < 1970 or parsed.year > 2200:
        raise ValueError('Enter a reasonable manual expiry date.')
    return parsed.isoformat()


def _result(status, checked_at, expires_at=None, source=None, error=None):
    days=None
    if expires_at is not None:
        days=int((expires_at-checked_at).total_seconds()//86400)
    return {
        'status':status,
        'checked_at':checked_at.timestamp(),
        'expires_at':expires_at.timestamp() if expires_at else None,
        'days_remaining':days,
        'source':source,
        'error':error,
    }


def _parse_date(raw):
    raw=raw.strip()
    value=datetime.fromisoformat(raw.replace('Z','+00:00'))
    if value.tzinfo is None:
        value=value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def parse_rdap(payload, checked_at=None):
    checked_at=checked_at or datetime.now(timezone.utc)
    dates=[]
    for event in payload.get('events',[]) if isinstance(payload,dict) else []:
        if not isinstance(event,dict) or event.get('eventAction')!='expiration':
            continue
        raw=event.get('eventDate')
        if not isinstance(raw,str):
            continue
        try:
            dates.append(_parse_date(raw))
        except ValueError:
            continue
    if not dates:
        return _result('not_published',checked_at,source='RDAP')
    return _result('ok',checked_at,max(dates),source='RDAP')


def parse(payload, checked_at=None):
    """Backward-compatible RDAP parser."""
    return parse_rdap(payload, checked_at)


def parse_nz_whois(text, checked_at=None):
    checked_at=checked_at or datetime.now(timezone.utc)
    patterns=(
        r'(?im)^Registry Expiry Date:\s*(\S+)\s*$',
        r'(?im)^Expiry Date:\s*(\S+)\s*$',
        r'(?im)^Expiration Date:\s*(\S+)\s*$',
        r'(?im)^Renewal Date:\s*(\S+)\s*$',
    )
    for pattern in patterns:
        match=re.search(pattern,text)
        if not match:
            continue
        try:
            return _result('ok',checked_at,_parse_date(match.group(1)),source='.nz WHOIS')
        except ValueError:
            return _result('registry_error',checked_at,source='.nz WHOIS',error='Invalid expiry date returned by registry')
    # Updated Date is intentionally not used as expiry.
    return _result('not_published',checked_at,source='.nz WHOIS')


def _rdap(domain, now):
    request=Request(
        'https://rdap.org/domain/'+quote(domain.rstrip('.'),safe=''),
        headers={
            'Accept':'application/rdap+json, application/json',
            'User-Agent':USER_AGENT,
        },
    )
    with urlopen(request,timeout=10) as response:
        body=response.read(MAX_RESPONSE+1)
    if len(body)>MAX_RESPONSE:
        raise ValueError('RDAP response too large')
    return parse_rdap(json.loads(body),now)


def _nz_whois(domain, now):
    chunks=[]
    size=0
    with socket.create_connection((NZ_WHOIS_HOST,43),timeout=10) as connection:
        connection.settimeout(10)
        connection.sendall((domain.rstrip('.')+'\r\n').encode('ascii'))
        while True:
            chunk=connection.recv(65536)
            if not chunk:
                break
            size+=len(chunk)
            if size>MAX_RESPONSE:
                raise ValueError('WHOIS response too large')
            chunks.append(chunk)
    return parse_nz_whois(b''.join(chunks).decode('utf-8',errors='replace'),now)


def lookup(domain):
    now=datetime.now(timezone.utc)
    domain=domain.rstrip('.').lower()
    try:
        return _rdap(domain,now)
    except HTTPError as error:
        if error.code==404 and domain.endswith('.nz'):
            try:
                return _nz_whois(domain,now)
            except (OSError,ValueError) as fallback_error:
                return _result('temporary_error',now,source='.nz WHOIS',error=type(fallback_error).__name__)
        if error.code in (404,410):
            return _result('not_published',now,source='RDAP')
        return _result('temporary_error',now,source='RDAP',error=f'HTTP {error.code}')
    except (URLError,TimeoutError,OSError,json.JSONDecodeError,ValueError) as error:
        if domain.endswith('.nz'):
            try:
                return _nz_whois(domain,now)
            except (OSError,ValueError) as fallback_error:
                return _result('temporary_error',now,source='.nz WHOIS',error=type(fallback_error).__name__)
        return _result('temporary_error',now,source='RDAP',error=type(error).__name__)


def _manual(manual_date,manual_source):
    value=validate_manual_date(manual_date)
    if not value:
        return None
    expiry=datetime.combine(date.fromisoformat(value),datetime.min.time(),tzinfo=timezone.utc)
    now=datetime.now(timezone.utc)
    return {
        'status':'ok',
        'expires_at':expiry.timestamp(),
        'days_remaining':int((expiry-now).total_seconds()//86400),
        'source':(manual_source or '').strip() or 'Manual / registrar portal',
        'manual':True,
    }


def effective(data,manual_date='',manual_source=''):
    manual=_manual(manual_date,manual_source)
    if manual:
        return manual
    if not isinstance(data,dict) or 'domain_expiry' not in data:
        return {'status':'not_checked','source':'Not checked yet'}
    item=data.get('domain_expiry')
    return item if isinstance(item,dict) else {'status':'temporary_error','source':'Automatic lookup'}


def label(data,manual_date='',manual_source=''):
    item=effective(data,manual_date,manual_source)
    status=item.get('status')
    if status=='not_checked':
        return 'Not checked yet'
    if status=='not_published':
        return 'Not published by registry'
    if status in ('temporary_error','registry_error'):
        return 'Temporary lookup error'
    if status!='ok' or item.get('expires_at') is None:
        return 'Unavailable'
    expiry=datetime.fromtimestamp(float(item['expires_at']),timezone.utc)
    days=item.get('days_remaining')
    if item.get('manual'):
        days=int((expiry-datetime.now(timezone.utc)).total_seconds()//86400)
    date_text=expiry.strftime('%d %b %Y')
    suffix=' · Manual' if item.get('manual') else ''
    if days is None:
        return date_text+suffix
    if days<0:
        return f'{date_text} · Expired{suffix}'
    return f'{date_text} · {days} days{suffix}'


def css_class(data,manual_date=''):
    item=effective(data,manual_date,'')
    if item.get('status')!='ok':
        return 'muted'
    days=item.get('days_remaining')
    if item.get('manual') and item.get('expires_at') is not None:
        expiry=datetime.fromtimestamp(float(item['expires_at']),timezone.utc)
        days=int((expiry-datetime.now(timezone.utc)).total_seconds()//86400)
    if days is None:
        return 'muted'
    if days<=30:
        return 'fail'
    if days<=90:
        return 'warn'
    return 'pass'


def source_label(data,manual_date='',manual_source=''):
    item=effective(data,manual_date,manual_source)
    return item.get('source') or 'Unknown'
