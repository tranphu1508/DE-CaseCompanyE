"""Create 35 empty Iceberg tables, read metadata back, and test helper registration."""
from pathlib import Path
import hashlib,json
from datetime import datetime,timezone
from analytics_runtime.session import create_session
from analytics_runtime.validation_views import register_validation_views

manifest_path=Path('/workspace/config/analytics/ddl/manifest.json')
contract=json.loads(manifest_path.read_text())
spark=create_session('CompanyE business schema deployment')
spark.sparkContext.setLogLevel('WARN')
spark.sql('CREATE NAMESPACE IF NOT EXISTS ce.gold')
for entry in contract['iceberg_statements']:
    spark.sql(entry['sql'])
expected={e['physical_name']:e for e in contract['entities'] if e['kind']!='VALIDATION_VIEW'}
actual={r.tableName for r in spark.sql('SHOW TABLES IN ce.gold').collect()}
assert actual==set(expected), 'Unexpected or missing gold tables'
inventory=[]
for name,entity in expected.items():
    table=spark._jvm.org.apache.iceberg.spark.Spark3Util.loadIcebergTable(spark._jsparkSession,'ce.gold.'+name)
    fields=table.schema().columns()
    columns=[dict(name=fields.get(i).name(),type=str(fields.get(i).type()).replace(' ',''),required=fields.get(i).isRequired()) for i in range(fields.size())]
    wanted=[dict(name=c['name'],type=c['iceberg_type'],required=not c['nullable']) for c in entity['columns']]
    assert columns==wanted, 'Iceberg schema drift: '+name+' '+str([(a,b) for a,b in zip(columns,wanted) if a!=b])
    assert table.spec().isUnpartitioned() and table.sortOrder().isUnsorted(), 'Unexpected tuning: '+name
    props=table.properties()
    for k,v in entity['iceberg']['table_properties'].items():
        if k=='format-version':assert table.operations().current().formatVersion()==int(v)
        else:assert props.get(k)==v, 'Property drift: '+name+'/'+k
    count=spark.table('ce.gold.'+name).count()
    inventory.append(dict(name=name,columns=columns,row_count=count,partitioned=False,format_version=2))

# Explicit empty fixtures prove registration and types only; they do not pretend
# that a business publication or its helper data exists.
fixture_root=Path('/analytics/schema-validation')/hashlib.sha256(manifest_path.read_bytes()).hexdigest()[:16]
publication=dict(publication_id='SCHEMA_VALIDATION_ONLY_NOT_PUBLISHED',helpers={})
for e in contract['entities']:
    if e['kind']!='VALIDATION_VIEW':continue
    name=e['physical_name']; path=fixture_root/name
    schema_sql=', '.join('`'+c['name']+'` '+c['spark_sql_type'] for c in e['columns'])
    df=spark.createDataFrame([],schema_sql)
    if not path.exists():df.write.mode('errorifexists').parquet(str(path))
    publication['helpers'][name]=dict(path=str(path),schema=df.schema.jsonValue(),
        sha256={str(p.relative_to(path)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(path.rglob('*')) if p.is_file()})
register_validation_views(spark,publication,contract)
for e in contract['entities']:
    if e['kind']=='VALIDATION_VIEW':
        assert spark.table(e['physical_name']).columns==[c['name'] for c in e['columns']]
        assert spark.table(e['physical_name']).count()==0
bad=json.loads(json.dumps(publication))
next(iter(bad['helpers'].values()))['sha256']['missing-file.parquet']='0'*64
try:register_validation_views(spark,bad,contract)
except ValueError:rejected_missing=True
else:raise AssertionError('Missing helper did not fail closed')
out=Path('/workspace/reports/schema-deployment');out.mkdir(parents=True,exist_ok=True)
(out/'helper-fixture-manifest.json').write_text(json.dumps(publication,indent=2)+'\n')
report=dict(status='PASSED',checked_at=datetime.now(timezone.utc).isoformat(),tables=inventory,
            manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            logical_columns=sum(len(e['columns']) for e in contract['entities']),
            session_views_verified=2,missing_helper_rejected=rejected_missing,
            all_tables_empty=all(t['row_count']==0 for t in inventory),
            limits=['No native Iceberg PK/UK/FK/CHECK enforcement claimed.','Helper views must be registered in every Spark session using actual pinned publication files.','No business publication or ETL has been created.'])
(out/'iceberg-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='tables'}))
spark.stop()
