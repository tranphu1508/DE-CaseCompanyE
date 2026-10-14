"""Separate v2 databases and lake; the default v1 commands remain unchanged."""
import argparse
import csv
import json
import shutil
import subprocess
import sys
from datetime import datetime,timezone

from manage import ROOT, dc, psql, save, digest, source_checks
from model_v2 import MODELS

V2_CHECKS={
 'received_quantity_balance':"SELECT count(*) FROM purchase_lines l LEFT JOIN (SELECT purchase_line_id,sum(accepted_qty+rejected_qty) qty FROM receipts GROUP BY purchase_line_id) r USING(purchase_line_id) WHERE l.ordered_qty<>coalesce(r.qty,0)",
 'lot_receipt_quantity':"SELECT count(*) FROM receipts r LEFT JOIN (SELECT receipt_id,sum(quantity) qty FROM stock_movements WHERE movement_type='IN' GROUP BY receipt_id) s USING(receipt_id) WHERE r.accepted_qty<>coalesce(s.qty,0)",
 'stock_before_receipt':"SELECT count(*) FROM stock_movements s JOIN receipts r USING(receipt_id) WHERE s.movement_date<r.received_on",
 'daily_negative_stock':"SELECT count(*) FROM (SELECT receipt_id,movement_date,sum(sum(CASE WHEN movement_type='IN' THEN quantity ELSE -quantity END)) OVER(PARTITION BY receipt_id ORDER BY movement_date) qty FROM stock_movements GROUP BY receipt_id,movement_date) x WHERE qty<0",
 'final_revision_money':"SELECT count(*) FROM booking_revisions r JOIN bookings b USING(booking_id) WHERE r.revision_no=2 AND (r.gross_vnd<>b.gross_vnd OR r.discount_vnd<>b.discount_vnd OR r.customer_due_vnd<>b.customer_due_vnd OR r.company_share_vnd<>b.company_share_vnd OR r.partner_share_vnd<>b.partner_share_vnd OR r.commission_vnd<>b.commission_vnd)",
 'revision_room_total':"SELECT count(*) FROM booking_revisions v JOIN bookings b USING(booking_id) JOIN (SELECT revision_id,sum(nightly_rate_vnd) rate FROM booking_room_revisions GROUP BY revision_id) r USING(revision_id) WHERE v.gross_vnd<>r.rate*(b.departure-b.arrival)",
 'final_revision_room_rate':"SELECT count(*) FROM booking_room_revisions r JOIN booking_revisions v USING(revision_id) JOIN booking_rooms b USING(booking_room_id) WHERE v.revision_no=2 AND r.nightly_rate_vnd<>b.nightly_rate_vnd",
 'completed_payment_balance':"SELECT count(*) FROM bookings b LEFT JOIN (SELECT booking_id,sum(CASE WHEN event_type='CHARGE' THEN amount_vnd ELSE -amount_vnd END) amount FROM payments GROUP BY booking_id) p USING(booking_id) WHERE b.status='COMPLETED' AND b.customer_due_vnd<>coalesce(p.amount,0)"
}
COVERAGE={
 'multi_item_orders':"SELECT count(*) FROM (SELECT purchase_order_id FROM purchase_lines GROUP BY purchase_order_id HAVING count(DISTINCT item_id)>1) x",
 'split_receipt_lines':"SELECT count(*) FROM (SELECT purchase_line_id FROM receipts GROUP BY purchase_line_id HAVING count(*)>1) x",
 'revised_bookings':"SELECT count(DISTINCT booking_id) FROM booking_revisions WHERE revision_no=2",
 'shared_phones':"SELECT count(*) FROM (SELECT phone FROM guests WHERE phone IS NOT NULL GROUP BY phone HAVING count(*)>1) x",
 'missing_source_contacts':None
}


def load():
    existing=set(psql('postgres',"SELECT datname FROM pg_database WHERE datname IN ('hotel_ops_v2','entertainment_ops_v2')").splitlines())
    if not existing: dc('exec','-T','postgres','psql','-X','-v','ON_ERROR_STOP=1','-U','companye','-d','postgres','-f','/seed/v2/load.sql',capture=True)
    elif existing!={'hotel_ops_v2','entertainment_ops_v2'}: raise RuntimeError('Partial v2 initialization; no database was dropped.')
    validate()
    for db in MODELS:
        backup=ROOT/'databases'/f'{db}_v2.dump'
        if not backup.exists(): dc('exec','-T','postgres','pg_dump','-U','companye','-d',db+'_v2','-Fc','-f','/backups/'+backup.name)


def validate():
    manifest=json.loads((ROOT/'generated/v2/manifest.json').read_text(encoding='utf-8'))
    counts={}; checks=[]; aggregates={}
    for db,tables in MODELS.items():
        physical=db+'_v2'
        counts[db]={t.name:int(psql(physical,f'SELECT count(*) FROM {t.name}')) for t in tables}
        assert counts[db]==manifest['rows'][db],db+' changed from frozen v2'
        queries={**source_checks()[db],**(V2_CHECKS if db=='hotel_ops' else {})}
        for name,sql in queries.items():
            n=int(psql(physical,sql)); checks.append({'database':physical,'rule':name,'violations':n})
        for table in tables:
            numeric=[c[0] for c in table.columns if c[1] in ('INTEGER','BIGINT') or c[1].startswith('NUMERIC')]
            if numeric:
                result=psql(physical,'SELECT '+','.join(f'coalesce(sum({c}),0)' for c in numeric)+f' FROM {table.name}')
                aggregates[db+'.'+table.name]=dict(zip(numeric,result.split('|')))
    coverage={n:int(psql('hotel_ops_v2',sql)) for n,sql in COVERAGE.items() if sql}
    coverage['missing_source_contacts']=int(psql('entertainment_ops_v2','SELECT count(*) FROM customers WHERE phone IS NULL AND email IS NULL'))
    passed=not any(c['violations'] for c in checks) and all(coverage.values())
    report={'status':'PASSED' if passed else 'FAILED','checks':checks,'counts':counts,'coverage':coverage}
    save(ROOT/'reports/source_v2_validation.json',report)
    assert passed,report
    path=ROOT/'reports/reproducibility/v2/source_aggregates.json'
    if path.exists(): assert json.loads(path.read_text())==aggregates,'Frozen source aggregate mismatch'
    else: save(path,aggregates)
    print(json.dumps({'status':'PASSED','checks':len(checks),'coverage':coverage}))


def ingest():
    folder=ROOT/'generated/v2'; manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    assert all(digest(folder/p)==h for p,h in manifest['files'].items()),'Frozen v2 files changed'
    batch='v2_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    lake=ROOT/'lake/v2'; target=lake/'raw'/batch; target.mkdir(parents=True)
    jobs=lake/'_jobs'/batch; jobs.mkdir(parents=True)
    datasets=[]
    for db,tables in MODELS.items():
        statements=['\\set ON_ERROR_STOP on','BEGIN ISOLATION LEVEL REPEATABLE READ;',"SET TIME ZONE 'Asia/Ho_Chi_Minh';"]
        for table in tables:
            path=target/db/table.name/'data.csv'; path.parent.mkdir(parents=True)
            location='/lake/v2/'+path.relative_to(lake).as_posix()
            statements.append(f"COPY (SELECT * FROM {table.name} ORDER BY {table.columns[0][0]}) TO '{location}' WITH (FORMAT CSV,HEADER true,NULL '\\N');")
        statements.append('COMMIT;'); script=jobs/(db+'.sql'); script.write_text('\n'.join(statements),encoding='utf-8')
        dc('exec','-T','postgres','psql','-X','-v','ON_ERROR_STOP=1','-U','companye','-d',db+'_v2','-f','/lake/v2/'+script.relative_to(lake).as_posix(),capture=True)
        for table in tables:
            path=target/db/table.name/'data.csv'
            with path.open(encoding='utf-8',newline='') as f: count=sum(1 for _ in csv.reader(f))-1
            assert count==manifest['rows'][db][table.name]
            datasets.append({'dataset_id':db+'.'+table.name,'source_system':db,'physical_database':db+'_v2',
                'table':table.name,'relative_path':path.relative_to(lake).as_posix(),'format':'CSV','row_count':count,'sha256':digest(path),'bytes':path.stat().st_size})
    (target/'external').mkdir()
    for src in sorted((folder/'external').iterdir()):
        dst=target/'external'/src.name; shutil.copyfile(src,dst)
        datasets.append({'dataset_id':'external.'+src.stem,'source_system':'external_suppliers_or_distributors','table':src.stem,
            'relative_path':dst.relative_to(lake).as_posix(),'format':src.suffix[1:].upper(),'row_count':None,'sha256':digest(dst),'bytes':dst.stat().st_size})
    save(target/'ingestion_manifest.json',{'batch_id':batch,'status':'RAW_COMMITTED','source_dataset_version':'v2','seed':manifest['seed'],
        'generator_sha256':manifest['generator_sha256'],'source_manifest_sha256':digest(folder/'manifest.json'),
        'ingested_at_utc':datetime.now(timezone.utc).isoformat(),'datasets':datasets,'synthetic':True})
    save(lake/'catalog/latest_ingestion.json',{'batch_id':batch})
    print('V2 raw batch:',batch); return batch


def spark(action,batch,sql=None):
    archive=ROOT/'reports/processing'/batch; archive.mkdir(parents=True,exist_ok=True)
    files={}
    for name in ['manage_v2.py','lake_v2.py','lake_job.py','model_v2.py','model.py']:
        path=ROOT/'src'/name; target=archive/(path.stem+'_'+digest(path)[:12]+'.py')
        if not target.exists(): shutil.copyfile(path,target)
        files[name]=digest(path)
    save(archive/('attempt_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json'),{'action':action,'files':files})
    args=['exec','-T','spark','/opt/spark/bin/spark-submit','--master','local[2]','--driver-memory','1536m','/workspace/src/lake_v2.py',action,'--batch',batch]
    if sql: args+=['--sql',sql]
    dc(*args)


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('action',choices=['all','generate','load','ingest','lake','verify','query']); parser.add_argument('--sql'); args=parser.parse_args()
    if args.action in ('all','generate'): subprocess.run([sys.executable,'-X','utf8',str(ROOT/'src/generate_v2.py')],check=True)
    if args.action in ('all','load'): load()
    if args.action in ('all','ingest'): batch=ingest()
    else:
        pointer=ROOT/'lake/v2/catalog/latest_ingestion.json'
        batch=json.loads(pointer.read_text())['batch_id'] if pointer.exists() else None
    if args.action in ('all','lake'): spark('build',batch)
    if args.action in ('all','verify'):
        validate(); spark('verify',batch)
    if args.action=='query': spark('query',batch,args.sql)


if __name__=='__main__': main()
