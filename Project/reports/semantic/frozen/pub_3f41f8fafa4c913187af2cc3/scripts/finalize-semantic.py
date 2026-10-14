"""Seal the 47-KPI acceptance with independent raw and cross-engine evidence."""
from pathlib import Path
from datetime import datetime,timezone
from decimal import Decimal
import hashlib,importlib.util,json,sys

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/semantic'
sys.path.insert(0,str(ROOT/'src'))
from semantic.queries import IDS,ALLOWED,VERSION,build
spec=importlib.util.spec_from_file_location('publication_launcher',ROOT/'scripts/publication.py')
pub=importlib.util.module_from_spec(spec);spec.loader.exec_module(pub)
def read(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf8')

baseline=read(OUT/'baseline.json');slices=read(OUT/'slices.json');fixtures=read(OUT/'fixtures.json')
for report in [baseline,slices,fixtures]:
    assert report['status']=='PASSED'
    for rel,digest in report['code_sha256'].items():assert sha(ROOT/rel)==digest,'Code changed since test '+rel
assert baseline['publication_id']==slices['publication_id'];pid=baseline['publication_id']
assert baseline['metric_comparisons']==47
assert {m for c in baseline['checks'] for m in c['selected']}==set(IDS)
assert fixtures['sql_fixture_cases']==20 and fixtures['metric_checks']==117 and len(fixtures['policy_checks'])==15
first=read(OUT/'baseline-first.json')
assert [(c['group'],c['oracle']) for c in first['checks']]==[(c['group'],c['oracle']) for c in baseline['checks']],'Repeated read changed KPI results'

publication=read(ROOT/'reports/publication/manifest.json')
assert publication['publication_id']==pid
catalog=read(ROOT/'lake/v2/catalog/catalog.json')
assert sha(ROOT/'lake/v2/catalog/catalog.json')==publication['source_catalog_sha256']
for ds in catalog['datasets']:assert sha(ROOT/'lake/v2'/ds['relative_path'])==ds['sha256']
for phase in ['dimension-etl','fact-etl']:
    evidence=read(ROOT/'reports'/phase/'verification.json')
    for rel,digest in evidence['evidence_sha256'].items():assert sha(ROOT/rel)==digest,rel
frozen_etl=read(ROOT/'reports/fact-etl/frozen-code.json')
for rel,digest in frozen_etl['sha256'].items():assert sha(ROOT/rel)==digest,rel

# Independent consistency relations, beyond equality of Oracle and Iceberg.
relations=[];base={m:v for c in baseline['checks'] for m,v in c['oracle'].items()}
by_case={(c['case'],c['group']):c for c in slices['checks']}
for mid in IDS:
    parts=[by_case[('site_'+site,mid[:3])]['oracle'][mid] for site in ['SP','DN','DL','PQ']]
    assert sum(Decimal(p['diagnostic_accepted_numerator']) for p in parts)==Decimal(base[mid]['diagnostic_accepted_numerator']),mid
    ratio=build(mid[:3],{},[mid])[2][mid]
    if ratio:assert sum(Decimal(p['diagnostic_accepted_denominator']) for p in parts)==Decimal(base[mid]['diagnostic_accepted_denominator']),mid
    relations.append(dict(metric=mid,site_numerators_roll_up=True,site_denominators_roll_up=ratio))
assert base['B01.02']['value']==base['B08.03']['value']
assert Decimal(base['B02.06']['value'])==Decimal(base['B02.02']['value'])+Decimal(base['B02.04']['value'])-Decimal(base['B02.05']['value'])
assert Decimal(base['B03.05']['value'])==Decimal(base['B02.02']['value'])+Decimal(base['B03.03']['value'])+Decimal(base['B03.04']['value'])
save(OUT/'reconciliation.json',dict(status='PASSED',site_rollup=relations,available_room_identity=True,retained_value_identity=True,cross_sell_value_identity=True,repeated_read_unchanged=True))

mid=pub.svc.container('metadata')
sql="""SELECT json_build_object('active',(SELECT publication_id FROM ce_control.active_publication WHERE singleton),
 'publication_count',(SELECT count(*) FROM ce_control.publication),
 'live_readers',(SELECT count(*) FROM ce_control.reader_lease WHERE expires_at>clock_timestamp()),
 'events',(SELECT count(*) FROM ce_control.publication_event),
 'state',(SELECT state FROM ce_control.publication_candidate WHERE state='PUBLISHED'));
"""
control=json.loads(pub.call(['docker','exec','-i',mid,'psql','-U','ce_meta_admin','-d','ce_metadata','-X','-At','-v','ON_ERROR_STOP=1'],sql))
assert control==dict(active=pid,publication_count=1,live_readers=0,events=3,state='PUBLISHED')
save(OUT/'control-verification.json',control)

contract=read(ROOT/'config/kpi_contract_v1.json');mapping=read(ROOT/'config/source_target_mapping_v1.json')
details={m['id']:m for r in contract['requirements'] for m in r['metrics']}
metrics=[]
for m in mapping['metric_mapping']:
    metrics.append(dict(m,allowed_filters=sorted(ALLOWED[m['id']]),aggregation=details[m['id']]['aggregation'],
                        query_template='reports/semantic/sql/'+m['id']+'.sql',verified=True))
assert set(m['id'] for m in metrics)==set(IDS)
semantic_contract=dict(version=VERSION,kpi_contract_version=contract['version'],kpi_contract_sha256=sha(ROOT/'config/kpi_contract_v1.json'),
 publication_id=pid,coverage=dict(start='2024-01-01',end_exclusive='2026-01-01',assessment_default='2025-12-31'),
 result_contract=['publication_id','source_batch_id','contract_version','semantic_version','engine','context','metrics','external_reconciliation_warnings'],
 consumption_rule='Use SemanticSession with Publication Reader. SQL templates expose diagnostic components; quality/quantity policy is mandatory.',
 source_manifest_sha256=publication['source_catalog_sha256'],metrics=metrics)
save(ROOT/'config/semantic_contract_v1.json',semantic_contract)

# Reviewable catalogue of all 47 results; mixed-item quantities remain blank.
rows=['# Kết quả kiểm chứng 47 KPI CompanyE','',
      'Batch `'+pid+'`; kỳ mặc định [2024-01-01, 2026-01-01), assessment 31/12/2025. '
      'B06.01–06 và B07.01–04 dưới đây chọn RICE để giữ cùng mặt hàng/đơn vị; các chỉ tiêu còn lại ở toàn chuỗi. '
      'Tỷ lệ là phân số 0–1; VND/lượt và điểm đánh giá không phải phần trăm.','',
      '| KPI | Chỉ tiêu | Phạm vi bổ sung | Giá trị | Chất lượng |','|---|---|---|---|---|']
for metric in metrics:
    key=metric['id'];group=key[:3]
    item_scope=(group=='B06' and int(key[-2:])<=6) or (group=='B07' and int(key[-2:])<=4)
    value=by_case[('item_RICE',group)]['oracle'][key] if item_scope else base[key]
    raw=value['value'];display='BLANK' if raw is None else format(Decimal(raw).quantize(Decimal('0.000000001')),'f').rstrip('0').rstrip('.')
    if display=='':display='0'
    rows.append('| '+key+' | '+metric['name']+' | '+('RICE (kg)' if item_scope else 'Toàn chuỗi')+' | '+display+' | '+value['quality']+' |')
rows+=['','Các file baseline.json/slices.json giữ tử số, mẫu số, giá trị Decimal đầy đủ, cảnh báo và context. '
        'Không cộng các dòng trong bảng này: chúng khác đơn vị, kỳ ghi nhận và grain.']
(OUT/'KPI_Results.md').write_text('\n'.join(rows)+'\n',encoding='utf8')

paths=[p.relative_to(ROOT).as_posix() for p in sorted((ROOT/'src/semantic').glob('*.py'))]+[
 'scripts/kpi-pipeline.py','scripts/finalize-semantic.py','config/semantic_contract_v1.json',
 'config/kpi_contract_v1.json','config/source_target_mapping_v1.json','docs/CompanyE_Physical_Design.md','README.md']
paths+=[p.relative_to(ROOT).as_posix() for p in sorted((OUT/'sql').glob('*.sql'))]
archive=OUT/'frozen'/pid
for rel in paths:
    dest=archive/rel;dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists():assert sha(dest)==sha(ROOT/rel),'Cannot overwrite frozen '+rel
    else:dest.write_bytes((ROOT/rel).read_bytes())
save(OUT/'frozen-code.json',dict(path=archive.relative_to(ROOT).as_posix(),sha256={rel:sha(archive/rel) for rel in paths},secrets_included=False))
evidence={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(OUT.glob('*')) if p.is_file() and p.name!='verification.json' and not p.name.endswith('-progress.json')}
result=dict(status='PASSED_SEMANTIC_47_KPI',checked_at=datetime.now(timezone.utc).isoformat(),publication_id=pid,
 contract_version=contract['version'],semantic_version=VERSION,metric_count=47,
 baseline_metric_comparisons=baseline['metric_comparisons'],slice_cases=len(slices['checks']),slice_metric_comparisons=slices['metric_comparisons'],
 sql_fixture_cases=fixtures['sql_fixture_cases'],fixture_metric_checks=fixtures['metric_checks'],policy_checks=len(fixtures['policy_checks']),
 source_files_unchanged=len(catalog['datasets']),independent_reference='Operational raw CSV; no generator truth or ETL transformer reused',
 raw_and_both_engines_equal=True,exact_numerators_denominators=True,sql_ratio_tolerance='1e-9',
 replay_results_unchanged=True,publication_unchanged=True,live_readers=0,
 limitations=['Accepted frozen v2 final snapshot; coverage 2024-01-01 through 2025-12-31, no historical as-known reconstruction.',
 'Some quantity metrics require a single item; blanket company-wide quantities are intentionally NOT_APPLICABLE.',
 'PARTIAL dependency warnings conservatively apply to the whole batch; lot issues lack dimensional scope, so affected stock balances are conservatively withheld.',
 'Templates must be consumed through semantic quality policy and Publication Reader; direct latest SQL bypasses guarantees.',
 'Local queries/materialized aggregate results; no performance benchmark, Power BI/web integration or production serving SLA claimed.',
 'SQL division casts numerator and denominator to DECIMAL(28,12); baseline magnitudes fit its 16 integer digits. Revisit before much larger scale.'],
 next_step='Connect semantic results to Power BI/web; verify visual filters, totals and BLANK; then benchmark controlled equivalent workloads.',evidence_sha256=evidence)
save(OUT/'verification.json',result)
print(json.dumps({k:v for k,v in result.items() if k not in ['evidence_sha256','limitations']},ensure_ascii=False,indent=2))
