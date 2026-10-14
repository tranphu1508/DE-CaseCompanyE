"""Spark batch lake with persistent embedded Hive Metastore and explicit metadata.

Local single-writer deployment; external Parquet tables are NOT an ACID lakehouse.
"""
import argparse
import fcntl
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from pyspark.sql import SparkSession, functions as F, types as T, Window
from model import MODELS

ROOT=Path('/workspace'); LAKE=ROOT/'lake'; CATALOG=LAKE/'catalog'


def utc(): return datetime.now(timezone.utc).isoformat()
def read_json(p): return json.loads(p.read_text(encoding='utf-8'))
def save(p,data):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
def checksum(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def literal(s): return "'"+str(s).replace("'","''")+"'"


def session():
    return (SparkSession.builder.appName('CompanyE Basic Data Lake')
        .config('spark.sql.warehouse.dir',str(CATALOG/'warehouse'))
        .config('spark.hadoop.javax.jdo.option.ConnectionURL',f'jdbc:derby:;databaseName={CATALOG}/hive_state/metastore_db;create=true')
        .config('spark.hadoop.datanucleus.schema.autoCreateAll','true')
        .config('spark.sql.session.timeZone','Asia/Ho_Chi_Minh')
        .config('spark.sql.shuffle.partitions','2')
        .config('spark.sql.ansi.enabled','false')
        .config('spark.sql.legacy.timeParserPolicy','CORRECTED')
        .enableHiveSupport().getOrCreate())


def datatype(sql):
    if sql=='TEXT': return T.StringType()
    if sql=='INTEGER': return T.IntegerType()
    if sql=='BIGINT': return T.LongType()
    if sql=='DATE': return T.DateType()
    if sql=='TIMESTAMPTZ': return T.TimestampType()
    if sql.startswith('NUMERIC'): return T.DecimalType(12,3)
    raise ValueError(sql)


def register(spark, df, database, table, path, description, props):
    spark.sql(f'CREATE DATABASE IF NOT EXISTS {database}')
    full=f'{database}.{table}'
    if not path.exists(): df.coalesce(2).write.mode('errorifexists').parquet(str(path))
    actual=spark.read.parquet(str(path))
    if spark.catalog.tableExists(full):
        existing=spark.table(full).schema
        if existing.simpleString()!=actual.schema.simpleString():
            raise RuntimeError(f'Schema evolution requires an explicit migration: {full}')
        spark.sql(f'ALTER TABLE {full} SET LOCATION {literal(path.as_uri())}')
        spark.catalog.refreshTable(full)
    else:
        spark.sql(f'CREATE TABLE {full} USING PARQUET LOCATION {literal(path.as_uri())}')
    properties={'comment':description,'companye.synthetic':'true',**props}
    spark.sql(f"ALTER TABLE {full} SET TBLPROPERTIES ("+','.join(literal(k)+'='+literal(v) for k,v in properties.items())+')')
    return actual


def add_lineage(df, source, path, batch, ingested_at):
    return (df.withColumn('_source_system',F.lit(source))
              .withColumn('_source_path',F.lit(str(path)))
              .withColumn('_ingestion_batch',F.lit(batch))
              .withColumn('_ingested_at_utc',F.to_timestamp(F.lit(ingested_at))))


def normalize_supplier(spark, batch, manifest, output):
    src=LAKE/'raw'/batch/'external/supplier_mixed.csv'
    raw=spark.read.option('header',True).option('sep',';').option('encoding','UTF-8').csv(str(src))
    normalized=(raw.withColumn('service_date',F.to_date('Date','dd/MM/yyyy'))
        .withColumn('quantity',F.col('Qty').cast('decimal(12,3)'))
        .withColumn('unit_price_vnd',F.when(F.col('Price').rlike(r'^\d+k$'),F.regexp_replace('Price','k$','').cast('long')*1000).otherwise(F.col('Price').cast('long')))
        .withColumn('item_id',F.when(F.lower(F.col('Item')).isin('cà chua','ca chua'),'TOMATO')))
    # Identical business document IDs are not counted twice. Original rows remain in raw.
    normalized=normalized.withColumn('_duplicate_rank',F.row_number().over(Window.partitionBy('Supplier','Document').orderBy('Hotel','Item','Qty','Price','Date')))
    normalized=normalized.withColumn('quality_reason',F.concat_ws('|',
        F.when(F.col('service_date').isNull(),'INVALID_DATE'),
        F.when(F.col('Unit')!='kg','UNKNOWN_UNIT_CONVERSION'),
        F.when(F.col('quantity').isNull() | (F.col('quantity')<=0),'INVALID_QUANTITY'),
        F.when(F.col('unit_price_vnd').isNull(),'INVALID_PRICE'),
        F.when(F.col('item_id').isNull(),'UNKNOWN_ITEM'),
        F.when(F.col('_duplicate_rank')>1,'DUPLICATE_DOCUMENT')))
    normalized=add_lineage(normalized,'local_supplier',src,batch,manifest['ingested_at_utc']).cache()
    bad=normalized.filter(F.col('quality_reason')!='')
    good=normalized.filter(F.col('quality_reason')=='').select(
        F.col('Supplier').alias('supplier_id'),F.col('Hotel').alias('hotel_id'),F.col('Document').alias('document_id'),
        'service_date','item_id',F.col('Unit').alias('unit'),'quantity','unit_price_vnd',
        '_source_system','_source_path','_ingestion_batch','_ingested_at_utc')
    raw_count=raw.count(); good_count=good.count(); bad_count=bad.count()
    if raw_count!=good_count+bad_count: raise RuntimeError('Supplier row conservation failed')
    reasons={r['quality_reason']:r['count'] for r in bad.groupBy('quality_reason').count().collect()}
    register(spark,good,'companye_external','supplier_deliveries',output/'external/supplier_deliveries','Dòng nhà cung cấp được chuẩn hóa; không tự coi là phiếu nhập kho đã duyệt.',{'companye.batch':batch,'companye.owner':'Procurement','companye.source_sha256':checksum(src)})
    register(spark,bad,'companye_external','supplier_quarantine',LAKE/'quarantine'/batch/'supplier_mixed','Dòng cần xác minh, vẫn giữ các giá trị gốc và lý do.',{'companye.batch':batch,'companye.owner':'Procurement'})
    normalized.unpersist()
    return {'dataset_id':'external.supplier_mixed','input_rows':raw_count,'accepted_rows':good_count,'quarantined_rows':bad_count,'reasons':reasons,'passed':raw_count==good_count+bad_count}


def metadata_tables(spark, entries, manifest, batch, output):
    rows=[]; cols=[]
    for entry in entries:
        rows.append((entry['dataset_id'],entry['source_system'],entry.get('catalog_table'),entry['description'],entry['grain'],entry['owner'],entry['format'],entry['raw_path'],entry.get('standardized_path'),entry.get('row_count'),entry['sha256'],entry['bytes'],batch,manifest['ingested_at_utc'],entry['quality_status'],True))
        for col in entry.get('columns',[]):
            cols.append((entry['dataset_id'],col['name'],col['sql_type'],col['description'],col['nullable'],col['constraints'],col['classification'],col.get('unit')))
    schema='dataset_id string, source_system string, catalog_table string, description string, grain string, owner string, format string, raw_path string, standardized_path string, row_count long, source_sha256 string, source_bytes long, batch_id string, ingested_at_utc string, quality_status string, synthetic boolean'
    register(spark,spark.createDataFrame(rows,schema),'companye_metadata','datasets',output/'metadata/datasets','Catalog nghiệp vụ và kỹ thuật của từng nguồn; bao gồm file chưa cấu trúc.',{'companye.batch':batch,'companye.owner':'Data Engineering'})
    col_schema='dataset_id string, column_name string, sql_type string, description string, nullable boolean, constraints string, classification string, unit string'
    register(spark,spark.createDataFrame(cols,col_schema),'companye_metadata','columns',output/'metadata/columns','Từ điển cột, khóa, ràng buộc, đơn vị và phân loại.',{'companye.batch':batch,'companye.owner':'Data Engineering'})
    artifacts=[]
    for entry in entries:
        if entry['source_system']=='external_suppliers_or_distributors':
            artifacts.append((entry['dataset_id'],entry['raw_path'],entry['format'],entry['sha256'],entry['bytes'],entry['quality_status'],batch))
    artifact_schema='dataset_id string, raw_path string, format string, sha256 string, bytes long, status string, batch_id string'
    register(spark,spark.createDataFrame(artifacts,artifact_schema),'companye_metadata','artifacts',output/'metadata/artifacts','Catalog file ngoài, kể cả nội dung cần kiểm tra thủ công.',{'companye.batch':batch})


def build(spark, batch):
    root=LAKE/'raw'/batch; manifest=read_json(root/'ingestion_manifest.json')
    report_path=ROOT/'reports'/f'lake_build_{batch}.json'
    if report_path.exists() and read_json(report_path).get('status')=='PASSED':
        print('Batch already built; verifying persisted catalog instead of appending duplicate data.',flush=True)
        verify(spark,batch); return
    started=utc(); output=LAKE/'standardized'/batch
    entries=[]; checks=[]
    for src in manifest['datasets']:
        p=LAKE/src['relative_path']
        if checksum(p)!=src['sha256']: raise RuntimeError('Raw checksum mismatch: '+str(p))
        if src['source_system'] not in MODELS:
            descriptions={
                'supplier_mixed':('Bảng thương nhân cố ý chưa chuẩn hóa.','Một dòng chứng từ bên ngoài.','NORMALIZED_WITH_QUARANTINE'),
                'supplier_message':('Nội dung trao đổi thiếu quy cách, cần xác minh.','Một nội dung trao đổi.','NEEDS_REVIEW'),
                'supplier_delivery_scan':('Ảnh SVG chứng từ giả lập, chưa OCR.','Một ảnh minh họa chứng từ.','NEEDS_REVIEW'),
                'supplier_updates':('Các phiên bản điều chỉnh của chứng từ.','Một thông báo điều chỉnh.','RAW_ONLY'),
                'vendor_settlement':('Bản kê đối tác; không được cộng như một giao dịch thu độc lập.','Một dòng đối soát.','RAW_ONLY')}
            desc,grain,status=descriptions[src['table']]
            entries.append({**src,'description':desc,'grain':grain,'owner':'Procurement' if src['table'].startswith('supplier') else 'Distribution Finance','raw_path':str(p),'standardized_path':str(output/'external/supplier_deliveries') if src['table']=='supplier_mixed' else None,'quality_status':status,'catalog_table':'companye_external.supplier_deliveries' if src['table']=='supplier_mixed' else None})
            continue
        db=src['source_system']; name=src['table']; model=next(t for t in MODELS[db] if t.name==name)
        # String landing first, then explicit contract casts; no inferSchema drift.
        raw_schema=T.StructType([T.StructField(n,T.StringType(),True) for n,_,_,_ in model.columns])
        raw=spark.read.schema(raw_schema).option('header',True).option('nullValue','\\N').option('escape','"').option('multiLine',True).option('mode','FAILFAST').csv(str(p))
        typed=raw.select([F.col(n).cast(datatype(typ)).alias(n) for n,typ,_,_ in model.columns]).cache()
        aggregations=[F.count('*').alias('_count'),F.countDistinct(model.columns[0][0]).alias('_distinct_pk')]
        for n,typ,rules,desc in model.columns:
            if 'NOT NULL' in rules or 'PRIMARY KEY' in rules:
                aggregations.append(F.sum(F.when(F.col(n).isNull(),1).otherwise(0)).alias('null_'+n))
        stat=typed.agg(*aggregations).first().asDict()
        bad_nulls={k:v for k,v in stat.items() if k.startswith('null_') and v}
        # Cast failures on nullable fields must not silently become missing values.
        casts=[F.sum(F.when(F.col(n).isNotNull() & F.col(n).cast(datatype(t)).isNull(),1).otherwise(0)).alias(n) for n,t,_,_ in model.columns if t!='TEXT']
        bad_casts={k:v for k,v in raw.agg(*casts).first().asDict().items() if v} if casts else {}
        passed=stat['_count']==src['row_count'] and stat['_distinct_pk']==stat['_count'] and not bad_nulls and not bad_casts
        check={'dataset_id':src['dataset_id'],'rows':stat['_count'],'distinct_pk':stat['_distinct_pk'],'invalid_required':bad_nulls,'invalid_casts':bad_casts,'passed':passed}
        checks.append(check)
        if not passed:
            save(report_path,{'status':'FAILED','started_at':started,'checks':checks}); raise RuntimeError(str(check))
        target=output/db/name
        full=f"companye_{'hotel' if db=='hotel_ops' else 'entertainment'}.{name}"
        lined=add_lineage(typed,db,p,batch,manifest['ingested_at_utc'])
        actual=register(spark,lined,full.split('.')[0],name,target,model.description,{'companye.batch':batch,'companye.source':src['dataset_id'],'companye.source_sha256':src['sha256'],'companye.owner':model.owner,'companye.grain':model.grain})
        if actual.count()!=src['row_count']: raise RuntimeError('Parquet row count mismatch: '+name)
        entries.append({**src,**model.contract(),'dataset_id':src['dataset_id'],'catalog_table':full,'raw_path':str(p),'standardized_path':str(target),'quality_status':'VALIDATED'})
        typed.unpersist()
        print(f"REGISTERED {full}: {src['row_count']:,} rows",flush=True)
    external=normalize_supplier(spark,batch,manifest,output)
    for entry in entries:
        if entry['dataset_id']=='external.supplier_mixed':
            entry['row_count']=external['input_rows']; entry['accepted_rows']=external['accepted_rows']; entry['quarantined_rows']=external['quarantined_rows']
    metadata_tables(spark,entries,manifest,batch,output)
    catalog={'catalog_backend':'Apache Hive Metastore / embedded Derby; persisted single-writer local deployment','spark_version':spark.version,'batch_id':batch,'created_at':utc(),'synthetic':True,'datasets':entries}
    save(CATALOG/f'catalog_{batch}.json',catalog)
    save(CATALOG/'catalog.json',catalog)
    index=['# CompanyE Data Catalog','',f'Batch: `{batch}`. Dữ liệu giả lập; Hive Metastore lưu schema và vị trí bảng.','', '| Dataset | Rows | Quality | SQL table |','|---|---:|---|---|']
    index += [f"| {e['dataset_id']} | {e.get('row_count') if e.get('row_count') is not None else '—'} | {e['quality_status']} | {e.get('catalog_table') or 'companye_metadata.artifacts'} |" for e in entries]
    (CATALOG/'CATALOG.md').write_text('\n'.join(index)+'\n',encoding='utf-8')
    save(report_path,{'status':'PASSED','batch_id':batch,'started_at':started,'finished_at':utc(),'structured_tables':len(checks),'row_count':sum(x['rows'] for x in checks),'checks':checks,'external_quality':external,'raw_manifest_sha256':checksum(root/'ingestion_manifest.json')})
    print(json.dumps({'status':'PASSED','batch':batch,'tables':len(checks),'supplier_quality':external},ensure_ascii=False),flush=True)


def verify(spark,batch):
    manifest=read_json(LAKE/'raw'/batch/'ingestion_manifest.json')
    results=[]
    for src in manifest['datasets']:
        p=LAKE/src['relative_path']
        if checksum(p)!=src['sha256']: raise RuntimeError('Raw data changed: '+str(p))
        if src['source_system'] not in MODELS: continue
        prefix='hotel' if src['source_system']=='hotel_ops' else 'entertainment'
        full=f"companye_{prefix}.{src['table']}"
        rows=spark.table(full).count()
        batches=[r[0] for r in spark.table(full).select('_ingestion_batch').distinct().collect()]
        passed=rows==src['row_count'] and batches==[batch]
        results.append({'table':full,'rows':rows,'passed':passed})
        if not passed: raise RuntimeError('Persisted catalog mismatch: '+full)
    golden=read_json(ROOT/'reports'/'reproducibility'/manifest['source_dataset_version']/'golden_aggregates.json')
    aggregates=[]
    for key,expected in golden.items():
        db,table=key.split('.'); full=f"companye_{'hotel' if db=='hotel_ops' else 'entertainment'}.{table}"
        actual=spark.table(full).agg(*[F.sum(c).alias(c) for c in expected]).first().asDict()
        aggregates.append({'table':full,'expected':expected,'actual':actual,'passed':actual==expected})
    if not all(x['passed'] for x in aggregates): raise RuntimeError('Golden source-to-lake aggregates mismatch')
    rejected=spark.table('companye_external.supplier_quarantine').count()
    accepted=spark.table('companye_external.supplier_deliveries').count()
    if accepted+rejected!=121: raise RuntimeError('External source row conservation failed')
    # Key real business invariants after typed loading. These do not use hidden identity truth.
    invariant_sql={
        'breakfast_policy':"SELECT count(*) n FROM companye_hotel.rate_plans p JOIN companye_hotel.hotels h ON p.hotel_id=h.hotel_id WHERE h.stars=5 AND p.breakfast_included<>1",
        'funding_balance':"SELECT count(*) n FROM companye_hotel.bookings WHERE discount_vnd<>company_share_vnd+partner_share_vnd OR customer_due_vnd<>gross_vnd-discount_vnd",
        'no_source_truth_in_catalog':"SELECT count(*) n FROM companye_metadata.datasets WHERE lower(raw_path) LIKE '%audit_only%' OR lower(dataset_id) LIKE '%truth%'",
        'cross_system_booking_refs':"SELECT count(*) n FROM companye_entertainment.ticket_orders t LEFT JOIN companye_hotel.bookings b ON t.hotel_booking_ref=b.booking_id WHERE t.hotel_booking_ref IS NOT NULL AND b.booking_id IS NULL"
    }
    invariants={name:spark.sql(query).first()['n'] for name,query in invariant_sql.items()}
    if any(invariants.values()): raise RuntimeError(str(invariants))
    report={'status':'PASSED','checked_at':utc(),'batch_id':batch,'persisted_hive_tables':results,'source_vs_lake_aggregates':aggregates,'invariants':invariants,'supplier_accepted':accepted,'supplier_quarantined':rejected,'catalog_implementation':spark.conf.get('spark.sql.catalogImplementation')}
    save(ROOT/'reports/lake_validation.json',report)
    print(json.dumps({'status':'PASSED','persisted_tables':len(results),'catalog':report['catalog_implementation'],'accepted':accepted,'quarantined':rejected},ensure_ascii=False),flush=True)


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('action',choices=['build','verify','query']); parser.add_argument('--batch'); parser.add_argument('--sql'); args=parser.parse_args()
    CATALOG.mkdir(parents=True,exist_ok=True)
    with (CATALOG/'.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        spark=session(); spark.sparkContext.setLogLevel('WARN')
        try:
            if args.action=='build': build(spark,args.batch)
            elif args.action=='verify': verify(spark,args.batch)
            else: spark.sql(args.sql or 'SHOW DATABASES').show(100,truncate=False)
        finally: spark.stop()


if __name__=='__main__': main()
