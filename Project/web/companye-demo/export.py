"""Build a small public demo export. Never copy raw data or credentials."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
DIST=HERE/'dist';DIST.mkdir(exist_ok=True)
def read(rel):return json.loads((ROOT/rel).read_text(encoding='utf-8-sig'))
sources=['config/kpi_contract_v1.json','config/generation_v2.json','reports/semantic/baseline.json','reports/semantic/slices.json','reports/semantic/verification.json','reports/powerbi/dashboard/results.json','reports/powerbi/dashboard/verification.json','reports/powerbi/dashboard/kpi-regression.json']
baseline=read(sources[2]);slices=read(sources[3]);verified=read(sources[4])
assert baseline['status']=='PASSED' and slices['status']=='PASSED' and verified['raw_and_both_engines_equal']
checks=baseline['checks']+slices['checks']
assert all(c['iceberg_equal'] and c['raw_reference_equal'] for c in checks)
cases=[]
for i,c in enumerate(checks):
    cases.append(dict(id=str(i),name=c['case'],group=c['group'],context=c['context'],metrics={k:{n:v[n] for n in ['value','quality','reasons','numerator','denominator']} for k,v in c['oracle'].items()},engines_equal=True))
monthly=[]
for c in read(sources[5]):
    if c['id'].startswith('month/'):
        _,engine,month=c['id'].split('/')
        assert 'error' not in c
        monthly.append(dict(engine=engine,month=month,values={k.strip('[]'):v for k,v in c['rows'][0].items()}))
assert len(monthly)==48
chart=read(sources[6]);regression=read(sources[7])
assert chart['status']=='PASSED' and regression['status']=='PASSED_DAX'
groups=[{k:g[k] for k in ['id','name','grain','metrics']} for g in read(sources[0])['requirements']]
assert sum(len(g['metrics']) for g in groups)==47
data=dict(publication=baseline['publication_id'],checked_at=verified['checked_at'],period='2024–2025',groups=groups,cases=cases,monthly=monthly,seeds=read(sources[1]),verification=dict(kpis=47,slices=96,sql_fixture_checks=117,policy_checks=15,chart_checks=chart['value_checks'],dax_checks=regression['metric_checks']),provenance={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources})
(DIST/'data.json').write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf8')
config=json.loads((HERE/'site-config.json').read_text(encoding='utf8'))
assert not config['repositoryUrl'] or config['repositoryUrl'].startswith('https://')
(DIST/'config.json').write_text(json.dumps(config,ensure_ascii=False),encoding='utf8')
print(f'Exported {len(cases)} verified contexts, 47 KPI definitions, {len(monthly)} engine/month results. No raw customer records.')

