"""Export aggregate evidence from historical A and independent B, never raw records."""
from pathlib import Path
from decimal import Decimal
import hashlib,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];DIST=HERE/'dist'
sources={}
def read(rel):
    p=ROOT/rel;sources[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
    return json.loads(p.read_text(encoding='utf-8-sig'))

groups=[{k:g[k] for k in ['id','name','grain','metrics']} for g in read('config/kpi_contract_v1.json')['requirements']]
seeds=read('config/generation_v2.json')
assert sum(len(g['metrics']) for g in groups)==47
engine_sources={
    'oracle':dict(sql='semantic',bi='powerbi/dashboard',chart='verification.json',dax='kpi-regression.json',label='Oracle Warehouse · mốc đối chứng A',historical=True),
    'iceberg':dict(sql='lakehouse-b',bi='bi-migration',chart='chart-verification.json',dax='dax-verification.json',label='Lakehouse B · độc lập',historical=False),
}
engines={};by_engine={};monthly=[]
for engine,paths in engine_sources.items():
    baseline=read('reports/'+paths['sql']+'/baseline.json');slices=read('reports/'+paths['sql']+'/slices.json')
    verified=read('reports/'+paths['sql']+'/verification.json')
    assert baseline['status']==slices['status']=='PASSED'
    pid=baseline['publication_id'];assert pid==slices['publication_id']==verified['publication_id']
    if engine=='oracle':assert verified['raw_and_both_engines_equal']
    else:
        assert verified['status']=='PASSED' and verified['raw_reference_equal'] and verified['historical_oracle_equal']
        export=read('reports/bi-migration/export.json');assert export['publication_id']==pid and export['engines']==['iceberg']
    chart=read('reports/'+paths['bi']+'/'+paths['chart']);dax=read('reports/'+paths['bi']+'/'+paths['dax'])
    assert chart['status']=='PASSED' and dax['status']=='PASSED_DAX'
    if engine=='iceberg':assert chart['publication_id']==dax['publication_id']==pid
    checks=baseline['checks']+slices['checks'];assert len(checks)==104
    by_engine[engine]={(c['case'],c['group'],json.dumps(c['context'],sort_keys=True)):c for c in checks}
    assert len(by_engine[engine])==104
    chart_results=read('reports/'+paths['bi']+('/results.json' if engine=='oracle' else '/chart-results.json'))
    rows=[]
    for c in chart_results:
        if c['id'].startswith('month/'+engine+'/'):
            assert 'error' not in c and len(c['rows'])==1
            rows.append(dict(engine=engine,publication=pid,month=c['id'].split('/')[2],values={k.strip('[]'):v for k,v in c['rows'][0].items()}))
    assert len(rows)==24;monthly.extend(rows)
    engines[engine]=dict(label=paths['label'],historical=paths['historical'],publication=pid,checked_at=verified['checked_at'],external_warnings=12,
                         verification=dict(kpis=47,slices=96,dax_checks=dax['metric_checks'],chart_checks=chart['value_checks'],
                                           dax_queries=dax['queries'],chart_queries=chart['queries']))
assert set(by_engine['oracle'])==set(by_engine['iceberg'])
fields=['value','quality','reasons','numerator','denominator'];cases=[]
for i,(key,c) in enumerate(by_engine['oracle'].items()):
    metrics={eng:{mid:{n:v[n] for n in fields} for mid,v in by_engine[eng][key][eng].items()} for eng in engines}
    assert set(metrics['oracle'])==set(metrics['iceberg'])
    equal=all(all((Decimal(a[n])==Decimal(b[n]) if a[n] is not None and b[n] is not None else a[n]==b[n]) for n in ['value','numerator','denominator'])
              and a['quality']==b['quality'] and a['reasons']==b['reasons'] for mid,a in metrics['oracle'].items() for b in [metrics['iceberg'][mid]])
    assert equal,key
    cases.append(dict(id=str(i),name=c['case'],group=c['group'],context=c['context'],metrics_by_engine=metrics,engines_equal=equal))
data=dict(schema_version=2,default_engine='iceberg',engines=engines,period='2024–2025',groups=groups,cases=cases,monthly=monthly,seeds=seeds,provenance=sources,
          limitations=['Oracle is an immutable historical reference; it was not rerun during B migration.',
                       'Desktop excludes two weather contexts and one variable-assessment context; web KPI tables use SQL evidence for all 104 contexts.',
                       'Monthly values come from separately verified Power BI imports; the web is a static snapshot, not a live query or benchmark.'])
(DIST/'data.json').write_bytes(json.dumps(data,ensure_ascii=False,separators=(',',':')).encode())
config=json.loads((HERE/'site-config.json').read_text(encoding='utf8'))
assert not config['repositoryUrl'] or config['repositoryUrl'].startswith('https://')
(DIST/'config.json').write_bytes(json.dumps(config,ensure_ascii=False).encode())
print('Exported 104 contexts x 2 separately attributed engines, 47 KPI definitions, 48 monthly rows.')
