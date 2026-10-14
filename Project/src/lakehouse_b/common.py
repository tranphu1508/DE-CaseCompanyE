import hashlib,json,os,re
from pathlib import Path
from datetime import datetime,timezone
from analytics_runtime.scd2 import canonical,scalar
from analytics_runtime.etl_io import Jdbc
from analytics_runtime.session import create_session,secret

LAKE=Path('/companye-lakehouse');OUT=Path('/workspace/reports');CONFIG=Path('/workspace/config')
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(v):
    # PostgreSQL JSONB reorders object keys. Hash meaning, not insertion order.
    stable=json.dumps(json.loads(canonical(v)),ensure_ascii=False,sort_keys=True,separators=(',',':'))
    return hashlib.sha256(stable.encode()).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()
def save(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(v,ensure_ascii=False,indent=2,default=scalar)+'\n',encoding='utf8');os.replace(str(tmp),str(p))
def immutable(p,v):
    p=Path(p)
    if p.exists():assert read(p)==json.loads(canonical(v)),'Immutable manifest drift: '+str(p)
    else:save(p,v)
def code_version():
    roots=[Path('/workspace/src')/s for s in ['lakehouse_b','analytics_runtime','fact_etl','semantic']]
    inputs={str(p.relative_to('/workspace')):sha(p) for root in roots for p in sorted(root.glob('*.py'))}
    for name in ['lake_v2.py','lake_job.py']:
        inputs['src/'+name]=sha(Path('/workspace/src')/name)
    for rel in ['source_target_mapping_v1.json','warehouse_design_v1.json','kpi_contract_v1.json','analytics/ddl/manifest.json','analytics_runtime_lock_v1.json']:
        inputs['config/'+rel]=sha(CONFIG/rel)
    return digest(inputs)
def row_hash(rows,columns):return digest(sorted(canonical([r[c] for c in columns]) for r in rows))
def snapshot(spark,table):
    native=spark._jvm.org.apache.iceberg.spark.Spark3Util.loadIcebergTable(spark._jsparkSession,table)
    snap=native.currentSnapshot()
    return None if snap is None else int(snap.snapshotId())
def pinned(spark,spec):
    assert re.fullmatch(r'ce\.[a-z0-9_]+\.[a-z0-9_]+',spec['table'])
    if spec['snapshot_id'] is None:
        assert spec['rows']==0
        return spark.createDataFrame([],spec['schema'])
    return spark.read.option('snapshot-id',str(spec['snapshot_id'])).table(spec['table'])
def put_table(spark,table,df,columns):
    rows=[r.asDict(recursive=True) for r in df.select(*columns).collect()]
    expected=row_hash(rows,columns)
    spark.sql('CREATE NAMESPACE IF NOT EXISTS '+table.rsplit('.',1)[0])
    if spark.catalog.tableExists(table):
        old=spark.table(table)
        assert old.schema.simpleString()==df.schema.simpleString(),'Schema drift: '+table
        actual=row_hash([r.asDict(recursive=True) for r in old.select(*columns).collect()],columns)
        assert actual==expected,'Existing candidate differs; preserve it: '+table
    else:
        df.coalesce(2).writeTo(table).using('iceberg').tableProperty('format-version','2').tableProperty('write.parquet.compression-codec','snappy').create()
    spec={'table':table,'snapshot_id':snapshot(spark,table),'rows':len(rows),'columns':columns,'schema':df.schema.simpleString(),'content_sha256':expected}
    actual=pinned(spark,spec).select(*columns).collect()
    assert row_hash([r.asDict(recursive=True) for r in actual],columns)==expected,'Write/read content mismatch'
    return spec

class Database(Jdbc):
    def __init__(self,spark,namespace='ce_b'):
        assert namespace in ['ce_b','ce_b_fixture']
        self.namespace=namespace
        self.spark=spark;self.j=spark._jvm;self.engine='postgres'
        props=self.j.java.util.Properties();props.setProperty('user','ce_catalog');props.setProperty('password',secret('CE_CATALOG_PASSWORD_FILE'))
        self.conn=self.j.org.postgresql.Driver().connect('jdbc:postgresql://metadata:5432/ce_metadata',props)
        self.execute('''CREATE SCHEMA IF NOT EXISTS ce_b;
        CREATE TABLE IF NOT EXISTS ce_b.key_registry(canonical_key text PRIMARY KEY,surrogate_key bigint UNIQUE NOT NULL);
        CREATE TABLE IF NOT EXISTS ce_b.publication(id text PRIMARY KEY,manifest jsonb NOT NULL,sha256 text NOT NULL,state text NOT NULL CHECK(state IN ('PREPARED','PUBLISHED')));
        CREATE TABLE IF NOT EXISTS ce_b.active(name text PRIMARY KEY,id text REFERENCES ce_b.publication(id));
        CREATE TABLE IF NOT EXISTS ce_b.lease(token text PRIMARY KEY,publication_id text NOT NULL REFERENCES ce_b.publication(id),expires_at timestamptz NOT NULL);
        INSERT INTO ce_b.active(name,id) VALUES ('gold',NULL) ON CONFLICT DO NOTHING;''')
    def statement(self,sql,params):
        sql=sql.replace('ce_b.',self.namespace+'.').replace('SCHEMA IF NOT EXISTS ce_b;', 'SCHEMA IF NOT EXISTS '+self.namespace+';')
        return super().statement(sql,params)
    def lock(self):
        assert self.query('SELECT pg_try_advisory_lock(51732026)')[0][0]=='t','Another B writer is active'
    def registry(self,keys):
        # 56 bits fit the shared NUMBER(18,0)/BIGINT contract. The v2 prefix
        # preserves abandoned allocations from early pre-publication trials.
        values={canonical(k):1+int(hashlib.sha256(canonical(k).encode()).hexdigest()[:14],16) for k in keys}
        assert all(0<v<=999999999999999999 for v in values.values())
        entries=[('v2:'+k,v) for k,v in values.items()]
        for start in range(0,len(entries),1000):
            rows=entries[start:start+1000]
            self.execute('INSERT INTO ce_b.key_registry SELECT x->>0,(x->>1)::bigint FROM jsonb_array_elements(?::jsonb) x ON CONFLICT(canonical_key) DO NOTHING',[canonical(rows)])
            # Validate only this allocation batch inside PostgreSQL. Do not pull
            # the entire growing registry through row-by-row Py4J calls.
            bad=self.query('''SELECT count(*) FROM jsonb_array_elements(?::jsonb) x
                LEFT JOIN ce_b.key_registry r ON r.canonical_key=x->>0
                WHERE r.surrogate_key IS NULL OR r.surrogate_key<>(x->>1)::bigint''',[canonical(rows)])
            assert bad[0][0]=='0','Durable key mapping changed'
        # A unique constraint rejects a hash collision; no silent remapping.
        return values
    def active(self):return self.query("SELECT id FROM ce_b.active WHERE name='gold'")[0][0]

class Reader:
    def __init__(self,spark,db,pid=None):
        import uuid
        self.spark=spark;self.db=db;self.token=uuid.uuid4().hex
        db.conn.setAutoCommit(False)
        try:
            # Lock pointer until its reader lease exists; future GC must honor leases.
            current=db.query("SELECT id FROM ce_b.active WHERE name='gold' FOR SHARE")[0][0]
            self.pid=pid or current
            assert self.pid,'No publication'
            rows=db.query("SELECT manifest::text,sha256 FROM ce_b.publication WHERE id=? AND state='PUBLISHED'",[self.pid]);assert rows
            self.manifest=json.loads(rows[0][0]);assert digest(self.manifest)==rows[0][1]
            db.execute("INSERT INTO ce_b.lease VALUES(?,?,clock_timestamp()+interval '15 minutes')",[self.token,self.pid]);db.conn.commit()
        except Exception:db.conn.rollback();raise
        finally:db.conn.setAutoCommit(True)
        self.names={}
        for eid,spec in self.manifest['tables'].items():
            name='b_'+self.token+'_'+eid.lower();pinned(spark,spec).createOrReplaceTempView(name);self.names[eid]=name
    def query(self,sql,engine='iceberg'):
        if engine!='iceberg':raise ValueError('B does not connect to Oracle')
        n=self.db.execute("UPDATE ce_b.lease SET expires_at=clock_timestamp()+interval '15 minutes' WHERE token=? AND expires_at>clock_timestamp()",[self.token]);assert n==1,'Reader lease expired'
        text=re.sub(r'\{([DFL][0-9]{2})\}',lambda m:self.names[m.group(1)],sql)
        return {'rows':[list(r) for r in self.spark.sql(text).collect()]}
    def close(self):
        self.db.execute('DELETE FROM ce_b.lease WHERE token=?',[self.token])
        for name in self.names.values():self.spark.catalog.dropTempView(name)
