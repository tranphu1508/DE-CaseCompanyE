import csv
from pathlib import Path
from pyspark.sql import functions as F,types as T
from analytics_runtime.dimension_transform import read_sources,sql_type
from lake_v2 import receipt_events,EVENT_FIELDS
from lakehouse_b.common import *

def table_name(dataset):
    domain,name=dataset.split('.')
    return 'ce.'+{'hotel_ops':'silver_hotel','entertainment_ops':'silver_entertainment','external':'silver_external'}[domain]+'.'+name
def build(spark,fail_after=0):
    catalog=read(LAKE/'catalog/catalog.json');mapping=read(CONFIG/'source_target_mapping_v1.json')
    for ds in catalog['datasets']:
        p=(LAKE/ds['relative_path']).resolve()
        assert LAKE in p.parents and sha(p)==ds['sha256'],'Raw input changed: '+ds['dataset_id']
    business=[d for d in catalog['datasets'] if 'columns' in d]
    mapping=dict(mapping,entities=[{'id':'D_ALL','aliases':{str(i):d['dataset_id'] for i,d in enumerate(business)}}])
    version=code_version();parent=LAKE/'manifests/silver';parent.mkdir(parents=True,exist_ok=True)
    source_hash=sha(LAKE/'catalog/catalog.json');runid='silver_'+digest([source_hash,version])[:20]
    path=parent/(runid+'.json')
    if path.exists():
        report=read(path)
        for spec in report['tables'].values():
            rows=[r.asDict(recursive=True) for r in pinned(spark,spec).select(*spec['columns']).collect()]
            assert row_hash(rows,spec['columns'])==spec['content_sha256']
        save(LAKE/'manifests/silver-active.json',{'path':str(path),'sha256':sha(path)})
        save(OUT/'silver.json',report);print('Silver replay verified',flush=True);return report
    sources,quality=read_sources(spark,LAKE,catalog,mapping)
    specs={}
    for d in business:
        name=d['dataset_id'];cols=[c['name'] for c in d['columns']]
        schema=', '.join('`'+c['name']+'` '+sql_type(c['sql_type']) for c in d['columns'])
        rows=sources.get(name,[])
        df=spark.createDataFrame([tuple(r[c] for c in cols) for r in rows],schema)
        df=df.withColumn('_source_batch_id',F.lit(catalog['batch_id'])).withColumn('_source_system',F.lit(d['source_system'])).withColumn('_source_sha256',F.lit(d['sha256']))
        spec=put_table(spark,table_name(name),df,df.columns)
        spec['business_columns']=cols;spec['raw_sha256']=d['sha256'];spec['quality']=quality['source_status'][name]
        specs[name]=spec
        print('Silver '+name+' '+str(spec['rows']),flush=True)
        if fail_after and len(specs)==fail_after:raise RuntimeError('INJECTED_FAILURE_AFTER_SILVER_TABLE')
    rawdir=LAKE/'raw'/catalog['batch_id']/'external';schedule=read(rawdir/'delivery_schedule.json')['deliveries']
    paths=[]
    for d in schedule:
        p=(rawdir/d['file']).resolve();assert rawdir in p.parents,'Invalid schedule path'
        with p.open(encoding='utf8',newline='') as stream:assert next(csv.reader(stream))==EVENT_FIELDS
        paths.append(str(p))
    schema=T.StructType([T.StructField(c,T.StringType()) for c in EVENT_FIELDS])
    raw=spark.read.schema(schema).option('header',True).option('mode','FAILFAST').csv(paths).withColumn('_source_path',F.input_file_name()).withColumn('_file',F.regexp_extract('_source_path',r'([^/]+)$',1))
    meta=spark.createDataFrame([(d['file'],d['delivery_id'],d['received_at']) for d in schedule],'_file string, delivery_id string, received_at string')
    raw=raw.join(F.broadcast(meta),'_file').drop('_file').cache()
    # Legacy normalization quarantines malformed values; ANSI is restored immediately.
    spark.conf.set('spark.sql.ansi.enabled','false')
    try:
        frames=receipt_events(raw);counts={}
        for name,df in zip(['receipt_versions','receipt_quarantine','receipt_replays','receipt_latest'],frames):
            df=df.withColumn('_ingestion_batch',F.lit(catalog['batch_id'])).withColumn('_source_system',F.lit('supplier_receipt_export'))
            spec=put_table(spark,table_name('external.'+name),df,df.columns)
            specs['external.'+name]=spec;counts[name]=spec['rows']
        counts['input_rows']=raw.count()
        assert counts['input_rows']==sum(counts[n] for n in ['receipt_versions','receipt_quarantine','receipt_replays'])
    finally:spark.conf.set('spark.sql.ansi.enabled','true');raw.unpersist()
    save(LAKE/'quarantine'/runid/'source-quality.json',quality)
    report={'status':'PASSED','run_id':runid,'source_batch_id':catalog['batch_id'],'source_catalog_sha256':source_hash,'transform_version':version,'created_at':now(),'tables':specs,'source_quality':quality,'external_counts':counts,'limitations':['Local input adapter retains the existing 100000-row per-source bound.','Initial immutable source batch; later ingestion batches require a reviewed version transition.']}
    immutable(path,report);save(OUT/'silver.json',report)
    save(LAKE/'manifests/silver-active.json',{'path':str(path),'sha256':sha(path)})
    return report

def load(spark,manifest):
    """Gold has no fallback to raw or standardized file paths."""
    sources={};external={}
    for name,spec in manifest['tables'].items():
        cols=spec.get('business_columns',spec['columns'])
        rows=[r.asDict(recursive=True) for r in pinned(spark,spec).select(*cols).collect()]
        assert len(rows)==spec['rows']
        if name.startswith('external.'):external[name.split('.')[1]]=rows
        else:sources[name]=rows
    return sources,external
