"""Copy only catalog-pinned raw, never standardized data, from the migration input."""
import hashlib,json,shutil
from pathlib import Path
SOURCE=Path('/seed-input');DEST=Path('/companye-lakehouse')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
catalog=json.loads((SOURCE/'catalog/catalog.json').read_text())
copied=[]
for ds in catalog['datasets']:
    if 'relative_path' not in ds:continue
    rel=Path(ds['relative_path'])
    if rel.is_absolute() or '..' in rel.parts or rel.parts[0]!='raw':raise ValueError('Invalid raw path')
    src=SOURCE/rel;target=DEST/rel
    assert sha(src)==ds['sha256'],str(rel)
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():assert sha(target)==ds['sha256'],'Existing immutable raw differs'
    else:shutil.copyfile(src,target)
    copied.append(ds)
new={'batch_id':catalog['batch_id'],'datasets':copied,'migration':'Only immutable raw imported; Silver is rebuilt from raw.'}
(DEST/'catalog').mkdir(exist_ok=True)
out=DEST/'catalog/catalog.json'
payload=json.dumps(new,ensure_ascii=False,indent=2)
if out.exists():assert json.loads(out.read_text())==new,'Different source batch requires a reviewed new run'
else:out.write_text(payload,encoding='utf8')
print(json.dumps({'status':'RAW_IMPORTED','datasets':len(copied),'batch':new['batch_id'],'bytes':sum((DEST/d['relative_path']).stat().st_size for d in copied)}))
