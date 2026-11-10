from pathlib import Path
import ast, sys, re
root=Path(__file__).resolve().parents[1]
tree=ast.parse((root/'app.py').read_text())
v=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='APP_VERSION' for t in n.targets))
assert re.fullmatch(r'\d+\.\d+\.\d+',v)
start='<!-- BEGIN UPDATE COMMANDS -->'
end='<!-- END UPDATE COMMANDS -->'
section=f'''{start}
## Updating Domain Monitor

Latest documented release: **v{v}**

Run these commands through SSH on the application host, not in a separate development checkout. Adjust the directory if your installation uses another path.

### Check for updates

```bash
cd /opt/domain-monitor
sudo ./scripts/update.sh --check
```

### Install the latest stable release

```bash
cd /opt/domain-monitor
sudo ./scripts/update.sh
```

### Install this release explicitly

```bash
cd /opt/domain-monitor
sudo ./scripts/update.sh --version {v}
```

### Verify the deployment

```bash
cd /opt/domain-monitor
sudo ./scripts/update.sh --check
sudo docker compose ps
sudo docker compose exec -T web python -c 'import app; print(app.APP_VERSION)'
sudo docker compose config --images
sudo docker compose port web 8080
```

Source and running versions should agree, both services should be healthy, and the published binding should match your deployment.

### Manual backup

```bash
cd /opt/domain-monitor
sudo ./scripts/backup.sh
```

Updates briefly interrupt service. Keep an off-host backup. Backups contain sensitive configuration and domain data; never publish them.

These instructions assume a Git-managed installation with updater v0.10.5 or later. Older or script-managed installations need a reviewed migration/bootstrap first. Do not force a checkout over local changes. If an update fails, stop and retain its output and backup path before attempting recovery.

Never share full `docker compose config` output: it can expose credentials. Use `docker compose config --quiet` for validation.

See [the upgrade guide](docs/upgrading.md) for more information.
{end}'''
p=root/'README.md'; text=p.read_text()
if start in text:
    a=text.index(start); b=text.index(end,a)+len(end)
    updated=text[:a]+section+text[b:]
elif re.search(r'^## Updating\s*$',text,re.M):
    updated=re.sub(r'^## Updating\s*\n.*?(?=^## |\Z)',lambda m:section+'\n\n',text,count=1,flags=re.M|re.S)
else:
    updated=text.rstrip()+'\n\n'+section+'\n'
updated=updated.rstrip()+'\n'
if '--check' in sys.argv:
    if updated!=text: raise SystemExit('README is stale: run python3 scripts/update-readme-version.py')
    print('README release commands match APP_VERSION:',v)
else:
    p.write_text(updated)
    print('README commands updated for',v)
