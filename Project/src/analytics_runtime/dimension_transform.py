"""Frozen lake CSV -> validated dimension inputs. Bounded local driver adapter.

CSV is read from catalog-pinned lake files, never generator audit-only data.
Spark SQL validates source CHECKs; FK closure excludes dependent invalid rows.
This adapter deliberately rejects growth beyond 100,000 rows per input.
"""
import csv,hashlib,json,re
from collections import Counter
from datetime import date,datetime,timedelta,timezone
from decimal import Decimal,InvalidOperation
from pathlib import Path
from pyspark.sql import functions as F
from analytics_runtime.scd2 import canonical,payload_hash

BOOTSTRAP=datetime(2022,12,31,17)
LIMIT=100000

def parse(value,typ):
    if value in (None,'','\\N'):return None
    if typ in ('TEXT','STRING') or typ.startswith('VARCHAR'):return value
    if typ in ('INTEGER','INT','BIGINT'):
        d=Decimal(value)
        bound=2**31 if typ in ('INTEGER','INT') else 2**63
        if not d.is_finite() or d!=d.to_integral_value() or not -bound<=d<bound:raise ValueError('integer precision/range')
        return int(d)
    if typ.startswith(('NUMERIC','DECIMAL')):
        p,s=map(int,re.findall(r'\d+',typ));d=Decimal(value)
        if not d.is_finite() or d!=d.quantize(Decimal(1).scaleb(-s)) or abs(d)>=Decimal(10)**(p-s):raise ValueError('decimal precision/scale')
        return d.quantize(Decimal(1).scaleb(-s))
    if typ=='DATE':return date.fromisoformat(value)
    if typ=='TIMESTAMPTZ':
        # PostgreSQL COPY emits hour-only offsets (+07/+00), valid source values
        # that Python 3.8 fromisoformat does not accept until minutes are added.
        normalized=re.sub(r'([+-]\d{2})$',r'\1:00',value.replace('Z','+00:00'))
        d=datetime.fromisoformat(normalized)
        if d.tzinfo is None:raise ValueError('timezone required')
        return d.astimezone(timezone.utc).replace(tzinfo=None)
    raise ValueError('Unsupported type '+typ)

def sql_type(typ):
    if typ=='TEXT':return 'STRING'
    if typ=='INTEGER':return 'INT'
    if typ=='TIMESTAMPTZ':return 'TIMESTAMP_NTZ'
    return typ.replace('NUMERIC','DECIMAL')

def read_sources(spark,lake,catalog,mapping):
    required={v for e in mapping['entities'] if e['id'].startswith('D') for v in e['aliases'].values()}
    contracts={s['source_table']:s for s in mapping['source_validation_contracts']}
    # Follow parent requirements to avoid validating against rejected parent rows.
    for _ in range(len(contracts)):
        more={f['references'].rsplit('.',1)[0] for k in required for f in contracts[k]['foreign_keys']}
        if more<=required:break
        required|=more
    accepted={};quarantine=[];inputs=[];source_status={};years={2023};date_errors=[]
    for ds in catalog['datasets']:
        # External receipt files are inputs to procurement facts, not dimensions.
        if 'columns' not in ds:continue
        name=ds['dataset_id'];path=(lake/ds['relative_path']).resolve()
        if lake.resolve() not in path.parents:raise ValueError('Catalog path outside lake')
        if not path.exists():
            inputs.append(dict(dataset=name,status='MISSING',expected=ds['row_count']))
            source_status[name]='UNAVAILABLE';accepted[name]=[];continue
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if digest!=ds['sha256']:raise ValueError('Input checksum mismatch: '+name)
        records=[];count=0
        with path.open(encoding='utf-8',newline='') as f:
            reader=csv.DictReader(f)
            if reader.fieldnames!=[c['name'] for c in ds['columns']]:raise ValueError('Source header drift: '+name)
            for raw in reader:
                count+=1
                for c in ds['columns']:
                    if c['sql_type'] in ('DATE','TIMESTAMPTZ') and raw[c['name']] not in ('','\\N'):
                        try:
                            d=parse(raw[c['name']],c['sql_type'])
                            if isinstance(d,datetime):d=d+timedelta(hours=7)
                            years.add(d.year)
                        except (ValueError,InvalidOperation):date_errors.append(dict(dataset=name,line=count+1,column=c['name']))
                if name not in required:continue
                if count>LIMIT:raise ValueError('Local dimension input limit exceeded: '+name)
                try:
                    row={c['name']:parse(raw[c['name']],c['sql_type']) for c in ds['columns']}
                    for c in ds['columns']:
                        if not c['nullable'] and (row[c['name']] is None or isinstance(row[c['name']],str) and not row[c['name']].strip()):raise ValueError('Required field '+c['name'])
                    records.append(row)
                except (ValueError,InvalidOperation) as e:
                    quarantine.append(dict(source=name,line=count+1,code='PARSE_OR_REQUIRED',reason=str(e),payload=raw))
        if count!=ds['row_count']:raise ValueError('Source row count mismatch: '+name)
        inputs.append(dict(dataset=name,status='VERIFIED',sha256=digest,rows=count))
        source_status[name]='COMPLETE'
        if name not in required:continue
        contract=contracts[name]
        for key in [contract['primary_key']]+contract['additional_unique_keys']:
            counts=Counter(tuple(r[c] for c in key) for r in records if all(r[c] is not None for c in key))
            kept=[]
            for row in records:
                if counts.get(tuple(row[c] for c in key),0)>1:
                    quarantine.append(dict(source=name,code='DUPLICATE_KEY',key=key,payload=row))
                else:kept.append(row)
            records=kept
        if records and contract['declared_checks']:
            schema=', '.join('`'+c['name']+'` '+sql_type(c['sql_type']) for c in ds['columns'])
            df=spark.createDataFrame([tuple(r[c['name']] for c in ds['columns']) for r in records],schema)
            bad=F.lit(False)
            for check in contract['declared_checks']:bad=bad|(~F.coalesce(F.expr(check),F.lit(True)))
            tagged=df.withColumn('_bad',bad).collect();records=[]
            for r in tagged:
                row=r.asDict();flag=row.pop('_bad')
                if flag:quarantine.append(dict(source=name,code='SOURCE_CHECK',payload=row))
                else:records.append(row)
        accepted[name]=records
    # Iterate to fixed point for transitive invalid parent references.
    for _ in range(len(required)+1):
        removed=0
        for name in sorted(required):
            rows=accepted.get(name,[]);kept=[]
            parents={}
            for fk in contracts[name]['foreign_keys']:
                table,column=fk['references'].rsplit('.',1)
                parents[fk['column']]=Counter(r[column] for r in accepted.get(table,[]))
            for r in rows:
                invalid=[fk['column'] for fk in contracts[name]['foreign_keys'] if
                         not (r[fk['column']] is None and fk['optional_null']) and parents[fk['column']][r[fk['column']]]!=1]
                if invalid:
                    removed+=1;quarantine.append(dict(source=name,code='DEPENDENCY_EXCLUDED',columns=invalid,payload=r))
                else:kept.append(r)
            accepted[name]=kept
        if not removed:break
    for q in quarantine:
        if source_status.get(q['source'])!='UNAVAILABLE':source_status[q['source']]='PARTIAL'
    return accepted,dict(inputs=inputs,source_status=source_status,quarantine=quarantine,
                         calendar_start=f'{min(years)}-01-01',calendar_end=f'{max(years)}-12-31',date_errors=date_errors)

def dimension_inputs(entity,design,mapping,sources,source_report):
    eid=entity['id'];rows=[]
    def member(namespace,**attrs):rows.append(dict(source_system=namespace,member_kind='NORMAL',**attrs))
    if eid=='D01':
        d=date.fromisoformat(source_report['calendar_start']);end=date.fromisoformat(source_report['calendar_end'])
        while d<=end:
            member('calendar',date_key=int(d.strftime('%Y%m%d')),calendar_date=d,day=d.day,
                   day_of_week=d.isoweekday(),month=d.month,quarter=(d.month-1)//3+1,year=d.year)
            d+=timedelta(days=1)
    elif eid=='D10':
        for key,code,name in [(1,'BREAKFAST','Bữa sáng'),(2,'LUNCH','Bữa trưa'),(3,'DINNER','Bữa tối'),(4,'BAR','Bar')]:
            member('reference',meal_key=key,meal_code=code,meal_name=name)
    elif eid=='D05':
        for r in sources.get('hotel_ops.channels',[]):
            member('hotel_ops',channel_code=r['channel_id'],channel_name=r['channel_name'],channel_type=r['channel_type'],commission_bps=r['commission_bps'])
        for code in sorted({r['sales_channel'] for r in sources.get('entertainment_ops.ticket_orders',[])}):
            if code not in ('GATE','HOTEL_RECEPTION'):raise ValueError('Unapproved entertainment sales channel')
            member('entertainment_ops',channel_code=code,channel_name=code,channel_type='ENTERTAINMENT_SALES',commission_bps=None)
    elif eid=='D07':
        for ns,table,key in [('hotel_ops','guests','guest_id'),('entertainment_ops','customers','customer_id')]:
            for r in sources.get(ns+'.'+table,[]):
                member(ns,source_customer_id=r[key],full_name=r['full_name'],phone=r['phone'],email=r['email'],member_card_ref=r.get('member_card_ref'))
    else:
        table=mapping['aliases']['s'];namespace=table.split('.')[0]
        cols={c['target_column']:c['expression'][2:] for c in mapping['columns'] if c['expression'].startswith('s.')}
        for r in sources.get(table,[]):member(namespace,**{dest:r[src] for dest,src in cols.items()})
    kept=[];bad=[]
    for r in rows:
        errors=[]
        for c in entity['columns']:
            if c['name'] not in r:continue
            value=r[c['name']]
            if value is not None and c['spark_sql_type'].startswith('DECIMAL'):
                value=parse(str(value),c['spark_sql_type']);r[c['name']]=value
            if c['required_for_normal_member'] and (value is None or isinstance(value,str) and not value.strip()):errors.append(c['name']+':required')
            if isinstance(value,str) and c['oracle_type'].startswith('VARCHAR2') and len(value)>int(re.search(r'\d+',c['oracle_type'][8:]).group()):errors.append(c['name']+':length')
        if errors:bad.append(dict(entity=eid,code='TARGET_DOMAIN',reason=errors,payload=r))
        else:kept.append(r)
    return kept,bad
