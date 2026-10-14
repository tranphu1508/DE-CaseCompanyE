import hashlib,json,re,uuid
from pathlib import Path
from analytics_runtime.etl_io import Jdbc
from analytics_runtime.session import secret
from analytics_runtime.scd2 import scalar

def canonical(obj):return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'),default=scalar,allow_nan=False)
def digest(obj):return hashlib.sha256(canonical(obj).encode()).hexdigest()
def file_hash(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf8'))
def save(path,obj):Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=scalar)+'\n',encoding='utf8')
def content_hash(rows,entity):
    # Match the already frozen ETL serialization (column/PK order is contractual).
    values=['['+','.join(json.dumps(r[c['name']],ensure_ascii=False,separators=(',',':'),default=scalar,allow_nan=False) for c in entity['columns'])+']' for r in sorted(rows,key=lambda r:tuple(r[k] for k in entity['primary_key']))]
    return hashlib.sha256('\n'.join(values).encode()).hexdigest()

class Connection(Jdbc):
    def __init__(self,spark,role,engine='postgres'):
        self.spark=spark;self.j=spark._jvm;self.engine=engine
        user=('ce_'+role) if engine=='postgres' else ('CE_'+role.upper())
        env={('postgres','publisher'):'CE_PUBLICATION_PASSWORD_FILE',('postgres','reader'):'CE_READER_PASSWORD_FILE',('oracle','publisher'):'CE_ORACLE_PUBLICATION_PASSWORD_FILE',('oracle','reader'):'CE_ORACLE_READER_PASSWORD_FILE'}[(engine,role)]
        url='jdbc:postgresql://metadata:5432/ce_metadata' if engine=='postgres' else 'jdbc:oracle:thin:@//oracle:1521/FREEPDB1'
        props=self.j.java.util.Properties();props.setProperty('user',user);props.setProperty('password',secret(env))
        driver=self.j.org.postgresql.Driver() if engine=='postgres' else self.j.oracle.jdbc.OracleDriver()
        self.conn=driver.connect(url,props)
    def statement(self,sql,params):
        stmt=super().statement(sql,params)
        for i,value in enumerate(params,1):
            if isinstance(value,int):
                if -2**31<=value<2**31:stmt.setInt(i,value)
                else:stmt.setLong(i,value)
        return stmt

class Coordinator:
    def __init__(self,spark,schema='ce_control'):
        assert schema in ('ce_control','ce_pub_test')
        self.spark=spark;self.schema=schema;self.db=Connection(spark,'publisher')
    def active(self):
        rows=self.db.query('SELECT publication_id FROM '+self.schema+'.active_publication WHERE singleton')
        return rows[0][0] if rows else None
    def begin(self,pid,rid,slot,previous):return int(self.db.query('SELECT '+self.schema+'.begin_publication(?,?,?,?)',[pid,rid,slot,previous])[0][0])
    def prepare(self,manifest):
        result=self.db.query('SELECT '+self.schema+'.prepare_publication(?,?)',[canonical(manifest),manifest['generation']])[0][0]
        assert result==digest(manifest),'Manifest SHA256 mismatch';return result
    def publish(self,manifest,previous):
        return json.loads(self.db.query('SELECT '+self.schema+'.publish(?,?,?)',[manifest['publication_id'],previous,manifest['generation']])[0][0])
    def candidate(self,pid):
        rows=self.db.query('SELECT state,manifest_text,manifest_sha256,expected_active,generation FROM '+self.schema+'.publication_candidate WHERE publication_id=?',[pid])
        return rows[0] if rows else None
    def close(self):self.db.close()

def pin_tag(spark,table,tag,snapshot):
    assert re.fullmatch(r'ce\.[a-z_]+\.[a-z_]+',table) and re.fullmatch(r'pub_[a-z0-9_]+',tag)
    native=spark._jvm.org.apache.iceberg.spark.Spark3Util.loadIcebergTable(spark._jsparkSession,table)
    assert native.snapshot(snapshot) is not None,'Snapshot missing before tag'
    ref=native.refs().get(tag)
    if ref is None:native.manageSnapshots().createTag(tag,snapshot).commit()
    else:assert ref.snapshotId()==snapshot,'Tag identity conflict'
    native.refresh();assert native.refs().get(tag).snapshotId()==snapshot

def verify_pins(spark,manifest):
    for t in manifest['tables'].values():
        if t['mode']!='TABLE':continue
        native=spark._jvm.org.apache.iceberg.spark.Spark3Util.loadIcebergTable(spark._jsparkSession,t['iceberg_table'])
        ref=native.refs().get(manifest['publication_id'])
        assert ref is not None and ref.snapshotId()==t['snapshot_id'] and native.snapshot(t['snapshot_id']) is not None,'Lost publication snapshot/tag'
    for h in manifest['helpers'].values():
        path=Path(h['path']);actual={str(p.relative_to(path)):file_hash(p) for p in sorted(path.rglob('*')) if p.is_file()}
        assert actual==h['sha256'] and actual,'Missing or modified helper'

class Reader:
    """Trusted semantic-layer adapter. Fully materializes before lease postcheck.

SQL templates are developer-owned SELECTs with {entity_id} placeholders, not a
public SQL endpoint. No current/latest fallback. Each reader has a Spark session.
"""
    def __init__(self,spark,name='local-validation',ttl=300,schema='ce_control'):
        assert schema in ('ce_control','ce_pub_test')
        self.schema=schema;self.db=Connection(spark,'reader');self.ora=Connection(spark,'reader','oracle');self.spark=spark.newSession();self.ttl=ttl;self.closed=False
        self.lid=str(uuid.uuid4())
        try:
            response=json.loads(self.db.query('SELECT '+schema+'.acquire_reader(?,?,?)',[self.lid,name,ttl])[0][0])
            self.manifest=response['manifest'];self.pid=self.manifest['publication_id']
            assert digest(self.manifest)==response['manifest_sha256'],'Publication manifest checksum mismatch'
            verify_pins(self.spark,self.manifest);self.views={}
            for eid,t in self.manifest['tables'].items():
                if t['mode']=='DISABLED':continue
                view='r_'+self.lid.replace('-','')+'_'+eid.lower()
                if t['mode']=='TABLE':df=self.spark.read.option('snapshot-id',str(t['snapshot_id'])).table(t['iceberg_table'])
                else:
                    from pyspark.sql.types import StructType
                    h=self.manifest['helpers'][t['name']];df=self.spark.read.schema(StructType.fromJson(h['schema'])).parquet(h['path'])
                df.createOrReplaceTempView(view);self.views[eid]=view
            self.check()
        except Exception:
            if hasattr(self,'pid'):self.db.query('SELECT '+schema+'.release_reader(?,?)',[self.lid,self.pid])
            self.db.close();self.ora.close();raise
    def check(self):
        if self.closed:raise RuntimeError('READER_CLOSED')
        self.db.query('SELECT '+self.schema+'.assert_reader(?,?)',[self.lid,self.pid])
    def renew(self):
        self.db.query('SELECT '+self.schema+'.renew_reader(?,?,?)',[self.lid,self.pid,self.ttl])
    def query(self,template,engine):
        self.renew();self.check()
        ids=set(re.findall(r'\{([DFL][0-9]{2})\}',template));assert ids and template.lstrip().upper().startswith(('SELECT','WITH'))
        sql=template
        for eid in ids:
            if eid not in self.views:raise ValueError('Entity absent or optional disabled: '+eid)
            table=self.manifest['tables'][eid]
            replacement=self.views[eid] if engine=='iceberg' else table['oracle_object']
            assert re.fullmatch(r'[A-Za-z0-9_.]+',replacement)
            sql=sql.replace('{'+eid+'}',replacement)
        if engine=='iceberg':result=[list(r) for r in self.spark.sql(sql).collect()]
        elif engine=='oracle':result=self.ora.query(sql)
        else:raise ValueError(engine)
        self.check() # Do not release results from an expired long query.
        return dict(publication_id=self.pid,rows=result,quality_metrics=self.manifest['quality_metrics'])
    def close(self):
        if not self.closed:
            try:self.db.query('SELECT '+self.schema+'.release_reader(?,?)',[self.lid,self.pid])
            finally:self.closed=True;self.ora.close();self.db.close()
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
