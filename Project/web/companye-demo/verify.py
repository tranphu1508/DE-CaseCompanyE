"""Verify both payloads against their own immutable evidence, not against each other only."""
from pathlib import Path
import json,re,hashlib
H=Path(__file__).resolve().parent;R=H.parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
d=read(H/'dist/data.json');checks=[]
def check(name,ok):
    checks.append(dict(name=name,passed=bool(ok)))
    assert ok,name
check('schema_v2',d['schema_version']==2)
check('default_B',d['default_engine']=='iceberg')
check('two_engines',set(d['engines'])=={'oracle','iceberg'})
check('47_metrics',sum(len(g['metrics']) for g in d['groups'])==47)
check('104_contexts',len(d['cases'])==104 and len({c['id'] for c in d['cases']})==104)
n=0
for engine,sql,bi in [('oracle','semantic','powerbi/dashboard'),('iceberg','lakehouse-b','bi-migration')]:
    base=read(R/f'reports/{sql}/baseline.json');slices=read(R/f'reports/{sql}/slices.json');v=read(R/f'reports/{sql}/verification.json')
    srcs={(c['case'],c['group'],json.dumps(c['context'],sort_keys=True)):c for c in base['checks']+slices['checks']}
    source=d['engines'][engine];pid=base['publication_id']
    check(engine+'/publication',source['publication']==pid==slices['publication_id']==v['publication_id'])
    check(engine+'/historical',source['historical']==(engine=='oracle'))
    check(engine+'/checked_at',source['checked_at']==v['checked_at'])
    for out in d['cases']:
        key=(out['name'],out['group'],json.dumps(out['context'],sort_keys=True));check(engine+'/scope/'+out['id'],key in srcs)
        src=srcs[key][engine];metrics=out['metrics_by_engine'][engine]
        check(engine+'/metrics/'+out['id'],set(metrics)==set(src))
        for mid,m in metrics.items():
            check(engine+'/fields/'+out['id']+'/'+mid,set(m)=={'value','quality','reasons','numerator','denominator'})
            for field,value in m.items():check(engine+'/'+out['id']+'/'+mid+'/'+field,value==src[mid][field]);n+=1
    monthly=read(R/f'reports/{bi}'/('results.json' if engine=='oracle' else 'chart-results.json'))
    rows=[r for r in d['monthly'] if r['engine']==engine]
    check(engine+'/24_months',len(rows)==24 and len({r['month'] for r in rows})==24)
    for row in rows:
        src=next(x for x in monthly if x['id']=='month/'+engine+'/'+row['month'])
        check(engine+'/month/'+row['month'],row['publication']==pid and row['values']=={k.strip('[]'):v for k,v in src['rows'][0].items()})
    chart=read(R/f'reports/{bi}'/('verification.json' if engine=='oracle' else 'chart-verification.json'))
    dax=read(R/f'reports/{bi}'/('kpi-regression.json' if engine=='oracle' else 'dax-verification.json'))
    check(engine+'/certified',chart['status']=='PASSED' and dax['status']=='PASSED_DAX')
    check(engine+'/counts',source['verification']==dict(kpis=47,slices=96,dax_checks=dax['metric_checks'],chart_checks=chart['value_checks'],dax_queries=dax['queries'],chart_queries=chart['queries']))
check('distinct_publications',d['engines']['oracle']['publication']!=d['engines']['iceberg']['publication'])
check('48_monthly_rows',len(d['monthly'])==48)
required={'reports/lakehouse-b/baseline.json','reports/lakehouse-b/slices.json','reports/bi-migration/chart-results.json','reports/bi-migration/dax-verification.json','reports/semantic/baseline.json','reports/powerbi/dashboard/results.json'}
check('required_provenance',required<=set(d['provenance']))
for path,sha in d['provenance'].items():check('sha_'+path,sha==hashlib.sha256((R/path).read_bytes()).hexdigest())
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
result=dict(status='PASSED_STATIC_EXPORT',checks=len(checks),metric_component_comparisons=n,monthly_rows=48,publications={k:v['publication'] for k,v in d['engines'].items()},limitations=['Does not run UI; browser interaction checks are recorded separately.','noindex is a crawler directive, not access control.'],files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (H/'dist').iterdir()})
(H/'verification.json').write_bytes(json.dumps(result,ensure_ascii=False,indent=2).encode())
print(json.dumps({k:v for k,v in result.items() if k!='files'},ensure_ascii=False))
