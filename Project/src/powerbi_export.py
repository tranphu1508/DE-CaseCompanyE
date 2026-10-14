"""Read-only, pinned-publication import bundle for Power BI; no credentials in BI."""
from pathlib import Path
import csv,hashlib,json,os
from datetime import date,datetime,timezone
from decimal import Decimal
from analytics_runtime.session import create_session,secret
from publication.core import Reader,read,save,digest

ROOT=Path('/workspace');OUT=ROOT/'reports/powerbi';OUT.mkdir(exist_ok=True)
SKIP={'D07','D08','F15','L02','L04'}
AUDIT={'source_batch_id','transform_version','row_hash','created_at_utc','updated_at_utc','valid_from_utc','valid_to_utc','is_current','version_no','effective_time_basis','source_updated_at_utc','entered_at_utc'}
def value(v,c):
    if v is None:return ''
    typ=c['spark_sql_type']
    if typ in ('BIGINT','INT'):return str(int(v))
    if typ.startswith('DECIMAL'):return format(Decimal(str(v)),'f')
    if typ=='DATE':return (v.date() if isinstance(v,datetime) else v).isoformat()
    return str(v)
def run(spark):
    entities=read(ROOT/'config/analytics/ddl/manifest.json')['entities'];checks=[]
    with Reader(spark,'powerbi-import-export',ttl=1800) as reader:
        pid=reader.pid;folder=OUT/'imports'/pid;folder.mkdir(parents=True,exist_ok=True)
        for entity in entities:
            eid=entity['id']
            if eid in SKIP:continue
            cols=[c for c in entity['columns'] if c['name'] not in AUDIT];names=[c['name'] for c in cols]
            if eid.startswith('D'):
                # Shared dimensions are safe only after full row equality across both branches.
                engines=['oracle','iceberg']
            else:engines=['oracle','iceberg']
            content={};sha={}
            for engine in engines:
                reader.renew();reader.check();print('EXPORT '+eid+' '+engine,flush=True)
                if engine=='oracle':
                    obj=reader.manifest['tables'][eid]['oracle_object']
                    df=(spark.read.format('jdbc').option('url','jdbc:oracle:thin:@//oracle:1521/FREEPDB1')
                        .option('user','CE_READER').option('password',secret('CE_ORACLE_READER_PASSWORD_FILE'))
                        .option('driver','oracle.jdbc.OracleDriver').option('dbtable','(SELECT '+','.join(names)+' FROM '+obj+')').load())
                    rows=[{k.lower():v for k,v in r.asDict().items()} for r in df.collect()]
                else:
                    rows=[r.asDict() for r in reader.spark.table(reader.views[eid]).select(*names).collect()]
                reader.check()
                normalized=[tuple(value(r[c['name']],c) for c in cols) for r in rows]
                normalized.sort();content[engine]=normalized
                sha[engine]=hashlib.sha256(json.dumps(normalized,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
                assert len(rows)==reader.manifest['tables'][eid]['rows']
            assert content['oracle']==content['iceberg'],eid
            target=folder/(eid+'.csv');temp=folder/(eid+'.pending.csv')
            with temp.open('w',encoding='utf8',newline='') as f:
                writer=csv.writer(f);writer.writerow(names+([] if eid.startswith('D') else ['engine']))
                if eid.startswith('D'):writer.writerows(content['oracle'])
                else:
                    for engine in engines:writer.writerows([list(r)+[engine] for r in content[engine]])
            file_sha=hashlib.sha256(temp.read_bytes()).hexdigest()
            if target.exists():
                assert hashlib.sha256(target.read_bytes()).hexdigest()==file_sha,'Immutable export changed '+eid
                temp.unlink()
            else:os.replace(temp,target)
            checks.append(dict(entity=eid,columns=cols,rows_per_engine=len(content['oracle']),import_rows=len(content['oracle'])*(1 if eid.startswith('D') else 2),filename=target.name,sha256=file_sha,branch_payload_sha256=sha))
        manifest=dict(status='PINNED_EXPORT_READY',publication_id=pid,publication_manifest_sha256=digest(reader.manifest),source_batch_id=reader.manifest['source_batch_id'],source_catalog_sha256=reader.manifest['source_catalog_sha256'],tables=checks,quality_metrics=reader.manifest['quality_metrics'],quality_scope=reader.manifest['quality_scope'],external_warning_count=len(reader.manifest['external_warnings']),exported_at=datetime.now(timezone.utc).isoformat(),privacy='No customer profile dimension exported; only surrogate customer keys retained in facts.')
        existing=folder/'manifest.json'
        if existing.exists():
            old=read(existing);assert old['tables']==manifest['tables'];manifest=old
        else:save(existing,manifest)
        save(OUT/'export.json',manifest)
    print('PINNED_EXPORT_READY '+pid,flush=True)
if __name__=='__main__':
    spark=create_session('CompanyE-powerbi-export')
    try:run(spark)
    finally:spark.stop()
