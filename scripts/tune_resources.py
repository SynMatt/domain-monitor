#!/usr/bin/env python3
"""Choose CONTAINER_CPUS and CHECK_WORKERS that fit this host and save them in .env.

RESOURCE_TUNING='auto' (default): both values follow the host.
RESOURCE_TUNING='manual': your values are kept, except CONTAINER_CPUS is lowered
if it is higher than the host's cores, because Docker refuses to start otherwise.
On Hyper-V (--ignore-memory) memory is not used: Dynamic Memory makes the
guest reading change from minute to minute, so only CPU cores decide.
Exit codes: 0 = no change, 3 = .env changed, 1 = error.
"""
import argparse,os,re,sys,time
from pathlib import Path
GIB=1024**3
MAX_CPUS=4            # measured: 4 cores already checks 164 domains in about 1.2 minutes
SMALL_HOST_MEMORY=3*GIB
def recommend(host_cpus,host_memory,ignore_memory=False):
    host_cpus=max(1,int(host_cpus))
    cpus=min(host_cpus,MAX_CPUS)
    small_memory=not ignore_memory and host_memory<SMALL_HOST_MEMORY
    workers=2 if host_cpus<2 or small_memory else 4
    return {'CONTAINER_CPUS':str(cpus),'CHECK_WORKERS':str(workers)}
def parse(lines):
    values={}
    for line in lines:
        match=re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=(.*)$',line.strip())
        if match: values[match.group(1)]=match.group(2).strip().strip('\'"')
    return values
def plan(values,host_cpus,host_memory,ignore_memory=False):
    """Return (mode, updates). Updates hold only keys whose value should change."""
    host_cpus=max(1,int(host_cpus))
    mode=values.get('RESOURCE_TUNING','auto').strip().lower()
    if mode not in ('auto','manual'): mode='auto'
    if mode=='auto':
        target=recommend(host_cpus,host_memory,ignore_memory)
    else:
        target={}
        try: current=float(values.get('CONTAINER_CPUS',''))
        except ValueError: current=0
        if not 0<current<=host_cpus:
            target['CONTAINER_CPUS']=str(min(host_cpus,MAX_CPUS))
    updates={k:v for k,v in target.items() if values.get(k)!=v}
    if 'RESOURCE_TUNING' not in values: updates['RESOURCE_TUNING']=mode
    return mode,updates
def rewrite(lines,updates):
    out=[]; written=set()
    for line in lines:
        key=line.split('=',1)[0].strip() if '=' in line else None
        if key in updates:
            if key not in written: out.append(f"{key}='{updates[key]}'"); written.add(key)
            continue
        out.append(line)
    out.extend(f"{k}='{v}'" for k,v in updates.items() if k not in written)
    return out
def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env',default='.env')
    parser.add_argument('--cpus',type=int,required=True)
    parser.add_argument('--mem',type=int,required=True,help='host memory in bytes')
    parser.add_argument('--dry-run',action='store_true')
    parser.add_argument('--ignore-memory',action='store_true',help='Hyper-V: decide from CPU cores only')
    args=parser.parse_args(argv)
    path=Path(args.env)
    if not path.is_file(): print(f'No {path} found.',file=sys.stderr); return 1
    lines=path.read_text().splitlines()
    values=parse(lines)
    mode,updates=plan(values,args.cpus,args.mem,args.ignore_memory)
    print(f'Host: {max(1,args.cpus)} CPU core(s), {args.mem/GIB:.1f} GiB memory · tuning mode: {mode}')
    if args.ignore_memory:
        print('  Hyper-V detected: memory reading ignored (Dynamic Memory changes it); using CPU cores only.')
    for key in ('CONTAINER_CPUS','CHECK_WORKERS'):
        old=values.get(key,'(not set)'); new=updates.get(key,old)
        print(f'  {key:<15} {old} -> {new}' if new!=old else f'  {key:<15} {old} (unchanged)')
    if not updates: print('Settings already fit this host.'); return 0
    if args.dry_run: print('Dry run: .env not changed.'); return 0
    info=path.stat()
    backup=path.with_name(f'.env.backup-tune-{time.strftime("%Y%m%d-%H%M%S")}')
    backup.write_text(path.read_text()); os.chmod(backup,0o600)
    temp=path.with_name('.env.tune-new')
    temp.write_text('\n'.join(rewrite(lines,updates))+'\n'); os.chmod(temp,0o600)
    try: os.chown(temp,info.st_uid,info.st_gid)
    except PermissionError: pass
    os.replace(temp,path)
    print(f'.env updated. Previous copy: {backup.name}')
    return 3
if __name__=='__main__': sys.exit(main())
