from pathlib import Path
from datetime import datetime,timezone
from decimal import Decimal
import argparse,json,hashlib
from analytics_runtime.session import create_session
from publication.core import Reader,read,save,file_hash,Coordinator
from semantic.queries import IDS,COUNTS,build,VERSION
from semantic.service import SemanticSession
from semantic.reference import RawReference

ROOT=Path('/workspace');OUT=ROOT/'reports/semantic';OUT.mkdir(exist_ok=True)

def code_hashes():
    paths=list((ROOT/'src/semantic').glob('*.py'))+[ROOT/'scripts/kpi-pipeline.py',ROOT/'config/kpi_contract_v1.json',ROOT/'config/source_target_mapping_v1.json']
    return {p.relative_to(ROOT).as_posix():file_hash(p) for p in paths}

def cases(phase,reference):
    if phase=='baseline':return [('baseline',g,{},None) for g in COUNTS]
    out=[]
    # All metrics across month boundaries and all four sites.
    for s,e in [('2024-01-01','2024-02-01'),('2024-02-01','2024-03-01'),('2025-12-01','2026-01-01')]:
        for g in COUNTS:out.append((s,g,dict(start=s,end=e),None))
    for site in ['SP','DN','DL','PQ']:
        for g in COUNTS:out.append(('site_'+site,g,dict(filters={'site':site}),None))
    for item in reference.h('items'):
        for g in ['B06','B07']:out.append(('item_'+item['item_id'],g,dict(filters={'item':item['item_id']}),None))
    for channel in ['AGODA','BOOKING']:
        out.extend([('channel_'+channel,g,dict(filters={'channel':channel}),[g+'.04',g+'.05'] if g=='B01' else None) for g in ['B01','B02','B03']])
    for meal in ['BREAKFAST','LUNCH','DINNER','BAR']:out.append(('meal_'+meal,'B04',dict(filters={'meal':meal}),None))
    for severe in [0,1]:out.append(('weather_'+str(severe),'B05',dict(filters={'severe_weather':severe}),None))
    out.extend([
      ('hotel','B04',dict(filters={'hotel':'DL-3'}),None),('stars','B02',dict(filters={'stars':5}),None),
      ('roomtype','B01',dict(filters={'room_type':'DELUXE'}),None),
      ('roomtype','B08',dict(filters={'room_type':'DELUXE'}),['B08.02','B08.03','B08.04']),
      ('early_assessment','B06',dict(start='2024-01-01',end='2024-02-01',assessment='2024-01-01',filters={'item':'RICE'}),None),
      ('carry_in','B07',dict(start='2024-02-01',end='2024-02-02',filters={'item':'RICE'}),None),
      ('asset','B08',dict(filters={'asset_type':'AC','work_type':'BREAKDOWN'}),['B08.01']),
      ('outdoor','B05',dict(filters={'outdoor':1}),['B05.01','B05.02','B05.03'])])
    # Individually exercise the remaining declared slicers, using observed members.
    extras=[('promotion','B02','promotion',reference.h('promotions')[0]['promotion_id'],None),
      ('outlet','B04','outlet',reference.h('outlets')[0]['outlet_id'],None),
      ('centre','B05','centre',reference.e('centres')[0]['centre_id'],None),
      ('activity','B05','activity',reference.e('activities')[0]['activity_id'],['B05.01','B05.02','B05.03']),
      ('vehicle','B05','vehicle_type',reference.e('vehicles')[0]['vehicle_type'],['B05.04','B05.05','B05.06']),
      ('supplier','B06','supplier',reference.h('suppliers')[0]['supplier_id'],['B06.07']),
      ('supplier','B07','supplier',reference.h('suppliers')[0]['supplier_id'],['B07.05','B07.06']),
      ('usage_area','B07','usage_area','BUFFET',['B07.03'])]
    for label,g,key,value,metrics in extras:
        filters={key:value}
        if key=='usage_area':filters['item']='RICE'
        out.append((label,g,dict(filters=filters),metrics))
    return out

def run(spark,phase):
    reference=RawReference(ROOT/'lake/v2');checks=[];queries=OUT/'sql';queries.mkdir(exist_ok=True)
    with Reader(spark,'semantic-'+phase,ttl=600) as reader:
        session=SemanticSession(reader);pid=reader.pid
        assert reader.manifest['source_catalog_sha256']==file_hash(ROOT/'lake/v2/catalog/catalog.json')
        for label,group,ctx,metrics in cases(phase,reference):
            print('KPI '+phase+' '+label+' '+group,flush=True)
            expected=reference.compute(group,ctx)
            oracle=session.query(group,ctx,'oracle',metrics);ice=session.query(group,ctx,'iceberg',metrics)
            assert oracle['metrics']==ice['metrics'],(label,group,'engine mismatch')
            for mid,value in oracle['metrics'].items():
                assert (value['diagnostic_accepted_numerator'],value['diagnostic_accepted_denominator'])==expected[mid],(label,mid,value,expected[mid])
            sql,ids,ratios=build(group,ctx,metrics)
            if phase=='baseline':
                (queries/(group+'.sql')).write_text('-- Publication Reader placeholders; half-open period and final snapshot.\n'+sql+'\n',encoding='utf8')
                for mid in ids:
                    individual,_,_=build(group,ctx,[mid]);(queries/(mid+'.sql')).write_text('-- KPI '+mid+'; numerator, denominator, SQL value. Quality policy also required.\n'+individual+'\n',encoding='utf8')
            checks.append(dict(case=label,group=group,context=ctx,selected=list(oracle['metrics']),oracle=oracle['metrics'],iceberg_equal=True,raw_reference_equal=True,sql_sha256=hashlib.sha256(sql.encode()).hexdigest()))
            # Partial progress is never called a completed acceptance report.
            save(OUT/(phase+'-progress.json'),dict(status='RUNNING',publication_id=pid,completed=len(checks),checks=checks))
    co=Coordinator(spark)
    try:
        assert co.active()==pid
        assert co.db.query('SELECT count(*) FROM ce_control.reader_lease WHERE expires_at>clock_timestamp()')[0][0]=='0'
    finally:co.close()
    save(OUT/(phase+'.json'),dict(status='PASSED',phase=phase,publication_id=pid,semantic_version=VERSION,checked_at=datetime.now(timezone.utc).isoformat(),source_files_checked=reference.source_files,group_queries=len(checks)*2,metric_comparisons=sum(len(c['selected']) for c in checks),code_sha256=code_hashes(),checks=checks))
    print('PASSED '+phase+' '+str(len(checks))+' group cases',flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('phase');args=ap.parse_args();spark=create_session('CompanyE-semantic-'+args.phase)
    try:
        if args.phase=='fixtures':
            from semantic.fixtures import run as fixtures
            fixtures(spark,OUT,code_hashes)
        else:run(spark,args.phase)
    finally:spark.stop()
