"""Verify publication identity and every exported KPI component against evidence."""
from pathlib import Path
from decimal import Decimal
import json,re,hashlib
H=Path(__file__).resolve().parent;R=H.parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
d=read(H/'dist/data.json');checks=[]
def check(name,ok):
    checks.append(dict(name=name,passed=bool(ok)))
    assert ok,name
base=read(R/'reports/semantic/baseline.json');slices=read(R/'reports/semantic/slices.json')
check('publication',d['publication']==base['publication_id']==slices['publication_id'])
check('47_metrics',sum(len(g['metrics']) for g in d['groups'])==47)
check('104_contexts',len(d['cases'])==104)
n=0
for out,src in zip(d['cases'],base['checks']+slices['checks']):
    check('scope_'+out['id'],out['context']==src['context'] and out['group']==src['group'])
    for mid,v in out['metrics'].items():
        for field,value in v.items():
            check(out['id']+'/'+mid+'/'+field,value==src['oracle'][mid][field]);n+=1
monthly=read(R/'reports/powerbi/dashboard/results.json')
for row in d['monthly']:
    src=next(x for x in monthly if x['id']=='month/'+row['engine']+'/'+row['month'])
    check('monthly_'+row['engine']+'/'+row['month'],row['values']=={k.strip('[]'):v for k,v in src['rows'][0].items()})
check('48_monthly_rows',len(d['monthly'])==48)
for path,sha in d['provenance'].items():
    check('sha_'+path,sha==hashlib.sha256((R/path).read_bytes()).hexdigest())
html=(H/'dist/index.html').read_text(encoding='utf8')
check('noindex',bool(re.search(r'name="robots" content="noindex, nofollow, noarchive"',html)))
check('neutral_copy',not any(x in html.lower() for x in ['giảng viên','nhà tuyển dụng']))
check('no_sitemap',not list((H/'dist').glob('*sitemap*')))
check('repository_config_matches_source',read(H/'dist/config.json')['repositoryUrl']==read(H/'site-config.json')['repositoryUrl'])
check('repository_points_to_companye',read(H/'dist/config.json')['repositoryUrl']=='https://github.com/tranphu1508/DE-CaseCompanyE')
check('no_raw_or_credentials',set(p.name for p in (H/'dist').iterdir())=={'index.html','style.css','app.js','data.json','config.json','robots.txt','_headers'})
for name in ['data.json','config.json','index.html','app.js']:
    text=(H/'dist'/name).read_text(encoding='utf8').lower()
    check('no_secret_markers_'+name,not any(x in text for x in ['password','access_token','api_key','c:\\\\users','d:\\\\study']))
result=dict(status='PASSED_STATIC_EXPORT',checks=len(checks),metric_component_comparisons=n,monthly_rows=48,publication=d['publication'],limitations=['Does not run UI; browser interaction checks are recorded separately.','noindex is a crawler directive, not access control.'],files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (H/'dist').iterdir()})
(H/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(result,ensure_ascii=False))

