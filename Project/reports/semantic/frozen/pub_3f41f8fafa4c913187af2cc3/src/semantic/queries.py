"""Portable aggregate SQL for the frozen 47 KPI contract.

Identifiers come from code; values are validated literals, never user SQL.
Every dimension lookup uses the fact's version key, not is_current.
"""
from datetime import date
import re

VERSION='companye-semantic-1.0'
COUNTS={'B01':5,'B02':6,'B03':5,'B04':8,'B05':6,'B06':7,'B07':6,'B08':4}
IDS=[f'{g}.{n:02}' for g,count in COUNTS.items() for n in range(1,count+1)]
HOTEL={'site','hotel','stars'}
ALLOWED={}
for mid in IDS:
    g,n=mid.split('.');n=int(n)
    if g=='B01': a=HOTEL|{'room_type'}|({'channel'} if n in (1,4,5) else set())
    elif g=='B02': a=HOTEL|{'channel','promotion'}
    elif g=='B03': a=HOTEL|{'channel'}
    elif g=='B04': a=HOTEL|{'outlet','meal'}
    elif g=='B05': a={'site','centre','severe_weather'}|({'activity','outdoor'} if n<=3 else {'vehicle_type'})
    elif g=='B06': a=HOTEL|{'supplier','item'}
    elif g=='B07': a=HOTEL|{'supplier','item'}|({'usage_area'} if n==3 else set())
    else: a=HOTEL|({'asset_type','work_type'} if n==1 else {'room_type'})
    ALLOWED[mid]=a

DOMAINS={
 'site':('D02','site_id'),'hotel':('D03','hotel_id'),'stars':('D03','stars'),
 'room_type':('D04','room_type'),'channel':('D05','channel_code'),'promotion':('D06','promotion_id'),
 'outlet':('D09','outlet_id'),'meal':('D10','meal_code'),'centre':('D11','centre_id'),
 'activity':('D12','activity_id'),'outdoor':('D12','outdoor'),'vehicle_type':('D13','vehicle_type'),
 'supplier':('D14','supplier_id'),'item':('D15','item_id'),'asset_type':('D16','asset_type')}

def literal(value):
    if isinstance(value,int) and not isinstance(value,bool): return str(value)
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9 _./-]{1,80}',value):
        raise ValueError('Unsupported filter literal')
    return "'"+value+"'"

def validate(group,ctx,metrics=None):
    if group not in COUNTS: raise ValueError('Unknown KPI group')
    selected=metrics or [m for m in IDS if m.startswith(group+'.')]
    if not selected or len(set(selected))!=len(selected) or any(m not in IDS or not m.startswith(group+'.') for m in selected): raise ValueError('Invalid metric selection')
    s=date.fromisoformat(ctx.get('start','2024-01-01'));e=date.fromisoformat(ctx.get('end','2026-01-01'))
    if s>=e: raise ValueError('Expected half-open start < end')
    a=date.fromisoformat(ctx.get('assessment','2025-12-31'))
    if set(ctx)-{'start','end','assessment','filters'}: raise ValueError('Unknown context fields')
    filters=ctx.get('filters',{})
    for mid in selected:
        if set(filters)-ALLOWED[mid]: raise ValueError('Incompatible filters for '+mid+': '+str(sorted(set(filters)-ALLOWED[mid])))
    for k,v in filters.items():
        literal(v)
        if k in ('stars','outdoor','severe_weather') and (type(v)!=int or v not in ((3,5) if k=='stars' else (0,1))): raise ValueError('Invalid numeric category')
    return selected,int(s.strftime('%Y%m%d')),int(e.strftime('%Y%m%d')),int(a.strftime('%Y%m%d'))

def where(eid,day,ctx,start,end,alias='f'):
    f=ctx.get('filters',{});parts=[f'{alias}.{day}>={start}',f'{alias}.{day}<{end}']
    site='service_site_key' if eid in ('F04','F05') else 'site_key'
    hotel='service_hotel_key' if eid=='F07' else 'hotel_key'
    cols={'site':('D02','site_key',site,'site_id')}
    if eid not in ('F04','F05','F09','F10','F11'):
        cols.update(hotel=('D03','hotel_key',hotel,'hotel_id'),stars=('D03','hotel_key',hotel,'stars'))
    if eid in ('F02','F03'): cols['room_type']=('D04','room_key','room_key','room_type')
    if eid in ('F01','F03'): cols['channel']=('D05','channel_key','channel_key','channel_code')
    if eid=='F01': cols['promotion']=('D06','promotion_key','promotion_key','promotion_id')
    if eid in ('F06','F07','F08'):
        cols.update(outlet=('D09','outlet_key','outlet_key','outlet_id'),meal=('D10','meal_key','meal_key','meal_code'))
    if eid in ('F09','F10','F11'): cols['centre']=('D11','centre_key','centre_key','centre_id')
    if eid in ('F09','F10'): cols.update(activity=('D12','activity_key','activity_key','activity_id'),outdoor=('D12','activity_key','activity_key','outdoor'))
    if eid=='F11': cols['vehicle_type']=('D13','vehicle_key','vehicle_key','vehicle_type')
    if eid in ('F12','F13','F14'): cols.update(supplier=('D14','supplier_key','supplier_key','supplier_id'),item=('D15','item_key','item_key','item_id'))
    if eid=='F16': cols['asset_type']=('D16','asset_key','asset_key','asset_type')
    for key,(dim,pk,fk,col) in cols.items():
        if key in f: parts.append(f'EXISTS (SELECT 1 FROM {{{dim}}} d WHERE d.{pk}={alias}.{fk} AND d.{col}={literal(f[key])})')
    if eid=='F01' and 'room_type' in f:
        parts.append(f"EXISTS (SELECT 1 FROM {{L01}} l JOIN {{D04}} d ON d.room_key=l.room_key WHERE l.source_system={alias}.source_system AND l.booking_id={alias}.booking_id AND d.room_type={literal(f['room_type'])})")
    if eid=='F16' and 'work_type' in f:parts.append(f"{alias}.work_type={literal(f['work_type'])}")
    if eid=='F14' and 'usage_area' in f:parts.append(f"{alias}.usage_area={literal(f['usage_area'])}")
    if eid in ('F09','F10','F11') and 'severe_weather' in f:
        parts.append(f"EXISTS (SELECT 1 FROM {{F17}} w WHERE w.site_key={alias}.{site} AND w.weather_date_key={alias}.{day} AND w.severe_weather={literal(f['severe_weather'])})")
    return ' AND '.join(parts)

def build(group,ctx,metrics=None):
    selected,s,e,a=validate(group,ctx,metrics);ctes=[];expressions={}
    def agg(name,eid,day,columns,extra='',start=s,end=e):
        cols=', '.join('COALESCE(SUM('+expr+'),0) '+key for key,expr in columns.items())
        ctes.append(name+' AS (SELECT '+cols+' FROM {'+eid+'} f WHERE '+where(eid,day,ctx,start,end)+extra+')')
    def metric(n,num,den=None):expressions[f'{group}.{n:02}']=(num,den)
    if group=='B01':
        agg('stay','F03','service_date_key',{'occupied':'occupied_night'})
        agg('roomday','F02','date_key',{'available':'available_day'})
        agg('booking','F01','arrival_date_key',{'bookings':'1','cancelled':"CASE WHEN status='CANCELLED' THEN 1 ELSE 0 END",'noshow':"CASE WHEN status='NO_SHOW' THEN 1 ELSE 0 END"})
        source='stay CROSS JOIN roomday CROSS JOIN booking'
        for n,v,d in [(1,'occupied',None),(2,'available',None),(3,'occupied','available'),(4,'cancelled','bookings'),(5,'noshow','bookings')]:metric(n,v,d)
    elif group=='B02':
        names=['gross_vnd','customer_due_vnd','company_share_vnd','partner_share_vnd','commission_vnd']
        agg('booking','F01','departure_date_key',{v:v for v in names}," AND status='COMPLETED'");source='booking'
        for n,v in enumerate(names,1):metric(n,v)
        metric(6,'gross_vnd-company_share_vnd-commission_vnd')
    elif group=='B03':
        ctes.append('cohort AS (SELECT f.source_system,f.booking_id,f.customer_due_vnd FROM {F01} f WHERE '+where('F01','departure_date_key',ctx,s,e)+" AND f.status='COMPLETED')")
        # L03 supplies explicit source-aware identities; aggregate each child before join.
        ctes.append("tickets AS (SELECT l.booking_source_system,l.booking_id,SUM(t.net_ticket_vnd) ticket_value,MAX(CASE WHEN t.net_ticket_vnd>0 THEN 1 ELSE 0 END) bought_ticket FROM {F04} t JOIN {L03} l ON l.service_source_system=t.source_system AND l.service_id=t.ticket_order_id AND l.service_type='TICKET_ORDER' GROUP BY l.booking_source_system,l.booking_id)")
        ctes.append("rentals AS (SELECT l.booking_source_system,l.booking_id,SUM(r.agreed_vnd) rental_value,MAX(CASE WHEN r.agreed_vnd>0 THEN 1 ELSE 0 END) bought_rental FROM {F05} r JOIN {L03} l ON l.service_source_system=r.source_system AND l.service_id=r.rental_id AND l.service_type='RENTAL' WHERE r.status='COMPLETED' GROUP BY l.booking_source_system,l.booking_id)")
        ctes.append('cohort_total AS (SELECT COUNT(*) cohort_count,COALESCE(SUM(CASE WHEN COALESCE(t.bought_ticket,0)=1 OR COALESCE(r.bought_rental,0)=1 THEN 1 ELSE 0 END),0) bought,COALESCE(SUM(t.ticket_value),0) ticket_value,COALESCE(SUM(r.rental_value),0) rental_value,COALESCE(SUM(c.customer_due_vnd),0) room_value FROM cohort c LEFT JOIN tickets t ON t.booking_source_system=c.source_system AND t.booking_id=c.booking_id LEFT JOIN rentals r ON r.booking_source_system=c.source_system AND r.booking_id=c.booking_id)')
        source='cohort_total'
        for n,v,d in [(1,'bought',None),(2,'bought','cohort_count'),(3,'ticket_value',None),(4,'rental_value',None),(5,'room_value+ticket_value+rental_value',None)]:metric(n,v,d)
    elif group=='B04':
        agg('ent','F06','service_date_key',{'eligible':'eligible_covers','redeemed':'redeemed_covers'})
        agg('dining','F07','service_date_key',{'net':'net_vnd','covers':'covers','ratings':'rating_sum','rated':'rating_count'})
        agg('session_total','F08','service_date_key',{'cost':'ingredient_cost_vnd','actual':'actual_covers'}," AND EXISTS (SELECT 1 FROM {D10} m WHERE m.meal_key=f.meal_key AND m.meal_code IN ('BREAKFAST','DINNER'))")
        source='ent CROSS JOIN dining CROSS JOIN session_total'
        for n,v,d in [(1,'eligible',None),(2,'redeemed',None),(3,'redeemed','eligible'),(4,'net',None),(5,'covers+redeemed',None),(6,'cost',None),(7,'cost','actual'),(8,'ratings','rated')]:metric(n,v,d)
    elif group=='B05':
        agg('adm','F09','admission_date_key',{'admissions':'admission_count'})
        agg('act','F10','date_key',{'capacity':'available_capacity'})
        agg('vehicle','F11','date_key',{'rented':'rented_day','ready':'available_day'})
        source='adm CROSS JOIN act CROSS JOIN vehicle'
        for n,v,d in [(1,'admissions',None),(2,'capacity',None),(3,'admissions','capacity'),(4,'rented',None),(5,'ready',None),(6,'rented','ready')]:metric(n,v,d)
    elif group=='B06':
        ctes.append('due AS (SELECT f.source_system,f.purchase_line_id,f.ordered_qty FROM {F12} f WHERE '+where('F12','expected_date_key',ctx,s,e)+f' AND f.expected_date_key<={a})')
        ctes.append(f"received AS (SELECT source_system,purchase_line_id,SUM(accepted_qty) accepted,SUM(rejected_qty) rejected,SUM(late_accepted_qty) late,SUM(CASE WHEN received_date_key<=expected_date_key THEN accepted_qty ELSE 0 END) ontime FROM {{F13}} WHERE received_date_key<={a} GROUP BY source_system,purchase_line_id)")
        ctes.append('purchase_total AS (SELECT COALESCE(SUM(d.ordered_qty),0) ordered,COALESCE(SUM(r.accepted),0) accepted,COALESCE(SUM(r.rejected),0) rejected,COALESCE(SUM(r.late),0) late,COALESCE(SUM(CASE WHEN COALESCE(r.ontime,0)>=d.ordered_qty THEN 1 ELSE 0 END),0) otif,COUNT(*) lines FROM due d LEFT JOIN received r ON r.source_system=d.source_system AND r.purchase_line_id=d.purchase_line_id)')
        source='purchase_total'
        for n,v,d in [(1,'ordered',None),(2,'accepted',None),(3,'rejected',None),(4,'late',None),(5,'accepted','ordered'),(6,'rejected','accepted+rejected'),(7,'otif','lines')]:metric(n,v,d)
    elif group=='B07':
        agg('stock','F14','movement_date_key',{
            'opening':f'CASE WHEN movement_date_key<{s} THEN signed_qty ELSE 0 END','closing':'signed_qty',
            'used':f'CASE WHEN movement_date_key>={s} THEN use_qty ELSE 0 END',
            'wasted':f'CASE WHEN movement_date_key>={s} THEN waste_qty ELSE 0 END',
            'waste_value':f'CASE WHEN movement_date_key>={s} THEN waste_qty*unit_price_vnd ELSE 0 END',
            'available_value':f'CASE WHEN movement_date_key<{s} THEN signed_qty*unit_price_vnd ELSE in_qty*unit_price_vnd END'},start=1)
        source='stock'
        for n,v,d in [(1,'opening',None),(2,'closing',None),(3,'used',None),(4,'wasted',None),(5,'waste_value',None),(6,'waste_value','available_value')]:metric(n,v,d)
    else:
        agg('work','F16','end_date_key',{'cost':'cost_vnd'}," AND status='COMPLETED'")
        agg('roomday','F02','date_key',{'blocked':'blocked_day','available':'available_day','inventory':'inventory_day'})
        source='work CROSS JOIN roomday'
        for n,v,d in [(1,'cost',None),(2,'blocked',None),(3,'available',None),(4,'blocked','inventory')]:metric(n,v,d)
    columns=[]
    for mid in selected:
        num,den=expressions[mid];label=mid.lower().replace('.','_')
        columns.extend([f'({num}) {label}_n',f'({den or "1"}) {label}_d'])
        value=f'CAST(({num}) AS DECIMAL(28,12))/NULLIF(CAST(({den}) AS DECIMAL(28,12)),0)' if den else '('+num+')'
        columns.append(value+' '+label+'_value')
    return 'WITH '+',\n'.join(ctes)+'\nSELECT '+',\n'.join(columns)+' FROM '+source,selected,{mid:expressions[mid][1] is not None for mid in selected}
