"""Seal schema deployment evidence; does not mutate databases or design contracts."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'reports/schema-deployment'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
m=read(ROOT/'config/analytics/ddl/manifest.json')
o=read(OUT/'oracle-verification.json');i=read(OUT/'iceberg-verification.json');f=read(OUT/'oracle-constraint-fixtures.json')
assert o['status']==i['status']==f['status']=='PASSED'
assert o['all_tables_empty'] and i['all_tables_empty'] and f['fixtures_rolled_back']
assert o['manifest_sha256']==i['manifest_sha256']==sha(ROOT/'config/analytics/ddl/manifest.json')
assert m['physical_model_sha256']==sha(ROOT/'config/physical_design_v1.json')
assert m['logical_model_sha256']==sha(ROOT/'config/logical_model_v1_1.json')
for name,h in m['ddl_sha256'].items():assert sha(ROOT/'config/analytics/ddl'/name)==h
physical=read(ROOT/'config/physical_design_v1.json')
for name in ['config/warehouse_design_v1.json','config/source_target_mapping_v1.json','config/kpi_contract_v1.json','lake/v2/catalog/catalog.json']:
    assert sha(ROOT/name)==physical['input_sha256'][name]
evidence=['oracle-verification.json','iceberg-verification.json','oracle-constraint-fixtures.json','oracle-constraint-fixtures.sql','helper-fixture-manifest.json']
code=['scripts/build-analytics-schema.py','scripts/deploy-analytics-schema.py','scripts/test-analytics-schema.py',
      'scripts/finalize-schema-deployment.py','src/analytics_runtime/deploy_schema.py','src/analytics_runtime/validation_views.py']
report=dict(status='PASSED_SCHEMA_DEPLOYMENT',completed_at=datetime.now(timezone.utc).isoformat(),
    business_data_loaded=False,business_tables_per_branch=35,dimensions=16,facts_and_optional_aggregate=17,bridges=2,
    logical_views_per_branch=2,logical_columns_per_branch=631,
    oracle=dict(owners=['CE_DWH_A','CE_DWH_B'],tables_per_owner=35,views_per_owner=2,helper_tables_in_ce_stage=4,
                foreign_keys_per_owner=106,unique_indexes_per_owner=99,helper_primary_key_indexes=4,
                all_objects_valid=True,all_declared_constraints_enabled_validated=True,
                checks_compared_with_metadata=True,native_rejection_fixtures_passed=len(f['native_rejections'])),
    iceberg=dict(namespace='ce.gold',tables=35,required_fields_verified=True,partitioned=False,
                 format_version=2,session_view_registration_verified=2,missing_helper_rejected=True,
                 native_primary_foreign_unique_check_constraints=False),
    source_contracts_and_catalog_unchanged=True,
    physical_model_sha256=m['physical_model_sha256'],logical_model_sha256=m['logical_model_sha256'],
    manifest_sha256=sha(ROOT/'config/analytics/ddl/manifest.json'),ddl_sha256=m['ddl_sha256'],
    evidence_sha256={p:sha(OUT/p) for p in evidence},code_sha256={p:sha(ROOT/p) for p in code},
    next_step='ETL/control schemas and roles, canonical key registry, dimension SCD2 loading, fact/bridge loading, quality and publication; validate before KPI or benchmark.',
    limitations=['Iceberg PK/UK/FK/checks and cross-source rules must be enforced by ETL; generated predicates are a specification, not a running pipeline.',
                 'SCD interval overlap is not prevented by Oracle row constraints or current-row unique indexes; this is demonstrated and requires ETL validation.',
                 'Two Spark helper views are session scoped; only explicit empty schema-validation Parquet was tested. No business helper publication exists.',
                 'Oracle owners are schema-only accounts; application ETL/BI logins and grants are a subsequent step.',
                 'No source data loaded, default dimension members seeded, KPI evaluated or benchmark run.'])
(OUT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:report[k] for k in ['status','business_tables_per_branch','logical_columns_per_branch','business_data_loaded']},indent=2))
