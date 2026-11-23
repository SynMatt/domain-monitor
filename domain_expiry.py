"""Resilient domain registration-expiry lookup.

RDAP is primary. The IANA RDAP bootstrap is cached locally and used to contact
registries directly. Authoritative WHOIS is an automatic fallback. Temporary
lookup failures can be merged with a previous confirmed result by app.py so a
known date is not discarded.
"""
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
import fcntl
import ipaddress
import json
import os
from pathlib import Path
import random
import re
import socket
import time
import tldextract
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
import metaname_expiry

USER_AGENT='Domain-Monitor (+https://github.com/SynMatt/domain-monitor)'
MAX_RESPONSE=1024*1024
IANA_RDAP_BOOTSTRAP='https://data.iana.org/rdap/dns.json'
IANA_WHOIS_HOST='whois.iana.org'
NZ_WHOIS_HOST='whois.irs.net.nz'
BOOTSTRAP_MAX_AGE=7*86400
THROTTLE_SECONDS=float(os.environ.get('EXPIRY_SERVICE_DELAY','2.5'))
DATA_DIR=Path(os.environ.get('DATA_DIR','/data'))
BOOTSTRAP_CACHE=DATA_DIR/'rdap-dns.json'
THROTTLE_DIR=DATA_DIR/'expiry-throttle'


# Use tldextract's bundled Public Suffix List snapshot without network fetching.
_PSL=tldextract.TLDExtract(suffix_list_urls=(),include_psl_private_domains=False)


def registrable_domain(hostname):
    """Return the ICANN registrable domain used for registration-expiry lookup."""
    hostname=str(hostname or '').strip().rstrip('.').lower()
    extracted=_PSL(hostname)
    value=extracted.top_domain_under_public_suffix
    if not extracted.suffix or not extracted.domain or not value:
        raise ValueError('Domain has no registrable parent in the Public Suffix List')
    return value


def _expiry_subject(result,requested,registration):
    result=dict(result)
    result['requested_domain']=requested
    result['registration_domain']=registration
    result['subdomain_lookup']=requested!=registration
    return result


def validate_manual_date(value):
    value=(value or '').strip()
    if not value: return ''
    try: parsed=date.fromisoformat(value)
    except ValueError: raise ValueError('Enter the manual expiry date as YYYY-MM-DD.') from None
    if parsed.year<1970 or parsed.year>2200: raise ValueError('Enter a reasonable manual expiry date.')
    return parsed.isoformat()


def _result(status,checked_at,expires_at=None,source=None,error=None,**extra):
    days=None
    if expires_at is not None: days=int((expires_at-checked_at).total_seconds()//86400)
    result={'status':status,'checked_at':checked_at.timestamp(),'expires_at':expires_at.timestamp() if expires_at else None,
            'days_remaining':days,'source':source,'error':error}
    result.update(extra)
    return result


def _parse_date(raw):
    raw=str(raw).strip()
    try: value=datetime.fromisoformat(raw.replace('Z','+00:00'))
    except ValueError:
        value=parsedate_to_datetime(raw)
    if value.tzinfo is None: value=value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def parse_rdap(payload,checked_at=None,source='RDAP'):
    checked_at=checked_at or datetime.now(timezone.utc); dates=[]
    for event in payload.get('events',[]) if isinstance(payload,dict) else []:
        if not isinstance(event,dict) or event.get('eventAction') not in ('expiration','expiry','expire'): continue
        raw=event.get('eventDate')
        if not isinstance(raw,str): continue
        try: dates.append(_parse_date(raw))
        except (ValueError,TypeError): continue
    if not dates: return _result('not_published',checked_at,source=source)
    return _result('ok',checked_at,max(dates),source=source)


def parse(payload,checked_at=None): return parse_rdap(payload,checked_at)


WHOIS_PATTERNS=(
    r'(?im)^Registry Expiry Date:\s*(.+?)\s*$',
    r'(?im)^Registrar Registration Expiration Date:\s*(.+?)\s*$',
    r'(?im)^Expiration Date:\s*(.+?)\s*$',
    r'(?im)^Expiry Date:\s*(.+?)\s*$',
    r'(?im)^paid-till:\s*(.+?)\s*$',
    r'(?im)^Renewal Date:\s*(.+?)\s*$',
)


def parse_whois(text,checked_at=None,source='WHOIS fallback'):
    checked_at=checked_at or datetime.now(timezone.utc)
    for pattern in WHOIS_PATTERNS:
        match=re.search(pattern,text)
        if not match: continue
        raw=match.group(1).strip()
        try: return _result('ok',checked_at,_parse_date(raw),source=source)
        except (ValueError,TypeError): continue
    return _result('not_published',checked_at,source=source)


def parse_nz_whois(text,checked_at=None): return parse_whois(text,checked_at,'.nz WHOIS fallback')


def _https_json(url,timeout=12):
    request=Request(url,headers={'Accept':'application/rdap+json, application/json','User-Agent':USER_AGENT})
    if urlparse(request.full_url).scheme!='https': raise ValueError('RDAP lookups must use HTTPS')
    with urlopen(request,timeout=timeout) as response:  # nosec B310 - HTTPS enforced above
        body=response.read(MAX_RESPONSE+1)
        retry_after=response.headers.get('Retry-After')
    if len(body)>MAX_RESPONSE: raise ValueError('RDAP response too large')
    return json.loads(body),retry_after


def _load_bootstrap():
    DATA_DIR.mkdir(parents=True,exist_ok=True)
    try:
        if BOOTSTRAP_CACHE.exists() and time.time()-BOOTSTRAP_CACHE.stat().st_mtime<BOOTSTRAP_MAX_AGE:
            return json.loads(BOOTSTRAP_CACHE.read_text())
    except (OSError,ValueError,json.JSONDecodeError): pass
    payload,_=_https_json(IANA_RDAP_BOOTSTRAP)
    temporary=BOOTSTRAP_CACHE.with_suffix('.new')
    temporary.write_text(json.dumps(payload,separators=(',',':')))
    os.replace(temporary,BOOTSTRAP_CACHE)
    return payload


def _rdap_base(domain):
    tld=domain.rsplit('.',1)[-1].lower()
    payload=_load_bootstrap()
    for service in payload.get('services',[]):
        if not isinstance(service,list) or len(service)!=2: continue
        tlds,urls=service
        if tld in {str(x).lower() for x in tlds} and urls:
            base=str(urls[0])
            if urlparse(base).scheme!='https': continue
            return base.rstrip('/')+'/'
    return 'https://rdap.org/domain/'


def _throttle(service):
    THROTTLE_DIR.mkdir(parents=True,exist_ok=True)
    host=urlparse(service).hostname or 'unknown'
    key=re.sub(r'[^a-z0-9.-]','_',host.lower())
    marker=THROTTLE_DIR/key
    with marker.open('a+') as handle:
        fcntl.flock(handle,fcntl.LOCK_EX)
        handle.seek(0)
        try: previous=float(handle.read() or 0)
        except ValueError: previous=0
        delay=THROTTLE_SECONDS-(time.time()-previous)
        if delay>0: time.sleep(delay+random.uniform(0,0.35))
        handle.seek(0); handle.truncate(); handle.write(str(time.time())); handle.flush()
        fcntl.flock(handle,fcntl.LOCK_UN)


def _rdap(domain,now):
    base=_rdap_base(domain)
    url=base+('' if base.endswith('/domain/') else 'domain/')+quote(domain.rstrip('.'),safe='')
    _throttle(url)
    try:
        payload,_=_https_json(url)
    except HTTPError as error:
        retry_after=error.headers.get('Retry-After') if error.headers else None
        error.retry_after=retry_after
        raise
    return parse_rdap(payload,now,source='Authoritative RDAP')


def _whois_query(host,query):
    if not re.fullmatch(r'(?i)[a-z0-9.-]{1,253}',host or ''): raise ValueError('Invalid WHOIS host')
    try: ipaddress.ip_address(host); raise ValueError('WHOIS referral must be a hostname')
    except ValueError as exc:
        if str(exc)=='WHOIS referral must be a hostname': raise
    chunks=[]; size=0
    with socket.create_connection((host,43),timeout=10) as connection:
        connection.settimeout(10); connection.sendall((query.rstrip('.')+'\r\n').encode('ascii'))
        while True:
            chunk=connection.recv(65536)
            if not chunk: break
            size+=len(chunk)
            if size>MAX_RESPONSE: raise ValueError('WHOIS response too large')
            chunks.append(chunk)
    return b''.join(chunks).decode('utf-8',errors='replace')


def _authoritative_whois_host(domain):
    tld=domain.rsplit('.',1)[-1]
    text=_whois_query(IANA_WHOIS_HOST,tld)
    match=re.search(r'(?im)^whois:\s*([^\s]+)\s*$',text)
    if not match: return NZ_WHOIS_HOST if tld=='nz' else None
    return match.group(1).strip().lower()


def _whois(domain,now):
    host=_authoritative_whois_host(domain)
    if not host: return _result('not_published',now,source='WHOIS fallback')
    _throttle('whois://'+host)
    return parse_whois(_whois_query(host,domain),now,source=f'WHOIS fallback ({host})')


def _retry_seconds(error):
    raw=getattr(error,'retry_after',None)
    if raw:
        try: return max(60,min(24*3600,int(raw)))
        except (TypeError,ValueError): pass
    return 15*60


def lookup(domain):
    now=datetime.now(timezone.utc)
    requested=str(domain or '').rstrip('.').lower()
    try: registration=registrable_domain(requested)
    except ValueError as error:
        return _result('not_published',now,source='Public Suffix List',error=str(error),requested_domain=requested)
    def done(result): return _expiry_subject(result,requested,registration)
    metaname = metaname_expiry.lookup(registration)
    if metaname is not None:
        return done(metaname)
    try:
        result=_rdap(registration,now)
        if result.get('status')=='ok': return done(result)
        fallback=_whois(registration,now)
        return done(fallback if fallback.get('status')=='ok' else result)
    except HTTPError as error:
        if error.code in (404,410):
            try:
                fallback=_whois(registration,now)
                return done(fallback if fallback.get('status')=='ok' else _result('not_published',now,source='Authoritative RDAP'))
            except (OSError,ValueError,TimeoutError): return done(_result('not_published',now,source='Authoritative RDAP'))
        try:
            fallback=_whois(registration,now)
            if fallback.get('status')=='ok':
                fallback['rdap_error']=f'HTTP {error.code}'
                return done(fallback)
        except (OSError,ValueError,TimeoutError): pass
        return done(_result('temporary_error',now,source='Authoritative RDAP',error=f'HTTP {error.code}',retry_after=_retry_seconds(error)))
    except (URLError,TimeoutError,OSError,json.JSONDecodeError,ValueError) as error:
        try:
            fallback=_whois(registration,now)
            if fallback.get('status')=='ok':
                fallback['rdap_error']=type(error).__name__
                return done(fallback)
        except (OSError,ValueError,TimeoutError): pass
        return done(_result('temporary_error',now,source='Automatic expiry lookup',error=type(error).__name__,retry_after=15*60))


def merge_with_previous(current,previous,now=None):
    """Retain a confirmed date when a fresh automatic lookup fails temporarily."""
    now=time.time() if now is None else now
    if not isinstance(current,dict): return current
    if current.get('status') not in ('temporary_error','registry_error'): return current
    if not isinstance(previous,dict) or previous.get('status')!='ok' or previous.get('expires_at') is None: return current
    merged=dict(previous)
    merged.update({
        'status':'ok', 'last_known':True, 'latest_status':current.get('status'),
        'latest_checked_at':current.get('checked_at'), 'latest_error':current.get('error'),
        'retry_after':current.get('retry_after'), 'retry_at':now+int(current.get('retry_after') or 900),
    })
    merged['days_remaining']=int((float(previous['expires_at'])-now)//86400)
    merged.pop('cached',None)
    return merged


def _manual(manual_date,manual_source):
    value=validate_manual_date(manual_date)
    if not value: return None
    expiry=datetime.combine(date.fromisoformat(value),datetime.min.time(),tzinfo=timezone.utc)
    now=datetime.now(timezone.utc)
    return {'status':'ok','expires_at':expiry.timestamp(),'days_remaining':int((expiry-now).total_seconds()//86400),
            'source':(manual_source or '').strip() or 'Manual / registrar portal','manual':True}


def effective(data,manual_date='',manual_source=''):
    manual=_manual(manual_date,manual_source)
    if manual: return manual
    if not isinstance(data,dict) or 'domain_expiry' not in data: return {'status':'not_checked','source':'Not checked yet'}
    item=data.get('domain_expiry')
    return item if isinstance(item,dict) else {'status':'temporary_error','source':'Automatic lookup'}


def label(data,manual_date='',manual_source=''):
    item=effective(data,manual_date,manual_source); status=item.get('status')
    if status=='not_checked': return 'Not checked yet'
    if status=='not_published': return 'Not published by registry'
    if status in ('temporary_error','registry_error'): return 'Temporary lookup error'
    if status!='ok' or item.get('expires_at') is None: return 'Unavailable'
    expiry=datetime.fromtimestamp(float(item['expires_at']),timezone.utc); days=item.get('days_remaining')
    if item.get('manual'): days=int((expiry-datetime.now(timezone.utc)).total_seconds()//86400)
    date_text=expiry.strftime('%d %b %Y'); suffix=' · Manual' if item.get('manual') else ' · Last known' if item.get('last_known') else ''
    if days is None: return date_text+suffix
    if days<0: return f'{date_text} · Expired{suffix}'
    return f'{date_text} · {days} days{suffix}'


def css_class(data,manual_date=''):
    item=effective(data,manual_date,'')
    if item.get('status')!='ok': return 'muted'
    days=item.get('days_remaining')
    if item.get('manual') and item.get('expires_at') is not None:
        expiry=datetime.fromtimestamp(float(item['expires_at']),timezone.utc); days=int((expiry-datetime.now(timezone.utc)).total_seconds()//86400)
    if days is None: return 'muted'
    if days<=30: return 'fail'
    if days<=90: return 'warn'
    return 'pass'


def source_label(data,manual_date='',manual_source=''):
    item=effective(data,manual_date,manual_source)
    source=item.get('source') or 'Unknown'
    if item.get('last_known'):
        error=item.get('latest_error') or 'temporary lookup failure'
        source=f'{source}; last known, latest lookup: {error}'
    registration=item.get('registration_domain')
    requested=item.get('requested_domain')
    if registration and requested and registration!=requested:
        return f'{source} · Registration domain: {registration}'
    return source
