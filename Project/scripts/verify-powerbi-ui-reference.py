"""Cross-check manually observed overview figures against immutable Import rows.

This is NOT UI automation: observed values are transcribed from the PNG evidence.
The full DAX-to-SQL verification remains in verify-powerbi-dax.py.
"""
from pathlib import Path
from decimal import Decimal
import csv
import json

ROOT = Path(__file__).resolve().parents[1]
PID = 'pub_3f41f8fafa4c913187af2cc3'
DATA = ROOT / 'reports/powerbi/imports' / PID

def rows(name):
    with (DATA / (name + '.csv')).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

hotels = {r['hotel_key']: r['hotel_id'] for r in rows('D03')}
sites = {r['site_key']: r['site_id'] for r in rows('D02')}
facts = {n: rows(n) for n in ['F01', 'F02', 'F03']}
cases = [
    ('01-overview-total', 'oracle', None, None, 20240101, 20260101, [73275, 174478, '42.00%', 105545873007]),
    ('02-site-SP', 'oracle', 'SP', None, 20240101, 20260101, [18313, 43621, '41.98%', 26282805889]),
    ('03-iceberg-SP', 'iceberg', 'SP', None, 20240101, 20260101, [18313, 43621, '41.98%', 26282805889]),
    ('10-overview-January-2024', 'oracle', None, None, 20240101, 20240201, [2682, 7440, '36.05%', 3495785045]),
    ('11-overview-hotel-DL3', 'oracle', None, 'DL-3', 20240101, 20260101, [9079, 17445, '52.04%', 7626417211]),
    ('12-overview-filters-cleared', 'oracle', None, None, 20240101, 20260101, [73275, 174478, '42.00%', 105545873007]),
    ('13-reopened-overview', 'oracle', None, None, 20240101, 20260101, [73275, 174478, '42.00%', 105545873007]),
]
checks = []
for evidence, engine, site, hotel, start, end, observed in cases:
    def selected(table, day):
        return [r for r in facts[table] if r['engine'] == engine
                and (site is None or sites[r['site_key']] == site)
                and (hotel is None or hotels[r['hotel_key']] == hotel)
                and start <= int(r[day]) < end]
    occupied = sum(int(r['occupied_night']) for r in selected('F03', 'service_date_key'))
    available = sum(int(r['available_day']) for r in selected('F02', 'date_key'))
    retained = sum(Decimal(r['gross_vnd']) - Decimal(r['company_share_vnd']) - Decimal(r['commission_vnd'])
                   for r in selected('F01', 'departure_date_key') if r['status'] == 'COMPLETED')
    expected = [occupied, available, f'{Decimal(occupied) / Decimal(available):.2%}', int(retained)]
    evidence_path = ROOT / 'reports/powerbi/ui-evidence' / (evidence + '.png')
    checks.append(dict(evidence=str(evidence_path.relative_to(ROOT)), observed=observed,
                       reference=expected, passed=expected == observed and evidence_path.exists()))
result = dict(status='PASSED' if all(c['passed'] for c in checks) else 'FAILED',
              source='Immutable CSV independently aggregated; UI values manually transcribed from evidence.',
              checks=checks)
(ROOT / 'reports/powerbi/ui-reference-verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
print(result['status'], len(checks), 'UI overview cases')
raise SystemExit(result['status'] != 'PASSED')
