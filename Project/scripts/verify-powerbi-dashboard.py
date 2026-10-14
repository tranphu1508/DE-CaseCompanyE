"""Prepare/verify chart DAX against independent streaming CSV aggregates.

Usage: prepare -> query-powerbi.ps1 with vectors.json -> verify.
Does not modify the original 47 KPI contract, import, or SQL verification.
"""
from pathlib import Path
from collections import defaultdict
from decimal import Decimal as D
import csv, json, sys
ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'reports/powerbi/dashboard'
PID='pub_3f41f8fafa4c913187af2cc3'
DATA=ROOT/'reports/powerbi/imports'/PID
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf8')
def rows(e,enriched=False):
    p=(ROOT/'powerbi/data'/PID if enriched else DATA)/(e+'.csv')
    with p.open(encoding='utf-8-sig',newline='') as f:yield from csv.DictReader(f)

if sys.argv[1]=='prepare':
    # Independent aggregates use each metric's own date and grain.
    a=defaultdict(lambda:defaultdict(D))
    dates={'F01':'departure_date_key','F02':'date_key','F03':'service_date_key','F07':'service_date_key',
           'F09':'admission_date_key','F10':'date_key','F11':'date_key','F12':'expected_date_key'}
    for e,day in dates.items():
        for r in rows(e,e in ('F01','F12')):
            key=(r['engine'],int(r[day])//100); v=a[key]
            if e=='F01' and r['status']=='COMPLETED':
                v['retained']+=D(r['gross_vnd'])-D(r['company_share_vnd'])-D(r['commission_vnd'])
                v['bookings']+=1;v['cross']+=D(r['cross_bought'])
            elif e=='F02':
                for c in ['available_day','blocked_day','inventory_day']:v[c]+=D(r[c])
            elif e=='F03':v['occupied']+=D(r['occupied_night'])
            elif e=='F07':v['food']+=D(r['net_vnd'])
            elif e=='F09':v['admissions']+=D(r['admission_count'])
            elif e=='F10':v['capacity']+=D(r['available_capacity'])
            elif e=='F11':v['rented']+=D(r['rented_day']);v['vehicles']+=D(r['available_day'])
            elif e=='F12' and int(r[day])<=20251231:v['otif']+=D(r['otif']);v['orders']+=1
    rice={r['item_key'] for r in rows('D15') if r['item_id']=='RICE'}
    movement=defaultdict(D)
    for r in rows('F14'):
        if r['item_key'] in rice:movement[(r['engine'],int(r['movement_date_key']))]+=D(r['signed_qty'])
    chart_metrics=['B01.03','B02.06','B03.02','B04.04','B05.03','B05.06','B06.07','B07.02','B08.04']
    def div(n,d):return n/d if d else None
    cases=[]
    for engine in ['oracle','iceberg']:
        for y in [2024,2025]:
            for m in range(1,13):
                month=f'{y}-{m:02}';end=y*10000+(m+1)*100+1 if m<12 else (y+1)*10000+101
                v=a[(engine,y*100+m)]
                values=[div(v['occupied'],v['available_day']),v['retained']/D(10**9),div(v['cross'],v['bookings']),
                        v['food']/D(10**9),div(v['admissions'],v['capacity']),div(v['rented'],v['vehicles']),
                        div(v['otif'],v['orders']),sum(q for (eng,date),q in movement.items() if eng==engine and date<end),
                        div(v['blocked_day'],v['inventory_day'])]
                fields=[]
                for mid in chart_metrics:
                    expr='[DB '+mid+' tháng]'
                    if mid=='B07.02':expr='CALCULATE('+expr+',TREATAS({"RICE"},D15[item_id]))'
                    fields+=['"'+mid+'"',expr]
                cases.append(dict(id=f'month/{engine}/{month}',query='EVALUATE CALCULATETABLE(ROW('+','.join(fields)+'),TREATAS({"'+engine+'"},Engine[engine]),TREATAS({"'+month+'"},ChartMonth[month]))',
                                  expected={mid:None if val is None else str(val) for mid,val in zip(chart_metrics,values)}))
    # Explicit selection boundaries, incomplete-month behavior, and blank guards.
    for cid,filters,expected in [
        ('selected_year_inside','TREATAS({"2024 | Cả năm"},Period[period]),TREATAS({"2024-01"},ChartMonth[month])',str(div(a[('oracle',202401)]['occupied'],a[('oracle',202401)]['available_day']))),
        ('selected_year_outside','TREATAS({"2024 | Cả năm"},Period[period]),TREATAS({"2025-01"},ChartMonth[month])',None),
        ('selected_month_inside','TREATAS({"2024-01"},Period[period]),TREATAS({"2024-01"},ChartMonth[month])',str(div(a[('oracle',202401)]['occupied'],a[('oracle',202401)]['available_day']))),
        ('selected_month_outside','TREATAS({"2024-01"},Period[period]),TREATAS({"2024-02"},ChartMonth[month])',None),
        ('partial_month','TREATAS({20240201},Period[start_key]),TREATAS({20240202},Period[end_key]),TREATAS({"2024-02"},ChartMonth[month])',None),
        ('multi_period','TREATAS({"2024-01","2024-02"},Period[period]),TREATAS({"2024-01"},ChartMonth[month])',None),
    ]:cases.append(dict(id=cid,query='EVALUATE CALCULATETABLE(ROW("value",[DB B01.03 tháng]),'+filters+')',expected={'value':expected}))
    cases.append(dict(id='stock_without_item',query='EVALUATE CALCULATETABLE(ROW("value",[DB B07.02 tháng]),TREATAS({"2024-01"},ChartMonth[month]))',expected={'value':None}))
    # Presentation money cards: compare scale with certified SQL baseline.
    model=read(ROOT/'powerbi/CompanyE.SemanticModel/model.bim')
    money=[m['name'] for t in model['model']['tables'] for m in t.get('measures',[]) if m['name'].startswith('DB ') and m['name'].endswith(' tỷ')]
    baseline={k:v for c in read(ROOT/'reports/powerbi/dax-test-vectors.json')['cases'] if c['id'].startswith('baseline/') and c['engine']=='oracle' for k,v in c['expected'].items()}
    for engine in ['oracle','iceberg']:
        fields=[];expected={}
        for name in money:
            mid=name.split()[1];fields+=['"'+mid+'"','['+name+']'];expected[mid]=str(D(baseline[mid]['value'])/D(10**9))
        cases.append(dict(id='scaled_cards/'+engine,query='EVALUATE CALCULATETABLE(ROW('+','.join(fields)+'),TREATAS({"'+engine+'"},Engine[engine]))',expected=expected))
    write(R/'vectors.json',dict(cases=cases,reference='Independent CSV aggregates for monthly chart values; certified SQL baseline for money cards.'))
    print('PREPARED',len(cases),'queries',sum(len(c['expected']) for c in cases),'value checks')
else:
    cases=read(R/'vectors.json')['cases'];actual={r['id']:r for r in read(R/'results.json')};checks=[]
    for case in cases:
        got=actual.get(case['id'],{});rs=got.get('rows',[])
        for key,want in case['expected'].items():
            value=rs[0].get('['+key+']') if len(rs)==1 else None
            passed='error' not in got and len(rs)==1 and ((value is None and want is None) or (value is not None and want is not None and abs(D(str(value))-D(want))<D('0.000000001')))
            checks.append(dict(case=case['id'],metric=key,actual=value,expected=want,passed=passed,error=got.get('error')))
    failures=[c for c in checks if not c['passed']]
    write(R/'verification.json',dict(status='PASSED' if not failures else 'FAILED',queries=len(cases),value_checks=len(checks),failures=failures,checks=checks))
    print('PASSED' if not failures else 'FAILED',len(checks),'chart/card checks;',len(failures),'failures')
    for f in failures[:10]:print(f)
    raise SystemExit(bool(failures))
