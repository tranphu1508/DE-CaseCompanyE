"""Provision and operate independent B. Run from repository root; Python stdlib only."""
import argparse, hashlib, json, os, secrets, subprocess, sys, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'.work/lakehouse-b'
def run(args,**kw):
    return subprocess.run(args,cwd=WORK,check=True,**kw)
def compose(*args,**kw):
    return run(['docker','compose','-p','ce-lakehouse-b','-f',str(WORK/'compose.yaml'),*args],**kw)
def prepare(source):
    WORK.mkdir(parents=True,exist_ok=True)
    for d in ['reports','jars','secrets']: (WORK/d).mkdir(exist_ok=True)
    pw=WORK/'secrets/catalog_password'
    if not pw.exists(): pw.write_text('Ce9a'+secrets.token_hex(20),encoding='utf8')
    lock=json.loads((ROOT/'Project/config/analytics_runtime_lock_v1.json').read_text(encoding='utf8'))
    def q(p): return json.dumps(str(p.resolve()).replace('\\','/'),ensure_ascii=False)
    conf='''spark.master local[2]
spark.driver.memory 2g
spark.sql.session.timeZone UTC
spark.sql.timestampType TIMESTAMP_NTZ
spark.sql.ansi.enabled true
spark.sql.decimalOperations.allowPrecisionLoss false
spark.sql.shuffle.partitions 8
spark.default.parallelism 2
spark.sql.adaptive.enabled true
spark.sql.files.ignoreMissingFiles false
spark.sql.files.ignoreCorruptFiles false
spark.sql.parquet.outputTimestampType TIMESTAMP_MICROS
spark.sql.extensions org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions
spark.sql.catalog.ce org.apache.iceberg.spark.SparkCatalog
spark.sql.catalog.ce.type jdbc
spark.sql.catalog.ce.uri jdbc:postgresql://metadata:5432/ce_metadata
spark.sql.catalog.ce.warehouse file:///companye-lakehouse/tables
spark.sql.catalog.ce.cache-enabled false
spark.local.dir /tmp/spark-local
'''
    (WORK/'spark-defaults.conf').write_text(conf,encoding='utf8')
    common=f'''    image: {lock['spark']['image']}
    user: "0:0"
    working_dir: /workspace
    entrypoint: []
'''
    yaml=f'''services:
  metadata:
    image: {lock['metadata_postgres']['image']}
    environment:
      POSTGRES_USER: ce_catalog
      POSTGRES_DB: ce_metadata
      POSTGRES_PASSWORD_FILE: /run/secrets/catalog_password
    secrets: [catalog_password]
    volumes: [metadata:/var/lib/postgresql/data]
    mem_limit: 512m
    healthcheck:
      test: [CMD-SHELL, "pg_isready -U ce_catalog -d ce_metadata"]
      interval: 3s
      retries: 30
  spark:
{common}    command: [sleep, infinity]
    mem_limit: 4g
    cpus: 2
    environment:
      PYTHONPATH: /workspace/src
      SPARK_CONF_DIR: /conf
      SPARK_LOCAL_IP: 127.0.0.1
      CE_CATALOG_PASSWORD_FILE: /run/secrets/catalog_password
    secrets: [catalog_password]
    volumes:
      - type: bind
        source: {q(ROOT/'Project/src')}
        target: /workspace/src
        read_only: true
      - type: bind
        source: {q(ROOT/'Project/config')}
        target: /workspace/config
        read_only: true
      - type: bind
        source: {q(ROOT/'Project/reports')}
        target: /baseline
        read_only: true
      - type: bind
        source: {q(WORK/'reports')}
        target: /workspace/reports
      - type: bind
        source: {q(WORK/'jars')}
        target: /jars
        read_only: true
      - type: bind
        source: {q(WORK/'spark-defaults.conf')}
        target: /conf/spark-defaults.conf
        read_only: true
      - lakehouse:/companye-lakehouse
    depends_on:
      metadata: {{condition: service_healthy}}
  ingest:
{common}    profiles: [ingest]
    volumes:
      - type: bind
        source: {q(ROOT/'Project/src')}
        target: /workspace/src
        read_only: true
      - type: bind
        source: {q(source)}
        target: /seed-input
        read_only: true
      - lakehouse:/companye-lakehouse
volumes:
  lakehouse:
  metadata:
secrets:
  catalog_password:
    file: ./secrets/catalog_password
'''
    (WORK/'compose.yaml').write_text(yaml,encoding='utf8')
    jars=[]
    for p in lock['packages']:
        if p['coordinate'].startswith('com.oracle.'): continue
        target=WORK/'jars'/p['jar_url'].rsplit('/',1)[1]
        if not target.exists():
            with urllib.request.urlopen(p['jar_url'],timeout=120) as resp:target.write_bytes(resp.read())
        if hashlib.sha256(target.read_bytes()).hexdigest()!=p['jar_sha256']:raise ValueError('Pinned JAR mismatch: '+target.name)
        jars.append('/jars/'+target.name)
    (WORK/'jars.json').write_text(json.dumps(jars),encoding='utf8')
    compose('config','--quiet')
    print('Independent B prepared; no Oracle service, credential, JDBC driver or original lake mount in Spark.')
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('phase',choices=['prepare','up','ingest','silver','explore','gold','publish','verify','fixtures','status','stop','all'])
    ap.add_argument('--source-lake',type=Path,default=ROOT/'.work/platform/Project/lake/v2')
    ap.add_argument('--fail-after',type=int,default=0,help='Inject failure after N committed tables for recovery testing')
    a=ap.parse_args()
    if a.phase in ['prepare','all']:prepare(a.source_lake)
    if a.phase=='prepare':return
    if a.phase in ['up','all']:compose('up','-d','--wait','metadata','spark')
    if a.phase in ['ingest','all']:compose('--profile','ingest','run','--rm','--no-deps','ingest','python3','/workspace/src/lakehouse_b/ingest.py')
    phases=['silver','explore','gold','publish','verify','fixtures'] if a.phase=='all' else [a.phase]
    for phase in phases:
        if phase in ['silver','explore','gold','publish','verify','fixtures']:
            jars=json.loads((WORK/'jars.json').read_text())
            cmd=['docker','compose','-p','ce-lakehouse-b','-f',str(WORK/'compose.yaml'),'exec','-T','spark','/opt/spark/bin/spark-submit','--jars',','.join(jars),'/workspace/src/lakehouse_b/job.py',phase,'--fail-after',str(a.fail_after)]
            path=WORK/'reports'/(phase+'.log')
            with path.open('w',encoding='utf8') as f:
                proc=subprocess.Popen(cmd,cwd=WORK,stdout=f,stderr=subprocess.STDOUT)
                print('Running '+phase+'; log: '+str(path),flush=True)
                code=proc.wait()
            print(path.read_text(encoding='utf8')[-5500:])
            if code:raise SystemExit(code)
    if a.phase=='status':compose('ps')
    if a.phase=='stop':compose('stop')
if __name__=='__main__':main()
