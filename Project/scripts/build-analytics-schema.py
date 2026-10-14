"""Generate non-destructive Oracle/Iceberg DDL from the approved physical model.

DDL has no DROP/TRUNCATE, and does not insert seed/business data. Native Oracle
constraints and equivalent Spark predicates are inventoried separately from
cross-row/source-dependent rules that must still be implemented in ETL.
"""
from pathlib import Path
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'config/analytics/ddl'
OUT.mkdir(parents=True,exist_ok=True)
model=json.loads((ROOT/'config/physical_design_v1.json').read_text(encoding='utf-8'))
entities=model['entities']; byid={t['id']:t for t in entities}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,obj):(OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def literal(value):return "'"+value.replace("'","''")+"'"
def guarded(sql,query):
    return 'DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM '+query+'; IF n=0 THEN EXECUTE IMMEDIATE '+literal(sql)+'; END IF; END;\n/'

# SQL predicates for row-local business rules. NULL remains permitted only where
# the column contract permits it; required NORMAL attributes have explicit IS NOT NULL.
local={
'D03':["stars IN (3,5)"],
'D04':['capacity>0','base_rate_vnd>0'],
'D05':['commission_bps BETWEEN 0 AND 10000'],
'D06':['discount_bps BETWEEN 0 AND 10000','partner_share_bps BETWEEN 0 AND 10000','cap_vnd>=0','sale_to>=sale_from','stay_to>=stay_from'],
'D09':["outlet_type IN ('RESTAURANT','BAR')",'capacity>0'],
'D12':['capacity_per_day>0'], 'D13':['daily_rate_vnd>0'], 'D15':['shelf_life_days>=0'],
'F01':["status IN ('COMPLETED','CANCELLED','NO_SHOW')",'arrival_date_key<departure_date_key','booked_date_key<=arrival_date_key','discount_vnd=company_share_vnd+partner_share_vnd','customer_due_vnd=gross_vnd-discount_vnd','booking_count=1'],
'F02':['inventory_day=1','available_day=inventory_day-blocked_day'], 'F03':['occupied_night=1'],
'F04':['gross_vnd>=refunded_vnd','net_ticket_vnd=gross_vnd-refunded_vnd'],
'F05':["status IN ('COMPLETED','CANCELLED')",'pickup_date_key<return_date_key'],
'F06':['eligible_covers>=redeemed_covers','meal_key=1'],
'F07':['rating_sum BETWEEN 1 AND 5','rating_count=1'],
'F08':['meal_key IN (1,3)'], 'F09':['admission_count=1'],
'F10':['nominal_capacity>0','available_capacity=nominal_capacity*(1-is_closed)'],
'F11':['inventory_day=1','available_day=1-maintenance_day','rented_day<=available_day'],
'F12':['ordered_qty>0','unit_price_vnd>=0','ordered_date_key<=expected_date_key'],
'F13':['accepted_qty>=0','rejected_qty>=0','late_accepted_qty IN (0,accepted_qty)'],
'F14':["movement_type IN ('IN','USE','WASTE')",'quantity>=0','in_qty>=0','use_qty>=0','waste_qty>=0','signed_qty=in_qty-use_qty-waste_qty'],
'F15':['closing_qty>=0','in_qty>=0','use_qty>=0','waste_qty>=0'],
'F16':['start_date_key<end_date_key',"work_type IN ('BREAKDOWN','PLANNED')","status='COMPLETED'"],
'F17':['rain_mm>=0'],
}
rows={}
for t in entities:
    tid=t['id']; checks=[]
    def add(oracle,spark=None):checks.append(dict(name=f'ck_{tid.lower()}_{len(checks)+1:02}',oracle=oracle,spark=spark or oracle))
    names={c['name'] for c in t['columns']}
    for c in t['columns']:
        name=c['name']; typ=c['logical_type']
        if typ=='FLAG':add(f'{name} IN (0,1)')
        if typ=='COUNT':add(f'{name}>=0 AND {name}<=999999999999999999')
        if typ=='INT':add(f'{name} BETWEEN -2147483648 AND 2147483647')
        if typ=='KEY':add(f'{name} BETWEEN -1 AND 999999999999999999')
        if typ=='DATEKEY':add(f'{name} BETWEEN -1 AND 99999999')
        if typ=='DATE':add(f'{name}=TRUNC({name})','TRUE')
        if typ=='HASH':add(f"REGEXP_LIKE({name}, '^[0-9a-f]{{64}}$', 'c')",f"{name} RLIKE '^[0-9a-f]{{64}}$'")
        if tid.startswith('F') and typ=='MONEY':add(f'{name}>=0')
    if 'fact_key' in names:add('fact_key>0')
    if t['kind']=='DIMENSION':
        key=t['primary_key'][0]
        add(f"(member_kind='NORMAL' AND {key}>0) OR (member_kind='UNKNOWN' AND {key}=0) OR (member_kind='NOT_APPLICABLE' AND {key}=-1)")
        required=[c['name']+' IS NOT NULL' for c in t['columns'] if c['required_for_normal_member']]
        if required:add("member_kind<>'NORMAL' OR ("+' AND '.join(required)+')')
    if t['history_policy']=='SCD_TYPE2':
        add('version_no>=1')
        add('(is_current=1 AND valid_to_utc IS NULL) OR (is_current=0 AND valid_to_utc IS NOT NULL)')
        add('valid_to_utc IS NULL OR valid_from_utc<valid_to_utc')
        add("member_kind='NORMAL' OR (version_no=1 AND is_current=1 AND valid_to_utc IS NULL)")
    for expr in local.get(tid,[]):
        add(("member_kind<>'NORMAL' OR ("+expr+')') if t['kind']=='DIMENSION' else expr)
    if tid=='D01':
        add("member_kind<>'NORMAL' OR date_key=TO_NUMBER(TO_CHAR(calendar_date,'YYYYMMDD'))",
            "member_kind<>'NORMAL' OR date_key=CAST(date_format(calendar_date,'yyyyMMdd') AS INT)")
        for col,part in [('year','YEAR'),('month','MONTH'),('day','DAY')]:
            add(f"member_kind<>'NORMAL' OR {col}=EXTRACT({part} FROM calendar_date)")
        add("member_kind<>'NORMAL' OR quarter=CEIL(month/3.0)")
        add("member_kind<>'NORMAL' OR day_of_week=calendar_date-TRUNC(calendar_date,'IW')+1",
            "member_kind<>'NORMAL' OR day_of_week=pmod(dayofweek(calendar_date)+5,7)+1")
    if tid=='D10':
        add("member_kind<>'NORMAL' OR (meal_key=1 AND meal_code='BREAKFAST') OR (meal_key=2 AND meal_code='LUNCH') OR (meal_key=3 AND meal_code='DINNER') OR (meal_key=4 AND meal_code='BAR')")
    rows[tid]=checks

statements=[]; objects=[]; constraints=[]; indexes=[]
def emit(sql,query):statements.append(guarded(sql,query))
for name,maxg in [('ce_data',8),('ce_stage_data',1)]:
    sql=f"CREATE TABLESPACE {name} DATAFILE '/opt/oracle/oradata/FREE/FREEPDB1/{name}01.dbf' SIZE 256M AUTOEXTEND ON NEXT 64M MAXSIZE {maxg}G"
    emit(sql,f"dba_tablespaces WHERE tablespace_name='{name.upper()}'")
for owner,ts,quota in [('ce_dwh_a','ce_data','8G'),('ce_dwh_b','ce_data','8G'),('ce_stage','ce_stage_data','1G')]:
    emit(f'CREATE USER {owner} NO AUTHENTICATION DEFAULT TABLESPACE {ts} QUOTA {quota} ON {ts}',f"dba_users WHERE username='{owner.upper()}'")

def constraint(owner,table,name,kind,clause,columns=None,expr=None,reference=None):
    emit(f'ALTER TABLE {owner}.{table} ADD CONSTRAINT {name} {clause}',
         f"dba_constraints WHERE owner='{owner.upper()}' AND constraint_name='{name.upper()}'")
    constraints.append(dict(owner=owner,table=table,name=name,kind=kind,columns=columns or [],expression=expr,reference=reference))

for slot in ['a','b']:
    owner='ce_dwh_'+slot
    for t in entities:
        tid=t['id']; view=t['kind']=='VALIDATION_VIEW'
        target_owner='ce_stage' if view else owner
        table=t['physical_name']+f'_input_{slot}' if view else t['physical_name']
        ts='ce_stage_data' if view else 'ce_data'
        cols=',\n  '.join(c['name']+' '+c['oracle_type']+(' NOT NULL' if not c['nullable'] else '') for c in t['columns'])
        emit(f'CREATE TABLE {target_owner}.{table} (\n  {cols}\n) TABLESPACE {ts} NOCOMPRESS NOPARALLEL',
             f"dba_tables WHERE owner='{target_owner.upper()}' AND table_name='{table.upper()}'")
        objects.append(dict(owner=target_owner,name=table,kind='TABLE',entity_id=tid,tablespace=ts,columns=t['columns']))
        suffix='_'+slot if view else ''
        index_plan=t['oracle']['indexes'] if not view else [dict(name='pk_'+tid.lower(),kind='PRIMARY_KEY_BTREE',columns=t['primary_key'])]
        for ix in index_plan:
            name=ix['name']+suffix
            expressions=ix.get('expressions',ix['columns'])
            if ix['kind']=='PRIMARY_KEY_BTREE' or (ix['kind']=='UNIQUE_BTREE' and not ix.get('condition')):
                kind='P' if ix['kind']=='PRIMARY_KEY_BTREE' else 'U'
                typ='PRIMARY KEY' if kind=='P' else 'UNIQUE'
                constraint(target_owner,table,name,kind,f"{typ} ({','.join(ix['columns'])}) USING INDEX TABLESPACE {ts}",ix['columns'])
            else:
                emit(f"CREATE UNIQUE INDEX {target_owner}.{name} ON {target_owner}.{table} ({','.join(expressions)}) TABLESPACE {ts}",
                     f"dba_indexes WHERE owner='{target_owner.upper()}' AND index_name='{name.upper()}'")
            indexes.append(dict(owner=target_owner,table=table,name=name,expressions=expressions,function_based=bool(ix.get('condition')),tablespace=ts))
        for check in rows[tid]:
            constraint(target_owner,table,check['name']+suffix,'C','CHECK ('+check['oracle']+')',expr=check['oracle'])
        if view:
            statements.append(f'GRANT SELECT ON {target_owner}.{table} TO {owner};')
            name=t['physical_name']
            emit(f"CREATE VIEW {owner}.{name} AS SELECT {','.join(c['name'] for c in t['columns'])} FROM {target_owner}.{table}",
                 f"dba_views WHERE owner='{owner.upper()}' AND view_name='{name.upper()}'")
            objects.append(dict(owner=owner,name=name,kind='VIEW',entity_id=tid,columns=t['columns'],helper=f'{target_owner}.{table}'))
    for t in entities:
        if t['kind']=='VALIDATION_VIEW':continue
        for i,c in enumerate(t['columns']):
            if not c['references']:continue
            refid,refcol=c['references'].split('.')
            reftable=byid[refid]['physical_name']
            constraint(owner,t['physical_name'],f"fk_{t['id'].lower()}_{i:02}",'R',
                       f"FOREIGN KEY ({c['name']}) REFERENCES {owner}.{reftable} ({refcol})",
                       [c['name']],reference=dict(owner=owner,table=reftable,column=refcol))

prefix="set echo off verify off define off feedback off\nwhenever sqlerror exit sql.sqlcode\nwhenever oserror exit failure\nalter session set container=FREEPDB1;\n"
(OUT/'oracle_schema.sql').write_text(prefix+'\n\n'.join(statements)+'\nprompt SCHEMA_DDL_COMPLETE\nexit\n',encoding='utf-8')
iceberg=[]
for t in entities:
    if t['kind']=='VALIDATION_VIEW':continue
    cols=',\n  '.join('`'+c['name']+'` '+c['spark_sql_type']+(' NOT NULL' if not c['nullable'] else '') for c in t['columns'])
    props=', '.join(literal(k)+'='+literal(v) for k,v in t['iceberg']['table_properties'].items())
    iceberg.append(dict(entity_id=t['id'],name=t['physical_name'],sql=f"CREATE TABLE IF NOT EXISTS ce.gold.{t['physical_name']} (\n  {cols}\n) USING iceberg TBLPROPERTIES ({props})"))
(OUT/'iceberg_schema.sql').write_text('CREATE NAMESPACE IF NOT EXISTS ce.gold;\n\n'+';\n\n'.join(s['sql'] for s in iceberg)+';\n',encoding='utf-8')
manifest=dict(version='companye-schema-ddl-1.0',generated_on='2026-10-14',
    physical_model_sha256=sha(ROOT/'config/physical_design_v1.json'),
    logical_model_sha256=sha(ROOT/'config/logical_model_v1_1.json'),entities=entities,
    oracle_objects=objects,oracle_constraints=constraints,oracle_indexes=indexes,
    iceberg_statements=iceberg,row_checks=rows,
    pipeline_required={t['id']:dict(declared_rules=t['checks'],required_checks=['PK/UK/FK and row predicates on Iceberg accepted data',
        'SCD interval non-overlap and correct temporal dimension lookup' if t['history_policy']=='SCD_TYPE2' else 'Cross-source, cross-table and eligibility rules as applicable'],
        status='NOT_IMPLEMENTED_BY_DDL') for t in entities},
    view_policy='Oracle views read separate ce_stage helper tables per slot. Spark views require explicit publication helper paths, schema and SHA-256. No silent empty view for missing input.',
    ddl_sha256={f:sha(OUT/f) for f in ['oracle_schema.sql','iceberg_schema.sql']})
assert len(iceberg)==35 and len(objects)==78 and sum(len(t['columns']) for t in entities)==631
assert sum(c['kind']=='R' for c in constraints)==212
assert len(indexes)==202
assert all(re.fullmatch('[a-z][a-z0-9_]*',c['name']) and len(c['name'])<=30 for c in constraints)
save('manifest.json',manifest)
print(json.dumps(dict(oracle_tables=74,oracle_views=4,iceberg_tables=35,oracle_foreign_keys=212,oracle_indexes=202,row_predicates=sum(map(len,rows.values())))))
