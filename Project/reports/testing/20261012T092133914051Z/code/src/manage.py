"""Local orchestrator. Only manages the companye Compose project and named DBs."""
import argparse
import csv
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from model import MODELS, all_contracts

ROOT=Path(__file__).resolve().parents[1]


def now(): return datetime.now(timezone.utc).isoformat()
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')


def dc(*args, capture=False):
    cmd=['docker','compose','--project-directory',str(ROOT),*args]
    result=subprocess.run(cmd,cwd=ROOT,check=True,capture_output=capture,encoding='utf-8',errors='replace')
    return result.stdout.strip() if capture else None


def psql(db, sql):
    return dc('exec','-T','postgres','psql','-X','-v','ON_ERROR_STOP=1','-U','companye','-d',db,'-At','-c',sql,capture=True)


def setup():
    for part in ['generated','databases','lake/raw','lake/standardized','lake/quarantine','lake/catalog/hive_state','lake/catalog/warehouse','lake/_jobs','reports']:
        (ROOT/part).mkdir(parents=True,exist_ok=True)
    env=ROOT/'.env'
    if not env.exists(): env.write_text('COMPANYE_DB_PASSWORD='+secrets.token_hex(24)+'\n',encoding='utf-8')


def version_folder():
    cfg=json.loads((ROOT/'config/generation.json').read_text(encoding='utf-8'))
    return ROOT/'generated'/cfg['dataset_version']


def archive_provenance():
    folder=version_folder()
    dst=ROOT/'reports/reproducibility'/folder.name
    dst.mkdir(parents=True,exist_ok=True)
    for src in [ROOT/'src/generate.py',ROOT/'src/model.py',ROOT/'config/generation.json',folder/'manifest.json',folder/'audit_only/generation_audit.json']:
        target=dst/src.name
        if target.exists() and digest(target)!=digest(src):
            raise RuntimeError(f'Frozen provenance differs: {target}. Use a new dataset version.')
        if not target.exists(): shutil.copyfile(src,target)


def load():
    folder=version_folder()
    expected=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    existing=psql('postgres',"SELECT datname FROM pg_database WHERE datname IN ('hotel_ops','entertainment_ops') ORDER BY datname;").splitlines()
    if not existing:
        dc('exec','-T','postgres','psql','-X','-v','ON_ERROR_STOP=1','-U','companye','-d','postgres','-f',f'/seed/{folder.name}/load.sql',capture=True)
    elif set(existing)!=set(MODELS):
        raise RuntimeError('Partial source initialization. No database is dropped automatically; inspect the existing CompanyE DB.')
    counts={}
    for db,tables in MODELS.items():
        sql=' UNION ALL '.join(f"SELECT '{t.name}', COUNT(*) FROM {t.name}" for t in tables)
        counts[db]={name:int(n) for name,n in (x.split('|') for x in psql(db,sql).splitlines())}
        if counts[db]!=expected['rows'][db]:
            raise RuntimeError(f'{db} does not match seed version {folder.name}; existing DB retained unchanged.')
        backup=ROOT/'databases'/f'{db}_{folder.name}.dump'
        if not backup.exists():
            dc('exec','-T','postgres','pg_dump','-U','companye','-d',db,'-Fc','-f',f'/backups/{db}_{folder.name}.dump')
    save(ROOT/'reports/source_load.json',{'verified_at':now(),'dataset_version':folder.name,'counts':counts,'manifest_sha256':digest(folder/'manifest.json')})
    archive_provenance()
    print('Source databases loaded and counted; portable pg_dump backups created.',flush=True)


def ingest():
    folder=version_folder(); manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    # Revalidate immutable files before ingesting; no truth files are eligible inputs.
    for name,want in manifest['files'].items():
        if digest(folder/name.replace('\\','/'))!=want: raise RuntimeError('Seed provenance checksum changed: '+name)
    batch=folder.name+'_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    target=ROOT/'lake/raw'/batch; target.mkdir(parents=True,exist_ok=False)
    job=ROOT/'lake/_jobs'/batch; job.mkdir(parents=True)
    datasets=[]
    for db,tables in MODELS.items():
        statements=['\\set ON_ERROR_STOP on','BEGIN ISOLATION LEVEL REPEATABLE READ;',"SET TIME ZONE 'Asia/Ho_Chi_Minh';"]
        for t in tables:
            tabledir=target/db/t.name; tabledir.mkdir(parents=True)
            location=f'/lake/raw/{batch}/{db}/{t.name}/data.csv'
            statements.append(f"COPY (SELECT * FROM {t.name} ORDER BY {t.columns[0][0]}) TO '{location}' WITH (FORMAT CSV, HEADER true, NULL '\\N');")
        statements.append('COMMIT;')
        script=job/(db+'_export.sql'); script.write_text('\n'.join(statements),encoding='utf-8')
        dc('exec','-T','postgres','psql','-X','-v','ON_ERROR_STOP=1','-U','companye','-d',db,'-f',f'/lake/_jobs/{batch}/{script.name}',capture=True)
        for t in tables:
            path=target/db/t.name/'data.csv'
            with path.open(encoding='utf-8',newline='') as f: count=sum(1 for _ in csv.reader(f))-1
            if count!=manifest['rows'][db][t.name]: raise RuntimeError(f'Source row count changed: {db}.{t.name}')
            datasets.append({'dataset_id':db+'.'+t.name,'source_system':db,'table':t.name,'relative_path':path.relative_to(ROOT/'lake').as_posix(),'format':'CSV','row_count':count,'sha256':digest(path),'bytes':path.stat().st_size})
    external=target/'external'; external.mkdir()
    for src in sorted((folder/'external').iterdir()):
        if src.suffix.lower() not in ['.csv','.txt','.svg','.jsonl']: raise RuntimeError('Unexpected external input: '+str(src))
        dst=external/src.name; shutil.copyfile(src,dst)
        datasets.append({'dataset_id':'external.'+src.stem,'source_system':'external_suppliers_or_distributors','table':src.stem,'relative_path':dst.relative_to(ROOT/'lake').as_posix(),'format':src.suffix[1:].upper(),'row_count':None,'sha256':digest(dst),'bytes':dst.stat().st_size})
    record={'batch_id':batch,'status':'RAW_COMMITTED','ingested_at_utc':now(),'source_dataset_version':folder.name,'seed':manifest['seed'],'generator_sha256':manifest['generator_sha256'],'source_manifest_sha256':digest(folder/'manifest.json'),'synthetic':True,'snapshot_semantics':'Repeatable-read per source DB; independent databases are not a distributed atomic snapshot. Full snapshot, not CDC.','datasets':datasets}
    save(target/'ingestion_manifest.json',record)
    save(ROOT/'lake/catalog/latest_ingestion.json',{'batch_id':batch})
    print('Raw batch committed:',batch,flush=True)
    return batch


def latest():
    return json.loads((ROOT/'lake/catalog/latest_ingestion.json').read_text(encoding='utf-8'))['batch_id']


def spark(action,batch=None,sql=None):
    if action=='build' and batch:
        archive=ROOT/'reports/processing'/batch
        archive.mkdir(parents=True,exist_ok=True)
        files={}
        for relative in ['src/manage.py','src/lake_job.py','src/model.py','compose.yaml']:
            src=ROOT/relative; target=archive/src.name
            if target.exists() and digest(target)!=digest(src):
                # Do not overwrite code evidence for an earlier processing attempt.
                target=archive/(src.stem+'_'+digest(src)[:12]+src.suffix)
            if not target.exists(): shutil.copyfile(src,target)
            files[relative]={'sha256':digest(src),'archive_file':target.name}
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        save(archive/f'attempt_{stamp}.json',{'action':action,'batch_id':batch,'started_at':now(),'files':files})
    args=['exec','-T','spark','/opt/spark/bin/spark-submit','--master','local[2]','--driver-memory','1536m','/workspace/src/lake_job.py',action]
    if batch: args+=['--batch',batch]
    if sql: args+=['--sql',sql]
    dc(*args)


def source_checks():
    return {
      'hotel_ops':{
        'five_star_breakfast_missing':"SELECT count(*) FROM rate_plans r JOIN hotels h USING(hotel_id) WHERE h.stars=5 AND r.breakfast_included<>1",
        'booking_room_hotel_mismatch':"SELECT count(*) FROM booking_rooms br JOIN bookings b USING(booking_id) JOIN rooms r USING(room_id) JOIN rate_plans p USING(rate_plan_id) WHERE b.hotel_id<>r.hotel_id OR p.hotel_id<>b.hotel_id OR p.channel_id<>b.channel_id",
        'booking_price_mismatch':"SELECT count(*) FROM bookings b JOIN (SELECT br.booking_id,SUM(br.nightly_rate_vnd*(bb.departure-bb.arrival)) amount FROM booking_rooms br JOIN bookings bb USING(booking_id) GROUP BY br.booking_id) x USING(booking_id) WHERE b.gross_vnd<>x.amount",
        'room_overlaps':"SELECT count(*) FROM stays a JOIN booking_rooms x ON a.booking_room_id=x.booking_room_id JOIN stays b ON a.stay_id<b.stay_id JOIN booking_rooms y ON b.booking_room_id=y.booking_room_id WHERE x.room_id=y.room_id AND a.checkin_date<b.checkout_date AND b.checkin_date<a.checkout_date",
        'stay_during_maintenance':"SELECT count(*) FROM stays s JOIN booking_rooms br USING(booking_room_id) JOIN assets a USING(room_id) JOIN maintenance m USING(asset_id) WHERE s.checkin_date<m.ends_on AND m.starts_on<s.checkout_date",
        'invalid_stay_status':"SELECT count(*) FROM stays s JOIN booking_rooms br USING(booking_room_id) JOIN bookings b USING(booking_id) WHERE b.status<>'COMPLETED'",
        'invalid_breakfast_day':"SELECT count(*) FROM breakfast_entitlements e JOIN booking_rooms br USING(booking_room_id) JOIN bookings b USING(booking_id) WHERE e.service_date<=b.arrival OR e.service_date>b.departure OR e.eligible_covers<>br.breakfast_guests",
        'negative_lot_balance':"SELECT count(*) FROM (SELECT receipt_id,SUM(CASE WHEN movement_type='IN' THEN quantity ELSE -quantity END) balance FROM stock_movements GROUP BY receipt_id) s WHERE balance<0",
        'meal_cost_mismatch':"SELECT count(*) FROM meal_sessions s LEFT JOIN (SELECT m.session_id,SUM(m.quantity*l.unit_price_vnd) cost FROM stock_movements m JOIN receipts r USING(receipt_id) JOIN purchase_lines l USING(purchase_line_id) WHERE m.movement_type='USE' AND m.session_id IS NOT NULL GROUP BY m.session_id) x USING(session_id) WHERE s.ingredient_cost_vnd<>COALESCE(x.cost,0)",
        'promotion_outside_conditions':"SELECT count(*) FROM bookings b JOIN promotions p USING(promotion_id) JOIN hotels h ON h.hotel_id=b.hotel_id JOIN channels c ON c.channel_id=b.channel_id WHERE b.booked_on NOT BETWEEN p.sale_from AND p.sale_to OR b.arrival<p.stay_from OR b.departure>p.stay_to OR h.site_id<>p.site_id OR (p.channel_id IS NOT NULL AND p.channel_id<>b.channel_id) OR (p.channel_id IS NULL AND c.channel_type<>'DIRECT')",
        'breakfast_cover_mismatch':"SELECT count(*) FROM meal_sessions s JOIN outlets o USING(outlet_id) LEFT JOIN (SELECT b.hotel_id,e.service_date,SUM(e.redeemed_covers) covers FROM breakfast_entitlements e JOIN booking_rooms br USING(booking_room_id) JOIN bookings b USING(booking_id) GROUP BY b.hotel_id,e.service_date) x ON x.hotel_id=o.hotel_id AND x.service_date=s.service_date LEFT JOIN (SELECT outlet_id,service_date,SUM(covers) covers FROM dining_orders WHERE meal='BREAKFAST' GROUP BY outlet_id,service_date) y ON y.outlet_id=s.outlet_id AND y.service_date=s.service_date WHERE s.meal='BREAKFAST' AND s.actual_covers<>COALESCE(x.covers,0)+COALESCE(y.covers,0)"
      },
      'entertainment_ops':{
        'admission_when_closed':"SELECT count(*) FROM admissions a JOIN tickets t USING(ticket_id) JOIN closures c ON c.activity_id=t.activity_id AND c.closed_on=(a.entered_at AT TIME ZONE 'Asia/Ho_Chi_Minh')::date",
        'admission_wrong_status':"SELECT count(*) FROM admissions a JOIN tickets t USING(ticket_id) WHERE t.status NOT IN ('USED','RESCHEDULED')",
        'ticket_total_mismatch':"SELECT count(*) FROM ticket_orders o JOIN (SELECT ticket_order_id,SUM(price_vnd) gross,SUM(CASE WHEN status='REFUNDED' THEN price_vnd ELSE 0 END) refunded FROM tickets GROUP BY ticket_order_id) x USING(ticket_order_id) WHERE o.gross_vnd<>x.gross OR o.refunded_vnd<>x.refunded",
        'vehicle_overlaps':"SELECT count(*) FROM rentals a JOIN rentals b ON a.vehicle_id=b.vehicle_id AND a.rental_id<b.rental_id WHERE a.status='COMPLETED' AND b.status='COMPLETED' AND a.pickup_date<b.return_date AND b.pickup_date<a.return_date",
        'rental_during_maintenance':"SELECT count(*) FROM rentals r JOIN vehicle_maintenance m USING(vehicle_id) WHERE r.status='COMPLETED' AND r.pickup_date<m.ends_on AND m.starts_on<r.return_date"
      }
    }
def validate_sources():
    checks=source_checks()
    results=[]
    for db,queries in checks.items():
        sql=' UNION ALL '.join(f"SELECT '{name}',({query})" for name,query in queries.items())
        for line in psql(db,sql).splitlines():
            name,n=line.split('|'); results.append({'database':db,'check':name,'violations':int(n),'passed':int(n)==0})
    golden={}
    for db,table,columns in [('hotel_ops','bookings',['gross_vnd','discount_vnd','company_share_vnd','partner_share_vnd','customer_due_vnd']),('hotel_ops','meal_sessions',['actual_covers','ingredient_cost_vnd']),('entertainment_ops','ticket_orders',['gross_vnd','refunded_vnd']),('entertainment_ops','rentals',['agreed_vnd'])]:
        value=psql(db,'SELECT '+','.join(f'COALESCE(SUM({col}),0)' for col in columns)+f' FROM {table}')
        golden[db+'.'+table]=dict(zip(columns,map(int,value.split('|'))))
    output={'evaluated_at':now(),'checks':results,'passed':all(x['passed'] for x in results),'golden_aggregates_DO_NOT_USE_AS_TRANSFORM_INPUT':golden}
    save(ROOT/'reports/source_validation.json',output)
    golden_path=ROOT/'reports/reproducibility'/version_folder().name/'golden_aggregates.json'
    if golden_path.exists() and json.loads(golden_path.read_text(encoding='utf-8'))!=golden:
        raise RuntimeError('Source aggregates differ from frozen baseline. Baseline was NOT overwritten; version the source change explicitly.')
    if not golden_path.exists(): save(golden_path,golden)
    if not output['passed']: raise RuntimeError('Source invariant violation; inspect reports/source_validation.json')
    print(f"Source invariants passed: {len(results)}",flush=True)


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('action',choices=['all','up','load','ingest','lake','verify','query','status']); parser.add_argument('--sql'); args=parser.parse_args()
    setup()
    if args.action=='all':
        subprocess.run([sys.executable,'-X','utf8',str(ROOT/'src/generate.py')],check=True,cwd=ROOT)
        subprocess.run([sys.executable,'-X','utf8',str(ROOT/'src/audit_generation.py')],check=True,cwd=ROOT)
        dc('up','-d','--wait'); load(); validate_sources(); batch=ingest(); spark('build',batch); spark('verify',batch)
        subprocess.run([sys.executable,'-X','utf8',str(ROOT/'src/capture_provenance.py')],check=True,cwd=ROOT)
    elif args.action=='up': dc('up','-d','--wait')
    elif args.action=='load': load(); validate_sources()
    elif args.action=='ingest': ingest()
    elif args.action=='lake': spark('build',latest())
    elif args.action=='verify': validate_sources(); spark('verify',latest())
    elif args.action=='query': spark('query',sql=args.sql or 'SHOW DATABASES')
    else: dc('ps')


if __name__=='__main__': main()
