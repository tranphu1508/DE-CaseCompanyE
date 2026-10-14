import json
import os

import great_expectations as gx
import pytest
from pyspark.sql import functions as F

pytestmark=pytest.mark.gx


def run_checkpoint(context, name, definition, expectations, parameters=None):
    suite=context.suites.add(gx.ExpectationSuite(name=name))
    for expectation in expectations: suite.add_expectation(expectation)
    validation=context.validation_definitions.add(gx.ValidationDefinition(
        name=name,data=definition,suite=suite))
    checkpoint=context.checkpoints.add(gx.Checkpoint(name=name,
        validation_definitions=[validation],actions=[gx.checkpoint.actions.UpdateDataDocsAction(name='local_docs')]))
    return checkpoint.run(batch_parameters=parameters or {})


def test_gx_postgres_spark_and_negative_control(spark,root,report_dir,pg):
    context=gx.get_context(mode='file',project_root_dir=str(report_dir/'gx'))
    source=context.data_sources.add_postgres(name='companye_test_postgres',
        connection_string=os.environ['COMPANYE_TEST_DSN']+'/hotel_ops')
    asset=source.add_table_asset(name='bookings',table_name='bookings',schema_name='public')
    batch=asset.add_batch_definition_whole_table(name='all_bookings')
    expectations=[gx.expectations.ExpectTableRowCountToEqual(value=32000),
        gx.expectations.ExpectColumnValuesToNotBeNull(column='booking_id'),
        gx.expectations.ExpectColumnValuesToBeUnique(column='booking_id'),
        gx.expectations.ExpectColumnValuesToBeBetween(column='customer_due_vnd',min_value=0),
        gx.expectations.ExpectColumnValuesToBeInSet(column='status',value_set=['COMPLETED','CANCELLED','NO_SHOW'])]
    postgres_result=run_checkpoint(context,'postgres_bookings',batch,expectations)
    assert postgres_result.success
    latest=json.loads((root/'lake/catalog/latest_ingestion.json').read_text())['batch_id']
    df=spark.read.parquet(str(root/'lake/standardized'/latest/'hotel_ops/bookings'))
    df=df.withColumn('funding_balanced',F.col('discount_vnd')==(F.col('company_share_vnd')+F.col('partner_share_vnd')))
    spark_source=context.data_sources.add_spark(name='companye_spark',persist=False)
    spark_asset=spark_source.add_dataframe_asset(name='standardized_bookings')
    spark_batch=spark_asset.add_batch_definition_whole_dataframe(name='snapshot')
    spark_expectations=[gx.expectations.ExpectTableRowCountToEqual(value=32000),
        gx.expectations.ExpectColumnValuesToBeUnique(column='booking_id'),
        gx.expectations.ExpectColumnValuesToNotBeNull(column='_ingestion_batch'),
        gx.expectations.ExpectColumnValuesToBeInSet(column='funding_balanced',value_set=[True])]
    spark_result=run_checkpoint(context,'spark_bookings',spark_batch,spark_expectations,{'dataframe':df})
    assert spark_result.success
    # An intentionally wrong accounting allocation must be caught, not silently pass.
    broken=df.limit(2).withColumn('funding_balanced',F.lit(False))
    negative=run_checkpoint(context,'intentional_bad_funding',spark_batch,
        [gx.expectations.ExpectColumnValuesToBeInSet(column='funding_balanced',value_set=[True])],
        {'dataframe':broken})
    assert not negative.success
    context.build_data_docs()
    html=list((report_dir/'gx').rglob('index.html'))
    assert html,'GX Data Docs were not persisted'
    (report_dir/'gx_results.json').write_text(json.dumps({
        'gx_version':gx.__version__,'postgres_bookings_passed':bool(postgres_result.success),
        'spark_bookings_passed':bool(spark_result.success),
        'intentional_bad_funding_detected':not negative.success,
        'data_docs':[str(p.relative_to(report_dir)) for p in html],
        'scope':'Compatibility proof on one PostgreSQL table and one Spark dataset; not all 39 tables.'},indent=2))
