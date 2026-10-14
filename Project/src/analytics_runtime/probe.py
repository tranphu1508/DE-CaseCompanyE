"""Integration probe of Oracle JDBC, Iceberg/JDBC catalog and persistent volumes.

Writes only CE_PROBE.RUNTIME_PROBE and ce.runtime_probe.types_probe. The after-
restart phase performs reads only. These are not business DDL or ETL tests.
"""
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import argparse
import json
import re
from analytics_runtime.session import create_session, secret
from pyspark.sql.types import (StructType, StructField, StringType, LongType,
                              DecimalType, TimestampNTZType)

parser=argparse.ArgumentParser()
parser.add_argument('phase', choices=['write','verify'])
parser.add_argument('run_id')
args=parser.parse_args()
if not re.fullmatch('[a-z0-9_]{1,64}', args.run_id):
    raise ValueError('Invalid probe run ID')
spark=create_session('CompanyE analytics service integration probe')
spark.sparkContext.setLogLevel('WARN')
run=args.run_id
fixture=[
    (run,1,'Đà Nẵng – khách sạn E',Decimal('9999999999999999999'),Decimal('1234.567'),datetime(2026,1,1,17,0,0,123456),None),
    (run,2,'Phú Quốc / buffet sáng',Decimal('-120000'),Decimal('-999999999999999.999'),datetime(2026,1,1,16,59,59,999999),Decimal('0')),
    (run,3,None,Decimal('0'),Decimal('0.001'),datetime(2026,6,30,23,59,59),Decimal('-1')),
]
schema=StructType([
    StructField('run_id',StringType(),False), StructField('id',LongType(),False),
    StructField('label',StringType(),True), StructField('amount',DecimalType(19,0),True),
    StructField('qty',DecimalType(18,3),True), StructField('event_utc',TimestampNTZType(),True),
    StructField('optional_amount',DecimalType(19,0),True),
])
url='jdbc:oracle:thin:@//oracle:1521/FREEPDB1'
options=dict(url=url,user='CE_PROBE',password=secret('CE_ORACLE_PROBE_PASSWORD_FILE'),driver='oracle.jdbc.OracleDriver')
table='ce.runtime_probe.types_probe'
if args.phase=='write':
    spark.sql('CREATE NAMESPACE IF NOT EXISTS ce.runtime_probe')
    spark.sql(f"""CREATE TABLE IF NOT EXISTS {table} (
        run_id STRING NOT NULL, id BIGINT NOT NULL, label STRING,
        amount DECIMAL(19,0), qty DECIMAL(18,3), event_utc TIMESTAMP_NTZ,
        optional_amount DECIMAL(19,0)) USING iceberg
        TBLPROPERTIES ('format-version'='2','write.parquet.compression-codec'='snappy')""")
    if spark.sql(f"SELECT COUNT(*) n FROM {table} WHERE run_id='{run}'").first().n:
        raise RuntimeError('Probe run already exists; use a fresh run_id, do not overwrite evidence')
    df=spark.createDataFrame(fixture,schema)
    df.writeTo(table).append()
    (df.write.format('jdbc').options(**options).option('dbtable','CE_PROBE.RUNTIME_PROBE')
     .option('batchsize','100').option('numPartitions','1').mode('append').save())

oracle_query=f"(SELECT run_id,id,label,amount,qty,event_utc,optional_amount FROM CE_PROBE.RUNTIME_PROBE WHERE run_id='{run}')"
oracle=(spark.read.format('jdbc').options(**options).option('dbtable',oracle_query)
        .option('sessionInitStatement',"ALTER SESSION SET TIME_ZONE='+00:00'").load())
iceberg=spark.sql(f"SELECT * FROM {table} WHERE run_id='{run}' ORDER BY id")
keys=[f.name for f in schema]
expected=sorted(fixture,key=lambda row:row[1])
def values(df):
    records=[{k.lower():v for k,v in row.asDict().items()} for row in df.collect()]
    return [tuple(r[k] for k in keys) for r in sorted(records,key=lambda r:r['id'])]
assert values(oracle)==expected, 'Oracle precision/Unicode/NULL/timestamp check failed'
assert values(iceberg)==expected, 'Iceberg precision/Unicode/NULL/timestamp check failed'
snapshots=[r.asDict() for r in spark.sql(f'SELECT snapshot_id, operation FROM {table}.snapshots').collect()]
assert snapshots, 'Iceberg snapshot metadata missing'
version=spark.read.format('jdbc').options(**options).option('dbtable',"(SELECT banner_full FROM v$version)").load().first()[0]
report=dict(status='PASSED',phase=args.phase,run_id=run,checked_at=datetime.now(timezone.utc).isoformat(),
            spark_version=spark.version,oracle_version=version,
            iceberg_version=spark._jvm.org.apache.iceberg.IcebergBuild.fullVersion(),
            oracle_rows=len(expected),iceberg_rows=len(expected),snapshots=snapshots,
            checks=['Oracle TCP/JDBC connection','Iceberg PostgreSQL JDBC catalog','Parquet write/read',
                    'Unicode Vietnamese','DECIMAL(19,0) max positive value','DECIMAL(18,3) negative boundary',
                    'NULL versus numeric zero','Timestamp microseconds across Vietnam midnight in UTC',
                    'Both engines exactly match independent literal fixture'],
            oracle_schema=str(oracle.schema),iceberg_schema=str(iceberg.schema),
            limitation='Service integration only; no business DDL, SCD2 pipeline, KPI or performance validation.')
if args.phase=='verify':
    before=json.loads(Path(f'/workspace/reports/analytics-runtime/{run}-write.json').read_text())
    assert before['snapshots']==snapshots, 'Read-only restart verification changed Iceberg snapshots'
    report['checks'].append('Data and Iceberg snapshot IDs preserved across container restart')
path=Path(f'/workspace/reports/analytics-runtime/{run}-{args.phase}.json')
path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('COMPANYE_PROBE_RESULT '+json.dumps(report,ensure_ascii=False))
spark.stop()
