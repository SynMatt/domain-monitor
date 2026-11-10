import os,sys,time,json,re,base64,sqlite3,secrets,subprocess,logging
from contextlib import contextmanager
from datetime import datetime,timezone,timedelta
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
APP_VERSION='0.10.2'
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
""")
        columns={r[1] for r in c.execute('PRAGMA table_info(domains)')}
        if 'manual_pending' not in columns:
            c.execute('ALTER TABLE domains ADD COLUMN manual_pending INTEGER NOT NULL DEFAULT 0')
        c.execute("INSERT OR IGNORE INTO state VALUES('daily_time','03:00')")
        c.execute("INSERT OR IGNORE INTO state VALUES('timezone',?)",(DEFAULT_TIMEZONE,))
        if not c.execute("SELECT 1 FROM state WHERE key='fixed_schedule_v1'").fetchone():
            due=next_run(time.time(),get_clock(c),selected_zone(c))
            c.execute('UPDATE domains SET due=?,manual_pending=CASE WHEN checked IS NULL THEN 1 ELSE 0 END',(due,))
            c.execute("INSERT INTO state VALUES('fixed_schedule_v1','1')")
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
def record_check(kind,domain,policy):
    from checkdmarc.spf import check_spf
    from checkdmarc.dmarc import check_dmarc
    try:
        raw=(check_spf if kind=='spf' else check_dmarc)(domain,timeout=3.0,retries=1)
        raw=json.loads(json.dumps(raw,default=str)); warnings=list(raw.get('warnings',[]))
        if raw.get('valid') is not True:
            error=str(raw.get('error','No valid result returned.'))
            return res('unknown' if temporary(error) else 'fail',error,raw=raw)
        if kind=='spf':
            if raw.get('parsed',{}).get('all') in ('pass','neutral'):
                return res('fail','SPF allows all senders or has no restrictive fallback.',raw=raw)
            if '%' in str(raw.get('record','')): warnings.append('SPF macros require runtime sender context; static validation is incomplete.')
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
    except Exception as e: return res('unknown',f'Checker error: {type(e).__name__}: {e}')
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
        if pub.key_size<2048: warnings.append('RSA key below recommended 2048 bits.')
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
        except (dns.resolver.NXDOMAIN,dns.resolver.NoAnswer): item=res('fail','DKIM TXT record not found, including any CNAME target.')
        except (ValueError,UnicodeError) as e: item=res('fail',str(e))
        except Exception as e: item=res('unknown','DNS/checker error: '+str(e))
        results.append(dict(selector=s,query=name,**item))
    return res(worst(results),'All configured selectors must pass.',selectors=results)
def isolated(kind,row):
    try:
        p=subprocess.run([sys.executable,__file__,'check',kind,row['domain'],row['selectors'],row['policy']],capture_output=True,text=True,timeout=120)
        if p.returncode:
            logging.error('Checker failed: %s',p.stderr[-2000:]); return res('unknown','Checker process failed; see worker logs.')
        return json.loads(p.stdout)
    except subprocess.TimeoutExpired: return res('unknown','Check exceeded 120-second time limit.')
    except Exception as e: return res('unknown','Checker error: '+str(e))
def beat():
    with db() as c: c.execute("INSERT OR REPLACE INTO state VALUES('heartbeat',?)",(str(time.time()),))
def worker():
    init()
    while True:
        try:
            beat()
            with db() as c: row=c.execute('SELECT * FROM domains WHERE manual_pending=1 OR due<=? ORDER BY due,id LIMIT 1',(time.time(),)).fetchone()
            if row:
                started=time.time()
                scheduled=row['due']<=started
                data={}
                for kind in ('spf','dkim','dmarc'):
                    beat(); data[kind]=isolated(kind,row)
                data['status']=worst(data.values())
                data['configuration']={k:row[k] for k in ('domain','label','selectors','policy')}
                data['trigger']='scheduled' if scheduled else 'manual / new or edited domain'
                now=time.time(); encoded=json.dumps(data)
                with db() as c:
                    due=next_run(now,get_clock(c),selected_zone(c)) if scheduled else row['due']
                    updated=c.execute('UPDATE domains SET result=?,checked=?,due=?,manual_pending=0 WHERE id=? AND revision=?',(encoded,now,due,row['id'],row['revision'])).rowcount
                    if updated:
                        c.execute('INSERT INTO history(domain_id,checked,result) VALUES(?,?,?)',(row['id'],now,encoded))
                        c.execute('DELETE FROM history WHERE domain_id=? AND id NOT IN(SELECT id FROM history WHERE domain_id=? ORDER BY id DESC LIMIT 1000)',(row['id'],row['id']))
                    c.execute('DELETE FROM history WHERE checked<?',(now-90*86400,))
            else: time.sleep(5)
        except Exception:
            logging.exception('Worker loop error'); time.sleep(10)
app=Flask(__name__)
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
    r.headers.update({'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','Referrer-Policy':'no-referrer','Content-Security-Policy':"default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'none'; frame-ancestors 'none'; form-action 'self'; base-uri 'none'"})
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
    domains=[]; now=time.time()
    for r in rows:
        d=dict(r); d['data']=json.loads(r['result']) if r['result'] else None
        d['stale']=bool(r['checked'] and now-r['checked']>26*3600); domains.append(d)
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
    sort_mode=request.args.get('sort','severity')
    valid_sorts=('severity','domain','last_checked','next_due')
    if sort_mode not in valid_sorts: sort_mode='severity'
    filtered_domains=domains
    if filter_kind:
        filtered_domains=[d for d in filtered_domains if displayed_status(d,filter_kind)==filter_status]
    if search_query:
        needle=search_query.casefold()
        filtered_domains=[d for d in filtered_domains if needle in d['domain'].casefold() or needle in (d['label'] or '').casefold()]
    severity={'fail':0,'unknown':1,'warn':2,'pass':3}
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
    return render_template('index.html',domains=domains,filtered_domains=filtered_domains,worker_ok=bool(b and now-float(b[0])<180),clock=clock,timezone_name=timezone_name,summary=summary,filter_kind=filter_kind,filter_status=filter_status,search_query=search_query,sort_mode=sort_mode)
@app.route('/new',methods=['GET','POST'])
@app.route('/domain/<int:ident>/edit',methods=['GET','POST'])
def edit(ident=None):
    with db() as c: row=c.execute('SELECT * FROM domains WHERE id=?',(ident,)).fetchone() if ident else None
    if ident and not row: abort(404)
    form=dict(row) if row else dict(domain='',label='',selectors='',policy='quarantine')
    if request.method=='POST':
        form.update({k:request.form.get(k,'') for k in ('domain','label','selectors','policy')})
        try:
            name=domain_name(form['domain']); selected=selectors(form['selectors'])
            if selected and any(len(f'{s}._domainkey.{name}')>253 for s in selected.split(',')): raise ValueError('Selector and domain name are too long together.')
            if form['policy'] not in ('none','quarantine','reject'): raise ValueError('Invalid policy.')
            if len(form['label'])>100: raise ValueError('Label exceeds 100 characters.')
            with db() as c:
                if ident:
                    c.execute('UPDATE domains SET domain=?,label=?,selectors=?,policy=?,revision=revision+1,manual_pending=1,checked=NULL,result=NULL WHERE id=?',(name,form['label'],selected,form['policy'],ident))
                else:
                    if c.execute('SELECT COUNT(*) FROM domains').fetchone()[0]>=500: raise ValueError('Initial version limit: 500 domains.')
                    c.execute('INSERT INTO domains(domain,label,selectors,policy,due,manual_pending) VALUES(?,?,?,?,?,1)',(name,form['label'],selected,form['policy'],next_run(time.time(),get_clock(c),selected_zone(c))))
            flash('Saved. Check queued.'); return redirect('/')
        except (ValueError,sqlite3.IntegrityError) as e: flash('Domain already exists.' if isinstance(e,sqlite3.IntegrityError) else str(e))
    return render_template('edit.html',form=form,ident=ident)
@app.post('/domain/<int:ident>/check')
def queue(ident):
    with db() as c: c.execute('UPDATE domains SET manual_pending=1,revision=revision+1 WHERE id=?',(ident,))
    flash('Check queued. Refresh shortly.'); return redirect('/')
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
    return render_template('detail.html',domain=row,history=[dict(x,data=json.loads(x['result'])) for x in hist])

@app.route('/bulk-add', methods=['GET', 'POST'])
def bulk_add():
    import csv, io
    text=request.form.get('domains','')
    selected=request.form.get('selectors','')
    policy=request.form.get('policy','quarantine')
    summary=None
    if request.method=='POST':
        try:
            default_selectors=selectors(selected)
            if policy not in ('none','quarantine','reject'):
                raise ValueError('Invalid minimum DMARC policy.')
            lines=[line for line in text.splitlines() if line.strip()]
            if not lines: raise ValueError('Enter at least one domain.')
            if len(lines)>200: raise ValueError('Import at most 200 domains per batch.')
            pending=[]; seen=set(); errors=[]; repeated=0
            for number,line in enumerate(lines,1):
                try:
                    fields=next(csv.reader([line],strict=True))
                    if not 1<=len(fields)<=2:
                        raise ValueError('Use domain or domain,label on each line.')
                    name=domain_name(fields[0])
                    label=fields[1].strip() if len(fields)==2 else ''
                    if len(label)>100: raise ValueError('Label exceeds 100 characters.')
                    if default_selectors and any(len(f'{s}._domainkey.{name}')>253 for s in default_selectors.split(',')):
                        raise ValueError('Selector and domain combination is too long.')
                    if name in seen: repeated+=1; continue
                    seen.add(name); pending.append((name,label))
                except (ValueError,csv.Error) as exc:
                    errors.append(f'Line {number}: {exc}')
            if errors:
                raise ValueError('Nothing imported. '+ ' | '.join(errors[:10]))
            with db() as c:
                c.execute('BEGIN IMMEDIATE')
                existing={r[0] for r in c.execute('SELECT domain FROM domains')}
                new=[row for row in pending if row[0] not in existing]
                skipped=len(pending)-len(new)+repeated
                if len(existing)+len(new)>500:
                    raise ValueError('Import would exceed the 500-domain limit. Nothing imported.')
                due=next_run(time.time(),get_clock(c),selected_zone(c))
                c.executemany('INSERT INTO domains(domain,label,selectors,policy,due,manual_pending) VALUES(?,?,?,?,?,1)',
                    [(name,label,default_selectors,policy,due) for name,label in new])
            summary=f'Added {len(new)} domains; skipped {skipped} duplicates. Existing domains were not changed. Initial checks queued; daily schedule preserved.'
            text=''
        except ValueError as exc:
            flash(str(exc))
    return render_template('bulk.html',text=text,selected=selected,policy=policy,summary=summary)



@app.post('/check-all')
def check_all():
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        total=c.execute('SELECT COUNT(*) FROM domains').fetchone()[0]
        added=c.execute('UPDATE domains SET manual_pending=1,revision=revision+1 WHERE manual_pending=0').rowcount
    flash(f'{added} domains queued; {total-added} already queued. Daily schedule unchanged. Refresh for results.')
    return redirect('/')


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

if __name__=='__main__':
    mode=sys.argv[1]
    if mode=='init': init()
    elif mode=='worker': worker()
    elif mode=='check':
        _,_,kind,name,selected,policy=sys.argv
        print(json.dumps(dkim_check(name,selected) if kind=='dkim' else record_check(kind,name,policy),default=str))
    elif mode=='worker-health':
        with db() as c: b=c.execute("SELECT value FROM state WHERE key='heartbeat'").fetchone()
        sys.exit(0 if b and time.time()-float(b[0])<180 else 1)
