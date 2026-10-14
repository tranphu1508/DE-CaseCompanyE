import hashlib
import json
import os
import shutil
import subprocess
import sys

import pytest
from pyspark.sql import functions as F, types as T
import lake_job
from model import MODELS

pytestmark=pytest.mark.lake


@pytest.fixture(scope='module')
def isolated_batch(spark,root,pg,report_dir):
    batch='v1_test_export'
    raw=lake_job.LAKE/'raw'/batch
    raw.mkdir(parents=True)
    manifest=json.loads((root/'generated/v1/manifest.json').read_text())
    entries=[]
    for db,tables in MODELS.items():
        with pg(db) as conn:
            # Consistent snapshot within each operational source.
            conn.execute('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY')
            conn.execute("SET TIME ZONE 'Asia/Ho_Chi_Minh'")
            for table in tables:
                path=raw/db/table.name/'data.csv'; path.parent.mkdir(parents=True)
                query=f"COPY (SELECT * FROM {table.name} ORDER BY {table.columns[0][0]}) TO STDOUT WITH (FORMAT CSV,HEADER true,NULL '\\N')"
                with path.open('wb') as dest, conn.cursor().copy(query) as copy:
                    for chunk in copy: dest.write(bytes(chunk))
                entries.append({'dataset_id':db+'.'+table.name,'source_system':db,'table':table.name,
                    'relative_path':path.relative_to(lake_job.LAKE).as_posix(),'format':'CSV',
                    'row_count':manifest['rows'][db][table.name],
                    'sha256':lake_job.checksum(path),'bytes':path.stat().st_size})
            conn.execute('COMMIT')
    (raw/'external').mkdir()
    for original in (root/'generated/v1/external').iterdir():
        path=raw/'external'/original.name; shutil.copyfile(original,path)
        entries.append({'dataset_id':'external.'+path.stem,'source_system':'external_suppliers_or_distributors',
            'table':path.stem,'relative_path':path.relative_to(lake_job.LAKE).as_posix(),
            'format':path.suffix[1:].upper(),'row_count':None,'sha256':lake_job.checksum(path),'bytes':path.stat().st_size})
    lake_job.save(raw/'ingestion_manifest.json',{'batch_id':batch,'status':'RAW_COMMITTED',
        'ingested_at_utc':'2026-10-12T00:00:00Z','source_dataset_version':'v1',
        'seed':manifest['seed'],'datasets':entries,'synthetic':True})
    golden=lake_job.ROOT/'reports/reproducibility/v1/golden_aggregates.json'
    golden.parent.mkdir(parents=True)
    shutil.copyfile(root/'reports/reproducibility/v1/golden_aggregates.json',golden)
    lake_job.build(spark,batch)
    yield batch,entries
    for path in (lake_job.ROOT/'reports').glob('*.json'):
        shutil.copyfile(path,report_dir/path.name)
    shutil.copyfile(lake_job.CATALOG/'catalog.json',report_dir/'isolated_catalog.json')


def test_full_source_to_lake_values_and_metadata(spark,isolated_batch,report_dir):
    batch,entries=isolated_batch
    result=[]
    for src in entries:
        if src['source_system'] not in MODELS: continue
        db=src['source_system']; name=src['table']
        model=next(t for t in MODELS[db] if t.name==name)
        schema=T.StructType([T.StructField(c[0],T.StringType()) for c in model.columns])
        path=lake_job.LAKE/src['relative_path']
        expected=(spark.read.schema(schema).option('header',True).option('nullValue','\\N')
                  .option('multiLine',True).option('escape','"').csv(str(path)))
        expected=expected.select(*[F.col(n).cast(lake_job.datatype(t)).alias(n) for n,t,_,_ in model.columns])
        full=f"companye_{'hotel' if db=='hotel_ops' else 'entertainment'}.{name}"
        actual=spark.table(full)
        values=actual.select(*expected.columns)
        assert not values.exceptAll(expected).limit(1).count(),full
        assert not expected.exceptAll(values).limit(1).count(),full
        assert actual.filter(F.col('_ingestion_batch')!=batch).count()==0
        assert actual.filter(F.col('_source_system')!=db).count()==0
        assert actual.filter(F.col('_source_path')!=str(path)).count()==0
        assert actual.filter(F.col('_ingested_at_utc').isNull()).count()==0
        result.append({'table':full,'all_source_columns_reconciled':True})
    (report_dir/'row_reconciliation.json').write_text(json.dumps(result,indent=2))
    catalog=lake_job.read_json(lake_job.CATALOG/'catalog.json')
    assert len(catalog['datasets'])==44
    assert spark.table('companye_metadata.columns').count()==234
    for dataset in catalog['datasets']:
        for name in ['description','grain','owner','sha256','raw_path']:
            assert dataset[name],(dataset['dataset_id'],name)
        assert 'audit_only' not in dataset['raw_path']
    lake_job.verify(spark,batch)


def test_same_batch_retry_and_raw_immutability(spark,isolated_batch):
    batch,entries=isolated_batch
    before={e['relative_path']:e['sha256'] for e in entries}
    # A successful batch takes the actual production verification path on rerun.
    lake_job.build(spark,batch)
    assert before=={path:lake_job.checksum(lake_job.LAKE/path) for path in before}
    assert spark.table('companye_external.supplier_deliveries').count()==77
    assert spark.table('companye_external.supplier_quarantine').count()==44


def test_raw_corruption_rejected_and_reported(spark,isolated_batch):
    batch,entries=isolated_batch
    path=lake_job.LAKE/entries[0]['relative_path']
    original=path.read_bytes()
    try:
        path.write_bytes(original+b'corruption')
        with pytest.raises(RuntimeError,match='Raw data changed'):
            lake_job.build(spark,batch)
        assert lake_job.read_json(lake_job.ROOT/'reports'/f'lake_build_{batch}.json')['status']=='FAILED'
    finally:
        path.write_bytes(original)
    # A failed verification is restored by a real retry, reusing content-checked outputs.
    lake_job.build(spark,batch)


def test_zz_catalog_survives_new_jvm(spark,isolated_batch,report_dir):
    batch,_=isolated_batch
    spark.stop()
    # Embedded Derby is held by the gateway JVM, even after SparkContext.stop().
    spark.sparkContext._gateway.shutdown()
    gateway_process=spark.sparkContext._gateway.proc
    gateway_process.stdin.close()
    gateway_process.wait(timeout=30)
    env={**os.environ,'COMPANYE_WORKSPACE':str(lake_job.ROOT),
         'PYSPARK_SUBMIT_ARGS':'--master local[2] --driver-memory 1536m pyspark-shell'}
    with (report_dir/'fresh_jvm_verification.log').open('w') as log:
        subprocess.run([sys.executable,'/workspace/src/lake_job.py','verify','--batch',batch],
                       env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=300)
