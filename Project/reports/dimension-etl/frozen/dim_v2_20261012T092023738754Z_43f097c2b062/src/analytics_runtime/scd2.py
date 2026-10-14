"""Engine-independent SCD2 timeline reducer. No clock, IO or source mutation.

Events are retained even when they are no-ops today: an out-of-order event can
make an earlier no-op a meaningful future boundary. Equal-time conflicts are
rejected, never resolved by ingestion order. All times are naive UTC instants.
"""
from datetime import date,datetime
from decimal import Decimal
import hashlib,json

def scalar(value):
    if isinstance(value,datetime):return value.isoformat(timespec='microseconds')+'Z'
    if isinstance(value,date):return value.isoformat()
    if isinstance(value,Decimal):return format(value,'f')
    return value

def canonical(value):
    return json.dumps(value,ensure_ascii=False,separators=(',',':'),default=scalar,allow_nan=False)

def payload_hash(row,columns):
    return hashlib.sha256(canonical([row.get(c) for c in columns]).encode()).hexdigest()

class EffectiveConflict(ValueError):pass

def timeline(events):
    by_time={}
    for event in events:
        t=event['effective_at']
        if t.tzinfo is not None:raise ValueError('Use normalized naive UTC')
        if t in by_time and event['row_hash']!=by_time[t]['row_hash']:
            raise EffectiveConflict('Conflicting payloads at the same effective timestamp')
        by_time.setdefault(t,event)
    changes=[]
    for t,e in sorted(by_time.items()):
        if not changes or changes[-1]['row_hash']!=e['row_hash']:
            changes.append(dict(e,valid_from_utc=t))
    for i,row in enumerate(changes):
        row['valid_to_utc']=changes[i+1]['valid_from_utc'] if i+1<len(changes) else None
        row['is_current']=int(i==len(changes)-1);row['version_no']=i+1
    return changes

def lookup(rows,t):
    matches=[r for r in rows if r['valid_from_utc']<=t and (r['valid_to_utc'] is None or t<r['valid_to_utc'])]
    if len(matches)!=1:raise ValueError('SCD lookup requires exactly one interval')
    return matches[0]

def materialize(events,existing,key_for,pk,now):
    """Assign durable BK+effective-time keys; preserve audit columns on no-op."""
    previous={r['valid_from_utc']:r for r in existing};result=[]
    for e in timeline(events):
        r=dict(e['payload']);r.update({k:e[k] for k in ['valid_from_utc','valid_to_utc','is_current','version_no']})
        r.update(row_hash=e['row_hash'],effective_time_basis=e['basis'],source_batch_id=e['batch'],
                 transform_version=e['transform'],created_at_utc=now,updated_at_utc=now)
        r[pk]=key_for(e['valid_from_utc'])
        old=previous.get(e['valid_from_utc'])
        if old:
            r['created_at_utc']=old['created_at_utc']
            if all(r[k]==old[k] for k in ['row_hash','valid_to_utc','is_current','version_no']):
                r=dict(old)
        result.append(r)
    return result
