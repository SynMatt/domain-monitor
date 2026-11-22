import os,sys,time,json,re,base64,sqlite3,secrets,subprocess,logging  # nosec B404 - fixed argument lists only, never a shell
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
TIMEZONES={
    'Pacific/Auckland':'Auckland (New Zealand)',
    'Pacific/Chatham':'Chatham Islands (New Zealand)',
    'Australia/Sydney':'Sydney (Australia)',
    'Australia/Melbourne':'Melbourne (Australia)',
    'Australia/Brisbane':'Brisbane (Australia)',
    'Australia/Perth':'Perth (Australia)',
    'Asia/Singapore':'Singapore',
    'Asia/Tokyo':'Tokyo (Japan)',
    'Asia/Kolkata':'India',
    'Europe/London':'London (United Kingdom)',
    'Europe/Paris':'Central Europe',
    'America/New_York':'New York (United States)',
    'America/Chicago':'Chicago (United States)',
    'America/Denver':'Denver (United States)',
    'America/Los_Angeles':'Los Angeles (United States)',
    'UTC':'UTC',
}
DEFAULT_TIMEZONE='Pacific/Auckland'

def validate_timezone(value):
    if value not in TIMEZONES:
        raise ValueError('Select a supported timezone.')
    return value

def get_timezone(c):
    row=c.execute("SELECT value FROM state WHERE key='timezone'").fetchone()
    value=row[0] if row else DEFAULT_TIMEZONE
    return value if value in TIMEZONES else DEFAULT_TIMEZONE

def selected_zone(c=None):
    if c is not None:
        return ZoneInfo(get_timezone(c))
    with db() as connection:
        return ZoneInfo(get_timezone(connection))
from flask import Flask,request,session,redirect,render_template,abort,flash
from werkzeug.security import check_password_hash
DATA=os.environ.get('DATA_DIR','/data')
DB=DATA+'/monitor.sqlite3'
logging.basicConfig(level=logging.INFO)
APP_VERSION='1.5.1'
def check_workers():
    try: value=int(os.environ.get('CHECK_WORKERS','4'))
    except ValueError: value=4
    return min(8,max(1,value))
@contextmanager
def db():
    c=sqlite3.connect(DB,timeout=30); c.row_factory=sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    try:
        yield c
        c.commit()
    except Exception:
        c.rollback(); raise
    finally: c.close()

def validate_time(value):
    if not re.fullmatch(r'(?:[01][0-9]|2[0-3]):[0-5][0-9]',value):
        raise ValueError('Enter a daily check time in HH:MM format.')
    return value

def next_run(now,clock,zone=None):
    validate_time(clock)
    zone=zone or selected_zone()
    hour,minute=map(int,clock.split(':'))
    today=datetime.fromtimestamp(now,zone).date()
    for offset in range(4):
        day=today+timedelta(days=offset)
        wall=datetime(day.year,day.month,day.day,hour,minute)
        # A nonexistent spring-forward time moves to the first valid minute.
        # Ambiguous autumn times use the first occurrence, once per local day.
        for adjustment in range(181):
            candidate=(wall+timedelta(minutes=adjustment)).replace(tzinfo=zone,fold=0)
            epoch=candidate.timestamp()
            if datetime.fromtimestamp(epoch,zone).replace(tzinfo=None)==candidate.replace(tzinfo=None):
                if epoch>now: return epoch
                break
    raise ValueError('Could not determine next daily run.')

def get_clock(c):
    return c.execute("SELECT value FROM state WHERE key='daily_time'").fetchone()[0]

def init():
    os.makedirs(DATA,exist_ok=True)
    with db() as c:
        c.execute('PRAGMA journal_mode=WAL')
        c.executescript("""
CREATE TABLE IF NOT EXISTS domains(id INTEGER PRIMARY KEY,domain TEXT UNIQUE NOT NULL,label TEXT NOT NULL,selectors TEXT NOT NULL,policy TEXT NOT NULL,revision INTEGER NOT NULL DEFAULT 1,due REAL NOT NULL DEFAULT 0,checked REAL,result TEXT);
CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY,domain_id INTEGER NOT NULL REFERENCES domains(id) ON DELETE CASCADE,checked REAL NOT NULL,result TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS history_domain ON history(domain_id,id);
CREATE TABLE IF NOT EXISTS state(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS attempts(at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS check_batches(id INTEGER PRIMARY KEY,status TEXT NOT NULL CHECK(status IN ('active','complete','stalled')),total INTEGER NOT NULL,created REAL NOT NULL,updated REAL NOT NULL,finished REAL);
CREATE TABLE IF NOT EXISTS check_batch_items(batch_id INTEGER NOT NULL REFERENCES check_batches(id) ON DELETE CASCADE,domain_id INTEGER NOT NULL REFERENCES domains(id) ON DELETE CASCADE,status TEXT NOT NULL CHECK(status IN ('queued','running','complete','failed')),started REAL,finished REAL,error TEXT NOT NULL DEFAULT '',PRIMARY KEY(batch_id,domain_id));
CREATE INDEX IF NOT EXISTS check_batch_items_status ON check_batch_items(batch_id,status);
""")
        columns={r[1] for r in c.execute('PRAGMA table_info(domains)')}
        if 'manual_pending' not in columns:
            c.execute('ALTER TABLE domains ADD COLUMN manual_pending INTEGER NOT NULL DEFAULT 0')
        if 'manual_expiry' not in columns:
            c.execute("ALTER TABLE domains ADD COLUMN manual_expiry TEXT NOT NULL DEFAULT ''")
        if 'manual_expiry_source' not in columns:
            c.execute("ALTER TABLE domains ADD COLUMN manual_expiry_source TEXT NOT NULL DEFAULT ''")
        if 'approved_spf' not in columns:
            c.execute("ALTER TABLE domains ADD COLUMN approved_spf TEXT NOT NULL DEFAULT ''")
        if 'approved_dmarc' not in columns:
            c.execute("ALTER TABLE domains ADD COLUMN approved_dmarc TEXT NOT NULL DEFAULT ''")
        if 'approval_note' not in columns:
            c.execute("ALTER TABLE domains ADD COLUMN approval_note TEXT NOT NULL DEFAULT ''")
        if 'dkim_rotation_started' not in columns:
            c.execute("ALTER TABLE domains ADD COLUMN dkim_rotation_started TEXT NOT NULL DEFAULT ''")
        batch_columns={r[1] for r in c.execute('PRAGMA table_info(check_batches)')}
        if 'cancelled' not in batch_columns:
            c.execute('ALTER TABLE check_batches ADD COLUMN cancelled INTEGER NOT NULL DEFAULT 0')
        item_columns={r[1] for r in c.execute('PRAGMA table_info(check_batch_items)')}
        if 'was_pending' not in item_columns:
            c.execute('ALTER TABLE check_batch_items ADD COLUMN was_pending INTEGER NOT NULL DEFAULT 0')
        history_columns={r[1] for r in c.execute('PRAGMA table_info(history)')}
        if 'first_checked' not in history_columns:
            c.execute('ALTER TABLE history ADD COLUMN first_checked REAL')
        if 'checks' not in history_columns:
            c.execute('ALTER TABLE history ADD COLUMN checks INTEGER NOT NULL DEFAULT 1')
        compacted=compact_history(c)
        c.execute("INSERT OR IGNORE INTO state VALUES('daily_time','03:00')")
        c.execute("INSERT OR IGNORE INTO state VALUES('timezone',?)",(DEFAULT_TIMEZONE,))
        if not c.execute("SELECT 1 FROM state WHERE key='fixed_schedule_v1'").fetchone():
            due=next_run(time.time(),get_clock(c),selected_zone(c))
            c.execute('UPDATE domains SET due=?,manual_pending=CASE WHEN checked IS NULL THEN 1 ELSE 0 END',(due,))
            c.execute("INSERT INTO state VALUES('fixed_schedule_v1','1')")
    if compacted: vacuum_database()
HISTORY_COMPACT_KEY='history_compact_v1'
def slim_result(data):
    """History copy without bulky diagnostics. Statuses, messages, warnings and records are kept."""
    if not isinstance(data,dict): return data
    out=dict(data)
    for kind in ('spf','dmarc'):
        item=out.get(kind)
        if isinstance(item,dict) and isinstance(item.get('raw'),dict):
            item=dict(item)
            item['raw']={k:v for k,v in item['raw'].items() if k!='parsed'}
            out[kind]=item
    evidence=out.get('dns_evidence')
    if isinstance(evidence,dict) and isinstance(evidence.get('queries'),dict):
        queries={}
        for kind,item in evidence['queries'].items():
            if kind=='dkim' or not isinstance(item,dict): continue
            queries[kind]={k:item[k] for k in ('consensus','recursive_matches_authoritative','authoritative_records') if k in item}
        out['dns_evidence']={'status':evidence.get('status'),'warnings':evidence.get('warnings',[]),'queries':queries,'compact':True}
    return out
def history_fingerprint(data):
    """Compare results while ignoring timing, trigger and cache metadata."""
    if not isinstance(data,dict): return None
    out=slim_result(data); out.pop('trigger',None)
    expiry=out.get('domain_expiry')
    if isinstance(expiry,dict):
        out['domain_expiry']={k:expiry.get(k) for k in ('status','expires_at','source','manual')}
    return json.dumps(out,sort_keys=True,separators=(',',':'),default=str)
def record_history(c,domain_id,now,data,encoded):
    """Save a check. An unchanged result extends the previous entry instead of adding a row."""
    last=c.execute('SELECT id,result FROM history WHERE domain_id=? ORDER BY id DESC LIMIT 1',(domain_id,)).fetchone()
    if last:
        try: previous=json.loads(last['result'])
        except (TypeError,ValueError): previous=None
        if isinstance(previous,dict) and history_fingerprint(previous)==history_fingerprint(data):
            c.execute('UPDATE history SET checked=?,result=?,checks=checks+1 WHERE id=?',(now,encoded,last['id']))
            return False
        if isinstance(previous,dict):
            c.execute('UPDATE history SET result=? WHERE id=?',(json.dumps(slim_result(previous),separators=(',',':')),last['id']))
    c.execute('INSERT INTO history(domain_id,checked,first_checked,result) VALUES(?,?,?,?)',(domain_id,now,now,encoded))
    return True
def compact_history(c):
    """One-time upgrade: keep full diagnostics only on each domain's newest history entry."""
    if c.execute('SELECT 1 FROM state WHERE key=?',(HISTORY_COMPACT_KEY,)).fetchone(): return 0
    newest={r[0] for r in c.execute('SELECT MAX(id) FROM history GROUP BY domain_id')}
    changed=0
    for (ident,) in c.execute('SELECT id FROM history ORDER BY id').fetchall():
        if ident in newest: continue
        text=c.execute('SELECT result FROM history WHERE id=?',(ident,)).fetchone()[0]
        try: compact=json.dumps(slim_result(json.loads(text)),separators=(',',':'))
        except (TypeError,ValueError): continue
        if len(compact)<len(text):
            c.execute('UPDATE history SET result=? WHERE id=?',(compact,ident)); changed+=1
    c.execute('UPDATE history SET first_checked=checked WHERE first_checked IS NULL')
    c.execute('INSERT OR REPLACE INTO state VALUES(?,?)',(HISTORY_COMPACT_KEY,'1'))
    if changed: logging.info('Compacted %s history entries.',changed)
    return changed
def vacuum_database():
    """Reclaim space after compaction. Skipped safely if the database is busy."""
    try:
        c=sqlite3.connect(DB,timeout=30,isolation_level=None)
        try:
            c.execute('VACUUM'); c.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        finally: c.close()
        logging.info('Database vacuumed after history compaction.')
    except sqlite3.Error as e:
        logging.warning('Database VACUUM skipped: %s',e)

DKIM_ROTATION_DAYS=4

def validate_dkim_rotation_date(value,now=None,zone=None):
    value=str(value or '').strip()
    if not value: return ''
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value): raise ValueError('Enter a rotation date in YYYY-MM-DD format.')
    try: day=datetime.strptime(value,'%Y-%m-%d').date()
    except ValueError: raise ValueError('Enter a valid DKIM rotation date.')
    zone=zone or selected_zone()
    now=time.time() if now is None else now
    if day>datetime.fromtimestamp(now,zone).date(): raise ValueError('DKIM rotation cannot start on a future date.')
    return day.isoformat()

def dkim_rotation_info(value,now=None,zone=None):
    if not value: return None
    zone=zone or selected_zone()
    now=time.time() if now is None else now
    try:
        start=datetime.strptime(str(value),'%Y-%m-%d').date()
        elapsed=(datetime.fromtimestamp(now,zone).date()-start).days
        end=start+timedelta(days=DKIM_ROTATION_DAYS)
    except (ValueError,TypeError,OverflowError): return None
    if elapsed<0: return None
    active=elapsed<DKIM_ROTATION_DAYS
    return dict(started=start.isoformat(),ends=end.isoformat(),active=active,day=min(elapsed+1,4),
        message=f'DKIM rotation: Day {elapsed+1} of 4' if active else 'DKIM rotation window ended - review the latest result.')

def domain_name(s):
    s=s.strip().rstrip('.').lower()
    try: s=s.encode('idna').decode('ascii')
    except UnicodeError: raise ValueError('Invalid domain name.')
    if len(s)>253 or len(s.split('.'))<2 or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?',x) for x in s.split('.')):
        raise ValueError('Enter a domain only, not a URL or email address.')
    import ipaddress
    try: ipaddress.ip_address(s)
    except ValueError: return s
    raise ValueError('Enter a domain, not an IP address.')
def selectors(s):
    a=list(dict.fromkeys(x.lower() for x in re.split(r'[,\s]+',s.strip()) if x))
    if len(a)>10: raise ValueError('Maximum 10 selectors per domain.')
    for x in a:
        if len(x)>100 or any(not re.fullmatch(r'[a-z0-9_](?:[a-z0-9_-]{0,61}[a-z0-9_])?',p) for p in x.split('.')):
            raise ValueError('Enter selector names only, e.g. selector1, selector2.')
    return ','.join(a)
def res(status,message,**kw): return dict(status=status,message=message,**kw)
def worst(a):
    states=[x['status'] for x in a]
    return next((x for x in ('fail','unknown','warn') if x in states),'pass')
def temporary(s):
    return any(x in str(s).lower() for x in ('timeout','timed out','lifetime','servfail','no nameservers','unreachable','refused','temporary','resolution failed','dns operation'))

_SPF_A_WARNING = re.compile(
    r'^Error when processing (?P<owner>[^:]+): '
    r'An? a mechanism points to (?P<target>[^,]+), but that domain/subdomain '
    r'does not have any A/AAAA records\.$',
    re.IGNORECASE,
)
_SPF_SIZE_WARNING = re.compile(
    r'^The SPF record for (?P<owner>\S+) is (?P<size>\d+) bytes\.',
    re.IGNORECASE,
)

def _normalise_host(value):
    return str(value or '').lower().rstrip('.')

def _included_spf_hosts(raw):
    hosts=set()
    def walk(parsed):
        if not isinstance(parsed,dict): return
        for item in parsed.get('mechanisms',[]) or []:
            if not isinstance(item,dict): continue
            if item.get('mechanism')=='include':
                hosts.add(_normalise_host(item.get('value')))
            walk(item.get('parsed'))
    walk((raw or {}).get('parsed',{}))
    return hosts

def friendly_spf_warning(domain,warning,raw=None):
    """Add ownership, impact and action without mislabelling direct-domain SPF."""
    warning=str(warning)
    domain=_normalise_host(domain)
    includes=_included_spf_hosts(raw or {})
    match=_SPF_A_WARNING.fullmatch(warning)
    if match:
        owner=_normalise_host(match.group('owner'))
        target=_normalise_host(match.group('target'))
        external=owner != domain and owner in includes
        if external:
            return (f'External provider: {owner} uses an a mechanism but has no '
                    'A/AAAA records. The included SPF provider must correct this record.')
        return (f'Action recommended: {target} uses an a mechanism but has no A/AAAA '
                'records. Remove the ineffective mechanism or publish the intended address record.')
    match=_SPF_SIZE_WARNING.match(warning)
    if match:
        owner=_normalise_host(match.group('owner'))
        size=match.group('size')
        if owner != domain and owner in includes:
            return (f'External provider: {owner} publishes a {size}-byte SPF response, above '
                    'the approximately 450-byte recommendation. The included SPF provider owns this record.')
    return warning

def friendly_dmarc_warning(warning):
    warning=str(warning)
    obsolete=re.fullmatch(r'Support for the (pct|ri|rf) tag was removed in RFC 9989',warning)
    if obsolete:
        tag=obsolete.group(1)
        return (f'Recommendation: The {tag} tag is obsolete under RFC 9989. '
                'Remove it during the next DMARC record update; DMARC can still operate meanwhile.')
    if warning.startswith('An sp tag value of none makes DMARC unenforced'):
        return ('Action recommended: DMARC is not enforced for subdomains because sp=none. '
                'Review whether subdomains send mail, then change or remove sp=none if they should inherit the main policy.')
    if warning=='rua tag (destination for aggregate reports) not found.':
        return ('Recommendation: No aggregate-reporting address (rua) is configured. '
                'DMARC enforcement can still work, but aggregate visibility is unavailable.')
    if warning=='Some DMARC reporters might not send to more than two rua URIs.':
        return ('Recommendation: More than two rua destinations are configured. '
                'Some DMARC reporters may skip additional destinations.')
    return warning

APPROVAL_KINDS=('spf','dmarc')
MAX_APPROVED_FRAGMENTS=20
MAX_APPROVED_TEXT=5000

def normalise_record_fragment(value):
    """Case/whitespace-insensitive comparison while preserving punctuation and order."""
    return re.sub(r'\s+','',str(value or '')).lower()

def approved_fragments(text):
    text=str(text or '')
    if len(text)>MAX_APPROVED_TEXT: raise ValueError('Approved exception text is too long.')
    items=[]
    for line in text.splitlines():
        line=line.strip()
        if not line: continue
        if len(line)>1000: raise ValueError('Each approved record section must be 1,000 characters or fewer.')
        if line not in items: items.append(line)
    if len(items)>MAX_APPROVED_FRAGMENTS: raise ValueError('Maximum 20 approved record sections for SPF or DMARC.')
    return items

def warning_detail(kind,warning,raw=None):
    """Explain a warning and describe which existing record section may approve it."""
    warning=str(warning); raw=raw if isinstance(raw,dict) else {}; record=str(raw.get('record') or '')
    detail={'warning':warning,'id':'','title':'Configuration warning','problem':warning,
            'evidence':'See Technical details.','action':'Review the DNS record.','approvable':False,'suggested_fragment':''}
    if kind=='spf' and not warning.startswith('External provider:') and 'uses an a mechanism but has no A/AAAA records' in warning:
        token=next((x for x in record.split() if x.lower() in ('a','+a')), '+a')
        detail.update(id='spf.a_without_address',title='Ineffective SPF a mechanism',
            problem='The SPF record contains an a mechanism, but its target has no A or AAAA address. The mechanism cannot authorize a sender.',
            evidence='The address lookup returned no A/AAAA record. MX authorization is separate and is not affected.',
            action='Remove the a mechanism if it is not needed, or publish the intended A/AAAA address.',
            approvable=True,suggested_fragment=token)
    elif kind=='spf' and warning.startswith('External provider:') and 'A/AAAA records' in warning:
        owner=warning.split(':',1)[1].split(' uses ',1)[0].strip().lower()
        wanted='include:'+owner
        include=next((x for x in record.split() if x.lower()==wanted), '')
        detail.update(id='spf.external_a_without_address',title='Included SPF provider has an ineffective a mechanism',
            problem='A record included by this SPF policy contains an a mechanism with no usable address.',
            evidence='The issue is inside the included provider record, not the monitored domain record itself.',
            action='Ask the included provider to correct the record, or approve the include while accepting the provider-owned warning.',
            approvable=bool(include),suggested_fragment=include)
    elif kind=='spf' and warning.startswith('External provider:') and 'SPF response' in warning:
        include=next((x for x in record.split() if x.lower().startswith('include:')), '')
        detail.update(id='spf.external_record_size',title='Large included SPF response',
            problem='An included provider publishes a larger-than-recommended SPF response.',
            evidence='The warning belongs to the included provider record.',
            action='Ask the provider to reduce the record, or approve the specific include for this domain.',
            approvable=bool(include),suggested_fragment=include)
    elif kind=='dmarc' and warning.startswith('Recommendation: More than two rua destinations'):
        tags=[]
        for part in record.split(';'):
            part=part.strip()
            if part.lower().startswith(('rua=','ruf=')): tags.append(part)
        fragment='; '.join(tags)+(';' if tags else '')
        detail.update(id='dmarc.too_many_rua',title='More than two DMARC aggregate-report destinations',
            problem='The rua tag contains more than two destinations. Some receivers may ignore destinations beyond the first two.',
            evidence='The current DMARC record publishes multiple rua reporting addresses.',
            action='Reduce the rua destinations, or approve this exact rua/ruf configuration if the reporting layout is intentional.',
            approvable=bool(fragment),suggested_fragment=fragment)
    elif kind=='dmarc' and 'tag is obsolete under RFC 9989' in warning:
        match=re.search(r'The ([a-z]+) tag',warning); tag=match.group(1) if match else ''
        fragment=next((x.strip() for x in record.split(';') if x.strip().lower().startswith(tag+'=')), '')
        detail.update(id='dmarc.obsolete_'+tag,title='Obsolete DMARC tag',problem=warning,
            evidence=f'The current record contains the {tag} tag.',action='Remove the obsolete tag during DNS maintenance, or approve this exact tag temporarily.',
            approvable=bool(fragment),suggested_fragment=fragment+(';' if fragment else ''))
    elif kind=='dmarc' and warning.startswith('Action recommended: DMARC is not enforced for subdomains because sp=none'):
        fragment=next((x.strip() for x in record.split(';') if x.strip().lower()=='sp=none'), '')
        detail.update(id='dmarc.sp_none',title='DMARC is not enforced for subdomains',problem=warning,
            evidence='The current DMARC record contains sp=none.',action='Review subdomain mail use, then change/remove sp=none or approve this exact setting.',
            approvable=bool(fragment),suggested_fragment=fragment+(';' if fragment else ''))
    return detail

def _record_tag(record,name):
    """Return the whole current DMARC tag, normalised, e.g. 'rua=mailto:a,mailto:b'."""
    for part in str(record or '').split(';'):
        part=part.strip()
        if part.lower().startswith(name+'='): return normalise_record_fragment(part)
    return ''

def fragment_matches_warning(kind,fragment,detail,raw):
    """An approval matches only the exact record section the warning is about.
    Any change to that section (an added address, a different include) stops the match."""
    if kind not in APPROVAL_KINDS or not detail.get('approvable'): return False
    raw_record=(raw or {}).get('record')
    record=normalise_record_fragment(raw_record)
    wanted=normalise_record_fragment(fragment)
    if not wanted or wanted not in record: return False
    ident=detail.get('id','')
    if ident=='spf.a_without_address': return wanted.rstrip(';') in ('a','+a')
    if ident.startswith('spf.external_'):
        expected=normalise_record_fragment(detail.get('suggested_fragment'))
        return bool(expected) and wanted.rstrip(';')==expected
    if ident=='dmarc.too_many_rua':
        tag=_record_tag(raw_record,'rua'); return bool(tag) and tag in wanted
    if ident.startswith('dmarc.obsolete_'):
        tag=_record_tag(raw_record,ident.rsplit('_',1)[-1]); return bool(tag) and tag in wanted
    if ident=='dmarc.sp_none':
        return _record_tag(raw_record,'sp')=='sp=none' and 'sp=none' in wanted
    return False

def apply_approved_exceptions(kind,item,approval_text,note=''):
    """Only warning results can become pass. Fail/unknown results are never changed."""
    if kind not in APPROVAL_KINDS or not isinstance(item,dict) or item.get('status')!='warn': return item
    raw=item.get('raw') if isinstance(item.get('raw'),dict) else {}
    fragments=approved_fragments(approval_text)
    approved=[]; remaining=[]; details=[]
    for warning in item.get('warnings') or []:
        detail=warning_detail(kind,warning,raw); match=''
        for fragment in fragments:
            if fragment_matches_warning(kind,fragment,detail,raw): match=fragment; break
        detail=dict(detail,approved=bool(match),approved_fragment=match)
        details.append(detail)
        if match: approved.append(dict(warning=str(warning),finding_id=detail.get('id'),fragment=match))
        else: remaining.append(str(warning))
    out=dict(item,warning_details=details,approved_warnings=approved,warnings=remaining)
    if approved:
        out['approval_note']=str(note or '').strip()
        out['technical_status']='warn'
        if not remaining:
            out['status']='pass'
            out['manual_approval_message']='Manually approved exception: All current warnings match approved sections of this DNS record. The original warnings remain visible for audit purposes but do not affect the effective status.'
        else:
            out['manual_approval_message']='Manually approved exception: Some current warnings match approved sections of this DNS record. Unapproved warnings still affect the effective status.'
    return out

def record_check(kind,domain,policy):
    from checkdmarc.spf import check_spf
    from checkdmarc.dmarc import check_dmarc
    try:
        raw=(check_spf if kind=='spf' else check_dmarc)(domain,timeout=3.0,retries=1)
        raw=json.loads(json.dumps(raw,default=str)); warnings=list(raw.get('warnings',[]))
        if kind=='spf':
            warnings=[friendly_spf_warning(domain,warning,raw) for warning in warnings]
        else:
            warnings=[friendly_dmarc_warning(warning) for warning in warnings]
        if raw.get('valid') is not True:
            error=str(raw.get('error','No valid result returned.'))
            if temporary(error):
                return res('unknown','Temporary lookup issue: '+error,raw=raw)
            return res('fail',error,raw=raw)
        if kind=='spf':
            if raw.get('parsed',{}).get('all') in ('pass','neutral'):
                return res('fail','SPF allows all senders or has no restrictive fallback.',raw=raw)
            if '%' in str(raw.get('record','')):
                warnings.append('Recommendation: SPF macros require runtime sender context; static validation is incomplete.')
            message='Valid SPF; DNS lookups: '+str(raw.get('dns_lookups','?'))
        else:
            tags=raw.get('tags',{}); actual=tags.get('p',{}).get('value','none')
            if raw.get('location') and raw['location'].rstrip('.').lower()!=domain:
                actual=tags.get('sp',{}).get('value',actual)
            rank={'none':0,'quarantine':1,'reject':2}
            if actual not in rank: return res('unknown','Unrecognised effective policy.',raw=raw)
            if rank[actual]<rank[policy]: return res('fail',f'Effective policy {actual}; required minimum {policy}.',raw=raw)
            message=f'Valid DMARC; effective policy {actual}; required {policy}.'
        return res('warn' if warnings else 'pass',message,warnings=warnings,raw=raw)
    except Exception as e:
        message=f'{type(e).__name__}: {e}'
        if temporary(message): return res('unknown','Temporary lookup issue: '+message)
        return res('unknown','Checker error: '+message)

def key_check(text):
    from cryptography.hazmat.primitives.serialization import load_der_public_key
    from cryptography.hazmat.primitives.asymmetric import rsa
    tags={}; first=None
    for part in text.split(';'):
        if not part.strip(): continue
        if '=' not in part: raise ValueError('Malformed DKIM tag.')
        k,v=part.split('=',1); k=k.strip(); v=v.strip()
        if not re.fullmatch('[a-z][a-z0-9_]*',k) or k in tags: raise ValueError('Invalid or duplicate DKIM tag.')
        if first is None: first=k
        tags[k]=v
    if 'v' in tags and (tags['v']!='DKIM1' or first!='v'): raise ValueError('DKIM version must be DKIM1 and first when present.')
    if 'p' not in tags: raise ValueError('Missing public key p tag.')
    payload=re.sub(r'\s+','',tags['p'])
    if not payload: raise ValueError('DKIM key is revoked: empty p tag.')
    try: key=base64.b64decode(payload,validate=True)
    except Exception: raise ValueError('Invalid base64 public key.')
    warnings=[]; kind=tags.get('k','rsa')
    if kind=='rsa':
        try: pub=load_der_public_key(key)
        except Exception: raise ValueError('Invalid DER-encoded public key.')
        if not isinstance(pub,rsa.RSAPublicKey): raise ValueError('Public key is not RSA.')
        if pub.key_size<1024: raise ValueError('RSA key shorter than 1024 bits.')
        if pub.key_size<2048:
            warnings.append('Recommendation: Rotate this selector to a 2048-bit RSA key when practical. Existing DKIM signing may still work.')
            message=f'Recommendation: RSA {pub.key_size}-bit key; rotate to 2048-bit when practical.'
        else:
            message=f'RSA {pub.key_size}-bit key'
    elif kind=='ed25519':
        if len(key)!=32: raise ValueError('Ed25519 key must contain 32 bytes.')
        message='Ed25519 key'
    else: raise ValueError('Unsupported DKIM key algorithm: '+kind)
    if 'h' in tags and 'sha256' not in tags['h'].split(':'): raise ValueError('Key does not allow SHA-256.')
    if 's' in tags and not {'*','email'}.intersection(tags['s'].split(':')): raise ValueError('Key is not authorised for email.')
    if 'y' in tags.get('t','').split(':'): warnings.append('DKIM key is marked as testing.')
    if 'g' in tags: warnings.append('Legacy g tag: manually review sender restrictions.')
    return res('warn' if warnings else 'pass',message,warnings=warnings,record=text)
def dkim_check(domain,selected):
    import dns.resolver
    if not selected: return res('unknown','No DKIM selectors configured. Automatic selector discovery is not reliable.')
    results=[]
    for s in selected.split(','):
        name=f'{s}._domainkey.{domain}.'
        try:
            r=dns.resolver.Resolver(); r.timeout=3; r.lifetime=8
            answer=r.resolve(name,'TXT',search=False)
            records=[b''.join(x.strings).decode('ascii') for x in answer]
            if len(records)!=1: raise ValueError('Expected exactly one DKIM TXT record.')
            item=key_check(records[0]); item['canonical_name']=str(answer.canonical_name)
        except (dns.resolver.NXDOMAIN,dns.resolver.NoAnswer): item=res('fail',f'Action required: DKIM record not found for {s}. Confirm this selector is currently used for signing; remove it from Domain Monitor if obsolete, otherwise publish or repair its DNS record.')
        except (ValueError,UnicodeError) as e: item=res('fail',str(e))
        except Exception as e: item=res('unknown','DNS/checker error: '+str(e))
        results.append(dict(selector=s,query=name,**item))
    return res(worst(results),'All configured selectors must pass.',selectors=results)
from dns_host import lookup as dns_host_lookup, label as dns_host_label
import domain_expiry
import dns_evidence

def isolated(kind,row):
    try:
        p=subprocess.run([sys.executable,__file__,'check',kind,row['domain'],row['selectors'],row['policy']],capture_output=True,text=True,timeout=120)  # nosec B603 - fixed argument list, no shell
        if p.returncode:
            logging.error('Checker failed: %s',p.stderr[-2000:]); return res('unknown','Checker process failed; see worker logs.')
        return json.loads(p.stdout)
    except subprocess.TimeoutExpired: return res('unknown','Check exceeded 120-second time limit.')
    except Exception as e: return res('unknown','Checker error: '+str(e))
DOMAIN_CHECK_TIMEOUT=240
def collect_domain(name,selected,policy,include_expiry=True):
    """Run every check for one domain in a single process.
    Each step is isolated so one failure cannot discard the others."""
    def safe(label,fn,*args):
        try: return fn(*args)
        except Exception as e: return res('unknown',f'{label} checker error: {type(e).__name__}: {e}')
    data={}
    data['spf']=safe('SPF',record_check,'spf',name,policy)
    data['dkim']=safe('DKIM',dkim_check,name,selected)
    data['dmarc']=safe('DMARC',record_check,'dmarc',name,policy)
    data['dns_evidence']=safe('DNS evidence',dns_evidence.lookup,name,selected)
    data['dns_host']=safe('DNS host',dns_host_lookup,name)
    if include_expiry: data['domain_expiry']=safe('Domain expiry',domain_expiry.lookup,name)
    return data
def isolated_domain(row,include_expiry=True):
    """Check one domain in one child process. Returns None on process failure."""
    args=[sys.executable,__file__,'check-domain',row['domain'],row['selectors'],row['policy'],'1' if include_expiry else '0']
    try:
        p=subprocess.run(args,capture_output=True,text=True,timeout=DOMAIN_CHECK_TIMEOUT)  # nosec B603 - fixed argument list, no shell
        if p.returncode:
            logging.error('Domain checker failed for %s: %s',row['domain'],p.stderr[-2000:]); return None
        data=json.loads(p.stdout)
        return data if isinstance(data,dict) else None
    except subprocess.TimeoutExpired:
        logging.error('Domain checker exceeded %s seconds for %s',DOMAIN_CHECK_TIMEOUT,row['domain']); return None
    except Exception as e:
        logging.error('Domain checker error for %s: %s',row['domain'],e); return None
def beat():
    with db() as c: c.execute("INSERT OR REPLACE INTO state VALUES('heartbeat',?)",(str(time.time()),))
def active_batch(c):
    row=c.execute("SELECT * FROM check_batches WHERE status='active' ORDER BY id DESC LIMIT 1").fetchone()
    if row and time.time()-row['updated']>600:
        c.execute("UPDATE check_batches SET status='stalled',finished=? WHERE id=?",(time.time(),row['id']))
        return None
    return row

def batch_snapshot(c):
    row=active_batch(c) or c.execute('SELECT * FROM check_batches ORDER BY id DESC LIMIT 1').fetchone()
    if not row: return None
    counts={x['status']:x['n'] for x in c.execute('SELECT status,COUNT(*) n FROM check_batch_items WHERE batch_id=? GROUP BY status',(row['id'],))}
    complete=counts.get('complete',0); failed=counts.get('failed',0); done=complete+failed
    elapsed=max(0,time.time()-row['created']); rate=done/elapsed if done and elapsed else 0
    remaining=max(0,row['total']-done); eta=round(remaining/rate) if rate else None
    avg=c.execute("SELECT AVG(finished-started) FROM check_batch_items WHERE batch_id=? AND status='complete' AND started IS NOT NULL AND finished IS NOT NULL",(row['id'],)).fetchone()[0]
    return dict(id=row['id'],status=row['status'],total=row['total'],done=done,complete=complete,failed=failed,queued=counts.get('queued',0),running=counts.get('running',0),percent=round(done*100/row['total']) if row['total'] else 100,workers=check_workers(),elapsed_seconds=round(elapsed),eta_seconds=eta,avg_seconds=round(avg,1) if avg is not None else None,cancelled=bool(row['cancelled']) if 'cancelled' in row.keys() else False)

EXPIRY_CACHE_SECONDS=24*3600
def cached_expiry(row,now=None):
    """Reuse a recent confirmed or not-published expiry result; retry errors."""
    now=now or time.time()
    try:
        previous=json.loads(row.get('result') or '{}')
    except (TypeError,ValueError):
        return None
    item=previous.get('domain_expiry') if isinstance(previous,dict) else None
    if not isinstance(item,dict) or item.get('status') not in ('ok','not_published'):
        return None
    checked=item.get('checked_at')
    if not isinstance(checked,(int,float)) or now-checked>EXPIRY_CACHE_SECONDS or checked>now+300:
        return None
    result=dict(item)
    result['cached']=True
    if result.get('expires_at') is not None:
        result['days_remaining']=int((float(result['expires_at'])-now)//86400)
    return result
def run_domain_check(row,batch_id,scheduled):
    cached=cached_expiry(row)
    checked=isolated_domain(row,include_expiry=cached is None)
    if checked is None:
        checked={}; failure=res('unknown',f'Domain check process failed or exceeded {DOMAIN_CHECK_TIMEOUT} seconds; see worker logs.')
    else: failure=res('unknown','Checker returned no result.')
    def part(kind):
        value=checked.get(kind)
        return value if isinstance(value,dict) and 'status' in value else failure
    data={}
    for kind in ('spf','dkim','dmarc'):
        data[kind]=part(kind)
    data['spf']=apply_approved_exceptions('spf',data['spf'],row['approved_spf'],row['approval_note'])
    data['dmarc']=apply_approved_exceptions('dmarc',data['dmarc'],row['approved_dmarc'],row['approval_note'])
    data['status']=worst(data.values())
    data['dns_evidence']=checked.get('dns_evidence') if isinstance(checked.get('dns_evidence'),dict) else failure
    data['dns_host']=checked.get('dns_host') if isinstance(checked.get('dns_host'),dict) else failure
    data['domain_expiry']=cached or part('domain_expiry')
    data['configuration']={k:row[k] for k in ('domain','label','selectors','policy','approved_spf','approved_dmarc','approval_note')}
    data['configuration']['dkim_rotation_started']=row.get('dkim_rotation_started','')
    data['trigger']='scheduled' if scheduled else 'manual / new or edited domain'
    now=time.time(); encoded=json.dumps(data)
    with db() as c:
        due=next_run(now,get_clock(c),selected_zone(c)) if scheduled else row['due']
        updated=c.execute('UPDATE domains SET result=?,checked=?,due=?,manual_pending=0 WHERE id=? AND revision=?',(encoded,now,due,row['id'],row['revision'])).rowcount
        if updated:
            # Only a fresh check accepted by the revision guard may clear tracking.
            if data['dkim'].get('status')=='pass' and row.get('dkim_rotation_started'):
                c.execute("UPDATE domains SET dkim_rotation_started='' WHERE id=? AND revision=? AND dkim_rotation_started=?",(row['id'],row['revision'],row['dkim_rotation_started']))
            record_history(c,row['id'],now,data,encoded)
            c.execute('DELETE FROM history WHERE domain_id=? AND id NOT IN(SELECT id FROM history WHERE domain_id=? ORDER BY id DESC LIMIT 1000)',(row['id'],row['id']))
        if batch_id:
            state='complete' if updated else 'failed'; error='' if updated else 'Domain changed during check.'
            c.execute('UPDATE check_batch_items SET status=?,finished=?,error=? WHERE batch_id=? AND domain_id=?',(state,now,error,batch_id,row['id']))
            counts=c.execute("SELECT COUNT(*) total,SUM(status IN ('complete','failed')) done FROM check_batch_items WHERE batch_id=?",(batch_id,)).fetchone()
            finished=counts['done']>=counts['total']
            c.execute('UPDATE check_batches SET updated=?,status=?,finished=? WHERE id=?',(now,'complete' if finished else 'active',now if finished else None,batch_id))
        c.execute('DELETE FROM history WHERE checked<?',(now-90*86400,))
    return row['id']

def worker():
    init(); workers=check_workers(); logging.info('Worker concurrency: %s',workers)
    with db() as c:
        c.execute("UPDATE check_batch_items SET status='queued',started=NULL WHERE status='running'")
        batch=active_batch(c)
        if batch: c.execute('UPDATE check_batches SET updated=? WHERE id=?',(time.time(),batch['id']))
    futures={}
    with ThreadPoolExecutor(max_workers=workers,thread_name_prefix='domain-check') as pool:
        while True:
            try:
                beat()
                done,_=wait(tuple(futures),timeout=0,return_when=FIRST_COMPLETED) if futures else (set(),set())
                for future in done:
                    ident=futures.pop(future)
                    try: future.result()
                    except Exception:
                        logging.exception('Domain check failed for id %s',ident)
                        now=time.time()
                        with db() as c:
                            c.execute('UPDATE domains SET manual_pending=0 WHERE id=?',(ident,))
                            item=c.execute("SELECT batch_id FROM check_batch_items WHERE domain_id=? AND status='running' ORDER BY batch_id DESC LIMIT 1",(ident,)).fetchone()
                            if item:
                                c.execute("UPDATE check_batch_items SET status='failed',finished=?,error=? WHERE batch_id=? AND domain_id=?",(now,'Unhandled worker error',item['batch_id'],ident))
                                counts=c.execute("SELECT COUNT(*) total,SUM(status IN ('complete','failed')) done FROM check_batch_items WHERE batch_id=?",(item['batch_id'],)).fetchone()
                                finished=counts['done']>=counts['total']
                                c.execute('UPDATE check_batches SET updated=?,status=?,finished=? WHERE id=?',(now,'complete' if finished else 'active',now if finished else None,item['batch_id']))
                busy=set(futures.values())
                while len(futures)<workers:
                    now=time.time()
                    with db() as c:
                        placeholders=','.join('?' for _ in busy)
                        sql='SELECT * FROM domains WHERE (manual_pending=1 OR due<=?)'
                        params=[now]
                        if busy:
                            sql+=f' AND id NOT IN ({placeholders})'; params.extend(sorted(busy))
                        sql+=' ORDER BY manual_pending DESC,due,id LIMIT 1'
                        row=c.execute(sql,params).fetchone()
                        if not row: break
                        row=dict(row); started=time.time(); batch_id=None
                        batch=active_batch(c)
                        if batch:
                            item=c.execute("SELECT status FROM check_batch_items WHERE batch_id=? AND domain_id=?",(batch['id'],row['id'])).fetchone()
                            if item and item['status']=='queued':
                                c.execute("UPDATE check_batch_items SET status='running',started=? WHERE batch_id=? AND domain_id=?",(started,batch['id'],row['id']))
                                c.execute('UPDATE check_batches SET updated=? WHERE id=?',(started,batch['id']))
                                batch_id=batch['id']
                        scheduled=row['due']<=started
                    future=pool.submit(run_domain_check,row,batch_id,scheduled)
                    futures[future]=row['id']; busy.add(row['id'])
                time.sleep(0.5 if futures else 5)
            except Exception:
                logging.exception('Worker coordinator error'); time.sleep(5)
app=Flask(__name__)
app.jinja_env.globals['dns_host_label']=dns_host_label
app.jinja_env.globals['expiry_label']=domain_expiry.label
app.jinja_env.globals['expiry_class']=domain_expiry.css_class
app.jinja_env.globals['expiry_source']=domain_expiry.source_label
def history_changes(newer,older):
    """Plain-English list of what differs between a history entry and the one before it."""
    if not isinstance(newer,dict) or not isinstance(older,dict): return []
    changes=[]
    for kind in ('spf','dkim','dmarc'):
        new=newer.get(kind) or {}; old=older.get(kind) or {}
        if new.get('status')!=old.get('status'):
            changes.append(f"{kind.upper()} {old.get('status','unknown')} → {new.get('status','unknown')}")
            continue
        if kind=='dkim':
            pick=lambda r:[(s.get('selector'),s.get('record'),s.get('status')) for s in r.get('selectors') or []]
        else:
            pick=lambda r:(r.get('raw') or {}).get('record')
        if pick(new)!=pick(old): changes.append(f'{kind.upper()} record changed')
    if (newer.get('dns_host') or {}).get('nameservers')!=(older.get('dns_host') or {}).get('nameservers'):
        changes.append('DNS host changed')
    if (newer.get('domain_expiry') or {}).get('expires_at')!=(older.get('domain_expiry') or {}).get('expires_at'):
        changes.append('Expiry date changed')
    return changes
@app.template_filter('shortdate')
def shortdate(v):
    try: return datetime.strptime(str(v),'%Y-%m-%d').strftime('%d %b %Y')
    except (ValueError,TypeError): return str(v or '')
app.jinja_env.globals['app_version']=APP_VERSION
app.jinja_env.globals['history_changes']=history_changes
app.secret_key=os.environ.get('SECRET_KEY','')
app.config.update(MAX_CONTENT_LENGTH=16384,SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Strict',PERMANENT_SESSION_LIFETIME=timedelta(hours=8))
@app.template_filter('stamp')
def stamp(v): return datetime.fromtimestamp(v,selected_zone()).strftime('%d %b %Y %H:%M %Z') if v else 'Never'
@app.before_request
def protect():
    if request.endpoint=='health': return
    if not app.secret_key: abort(503)
    if 'csrf' not in session: session['csrf']=secrets.token_urlsafe(32)
    if request.method=='POST' and not secrets.compare_digest(session['csrf'],request.form.get('csrf','')): abort(400,'Invalid form token. Refresh and retry.')
    if request.endpoint!='login' and not session.get('authenticated'): return redirect('/login')
@app.after_request
def headers(r):
    r.headers.update({'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','Referrer-Policy':'no-referrer','Content-Security-Policy':"default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'none'"})
    return r
@app.get('/health')
def health():
    with db() as c: c.execute('SELECT 1').fetchone()
    return {'status':'ok','version':APP_VERSION}
@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        now=time.time()
        with db() as c:
            c.execute('BEGIN IMMEDIATE'); c.execute('DELETE FROM attempts WHERE at<?',(now-300,))
            count=c.execute('SELECT COUNT(*) FROM attempts').fetchone()[0]
            if count<5: c.execute('INSERT INTO attempts VALUES(?)',(now,))
        if count>=5: flash('Too many login attempts. Wait five minutes.')
        elif check_password_hash(os.environ['ADMIN_PASSWORD_HASH'],request.form.get('password','')):
            session.clear(); session['authenticated']=True; session['csrf']=secrets.token_urlsafe(32); session.permanent=True
            return redirect('/')
        else: flash('Incorrect password.')
    return render_template('login.html')
@app.post('/logout')
def logout(): session.clear(); return redirect('/login')
@app.get('/')
def index():
    with db() as c:
        rows=c.execute('SELECT * FROM domains ORDER BY domain').fetchall()
        b=c.execute("SELECT value FROM state WHERE key='heartbeat'").fetchone()
        clock=get_clock(c)
        timezone_name=get_timezone(c)
        check_batch=batch_snapshot(c)
    domains=[]; now=time.time()
    for r in rows:
        d=dict(r); d['data']=json.loads(r['result']) if r['result'] else None
        d['stale']=bool(r['checked'] and now-r['checked']>26*3600)
        d['rotation']=dkim_rotation_info(d.get('dkim_rotation_started'),now,ZoneInfo(timezone_name))
        # Use the same database-backed provider label as the card display.
        # This includes built-in and custom DNS provider mappings.
        d['dns_host_search']=app.jinja_env.globals['dns_host_label'](d['data'])
        host=(d['data'] or {}).get('dns_host') or {}
        d['dns_nameserver_search']=' '.join(str(x) for x in host.get('nameservers',[]) if isinstance(x,str))
        domains.append(d)
    summary={kind:{status:0 for status in ('pass','warn','fail','unknown')} for kind in ('spf','dkim','dmarc')}
    for d in domains:
        for kind in summary:
            if d['stale'] or not d['data'] or not d['data'].get(kind):
                status='unknown'
            else:
                status=d['data'][kind].get('status','unknown')
                if status not in summary[kind]: status='unknown'
            summary[kind][status]+=1
    filter_kind=request.args.get('kind','').lower()
    filter_status=request.args.get('status','').lower()
    valid_kinds=('spf','dkim','dmarc')
    valid_statuses=('pass','warn','fail','unknown')
    if filter_kind not in valid_kinds or filter_status not in valid_statuses:
        filter_kind=filter_status=''
    def displayed_status(d,kind):
        if d['stale'] or not d['data'] or not d['data'].get(kind): return 'unknown'
        status=d['data'][kind].get('status','unknown')
        return status if status in valid_statuses else 'unknown'
    search_query=request.args.get('q','').strip()[:100]
    sort_mode=request.args.get('sort','domain')
    valid_sorts=('severity','domain','last_checked','next_due')
    if sort_mode not in valid_sorts: sort_mode='domain'
    filtered_domains=domains
    if filter_kind:
        filtered_domains=[d for d in filtered_domains if displayed_status(d,filter_kind)==filter_status]
    if search_query:
        needle=search_query.casefold()
        filtered_domains=[d for d in filtered_domains if any(needle in value.casefold() for value in (
            d['domain'], d['label'] or '', d['dns_host_search'] or '', d['dns_nameserver_search'] or ''
        ))]
    severity={'fail':0,'unknown':1,'warn':2,'pass':3}  # nosec B105 - sort order, not a password
    def severity_key(d):
        states=[displayed_status(d,k) for k in valid_kinds]
        return (min(severity[x] for x in states),d['domain'])
    sort_keys={
        'severity':severity_key,
        'domain':lambda d:d['domain'],
        'last_checked':lambda d:(-(d['checked'] or 0),d['domain']),
        'next_due':lambda d:(d['due'] or float('inf'),d['domain'])
    }
    filtered_domains=sorted(filtered_domains,key=sort_keys[sort_mode])
    return render_template('index.html',domains=domains,filtered_domains=filtered_domains,worker_ok=bool(b and now-float(b[0])<180),clock=clock,timezone_name=timezone_name,summary=summary,filter_kind=filter_kind,filter_status=filter_status,search_query=search_query,sort_mode=sort_mode,check_batch=check_batch,now=now)
DEFAULT_SELECTORS='selector1,selector2'
MAX_DOMAINS_PER_ADD=200
MAX_DOMAINS_TOTAL=500
MAX_DOMAIN_TEXT=20000
def parse_domain_entries(text,shared_label='',chosen_selectors=''):
    """Turn the Add domain text into [(domain,label)] without touching the database.
    Each line is a domain, optionally followed by a comma and a client label.
    Returns (entries,repeated_lines,errors); errors is a list of (line number,message)."""
    import csv
    if len(text)>MAX_DOMAIN_TEXT: raise ValueError(f'Too much text. Add at most {MAX_DOMAINS_PER_ADD} domains at a time.')
    lines=[line for line in text.splitlines() if line.strip()]
    if not lines: raise ValueError('Enter at least one domain.')
    if len(lines)>MAX_DOMAINS_PER_ADD: raise ValueError(f'Add at most {MAX_DOMAINS_PER_ADD} domains at a time.')
    entries=[]; seen=set(); errors=[]; repeated=0
    for number,line in enumerate(lines,1):
        try:
            fields=next(csv.reader([line],strict=True))
            if not 1<=len(fields)<=2: raise ValueError('Use domain or domain,label on each line.')
            name=domain_name(fields[0])
            label=fields[1].strip() if len(fields)==2 and fields[1].strip() else shared_label
            if len(label)>100: raise ValueError('Label exceeds 100 characters.')
            if chosen_selectors and any(len(f'{s}._domainkey.{name}')>253 for s in chosen_selectors.split(',')):
                raise ValueError('Selector and domain name are too long together.')
            if name in seen: repeated+=1; continue
            seen.add(name); entries.append((name,label))
        except (ValueError,csv.Error,StopIteration) as exc:
            errors.append((number,str(exc)))
    return entries,repeated,errors
def add_summary(added,existing,repeated):
    """Message shown after an Add domain submission."""
    if added==1 and not existing and not repeated: return 'Saved. Check queued.'
    text=f"Added {added} domain{'s' if added!=1 else ''}."
    skipped=[]
    if existing: skipped.append(f"{existing} existing domain{'s' if existing!=1 else ''}")
    if repeated: skipped.append(f"{repeated} duplicate line{'s' if repeated!=1 else ''}")
    if skipped: text+=' '+' and '.join(skipped)+' skipped.'
    if existing: text+=' Existing domains were not changed.'
    return text+(' Initial check queued.' if added==1 else ' Initial checks queued.')
def add_domains(form):
    """Add one or many domains from the Add domain form and return the message to show.
    Everything is checked before anything is saved. ValueError means nothing was added."""
    selected=selectors(form['selectors']) or DEFAULT_SELECTORS
    if form['policy'] not in ('none','quarantine','reject'): raise ValueError('Invalid policy.')
    shared_label=form['label'].strip()
    if len(shared_label)>100: raise ValueError('Label exceeds 100 characters.')
    line_count=len([line for line in form['domain'].splitlines() if line.strip()])
    entries,repeated,errors=parse_domain_entries(form['domain'],shared_label,selected)
    if errors:
        if line_count==1: raise ValueError(errors[0][1])
        raise ValueError('Nothing was added. '+' | '.join(f'Line {number}: {message}' for number,message in errors[:10]))
    if len(entries)>1 and form['manual_expiry'].strip():
        raise ValueError('A manual expiry date can only be set when adding a single domain. Leave it blank, or edit each domain afterwards.')
    manual_expiry=domain_expiry.validate_manual_date(form['manual_expiry'])
    manual_expiry_source=form['manual_expiry_source'].strip()
    if len(manual_expiry_source)>100: raise ValueError('Expiry source/note exceeds 100 characters.')
    if manual_expiry and not manual_expiry_source: manual_expiry_source='Manual / registrar portal'
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        existing={row[0] for row in c.execute('SELECT domain FROM domains')}
        new=[entry for entry in entries if entry[0] not in existing]
        skipped=len(entries)-len(new)
        if not new:
            raise ValueError('Domain already exists.' if len(entries)==1 else f'No domains added. All {len(entries)} domains already exist.')
        if len(existing)+len(new)>MAX_DOMAINS_TOTAL: raise ValueError(f'Initial version limit: {MAX_DOMAINS_TOTAL} domains. Nothing was added.')
        due=next_run(time.time(),get_clock(c),selected_zone(c))
        c.executemany('INSERT INTO domains(domain,label,selectors,policy,manual_expiry,manual_expiry_source,due,manual_pending) VALUES(?,?,?,?,?,?,?,1)',
            [(name,label,selected,form['policy'],manual_expiry,manual_expiry_source,due) for name,label in new])
    return add_summary(len(new),skipped,repeated)
@app.route('/new',methods=['GET','POST'])
@app.route('/domain/<int:ident>/edit',methods=['GET','POST'])
def edit(ident=None):
    with db() as c: row=c.execute('SELECT * FROM domains WHERE id=?',(ident,)).fetchone() if ident else None
    if ident and not row: abort(404)
    form=dict(row) if row else dict(domain='',label='',selectors='',policy='quarantine',manual_expiry='',manual_expiry_source='',approved_spf='',approved_dmarc='',approval_note='',dkim_rotation_started='')
    if request.method=='POST':
        form.update({k:request.form.get(k,'') for k in ('domain','label','selectors','policy','manual_expiry','manual_expiry_source','approved_spf','approved_dmarc','approval_note','dkim_rotation_started')})
        try:
            if not ident:
                flash(add_domains(form)); return redirect('/')
            name=domain_name(form['domain']); selected=selectors(form['selectors'])
            if selected and any(len(f'{s}._domainkey.{name}')>253 for s in selected.split(',')): raise ValueError('Selector and domain name are too long together.')
            if form['policy'] not in ('none','quarantine','reject'): raise ValueError('Invalid policy.')
            if len(form['label'])>100: raise ValueError('Label exceeds 100 characters.')
            manual_expiry=domain_expiry.validate_manual_date(form['manual_expiry'])
            manual_expiry_source=form['manual_expiry_source'].strip()
            if len(manual_expiry_source)>100: raise ValueError('Expiry source/note exceeds 100 characters.')
            if manual_expiry and not manual_expiry_source: manual_expiry_source='Manual / registrar portal'
            approved_spf='\n'.join(approved_fragments(form['approved_spf']))
            approved_dmarc='\n'.join(approved_fragments(form['approved_dmarc']))
            rotation_started=validate_dkim_rotation_date(form['dkim_rotation_started'])
            approval_note=form['approval_note'].strip()
            if len(approval_note)>500: raise ValueError('Approval note exceeds 500 characters.')
            with db() as c:
                c.execute('UPDATE domains SET domain=?,label=?,selectors=?,policy=?,manual_expiry=?,manual_expiry_source=?,approved_spf=?,approved_dmarc=?,approval_note=?,dkim_rotation_started=?,revision=revision+1,manual_pending=1,checked=NULL,result=NULL WHERE id=?',(name,form['label'],selected,form['policy'],manual_expiry,manual_expiry_source,approved_spf,approved_dmarc,approval_note,rotation_started,ident))
            flash('Saved. Check queued.'); return redirect(f'/domain/{ident}')
        except (ValueError,sqlite3.IntegrityError) as e: flash('Domain already exists.' if isinstance(e,sqlite3.IntegrityError) else str(e))
    return render_template('edit.html',form=form,ident=ident,rotation_today=datetime.now(selected_zone()).date().isoformat())

@app.post('/domain/<int:ident>/dkim-rotation')
def save_dkim_rotation(ident):
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        row=c.execute('SELECT * FROM domains WHERE id=?',(ident,)).fetchone()
        if not row: abort(404)
        action=request.form.get('rotation_action','save')
        if action not in ('save','today','clear'): abort(400,'Invalid rotation action.')
        zone=selected_zone(c)
        try:
            value='' if action=='clear' else datetime.now(zone).date().isoformat() if action=='today' else validate_dkim_rotation_date(request.form.get('dkim_rotation_started',''),zone=zone)
        except ValueError as exc:
            flash(str(exc)); return redirect(f'/domain/{ident}')
        changed=value!=row['dkim_rotation_started']
        if changed:
            c.execute("UPDATE domains SET dkim_rotation_started=?,revision=revision+1,manual_pending=CASE WHEN ?<>'' THEN 1 ELSE manual_pending END WHERE id=?",(value,value,ident))
    flash(('DKIM rotation date saved. Fresh check queued; DNS status is unchanged.' if value else 'DKIM rotation tracking cleared. DNS status is unchanged.') if changed else 'DKIM rotation date unchanged.')
    return redirect(f'/domain/{ident}')

@app.post('/domain/<int:ident>/check')
def queue(ident):
    with db() as c:
        exists=c.execute('SELECT 1 FROM domains WHERE id=?',(ident,)).fetchone()
        if not exists: abort(404)
        batch=active_batch(c)
        included=batch and c.execute("SELECT 1 FROM check_batch_items WHERE batch_id=? AND domain_id=? AND status IN ('queued','running')",(batch['id'],ident)).fetchone()
        added=0 if included else c.execute('UPDATE domains SET manual_pending=1,revision=revision+1 WHERE id=? AND manual_pending=0',(ident,)).rowcount
    flash('Already included in the active Check-all run.' if included else 'Check queued. Refresh shortly.' if added else 'Check already queued. Daily schedule unchanged.')
    target=request.form.get('next','')
    if not target.startswith('/') or target.startswith('//'):
        target=f'/domain/{ident}'
    return redirect(target)
@app.post('/domain/<int:ident>/delete')
def delete(ident):
    if request.form.get('confirm')!='DELETE': abort(400,'Type DELETE to confirm.')
    with db() as c: c.execute('DELETE FROM domains WHERE id=?',(ident,))
    flash('Domain and history deleted.'); return redirect('/')
@app.route('/settings',methods=['GET','POST'])
def settings():
    if request.method=='POST':
        try:
            clock=validate_time(request.form.get('daily_time',''))
            timezone_name=validate_timezone(request.form.get('timezone',''))
            zone=ZoneInfo(timezone_name)
            with db() as c:
                c.execute('BEGIN IMMEDIATE')
                c.execute("INSERT OR REPLACE INTO state VALUES('daily_time',?)",(clock,))
                c.execute("INSERT OR REPLACE INTO state VALUES('timezone',?)",(timezone_name,))
                c.execute('UPDATE domains SET due=?,revision=revision+1',(next_run(time.time(),clock,zone),))
            flash('Daily check time and timezone saved for all domains. Manual checks do not change this schedule.')
            return redirect('/')
        except ValueError as e: flash(str(e))
    with db() as c:
        clock=get_clock(c)
        timezone_name=get_timezone(c)
    return render_template('settings.html',clock=clock,timezone_name=timezone_name,timezones=TIMEZONES)

@app.get('/domain/<int:ident>')
def detail(ident):
    with db() as c:
        row=c.execute('SELECT * FROM domains WHERE id=?',(ident,)).fetchone()
        hist=c.execute('SELECT * FROM history WHERE domain_id=? ORDER BY id DESC LIMIT 30',(ident,)).fetchall()
    if not row: abort(404)
    now=time.time()
    rotation=dkim_rotation_info(row['dkim_rotation_started'],now)
    rotation_fresh=bool(row['result'] and row['checked'] and now-row['checked']<=26*3600)
    return render_template('detail.html',domain=row,history=[dict(x,data=json.loads(x['result'])) for x in hist],rotation=rotation,rotation_fresh=rotation_fresh,rotation_today=datetime.now(selected_zone()).date().isoformat())

@app.route('/bulk-add', methods=['GET', 'POST'])
def bulk_add():
    """Bulk add was merged into Add domain. Keep the old address working."""
    return redirect('/new')



@app.post('/check-all')
def check_all():
    now=time.time(); target=request.form.get('next','/')
    if not target.startswith('/') or target.startswith('//'): target='/'
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        existing=active_batch(c)
        if existing:
            snap=batch_snapshot(c); flash(f"Check-all already running: {snap['done']} / {snap['total']} complete.")
            return redirect(target)
        domain_rows=c.execute('SELECT id,manual_pending FROM domains ORDER BY id').fetchall()
        if not domain_rows: flash('There are no domains to check.'); return redirect(target)
        batch=c.execute("INSERT INTO check_batches(status,total,created,updated) VALUES('active',?,?,?)",(len(domain_rows),now,now)).lastrowid
        c.executemany("INSERT INTO check_batch_items(batch_id,domain_id,status,was_pending) VALUES(?,?,'queued',?)",[(batch,r['id'],int(bool(r['manual_pending']))) for r in domain_rows])
        c.execute('UPDATE domains SET manual_pending=1,revision=revision+1 WHERE manual_pending=0')
    flash(f'Check-all started: 0 / {len(domain_rows)} complete.'); return redirect(target)

@app.post('/check-all/cancel')
def cancel_check_all():
    now=time.time(); target=request.form.get('next','/')
    if not target.startswith('/') or target.startswith('//'): target='/'
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        batch=active_batch(c)
        if not batch:
            flash('No active Check-all run to cancel.')
            return redirect(target)
        queued=c.execute("SELECT domain_id,was_pending FROM check_batch_items WHERE batch_id=? AND status='queued'",(batch['id'],)).fetchall()
        running=c.execute("SELECT COUNT(*) FROM check_batch_items WHERE batch_id=? AND status='running'",(batch['id'],)).fetchone()[0]
        clear_ids=[r['domain_id'] for r in queued if not r['was_pending']]
        if clear_ids:
            marks=','.join('?' for _ in clear_ids)
            c.execute(f'UPDATE domains SET manual_pending=0 WHERE id IN ({marks})',clear_ids)  # nosec B608 - placeholders only; values are bound
        c.execute("UPDATE check_batch_items SET status='failed',finished=?,error='Cancelled by administrator' WHERE batch_id=? AND status='queued'",(now,batch['id']))
        c.execute("UPDATE check_batches SET status='complete',cancelled=1,updated=?,finished=? WHERE id=?",(now,now,batch['id']))
    flash(f'Check-all cancelled: {len(queued)} queued checks removed; {running} already running will finish.')
    return redirect(target)

@app.get('/check-all/status')
def check_all_status():
    with db() as c: snap=batch_snapshot(c)
    return snap or {'status':'idle','total':0,'done':0,'complete':0,'failed':0,'queued':0,'running':0,'percent':0,'cancelled':False}


@app.get('/domains/status')
def domains_status():
    ids=[]
    for part in request.args.get('ids','').split(',')[:200]:
        if part.strip().isdigit():
            ids.append(int(part.strip()))
    if not ids:
        return {'domains':{}}
    with db() as c:
        batch=active_batch(c)
        running=set()
        if batch:
            running={r['domain_id'] for r in c.execute("SELECT domain_id FROM check_batch_items WHERE batch_id=? AND status='running'",(batch['id'],))}
        marks=','.join('?' for _ in ids)
        rows=c.execute(f'SELECT id,manual_pending,checked FROM domains WHERE id IN ({marks})',ids).fetchall()  # nosec B608 - placeholders only; values are bound
    return {'domains':{str(r['id']):{'pending':bool(r['manual_pending']),'checking':r['id'] in running,'checked':r['checked']} for r in rows}}
@app.get('/changelog')
def changelog():
    from pathlib import Path
    lines=Path('/app/CHANGELOG.md').read_text().splitlines()
    releases=[]; release=None; section=None
    for line in lines:
        if line.startswith('## '):
            match=re.fullmatch(r'## ([0-9]+\.[0-9]+\.[0-9]+) - ([0-9]{4}-[0-9]{2}-[0-9]{2})',line)
            if not match: continue
            release={'version':match.group(1),'date':match.group(2),'sections':[]}
            releases.append(release); section=None
        elif release and line.startswith('### '):
            section={'name':line[4:],'items':[]}; release['sections'].append(section)
        elif release and section and line.startswith('- '):
            section['items'].append(line[2:])
    return render_template('changelog.html',releases=releases,version=APP_VERSION)

from dns_providers import register as register_dns_providers
register_dns_providers(sys.modules[__name__])

if __name__=='__main__':
    mode=sys.argv[1]
    if mode=='init': init()
    elif mode=='worker': worker()
    elif mode=='check':
        _,_,kind,name,selected,policy=sys.argv
        print(json.dumps(dns_evidence.lookup(name,selected) if kind=='dns_evidence' else domain_expiry.lookup(name) if kind=='domain_expiry' else dns_host_lookup(name) if kind=='dns_host' else dkim_check(name,selected) if kind=='dkim' else record_check(kind,name,policy),default=str))
    elif mode=='check-domain':
        _,_,name,selected,policy,include_expiry=sys.argv
        print(json.dumps(collect_domain(name,selected,policy,include_expiry=='1'),default=str))
    elif mode=='worker-health':
        with db() as c: b=c.execute("SELECT value FROM state WHERE key='heartbeat'").fetchone()
        sys.exit(0 if b and time.time()-float(b[0])<180 else 1)
