"""Independent raw-to-target controls, both engines, and dimension preservation.

Does not import the fact transformer and never uses generator hidden truth.
Full-batch expected totals apply to this complete synthetic baseline only.
"""
from pathlib import Path
from datetime import date,datetime,timedelta
from decimal import Decimal
from collections import Counter
import csv,json,hashlib
from analytics_runtime.session import create_session
from analytics_runtime.etl_io import Jdbc,oracle_rows,fingerprint

ROOT=Path('/workspace');OUT=ROOT/'reports/fact-etl'
def read(p):return json.loads(p.read_text(encoding='utf8'))
def save(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf8')
def span(a,b):
    a=date.fromisoformat(a);b=date.fromisoformat(b)
    return [a+timedelta(days=n) for n in range((b-a).days)]
def run(spark):
    catalog=read(ROOT/'lake/v2/catalog/catalog.json');report=read(OUT/'verify.json');manifest=read(ROOT/'config/analytics/ddl/manifest.json')
    assert report['status']=='PASSED_FACT_ETL' and report['replay_unchanged']
    raw={}
    for ds in catalog['datasets']:
        p=ROOT/'lake/v2'/ds['relative_path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==ds['sha256']
        if 'columns' in ds:
            with p.open(encoding='utf8',newline='') as f:raw[ds['dataset_id']]=list(csv.DictReader(f))
    def h(name):return raw['hotel_ops.'+name]
    def e(name):return raw['entertainment_ops.'+name]
    def total(rows,col):return sum((Decimal(r[col]) for r in rows),Decimal(0))
    mapping={'F01':h('bookings'),'F04':e('ticket_orders'),'F05':e('rentals'),'F06':h('breakfast_entitlements'),'F07':h('dining_orders'),'F08':h('meal_sessions'),'F09':e('admissions'),'F12':h('purchase_lines'),'F13':h('receipts'),'F14':h('stock_movements'),'F16':h('maintenance'),'F17':h('weather_daily'),'L01':h('booking_rooms'),'L04':e('centres')}
    expected={k:len(v) for k,v in mapping.items()};ndays=(date(2026,1,1)-date(2024,1,1)).days
    expected.update(F02=len(h('rooms'))*ndays,F10=len(e('activities'))*ndays,F11=len(e('vehicles'))*ndays,F03=sum(len(span(r['checkin_date'],r['checkout_date'])) for r in h('stays')),L03=sum(r['hotel_booking_ref'] not in ('','\\N') for r in e('ticket_orders')+e('rentals')))
    assets={r['asset_id']:r for r in h('assets')};blocked=set();bridge=[]
    for r in h('maintenance'):
        room=assets[r['asset_id']]['room_id']
        if room in ('','\\N'):continue
        for d in span(r['starts_on'],r['ends_on']):
            if date(2024,1,1)<=d<date(2026,1,1):bridge.append((room,d,r['maintenance_id']));blocked.add((room,d))
    expected['L02']=len(bridge)
    oracle=Jdbc(spark,'oracle');pg=Jdbc(spark,'postgres');checks=[]
    entities={x['id']:x for x in manifest['entities']}
    for eid in ['L03','L04']:
        name=entities[eid]['physical_name'];spark.read.parquet(report['canonical_path']+'/'+name).createOrReplaceTempView(name)
    def check(label,sql,answer):
        ora=oracle.query(sql.replace('{db}','CE_DWH_A.'))[0][0]
        ice=spark.sql(sql.replace('{db}','ce.gold.')).first()[0]
        assert ora is not None and ice is not None,'Unexpected NULL '+label
        o=Decimal(str(ora));i=Decimal(str(ice));a=Decimal(str(answer))
        assert o==i==a,label+': '+str((o,i,a))
        checks.append(dict(check=label,expected=str(a),oracle=str(o),iceberg=str(i)))
    for eid,count in expected.items():
        name=entities[eid]['physical_name']
        if eid in ('L03','L04'):
            o=int(oracle.query('SELECT COUNT(*) FROM CE_DWH_A.'+name)[0][0]);i=spark.table(name).count();assert o==i==count
            checks.append(dict(check=eid+'_raw_count',expected=count,oracle=o,iceberg=i))
        else:check(eid+'_raw_count','SELECT COUNT(*) FROM {db}'+name,count)
    for col in ['gross_vnd','discount_vnd','customer_due_vnd','company_share_vnd','partner_share_vnd','commission_vnd']:
        check('booking_'+col,'SELECT SUM('+col+') FROM {db}fact_booking',total(h('bookings'),col))
    check('room_unavailable_union','SELECT SUM(blocked_day) FROM {db}fact_room_day',len(blocked))
    check('room_available','SELECT SUM(available_day) FROM {db}fact_room_day',expected['F02']-len(blocked))
    check('night_measure','SELECT SUM(occupied_night) FROM {db}fact_stay_night',expected['F03'])
    for col in ['eligible_covers','redeemed_covers']:check('breakfast_'+col,'SELECT SUM('+col+') FROM {db}fact_breakfast_entitlement',total(h('breakfast_entitlements'),col))
    for col in ['net_vnd','covers']:check('dining_'+col,'SELECT SUM('+col+') FROM {db}fact_dining_order',total(h('dining_orders'),col))
    check('rating_sum','SELECT SUM(rating_sum) FROM {db}fact_dining_order',total(h('dining_orders'),'rating'))
    check('session_cost','SELECT SUM(ingredient_cost_vnd) FROM {db}fact_meal_session',total(h('meal_sessions'),'ingredient_cost_vnd'))
    check('ticket_net','SELECT SUM(net_ticket_vnd) FROM {db}fact_ticket_order',total(e('ticket_orders'),'gross_vnd')-total(e('ticket_orders'),'refunded_vnd'))
    check('rental_agreed_once','SELECT SUM(agreed_vnd) FROM {db}fact_rental',total(e('rentals'),'agreed_vnd'))
    rented=sum(len(span(r['pickup_date'],r['return_date'])) for r in e('rentals') if r['status']=='COMPLETED')
    check('rented_days','SELECT SUM(rented_day) FROM {db}fact_vehicle_day',rented)
    for col in ['accepted_qty','rejected_qty']:check('receipt_'+col,'SELECT SUM('+col+') FROM {db}fact_receipt',total(h('receipts'),col))
    check('ordered_qty','SELECT SUM(ordered_qty) FROM {db}fact_purchase_line',total(h('purchase_lines'),'ordered_qty'))
    signed=Decimal(0)
    for kind,col in [('IN','in_qty'),('USE','use_qty'),('WASTE','waste_qty')]:
        amount=total([r for r in h('stock_movements') if r['movement_type']==kind],'quantity');signed+=amount if kind=='IN' else -amount
        check('movement_'+kind,'SELECT SUM('+col+') FROM {db}fact_stock_movement',amount)
    check('stock_signed','SELECT SUM(signed_qty) FROM {db}fact_stock_movement',signed)
    check('maintenance_cost_once','SELECT SUM(cost_vnd) FROM {db}fact_maintenance_work',total(h('maintenance'),'cost_vnd'))
    ticket_status={r['ticket_id']:r['status'] for r in e('tickets')};rescheduled=sum(ticket_status[r['ticket_id']]=='RESCHEDULED' for r in e('admissions'))
    assert rescheduled>0
    # Fixture and source evidence demonstrate that RESCHEDULED was not filtered.
    checks.append(dict(check='rescheduled_admissions_in_raw_and_complete_F09',expected=rescheduled,verified_by='F09 full raw count plus transformation fixture'))
    check('F15_disabled','SELECT COUNT(*) FROM {db}agg_inventory_lot_day',0)
    dims=read(ROOT/'reports/dimension-etl/run.json');preserved=[]
    for entry in dims['tables']:
        ent=entities[entry['entity']];ora=oracle_rows(spark,ent);ice=[r.asDict() for r in spark.table('ce.gold.'+ent['physical_name']).collect()]
        assert fingerprint(ora,ent)==fingerprint(ice,ent)==entry['content_sha256']
        native=spark._jvm.org.apache.iceberg.spark.Spark3Util.loadIcebergTable(spark._jsparkSession,'ce.gold.'+ent['physical_name'])
        assert native.currentSnapshot().snapshotId()==entry['iceberg_snapshot_id'];preserved.append(ent['id'])
    assert pg.query('SELECT count(*) FROM ce_control.active_publication')[0][0]=='0'
    assert pg.query("SELECT state FROM ce_control.pipeline_run WHERE run_id=?",[report['run_id']])[0][0]=='ETL_READY'
    assert pg.query('SELECT count(*) FROM ce_control.quality_metric WHERE run_id=?',[report['run_id']])[0][0]=='47'
    quality=read(Path(report['canonical_path'])/'source-quality.json');assert not quality['quarantine']
    recon=read(Path(report['canonical_path'])/'reconciliation.json');assert not recon['meal_session_mismatches'] and not recon['negative_lot_prefixes']
    assert not read(Path(report['canonical_path'])/'quarantine.json')
    assert all(q['status']=='COMPLETE' for q in report['quality'].values())
    result=dict(status='PASSED_INDEPENDENT_BASELINE',run_id=report['run_id'],source_files_unchanged=len(catalog['datasets']),source_tables=len(raw),source_rows=sum(len(v) for v in raw.values()),target_rows=sum(expected.values()),expected_target_counts=expected,checks=checks,dimensions_unchanged=preserved,metric_readiness_rows=47,publication_count=0,limitation='Complete frozen-v2 controls, not a general missing-data oracle, not KPI query acceptance or performance benchmark.')
    save(OUT/'independent-validation.json',result);oracle.close();pg.close();print(json.dumps(dict(status=result['status'],checks=len(checks),rows=result['target_rows'])),flush=True)

if __name__=='__main__':
    spark=create_session('CompanyE-independent-fact-validation')
    try:run(spark)
    finally:spark.stop()
