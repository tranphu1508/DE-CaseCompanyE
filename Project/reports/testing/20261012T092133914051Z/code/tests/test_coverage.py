import json
import pytest

pytestmark=pytest.mark.coverage


def test_required_scenarios_and_report_gaps(root,pg,report_dir):
    matrix=json.loads((root/'tests/scenario_matrix.json').read_text())
    results=[]
    for scenario in matrix['required_now']:
        with pg(scenario['db']) as conn:
            observed=conn.execute(scenario['sql']).fetchone()[0]
        results.append({**scenario,'observed':observed,'passed':observed>=scenario['minimum']})
    report={'status':'PASSED' if all(r['passed'] for r in results) else 'FAILED',
            'scope':'v1 declared scenarios only; not all CompanyE business scenarios',
            'checks':results,'deferred':matrix['deferred']}
    (report_dir/'scenario_coverage.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    assert all(r['passed'] for r in results), [r for r in results if not r['passed']]
