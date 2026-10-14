"""Hand-calculated fixtures execute the real SQL on both engines, using CTEs only."""
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
import re
from publication.core import Connection,Reader,read,save
from semantic.queries import build,IDS,COUNTS,validate
from semantic.service import decode,policy,SemanticSession

def data_cases():
    ctx=dict(start='2024-01-01',end='2024-01-04')
    day=dict(service_date_key=20240101,date_key=20240101,arrival_date_key=20240101,departure_date_key=20240101)
    def rows(count,**fields):return [dict(day,**fields) for _ in range(count)]
    data={
      'B01':{'F01':[dict(day,status=s) for s in ['COMPLETED','CANCELLED','NO_SHOW']],
             'F03':rows(4,occupied_night=1),'F02':rows(4,available_day=1)},
      'B02':{'F01':[dict(day,status='COMPLETED',gross_vnd=2050000,customer_due_vnd=1850000,company_share_vnd=50000,partner_share_vnd=150000,commission_vnd=150000),
                    dict(day,status='COMPLETED',gross_vnd=950000,customer_due_vnd=850000,company_share_vnd=30000,partner_share_vnd=70000,commission_vnd=50000),
                    dict(day,status='CANCELLED',gross_vnd=999999,customer_due_vnd=999999)]},
      'B03':{'F01':[dict(day,source_system='hotel_ops',booking_id='B1',status='COMPLETED',customer_due_vnd=2000000),dict(day,source_system='hotel_ops',booking_id='B2',status='COMPLETED',customer_due_vnd=1000000)],
             'F04':[dict(source_system='entertainment_ops',ticket_order_id=t,net_ticket_vnd=v) for t,v in [('T1',100000),('T2',200000),('T3',0)]],
             'F05':[dict(source_system='entertainment_ops',rental_id='R1',status='COMPLETED',agreed_vnd=400000),dict(source_system='entertainment_ops',rental_id='R2',status='CANCELLED',agreed_vnd=999999)],
             'L03':[dict(service_source_system='entertainment_ops',service_type=kind,service_id=sid,booking_source_system='hotel_ops',booking_id=bid) for kind,sid,bid in [('TICKET_ORDER','T1','B1'),('TICKET_ORDER','T2','B1'),('TICKET_ORDER','T3','B2'),('RENTAL','R1','B1'),('RENTAL','R2','B2')]]},
      'B04':{'F06':rows(1,eligible_covers=3,redeemed_covers=2),
             'F07':[dict(day,meal_key=1,net_vnd=150000,covers=1,rating_sum=4,rating_count=1),dict(day,meal_key=3,net_vnd=900000,covers=2,rating_sum=2,rating_count=1)],
             'F08':[dict(day,meal_key=1,ingredient_cost_vnd=100000,actual_covers=3),dict(day,meal_key=3,ingredient_cost_vnd=200000,actual_covers=2)]},
      'B05':{'F09':[dict(admission_date_key=20240102,admission_count=1) for _ in range(3)],
             'F10':rows(1,available_capacity=10)+rows(1,available_capacity=0),
             'F11':rows(1,available_day=1,rented_day=1)+rows(2,available_day=1,rented_day=0)+rows(1,available_day=0,rented_day=0)},
      'B06':{'F12':[dict(expected_date_key=20240101,source_system='hotel_ops',purchase_line_id=pid,ordered_qty=v,item_key=1) for pid,v in [('P1',10),('P2',5)]],
             'F13':[dict(source_system='hotel_ops',purchase_line_id='P1',received_date_key=20240101,expected_date_key=20240101,accepted_qty=6,rejected_qty=0,late_accepted_qty=0),dict(source_system='hotel_ops',purchase_line_id='P1',received_date_key=20240103,expected_date_key=20240101,accepted_qty=3,rejected_qty=1,late_accepted_qty=3)]},
      'B07':{'F14':[dict(movement_date_key=d,signed_qty=s,in_qty=i,use_qty=u,waste_qty=w,unit_price_vnd=10000,item_key=1) for d,s,i,u,w in [(20240101,10,10,0,0),(20240102,-6,0,6,0),(20240102,-2,0,0,2),(20240103,-1,0,0,1)]]},
      'B08':{'F16':[dict(end_date_key=d,status='COMPLETED',cost_vnd=v) for d,v in [(20240103,100000),(20240104,200000),(20240102,50000)]],
             'F02':rows(3,inventory_day=1,blocked_day=1,available_day=0)+rows(3,inventory_day=1,blocked_day=0,available_day=1)}}
    expected={
      'B01':[(4,1),(4,1),(4,4),(1,3),(1,3)],
      'B02':[(3000000,1),(2700000,1),(80000,1),(220000,1),(200000,1),(2720000,1)],
      'B03':[(1,1),(1,2),(300000,1),(400000,1),(3700000,1)],
      'B04':[(3,1),(2,1),(2,3),(1050000,1),(5,1),(300000,1),(300000,5),(6,2)],
      'B05':[(3,1),(10,1),(3,10),(1,1),(3,1),(1,3)],
      'B06':[(15,1),(9,1),(1,1),(3,1),(9,15),(1,10),(0,2)],
      'B07':[(0,1),(2,1),(6,1),(2,1),(20000,1),(20000,100000)],
      'B08':[(150000,1),(3,1),(3,1),(3,6)]}
    cases=[]
    for g in COUNTS:
        c=deepcopy(ctx)
        if g in ('B06','B07'):c['filters']={'item':'RICE'}
        if g=='B07':c['end']='2024-01-03'
        cases.append(('hand_'+g,g,c,data[g],expected[g]))
        zero=[(0,0 if build(g,c)[2][g+f'.{n:02}'] else 1) for n in range(1,COUNTS[g]+1)]
        cases.append(('empty_'+g,g,c,{},zero))
    cases.extend([
      ('inventory_carry_in','B07',dict(start='2024-01-03',end='2024-01-04',filters={'item':'RICE'}),data['B07'],[(2,1),(1,1),(0,1),(1,1),(10000,1),(10000,20000)]),
      ('inventory_no_movement','B07',dict(start='2024-01-04',end='2024-01-05',filters={'item':'RICE'}),data['B07'],[(1,1),(1,1),(0,1),(0,1),(0,1),(0,10000)]),
      ('receipt_asof_cutoff','B06',dict(ctx,assessment='2024-01-01',filters={'item':'RICE'}),data['B06'],[(15,1),(6,1),(0,1),(0,1),(6,15),(0,6),(0,2)]),
      ('maintenance_end_exclusive','B08',dict(start='2024-01-04',end='2024-01-05'),data['B08'],[(200000,1),(0,1),(0,1),(0,0)])])
    return cases

def inline(sql,data,entities,engine):
    ctes=[]
    for eid in sorted(set(re.findall(r'\{([DFL][0-9]{2})\}',sql))):
        cols=entities[eid]['columns'];records=data.get(eid,[])
        if eid=='D10':records=[dict(meal_key=1,meal_code='BREAKFAST'),dict(meal_key=3,meal_code='DINNER')]
        if eid=='D15':records=[dict(item_key=1,item_id='RICE',base_unit='kg')]
        statements=[]
        for record in records or [{}]:
            values=[]
            for c in cols:
                value=record.get(c['name']);typ=c['oracle_type'] if engine=='oracle' else c['spark_sql_type']
                if value is None:
                    # Missing numeric measures in deliberately small fixtures are zero; keys also zero.
                    expression='0' if c['spark_sql_type'].startswith(('BIGINT','INT','DECIMAL','DOUBLE')) else 'NULL'
                elif isinstance(value,str):expression="'"+value.replace("'","''")+"'"
                else:expression=str(value)
                values.append('CAST('+expression+' AS '+typ+') '+c['name'])
            statements.append('SELECT '+','.join(values)+(' FROM dual' if engine=='oracle' else '')+(' WHERE 1=0' if not records else ''))
        ctes.append('fx_'+eid+' AS ('+' UNION ALL '.join(statements)+')')
        sql=sql.replace('{'+eid+'}','fx_'+eid)
    assert sql.startswith('WITH ')
    return 'WITH '+',\n'.join(ctes)+',\n'+sql[5:]

def run(spark,out,hashes):
    entities={e['id']:e for e in read(Path('/workspace/config/analytics/ddl/manifest.json'))['entities']}
    manifest=read(Path('/workspace/reports/publication/manifest.json'));checks=[];ora=Connection(spark,'reader','oracle')
    try:
        for name,g,ctx,data,expected in data_cases():
            print('FIXTURE '+name,flush=True);sql,selected,ratios=build(g,ctx)
            o=decode(ora.query(inline(sql,data,entities,'oracle')),selected,ratios,ctx,manifest)
            i=decode([list(r) for r in spark.sql(inline(sql,data,entities,'iceberg')).collect()],selected,ratios,ctx,manifest)
            assert o==i,(name,'engines')
            for mid,(num,den) in zip(selected,expected):
                assert (o[mid]['diagnostic_accepted_numerator'],o[mid]['diagnostic_accepted_denominator'])==(Decimal(num),Decimal(den)),(name,mid,o[mid],num,den)
                if den==0:assert o[mid]['value'] is None
            checks.append(dict(name=name,metrics=len(selected),both_engines=True,hand_expected=expected))
    finally:ora.close()
    # Quality and filter tests target the semantic contract, not only SQL equality.
    policy_checks=[]
    def expect(name,mid,ctx,m,status,reason):
        actual=policy(mid,ctx,m);assert actual[0]==status and reason in actual[1],(name,actual)
        policy_checks.append(name)
    expect('mixed_units_quantity_blank','B06.01',{},manifest,'NOT_APPLICABLE','SELECT_ONE_ITEM_FOR_COMPATIBLE_QUANTITY')
    expect('mixed_items_inventory_blank','B07.02',{},manifest,'NOT_APPLICABLE','SELECT_ONE_ITEM_FOR_COMPATIBLE_QUANTITY')
    expect('breakfast_not_lunch','B04.01',dict(filters={'meal':'LUNCH'}),manifest,'NOT_APPLICABLE','MEAL_OUTSIDE_METRIC_SCOPE')
    expect('no_bar_cost','B04.06',dict(filters={'meal':'BAR'}),manifest,'NOT_APPLICABLE','MEAL_OUTSIDE_METRIC_SCOPE')
    expect('out_of_coverage_not_zero','B01.01',dict(start='2023-01-01'),manifest,'UNAVAILABLE','OUTSIDE_VERIFIED_V2_COVERAGE')
    partial=deepcopy(manifest);partial['quality_entities']['F04']['status']='PARTIAL'
    expect('partial_cross_sell_propagates','B03.02',{},partial,'PARTIAL','DEPENDENCY_QUALITY_PARTIAL_CONSERVATIVE_BATCH_SCOPE')
    missing=deepcopy(manifest);missing['quality_entities']['F17']['status']='UNAVAILABLE'
    expect('weather_dependency','B05.03',dict(filters={'severe_weather':1}),missing,'UNAVAILABLE','DEPENDENCY_QUALITY_UNAVAILABLE_CONSERVATIVE_BATCH_SCOPE')
    broken=deepcopy(manifest);broken['quality_scope']=[dict(entity='F14',receipt_id='LOT1',from_date='2024-02-01')]
    expect('negative_lot_closing_suppressed','B07.02',dict(filters={'item':'RICE'}),broken,'UNAVAILABLE','LOT_HISTORY_UNRELIABLE_CONSERVATIVE_SCOPE')
    assert policy('B07.01',dict(start='2024-02-01',filters={'item':'RICE'}),broken)[0]=='COMPLETE';policy_checks.append('opening_before_first_bad_day_valid')
    for name,g,ctx,metrics in [
      ('channel_capacity_rejected','B01',dict(filters={'channel':'AGODA'}),None),
      ('usage_area_balance_rejected','B07',dict(filters={'usage_area':'BAR'}),None),
      ('asset_filter_capacity_rejected','B08',dict(filters={'asset_type':'AC'}),None),
      ('invalid_date_order','B01',dict(start='2024-02-01',end='2024-01-01'),None),
      ('sql_injection_rejected','B02',dict(filters={'channel':"x' OR 1=1--"}),None)]:
        try:build(g,ctx,metrics)
        except ValueError:policy_checks.append(name)
        else:raise AssertionError(name)
    with Reader(spark,'semantic-filter-fixture') as reader:
        service=SemanticSession(reader)
        try:service.query('B02',dict(filters={'hotel':'NOT_A_HOTEL'}),'oracle')
        except ValueError:policy_checks.append('unknown_filter_not_zero')
        else:raise AssertionError('Unknown member accepted')
    save(out/'fixtures.json',dict(status='PASSED',sql_fixture_cases=len(checks),metric_checks=sum(c['metrics'] for c in checks),policy_checks=policy_checks,checks=checks,code_sha256=hashes(),business_tables_mutated=False))
    print('PASSED fixtures',flush=True)
