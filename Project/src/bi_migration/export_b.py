"""Export certified B snapshots for BI without changing its pipeline fingerprint."""
from pathlib import Path
import csv,hashlib,json,os
from lakehouse_b.common import create_session,Database,Reader,OUT,save,digest,sha,now
from powerbi_export import SKIP,AUDIT,value

def main():
    certified=json.loads((OUT/'verification.json').read_text())
    fixtures=json.loads((OUT/'fixtures.json').read_text())
    assert certified['status']==fixtures['status']=='PASSED'
    spark=create_session('CompanyE-B-BI-export');spark.sparkContext.setLogLevel('WARN')
    db=Database(spark);reader=Reader(spark,db)
    try:
        assert reader.pid==certified['publication_id']
        entities=json.loads(Path('/workspace/config/analytics/ddl/manifest.json').read_text())['entities']
        folder=OUT/'bi-imports'/reader.pid;folder.mkdir(parents=True,exist_ok=True);checks=[]
        for e in entities:
            eid=e['id']
            if eid in SKIP:continue
            cols=[c for c in e['columns'] if c['name'] not in AUDIT];names=[c['name'] for c in cols]
            # Renew the lease, then read the session's already pinned view.
            reader.query('SELECT 1 FROM {D01} LIMIT 1')
            rows=spark.table(reader.names[eid]).select(*names).collect()
            normalized=sorted(tuple(value(r[c['name']],c) for c in cols) for r in rows)
            assert len(rows)==reader.manifest['tables'][eid]['rows']
            target=folder/(eid+'.csv');temp=folder/(eid+'.pending.csv')
            with temp.open('w',encoding='utf8',newline='') as f:
                writer=csv.writer(f);writer.writerow(names+([] if eid.startswith('D') else ['engine']))
                writer.writerows(normalized if eid.startswith('D') else [list(r)+['iceberg'] for r in normalized])
            if target.exists():assert sha(target)==sha(temp),'Immutable BI export changed';temp.unlink()
            else:os.replace(str(temp),str(target))
            checks.append({'entity':eid,'columns':cols,'rows_per_engine':len(rows),'import_rows':len(rows),
                           'filename':target.name,'sha256':sha(target),'snapshot_id':reader.manifest['tables'][eid]['snapshot_id']})
            print('BI B exported '+eid+' '+str(len(rows)),flush=True)
        m={'status':'PINNED_EXPORT_READY','publication_id':reader.pid,'publication_manifest_sha256':digest(reader.manifest),
           'source_batch_id':reader.manifest['source_batch_id'],'source_catalog_sha256':reader.manifest['source_catalog_sha256'],
           'engines':['iceberg'],'default_engine':'iceberg','tables':checks,'quality_metrics':reader.manifest['quality_metrics'],
           'quality_scope':reader.manifest['quality_scope'],'external_warning_count':len(reader.manifest['external_warnings']),
           'exported_at':now(),'privacy':'No customer profile dimensions; row-level exports remain local and are not committed.'}
        save(folder/'manifest.json',m);save(OUT/'bi-export.json',m)
    finally:reader.close();db.close();spark.stop()

if __name__=='__main__':main()
