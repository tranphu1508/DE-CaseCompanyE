"""Semantic responses attach quality and publication identity to exact components."""
from decimal import Decimal, localcontext
from semantic.queries import build,validate,DOMAINS,VERSION

def policy(mid,ctx,manifest):
    reasons=[];status='COMPLETE';n=int(mid[-2:]);g=mid[:3];filters=ctx.get('filters',{})
    s=ctx.get('start','2024-01-01');e=ctx.get('end','2026-01-01');a=ctx.get('assessment','2025-12-31')
    if s<'2024-01-01' or e>'2026-01-01' or (g=='B06' and (a<'2024-01-01' or a>'2025-12-31')):
        return 'UNAVAILABLE',['OUTSIDE_VERIFIED_V2_COVERAGE']
    if (g=='B06' and n<=6 or g=='B07' and n<=4) and 'item' not in filters:
        return 'NOT_APPLICABLE',['SELECT_ONE_ITEM_FOR_COMPATIBLE_QUANTITY']
    if g=='B04' and 'meal' in filters:
        if (n<=3 and filters['meal']!='BREAKFAST') or (n in (6,7) and filters['meal'] not in ('BREAKFAST','DINNER')):
            return 'NOT_APPLICABLE',['MEAL_OUTSIDE_METRIC_SCOPE']
    q=manifest['quality_metrics'].get(mid)
    if q is None:return 'UNAVAILABLE',['MISSING_METRIC_QUALITY']
    deps=set(q.get('dependencies',[]))
    if 'severe_weather' in filters:deps.add('F17')
    # A filter depends on its dimension; unknown/missing metadata never means complete.
    deps.update(DOMAINS[k][0] for k in filters if k in DOMAINS)
    if g=='B03':deps.add('L03')
    statuses=[q['status']]+[manifest['quality_entities'].get(d,{'status':'UNAVAILABLE'})['status'] for d in deps]
    if 'UNAVAILABLE' in statuses:status='UNAVAILABLE'
    elif any(v!='COMPLETE' for v in statuses):status='PARTIAL'
    if status!='COMPLETE':reasons.append('DEPENDENCY_QUALITY_'+status+'_CONSERVATIVE_BATCH_SCOPE')
    if g=='B07':
        for issue in manifest.get('quality_scope',[]):
            boundary=s if n==1 else e
            if issue.get('entity')=='F14' and issue.get('from_date','0000')<boundary:
                # Published scope currently lacks hotel/item identifiers. Cannot prove disjointness.
                status='UNAVAILABLE' if n in (1,2,6) else ('UNAVAILABLE' if status=='UNAVAILABLE' else 'PARTIAL')
                reasons.append('LOT_HISTORY_UNRELIABLE_CONSERVATIVE_SCOPE');break
    return status,reasons

def decode(rows,selected,ratios,ctx,manifest):
    assert len(rows)==1 and len(rows[0])==3*len(selected)
    out={}
    for index,mid in enumerate(selected):
        raw=rows[0][3*index:3*index+3]
        num,den,sql_value=[None if x is None else Decimal(str(x)) for x in raw]
        assert num is not None and den is not None
        with localcontext() as dc:
            dc.prec=50;value=num/den if ratios[mid] and den!=0 else None if ratios[mid] else num
        if value is None:assert sql_value is None
        else:assert sql_value is not None and abs(sql_value-value)<=Decimal('0.000000001'),(mid,sql_value,value)
        status,reasons=policy(mid,ctx,manifest)
        if den==0 and ratios[mid]:reasons.append('ZERO_DENOMINATOR')
        if mid=='B04.07' and den==0 and num>0:reasons.append('BUFFET_COST_WITHOUT_COVERS')
        suppressed=status in ('UNAVAILABLE','NOT_APPLICABLE')
        out[mid]=dict(numerator=None if suppressed else num,denominator=None if suppressed else den,
                      value=None if suppressed else value,quality=status,reasons=reasons,
                      diagnostic_accepted_numerator=num,diagnostic_accepted_denominator=den)
    return out

class SemanticSession:
    def __init__(self,reader):self.reader=reader;self.domain_cache={}
    def query(self,group,ctx,engine,metrics=None):
        validate(group,ctx,metrics)
        for key,value in ctx.get('filters',{}).items():
            if key in DOMAINS:
                eid,col=DOMAINS[key]
                if key not in self.domain_cache:
                    result=self.reader.query('SELECT DISTINCT '+col+' FROM {'+eid+'} WHERE member_kind=\'NORMAL\'',engine)
                    self.domain_cache[key]={str(r[0]) for r in result['rows'] if r[0] is not None}
                if str(value) not in self.domain_cache[key]:raise ValueError('Unknown filter member: '+key+'='+str(value))
            elif key=='work_type' and value not in ('PLANNED','BREAKDOWN'):raise ValueError('Unknown work type')
            elif key=='usage_area' and value not in ('WAREHOUSE','BUFFET','HOUSEKEEPING','KITCHEN_OTHER'):raise ValueError('Unknown usage area')
        sql,selected,ratios=build(group,ctx,metrics)
        result=self.reader.query(sql,engine)
        return dict(publication_id=self.reader.pid,source_batch_id=self.reader.manifest['source_batch_id'],
                    contract_version='companye-kpi-1.0',semantic_version=VERSION,engine=engine,context=ctx,
                    metrics=decode(result['rows'],selected,ratios,ctx,self.reader.manifest),
                    external_reconciliation_warnings=len(self.reader.manifest.get('external_warnings',[])))
