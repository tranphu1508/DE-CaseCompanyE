from pathlib import Path
from decimal import Decimal as D
import json
ROOT=Path(__file__).resolve().parents[1]
read=lambda n:json.loads((ROOT/'reports/powerbi'/n).read_text(encoding='utf-8-sig'))
vectors=read('dax-test-vectors.json');results={r['id']:r for r in read('dax-results.json')};checks=[];failures=[]
for case in vectors['cases']:
    actual=results.get(case['id'],{})
    if 'error' in actual or len(actual.get('rows',[]))!=1:
        failures.append(dict(case=case['id'],result=actual));continue
    row=actual['rows'][0]
    for mid,want in case['expected'].items():
        errors=[]
        for suffix,key in [(' n','diagnostic_accepted_numerator'),(' d','diagnostic_accepted_denominator'),('','value')]:
            got=row.get('['+mid+suffix+']');expected=want[key]
            if (got is None)!=(expected is None):errors.append(dict(field=key,expected=expected,actual=got))
            elif got is not None and abs(D(str(got))-D(expected))>(D('0.000000001') if suffix=='' else D('0.0001')):errors.append(dict(field=key,expected=expected,actual=got))
        expectedstate=want['quality']
        if expectedstate=='NOT_APPLICABLE':expectedstate='BỮA ĂN NGOÀI PHẠM VI' if 'MEAL_OUTSIDE_METRIC_SCOPE' in want['reasons'] else 'CHỌN MỘT MẶT HÀNG'
        if row.get('['+mid+' state]')!=expectedstate:errors.append(dict(field='state',expected=expectedstate,actual=row.get('['+mid+' state]')))
        check=dict(case=case['id'],metric=mid,passed=not errors,errors=errors);checks.append(check)
        if errors:failures.append(check)
report=dict(status='PASSED_DAX' if not failures else 'FAILED_DAX',queries=len(vectors['cases']),metric_checks=len(checks),failures=failures,excluded=vectors['excluded'],checks=checks)
(ROOT/'reports/powerbi/dax-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(report['status'],len(checks),'metric checks;',len(failures),'failures')
for x in failures[:8]:print(x)
