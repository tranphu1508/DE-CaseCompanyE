"""Independent raw CSV calculator: no fact transformer or SQL/formula imports.

Only for accepted complete v2 data. Synthetic truth/audit_only never loaded.
Reconstructs intervals and joins from operational keys, not warehouse measures.
"""
from collections import defaultdict
from datetime import date,datetime,timedelta,timezone
from decimal import Decimal
from pathlib import Path
import csv,hashlib,json

def span(a,b):
    day=date.fromisoformat(a);end=date.fromisoformat(b)
    while day<end:
        yield day.isoformat();day+=timedelta(days=1)
def total(rows,col):return sum((Decimal(r[col]) for r in rows if r[col] not in ('','\\N')),Decimal(0))

class RawReference:
    def __init__(self,root):
        root=Path(root);catalog=json.loads((root/'catalog/catalog.json').read_text(encoding='utf8'));self.raw={}
        self.source_files=0
        for ds in catalog['datasets']:
            path=root/ds['relative_path'];assert hashlib.sha256(path.read_bytes()).hexdigest()==ds['sha256']
            self.source_files+=1
            if 'columns' in ds:
                with path.open(encoding='utf8',newline='') as f:self.raw[ds['dataset_id']]=list(csv.DictReader(f))
        self.idx={}
        for ns,names in [('hotel_ops',['hotels','rooms','bookings','booking_rooms','outlets','assets','purchase_orders','purchase_lines','receipts']),('entertainment_ops',['activities','centres','vehicles','tickets'])]:
            for name in names:
                rows=self.raw[ns+'.'+name];pk=next(iter(rows[0]));self.idx[name]={r[pk]:r for r in rows}
        self.blocked=set()
        for r in self.h('maintenance'):
            room=self.idx['assets'][r['asset_id']]['room_id']
            if room not in ('','\\N'):self.blocked.update((room,d) for d in span(r['starts_on'],r['ends_on']))
        self.closed={(r['activity_id'],r['closed_on']) for r in self.e('closures')}
        self.vm={(r['vehicle_id'],d) for r in self.e('vehicle_maintenance') for d in span(r['starts_on'],r['ends_on'])}
        self.rented={(r['vehicle_id'],d) for r in self.e('rentals') if r['status']=='COMPLETED' for d in span(r['pickup_date'],r['return_date'])}
        self.weather={(r['site_id'],r['weather_date']):r for r in self.h('weather_daily')}
        self.booking_rooms=defaultdict(list)
        for r in self.h('booking_rooms'):self.booking_rooms[r['booking_id']].append(r)
        self.receipts=defaultdict(list)
        for r in self.h('receipts'):self.receipts[r['purchase_line_id']].append(r)
        self.ticket_by_booking=defaultdict(list);self.rental_by_booking=defaultdict(list)
        for r in self.e('ticket_orders'):self.ticket_by_booking[r['hotel_booking_ref']].append(r)
        for r in self.e('rentals'):self.rental_by_booking[r['hotel_booking_ref']].append(r)
    def h(self,name):return self.raw['hotel_ops.'+name]
    def e(self,name):return self.raw['entertainment_ops.'+name]
    def compute(self,group,ctx):
        s=ctx.get('start','2024-01-01');end=ctx.get('end','2026-01-01');a=ctx.get('assessment','2025-12-31');f=ctx.get('filters',{})
        period=lambda d:s<=d<end
        def match(**attrs):return all(str(attrs[k])==str(v) for k,v in f.items() if k in attrs)
        def hotel(hid):
            h=self.idx['hotels'][hid];return match(hotel=hid,site=h['site_id'],stars=h['stars'])
        def booking(b):
            return hotel(b['hotel_id']) and match(channel=b['channel_id'],promotion=b['promotion_id']) and ('room_type' not in f or any(self.idx['rooms'][r['room_id']]['room_type']==f['room_type'] for r in self.booking_rooms[b['booking_id']]))
        def room(r):return hotel(r['hotel_id']) and match(room_type=r['room_type'])
        def outlet(oid,meal):return hotel(self.idx['outlets'][oid]['hotel_id']) and match(outlet=oid,meal=meal)
        def centre(cid,day):
            site=self.idx['centres'][cid]['site_code']
            return match(centre=cid,site=site) and ('severe_weather' not in f or str(self.weather[(site,day)]['severe_weather'])==str(f['severe_weather']))
        def purchase(line):
            po=self.idx['purchase_orders'][line['purchase_order_id']]
            return hotel(po['hotel_id']) and match(supplier=po['supplier_id'],item=line['item_id'])
        result={}
        def put(n,num,den=1):result[f'{group}.{n:02}']=(Decimal(num),Decimal(den))
        if group=='B01':
            nights=set()
            for stay in self.h('stays'):
                br=self.idx['booking_rooms'][stay['booking_room_id']];b=self.idx['bookings'][br['booking_id']]
                if b['status']=='COMPLETED' and room(self.idx['rooms'][br['room_id']]) and match(channel=b['channel_id']):
                    nights.update((br['room_id'],d) for d in span(stay['checkin_date'],stay['checkout_date']) if period(d))
            available=sum((r['room_id'],d) not in self.blocked for r in self.h('rooms') if room(r) for d in span(s,end))
            cohort=[b for b in self.h('bookings') if period(b['arrival']) and booking(b)]
            put(1,len(nights));put(2,available);put(3,len(nights),available)
            put(4,sum(b['status']=='CANCELLED' for b in cohort),len(cohort));put(5,sum(b['status']=='NO_SHOW' for b in cohort),len(cohort))
        elif group in ('B02','B03'):
            cohort=[b for b in self.h('bookings') if period(b['departure']) and b['status']=='COMPLETED' and booking(b)]
            if group=='B02':
                for n,col in enumerate(['gross_vnd','customer_due_vnd','company_share_vnd','partner_share_vnd','commission_vnd'],1):put(n,total(cohort,col))
                put(6,total(cohort,'gross_vnd')-total(cohort,'company_share_vnd')-total(cohort,'commission_vnd'))
            else:
                bought=0;tv=Decimal(0);rv=Decimal(0)
                for b in cohort:
                    tickets=self.ticket_by_booking[b['booking_id']];rentals=[r for r in self.rental_by_booking[b['booking_id']] if r['status']=='COMPLETED']
                    nets=[Decimal(t['gross_vnd'])-Decimal(t['refunded_vnd']) for t in tickets]
                    bought+=any(v>0 for v in nets) or any(Decimal(r['agreed_vnd'])>0 for r in rentals)
                    tv+=sum(nets,Decimal(0));rv+=total(rentals,'agreed_vnd')
                put(1,bought);put(2,bought,len(cohort));put(3,tv);put(4,rv);put(5,total(cohort,'customer_due_vnd')+tv+rv)
        elif group=='B04':
            ents=[]
            for r in self.h('breakfast_entitlements'):
                br=self.idx['booking_rooms'][r['booking_room_id']];b=self.idx['bookings'][br['booking_id']]
                candidates=[o['outlet_id'] for o in self.h('outlets') if o['hotel_id']==b['hotel_id'] and o['outlet_type']=='RESTAURANT'];assert len(candidates)==1
                if period(r['service_date']) and b['status']=='COMPLETED' and outlet(candidates[0],'BREAKFAST'):ents.append(r)
            orders=[r for r in self.h('dining_orders') if period(r['service_date']) and outlet(r['outlet_id'],r['meal'])]
            sessions=[r for r in self.h('meal_sessions') if period(r['service_date']) and r['meal'] in ('BREAKFAST','DINNER') and outlet(r['outlet_id'],r['meal'])]
            eligible=total(ents,'eligible_covers');redeemed=total(ents,'redeemed_covers');cost=total(sessions,'ingredient_cost_vnd')
            ratings=[r for r in orders if r['rating'] not in ('','\\N') and 1<=Decimal(r['rating'])<=5]
            put(1,eligible);put(2,redeemed);put(3,redeemed,eligible);put(4,total(orders,'net_vnd'));put(5,total(orders,'covers')+redeemed)
            put(6,cost);put(7,cost,total(sessions,'actual_covers'));put(8,total(ratings,'rating'),len(ratings))
        elif group=='B05':
            admissions=0;capacity=0;ready=0;rented=0
            for r in self.e('admissions'):
                stamp=r['entered_at'];stamp=stamp+':00' if stamp[-3] in '+-' else stamp
                day=datetime.fromisoformat(stamp).astimezone(timezone(timedelta(hours=7))).date().isoformat()
                activity=self.idx['activities'][self.idx['tickets'][r['ticket_id']]['activity_id']]
                if period(day) and centre(activity['centre_id'],day) and match(activity=activity['activity_id'],outdoor=activity['outdoor']):admissions+=1
            for activity in self.e('activities'):
                if not match(activity=activity['activity_id'],outdoor=activity['outdoor']):continue
                for day in span(s,end):
                    if centre(activity['centre_id'],day) and (activity['activity_id'],day) not in self.closed:capacity+=int(activity['capacity_per_day'])
            for vehicle in self.e('vehicles'):
                if not match(vehicle_type=vehicle['vehicle_type']):continue
                for day in span(s,end):
                    if centre(vehicle['centre_id'],day):
                        ready+=(vehicle['vehicle_id'],day) not in self.vm;rented+=(vehicle['vehicle_id'],day) in self.rented
            put(1,admissions);put(2,capacity);put(3,admissions,capacity);put(4,rented);put(5,ready);put(6,rented,ready)
        elif group=='B06':
            ordered=Decimal(0);accepted=Decimal(0);rejected=Decimal(0);late=Decimal(0);otif=0;lines=0
            for line in self.h('purchase_lines'):
                po=self.idx['purchase_orders'][line['purchase_order_id']];due=po['expected_on']
                if not (period(due) and due<=a and purchase(line)):continue
                lines+=1;ordered+=Decimal(line['ordered_qty']);ontime=Decimal(0)
                for receipt in self.receipts[line['purchase_line_id']]:
                    if receipt['received_on']>a:continue
                    good=Decimal(receipt['accepted_qty']);accepted+=good;rejected+=Decimal(receipt['rejected_qty'])
                    if receipt['received_on']>due:late+=good
                    else:ontime+=good
                otif+=ontime>=Decimal(line['ordered_qty'])
            put(1,ordered);put(2,accepted);put(3,rejected);put(4,late);put(5,accepted,ordered);put(6,rejected,accepted+rejected);put(7,otif,lines)
        elif group=='B07':
            opening=Decimal(0);closing=Decimal(0);used=Decimal(0);wasted=Decimal(0);waste_value=Decimal(0);available_value=Decimal(0)
            for r in self.h('stock_movements'):
                if r['movement_date']>=end:continue
                receipt=self.idx['receipts'][r['receipt_id']];line=self.idx['purchase_lines'][receipt['purchase_line_id']]
                if not (purchase(line) and match(usage_area=r['usage_area'])):continue
                qty=Decimal(r['quantity']);price=Decimal(line['unit_price_vnd']);signed=qty if r['movement_type']=='IN' else -qty
                closing+=signed
                if r['movement_date']<s:opening+=signed;available_value+=signed*price
                elif r['movement_type']=='IN':available_value+=qty*price
                elif r['movement_type']=='USE':used+=qty
                elif r['movement_type']=='WASTE':wasted+=qty;waste_value+=qty*price
            put(1,opening);put(2,closing);put(3,used);put(4,wasted);put(5,waste_value);put(6,waste_value,available_value)
        elif group=='B08':
            work=[r for r in self.h('maintenance') if r['status']=='COMPLETED' and period(r['ends_on']) and hotel(self.idx['assets'][r['asset_id']]['hotel_id']) and match(work_type=r['work_type'],asset_type=self.idx['assets'][r['asset_id']]['asset_type'])]
            cells={(r['room_id'],d) for r in self.h('rooms') if room(r) for d in span(s,end)};blocked=len(cells & self.blocked)
            put(1,total(work,'cost_vnd'));put(2,blocked);put(3,len(cells)-blocked);put(4,blocked,len(cells))
        else:raise ValueError(group)
        return result
