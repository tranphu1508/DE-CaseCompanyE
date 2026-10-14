from collections import Counter,defaultdict
from datetime import datetime
from analytics_runtime.dimension_transform import BOOTSTRAP,dimension_inputs
from analytics_runtime.scd2 import payload_hash,materialize
from analytics_runtime.etl_io import frame
from analytics_runtime.dimensions import validate as validate_dimension
from fact_etl.transform import Transformer
from fact_etl.pipeline import ORDER,enrich,validate,reconciliation
from pyspark.sql import functions as F
from lakehouse_b.common import *
from lakehouse_b.silver import load

def external_reconcile(records,t):
    latest={r['receipt_ref']:r for r in records['receipt_latest']};versions=defaultdict(list)
    for r in records['receipt_versions']:versions[r['receipt_ref']].append(r)
    for ref,rows in versions.items():assert latest[ref]['revision']==max(r['revision'] for r in rows)
    newest=[];mismatches=[]
    for r in records['receipt_quarantine']:
        old=latest.get(r.get('receipt_ref'));rev=r.get('revision')
        if old is None or rev is None or rev>=old['revision']:newest.append({'receipt_ref':r.get('receipt_ref'),'revision':rev,'reason':r.get('quality_reason')})
    for r in records['receipt_latest']:
        db=t.index['hotel_ops.receipts'].get(r['receipt_ref']);reasons=[]
        if db is None:reasons.append('RECEIPT_NOT_IN_DB')
        else:
            line=t.index['hotel_ops.purchase_lines'][db['purchase_line_id']];po=t.index['hotel_ops.purchase_orders'][line['purchase_order_id']]
            for key,expected in [('purchase_line_ref',db['purchase_line_id']),('supplier_id',po['supplier_id']),('hotel_id',po['hotel_id']),('accepted_qty_kg',db['accepted_qty']),('unit_price_vnd',line['unit_price_vnd'])]:
                if r.get(key)!=expected:reasons.append('MISMATCH:'+key)
        if reasons:mismatches.append({'receipt_ref':r['receipt_ref'],'reasons':reasons})
    return {'mismatches':mismatches,'newest_invalid':newest,'policy':'External documents reconcile DB receipts; never additive facts.'}

def check_keys(e,rows):
    for cols in [e['primary_key']]+e['unique_keys']:
        keys=[tuple(r[c] for c in cols) for r in rows if all(r[c] is not None for c in cols)]
        assert len(keys)==len(set(keys)),'Duplicate key: '+e['id']+str(cols)

def build(spark,db,fail_after=0):
    pointer=read(LAKE/'manifests/silver-active.json');assert sha(pointer['path'])==pointer['sha256']
    silver=read(pointer['path']);version=code_version();runid='b_'+digest([pointer['sha256'],version])[:20]
    out=LAKE/'manifests/gold'/(runid+'.json')
    if out.exists():
        report=read(out)
        for spec in report['tables'].values():assert row_hash([r.asDict() for r in pinned(spark,spec).collect()],spec['columns'])==spec['content_sha256']
        save(OUT/'gold.json',report);return report
    source,external=load(spark,silver);sq=silver['source_quality']
    ddl=read(CONFIG/'analytics/ddl/manifest.json');entities={e['id']:e for e in ddl['entities']}
    design=read(CONFIG/'warehouse_design_v1.json');mapping=read(CONFIG/'source_target_mapping_v1.json')
    instant=datetime.fromisoformat(silver['created_at']).replace(tzinfo=None)
    dimensions={};quality={};tables={};business={};dimension_bad=[]
    namespace='ce.gold_'+runid
    def write(e,rows):
        check_keys(e,rows);df=frame(spark,e,rows)
        tables[e['id']]=put_table(spark,namespace+'.'+e['physical_name'],df,df.columns)
        business[e['id']]=rows
        print('Gold '+e['id']+' '+str(len(rows)),flush=True)
        if fail_after and len(tables)==fail_after:raise RuntimeError('INJECTED_FAILURE_AFTER_GOLD_TABLE')
    for e in [x for x in entities.values() if x['kind']=='DIMENSION']:
        eid=e['id'];d=next(x for x in design['tables'] if x['id']==eid);m=next(x for x in mapping['entities'] if x['id']==eid)
        normals,bad=dimension_inputs(e,d,m,source,sq);pk=e['primary_key'][0];rows=[]
        tracked=d.get('tracked_attributes',[c['name'] for c in e['columns'] if c['name'] not in e['primary_key']+['source_system','member_kind']])
        keys=[[eid]+[r[c] for c in d['business_key']]+[scalar(BOOTSTRAP)] for r in normals] if e['history_policy']=='SCD_TYPE2' else []
        registry=db.registry(keys)
        for r in normals:
            r['row_hash']=payload_hash(r,tracked)
            if e['history_policy']=='SCD_TYPE2':
                event={'effective_at':BOOTSTRAP,'payload':{k:v for k,v in r.items() if k!='row_hash'},'row_hash':r['row_hash'],'basis':'BOOTSTRAP_ASSUMPTION','batch':silver['source_batch_id'],'transform':version}
                bk=[r[c] for c in d['business_key']]
                rows+=materialize([event],[],lambda t:registry[canonical([eid]+bk+[scalar(t)])],pk,instant)
            else:rows.append(dict(r,source_batch_id=silver['source_batch_id'],transform_version=version,created_at_utc=instant,updated_at_utc=instant))
        for key,kind in [(0,'UNKNOWN'),(-1,'NOT_APPLICABLE')]:
            r={c['name']:None for c in e['columns']};r.update({pk:key,'source_system':'system','member_kind':kind,'source_batch_id':silver['source_batch_id'],'transform_version':version,'created_at_utc':instant,'updated_at_utc':instant})
            r['row_hash']=payload_hash(r,tracked)
            if e['history_policy']=='SCD_TYPE2':r.update(valid_from_utc=BOOTSTRAP,valid_to_utc=None,is_current=1,version_no=1,effective_time_basis='BOOTSTRAP_ASSUMPTION')
            rows.append(r)
        bad_predicate=F.lit(False)
        for check in ddl['row_checks'][eid]:
            bad_predicate=bad_predicate|(~F.coalesce(F.expr(check['spark']),F.lit(True)))
        invalid=[r.asDict() for r in frame(spark,e,rows).filter(bad_predicate).collect()]
        if invalid:
            assert all(r['member_kind']=='NORMAL' for r in invalid),'Invalid special member'
            rejected_keys={r[pk] for r in invalid};rows=[r for r in rows if r[pk] not in rejected_keys]
        dimension_bad+=bad+[{'entity':eid,'code':'TARGET_CHECK','payload':r} for r in invalid]
        validate_dimension(spark,e,rows,ddl['row_checks'][eid])
        flags=[sq['source_status'].get(n,'UNAVAILABLE') for n in m['aliases'].values()]
        if eid=='D01':flags=list(sq['source_status'].values())+(['PARTIAL'] if sq['date_errors'] else [])
        accepted=sum(r['member_kind']=='NORMAL' for r in rows)
        quality[eid]={'status':'COMPLETE' if not bad and not invalid and all(f=='COMPLETE' for f in flags) else 'PARTIAL' if accepted else 'UNAVAILABLE','accepted':accepted,'rejected':len(bad)+len(invalid)}
        dimensions[eid]=rows;write(e,rows)
    t=Transformer(source,dimensions,design,mapping,sq)
    for eid in ORDER:
        e=entities[eid];rows=t.build(eid)
        enrich(e,rows,t,db,silver['source_batch_id'],version,instant)
        rows=validate(spark,e,rows,ddl,dimensions,t);t.accept(eid,rows)
        bad=[q for q in t.bad if q['entity']==eid]
        flags=[sq['source_status'].get(n,'UNAVAILABLE') for n in t.mapping[eid]['aliases'].values()]+[quality[p]['status'] for p in t.mapping[eid]['depends_on'] if p in quality]
        quality[eid]={'status':'COMPLETE' if not bad and all(f=='COMPLETE' for f in flags) else 'PARTIAL' if rows else 'UNAVAILABLE','accepted':len(rows),'rejected':len(bad),'business_filtered':t.filtered[eid]}
        write(e,rows)
    # Check every declared FK across the complete candidate before publication.
    for eid,rows in business.items():
        for c in entities[eid]['columns']:
            if c.get('references'):
                parent,col=c['references'].split('.')
                if parent not in business:continue
                keys={r[col] for r in business[parent]}
                assert all(r[c['name']] is None or r[c['name']] in keys for r in rows),'FK '+eid+'.'+c['name']
    recon=reconciliation(t);external=external_reconcile(external,t)
    for eid,key in [('F08','meal_session_mismatches'),('F14','negative_lot_prefixes')]:
        if recon[key]:quality[eid]['status']='PARTIAL'
    metrics={}
    for m in mapping['metric_mapping']:
        deps=m['primary_facts']+m['supporting_facts'];flags=[quality.get(d,{'status':'UNAVAILABLE'})['status'] for d in deps]
        metrics[m['id']]={'status':'UNAVAILABLE' if 'UNAVAILABLE' in flags else 'PARTIAL' if 'PARTIAL' in flags else 'COMPLETE','dependencies':deps}
    report={'publication_id':runid,'source_batch_id':silver['source_batch_id'],'source_catalog_sha256':silver['source_catalog_sha256'],'silver_manifest':pointer,'transform_version':version,'tables':tables,'quality_entities':quality,'quality_metrics':metrics,'quality_scope':t.scope,'external_warnings':external['mismatches']+external['newest_invalid'],'external_reconciliation':external,'reconciliation':recon,'status':'PREPARED','created_at':silver['created_at'],'optional_disabled':['F15'],'storage':'Iceberg tables within the lakehouse volume; no canonical Parquet duplicate.'}
    save(LAKE/'quarantine'/runid/'gold.json',dimension_bad+t.bad)
    immutable(out,report);save(OUT/'gold.json',report)
    return report
