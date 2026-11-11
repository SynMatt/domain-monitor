"""Bounded authoritative DNS evidence; not a separate health signal."""
import time
import dns.exception
import dns.flags
import dns.message
import dns.query
import dns.rcode
import dns.resolver

MAX_NS = 8
TIMEOUT = 3.0
LIFETIME = 10.0


def resolver():
    value = dns.resolver.Resolver(configure=True)
    value.timeout = TIMEOUT
    value.lifetime = LIFETIME
    value.retry_servfail = True
    value.use_edns(edns=0, payload=1232)
    return value


def _text_records(answer):
    records = []
    for item in answer:
        if hasattr(item, 'strings'):
            records.append(b''.join(item.strings).decode('utf-8', errors='replace'))
        else:
            records.append(item.to_text())
    return sorted(set(records))


def _recursive(name, record_type):
    start = time.monotonic()
    current = resolver()
    try:
        answer = current.resolve(name, record_type, search=False, raise_on_no_answer=False)
        records = _text_records(answer) if answer.rrset else []
        ttl = answer.rrset.ttl if answer.rrset else None
        return {
            'status': 'ok', 'records': records, 'ttl': ttl,
            'elapsed_ms': round((time.monotonic() - start) * 1000),
            'servers': list(current.nameservers),
        }
    except dns.resolver.NXDOMAIN:
        return {'status': 'nxdomain', 'records': [], 'servers': list(current.nameservers)}
    except dns.resolver.NoAnswer:
        return {'status': 'no_answer', 'records': [], 'servers': list(current.nameservers)}
    except dns.resolver.NoNameservers as error:
        return {'status': 'no_nameservers', 'records': [], 'error': str(error)[:300], 'servers': list(current.nameservers)}
    except dns.exception.Timeout as error:
        return {'status': 'timeout', 'records': [], 'error': str(error)[:300], 'servers': list(current.nameservers)}
    except Exception as error:
        return {'status': 'error', 'records': [], 'error': f'{type(error).__name__}: {error}'[:300], 'servers': list(current.nameservers)}


def _authoritative_servers(domain):
    current = resolver()
    answer = current.resolve(domain.rstrip('.') + '.', 'NS', search=False)
    return sorted({str(item.target).lower().rstrip('.') for item in answer})[:MAX_NS]


def _addresses(host):
    current = resolver()
    values = []
    for record_type in ('A', 'AAAA'):
        try:
            answer = current.resolve(host.rstrip('.') + '.', record_type, search=False)
            values.extend(str(item) for item in answer)
        except Exception:
            pass
    return values


def _direct(server, name, record_type):
    query = dns.message.make_query(name, record_type, use_edns=True, payload=1232)
    start = time.monotonic()
    response = dns.query.udp(query, server, timeout=TIMEOUT)
    if response.flags & dns.flags.TC:
        response = dns.query.tcp(query, server, timeout=TIMEOUT)
    records = []
    ttl = None
    for rrset in response.answer:
        if rrset.rdtype == dns.rdatatype.from_text(record_type):
            ttl = rrset.ttl if ttl is None else min(ttl, rrset.ttl)
            for item in rrset:
                if hasattr(item, 'strings'):
                    records.append(b''.join(item.strings).decode('utf-8', errors='replace'))
                else:
                    records.append(item.to_text())
    return {
        'rcode': dns.rcode.to_text(response.rcode()),
        'records': sorted(set(records)),
        'ttl': ttl,
        'elapsed_ms': round((time.monotonic() - start) * 1000),
    }


def query_evidence(domain, name, record_type):
    recursive = _recursive(name, record_type)
    evidence = {
        'query_name': name.rstrip('.') + '.',
        'record_type': record_type,
        'recursive': recursive,
        'authoritative': [],
        'consensus': 'unavailable',
        'recursive_matches_authoritative': None,
    }
    try:
        nameservers = _authoritative_servers(domain)
    except Exception as error:
        evidence['authoritative_error'] = f'{type(error).__name__}: {error}'[:300]
        return evidence
    groups = []
    for nameserver in nameservers:
        item = {'nameserver': nameserver, 'status': 'unavailable'}
        last_error = None
        for address in _addresses(nameserver):
            try:
                result = _direct(address, evidence['query_name'], record_type)
                item.update(result, address=address, status='ok')
                break
            except Exception as error:
                last_error = error
        if item['status'] != 'ok' and last_error:
            item['error'] = f'{type(last_error).__name__}: {last_error}'[:300]
        evidence['authoritative'].append(item)
        if item['status'] == 'ok':
            groups.append(tuple(item.get('records', [])))
    if groups:
        unique = set(groups)
        evidence['consensus'] = 'yes' if len(unique) == 1 else 'inconsistent'
        if len(unique) == 1:
            authoritative_records = list(groups[0])
            evidence['authoritative_records'] = authoritative_records
            evidence['recursive_matches_authoritative'] = (
                recursive.get('status') == 'ok' and
                recursive.get('records', []) == authoritative_records
            )
    return evidence


def lookup(domain, selectors=''):
    domain = domain.rstrip('.').lower()
    queries = {
        'spf': query_evidence(domain, domain, 'TXT'),
        'dmarc': query_evidence(domain, '_dmarc.' + domain, 'TXT'),
    }
    dkim = {}
    for selector in [x for x in selectors.split(',') if x][:10]:
        dkim[selector] = query_evidence(
            domain, f'{selector}._domainkey.{domain}', 'TXT'
        )
    queries['dkim'] = dkim
    disagreements = []
    for kind, item in queries.items():
        values = item.values() if kind == 'dkim' else [item]
        for value in values:
            if value.get('consensus') == 'inconsistent':
                disagreements.append(f'{kind}: authoritative nameservers disagree')
            elif value.get('recursive_matches_authoritative') is False:
                disagreements.append(f'{kind}: recursive result differs from authoritative DNS')
    return {'status': 'ok', 'queries': queries, 'warnings': disagreements}
