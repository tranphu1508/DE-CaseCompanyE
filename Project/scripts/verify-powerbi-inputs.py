"""Verify Import integrity/relationships and enrichments against certified SQL.
This deliberately does not claim to execute DAX or validate a rendered report.
"""
from pathlib import Path
from decimal import Decimal as D
import csv,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf8'))
manifest=read(ROOT/'reports/powerbi/export.json');pid=manifest['publication_id']
bundle=ROOT/'reports/powerbi/imports'/pid;data=ROOT/'powerbi/data'/pid
def rows(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
allrows={t['entity']:rows(bundle/t['filename']) for t in manifest['tables']}
for t in manifest['tables']:
    assert hashlib.sha256((bundle/t['filename']).read_bytes()).hexdigest()==t['sha256']
    assert len(allrows[t['entity']])==t['import_rows']
model=read(ROOT/'powerbi/CompanyE.SemanticModel/model.bim')['model']
allrows.update({n:rows(data/(n+'.csv')) for n in ['F01','F12','Engine','Period','KPI','QA']})
for rel in model['relationships']:
    target=[r[rel['toColumn']] for r in allrows[rel['toTable']]]
    assert len(target)==len(set(target)),rel
    assert {r[rel['fromColumn']] for r in allrows[rel['fromTable']]} <= set(target),rel
domains={'site':('D02','site_key','site_id'),'hotel':('D03','hotel_key','hotel_id'),'stars':('D03','hotel_key','stars'),'channel':('D05','channel_key','channel_code'),'supplier':('D14','supplier_key','supplier_id'),'item':('D15','item_key','item_id')}
checks=[];skips=[]
for phase in ['baseline','slices']:
    for case in read(ROOT/f'reports/semantic/{phase}.json')['checks']:
        if case['group'] not in ('B03','B06'):continue
        ctx=case['context'];g=case['group']
        if ctx.get('assessment','2025-12-31')!='2025-12-31':
            skips.append(dict(case=case['case'],reason='The first report fixes assessment at 2025-12-31; no assessment slicer is exposed.'));continue
        s=int(ctx.get('start','2024-01-01').replace('-',''));e=int(ctx.get('end','2026-01-01').replace('-',''))
        for engine in ['oracle','iceberg']:
            rs=[r for r in allrows['F01' if g=='B03' else 'F12'] if r['engine']==engine]
            for k,v in ctx.get('filters',{}).items():
                dim,key,col=domains[k];valid={r[key] for r in allrows[dim] if r[col]==str(v)};rs=[r for r in rs if r[key] in valid]
            day='departure_date_key' if g=='B03' else 'expected_date_key'
            rs=[r for r in rs if s<=int(r[day])<e and (r['status']=='COMPLETED' if g=='B03' else int(r[day])<=20251231)]
            total=lambda col:sum((D(r[col]) for r in rs),D(0))
            if g=='B03':
                b,t,v,room=map(total,['cross_bought','cross_ticket','cross_rental','customer_due_vnd'])
                actual={1:(b,1),2:(b,len(rs)),3:(t,1),4:(v,1),5:(room+t+v,1)}
            else:
                o,a,r,l,otif=map(total,['ordered_qty','received_accepted','received_rejected','received_late','otif'])
                actual={1:(o,1),2:(a,1),3:(r,1),4:(l,1),5:(a,o),6:(r,a+r),7:(otif,len(rs))}
            assert case['iceberg_equal']
            for mid,expected in case['oracle'].items():
                n,d=actual[int(mid[-2:])]
                assert n==D(expected['diagnostic_accepted_numerator']),(phase,case['case'],mid,n,expected)
                assert d==D(expected['diagnostic_accepted_denominator']),(phase,case['case'],mid,d,expected)
                checks.append(dict(phase=phase,case=case['case'],engine=engine,metric=mid,numerator=str(n),denominator=str(d)))
result=dict(status='PASSED_IMPORT_INPUT_CHECKS',publication_id=pid,original_import_rows=sum(t['import_rows'] for t in manifest['tables']),csv_hashes=len(manifest['tables']),relationships=len(model['relationships']),enrichment_metric_checks=len(checks),checks=checks,excluded_contexts=skips,desktop_refresh='NOT_RUN',dax_execution='NOT_RUN',ui_tests='NOT_RUN')
(ROOT/'reports/powerbi/input-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(result['status'],result['csv_hashes'],'hashes',result['relationships'],'relationships',len(checks),'enrichment checks')
