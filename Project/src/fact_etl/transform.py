"""Business transformations. The reviewed mapping is compiled, never guessed.

The adapter is bounded to the local teaching dataset. All joins use validated
unique source indexes; dimensional attributes are always resolved as of event
time. Rejected source records and expanded grains are separate audit units.
"""
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
import re

H='hotel_ops'; E='entertainment_ops'
START=date(2024,1,1); END=date(2026,1,1)
AUDIT={'source_batch_id','transform_version','row_hash','created_at_utc','updated_at_utc'}

class Reject(ValueError):pass
def require(condition,reason):
    if not condition:raise Reject(reason)
def days(start,end):
    require(start is not None and end is not None and start<end,'INVALID_INTERVAL')
    require((end-start).days<4000,'EXPANSION_LIMIT')
    while start<end:
        yield start
        start+=timedelta(days=1)
def local_start(d):return datetime.combine(d,datetime.min.time())-timedelta(hours=7)
def datekey(d):return int(d.strftime('%Y%m%d'))

class Transformer:
    def __init__(self,sources,dimensions,design,mapping,source_quality):
        self.s=sources;self.d=dimensions;self.design={e['id']:e for e in design['tables']}
        self.mapping={e['id']:e for e in mapping['entities']};self.q=source_quality
        self.index={};self.di={};self.by_sk={};self.out={};self.bad=[];self.filtered=Counter()
        self.scope=[];self.programs={};self.current='';self.identity=None
        for name,rows in sources.items():
            # Primary keys are supplied by the actual source validation contract.
            contract=next(c for c in mapping['source_validation_contracts'] if c['source_table']==name)
            pk=contract['primary_key'];require(len(pk)==1,'UNSUPPORTED_COMPOSITE_SOURCE_PK')
            self.index[name]={r[pk[0]]:r for r in rows}
        for eid,rows in dimensions.items():
            self.by_sk[eid]={r[next(k for k in r if k==self.pk(eid))]:r for r in rows}
            if eid in ('D01','D10'):continue
            bk=self.design[eid]['business_key'];idx=defaultdict(list)
            for r in rows:
                if r['member_kind']=='NORMAL':idx[tuple(r[c] for c in bk)].append(r)
            self.di[eid]=idx
        self.blocked=set();self.rental_days=defaultdict(list);self.vehicle_maintenance=set();self.rental_conflicts=set()
        self.stays_by_br=defaultdict(list)
        for r in self.rows(H,'stays'):self.stays_by_br[r['booking_room_id']].append(r)
        self.prepare_operations()

    def pk(self,eid):
        return {'D01':'date_key','D02':'site_key','D03':'hotel_key','D04':'room_key','D05':'channel_key',
                'D06':'promotion_key','D07':'customer_profile_key','D08':'rate_plan_key','D09':'outlet_key',
                'D10':'meal_key','D11':'centre_key','D12':'activity_key','D13':'vehicle_key','D14':'supplier_key',
                'D15':'item_key','D16':'asset_key'}[eid]
    def rows(self,ns,name):return self.s.get(ns+'.'+name,[])
    def get(self,ns,name,key):
        r=self.index.get(ns+'.'+name,{}).get(key)
        require(r is not None,'MISSING_PARENT:'+ns+'.'+name+':'+str(key));return r
    def dim(self,eid,bk,t,namespace=None):
        ns=namespace or (E if eid in ('D11','D12','D13') else H)
        matches=[r for r in self.di[eid].get((ns,bk),[]) if r['valid_from_utc']<=t and (r['valid_to_utc'] is None or t<r['valid_to_utc'])]
        require(len(matches)==1,'SCD_ASOF:'+eid+':'+str(bk));return matches[0]
    def attr(self,eid,bk,t,col):return self.dim(eid,bk,t)[col]
    def complete(self,*names):
        require(all(self.q['source_status'].get(n)=='COMPLETE' for n in names),'UNKNOWN_OPERATIONAL_COVERAGE:'+','.join(names))
    def exclude(self,eid,identity,reason):self.bad.append(dict(entity=eid,grain=identity,reason=str(reason)))
    def prepare_operations(self):
        for r in self.rows(E,'vehicle_maintenance'):
            for d in days(r['starts_on'],r['ends_on']):self.vehicle_maintenance.add((r['vehicle_id'],d))
        for r in self.rows(E,'rentals'):
            if r['status']=='COMPLETED':
                for d in days(r['pickup_date'],r['return_date']):self.rental_days[(r['vehicle_id'],d)].append(r['rental_id'])
        for k,ids in self.rental_days.items():
            if len(ids)>1 or k in self.vehicle_maintenance:self.rental_conflicts.update(ids)

    def emit(self,eid,ctx,overrides=None):
        """Execute the approved column mapping; only explicit derived fields override it."""
        out={};overrides=overrides or {};self.current=eid
        env={k:SimpleNamespace(**v) if isinstance(v,dict) else v for k,v in ctx.items()}
        env.update(LOCAL_START=local_start,LOCAL_DATE=lambda t:(t+timedelta(hours=7)).date(),UTC=lambda t:t,
                   DIM_ATTR=self.attr,LOOKUP_MEAL=lambda m:{'BREAKFAST':1,'LUNCH':2,'DINNER':3,'BAR':4}[m])
        for c in self.mapping[eid]['columns']:
            name=c['target_column']
            if c['kind'] in ('AUDIT','SURROGATE_KEY'):continue
            if name in overrides:out[name]=overrides[name];continue
            ns=c.get('lookup_namespace',H);null=c.get('null_behavior','ERROR_REQUIRED')
            def lookup(dim,namespace,bk,t):
                if bk is None:
                    if '-> -1' in null:return -1
                    if '-> 0' in null:return 0
                    raise Reject('REQUIRED_DIMENSION:'+dim)
                return self.dim(dim,bk,t,namespace)[self.pk(dim)]
            def dk(d):
                if d is None:
                    if '-> -1' in null:return -1
                    if '-> 0' in null:return 0
                    raise Reject('REQUIRED_DATE')
                k=datekey(d);require(k in self.by_sk['D01'],'DATE_NOT_IN_DIMENSION');return k
            env.update(namespace=ns,LOOKUP_SCD=lookup,DATEKEY=dk);env.update(out)
            key=(eid,name)
            if key not in self.programs:
                expression=c['expression'].replace('$day','day')
                expression=re.sub(r'\b(D\d\d)\b',r"'\1'",expression)
                self.programs[key]=compile(expression,'mapping:'+eid+'.'+name,'eval')
            out[name]=eval(self.programs[key],{'__builtins__':{}},env)
        return out

    def attempt(self,eid,identity,fn):
        try:return fn()
        except (Reject,KeyError) as e:self.exclude(eid,identity,e);return None

    def referral(self,ref):
        if ref is None:return dict(cohort_departure_date_key=-1,booking_site_key=-1,referral_hotel_key=-1,booking_channel_key=-1)
        b=self.booking.get(ref);require(b is not None,'INVALID_BOOKING_REF:'+str(ref))
        return dict(cohort_departure_date_key=b['departure_date_key'],booking_site_key=b['site_key'],referral_hotel_key=b['hotel_key'],booking_channel_key=b['channel_key'])
    def room_contract(self,br,b,t):
        room=self.dim('D04',br['room_id'],t);rate=self.dim('D08',br['rate_plan_id'],t)
        require(room['hotel_id']==rate['hotel_id']==b['hotel_id'],'ROOM_RATE_HOTEL_MISMATCH')
        require(rate['channel_id']==b['channel_id'],'RATE_CHANNEL_MISMATCH')
        return room,rate

    def build(self,eid):
        rows=[]
        def add(identity,fn):
            row=self.attempt(eid,identity,fn)
            if row is not None:rows.append(row)
        if eid=='L04':
            for c in self.rows(E,'centres'):
                def make(c=c):
                    self.get(H,'sites',c['site_code'])
                    return self.emit(eid,{'c':c},dict(site_id=c['site_code']))
                add(c['centre_id'],make)
        elif eid=='L03':
            for name,kind,pk in [('ticket_orders','TICKET_ORDER','ticket_order_id'),('rentals','RENTAL','rental_id')]:
                for r in self.rows(E,name):
                    if r['hotel_booking_ref'] is None:self.filtered[eid]+=1;continue
                    add([kind,r[pk]],lambda r=r,kind=kind,pk=pk:self.emit(eid,{'b':self.get(H,'bookings',r['hotel_booking_ref'])},dict(service_type=kind,service_id=r[pk])))
        elif eid=='F01':
            for b in self.rows(H,'bookings'):add(b['booking_id'],lambda b=b:self.emit(eid,{'b':b}))
        elif eid=='L02':
            for m in self.rows(H,'maintenance'):
                for d in days(max(m['starts_on'],START),min(m['ends_on'],END)) if max(m['starts_on'],START)<min(m['ends_on'],END) else []:
                    def make(m=m,d=d):
                        room=self.attr('D16',m['asset_id'],local_start(d),'room_id')
                        if room is None:self.filtered[eid]+=1;return None
                        return self.emit(eid,dict(m=m,r={'room_id':room},day=d))
                    add([m['maintenance_id'],d],make)
        elif eid in ('F02','F10','F11'):
            spec={'F02':(H,'rooms','r','room_id'),'F10':(E,'activities','a','activity_id'),'F11':(E,'vehicles','v','vehicle_id')}[eid]
            ns,table,alias,pk=spec
            closed={(r['activity_id'],r['closed_on']) for r in self.rows(E,'closures')}
            for r in self.rows(ns,table):
                for d in days(START,END):
                    def make(r=r,d=d):
                        if eid=='F02':
                            self.complete(H+'.maintenance',H+'.assets')
                            require(not any(q['entity']=='L02' for q in self.bad),'UNKNOWN_MAINTENANCE_BRIDGE')
                            blocked=int((r[pk],datekey(d)) in self.blocked);values=dict(blocked_day=blocked)
                        elif eid=='F10':
                            self.complete(E+'.closures');values=dict(is_closed=int((r[pk],d) in closed),nominal_capacity=self.attr('D12',r[pk],local_start(d),'capacity_per_day'))
                        else:
                            self.complete(E+'.vehicle_maintenance',E+'.rentals')
                            n=len(self.rental_days.get((r[pk],d),[]));maintenance=int((r[pk],d) in self.vehicle_maintenance)
                            require(n<=1 and n<=1-maintenance,'VEHICLE_DAY_CONFLICT')
                            values=dict(maintenance_day=maintenance,rented_day=n)
                        return self.emit(eid,{alias:r,'day':d},values)
                    add([r[pk],d],make)
        elif eid in ('F04','F05'):
            rental=eid=='F05';table='rentals' if rental else 'ticket_orders';pk='rental_id' if rental else 'ticket_order_id';alias='r' if rental else 'o'
            for r in self.rows(E,table):
                def make(r=r):
                    if rental:require(r[pk] not in self.rental_conflicts,'RENTAL_OPERATION_CONFLICT')
                    return self.emit(eid,{alias:r},self.referral(r['hotel_booking_ref']))
                add(r[pk],make)
        elif eid in ('F08','F07'):
            table='meal_sessions' if eid=='F08' else 'dining_orders';pk='session_id' if eid=='F08' else 'dining_order_id';alias='s' if eid=='F08' else 'd'
            for r in self.rows(H,table):
                def make(r=r):
                    outlet=self.dim('D09',r['outlet_id'],local_start(r['service_date']))
                    override={}
                    if eid=='F08':require(outlet['outlet_type']=='RESTAURANT' and r['meal'] in ('BREAKFAST','DINNER'),'INVALID_BUFFET_SESSION')
                    else:
                        ref=r['booking_id'];require(ref is None or ref in self.booking,'INVALID_DINING_BOOKING')
                        override['booking_hotel_key']=-1 if ref is None else self.booking[ref]['hotel_key']
                    return self.emit(eid,{alias:r,'o':{'outlet_id':r['outlet_id']}},override)
                add(r[pk],make)
        elif eid in ('L01','F03','F06'):
            table={'L01':'booking_rooms','F03':'stays','F06':'breakfast_entitlements'}[eid]
            pk={'L01':'booking_room_id','F03':'stay_id','F06':'entitlement_id'}[eid]
            for r in self.rows(H,table):
                br=self.index[H+'.booking_rooms'].get(r['booking_room_id']);b=self.index[H+'.bookings'].get(br['booking_id']) if br else None
                if br is None or b is None:self.exclude(eid,r[pk],'SOURCE_PARENT');continue
                periods=list(days(r['checkin_date'],r['checkout_date'])) if eid=='F03' else [r['service_date'] if eid=='F06' else b['booked_on']]
                for d in periods:
                    def make(r=r,br=br,b=b,d=d):
                        require(b['booking_id'] in self.booking,'BOOKING_NOT_ACCEPTED')
                        room,rate=self.room_contract(br,b,local_start(d))
                        ctx=dict(br=br,b=b,r={'room_id':br['room_id']},day=d,s=r,e=r)
                        if eid!='L01':require(b['status']=='COMPLETED','STAY_WITHOUT_COMPLETED_BOOKING')
                        if eid=='F03':
                            require((br['room_id'],datekey(d)) in self.available,'ROOM_DAY_UNAVAILABLE_OR_MISSING')
                        if eid=='F06':
                            require(rate['breakfast_included']==1,'NO_INCLUDED_BREAKFAST')
                            matches=[s for s in self.stays_by_br[br['booking_room_id']] if s['checkin_date']<d<=s['checkout_date']]
                            require(len(matches)==1,'BREAKFAST_STAY_INTERVAL')
                            night=self.nights.get((br['room_id'],datekey(d-timedelta(days=1))))
                            require(night is not None and night['booking_room_id']==br['booking_room_id'],'MISSING_PRECEDING_STAY_NIGHT')
                            outlets=[o for o in self.d['D09'] if o['member_kind']=='NORMAL' and o['hotel_id']==b['hotel_id'] and o['outlet_type']=='RESTAURANT' and o['valid_from_utc']<=local_start(d) and (o['valid_to_utc'] is None or local_start(d)<o['valid_to_utc'])]
                            require(len(outlets)==1,'RESTAURANT_ASOF_NOT_UNIQUE');ctx['o']=outlets[0]
                        return self.emit(eid,ctx)
                    add([r[pk],d],make)
        elif eid=='F09':
            for a in self.rows(E,'admissions'):
                def make(a=a):
                    t=self.get(E,'tickets',a['ticket_id']);o=self.get(E,'ticket_orders',t['ticket_order_id'])
                    require(o['ticket_order_id'] in self.orders,'ORDER_NOT_ACCEPTED')
                    require(self.attr('D12',t['activity_id'],a['entered_at'],'centre_id')==o['centre_id'],'ACTIVITY_ORDER_CENTRE_MISMATCH')
                    return self.emit(eid,dict(a=a,t=t,o=o))
                add(a['admission_id'],make)
            groups=defaultdict(list)
            for r in rows:groups[(r['activity_key'],r['admission_date_key'])].append(r)
            rows=[]
            for key,group in groups.items():
                cap=self.capacity.get(key)
                if cap is None or len(group)>cap:
                    for r in group:self.exclude(eid,r['admission_id'],'ADMISSION_CAPACITY_CONFLICT')
                else:rows.extend(group)
        elif eid in ('F12','F13','F14'):
            table={'F12':'purchase_lines','F13':'receipts','F14':'stock_movements'}[eid];pk={'F12':'purchase_line_id','F13':'receipt_id','F14':'movement_id'}[eid]
            for r in self.rows(H,table):
                def make(r=r):
                    receipt=r if eid=='F13' else self.get(H,'receipts',r['receipt_id']) if eid=='F14' else None
                    line=r if eid=='F12' else self.get(H,'purchase_lines',receipt['purchase_line_id'])
                    po=self.get(H,'purchase_orders',line['purchase_order_id']);over={}
                    if eid!='F12':require(line['purchase_line_id'] in self.purchases,'PURCHASE_LINE_NOT_ACCEPTED')
                    if eid=='F13':over['late_accepted_qty']=r['accepted_qty'] if r['received_on']>po['expected_on'] else Decimal('0.000')
                    if eid=='F14':
                        require(receipt['receipt_id'] in self.receipts,'RECEIPT_NOT_ACCEPTED')
                        require(r['hotel_id']==po['hotel_id'] and r['item_id']==line['item_id'],'STOCK_LOT_MISMATCH')
                        require(r['movement_date']>=receipt['received_on'],'STOCK_BEFORE_RECEIPT')
                        if r['session_id'] is not None:
                            session=self.get(H,'meal_sessions',r['session_id'])
                            require(session['service_date']==r['movement_date'] and self.attr('D09',session['outlet_id'],local_start(r['movement_date']),'hotel_id')==r['hotel_id'],'MOVEMENT_SESSION_MISMATCH')
                        qty=r['quantity'];kind=r['movement_type'];over=dict(signed_qty=qty if kind=='IN' else -qty,in_qty=qty if kind=='IN' else Decimal('0.000'),use_qty=qty if kind=='USE' else Decimal('0.000'),waste_qty=qty if kind=='WASTE' else Decimal('0.000'),movement_value_vnd=qty*line['unit_price_vnd'])
                    return self.emit(eid,dict(l=line,p=po,r=receipt,m=r),over)
                add(r[pk],make)
        elif eid=='F16':
            for m in self.rows(H,'maintenance'):add(m['maintenance_id'],lambda m=m:self.emit(eid,{'m':m}))
        elif eid=='F17':
            for w in self.rows(H,'weather_daily'):add(w['weather_id'],lambda w=w:self.emit(eid,{'w':w}))
        else:raise ValueError('Unimplemented entity '+eid)
        # Every duplicate member is quarantined, never keep an arbitrary winner.
        for uk in self.mapping[eid]['unique_keys']:
            counts=Counter(tuple(r[c] for c in uk) for r in rows);kept=[]
            for r in rows:
                key=tuple(r[c] for c in uk)
                if counts[key]>1:self.exclude(eid,key,'DUPLICATE_TARGET_GRAIN')
                else:kept.append(r)
            rows=kept
        if eid=='F14':
            # Daily source grain cannot identify intraday order. Reject the whole
            # negative day and its dependent suffix, never sort movement IDs.
            groups=defaultdict(lambda:defaultdict(list))
            for r in rows:groups[r['receipt_id']][r['movement_date_key']].append(r)
            kept=[]
            for lot,events in groups.items():
                balance=Decimal(0);invalid_from=None
                for day,group in sorted(events.items()):
                    balance+=sum((r['signed_qty'] for r in group),Decimal(0))
                    if balance<0 and invalid_from is None:
                        invalid_from=day;self.scope.append(dict(entity='F14',receipt_id=lot,from_date=day,reason='NEGATIVE_DAILY_LOT_PREFIX',balance_status='UNAVAILABLE'))
                    if invalid_from is None:kept.extend(group)
                    else:
                        for r in group:self.exclude(eid,r['movement_id'],'LOT_BALANCE_DEPENDENCY_SUFFIX')
            rows=kept
            # Other rejected movements make later balances unknown, even when
            # the remaining accepted arithmetic happens to be positive.
            for q in self.bad:
                if q['entity']!=eid:continue
                mid=q['grain'] if isinstance(q['grain'],str) else None
                raw=self.index[H+'.stock_movements'].get(mid)
                if raw:self.scope.append(dict(entity=eid,receipt_id=raw['receipt_id'],from_date=datekey(raw['movement_date']),reason=q['reason'],balance_status='UNAVAILABLE'))
            for q in self.q.get('quarantine',[]):
                if q['source']==H+'.stock_movements':
                    self.scope.append(dict(entity=eid,receipt_id=q.get('payload',{}).get('receipt_id'),reason='SOURCE_MOVEMENT_REJECTED',balance_status='UNAVAILABLE'))
        self.out[eid]=rows
        return rows

    def accept(self,eid,rows):
        """Only post-validation accepted rows may become another fact's parent."""
        self.out[eid]=rows
        if eid=='F01':self.booking={r['booking_id']:r for r in rows}
        if eid=='L02':self.blocked={(r['room_id'],r['date_key']) for r in rows}
        if eid=='F02':self.available={(r['room_id'],r['date_key']) for r in rows if r['available_day']==1}
        if eid=='F03':self.nights={(r['room_id'],r['service_date_key']):r for r in rows}
        if eid=='F04':self.orders={r['ticket_order_id']:r for r in rows}
        if eid=='F10':self.capacity={(r['activity_key'],r['date_key']):r['available_capacity'] for r in rows}
        if eid=='F12':self.purchases={r['purchase_line_id'] for r in rows}
        if eid=='F13':self.receipts={r['receipt_id'] for r in rows}
