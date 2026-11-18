from pathlib import Path
import ast,re
root=Path(__file__).resolve().parents[1]
tree=ast.parse((root/'app.py').read_text())
v=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='APP_VERSION' for t in n.targets))
if not re.fullmatch(r'\d+\.\d+\.\d+',v):
    raise SystemExit('Invalid APP_VERSION')
start='<!-- BEGIN UPDATE COMMANDS -->'
end='<!-- END UPDATE COMMANDS -->'
section=(start+'\n### Current release commands\n\nLatest documented release: **v'+v+'**\n\n```bash\ncd /opt/domain-monitor\nsudo ./scripts/update.sh --check\nsudo ./scripts/update.sh --version '+v+'\nsudo docker compose ps\nsudo docker compose exec -T web python -c \'import app; print(app.APP_VERSION)\'\nsudo docker compose config --images\nsudo docker compose port web 8080\n```\n'+end)
p=root/'README.md'
text=p.read_text()
if start not in text or end not in text:
    raise SystemExit('README update markers missing')
p.write_text(text[:text.index(start)]+section+text[text.index(end)+len(end):])
