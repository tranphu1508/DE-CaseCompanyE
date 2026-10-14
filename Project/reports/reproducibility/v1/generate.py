"""Deterministic synthetic OLTP data. No external accounts or real customer data."""
import argparse
import csv
import hashlib
import json
import random
import platform
import unicodedata
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

from model import MODELS, all_contracts

ROOT = Path(__file__).resolve().parents[1]


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def days(start, end):
    return [start + timedelta(days=i) for i in range((end-start).days)]


def timestamp(d, hour=10):
    return f"{d.isoformat()}T{hour:02d}:00:00+07:00"


class Generator:
    def __init__(self, cfg):
        self.cfg = cfg
        self.r = random.Random(cfg["seed"])
        self.start = date.fromisoformat(cfg["date_from"])
        self.end = date.fromisoformat(cfg["date_to"])
        self.rows = {db: {t.name: [] for t in tables} for db,tables in MODELS.items()}
        self.models = {db: {t.name: t for t in tables} for db,tables in MODELS.items()}
        self.occupied = set()
        self.blocked = set()
        self.vehicle_busy = set()
        self.vehicle_blocked = set()
        self.closed = set()
        self.weather = {}
        self.meals = defaultdict(int)
        self.truth = []

    def put(self, db, table, **values):
        model = self.models[db][table]
        columns = [x[0] for x in model.columns]
        if set(values) - set(columns):
            raise ValueError((table, set(values)-set(columns)))
        values.setdefault(columns[0], f"{table.upper()}-{len(self.rows[db][table])+1:07d}")
        for name, kind, rules, desc in model.columns:
            if name not in values:
                if "NOT NULL" in rules:
                    raise ValueError(f"Missing {table}.{name}")
                values[name] = None
            if isinstance(values[name], date): values[name] = values[name].isoformat()
        self.rows[db][table].append(values)
        return values

    def h(self, table, **v): return self.put("hotel_ops",table,**v)
    def e(self, table, **v): return self.put("entertainment_ops",table,**v)

    def masters(self):
        labels = [("SP","Sa Pa","NORTH_MOUNTAIN","E Núi Mây"),
                  ("DN","Đà Nẵng","CENTRAL_COAST","E Sóng Biển"),
                  ("DL","Đà Lạt","HIGHLAND","E Vườn Thông"),
                  ("PQ","Phú Quốc","ISLAND","E Đảo Ngọc")]
        self.hotels=[]; self.hotel_rooms=defaultdict(list); self.centre_by_site={}; self.outlet_by_hotel={}
        for site, name, climate, centre_name in labels:
            self.h("sites",site_id=site,site_name=name,climate_region=climate)
            centre=self.e("centres",centre_id="C-"+site,site_code=site,centre_name=centre_name)
            self.centre_by_site[site]=centre["centre_id"]
            for stars,brand,n in [(5,"Grand",self.cfg["five_star_rooms"]),(3,"Stay",self.cfg["three_star_rooms"])]:
                hid=f"{site}-{stars}"
                self.h("channels",channel_id=f"WEB-{hid}",channel_name=f"Website E {brand} {name}",channel_type="DIRECT",commission_bps=0)
                hotel=self.h("hotels",hotel_id=hid,site_id=site,hotel_name=f"E {brand} {name}",stars=stars,website_channel=f"WEB-{hid}")
                self.hotels.append(hotel)
                for i in range(n):
                    deluxe=(i%4==0)
                    room=self.h("rooms",room_id=f"{hid}-{i+101}",hotel_id=hid,room_type="DELUXE" if deluxe else "STANDARD",capacity=4,base_rate_vnd=(2100000 if stars==5 else 750000)+(350000 if deluxe else 0))
                    self.hotel_rooms[hid].append(room)
                for typ in ["RESTAURANT","BAR"]:
                    outlet=self.h("outlets",outlet_id=f"{hid}-{typ}",hotel_id=hid,outlet_type=typ,capacity=120 if typ=="RESTAURANT" else 45,quality_profile=self.r.randint(2,5))
                    if typ=="RESTAURANT": self.outlet_by_hotel[hid]=outlet["outlet_id"]
        for cid,name,bps in [("AGODA","Agoda",1200),("BOOKING","Booking.com",1400),("BE","be",900),("MOMO","MoMo",800),("DESK","Lễ tân và điện thoại",0)]:
            self.h("channels",channel_id=cid,channel_name=name,channel_type="DIRECT" if cid=="DESK" else "DISTRIBUTOR",commission_bps=bps)
        self.channels={c["channel_id"]:c for c in self.rows['hotel_ops']['channels']}
        self.plans={}
        for hotel in self.hotels:
            hid=hotel['hotel_id']
            for ch in [hotel['website_channel'],'DESK','AGODA','BOOKING','BE','MOMO']:
                for included in ([1] if hotel['stars']==5 else [0,1]):
                    p=self.h("rate_plans",hotel_id=hid,channel_id=ch,plan_name="Room with breakfast" if included else "Room only",breakfast_included=included,refundable=1)
                    self.plans[(hid,ch,included)]=p['rate_plan_id']
        for pid,name,months,fee in [('MEMBER','E Member',0,0),('PLUS','E Plus',12,1500000),('FAMILY','E Family',12,2500000)]:
            self.h('membership_plans',plan_id=pid,plan_name=name,duration_months=months,fee_vnd=fee)
        self.card_by_guest={}
        for i in range(self.cfg['customers']):
            gid=f"H-{i+1:06d}"
            name=self.r.choice(['Nguyễn','Trần','Lê','Phạm','Đỗ'])+' '+self.r.choice(['Minh','Thanh','Ngọc','Hoàng','Gia'])+' '+self.r.choice(['An','Bình','Chi','Duy','Hà','Linh'])+f' {i+1}'
            phone=f"09{i+1:08d}"
            email=f"guest{i+1}@example.invalid"
            self.h('guests',guest_id=gid,full_name=name,phone=phone,email=email)
            if self.r.random()<0.34:
                plan=self.r.choices(['MEMBER','PLUS','FAMILY'],[.7,.2,.1])[0]
                membership=self.h('memberships',plan_id=plan,guest_id=gid,valid_from=self.start,valid_to=None if plan=='MEMBER' else self.start+timedelta(days=365),paid_vnd={'MEMBER':0,'PLUS':1500000,'FAMILY':2500000}[plan])
                card=self.h('member_cards',membership_id=membership['membership_id'],guest_id=gid,card_type='DIGITAL')
                self.card_by_guest[gid]=card['card_id']
            customer_id=f"E-{self.cfg['customers']-i:06d}"
            display=''.join(ch for ch in unicodedata.normalize('NFD',name) if unicodedata.category(ch)!='Mn').replace('Đ','D') if i%3==0 else name
            self.e('customers',customer_id=customer_id,full_name=display,phone=None if i%9==0 else ('+84 '+phone[1:] if i%2 else phone),email=None if i%5==0 else email.upper() if i%4==0 else email,member_card_ref=self.card_by_guest.get(gid) if i%2 else None)
            self.truth.append({'hotel_guest_id':gid,'entertainment_customer_id':customer_id})
        self.customer_for_guest={p['hotel_guest_id']:p['entertainment_customer_id'] for p in self.truth}
        # Distinct funding models, two annual seasons, source policies retain effective dates.
        for year in range(self.start.year,self.end.year+1):
            for site in ['SP','DN','DL','PQ']:
                for channel in [None,'AGODA','BOOKING','BE','MOMO']:
                    summer=(site in ['DN','DL'])
                    begin=date(year,5 if summer else 1,1)
                    stop=date(year,8 if summer else 4,30)
                    self.h('promotions',channel_id=channel,site_id=site,promotion_name=f"{site} Season {year} {channel or 'DIRECT'}",sale_from=begin-timedelta(days=90),sale_to=stop,stay_from=begin,stay_to=stop,discount_bps=1000,partner_share_bps=0 if channel is None else 10000 if channel=='AGODA' else 6000,cap_vnd=500000)
        for site,name,climate,cn in labels:
            for d in days(self.start,self.end+timedelta(days=1)):
                wet=(d.month in ([6,7,8] if site=='SP' else [9,10,11,12] if site=='DN' else [5,6,7,8,9,10]))
                rain=self.r.randint(8,85) if self.r.random() < (.48 if wet else .12) else 0
                base_temp=([8,10,14,17,20,22,22,21,19,16,12,9][d.month-1] if site=='SP' else 20 if site=='DL' else [23,24,26,28,30,32,32,31,29,27,25,23][d.month-1] if site=='DN' else 28)
                temp=base_temp+self.r.randint(-3,3)
                severe=int(rain>65)
                self.h('weather_daily',site_id=site,weather_date=d,temperature_c=temp,rain_mm=rain,severe_weather=severe,provenance='SYNTHETIC_CLIMATE_SCENARIO')
                self.weather[(site,d)]=severe
        self.suppliers_and_assets()
        self.activities={}; self.vehicles=defaultdict(list)
        for site,_,_,_ in labels:
            centre=self.centre_by_site[site]
            self.activities[site]=[]
            for label,outdoor,price in [('Outdoor experience',1,250000),('Indoor family activities',0,180000),('Evening performance',0,200000)]:
                a=self.e('activities',centre_id=centre,activity_name=label,outdoor=outdoor,capacity_per_day=450,ticket_price_vnd=price)
                self.activities[site].append(a)
                for d in days(self.start,self.end+timedelta(days=1)):
                    if (outdoor and self.weather[(site,d)]) or (d.day==15 and d.month%3==0):
                        self.e('closures',activity_id=a['activity_id'],closed_on=d,reason='WEATHER' if outdoor and self.weather[(site,d)] else 'MAINTENANCE')
                        self.closed.add((a['activity_id'],d))
            for i in range(30):
                typ='CAR' if i<10 or site=='SP' else 'MOTORBIKE'
                v=self.e('vehicles',centre_id=centre,vehicle_type=typ,daily_rate_vnd=900000 if typ=='CAR' else 180000)
                self.vehicles[site].append(v)
                for year in range(self.start.year,self.end.year+1):
                    start=date(year,6,1)+timedelta(days=i%20)
                    end=start+timedelta(days=3)
                    self.e('vehicle_maintenance',vehicle_id=v['vehicle_id'],starts_on=start,ends_on=end,cost_vnd=1500000 if typ=='CAR' else 250000)
                    self.vehicle_blocked.update((v['vehicle_id'],d) for d in days(start,end))

    def suppliers_and_assets(self):
        names=[('Everon','EQUIPMENT'),('Minh Long','EQUIPMENT'),('MM Mega Market','FOOD'),('Vinamilk','FOOD'),('Đà Lạt GAP','FOOD'),('Daikin','MAINTENANCE'),('Schindler','MAINTENANCE')]
        for i,(name,cat) in enumerate(names):
            self.h('suppliers',supplier_id=f'S-{i+1:02d}',supplier_name=name,category=cat,site_id=None,delivery_format='CSV')
        for site,label in [('SP','Núi Bắc'),('DN','D01'),('DL','L01'),('PQ','P01')]:
            self.h('suppliers',supplier_id=f'L-{site}-1',supplier_name='Đầu mối Rau '+label+' (giả định)',category='FOOD',site_id=site,delivery_format='MIXED')
            self.h('suppliers',supplier_id=f'L-{site}-2',supplier_name='Vựa thực phẩm '+label+' (giả định)',category='FOOD',site_id=site,delivery_format='TEXT')
        items=[('RICE','Gạo','Gạo trắng loại A','kg',180,20000),('TOMATO','Cà chua','Tươi, loại A','kg',7,25000),('FISH','Cá hồi phi lê','Phi lê đông lạnh','kg',30,250000),('MILK','Sữa','Sữa tươi không đường','litre',30,35000),('LINEN','Ga giường','Cotton 160x200','piece',0,300000),('PLATE','Đĩa sứ','Trắng 22cm','piece',0,85000)]
        for iid,name,spec,unit,life,cost in items:
            self.h('items',item_id=iid,item_name=name,specification=spec,base_unit=unit,shelf_life_days=life,reference_cost_vnd=cost)
        for hotel in self.hotels:
            for room in self.hotel_rooms[hotel['hotel_id']]:
                asset=self.h('assets',hotel_id=hotel['hotel_id'],room_id=room['room_id'],asset_type='AC',supplier_id='S-06')
                for year in range(self.start.year,self.end.year+1):
                    start=date(year,3,1)+timedelta(days=self.r.randint(0,200))
                    end=start+timedelta(days=self.r.randint(1,3))
                    self.h('maintenance',asset_id=asset['asset_id'],starts_on=start,ends_on=end,work_type=self.r.choice(['PLANNED','BREAKDOWN']),cost_vnd=self.r.choice([0,300000,600000]),status='COMPLETED')
                    self.blocked.update((room['room_id'],d) for d in days(start,end))
            for typ,supplier in [('LIFT','S-07'),('COLD_STORAGE','S-06')]:
                # Cold storage vendor is an internal maintenance unit, not a brand capability claim.
                if typ=='COLD_STORAGE':
                    supplier='S-INTERNAL'
                    if not any(x['supplier_id']==supplier for x in self.rows['hotel_ops']['suppliers']):
                        self.h('suppliers',supplier_id=supplier,supplier_name='CompanyE Internal Technical Team',category='MAINTENANCE',delivery_format='CSV')
                asset=self.h('assets',hotel_id=hotel['hotel_id'],room_id=None,asset_type=typ,supplier_id=supplier)
                for year in range(self.start.year,self.end.year+1):
                    start=date(year,9,5)
                    self.h('maintenance',asset_id=asset['asset_id'],starts_on=start,ends_on=start+timedelta(days=2),work_type='PLANNED',cost_vnd=800000,status='COMPLETED')

    def bookings(self):
        choices=days(self.start,self.end-timedelta(days=5))
        weights={}
        for site in self.centre_by_site:
            peak=[5,6,7,8] if site in ['DN','DL'] else [1,2,3,4,11,12] if site=='PQ' else [3,4,9,10,11,12]
            weights[site]=[(1.7 if d.month in peak else .85)*(1.35 if d.weekday()>=4 else 1) for d in choices]
        self.completed=[]
        attempts=0
        while len(self.rows['hotel_ops']['bookings'])<self.cfg['bookings']:
            attempts+=1
            if attempts>self.cfg['bookings']*8: raise RuntimeError('Requested volume exceeds available room capacity')
            hotel=self.r.choice(self.hotels); hid=hotel['hotel_id']; site=hotel['site_id']
            arrival=self.r.choices(choices,weights[site])[0]
            nights=self.r.choices([1,2,3,4,5],[.24,.35,.24,.12,.05])[0]
            departure=arrival+timedelta(days=nights)
            booked=arrival-timedelta(days=self.r.randint(0,60))
            status=self.r.choices(['COMPLETED','CANCELLED','NO_SHOW'],[.84,.13,.03])[0]
            available=[r for r in self.hotel_rooms[hid] if all((r['room_id'],d) not in self.occupied and (r['room_id'],d) not in self.blocked for d in days(arrival,departure))]
            nrooms=2 if self.r.random()<.15 else 1
            if len(available)<nrooms: continue
            rooms=self.r.sample(available,nrooms)
            channel=self.r.choices([hotel['website_channel'],'DESK','AGODA','BOOKING','BE','MOMO'],[.3,.1,.24,.2,.08,.08])[0]
            guest=self.r.choice(self.rows['hotel_ops']['guests'])
            lines=[]
            for room in rooms:
                included=1 if hotel['stars']==5 else int(self.r.random()<({'AGODA':.6,'BOOKING':.45,'MOMO':.65,'BE':.35}.get(channel,.3)))
                rate=int(room['base_rate_vnd']*(1.15 if arrival.month in [6,7,12] else .95)//1000)*1000
                if hotel['stars']==3 and included: rate+=180000
                adults=self.r.choice([1,2,2,2]); children=self.r.choice([0,0,1])
                lines.append((room,included,rate,adults,children))
            gross=sum(l[2]*nights for l in lines)
            eligible=[p for p in self.rows['hotel_ops']['promotions'] if p['site_id']==site and (p['channel_id']==channel or p['channel_id'] is None and self.channels[channel]['channel_type']=='DIRECT') and p['sale_from']<=booked.isoformat()<=p['sale_to'] and p['stay_from']<=arrival.isoformat() and departure.isoformat()<=p['stay_to']]
            promo=self.r.choice(eligible) if eligible and self.r.random()<.65 else None
            discount=min(gross*promo['discount_bps']//10000,promo['cap_vnd']) if promo else 0
            partner=discount*promo['partner_share_bps']//10000 if promo else 0
            company=discount-partner
            commission=(gross-company)*self.channels[channel]['commission_bps']//10000
            b=self.h('bookings',hotel_id=hid,guest_id=guest['guest_id'],channel_id=channel,promotion_id=promo['promotion_id'] if promo else None,booked_on=booked,arrival=arrival,departure=departure,status=status,payment_method=self.r.choice(['CARD','BANK','MOMO','CASH']),gross_vnd=gross,discount_vnd=discount,company_share_vnd=company,partner_share_vnd=partner,customer_due_vnd=gross-discount,commission_vnd=commission,updated_at=timestamp(departure))
            self.h('payments',booking_id=b['booking_id'],event_time=timestamp(booked),event_type='CHARGE',amount_vnd=gross-discount)
            if status=='CANCELLED':
                self.h('payments',booking_id=b['booking_id'],event_time=timestamp(max(booked,arrival-timedelta(days=1))),event_type='REFUND',amount_vnd=gross-discount)
            if self.channels[channel]['channel_type']=='DISTRIBUTOR':
                due=partner if status=='COMPLETED' else 0
                pending=due>0 and self.r.random()<.04
                self.h('settlements',booking_id=b['booking_id'],sponsor_due_vnd=due,sponsor_received_vnd=0 if pending else due,commission_vnd=commission if status!='CANCELLED' else 0,status='PENDING' if pending else 'MATCHED')
            for room,included,rate,adults,children in lines:
                br=self.h('booking_rooms',booking_id=b['booking_id'],room_id=room['room_id'],rate_plan_id=self.plans[(hid,channel,included)],adults=adults,children=children,breakfast_guests=adults if included else 0,nightly_rate_vnd=rate)
                if status=='COMPLETED':
                    self.occupied.update((room['room_id'],d) for d in days(arrival,departure))
                    self.h('stays',booking_room_id=br['booking_room_id'],checkin_date=arrival,checkout_date=departure)
                    for d in days(arrival+timedelta(days=1),departure+timedelta(days=1)):
                        if included:
                            redeemed=sum(self.r.random()<.9 for _ in range(adults))
                            self.h('breakfast_entitlements',booking_room_id=br['booking_room_id'],service_date=d,eligible_covers=adults,redeemed_covers=redeemed)
                            self.meals[(hid,d,'BREAKFAST')]+=redeemed
                        elif self.r.random()<.45:
                            self.dining(hotel,guest['guest_id'],b['booking_id'],d,'BREAKFAST',adults)
            if status=='COMPLETED':
                self.completed.append(b)
                if self.r.random()<.72:
                    target=next(h for h in self.hotels if h['site_id']==site and h['stars']!=hotel['stars']) if self.r.random()<.2 else hotel
                    self.dining(target,guest['guest_id'],b['booking_id'],arrival,self.r.choice(['LUNCH','DINNER','BAR']),sum(l[3] for l in lines))
                if self.r.random()<.55:
                    self.ticket(site,self.customer_for_guest[guest['guest_id']],arrival,b['booking_id'],sum(l[3] for l in lines))
                if self.r.random()<.24:
                    self.rental(site,self.customer_for_guest[guest['guest_id']],arrival,b['booking_id'])

    def dining(self, hotel, guest_id, booking_id, d, meal, covers):
        stars=hotel['stars']; hid=hotel['hotel_id']
        gross=covers*({'BREAKFAST':150000,'LUNCH':200000,'DINNER':450000,'BAR':160000}[meal])*(2 if stars==5 and meal!='BREAKFAST' else 1)
        discount=gross//10 if self.r.random()<.12 else 0
        profile=next(o['quality_profile'] for o in self.rows['hotel_ops']['outlets'] if o['outlet_id']==self.outlet_by_hotel[hid])
        self.h('dining_orders',outlet_id=f"{hid}-{'BAR' if meal=='BAR' else 'RESTAURANT'}",guest_id=guest_id,booking_id=booking_id,service_date=d,meal=meal,covers=covers,gross_vnd=gross,discount_vnd=discount,net_vnd=gross-discount,wait_minutes=self.r.randint(1,30),rating=max(1,min(5,profile+self.r.choice([-1,0,0,1]))))
        if meal in ['BREAKFAST','DINNER']: self.meals[(hid,d,meal)]+=covers

    def ticket(self, site, customer, d, booking, covers):
        act=self.r.choice(self.activities[site]); aid=act['activity_id']
        actual=d; status='USED'; refunded=0
        if (aid,d) in self.closed:
            if self.r.random()<.55 and (aid,d+timedelta(days=1)) not in self.closed and d<self.end:
                actual=d+timedelta(days=1); status='RESCHEDULED'
            else:
                status='REFUNDED'; refunded=covers*act['ticket_price_vnd']
        elif self.r.random()<.09: status='UNUSED'
        order=self.e('ticket_orders',centre_id=self.centre_by_site[site],customer_id=customer,hotel_booking_ref=booking,ordered_on=d,sales_channel='HOTEL_RECEPTION' if booking else 'GATE',gross_vnd=covers*act['ticket_price_vnd'],refunded_vnd=refunded)
        self.e('cash_events',ticket_order_id=order['ticket_order_id'],rental_id=None,event_time=timestamp(d,8),event_type='CHARGE',amount_vnd=order['gross_vnd'])
        if refunded:
            self.e('cash_events',ticket_order_id=order['ticket_order_id'],rental_id=None,event_time=timestamp(d,18),event_type='REFUND',amount_vnd=refunded)
        for i in range(covers):
            t=self.e('tickets',ticket_order_id=order['ticket_order_id'],activity_id=aid,original_date=d,valid_date=actual,status=status,price_vnd=act['ticket_price_vnd'])
            if status in ['USED','RESCHEDULED']:
                self.e('admissions',ticket_id=t['ticket_id'],entered_at=timestamp(actual,self.r.randint(9,18)))

    def rental(self, site, customer, d, booking):
        duration=self.r.choice([1,1,2]); end=d+timedelta(days=duration)
        available=[v for v in self.vehicles[site] if all((v['vehicle_id'],x) not in self.vehicle_busy and (v['vehicle_id'],x) not in self.vehicle_blocked for x in days(d,end))]
        if not available: return
        v=self.r.choice(available)
        status='CANCELLED' if self.r.random()<.07 else 'COMPLETED'
        contract=self.e('rentals',vehicle_id=v['vehicle_id'],customer_id=customer,hotel_booking_ref=booking,pickup_date=d,return_date=end,status=status,agreed_vnd=v['daily_rate_vnd']*duration)
        self.e('cash_events',ticket_order_id=None,rental_id=contract['rental_id'],event_time=timestamp(d,8),event_type='CHARGE',amount_vnd=contract['agreed_vnd'])
        if status=='COMPLETED': self.vehicle_busy.update((v['vehicle_id'],x) for x in days(d,end))
        else: self.e('cash_events',ticket_order_id=None,rental_id=contract['rental_id'],event_time=timestamp(d,9),event_type='REFUND',amount_vnd=contract['agreed_vnd'])

    def purchasing(self):
        # Purchases cover perishable food daily. Each lot has explicit movements.
        for hotel in self.hotels:
            hid=hotel['hotel_id']; site=hotel['site_id']
            for d in days(self.start,self.end-timedelta(days=2)):
                covers=sum(self.meals.get((hid,d,meal),0) for meal in ['BREAKFAST','DINNER'])
                for iid in ['RICE','TOMATO','FISH','MILK']:
                    item=next(i for i in self.rows['hotel_ops']['items'] if i['item_id']==iid)
                    supplier='S-04' if iid=='MILK' else self.r.choice(['S-03',f'L-{site}-1' if iid in ['RICE','TOMATO'] else f'L-{site}-2'])
                    if iid=='TOMATO' and site=='DL' and self.r.random()<.5: supplier='S-05'
                    amount=max(3,round(covers*({'RICE':.2,'TOMATO':.15,'FISH':.12,'MILK':.2}[iid])))
                    self.purchase(hotel,d,supplier,item,amount)
            for month in range(1,25):
                d=self.start+timedelta(days=month*28)
                if d>self.end-timedelta(days=3): continue
                for iid,supplier in [('LINEN','S-01'),('PLATE','S-02')]:
                    item=next(i for i in self.rows['hotel_ops']['items'] if i['item_id']==iid)
                    self.purchase(hotel,d,supplier,item,self.r.randint(8,30))

    def purchase(self, hotel, d, supplier, item, amount):
        po=self.h('purchase_orders',hotel_id=hotel['hotel_id'],supplier_id=supplier,ordered_on=d-timedelta(days=2),expected_on=d)
        line=self.h('purchase_lines',purchase_order_id=po['purchase_order_id'],item_id=item['item_id'],ordered_qty=amount,unit_price_vnd=int(item['reference_cost_vnd']*self.r.uniform(.9,1.15)//100)*100)
        received=d+timedelta(days=1 if self.r.random()<.05 else 0)
        accepted=max(1,amount-(1 if self.r.random()<.08 else 0)); rejected=amount-accepted
        receipt=self.h('receipts',purchase_line_id=line['purchase_line_id'],received_on=received,accepted_qty=accepted,rejected_qty=rejected,expires_on=received+timedelta(days=item['shelf_life_days']) if item['shelf_life_days'] else None)
        values=dict(hotel_id=hotel['hotel_id'],item_id=item['item_id'],receipt_id=receipt['receipt_id'],movement_date=received)
        self.h('stock_movements',**values,movement_type='IN',quantity=accepted,usage_area='WAREHOUSE')
        waste=1 if accepted>2 and self.r.random()<.08 and item['shelf_life_days'] else 0
        used=max(0,accepted-waste-1)
        bf=self.session_map.get((hotel['hotel_id'],received,'BREAKFAST'))
        dn=self.session_map.get((hotel['hotel_id'],received,'DINNER'))
        total=(bf['actual_covers'] if bf else 0)+(dn['actual_covers'] if dn else 0)
        if item['shelf_life_days'] and total:
            breakfast_used=round(used*(bf['actual_covers'] if bf else 0)/total)
            for session,amount_used in [(bf,breakfast_used),(dn,used-breakfast_used)]:
                if session and amount_used:
                    self.h('stock_movements',**values,session_id=session['session_id'],movement_type='USE',quantity=amount_used,usage_area='BUFFET')
                    session['ingredient_cost_vnd']+=amount_used*line['unit_price_vnd']
        else:
            self.h('stock_movements',**values,movement_type='USE',quantity=used,usage_area='KITCHEN_OTHER' if item['shelf_life_days'] else 'HOUSEKEEPING')
        if waste: self.h('stock_movements',**values,movement_type='WASTE',quantity=waste,usage_area='WAREHOUSE')
        if receipt['expires_on'] and receipt['expires_on']<=self.end.isoformat():
            self.h('stock_movements',hotel_id=hotel['hotel_id'],item_id=item['item_id'],receipt_id=receipt['receipt_id'],movement_date=receipt['expires_on'],movement_type='WASTE',quantity=1,usage_area='WAREHOUSE')

    def run(self):
        self.masters(); self.bookings()
        for i in range(self.cfg['walkin_tickets']):
            site=self.r.choice(list(self.centre_by_site)); customer=self.r.choice(self.rows['entertainment_ops']['customers'])['customer_id']
            d=self.start+timedelta(days=self.r.randint(0,(self.end-self.start).days-2))
            self.ticket(site,customer,d,None,self.r.choice([1,2,3,4]))
            if self.r.random()<.2: self.rental(site,customer,d,None)
            if self.r.random()<.5:
                hotel=self.r.choice([h for h in self.hotels if h['site_id']==site])
                self.dining(hotel,None,None,d,self.r.choice(['LUNCH','DINNER','BAR']),self.r.choice([1,2,3]))
        self.session_map={}
        for hotel in self.hotels:
            for d in days(self.start,self.end+timedelta(days=1)):
                for meal in ['BREAKFAST','DINNER']:
                    covers=self.meals.get((hotel['hotel_id'],d,meal),0)
                    session=self.h('meal_sessions',outlet_id=self.outlet_by_hotel[hotel['hotel_id']],service_date=d,meal=meal,actual_covers=covers,ingredient_cost_vnd=0)
                    self.session_map[(hotel['hotel_id'],d,meal)]=session
        self.purchasing()


def code_fingerprint():
    return {name:sha(ROOT/'src'/name) for name in ['generate.py','model.py']}


def export(gen, out):
    counts={}; init=['\\set ON_ERROR_STOP on']
    for db,tables in MODELS.items():
        folder=out/db; folder.mkdir(parents=True,exist_ok=True)
        init.append(f'CREATE DATABASE {db};')
        init += [f'\\connect {db}', 'BEGIN;']
        ddl='\n\n'.join(t.ddl() for t in tables)
        (folder/'schema.sql').write_text(ddl,encoding='utf-8')
        init.append(ddl)
        counts[db]={}
        for t in tables:
            path=folder/(t.name+'.csv')
            with path.open('w',encoding='utf-8',newline='') as f:
                w=csv.writer(f); cols=[c[0] for c in t.columns]; w.writerow(cols)
                w.writerows(['\\N' if row[n] is None else row[n] for n in cols] for row in gen.rows[db][t.name])
            counts[db][t.name]=len(gen.rows[db][t.name])
            init.append(f"COPY {t.name} FROM '/seed/{gen.cfg['dataset_version']}/{db}/{t.name}.csv' WITH (FORMAT CSV, HEADER true, NULL '\\N');")
            for name,kind,rules,desc in t.columns:
                if 'REFERENCES' in rules: init.append(f'CREATE INDEX ON {t.name} ({name});')
        init += ['COMMIT;', 'ANALYZE;']
    (out/'load.sql').write_text('\n'.join(init),encoding='utf-8')
    write_json(out/'contracts.json',all_contracts())
    write_json(out/'audit_only'/'identity_truth_DO_NOT_INGEST.json',gen.truth)
    audit={
        'seed':gen.cfg['seed'], 'rng':'Python random.Random / MT19937; single stream; preserve code and Python version',
        'python_version':platform.python_version(),'generator_sha256':code_fingerprint(),
        'configuration':gen.cfg,
        'rules':[
            {'id':'G01','rule':'Date sampling weights: destination peak=1.7, off-peak=.85; Fri-Sun=1.35 multiplier','bias':'Seasonal demand is imposed, not discovered from real observations.'},
            {'id':'G02','rule':'Booking status weights completed=.84, cancelled=.13, no_show=.03','bias':'Cancellation rate is synthetic and not causal evidence for channel quality.'},
            {'id':'G03','rule':'Breakfast included for all 5-star rate plans; 3-star inclusion depends on selected channel-specific plan','bias':'Any star-breakfast relationship is a business rule, not model accuracy.'},
            {'id':'G04','rule':'Promotion eligibility uses sale/stay/site/channel; eligible bookings use it with probability .65','bias':'No randomized control design; incremental campaign revenue cannot be identified.'},
            {'id':'G05','rule':'Cross-sell ticket=.55, rental=.24; customer identifiers differ; legitimate contacts may be missing','bias':'Identity truth is excluded from ingestion; no free enterprise customer key.'},
            {'id':'G06','rule':'Weather is synthetic with destination seasonality; affects outdoor closures','bias':'Not real weather; weather is not a direct demand model in v1.'},
            {'id':'G07','rule':'No completed room/vehicle interval may overlap occupancy or maintenance','bias':'Capacity censoring affects realized booking distribution; report actual generated counts.'},
            {'id':'G08','rule':'Ingredient costs come from linked USE movements times purchase unit price; breakfast/dinner split proportional to covers','bias':'Allocation is synthetic; correlation between covers and cost is partly imposed.'},
            {'id':'G09','rule':'Supplier price multipliers .9-1.15, delay .05, rejected unit .08, random waste .08; residual perishable unit expires','bias':'Artificial supplier performance; no claim about named real brands.'},
            {'id':'G10','rule':'Outlet quality baseline randomly 2-5 independent of hotel stars; ratings clipped to 1-5','bias':'Ratings and wait times do not represent observed service.'}
        ],
        'external_quality_scenarios':{'rows':121,'invalid_dates':18,'unknown_unit_rows':30,'duplicate_document_rows':1,'known_currency_tokens':['25k','1,2tr'],'unstructured_files_require_review':True},
        'limitations':['Annual paid membership not automatically renewed; E Family initially records owner only. No detailed point ledger or voucher redemption in v1.',
                       'Linked hotel/entertainment sales exist, but full composite package allocation and partial hotel cancellation histories are not yet modeled.',
                       'Meal ingredient cost uses an explicit allocation rule; it is not per-customer observed consumption.',
                       'Source loading and lake ingestion are full snapshots, not CDC. Original source update histories are not synthesized.',
                       'Procurement covers purchase, receipt and stock; full supplier invoice/payment workflows and transfers are reserved for a later version.'],
        'evaluation_guidance':['Use exact aggregates and integrity invariants for warehouse correctness; do not treat synthetic correlations as business evidence.',
                               'Benchmark on multiple versioned seeds/scales; keep data generation outside timed ETL measurements.',
                               'Do not tune ETL identity resolution using audit_only truth; use it only in separate evaluation.',
                               'Store an untouched holdout scenario/version if evaluating predictive models later.']
    }
    write_json(out/'audit_only'/'generation_audit.json',audit)
    external=out/'external'; external.mkdir(exist_ok=True)
    # Vendor settlement export is a second representation, not an extra economic event.
    with (external/'vendor_settlement.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['settlement_id','booking_id','sponsor_due_vnd','sponsor_received_vnd','commission_vnd','status']); w.writeheader()
        w.writerows(gen.rows['hotel_ops']['settlements'][:300])
    with (external/'supplier_mixed.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f,delimiter=';'); w.writerow(['Supplier','Hotel','Date','Item','Unit','Qty','Price','Document'])
        for i in range(120):
            site=['SP','DN','DL','PQ'][i%4]
            w.writerow([f'L-{site}-1',f'{site}-3','12/07/2025' if i%7 else 'khong ro','Cà chua' if i%3 else 'ca chua', 'kg' if i%4 else 'sọt',str(10+i%5),'25k',f'LOCAL-{i:04d}'])
        w.writerow(['L-DN-1','DN-3','12/07/2025','Cà chua','kg','11','25k','LOCAL-0001'])
    (external/'supplier_message.txt').write_text('CHỨNG TỪ GIẢ LẬP\nVựa P01 gửi E Stay Phú Quốc: ngày 15/7 giao 2 sọt cá, tổng 1,2tr. Chưa có quy cách sọt, chưa rõ loại cá. Cần xác minh trước khi nhập dữ liệu chuẩn.\n',encoding='utf-8')
    (external/'supplier_delivery_scan.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="780" height="180"><rect width="780" height="180" fill="#fff8e7"/><text x="20" y="40" font-size="22">SYNTHETIC DELIVERY NOTE — NOT A REAL INVOICE</text><text x="20" y="90" font-size="20">P01 / E Stay Phu Quoc / 15-07-2025</text><text x="20" y="130" font-size="20">2 baskets fish / 1.200.000 VND / size not provided</text></svg>',encoding='utf-8')
    with (external/'supplier_updates.jsonl').open('w',encoding='utf-8') as f:
        for version,price in [(1,'25k'),(2,'26k')]:
            f.write(json.dumps({'document':'LOCAL-0002','revision':version,'unit_price':price,'received_at':f'2025-07-{13+version}T09:00:00+07:00'},ensure_ascii=False)+'\n')
    manifest={'dataset_version':gen.cfg['dataset_version'],'seed':gen.cfg['seed'],'config':gen.cfg,'generator_sha256':code_fingerprint(),'python_version':platform.python_version(),'rows':counts,'total_rows':sum(sum(x.values()) for x in counts.values()),'synthetic':True,'external_files':[p.name for p in external.iterdir()], 'files':{str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}}
    write_json(out/'manifest.json',manifest)
    write_json(ROOT/'config'/'source_contracts.json',all_contracts())
    print(json.dumps({'path':str(out),'tables':sum(len(x) for x in counts.values()),'total_rows':manifest['total_rows'],'by_database':{k:sum(v.values()) for k,v in counts.items()}},ensure_ascii=False))


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--config',default=str(ROOT/'config'/'generation.json')); args=parser.parse_args()
    cfg=json.loads(Path(args.config).read_text(encoding='utf-8'))
    out=ROOT/'generated'/cfg['dataset_version']
    if out.exists():
        manifest=out/'manifest.json'
        if manifest.exists():
            saved=json.loads(manifest.read_text(encoding='utf-8'))
            if saved['config']==cfg and saved.get('generator_sha256')==code_fingerprint():
                changed=[name for name,digest in saved['files'].items() if not (out/name).exists() or sha(out/name)!=digest]
                if changed: raise SystemExit('Existing dataset checksum mismatch: '+str(changed[:5]))
                print('Existing deterministic dataset verified and retained:',out); return
        raise SystemExit('Output already exists with incomplete/different data. Choose a NEW dataset_version; no destructive reset is automatic.')
    gen=Generator(cfg); gen.run(); export(gen,out)


if __name__=='__main__': main()
