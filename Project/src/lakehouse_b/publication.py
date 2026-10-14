from lakehouse_b.common import *

def validate_manifest(spark,m):
    assert len(m['quality_metrics'])==47
    pointer=m['silver_manifest'];assert sha(pointer['path'])==pointer['sha256'],'Silver manifest changed'
    assert read(pointer['path'])['source_batch_id']==m['source_batch_id']
    for spec in m['tables'].values():
        df=pinned(spark,spec)
        assert df.count()==spec['rows'],'Snapshot rows changed'
        assert df.schema.simpleString()==spec['schema'],'Snapshot schema changed'
        assert row_hash([r.asDict(recursive=True) for r in df.select(*spec['columns']).collect()],spec['columns'])==spec['content_sha256'],'Snapshot content changed'
    assert set(m['quality_entities'])==set(m['tables'])
    assert all(q['status'] in ['COMPLETE','PARTIAL','UNAVAILABLE'] for q in m['quality_metrics'].values())

def prepare(db,m):
    pid=m['publication_id'];h=digest(m)
    db.execute("INSERT INTO ce_b.publication VALUES(?,?::jsonb,?,'PREPARED') ON CONFLICT DO NOTHING",[pid,canonical(m),h])
    old=db.query('SELECT sha256 FROM ce_b.publication WHERE id=?',[pid])
    assert old[0][0]==h,'Publication ID reused for different content'

def activate(db,pid,expected):
    db.conn.setAutoCommit(False)
    try:
        current=db.query("SELECT id FROM ce_b.active WHERE name='gold' FOR UPDATE")[0][0]
        if current!=expected:raise ValueError('STALE_PUBLICATION_POINTER')
        rows=db.query('SELECT state FROM ce_b.publication WHERE id=?',[pid]);assert rows
        db.execute("UPDATE ce_b.publication SET state='PUBLISHED' WHERE id=?",[pid])
        db.execute("UPDATE ce_b.active SET id=? WHERE name='gold'",[pid]);db.conn.commit()
    except Exception:db.conn.rollback();raise
    finally:db.conn.setAutoCommit(True)

def publish(spark,db,fail_after=0):
    m=read(OUT/'gold.json')
    assert m['transform_version']==code_version(),'Candidate code changed; rerun Silver and Gold before publication'
    validate_manifest(spark,m);prior=db.active();prepare(db,m)
    if fail_after:raise RuntimeError('INJECTED_FAILURE_BEFORE_POINTER_COMMIT')
    activate(db,m['publication_id'],prior)
    save(OUT/'publication.json',{'status':'PUBLISHED','publication_id':m['publication_id'],'previous':prior,'manifest_sha256':digest(m),'manifest':m,'checked_at':now()})
    print('Published B '+m['publication_id'],flush=True)
