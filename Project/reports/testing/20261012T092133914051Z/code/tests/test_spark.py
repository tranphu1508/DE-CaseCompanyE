import json
from datetime import date
from decimal import Decimal

import pytest
from pyspark.sql import functions as F, types as T, DataFrameWriter
from pyspark.testing.utils import assertDataFrameEqual, assertSchemaEqual
import lake_job
from model import MODELS

pytestmark = pytest.mark.spark
SUPPLIER_SCHEMA = 'Supplier string, Hotel string, Document string, Date string, Qty string, Price string, Item string, Unit string'


def test_supplier_independent_examples(spark, root):
    cases=json.loads((root/'tests/fixtures/supplier_cases.json').read_text())
    raw=spark.createDataFrame(cases['rows'],SUPPLIER_SCHEMA)
    actual=lake_job.supplier_rows(raw)
    reasons={r['Document']:r['quality_reason'] for r in actual.collect()}
    for row, reason in zip(cases['rows'],cases['expected_reasons']):
        assert reasons[row[2]] == reason
    expected=spark.createDataFrame([(date(2024,2,29),Decimal('2.500'),18000,'TOMATO')],
        'service_date date, quantity decimal(12,3), unit_price_vnd long, item_id string')
    good=actual.filter("quality_reason=''").select(*expected.columns)
    assertSchemaEqual(good.schema,expected.schema)
    assertDataFrameEqual(good,expected,rtol=0,atol=0)
    assert actual.count()==raw.count()


def test_duplicate_supplier_document_is_counted_once(spark):
    row=['S1','SP-5','D1','01/03/2024','1','18k','ca chua','kg']
    result=lake_job.supplier_rows(spark.createDataFrame([row,row],SUPPLIER_SCHEMA))
    assert sorted(r['quality_reason'] for r in result.collect())==['','DUPLICATE_DOCUMENT']


def test_supplier_missing_column_fails(spark):
    with pytest.raises(ValueError,match='Missing supplier columns'):
        lake_job.supplier_rows(spark.createDataFrame([('x',)],'Supplier string'))


@pytest.mark.parametrize('header',['site_id,site_name','site_name,site_id,climate_region'])
def test_source_missing_or_reordered_columns_rejected(spark,tmp_path,header):
    path=tmp_path/'sites.csv'; path.write_text(header+'\nSP,Sa Pa,NORTH\n')
    with pytest.raises(ValueError,match='header differs from contract'):
        lake_job.source_rows(spark,path,MODELS['hotel_ops'][0])


def test_lineage_and_timezone(spark):
    raw=spark.createDataFrame([(1,)],'id int')
    df=lake_job.add_lineage(raw,'hotel_ops','/raw/test.csv','fixture','2024-01-01T00:00:00Z')
    assert df.select('_source_system','_source_path','_ingestion_batch').first()==('hotel_ops','/raw/test.csv','fixture')
    assert df.select(F.unix_timestamp('_ingested_at_utc')).first()[0]==1704067200
    assert df.filter(F.col('_ingested_at_utc').isNull()).count()==0


def test_register_retry_idempotence_and_corruption(spark,tmp_path):
    df=spark.createDataFrame([('B1',2000000),('B2',1000000)],'id string, money long')
    path=tmp_path/'published'
    first=lake_job.register(spark,df,'recovery_checks','payments',path,'test',{})
    again=lake_job.register(spark,df,'recovery_checks','payments',path,'test',{})
    assertDataFrameEqual(first,again,rtol=0,atol=0)
    assert again.count()==2
    corrupt=spark.createDataFrame([('B1',2000001),('B2',1000000)],df.schema)
    with pytest.raises(RuntimeError,match='content differs'):
        lake_job.register(spark,corrupt,'recovery_checks','payments',path,'test',{})


def test_failed_parquet_write_not_published_and_can_retry(spark,tmp_path,monkeypatch):
    df=spark.createDataFrame([('B1',1800000)],'id string, amount long')
    path=tmp_path/'payments'
    original=DataFrameWriter.parquet
    def interrupted(writer, destination, *args, **kwargs):
        from pathlib import Path
        Path(destination).mkdir(parents=True)
        (Path(destination)/'incomplete.part').write_text('injected interruption')
        raise OSError('injected disk interruption')
    monkeypatch.setattr(DataFrameWriter,'parquet',interrupted)
    with pytest.raises(OSError,match='injected'):
        lake_job.register(spark,df,'recovery_checks','interrupted',path,'test',{})
    assert not path.exists()
    assert not spark.catalog.tableExists('recovery_checks.interrupted')
    monkeypatch.setattr(DataFrameWriter,'parquet',original)
    actual=lake_job.register(spark,df,'recovery_checks','interrupted',path,'test',{})
    assertDataFrameEqual(actual,df,rtol=0,atol=0)


def test_incomplete_existing_output_is_rejected(spark,tmp_path):
    path=tmp_path/'incomplete'; path.mkdir()
    df=spark.createDataFrame([(1,)],'id int')
    with pytest.raises(RuntimeError,match='Incomplete existing Parquet'):
        lake_job.register(spark,df,'recovery_checks','incomplete',path,'test',{})


def test_failed_batch_has_failure_report(spark,monkeypatch):
    def interrupted(*args): raise OSError('injected build failure')
    monkeypatch.setattr(lake_job,'_build',interrupted)
    with pytest.raises(OSError): lake_job.build(spark,'TEST_FAILURE')
    result=lake_job.read_json(lake_job.ROOT/'reports/lake_build_TEST_FAILURE.json')
    assert result['status']=='FAILED' and 'injected' in result['error']
