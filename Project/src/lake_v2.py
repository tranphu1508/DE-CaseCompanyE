"""V2 snapshot lake plus replay-aware receipt feed; separate persistent catalog."""
import argparse
import csv
import fcntl
import json
from decimal import Decimal

from pyspark.sql import functions as F, types as T, Window
import lake_job as base
from model_v2 import MODELS

ROOT=base.ROOT
LAKE=ROOT/'lake/v2'
CATALOG=LAKE/'catalog'
EVENT_FIELDS=['event_id','receipt_ref','revision','occurred_at','source_recorded_at','supplier_id','hotel_id','purchase_line_ref','accepted_qty','unit','unit_price_vnd']


def receipt_events(raw):
    """Retain source versions; choose by revision, never arrival order."""
    if set(EVENT_FIELDS+['received_at','delivery_id','_source_path'])-set(raw.columns):
        raise ValueError('Incomplete receipt event contract')
    raw=raw.withColumn('_payload_hash',F.sha2(F.to_json(F.struct(*EVENT_FIELDS)),256))
    # A repeated identity with different content is not an ordinary replay.
    if raw.groupBy('event_id').agg(F.countDistinct('_payload_hash').alias('n')).filter('n>1').limit(1).count():
        raise ValueError('Conflicting payload for same event_id')
    rank=Window.partitionBy('event_id').orderBy('received_at','delivery_id')
    dedup=raw.withColumn('_delivery_rank',F.row_number().over(rank))
    replay=dedup.filter('_delivery_rank>1')
    unique=dedup.filter('_delivery_rank=1')
    typed=(unique.withColumn('revision',F.col('revision').cast('int'))
        .withColumn('occurred_at',F.to_timestamp('occurred_at'))
        .withColumn('source_recorded_at',F.to_timestamp('source_recorded_at'))
        .withColumn('received_at',F.to_timestamp('received_at'))
        .withColumn('unit_price_vnd',F.col('unit_price_vnd').cast('long'))
        .withColumn('accepted_qty_kg',F.when(F.col('unit')=='kg',F.col('accepted_qty').cast('decimal(12,3)'))
                    .when(F.col('unit')=='g',(F.col('accepted_qty').cast('decimal(15,3)')/1000).cast('decimal(12,3)'))))
    typed=typed.withColumn('quality_reason',F.concat_ws('|',
        F.when(F.col('event_id').isNull() | F.col('receipt_ref').isNull() | F.col('purchase_line_ref').isNull(),'MISSING_KEY'),
        F.when(F.col('revision').isNull() | (F.col('revision')<1),'INVALID_REVISION'),
        F.when(F.col('unit').isNull() | ~F.col('unit').isin('kg','g'),'UNKNOWN_UNIT'),
        F.when(F.col('accepted_qty_kg').isNull() | (F.col('accepted_qty_kg')<0),'INVALID_QUANTITY'),
        F.when(F.col('unit_price_vnd').isNull() | (F.col('unit_price_vnd')<=0),'INVALID_PRICE'),
        F.when(F.col('occurred_at').isNull() | F.col('source_recorded_at').isNull() | F.col('received_at').isNull(),'INVALID_TIME'),
        F.when((F.col('source_recorded_at')<F.col('occurred_at')) | (F.col('received_at')<F.col('source_recorded_at')),'INVALID_TIME_ORDER')))
    valid=typed.filter("quality_reason=''")
    invalid=typed.filter("quality_reason<>''")
    if valid.groupBy('receipt_ref','revision').count().filter('count>1').limit(1).count():
        raise ValueError('Conflicting identities for same receipt revision')
    latest=(valid.withColumn('_revision_rank',F.row_number().over(Window.partitionBy('receipt_ref').orderBy(F.desc('revision'))))
        .filter('_revision_rank=1').drop('_revision_rank'))
    return valid,invalid,replay,latest


def feed(spark,batch,manifest,output):
    rawdir=LAKE/'raw'/batch/'external'
    schedule=base.read_json(rawdir/'delivery_schedule.json')['deliveries']
    paths=[]
    for d in schedule:
        path=rawdir/d['file']
        with path.open(encoding='utf-8',newline='') as stream:
            if next(csv.reader(stream))!=EVENT_FIELDS: raise ValueError('Receipt file header changed: '+d['file'])
        paths.append(str(path))
    schema=T.StructType([T.StructField(c,T.StringType()) for c in EVENT_FIELDS])
    raw=(spark.read.schema(schema).option('header',True).option('mode','FAILFAST').csv(paths)
         .withColumn('_source_path',F.input_file_name()).withColumn('_file',F.regexp_extract('_source_path',r'([^/]+)$',1)))
    meta=spark.createDataFrame([(d['file'],d['delivery_id'],d['received_at']) for d in schedule],
                              '_file string, delivery_id string, received_at string')
    raw=raw.join(F.broadcast(meta),'_file').drop('_file').cache()
    valid,invalid,replay,latest=receipt_events(raw)
    counts={'input_rows':raw.count(),'valid_versions':valid.count(),'quarantined':invalid.count(),
            'replayed_rows':replay.count(),'latest_receipts':latest.count()}
    assert counts['input_rows']==counts['valid_versions']+counts['quarantined']+counts['replayed_rows']
    counts['superseded_versions']=counts['valid_versions']-counts['latest_receipts']
    counts['late_unique_events']=valid.filter(F.unix_timestamp('received_at')-F.unix_timestamp('source_recorded_at')>172800).count()
    counts['out_of_order_receipts']=valid.groupBy('receipt_ref').agg(
        F.max(F.when(F.col('revision')==1,F.col('received_at'))).alias('v1'),
        F.max(F.when(F.col('revision')==2,F.col('received_at'))).alias('v2')).filter('v1>v2').count()
    for name,df in [('receipt_versions',valid),('receipt_quarantine',invalid),('receipt_replays',replay),('receipt_latest',latest)]:
        df=df.withColumn('_ingestion_batch',F.lit(batch)).withColumn('_source_system',F.lit('supplier_receipt_export'))
        base.register(spark,df,'companye_v2_external',name,output/'external'/name,
            'Biểu diễn bên ngoài của phiếu nhận; không cộng thành mua hàng mới.',{'companye.batch':batch,'companye.owner':'Procurement'})
    raw.unpersist()
    return counts


def build(spark,batch):
    report_path=ROOT/'reports'/f'lake_v2_build_{batch}.json'
    if report_path.exists() and base.read_json(report_path)['status']=='PASSED':
        verify(spark,batch); return
    manifest=base.read_json(LAKE/'raw'/batch/'ingestion_manifest.json'); output=LAKE/'standardized'/batch
    entries=[]
    try:
        for src in manifest['datasets']:
            path=LAKE/src['relative_path']
            assert base.checksum(path)==src['sha256'],'Raw checksum: '+str(path)
            if src['source_system'] not in MODELS:
                entries.append({**src,'description':'Lần gửi file phiếu nhận hoặc lịch giao file; chưa phải giao dịch mới.',
                    'grain':'Một file nguồn.','owner':'Procurement','raw_path':str(path),'quality_status':'RAW_PRESERVED'})
                continue
            db=src['source_system']; model=next(t for t in MODELS[db] if t.name==src['table'])
            raw=base.source_rows(spark,path,model)
            typed=raw.select(*[F.col(n).cast(base.datatype(t)).alias(n) for n,t,_,_ in model.columns]).cache()
            required=[n for n,_,r,_ in model.columns if 'PRIMARY KEY' in r or 'NOT NULL' in r]
            stats=typed.agg(F.count('*').alias('rows'),F.countDistinct(model.columns[0][0]).alias('pk'),
                *[F.sum(F.col(c).isNull().cast('int')).alias('missing_'+c) for c in required]).first().asDict()
            assert stats['rows']==src['row_count']==stats['pk'] and not any(v for k,v in stats.items() if k.startswith('missing_')),stats
            casts=[F.sum((F.col(n).isNotNull() & F.col(n).cast(base.datatype(t)).isNull()).cast('int')).alias(n) for n,t,_,_ in model.columns if t!='TEXT']
            if casts: assert not any(raw.agg(*casts).first()),'Invalid cast in '+model.name
            namespace='companye_v2_'+('hotel' if db=='hotel_ops' else 'entertainment')
            target=output/db/model.name
            lined=base.add_lineage(typed,db,path,batch,manifest['ingested_at_utc'])
            actual=base.register(spark,lined,namespace,model.name,target,model.description,
                {'companye.batch':batch,'companye.source_sha256':src['sha256'],'companye.owner':model.owner,'companye.grain':model.grain})
            assert actual.count()==src['row_count']
            entries.append({**src,**model.contract(),'catalog_table':namespace+'.'+model.name,'raw_path':str(path),
                'standardized_path':str(target),'quality_status':'VALIDATED'})
            typed.unpersist()
            print('V2 REGISTERED',namespace+'.'+model.name,src['row_count'],flush=True)
        quality=feed(spark,batch,manifest,output)
        base.metadata_tables(spark,entries,manifest,batch,output)
        # Catalog the derived external datasets with their actual columns and row counts.
        derived=[]
        for name in ['receipt_versions','receipt_quarantine','receipt_replays','receipt_latest']:
            table='companye_v2_external.'+name; df=spark.table(table)
            derived.append({'dataset_id':table,'catalog_table':table,'grain':'Một sự kiện nguồn/phiên bản; latest là một phiếu nhận.',
                'owner':'Procurement','row_count':df.count(),'standardized_path':str(output/'external'/name),
                'columns':[{'name':f.name,'type':f.dataType.simpleString(),'nullable':f.nullable} for f in df.schema.fields],
                'upstream_datasets':[e['dataset_id'] for e in entries if e['source_system']=='external_suppliers_or_distributors']})
        base.save(CATALOG/'catalog.json',{'batch_id':batch,'datasets':entries,'derived_datasets':derived,
            'backend':'Separate persistent Hive/Derby catalog for v2','synthetic':True})
        derived_df=spark.createDataFrame([(d['dataset_id'],json.dumps(d,ensure_ascii=False)) for d in derived],'dataset_id string, metadata_json string')
        base.register(spark,derived_df,'companye_metadata','derived_datasets',output/'metadata/derived_datasets','Catalog bảng dẫn xuất nguồn ngoài.',{'companye.batch':batch})
        base.save(report_path,{'status':'PASSED','batch_id':batch,'tables':sum(len(v) for v in MODELS.values()),'external_quality':quality})
    except Exception as e:
        base.save(report_path,{'status':'FAILED','batch_id':batch,'error':str(e)}); raise


def verify(spark,batch):
    manifest=base.read_json(LAKE/'raw'/batch/'ingestion_manifest.json')
    checks=[]
    for src in manifest['datasets']:
        assert base.checksum(LAKE/src['relative_path'])==src['sha256']
        if src['source_system'] not in MODELS: continue
        full='companye_v2_'+('hotel' if src['source_system']=='hotel_ops' else 'entertainment')+'.'+src['table']
        df=spark.table(full)
        assert df.count()==src['row_count']
        assert [r[0] for r in df.select('_ingestion_batch').distinct().collect()]==[batch]
        checks.append(full)
    golden=base.read_json(ROOT/'reports/reproducibility/v2/source_aggregates.json')
    for key,values in golden.items():
        db,table=key.split('.'); full='companye_v2_'+('hotel' if db=='hotel_ops' else 'entertainment')+'.'+table
        actual=spark.table(full).agg(*[F.sum(c).alias(c) for c in values]).first().asDict()
        assert all(Decimal(str(actual[c]))==Decimal(value) for c,value in values.items()),full
    mismatch=spark.sql('''SELECT count(*) n FROM companye_v2_external.receipt_latest e
        LEFT JOIN companye_v2_hotel.receipts r ON e.receipt_ref=r.receipt_id
        LEFT JOIN companye_v2_hotel.purchase_lines l ON r.purchase_line_id=l.purchase_line_id
        LEFT JOIN companye_v2_hotel.purchase_orders p ON l.purchase_order_id=p.purchase_order_id
        WHERE r.receipt_id IS NULL OR e.accepted_qty_kg<>r.accepted_qty OR e.unit_price_vnd<>l.unit_price_vnd
           OR e.purchase_line_ref<>l.purchase_line_id OR e.hotel_id<>p.hotel_id OR e.supplier_id<>p.supplier_id''').first()['n']
    assert mismatch==0,'Latest receipt export differs from source'
    assert spark.sql("SELECT count(*) FROM companye_metadata.datasets WHERE raw_path LIKE '%audit_only%' OR raw_path LIKE '%truth%'").first()[0]==0
    quality=base.read_json(ROOT/'reports'/f'lake_v2_build_{batch}.json')['external_quality']
    assert quality['replayed_rows']>0 and quality['out_of_order_receipts']>0 and quality['late_unique_events']>0
    catalog=base.read_json(CATALOG/'catalog.json')
    assert spark.table('companye_metadata.datasets').count()==len(catalog['datasets'])
    assert spark.table('companye_metadata.derived_datasets').count()==4
    report={'status':'PASSED','batch_id':batch,'structured_tables':len(checks),'external_source_mismatches':mismatch,
        'external_quality':quality,'numeric_aggregate_tables':len(golden),'checked_at':base.utc()}
    base.save(ROOT/'reports/lake_v2_validation.json',report); print(json.dumps(report),flush=True)


def main():
    p=argparse.ArgumentParser(); p.add_argument('action',choices=['build','verify','query']); p.add_argument('--batch'); p.add_argument('--sql'); args=p.parse_args()
    base.LAKE=LAKE; base.CATALOG=CATALOG; CATALOG.mkdir(parents=True,exist_ok=True)
    with (CATALOG/'.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        spark=base.session(); spark.sparkContext.setLogLevel('WARN')
        try:
            if args.action=='build': build(spark,args.batch)
            elif args.action=='verify': verify(spark,args.batch)
            else: spark.sql(args.sql or 'SHOW DATABASES').show(100,truncate=False)
        finally: spark.stop()


if __name__=='__main__': main()
