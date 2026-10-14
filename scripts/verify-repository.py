"""Offline packaging checks; does not claim to rerun database/Power BI acceptance."""
from pathlib import Path
import ast, hashlib, json, re, sys
ROOT=Path(__file__).resolve().parents[1]
inventory=json.loads((ROOT/'evidence/assembly-inventory.json').read_text(encoding='utf-8'))
adaptations=json.loads((ROOT/'evidence/repository-adaptations.json').read_text(encoding='utf-8'))
errors=[];count=0
for entry in inventory['included']:
    p=ROOT/entry['path'];expected=adaptations.get(entry['path'],{}).get('sha256',entry['sha256'])
    if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=expected:errors.append('Copy checksum: '+entry['path'])
    count+=1
parsed=0
for p in ROOT.rglob('*.py'):
    if '.work' in p.parts or '.git' in p.parts:continue
    try:ast.parse(p.read_text(encoding='utf-8-sig'));parsed+=1
    except SyntaxError:errors.append('Syntax: '+str(p.relative_to(ROOT)))
required=['Project/CompanyE_Mo_ta_case.md','Project/docs/CompanyE_KPI_Specification.md','Project/docs/CompanyE_Bus_Matrix.pdf','Project/docs/CompanyE_Source_Target_Mapping.md','Project/reports/semantic/verification.json','Project/reports/publication/verification.json','Project/web/companye-demo/dist/index.html']
for name in required:
    if not (ROOT/name).is_file():errors.append('Missing: '+name)
# Obvious credential signatures; fixture-only test password is intentionally public.
pattern=re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')
scanned=0
for p in ROOT.rglob('*'):
    if not p.is_file() or any(x in p.parts for x in ['.work','.git','__pycache__']):continue
    rel=p.relative_to(ROOT).as_posix()
    if '.secrets' in p.parts or p.name in ['.env','.env.analytics']:errors.append('Private path: '+rel)
    if p.stat().st_size>50*1024**2:errors.append('Large Git blob: '+rel)
    if pattern.search(p.read_bytes()):errors.append('Credential signature: '+rel)
    scanned+=1
result={'status':'FAILED' if errors else 'PASSED','copied_file_checksums':count,'python_files_parsed':parsed,'files_scanned':scanned,'errors':errors,'scope':'Offline assembly integrity only; historical integration results are retained separately.'}
print(json.dumps(result,indent=2,ensure_ascii=False))
if '--save' in sys.argv:(ROOT/'evidence/repository-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
sys.exit(bool(errors))
