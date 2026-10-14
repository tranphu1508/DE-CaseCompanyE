"""Record the saved dashboard and the explicitly observed UI evidence.

Run after Desktop Save. This inventories evidence; it does not automate UI.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/powerbi/dashboard'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def expr(x): return ('\n'.join(x) if isinstance(x, list) else x).strip()
model = read(ROOT/'powerbi/CompanyE.SemanticModel/model.bim')['model']
old = read(OUT/'before-dashboard/model.bim')['model']
measures = {(t['name'], m['name']): m for t in model['tables'] for m in t.get('measures', [])}
original = {(t['name'], m['name']): m for t in old['tables'] for m in t.get('measures', [])}
assert len(original) == 196
assert all(expr(measures[k]['expression']) == expr(v['expression']) for k,v in original.items())
assert len(measures) == 223 and len(model['tables']) == 37 and len(model['relationships']) == 69
definition = ROOT/'powerbi/CompanyE.Report/definition'
pages = read(definition/'pages/pages.json')
assert pages['activePageName'] == 'overview' and len(pages['pageOrder']) == 10
counts = {}
for p in definition.glob('pages/*/visuals/*/visual.json'):
    typ = read(p)['visual']['visualType']
    counts[typ] = counts.get(typ, 0) + 1
assert sum(counts.get(t,0) for t in ('lineChart','clusteredBarChart','clusteredColumnChart')) == 18, counts
assert len(list(definition.glob('pages/*/visuals/score*/visual.json'))) == 36
for page in ('B06','B07'):
    assert any("'RICE'" in p.read_text(encoding='utf8') for p in (definition/'pages'/page/'visuals').glob('*/visual.json'))
charts = read(OUT/'verification.json'); regression = read(OUT/'kpi-regression.json')
assert charts['status'] == 'PASSED' and not charts['failures']
assert regression['status'] == 'PASSED_DAX' and not regression['failures']
observed = {
 'overview': 'Oracle default; full period; four sites; 105.55 billion retained, 42.00% occupancy, 64.43% cross-sell, 65.21% OTIF; 24 monthly points.',
 'overview-month-filter': '2024-01 selected: 3.50 billion retained, 36.05% occupancy; exactly one monthly point. Clearing Period restored 24 points.',
 'overview-iceberg': 'Switched source to Iceberg; cards, site table and monthly trend matched Oracle. Cleared source afterwards.',
 'overview-reopened': 'Closed and reopened saved PBIP; overview cards, four-site totals, 24-point trend and COMPLETE warning rendered with original totals.',
 'B01': 'Eight-hotel occupied/available comparison and monthly occupancy rendered.',
 'B02': 'Channel retained-value comparison and monthly trend rendered; long channel list scrolls.',
 'B03': 'Hotel cross-sell comparison, monthly trend and 17,281 cross-selling bookings rendered.',
 'B04': 'Eight-hotel buffet material cost comparison and monthly food-value trend rendered.',
 'B05': 'Site comparison and monthly trends both rendered two series for attraction and rental utilization.',
 'B06-no-item': 'Quantity cards BLANK; detail requests one item; order-count OTIF still renders.',
 'B06-RICE': 'RICE selected: OTIF 64.30%, accepted 97.72%, rejected 2.28%, late quantity 3,589; supplier and monthly charts render.',
 'B07-no-item': 'Quantity cards and stock charts BLANK; detail explicitly requests one item; money and supported ratio remain.',
 'B07-RICE': 'RICE selected: opening 0, closing 1,790, usage 16,516; eight hotel bars and 24 monthly closing balances render.',
 'B08': 'Maintenance 167,200,000 VND, blocked 962, available 174,478, blocked ratio 0.55%; both charts render.',
}
evidence = []
for name, observation in observed.items():
    p = OUT/'ui'/f'{name}.png'
    assert p.exists() and p.stat().st_size > 10000
    evidence.append(dict(file=str(p.relative_to(ROOT)),sha256=sha(p),observation=observation))
schema = read(ROOT/'reports/powerbi/static-validation.json')
files = [ROOT/'powerbi/CompanyE.pbip',ROOT/'powerbi/CompanyE.SemanticModel/model.bim',
         ROOT/'scripts/build-powerbi-dashboard.py',ROOT/'scripts/verify-powerbi-dashboard.py',
         ROOT/'scripts/finalize-powerbi-dashboard.py',ROOT/'powerbi/data/dashboard-months.csv']
files += sorted(definition.rglob('*.json'))
result = dict(status='PASSED_OBSERVED_UI_AND_NUMERIC_CHECKS',created_at=datetime.now(timezone.utc).isoformat(),
 publication_id='pub_3f41f8fafa4c913187af2cc3', pages=10,charts=18,kpi_cards=36,
 tables=37,relationships=69,measures=223,original_measure_expressions_unchanged=196,
 chart_value_checks=charts['value_checks'],kpi_regression_checks=regression['metric_checks'],
 visual_counts=counts,ui_evidence=evidence,
 saved_state=dict(active_page='overview',quantity_pages_default_item='RICE',format='TMSL',desktop_save_observed=True,reopen_ui_observed=True),
 schema_validation=dict(status=schema['status'],checked_files=schema['checked_files'],unavailable_files=len(schema['unavailable'])),
 limitations=['UI checks cover only the observations listed; not every filter combination.',
 'B01/B02 screenshots precede the DOUBLE scaling correction; final presentation measures pass the 457 numeric checks.',
 'QA page retained from prior acceptance; simulated PARTIAL is not a live incomplete publication.',
 'Frozen COMPLETE publication via local Import; no DirectQuery, scheduled refresh or web deployment.',
 'Microsoft visual schema 2.13.0 unavailable; those files are not counted as schema passes.'],
 files=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in files])
(OUT/'ui-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:result[k] for k in ('status','pages','charts','kpi_cards','original_measure_expressions_unchanged','schema_validation')},ensure_ascii=False))
