"""Nameserver metadata; not an email-health signal."""
PROVIDERS={'cloudflare.com':'Cloudflare','azure-dns.com':'Microsoft Azure DNS','azure-dns.net':'Microsoft Azure DNS','azure-dns.org':'Microsoft Azure DNS','azure-dns.info':'Microsoft Azure DNS','domaincontrol.com':'GoDaddy','digitalocean.com':'DigitalOcean','dnsimple.com':'DNSimple'}
def provider_for(names):
    labels=[next((v for k,v in PROVIDERS.items() if n.lower().rstrip('.')==k or n.lower().rstrip('.').endswith('.'+k)),None) for n in names]
    return labels[0] if labels and None not in labels and len(set(labels))==1 else None

def lookup(domain):
    import dns.resolver
    try:
        r=dns.resolver.Resolver(); r.timeout=3; r.lifetime=8
        names=sorted({str(x.target).lower().rstrip('.') for x in r.resolve(domain.rstrip('.')+'.','NS',search=False)})
        return dict(lookup_status='ok' if names else 'unknown',nameservers=names,provider=provider_for(names))
    except Exception:
        return dict(lookup_status='unknown',nameservers=[],provider=None)

def label(data):
    if not isinstance(data,dict) or 'dns_host' not in data: return 'Not checked yet'
    host=data.get('dns_host')
    if not isinstance(host,dict) or host.get('lookup_status')!='ok': return 'Unknown'
    return host.get('provider') or ', '.join(host.get('nameservers',[])) or 'Unknown'
