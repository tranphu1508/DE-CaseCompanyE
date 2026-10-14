"""Validate specification references and hand-calculated examples, not a warehouse."""
import hashlib
import json
import re
import sys
from datetime import date, timedelta, datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from model_v2 import MODELS


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dates(start, end):
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    return [first + timedelta(days=i) for i in range((last-first).days)]


def div(a, b):
    return None if b == 0 else Decimal(a) / Decimal(b)


def main():
    contract_path = ROOT / 'config/kpi_contract_v1.json'
    contract = json.loads(contract_path.read_text(encoding='utf-8'))
    doc_path = ROOT / contract['document']
    doc = doc_path.read_text(encoding='utf-8')
    schema = {db+'.'+t.name: {c[0] for c in t.columns} for db, tables in MODELS.items() for t in tables}
    expected_ids = [f'B{i:02}' for i in range(1, 9)]
    assert [r['id'] for r in contract['requirements']] == expected_ids
    metrics = [m for r in contract['requirements'] for m in r['metrics']]
    ids = [m['id'] for m in metrics]
    assert len(ids) == len(set(ids)) == 47
    documented = {}
    for line in doc.splitlines():
        if re.match(r'\| B\d\d\.\d\d \|', line):
            key, name, formula, unit = [s.strip() for s in line.strip('|').split('|')]
            assert key not in documented
            documented[key] = (name, formula, unit)
    assert set(documented) == set(ids)
    source_references = 0
    for group in contract['requirements']:
        assert group['source_columns'] and group['grain'] and group['filters']
        for table, columns in group['source_columns'].items():
            assert table in schema, table
            assert set(columns) <= schema[table], (table, set(columns)-schema[table])
            source_references += len(columns)
        for metric in group['metrics']:
            assert metric['id'].startswith(group['id']+'.')
            assert documented[metric['id']] == (metric['name'], metric['formula'], metric['unit'])
            assert metric['date_role'], metric['id']
            if metric['aggregation'] in ('ratio_of_totals', 'weighted_mean'):
                assert metric['zero_denominator'] == 'BLANK'

    # Preserve the code/data boundary: specifications must not change frozen generators.
    manifest_path = ROOT / 'generated/v2/manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    for filename, fingerprint in manifest['generator_sha256'].items():
        assert sha(ROOT / 'src' / filename) == fingerprint, filename

    examples = []

    def check(name, actual, expected, inputs):
        assert actual == expected, (name, actual, expected)
        examples.append({'case': name, 'inputs': inputs, 'actual': actual, 'expected': expected, 'status': 'PASSED'})

    check('B01_completed_two_rooms', 2*2, 4, {'rooms': 2, 'nights_per_room': 2})
    check('B01_cancel_no_show_cohort', [div(1, 3), div(1, 3)], [Decimal(1)/3, Decimal(1)/3], {'bookings': 3, 'cancelled': 1, 'no_show': 1})
    stay = dates('2024-01-30', '2024-02-02')
    check('B01_cross_month_nights', [sum(d.month == 1 for d in stay), sum(d.month == 2 for d in stay)], [2, 1], {'checkin': '2024-01-30', 'checkout': '2024-02-02'})
    check('B02_promotion_funding', [3000000-300000, 3000000-80000-200000], [2700000, 2720000], {'gross': 3000000, 'discount': 300000, 'company_discount': 80000, 'partner_discount': 220000, 'commission': 200000})
    versions = [(1, 2000000), (2, 2050000)]
    check('B02_latest_price_not_sum', max(versions)[1], 2050000, {'price_versions': versions})
    ticket_orders = [('B1', 100000, 0), ('B1', 200000, 0), ('B2', 80000, 80000)]
    rentals = [('B1', 'COMPLETED', 400000), ('B2', 'CANCELLED', 300000)]
    buyers = {b for b, gross, refund in ticket_orders if gross-refund > 0}
    buyers |= {b for b, status, amount in rentals if status == 'COMPLETED' and amount > 0}
    ticket_amount = sum(gross-refund for _, gross, refund in ticket_orders)
    rental_amount = sum(amount for _, status, amount in rentals if status == 'COMPLETED')
    check('B03_multiple_children_and_refunds', [len(buyers), div(len(buyers), 2), ticket_amount, rental_amount, 3000000+ticket_amount+rental_amount], [1, Decimal('0.5'), 300000, 400000, 3700000], {'hotel_customer_due': [2000000, 1000000], 'ticket_orders': ticket_orders, 'rentals': rentals})
    check('B04_entitlements_and_paid_covers', [div(2, 3), 150000+900000, 2+1+2, div(100000+200000, 3+2), div(4+2, 2)], [Decimal(2)/3, 1050000, 5, Decimal(60000), Decimal(3)], {'eligible': 3, 'redeemed': 2, 'paid': [[1, 150000, 4], [2, 900000, 2]], 'sessions': [[3, 100000], [2, 200000]]})
    check('B05_available_capacity', [div(3, 10), div(1, 4-1)], [Decimal('0.3'), Decimal(1)/3], {'open_activity_days': 1, 'capacity_per_day': 10, 'admissions': 3, 'vehicle_calendar_days': 4, 'maintenance_days': 1, 'used_days': 1})
    due = date(2024, 1, 3)
    receipts = [(date(2024, 1, 3), 6, 0), (date(2024, 1, 5), 3, 1)]
    accepted, rejected = sum(x[1] for x in receipts), sum(x[2] for x in receipts)
    late = sum(x[1] for x in receipts if x[0] > due)
    on_time = sum(x[1] for x in receipts if x[0] <= due)
    check('B06_split_delivery', [10, accepted, rejected, late, div(accepted, 10), div(rejected, accepted+rejected), int(on_time >= 10)], [10, 9, 1, 3, Decimal('0.9'), Decimal('0.1'), 0], {'ordered': 10, 'due': str(due), 'receipts': [(str(d), a, r) for d, a, r in receipts]})
    check('B06_due_unreceived_line_kept', [div(9, 10+10), div(0, 2)], [Decimal('0.45'), Decimal(0)], {'ordered_lines': [10, 10], 'accepted_lines': [9, 0], 'otif_lines': [False, False]})
    check('B06_line_otif_not_total_fill', [div(2*10, 2*10), div(1, 2)], [Decimal(1), Decimal('0.5')], {'ordered': [10, 10], 'accepted': [10, 10], 'accepted_on_time': [10, 0]})
    check('B07_first_period_balance', [10-6-2, 2*10000, div(2*10000, 10*10000)], [2, 20000, Decimal('0.2')], {'opening': 0, 'in': 10, 'use': 6, 'waste': 2, 'price': 10000})
    check('B07_next_period_no_receipt', [2-1, div(1*10000, 2*10000)], [1, Decimal('0.5')], {'opening': 2, 'in': 0, 'waste': 1, 'price': 10000})
    works = [('2024-01-01', '2024-01-03', 100000), ('2024-01-02', '2024-01-04', 200000)]
    window = set(dates('2024-01-01', '2024-01-04'))
    blocked = set().union(*(set(dates(s, e)) for s, e, _ in works)) & window
    cost = sum(c for _, end, c in works if date.fromisoformat(end) in window)
    check('B08_overlapping_work_and_completion_date', [len(blocked), 2*len(window)-len(blocked), div(len(blocked), 2*len(window)), cost], [3, 3, Decimal('0.5'), 100000], {'rooms': 2, 'period': ['2024-01-01', '2024-01-04'], 'work': works})
    check('B08_common_asset_cost_only', [cost+50000, len(blocked)], [150000, 3], {'common_asset_cost_completed_in_period': 50000, 'common_asset_room_id': None})
    check('zero_denominator_is_blank', [div(0, 0), div(100000, 0)], [None, None], {'numerators': [0, 100000], 'denominator': 0})
    check('weighted_ratio_not_average', div(9+1, 10+2), Decimal(10)/12, {'numerators': [9, 1], 'denominators': [10, 2]})
    events = [('R1', 2, 5), ('R1', 1, 6), ('R1', 2, 5)]
    current = {}
    for receipt, revision, amount in events:
        if receipt not in current or revision > current[receipt][0]:
            current[receipt] = (revision, amount)
    check('late_revision_and_replay', sum(v[1] for v in current.values()), 5, {'arrival_order': events})

    report = {
        'status': 'PASSED', 'scope': 'SPECIFICATION_REFERENCES_AND_HAND_CALCULATIONS_ONLY',
        'warehouse_lakehouse_powerbi_executed': False,
        'checked_at_utc': datetime.now(timezone.utc).isoformat(),
        'contract_version': contract['version'], 'requirements': len(expected_ids), 'metrics': len(metrics),
        'source_column_references': source_references, 'examples_passed': len(examples),
        'frozen_v2_generator_unchanged': True,
        'files_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in [doc_path, contract_path, Path(__file__).resolve(), manifest_path]},
        'examples': examples,
    }
    out = ROOT / 'reports/kpi_specification_v1_validation.json'
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str)+'\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ['status', 'scope', 'requirements', 'metrics', 'source_column_references', 'examples_passed']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
