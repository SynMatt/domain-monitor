"""Cached domain registration expiry via RDAP; separate from email health."""
from datetime import datetime, timezone
import json
from urllib.parse import quote
from urllib.request import Request, urlopen

USER_AGENT='Domain-Monitor/0.13.0 (+https://github.com/SynMatt/domain-monitor)'
MAX_RESPONSE=1024*1024

def parse(payload, checked_at=None):
    checked_at=checked_at or datetime.now(timezone.utc)
    dates=[]
    for event in payload.get('events',[]) if isinstance(payload,dict) else []:
        if not isinstance(event,dict) or event.get('eventAction')!='expiration':
            continue
        raw=event.get('eventDate')
        if not isinstance(raw,str):
            continue
        try:
            value=datetime.fromisoformat(raw.replace('Z','+00:00'))
            if value.tzinfo is None:
                value=value.replace(tzinfo=timezone.utc)
            dates.append(value.astimezone(timezone.utc))
        except ValueError:
            continue
    if not dates:
        return {'status':'unavailable','checked_at':checked_at.timestamp(),'expires_at':None,'days_remaining':None}
    expires=max(dates)
    days=int((expires-checked_at).total_seconds()//86400)
    return {'status':'ok','checked_at':checked_at.timestamp(),'expires_at':expires.timestamp(),'days_remaining':days}

def lookup(domain):
    now=datetime.now(timezone.utc)
    try:
        request=Request('https://rdap.org/domain/'+quote(domain.rstrip('.'),safe=''),headers={'Accept':'application/rdap+json, application/json','User-Agent':USER_AGENT})
        with urlopen(request,timeout=10) as response:
            body=response.read(MAX_RESPONSE+1)
        if len(body)>MAX_RESPONSE:
            raise ValueError('RDAP response too large')
        return parse(json.loads(body),now)
    except Exception:
        return {'status':'unavailable','checked_at':now.timestamp(),'expires_at':None,'days_remaining':None}

def label(data):
    if not isinstance(data,dict) or 'domain_expiry' not in data:
        return 'Not checked yet'
    item=data.get('domain_expiry')
    if not isinstance(item,dict) or item.get('status')!='ok' or item.get('expires_at') is None:
        return 'Unavailable'
    expiry=datetime.fromtimestamp(float(item['expires_at']),timezone.utc)
    days=item.get('days_remaining')
    date=expiry.strftime('%d %b %Y')
    if days is None:
        return date
    if days<0:
        return f'{date} · Expired'
    return f'{date} · {days} days'

def css_class(data):
    item=data.get('domain_expiry') if isinstance(data,dict) else None
    if not isinstance(item,dict) or item.get('status')!='ok':
        return 'muted'
    days=item.get('days_remaining')
    if days is None:
        return 'muted'
    if days<=30:
        return 'fail'
    if days<=90:
        return 'warn'
    return 'pass'
