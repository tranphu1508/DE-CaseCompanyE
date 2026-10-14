"""Freeze per-column physical mappings and local deployment/benchmark choices.

Documentation generator only: no database connection, DDL, image pull or ETL.
"""
from pathlib import Path
import json,hashlib,re

ROOT=Path(__file__).resolve().parents[1]
INPUTS=['config/warehouse_design_v1.json','config/logical_model_v1_1.json',
        'config/source_target_mapping_v1.json','config/kpi_contract_v1.json',
        'config/analytics_runtime_lock_v1.json','reports/local_environment_physical_design.json',
        'lake/v2/catalog/catalog.json','compose.analytics.yaml','config/analytics/spark-defaults.conf',
        'reports/docker-storage-migration-20261013/verification.json',
        'reports/analytics-runtime/verification.json']
def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def save(p,data):(ROOT/p).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
hashes={p:sha(p) for p in INPUTS}
design=read(INPUTS[0]);logical=read(INPUTS[1]);lock=read(INPUTS[4]);env=read(INPUTS[5]);catalog=read(INPUTS[6])
SPARK={'KEY':'BIGINT','DATEKEY':'INT','COUNT':'BIGINT','INT':'INT','FLAG':'INT',
       'MONEY':'DECIMAL(19,0)','QTY':'DECIMAL(18,3)','VALUE':'DECIMAL(38,3)',
       'DATE':'DATE','UTC':'TIMESTAMP_NTZ','ID':'STRING','CODE':'STRING','TEXT':'STRING','HASH':'STRING'}
TIMING={'F01':'arrival_date_key','F02':'date_key','F03':'service_date_key',
 'F04':'ordered_date_key','F05':'pickup_date_key','F06':'service_date_key',
 'F07':'service_date_key','F08':'service_date_key','F09':'admission_date_key','F10':'date_key',
 'F11':'date_key','F12':'ordered_date_key','F13':'received_date_key','F14':'movement_date_key',
 'F15':'snapshot_date_key','F16':'end_date_key','F17':'weather_date_key'}
ICEBERG_PROPS={'format-version':'2','write.format.default':'parquet','write.parquet.compression-codec':'snappy',
 'write.target-file-size-bytes':'134217728','write.delete.mode':'copy-on-write',
 'write.update.mode':'copy-on-write','write.merge.mode':'copy-on-write',
 'write.metadata.delete-after-commit.enabled':'false'}

entities=[]
for t in design['tables']:
    tid=t['id'];name=t['physical_name'];view=t['kind']=='VALIDATION_VIEW'
    idx=[]
    if not view:
        idx.append(dict(name='pk_'+tid.lower(),kind='PRIMARY_KEY_BTREE',columns=t['primary_key']))
        for n,key in enumerate(t['unique_keys'],1):
            if key==t['primary_key']:continue
            item=dict(name=f'uk_{tid.lower()}_{n}',kind='UNIQUE_BTREE',columns=key)
            if t.get('history_policy')=='SCD_TYPE2':
                item['condition']="member_kind='NORMAL'"
                item['expressions']=["CASE WHEN member_kind='NORMAL' THEN "+c+' END' for c in key]
            idx.append(item)
        for n,key in enumerate(t.get('conditional_unique_keys',[]),1):
            idx.append(dict(name=f'uc_{tid.lower()}_{n}',kind='CONDITIONAL_UNIQUE_BTREE',columns=key['columns'],condition=key['condition'],
                expressions=[f"CASE WHEN {key['condition']} THEN {c} END" for c in key['columns']]))
    cols=[]
    for c in t['columns']:
        types=design['types'][c['type']]
        cols.append(dict(name=c['name'],logical_type=c['type'],oracle_type=types['oracle'],iceberg_type=types['iceberg'],spark_sql_type=SPARK[c['type']],
            nullable=c['nullable'],required_for_normal_member=c.get('required_for_normal_member',False),
            references=c.get('references'),missing_policy=c.get('missing_policy'),aggregation=c['aggregation']))
    entities.append(dict(id=tid,name=t['name'],physical_name=name,kind=t['kind'],grain=t['grain'],scope=t['scope'],
        oracle=dict(owners=['ce_dwh_a','ce_dwh_b'],object_type='VIEW' if view else 'HEAP_TABLE',
            helper_source=('ce_stage.'+name+'_input_{slot}') if view else None,
            tablespace=None if view else 'ce_data',partitioning=None,indexes=idx,parallel_degree=1,compression='NONE',
            constraints='View key checks on canonical helper inputs; no PK on view' if view else 'NOT NULL, PK/UK, 106 declared FK roles across model, expressible CHECK; SCD interval checks also in pipeline'),
        iceberg=dict(catalog='ce',namespace='gold',object_type='SESSION_VIEW' if view else 'ICEBERG_TABLE',
            view_source='publication-pinned canonical Parquet input' if view else None,
            partitioning=[],sort_order=[],table_properties={} if view else ICEBERG_PROPS.copy(),
            constraints='Required fields via schema; PK/UK/FK/CHECK and SCD interval rules enforced by validation pipeline; identifiers are not uniqueness enforcement'),
        primary_key=t['primary_key'],unique_keys=t['unique_keys'],conditional_unique_keys=t.get('conditional_unique_keys',[]),
        history_policy=t['history_policy'],checks=t['checks'],columns=cols,
        optional_tuning=dict(enabled=False,date_column=TIMING.get(tid),
            oracle='Test one workload-driven date/FK B-tree after baseline; record DDL and rebuild time',
            iceberg='Test sort/compaction after baseline; monthly partition experiment only if measured size justifies it')))

plan=dict(version='companye-physical-design-1.0',created_on='2026-10-13',status='RUNTIME_READY_BUSINESS_SCHEMA_NOT_DEPLOYED',
 input_sha256=hashes,logical_version=logical['version'],design_version=design['version'],source_batch=catalog['batch_id'],
 runtime=lock,domains={k:dict(v,spark_sql=SPARK[k]) for k,v in design['types'].items()},
 resource_profiles={
  'baseline':{'oracle_cpu_quota':2,'oracle_container_gib':4,'oracle_database_memory_limit_gb':2,'spark_cpu_quota':2,'spark_container_gib':4,'spark_driver_heap_gib':2,'spark_master':'local[2]','metadata_cpu_quota':1,'metadata_container_mib':512,'run_engines_sequentially':True},
  'spark_engineering_optional':{'enabled':False,'cpu_quota':4,'container_gib':6,'driver_heap_gib':3,'master':'local[4]','eligible_for_equal_budget_comparison':False}},
 storage={'hot':'Docker named volumes on E-backed Linux VHDX','source':'Read-only bind mount Project/lake/v2',
          'input_snapshot_policy':'Copy the selected standardized snapshot once into /analytics/input after checksum verification; use same copy for both branch loads; source-copy time recorded separately',
          'start_min_free_gib':50,'reserve_min_free_gib':20,'windows_project_min_free_gib':5,'oracle_user_data_stop_gb':9,
          'stress_scales':[1,2,5,10],'stress_enabled':False,
          'growth_gate':'Next run requires measured projected additional footprint plus reserve; account for both Oracle slots, staging, Iceberg snapshots, index/temp and VHDX host free space'},
 oracle={'pdb':'FREEPDB1','character_set':'AL32UTF8','schemas':['ce_dwh_a','ce_dwh_b','ce_stage'],
         'tablespace':'ce_data','stage_tablespace':'ce_stage_data','session_time_zone':'+00:00','nls_comp':'BINARY','nls_sort':'BINARY',
         'result_cache_mode':'MANUAL','parallel_degree_policy':'MANUAL','default_parallel_degree':1,
         'query_client':'Oracle JDBC, native SQL; no Spark execution of Oracle KPI queries',
         'load_strategy':'Explicit pre-created DDL; JDBC append into isolated candidate tables with numPartitions<=2 and batchsize=1000; validation before publication; no inferred overwrite schema',
         'stats':'DBMS_STATS after accepted load, outside query timing; statistics time recorded in load totals',
         'tablespace_initial_mib':256,'tablespace_autoextend_next_mib':64,'tablespace_max_gib':{'ce_data':8,'ce_stage_data':1}},
 iceberg={'version':'1.10.2','catalog_type':'JDBC','catalog_metadata':'PostgreSQL 17, ce_metadata.iceberg_catalog',
          'warehouse':'file:///analytics/iceberg','catalog_name':'ce','namespace':'gold','format_version':2,
          'data_format':'Parquet','compression':'snappy','target_file_mib':128,
          'table_commit':'Atomic per table; not an atomic transaction spanning all 35 tables',
          'load_strategy':'Explicit schema; full accepted candidate for first load; controlled overwrite/replacement preserving complete SCD history; incremental MERGE experiments later',
          'read_strategy':'Each benchmark/report registers views pinned to the exact snapshot IDs in one publication manifest',
          'retention':'Keep snapshots referenced by current/previous publications and reader leases; no automatic expiration in baseline'},
 control={'database':'ce_metadata','schema':'ce_control','role':'metadata/control only, not a competing warehouse',
          'planned_entities':['key_registry','pipeline_run','quality_entity','quality_metric','publication','publication_table','active_publication','reader_lease','benchmark_run'],
          'key_registry':'Append-only canonical tuple->positive SK; dimensions include entity/namespace/BK/valid_from; facts use durable natural key; never allocate with row_number',
          'two_oracle_slots':'Candidate is inactive, unleased slot; build all tables and helper views there. Keep published slot read-only. Reader lease prevents slot reuse during a pinned query/refresh.',
          'publication':'Single coordinator validates both branch manifests, writes immutable publication with Oracle slot and Iceberg snapshots, then atomically changes active pointer in control transaction. This is visibility control, not distributed ACID.',
          'partial_policy':'Publish valid accepted set plus COMPLETE/PARTIAL/UNAVAILABLE per KPI; engine failure or indeterminate cutoff is not publishable',
          'unknown_missing_counts':'NULL/UNKNOWN if entire input missing and expected count untrusted; never manufacture 0%/100% completeness'},
 presentation={'power_bi_baseline':'Import per-publication KPI/detail exports calculated independently by each engine; one fixed publication_id and branch for entire refresh',
               'web_baseline':'Read the same published serving exports through a small API; render freshness and quality status',
               'direct_connect_optional':'Oracle connector / Spark JDBC-ODBC path requires separate connector smoke test and pinned publication context; not assumed available',
               'timing':'Engine SQL, export, BI refresh and UI latency measured separately'},
 benchmark={'input':'same catalog hash, seed, canonical accepted/rejected sets, key registry and KPI contract',
            'warmup_runs':1,'measured_runs':5,'summary':['median','min','max'],'engine_order':'alternate Oracle/Iceberg across series',
            'no_p95_claim_with_5_samples':True,'reader_levels':[1,2,4,8],'writer_count':1,
            'record':['input_rows','accepted_rows','quarantine_rows','dependency_excluded_rows','run_wall_time','query_wall_time','cpu','memory_peak','spill','gc','io','data_bytes','index_bytes','metadata_bytes','snapshot_bytes','quality_status','query_plan','image_digest'],
            'cache':'warm repeat baseline; no CACHE TABLE or query-result cache; container restart alone is not proven cold cache',
            'correctness':'Exact integers/monetary values/decimal quantities and null/status semantics; ratio numerator and denominator exact, display rounding per KPI contract',
            'fault_cases':['SCD2 no-change','SCD2 boundary change','A-B-A','late correction','replay','bad FK','duplicate room-night','missing source file','failure after one Iceberg commit','failure before active-pointer switch'],
            'interpretation':'Single host, bounded Oracle Free vs Spark; not proof of enterprise scale-out or production cost'},
 entities=entities)

# Verify the materialized plan rather than trusting a manually typed inventory.
assert len(entities)==37
assert sum(len(t['columns']) for t in entities)==631
assert sum(t['oracle']['object_type']=='HEAP_TABLE' for t in entities)==35
assert sum(t['oracle']['object_type']=='VIEW' for t in entities)==2
assert sum(t['history_policy']=='SCD_TYPE2' for t in entities)==14
fk=[(t['id'],c) for t in entities for c in t['columns'] if c.get('references')]
assert len(fk)==106 and sum(t.startswith('F') for t,c in fk)==102
logical_by_id={t['id']:t for t in logical['tables']}
for t in entities:
    assert re.fullmatch('[a-z][a-z0-9_]*',t['physical_name'])
    assert [c['name'] for c in t['columns']]==[c['name'] for c in logical_by_id[t['id']]['columns']]
    assert not t['oracle']['partitioning'] and not t['iceberg']['partitioning']
    for c in t['columns']:
        if c['logical_type']=='UTC':assert c['spark_sql_type']=='TIMESTAMP_NTZ' and c['iceberg_type']=='timestamp'
    for ix in t['oracle']['indexes']:assert len(ix['name'])<=30
assert all(hashes[p]==sha(p) for p in INPUTS)
save('config/physical_design_v1.json',plan)
migration=read(INPUTS[9])
assert migration['status']=='PASSED'
assert lock['storage_observation']['windows_vhdx']==migration['windows_vhdx'].replace('\\','/')
runtime=read(INPUTS[10])
assert runtime['status']=='PASSED_SERVICE_PROVISIONING_AND_RESTART'
volumes={x['DriveLetter']:x for x in runtime['host_storage']}
report=dict(status='PASSED_DESIGN_CHECKS',runtime_smoke_test='PASSED_SERVICE_INTEGRATION_AND_RESTART',compose_validation='PENDING',
    generated_on='2026-10-13',entities=37,business_tables_per_branch=35,logical_views_per_branch=2,columns=631,
    oracle_integrity_indexes=sum(len(t['oracle']['indexes']) for t in entities),foreign_keys=106,
    fact_dimension_foreign_keys=102,scd2_dimensions=14,static_dimensions=2,kpis=len(design['metric_mapping']),
    input_sha256=hashes,output_sha256={'config/physical_design_v1.json':sha('config/physical_design_v1.json')},
    host_free_gib={k:round(v['SizeRemaining']/1024**3,2) for k,v in volumes.items()},
    checks=['All 631 column types mapped','UTC is TIMESTAMP_NTZ in Spark and timezone-free timestamp in both engines',
            'PK/UK and SCD2 conditional index plan','35 tables and two logical views per branch',
            '106 FK roles retained','No baseline partition or optional tuning enabled','Input hashes preserved'],
    limits=['Service integration probe passed; business schema is not deployed',
            'No business ETL, SCD2 pipeline, KPI query benchmark or stress test run',
            'Storage gates must be rechecked immediately before data loads/scale-up'])
save('reports/physical_design_v1_validation.json',report)
print(json.dumps({k:v for k,v in report.items() if k not in ['input_sha256','output_sha256']},ensure_ascii=False,indent=2))
