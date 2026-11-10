"""Database-backed DNS provider display mappings; no page-load DNS requests."""
import json
import re
from flask import g, request, render_template, redirect, flash, abort

KEY = 'dns_provider_mappings_v1'
BUILTINS = {'dnspackage.com': 'Crazy Domains', 'hosting-cloud.net': 'DreamIT Host'}

def normal(value):
    return str(value).strip().lower().rstrip('.')

def match(name, suffix):
    return name == suffix or name.endswith('.' + suffix)

def provider(name, custom, builtins):
    name = normal(name)
    # User mappings take precedence; longest suffix wins within each directory.
    for directory in (custom, builtins):
        for suffix in sorted(directory, key=len, reverse=True):
            if match(name, suffix):
                return directory[suffix]
    return None

def fallback(name):
    name = normal(name)
    # Remove only a conventional leading nameserver label, not arbitrary labels.
    return re.sub(r'^ns[0-9]*\.', '', name)

def display(data, custom, builtins, legacy):
    if not isinstance(data, dict) or 'dns_host' not in data:
        return 'Not checked yet'
    host = data.get('dns_host')
    if not isinstance(host, dict) or host.get('lookup_status') != 'ok':
        return 'Unknown'
    names = sorted({normal(n) for n in host.get('nameservers', []) if isinstance(n, str) and n.strip()})
    if not names:
        return legacy(data)
    labels = [provider(n, custom, builtins) for n in names]
    known = {x for x in labels if x}
    if len(known) > 1:
        return 'Multiple providers'
    if labels and all(labels):
        return labels[0]
    return ', '.join(sorted({fallback(n) for n in names}))

def register(m):
    builtins = dict(m.dns_host_lookup.__globals__.get('PROVIDERS', {}))
    builtins.update(BUILTINS)
    legacy = m.dns_host_label

    def read(c):
        row = c.execute('SELECT value FROM state WHERE key=?', (KEY,)).fetchone()
        return json.loads(row[0]) if row else {}

    def current():
        if not hasattr(g, 'dns_provider_directory'):
            with m.db() as c:
                g.dns_provider_directory = read(c)
        return g.dns_provider_directory

    def label(data):
        return display(data, current(), builtins, legacy)

    m.app.jinja_env.globals['dns_host_label'] = label

    @m.app.route('/settings/dns-providers', methods=['GET', 'POST'])
    def dns_providers():
        if request.method == 'POST':
            try:
                action = request.form.get('action', '')
                suffix = m.domain_name(request.form.get('suffix', ''))
                if len(suffix.split('.')) < 2:
                    raise ValueError('Enter a nameserver domain suffix.')
                with m.db() as c:
                    c.execute('BEGIN IMMEDIATE')
                    mappings = read(c)
                    if action == 'delete':
                        if request.form.get('confirm') != 'DELETE':
                            raise ValueError('Type DELETE to confirm removal.')
                        if suffix not in mappings:
                            raise ValueError('Mapping no longer exists.')
                        del mappings[suffix]
                    elif action in ('add', 'edit'):
                        name = request.form.get('name', '').strip()
                        if not name or len(name) > 80 or any(ord(x) < 32 or x in '<>' for x in name):
                            raise ValueError('Enter a plain-text provider name of 1 to 80 characters.')
                        if action == 'add' and suffix in mappings:
                            raise ValueError('Mapping already exists; edit it below.')
                        if action == 'edit' and suffix not in mappings:
                            raise ValueError('Mapping no longer exists.')
                        if action == 'add' and len(mappings) >= 500:
                            raise ValueError('Maximum 500 custom mappings.')
                        mappings[suffix] = name
                    else:
                        raise ValueError('Invalid action.')
                    c.execute('INSERT OR REPLACE INTO state(key,value) VALUES(?,?)',
                              (KEY, json.dumps(mappings, sort_keys=True)))
                flash('DNS provider mapping saved. Cached cards update immediately; DNS and check schedules are unchanged.')
                return redirect('/settings/dns-providers')
            except ValueError as error:
                flash(str(error))
        with m.db() as c:
            mappings = read(c)
            rows = c.execute('SELECT domain,result FROM domains WHERE result IS NOT NULL').fetchall()
        unknown = {}
        for row in rows:
            try:
                host = json.loads(row['result']).get('dns_host', {})
                if host.get('lookup_status') != 'ok':
                    continue
                for ns in host.get('nameservers', []):
                    ns = normal(ns)
                    if not provider(ns, mappings, builtins):
                        unknown.setdefault(ns, set()).add(row['domain'])
            except (ValueError, TypeError, AttributeError):
                continue
        return render_template('dns_providers.html', mappings=sorted(mappings.items()),
                               builtins=sorted(builtins.items()),
                               unknown=[(ns, fallback(ns), len(domains)) for ns, domains in sorted(unknown.items())])
