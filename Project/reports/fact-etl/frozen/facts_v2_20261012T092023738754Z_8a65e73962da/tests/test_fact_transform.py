"""Small adversarial business fixtures; never mutate synthetic sources/targets."""
import sys,json,unittest
from pathlib import Path
from datetime import date,datetime,timedelta
from decimal import Decimal
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from fact_etl.transform import Transformer,Reject,days,local_start,datekey,H,E

class FactSemantics(unittest.TestCase):
    def setUp(self):
        self.mapping=json.loads((ROOT/'config/source_target_mapping_v1.json').read_text(encoding='utf8'))
        self.design=json.loads((ROOT/'config/warehouse_design_v1.json').read_text(encoding='utf8'))
        self.sources={c['source_table']:[] for c in self.mapping['source_validation_contracts']}
        self.dims={f'D{i:02}':[] for i in range(1,17)}
        self.q={'source_status':{s:'COMPLETE' for s in self.sources}}
        self.dim('D02',1,site_id='S');self.dim('D03',2,hotel_id='H',site_id='S')
        self.dim('D04',3,room_id='R',hotel_id='H');self.dim('D05',4,channel_code='WEB')
        self.dim('D07',5,source_customer_id='G');self.dim('D08',6,rate_plan_id='RP',hotel_id='H',channel_id='WEB',breakfast_included=1)
        self.dim('D09',7,outlet_id='O',hotel_id='H',outlet_type='RESTAURANT')
        self.dim('D11',8,source_system=E,centre_id='C',site_code='S')
        self.dim('D12',9,source_system=E,activity_id='A',centre_id='C',capacity_per_day=10)
        self.dim('D13',10,source_system=E,vehicle_id='V',centre_id='C')
        self.dim('D07',11,source_system=E,source_customer_id='G')
        for day in days(date(2023,12,31),date(2024,1,6)):
            self.dims['D01'].append(dict(date_key=datekey(day),member_kind='NORMAL',calendar_date=day))
        self.b=dict(booking_id='B',hotel_id='H',guest_id='G',channel_id='WEB',promotion_id=None,booked_on=date(2024,1,1),arrival=date(2024,1,2),departure=date(2024,1,4),status='COMPLETED',updated_at=datetime(2024,1,1),gross_vnd=Decimal(100),discount_vnd=Decimal(10),customer_due_vnd=Decimal(90),company_share_vnd=Decimal(4),partner_share_vnd=Decimal(6),commission_vnd=Decimal(2))
        self.br=dict(booking_room_id='BR',booking_id='B',room_id='R',rate_plan_id='RP')
        self.sources[H+'.bookings']=[self.b];self.sources[H+'.booking_rooms']=[self.br]
    def dim(self,eid,key,**attrs):
        pk=Transformer.pk(None,eid);self.dims[eid].append(dict({pk:key,'source_system':H,'member_kind':'NORMAL','valid_from_utc':datetime(2023,1,1),'valid_to_utc':None},**attrs))
    def transform(self):return Transformer(self.sources,self.dims,self.design,self.mapping,self.q)
    def booking(self,t):t.accept('F01',t.build('F01'))
    def test_half_open_days(self):self.assertEqual(list(days(date(2024,1,1),date(2024,1,3))),[date(2024,1,1),date(2024,1,2)])
    def test_local_midnight_utc(self):self.assertEqual(local_start(date(2024,1,1)),datetime(2023,12,31,17))
    def test_scd_boundary_and_gap(self):
        self.dims['D03'][0]['valid_to_utc']=datetime(2024,1,2)
        self.dim('D03',12,hotel_id='H',site_id='NEW',valid_from_utc=datetime(2024,1,2))
        t=self.transform();self.assertEqual(t.attr('D03','H',datetime(2024,1,2),'site_id'),'NEW')
        with self.assertRaises(Reject):t.dim('D03','H',datetime(2022,1,1))
    def test_scd_overlap_rejected(self):
        self.dim('D03',12,hotel_id='H',site_id='NEW')
        self.assertEqual(self.transform().build('F01'),[])
    def test_booking_amount_not_multiplied_by_rooms(self):
        self.sources[H+'.booking_rooms'] += [dict(self.br,booking_room_id='BR2')]
        rows=self.transform().build('F01');self.assertEqual(len(rows),1);self.assertEqual(rows[0]['gross_vnd'],100)
    def test_null_promotion_is_not_applicable(self):self.assertEqual(self.transform().build('F01')[0]['promotion_key'],-1)
    def test_bad_ref_does_not_erase_vehicle_operation(self):
        self.sources[E+'.rentals']=[dict(rental_id='X',vehicle_id='V',customer_id='G',hotel_booking_ref='missing',pickup_date=date(2024,1,2),return_date=date(2024,1,4),status='COMPLETED',agreed_vnd=Decimal(100))]
        t=self.transform();self.booking(t);self.assertEqual(t.build('F05'),[])
        self.assertEqual(t.rental_days[('V',date(2024,1,2))],['X'])
    def test_overlapping_rentals_all_rejected(self):
        r=dict(rental_id='X',vehicle_id='V',customer_id='G',hotel_booking_ref=None,pickup_date=date(2024,1,2),return_date=date(2024,1,4),status='COMPLETED',agreed_vnd=Decimal(100))
        self.sources[E+'.rentals']=[r,dict(r,rental_id='Y')];t=self.transform();self.booking(t)
        self.assertEqual(t.rental_conflicts,{'X','Y'});self.assertEqual(t.build('F05'),[])
    def test_missing_closures_not_open_zero(self):
        self.q['source_status'][E+'.closures']='UNAVAILABLE';t=self.transform()
        with self.assertRaises(Reject):t.complete(E+'.closures')
    def test_stay_overlap_rejects_both_nights(self):
        self.sources[H+'.stays']=[dict(stay_id=k,booking_room_id='BR',checkin_date=date(2024,1,2),checkout_date=date(2024,1,3)) for k in ['S1','S2']]
        t=self.transform();self.booking(t);t.available={('R',20240102)}
        self.assertEqual(t.build('F03'),[]);self.assertEqual(len(t.bad),2)
    def test_breakfast_checkout_uses_previous_night(self):
        self.sources[H+'.stays']=[dict(stay_id='ST',booking_room_id='BR',checkin_date=date(2024,1,2),checkout_date=date(2024,1,4))]
        self.sources[H+'.breakfast_entitlements']=[dict(entitlement_id='EN',booking_room_id='BR',service_date=date(2024,1,4),eligible_covers=2,redeemed_covers=1)]
        t=self.transform();self.booking(t);t.nights={('R',20240103):{'booking_room_id':'BR'}}
        self.assertEqual(t.build('F06')[0]['redeemed_covers'],1)
        t.nights={('R',20240104):{'booking_room_id':'BR'}};self.assertEqual(t.build('F06'),[])
    def test_dining_walkin_unknown_guest(self):
        self.sources[H+'.dining_orders']=[dict(dining_order_id='D',outlet_id='O',guest_id=None,booking_id=None,service_date=date(2024,1,2),meal='LUNCH',net_vnd=Decimal(50),covers=1,rating=4)]
        t=self.transform();self.booking(t);row=t.build('F07')[0]
        self.assertEqual((row['customer_profile_key'],row['booking_hotel_key']),(0,-1))
    def test_rescheduled_ticket_admission_retained(self):
        self.sources[E+'.ticket_orders']=[dict(ticket_order_id='TO',centre_id='C',customer_id='G')]
        self.sources[E+'.tickets']=[dict(ticket_id='T',ticket_order_id='TO',activity_id='A',status='RESCHEDULED')]
        self.sources[E+'.admissions']=[dict(admission_id='AD',ticket_id='T',entered_at=datetime(2024,1,2,1))]
        t=self.transform();t.orders={'TO'};t.capacity={(9,20240102):10};self.assertEqual(len(t.build('F09')),1)
        t.capacity={(9,20240102):0};self.assertEqual(t.build('F09'),[])
    def test_maintenance_union_uses_set(self):
        self.sources[E+'.vehicle_maintenance']=[dict(vehicle_work_id=k,vehicle_id='V',starts_on=date(2024,1,2),ends_on=date(2024,1,3)) for k in ['M1','M2']]
        self.assertEqual(len(self.transform().vehicle_maintenance),1)
    def test_stock_negative_prefix_rejects_day_and_suffix(self):
        self.dim('D14',14,supplier_id='SUP');self.dim('D15',15,item_id='ITEM')
        self.sources[H+'.purchase_orders']=[dict(purchase_order_id='PO',hotel_id='H',supplier_id='SUP',ordered_on=date(2024,1,1),expected_on=date(2024,1,2))]
        self.sources[H+'.purchase_lines']=[dict(purchase_line_id='PL',purchase_order_id='PO',item_id='ITEM',ordered_qty=Decimal('5.000'),unit_price_vnd=Decimal(10))]
        self.sources[H+'.receipts']=[dict(receipt_id='RC',purchase_line_id='PL',received_on=date(2024,1,2),expires_on=None,accepted_qty=Decimal('5.000'),rejected_qty=Decimal('0.000'))]
        base=dict(hotel_id='H',item_id='ITEM',receipt_id='RC',session_id=None,usage_area='OTHER')
        self.sources[H+'.stock_movements']=[dict(base,movement_id='M1',movement_type='IN',movement_date=date(2024,1,2),quantity=Decimal('5.000')),dict(base,movement_id='M2',movement_type='USE',movement_date=date(2024,1,3),quantity=Decimal('6.000')),dict(base,movement_id='M3',movement_type='IN',movement_date=date(2024,1,4),quantity=Decimal('2.000'))]
        t=self.transform();t.purchases={'PL'};t.receipts={'RC'}
        self.assertEqual([r['movement_id'] for r in t.build('F14')],['M1'])
        self.assertEqual(t.scope[0]['from_date'],20240103)
    def test_same_day_ledger_has_no_invented_intraday_order(self):
        self.test_stock_negative_prefix_rejects_day_and_suffix()
        movements=self.sources[H+'.stock_movements'];movements[1]['quantity']=Decimal('5.000');movements[1]['movement_date']=date(2024,1,2)
        # Deliberately list USE before IN: daily grain still closes at zero.
        self.sources[H+'.stock_movements']=[movements[1],movements[0]]
        t=self.transform();t.purchases={'PL'};t.receipts={'RC'}
        self.assertEqual(len(t.build('F14')),2);self.assertEqual(t.scope,[])

if __name__=='__main__':unittest.main(verbosity=2)
