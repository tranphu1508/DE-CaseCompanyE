"""Build a versioned column-level design, not DDL or an ETL implementation.

Inputs are the frozen logical model, diagram roles and v2 source contracts.
Run: python -X utf8 scripts/build-warehouse-design.py
"""
from pathlib import Path
import csv
import hashlib
import json
import re
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal

ROOT = Path(__file__).resolve().parents[1]
def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))
def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
def write(path, value):
    (ROOT / path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

INPUTS = ['config/dimensional_model_v1.json', 'config/dimensional_diagram_roles_v1.json',
          'config/kpi_contract_v1.json', 'config/generation_v2.json', 'generated/v2/contracts.json',
          'generated/v2/hotel_ops/schema.sql', 'generated/v2/entertainment_ops/schema.sql',
          'src/model.py', 'src/model_v2.py']
HASHES = {p: sha(p) for p in INPUTS}
model = read(INPUTS[0])
roles = read(INPUTS[1])
kpi = read(INPUTS[2])
generation = read(INPUTS[3])
contracts = read(INPUTS[4])
source = {f'{ns}.{t["name"]}.{c["name"]}': c
          for ns, ts in contracts.items() for t in ts for c in t['columns']}
tables = []

# Type aliases are shared by every target column. Lengths are contractual limits,
# checked against source values; never silently truncate strings or round quantities.
TYPES = {
 'KEY': ('NUMBER(18,0)', 'long', 'Khóa dương <= 999999999999999999; dành 0 và -1 cho dimension.'),
 'DATEKEY': ('NUMBER(8,0)', 'int', 'YYYYMMDD; 0 và -1 là thành viên đặc biệt.'),
 'COUNT': ('NUMBER(18,0)', 'long', 'Số nguyên không âm.'),
 'INT': ('NUMBER(10,0)', 'int', 'Số nguyên trong miền signed 32-bit.'),
 'FLAG': ('NUMBER(1,0)', 'int', '0 hoặc 1; không dùng BOOLEAN để giảm khác biệt driver.'),
 'MONEY': ('NUMBER(19,0)', 'decimal(19,0)', 'VND nguyên; không dùng float.'),
 'QTY': ('NUMBER(18,3)', 'decimal(18,3)', 'Lượng theo đơn vị cơ sở; không làm tròn âm thầm.'),
 'VALUE': ('NUMBER(38,3)', 'decimal(38,3)', 'Lượng nhân đơn giá, giữ 3 số lẻ đến lớp hiển thị.'),
 'DATE': ('DATE', 'date', 'Oracle DATE phải có giờ 00:00:00.'),
 'UTC': ('TIMESTAMP(6)', 'timestamp', 'Giá trị UTC không timezone; tên cột kết thúc _utc, session UTC.'),
 'ID': ('VARCHAR2(128 CHAR)', 'string', 'Mã nguồn giữ nguyên hoa/thường; không cắt hoặc chuẩn hóa tùy tiện.'),
 'CODE': ('VARCHAR2(64 CHAR)', 'string', 'Mã phân loại có danh mục kiểm soát.'),
 'TEXT': ('VARCHAR2(512 CHAR)', 'string', 'Unicode; Oracle dùng AL32UTF8.'),
 'HASH': ('VARCHAR2(64 CHAR)', 'string', 'SHA256 hex chữ thường, đúng 64 ký tự.'),
}

def col(name, typ, description, nullable=False, refs=None, aggregation='NONE', **extra):
    return dict(name=name, type=typ, nullable=nullable, description=description,
                source_references=refs or [], aggregation=aggregation, **extra)

def scol(ref, name=None, typ=None, **extra):
    s = source[ref]
    name = name or ref.rsplit('.', 1)[1]
    if typ is None:
        typ = {'BIGINT':'MONEY', 'INTEGER':'INT', 'DATE':'DATE',
               'TIMESTAMPTZ':'UTC', 'NUMERIC(12,3)':'QTY'}.get(s['sql_type'])
        if typ is None:
            typ = 'ID' if name.endswith(('_id','_ref','_code')) else 'TEXT'
    return col(name, typ, s['description'], s['nullable'], [ref], **extra)

AUDIT = [
 col('source_batch_id','ID','Batch của dữ liệu nguồn dùng tạo hoặc cập nhật dòng.'),
 col('transform_version','CODE','Phiên bản biến đổi, trỏ tới mã và cấu hình trong manifest.'),
 col('row_hash','HASH','Hash payload nghiệp vụ theo quy tắc canonical; loại khóa kỹ thuật và các cột audit.'),
 col('created_at_utc','UTC','Thời điểm tạo dòng đích; không phải ngày hiệu lực nghiệp vụ.'),
 col('updated_at_utc','UTC','Thời điểm cập nhật dòng đích gần nhất.'),
]

DIM_PK = {d['id']: roles['dimension_columns'][d['id']][0] for d in model['dimensions']}
DIM_SRC = {
 'D02': ('hotel_ops.sites','site_id site_name climate_region'),
 'D03': ('hotel_ops.hotels','hotel_id hotel_name stars site_id website_channel'),
 'D04': ('hotel_ops.rooms','room_id hotel_id room_type capacity base_rate_vnd'),
 'D06': ('hotel_ops.promotions','promotion_id promotion_name channel_id site_id sale_from sale_to stay_from stay_to discount_bps partner_share_bps cap_vnd'),
 'D08': ('hotel_ops.rate_plans','rate_plan_id hotel_id channel_id plan_name breakfast_included refundable'),
 'D09': ('hotel_ops.outlets','outlet_id hotel_id outlet_type capacity quality_profile'),
 'D11': ('entertainment_ops.centres','centre_id centre_name site_code'),
 'D12': ('entertainment_ops.activities','activity_id centre_id activity_name outdoor capacity_per_day'),
 'D13': ('entertainment_ops.vehicles','vehicle_id centre_id vehicle_type daily_rate_vnd'),
 'D14': ('hotel_ops.suppliers','supplier_id supplier_name category site_id delivery_format'),
 'D15': ('hotel_ops.items','item_id item_name specification base_unit shelf_life_days'),
 'D16': ('hotel_ops.assets','asset_id hotel_id room_id asset_type supplier_id'),
}
DIM_CHECKS = {
 'D01':['calendar_date duy nhất trên dòng NORMAL; date_key=YYYYMMDD.', 'day_of_week: Monday=1..Sunday=7; quarter=1..4; year/month/day lấy từ calendar_date.'],
 'D02':['site_id duy nhất trong hotel_ops.'],
 'D03':['stars IN (3,5); site_id phải tồn tại trong master sites.'],
 'D04':['capacity > 0; base_rate_vnd > 0; hotel_id hợp lệ.'],
 'D05':['commission_bps 0..10000 nếu có; entertainment channel không có mức hoa hồng thì NULL, không điền 0.'],
 'D06':['discount_bps và partner_share_bps 0..10000; cap_vnd >= 0; sale_to>=sale_from; stay_to>=stay_from.', 'NULL channel_id/site_id nghĩa là không giới hạn phạm vi tương ứng, không phải sai FK.'],
 'D07':['Không ghép hồ sơ khách theo tên/phone/email hoặc audit_only.', 'member_card_ref NULL cho khách không có thẻ và hồ sơ hotel; không suy ra trạng thái hội viên đang hiệu lực.'],
 'D08':['breakfast_included và refundable IN (0,1); hotel_id/channel_id hợp lệ.'],
 'D09':['outlet_type IN (RESTAURANT,BAR); capacity > 0; quality_profile là thang nguồn, không tự suy ra hạng sao.'],
 'D10':['meal_code IN (BREAKFAST,LUNCH,DINNER,BAR); khóa danh mục cố định 1,2,3,4 theo đúng thứ tự này.'],
 'D11':['site_code ánh xạ đúng một sites.site_id; tên giống nhau không phải bằng chứng ánh xạ.'],
 'D12':['outdoor IN (0,1); capacity_per_day > 0.'],
 'D13':['daily_rate_vnd > 0; centre_id hợp lệ.'],
 'D14':['site_id NULL cho nhà cung cấp phạm vi toàn chuỗi; category không suy ra nhà thầu thực hiện bảo trì.'],
 'D15':['base_unit phải giữ kèm quantity khi tổng hợp; shelf_life_days >= 0.'],
 'D16':['room_id có thể NULL; nếu có phải thuộc hotel_id của asset; supplier_id là bên bán tài sản.'],
}

for d in model['dimensions']:
    did=d['id']; pk=DIM_PK[did]
    columns=[col(pk,'DATEKEY' if did=='D01' else 'KEY','Khóa dimension dùng chung hai nhánh.')]
    columns += [col('source_system','CODE','Namespace nguồn; calendar/reference cho danh mục sinh.'),
                col('member_kind','CODE','NORMAL, UNKNOWN hoặc NOT_APPLICABLE.')]
    if did=='D01':
        columns += [col('calendar_date','DATE','Ngày lịch Gregorian.'),
                    *[col(n,'INT','Thuộc tính lịch sinh xác định.') for n in ['day','day_of_week','month','quarter','year']]]
        uk=['calendar_date']; namespace='calendar'
    elif did=='D05':
        columns += [col('channel_code','ID','Mã kênh nguồn.',refs=['hotel_ops.channels.channel_id','entertainment_ops.ticket_orders.sales_channel']),
                    scol('hotel_ops.channels.channel_name'),scol('hotel_ops.channels.channel_type'),
                    scol('hotel_ops.channels.commission_bps')]
        columns[-1]['nullable']=True
        columns[-3]['description']='Tên kênh hotel từ nguồn; entertainment dùng đúng sales_channel làm nhãn.'
        columns[-2]['description']='Loại kênh hotel từ nguồn; entertainment đặt ENTERTAINMENT_SALES.'
        uk=['source_system','channel_code']; namespace='hotel_ops hoặc entertainment_ops'
    elif did=='D07':
        columns += [col('source_customer_id','ID','ID hồ sơ trong từng nguồn.',refs=['hotel_ops.guests.guest_id','entertainment_ops.customers.customer_id'])]
        for n in ['full_name','phone','email']:
            columns.append(col(n,'TEXT','Thuộc tính hồ sơ khách giả lập; không dùng làm khóa toàn doanh nghiệp.',n!='full_name',
                               [f'hotel_ops.guests.{n}',f'entertainment_ops.customers.{n}']))
        columns.append(scol('entertainment_ops.customers.member_card_ref'))
        uk=['source_system','source_customer_id']; namespace='hotel_ops hoặc entertainment_ops'
    elif did=='D10':
        columns += [col('meal_code','CODE','Mã bữa theo danh mục bốn giá trị.'),col('meal_name','TEXT','Nhãn tiếng Việt tương ứng.')]
        uk=['meal_code']; namespace='reference'
    else:
        tab, fields=DIM_SRC[did]
        columns += [scol(tab+'.'+n,typ='FLAG' if n in ['breakfast_included','refundable','outdoor'] else None) for n in fields.split()]
        uk=['source_system',fields.split()[0]]; namespace=tab.split('.')[0]
    # Special dimension rows have no fake attributes. Enforce ordinary-row null
    # requirements conditionally, while allowing NULL in these physical columns.
    for c in columns:
        if c['name'] not in [pk,'source_system','member_kind']:
            c['required_for_normal_member']=not c['nullable']
            c['nullable']=True
    tables.append(dict(id=did,name=d['name'],kind='DIMENSION',grain='Một thành viên hiện hành cho mỗi business key trong namespace.',
                       primary_key=[pk],unique_keys=[uk],unique_scope='NORMAL rows; special rows identified by primary key',
                       namespace=namespace,columns=columns+AUDIT,checks=DIM_CHECKS[did],
                       history_policy='STATIC' if did in ['D01','D10'] else 'SCD_TYPE2',
                       update_policy='Upsert theo BK và registry; cập nhật khi row_hash thay đổi; không tự xóa thành viên vắng mặt.',
                       special_members={'0':'UNKNOWN','-1':'NOT_APPLICABLE'},scope='CORE'))

def srcfields(tab, fields):
    return [scol(tab+'.'+n) for n in fields.split()]
def measure(name,typ,desc,agg='SUM',refs=None):
    return col(name,typ,desc,refs=refs,aggregation=agg)
def direct_measures(tab, fields, typ, agg='SUM'):
    return [measure(n,typ,source[tab+'.'+n]['description'],agg,[tab+'.'+n]) for n in fields.split()]

DETAILS={
 'F01': dict(natural=['source_system','booking_id'],kind='CURRENT_TRANSACTION',
     columns=srcfields('hotel_ops.bookings','booking_id status updated_at')+
       direct_measures('hotel_ops.bookings','gross_vnd discount_vnd customer_due_vnd company_share_vnd partner_share_vnd commission_vnd','MONEY')+
       [measure('booking_count','COUNT','Luôn bằng 1.')],
     checks=['status IN (COMPLETED,CANCELLED,NO_SHOW).','arrival < departure; booked_on <= arrival.',
             'discount_vnd=company_share_vnd+partner_share_vnd; customer_due_vnd=gross_vnd-discount_vnd; các khoản tiền >= 0.']),
 'F02':dict(natural=['room_key','date_key'],kind='PERIODIC_SNAPSHOT',columns=[measure(n,'FLAG',desc) for n,desc in [
     ('inventory_day','1 cho mỗi phòng thuộc danh mục trong kỳ công suất.'),('blocked_day','1 nếu có ít nhất một bảo trì chặn ngày.'),('available_day','1-blocked_day.')]],
     checks=['inventory_day=1; blocked_day IN (0,1); available_day=inventory_day-blocked_day.', 'Gộp union khoảng bảo trì trước khi tạo row; không đếm nhiều lần một room-day.']),
 'F03':dict(natural=['room_key','service_date_key'],kind='EXPANDED_EVENT',columns=srcfields('hotel_ops.stays','stay_id')+
     srcfields('hotel_ops.booking_rooms','booking_room_id booking_id')+[measure('occupied_night','FLAG','1 cho mỗi đêm thực ở của booking COMPLETED.')],
     checks=['Không trùng room_key/service_date_key, kể cả khác stay_id; overlap phải báo lỗi trước DISTINCT.',
             'Đêm ở thuộc [checkin,checkout); không trùng ngày phòng bị chặn; phòng/rate plan/booking cùng hotel.']),
 'F04':dict(natural=['source_system','ticket_order_id'],kind='CURRENT_TRANSACTION',columns=srcfields('entertainment_ops.ticket_orders','ticket_order_id hotel_booking_ref')+
     direct_measures('entertainment_ops.ticket_orders','gross_vnd refunded_vnd','MONEY')+[measure('net_ticket_vnd','MONEY','gross_vnd-refunded_vnd.')],
     checks=['gross_vnd>=refunded_vnd>=0; net_ticket_vnd=gross_vnd-refunded_vnd.',
             'Tham chiếu booking có giá trị phải tồn tại; các khóa referral đồng loạt -1 khi không có booking_ref.']),
 'F05':dict(natural=['source_system','rental_id'],kind='CURRENT_TRANSACTION',columns=srcfields('entertainment_ops.rentals','rental_id hotel_booking_ref status')+
     direct_measures('entertainment_ops.rentals','agreed_vnd','MONEY'),
     checks=['status IN (COMPLETED,CANCELLED); pickup < return; agreed_vnd>=0.', 'B03 chỉ dùng COMPLETED; không nhân agreed_vnd theo ngày xe.']),
 'F06':dict(natural=['source_system','entitlement_id'],extra_unique=[['source_system','booking_room_id','service_date_key']],kind='TRANSACTION',
     columns=srcfields('hotel_ops.breakfast_entitlements','entitlement_id booking_room_id')+
     direct_measures('hotel_ops.breakfast_entitlements','eligible_covers redeemed_covers','COUNT'),
     checks=['eligible_covers>=redeemed_covers>=0; booking COMPLETED; meal=BREAKFAST.',
             'Một booking_room/service_date duy nhất; đúng một RESTAURANT trong hotel; entitlement thuộc ngày phục vụ hợp lệ của lưu trú.']),
 'F07':dict(natural=['source_system','dining_order_id'],kind='TRANSACTION',columns=srcfields('hotel_ops.dining_orders','dining_order_id booking_id')+
     direct_measures('hotel_ops.dining_orders','net_vnd','MONEY')+direct_measures('hotel_ops.dining_orders','covers','COUNT')+
     [measure('rating_sum','COUNT','rating nguồn trong 1..5; nguồn v2 bắt buộc có rating.',refs=['hotel_ops.dining_orders.rating']),measure('rating_count','COUNT','1 cho hóa đơn có rating hợp lệ; v2 luôn 1.')],
     checks=['net_vnd>=0; covers>=0; rating_sum BETWEEN 1 AND 5; rating_count=1.',
             'Không suy guest từ booking khi guest_id nguồn NULL; service_hotel lấy từ outlet, booking_hotel từ booking.']),
 'F08':dict(natural=['outlet_key','service_date_key','meal_key'],extra_unique=[['source_system','session_id']],kind='PERIODIC_SNAPSHOT',
     columns=srcfields('hotel_ops.meal_sessions','session_id')+direct_measures('hotel_ops.meal_sessions','actual_covers','COUNT')+
     direct_measures('hotel_ops.meal_sessions','ingredient_cost_vnd','MONEY'),
     checks=['meal IN (BREAKFAST,DINNER); actual_covers>=0; ingredient_cost_vnd>=0.', 'Một outlet/ngày/bữa; không tự gộp hai session_id trùng grain.']),
 'F09':dict(natural=['source_system','admission_id'],kind='TRANSACTION',columns=srcfields('entertainment_ops.admissions','admission_id ticket_id entered_at')+
     [measure('admission_count','COUNT','1 cho mỗi admission, không phải một ticket.')],
     checks=['Ngày vào lấy sau chuyển UTC sang Asia/Ho_Chi_Minh; không thay bằng valid_date.',
             'Activity và centre của ticket/order nhất quán; lượt vào ngày đóng cửa hoặc vượt capacity phải được kiểm tra.']),
 'F10':dict(natural=['activity_key','date_key'],kind='PERIODIC_SNAPSHOT',columns=[
     measure('nominal_capacity','COUNT','capacity_per_day của activity.',refs=['entertainment_ops.activities.capacity_per_day']),
     measure('is_closed','FLAG','1 nếu tồn tại closure cùng activity/date.','NONE'),
     measure('available_capacity','COUNT','nominal_capacity*(1-is_closed).')],
     checks=['nominal_capacity>0; is_closed IN (0,1); available_capacity=nominal_capacity*(1-is_closed).']),
 'F11':dict(natural=['vehicle_key','date_key'],kind='PERIODIC_SNAPSHOT',columns=[measure(n,'FLAG',desc) for n,desc in [
     ('inventory_day','1 trong lịch công suất.'),('maintenance_day','1 nếu thuộc union ngày bảo trì xe.'),
     ('available_day','1-maintenance_day.'),('rented_day','1 nếu thuộc một rental COMPLETED.')]],
     checks=['inventory_day=1; available_day=1-maintenance_day; rented_day<=available_day.',
             'Hai rental cùng vehicle-day là lỗi; không DISTINCT để che overlap.']),
 'F12':dict(natural=['source_system','purchase_line_id'],kind='TRANSACTION',columns=srcfields('hotel_ops.purchase_lines','purchase_line_id purchase_order_id')+
     direct_measures('hotel_ops.purchase_lines','ordered_qty','QTY','SUM_SAME_UNIT')+direct_measures('hotel_ops.purchase_lines','unit_price_vnd','MONEY','NONE'),
     checks=['ordered_qty>0; unit_price_vnd>=0; ordered_date<=expected_date.',
             'B06 cohort theo expected_date và A; dòng chưa receipt vẫn tồn tại.']),
 'F13':dict(natural=['source_system','receipt_id'],kind='TRANSACTION',columns=srcfields('hotel_ops.receipts','receipt_id purchase_line_id')+
     direct_measures('hotel_ops.receipts','accepted_qty rejected_qty','QTY','SUM_SAME_UNIT')+
     [measure('late_accepted_qty','QTY','accepted_qty nếu received_date>expected_date, ngược lại 0.','SUM_SAME_UNIT')],
     checks=['accepted_qty>=0; rejected_qty>=0; late_accepted_qty IN (0,accepted_qty) theo ngày nhận/hẹn.',
             'Không cộng receipt feed bên ngoài; expires_on NULL là chưa biết hạn dùng (date_key=0).']),
 'F14':dict(natural=['source_system','movement_id'],kind='TRANSACTION',columns=srcfields('hotel_ops.stock_movements','movement_id receipt_id session_id movement_type usage_area')+
     direct_measures('hotel_ops.stock_movements','quantity','QTY','SUM_SAME_UNIT')+
     [measure(n,'QTY',desc,'SUM_SAME_UNIT') for n,desc in [('signed_qty','+quantity nếu IN; -quantity nếu USE/WASTE.'),
     ('in_qty','quantity nếu IN, ngược lại 0.'),('use_qty','quantity nếu USE, ngược lại 0.'),('waste_qty','quantity nếu WASTE, ngược lại 0.')]]+
     [measure('unit_price_vnd','MONEY','Giá lô từ purchase_line của receipt.','NONE',['hotel_ops.purchase_lines.unit_price_vnd']),
      measure('movement_value_vnd','VALUE','quantity*unit_price_vnd; đây là trị tuyệt đối, lọc movement_type khi tính WASTE/IN.')],
     checks=['movement_type IN (IN,USE,WASTE); quantity>=0; signed_qty=in_qty-use_qty-waste_qty.',
             'Hotel/item khớp lô receipt và purchase order; balance cộng dồn theo lô không âm.', 'session_id optional; không suy usage_area thành dimension kho.']),
 'F15':dict(natural=['source_system','receipt_id','hotel_key','item_key','snapshot_date_key'],kind='OPTIONAL_AGGREGATE',columns=srcfields('hotel_ops.receipts','receipt_id')+
     [measure('closing_qty','QTY','SUM signed_qty tới hết snapshot_date.','SEMI_ADDITIVE_DATE_SAME_UNIT'),
      measure('closing_value_vnd','VALUE','closing_qty*giá lô.','SEMI_ADDITIVE_DATE')]+
     [measure(n,'QTY','Lượng của loại tương ứng trong đúng snapshot_date.','SUM_SAME_UNIT') for n in ['in_qty','use_qty','waste_qty']],
     checks=['closing_qty>=0; cuối ngày d=cuối ngày d-1+in_qty-use_qty-waste_qty.',
             'Giữ lô còn tồn cả ngày không biến động; không SUM số dư qua ngày hoặc cộng F14+F15.']),
 'F16':dict(natural=['source_system','maintenance_id'],kind='CURRENT_TRANSACTION',columns=srcfields('hotel_ops.maintenance','maintenance_id work_type status')+
     direct_measures('hotel_ops.maintenance','cost_vnd','MONEY'),
     checks=['start_date<end_date; cost_vnd>=0; work_type IN (BREAKDOWN,PLANNED); v2 status=COMPLETED.',
             'KPI chi phí lấy COMPLETED theo end_date; room_key=-1 cho tài sản không thuộc phòng.']),
 'F17':dict(natural=['site_key','weather_date_key'],extra_unique=[['source_system','weather_id']],kind='CONTEXT',columns=srcfields('hotel_ops.weather_daily','weather_id provenance')+
     [measure('temperature_c','INT','Nhiệt độ giả lập theo cụm/ngày.','AVG_SITE_DAY',['hotel_ops.weather_daily.temperature_c']),
      measure('rain_mm','INT','Lượng mưa ngày; chỉ cộng qua ngày trong cùng site.','SUM_DATE_WITHIN_SITE',['hotel_ops.weather_daily.rain_mm']),
      measure('severe_weather','FLAG','Cờ thời tiết cực đoan; dùng lọc, không cộng như lượng mưa.','NONE',['hotel_ops.weather_daily.severe_weather'])],
     checks=['Duy nhất site/date trước join; rain_mm>=0; severe_weather IN (0,1).', 'Không SUM nhiệt độ hoặc nhân bản weather khi join admission.']),
}

OPTIONAL_POLICY={
 ('F01','promotion_key'):'-1: booking không dùng promotion.',
 ('F07','customer_profile_key'):'0: hóa đơn không xác định khách; không tự điền guest từ booking.',
 ('F07','booking_hotel_key'):'-1: hóa đơn không gắn booking.',
 ('F13','expires_date_key'):'0: nguồn chưa cung cấp hạn dùng; không suy ra không hết hạn.',
 ('F16','room_key'):'-1: asset ở khu chung, không gắn phòng.',
}
for f in model['facts']:
    fid=f['id']; detail=DETAILS[fid]
    columns=[col('fact_key','KEY','Khóa kỹ thuật từ registry theo natural key; không thay ràng buộc grain.'),
             col('source_system','CODE','Namespace định danh các ID nguồn trong dòng.')]
    for r in roles['foreign_key_roles']:
        if r['fact']!=fid: continue
        special=OPTIONAL_POLICY.get((fid,r['fk']), '-1: dịch vụ độc lập không có booking_ref.') if r['conditional'] else 'Không cho khóa đặc biệt trên dữ liệu công bố.'
        columns.append(col(r['fk'],'DATEKEY' if r['dimension']=='D01' else 'KEY','Vai trò dimension theo sơ đồ đã chốt.',
                           dimension=r['dimension'],references=f'{r["dimension"]}.{DIM_PK[r["dimension"]]}',missing_policy=special))
    for c in detail['columns']:
        if c['name']=='updated_at': c['name']='source_updated_at_utc'
        elif c['type']=='UTC' and not c['name'].endswith('_utc'): c['name'] += '_utc'
        columns.append(c)
    tables.append(dict(id=fid,name=f['name'],kind=detail['kind'],grain=f['grain'],primary_key=['fact_key'],
                       unique_keys=[detail['natural']]+detail.get('extra_unique',[]),columns=columns+AUDIT,
                       history_policy='FINAL_SNAPSHOT_RESTATEMENT',scope=f['scope'],
                       source_tables=list(f['source_columns']),checks=detail['checks']+[f['rules']],
                       date_roles=f['date_roles'],namespace='entertainment_ops' if fid in ['F04','F05','F09','F10','F11'] else 'hotel_ops',
                       update_policy='Merge theo natural key; tính lại tập grain bị ảnh hưởng khi correction. Không append revision như giao dịch mới.'))

# Links retain source identifiers and explicit namespaces. No direct fact-to-fact
# referential constraint is introduced; these are controlled joins, not SUM paths.
LINKS=[
 dict(id='L01',name='BridgeBookingRoom',kind='BRIDGE',grain='Một booking_room_id trong hotel_ops.',
      primary_key=['source_system','booking_room_id'],unique_keys=[['source_system','booking_room_id']],
      columns=[col('source_system','CODE','hotel_ops')]+srcfields('hotel_ops.booking_rooms','booking_room_id booking_id')+
      [col('room_key','KEY','Phòng của dòng booking.',dimension='D04',references='D04.room_key'),col('rate_plan_key','KEY','Gói giá của dòng booking.',dimension='D08',references='D08.rate_plan_key')],
      checks=['booking_id tồn tại ở booking nguồn; room và rate plan cùng hotel với booking.', 'Dùng EXISTS hoặc COUNTD; không mang tiền booking và không cấp allocation weight.']),
 dict(id='L02',name='BridgeRoomDayMaintenance',kind='BRIDGE',grain='Một phòng/ngày/công việc bảo trì.',
      primary_key=['room_key','date_key','source_system','maintenance_id'],unique_keys=[['room_key','date_key','source_system','maintenance_id']],
      columns=[col('source_system','CODE','hotel_ops'),scol('hotel_ops.maintenance.maintenance_id'),
      col('room_key','KEY','Phòng chịu ảnh hưởng.',dimension='D04',references='D04.room_key'),col('date_key','DATEKEY','Ngày trong [starts_on,ends_on).',dimension='D01',references='D01.date_key')],
      checks=['Chỉ asset có room; mỗi cặp room/date/work đúng một lần.', 'F02 dùng EXISTS trên room/date; không SUM cost qua bridge.']),
 dict(id='L03',name='ValidatedBookingServiceLink',kind='VALIDATION_VIEW',grain='Một service_type/service_id có booking_ref hợp lệ.',
      primary_key=['service_source_system','service_type','service_id'],unique_keys=[['service_source_system','service_type','service_id']],
      columns=[col('service_source_system','CODE','entertainment_ops'),col('service_type','CODE','TICKET_ORDER hoặc RENTAL'),
      col('service_id','ID','ID ticket_order hoặc rental.'),col('booking_source_system','CODE','hotel_ops'),col('booking_id','ID','Booking đích đã kiểm chứng.')],
      checks=['Mỗi dịch vụ tối đa một booking; thiếu ref không có dòng link; ref có giá trị nhưng sai đưa quarantine.',
              'Kiểm chứng tồn tại ref độc lập với eligibility B03; cohort B03 tiếp tục lọc booking COMPLETED.']),
 dict(id='L04',name='SiteCrosswalk',kind='VALIDATION_VIEW',grain='Một centre ánh xạ đúng một site.',
      primary_key=['centre_source_system','centre_id'],unique_keys=[['centre_source_system','centre_id']],
      columns=[col('centre_source_system','CODE','entertainment_ops'),scol('entertainment_ops.centres.centre_id'),
      col('site_source_system','CODE','hotel_ops'),col('site_id','ID','centres.site_code trùng sites.site_id.',refs=['entertainment_ops.centres.site_code','hotel_ops.sites.site_id'])],
      checks=['Không yêu cầu một site chỉ có một centre bằng UNIQUE; bốn centre/bốn site là dữ liệu case.', 'Không suy ánh xạ bằng vị trí hoặc tên gần giống.']),
]
for t in LINKS:
    t.update(scope='CORE',history_policy='CURRENT_VALIDATED_LINK',update_policy='Tạo lại hoặc merge theo khóa từ cùng batch nguồn.',columns=t['columns']+AUDIT)
tables.extend(LINKS)

POLICIES={
 'architecture':'Fact constellation, star per fact; thuộc tính hotel_id/site_id trong dimension không trở thành FK dimension-to-dimension.',
 'time':'Ngày nghiệp vụ Asia/Ho_Chi_Minh; timestamp UTC ở cột _utc; mọi khoảng công suất/lưu trú [S,E).',
 'capacity_period':{'start':generation['date_from'],'end_exclusive':str(date.fromisoformat(generation['date_to'])+timedelta(days=1)),
                    'rule':'Danh mục phòng/hoạt động/xe tồn tại toàn kỳ mô phỏng. Không mở công suất từ ngày booked_on năm 2023.'},
 'date_coverage':'Lấy min/max của TẤT CẢ cột DATE và ngày địa phương của TIMESTAMPTZ trong hai DB v2; thêm ngày trước capacity start cho số dư đầu kỳ. Sinh liên tục từ 01/01 năm min tới 31/12 năm max; không sinh holiday/season khi chưa có rule version.',
 'special_members':'Mỗi dimension có key 0 UNKNOWN và -1 NOT_APPLICABLE; source_system=system; member_kind riêng; các thuộc tính NULL. Nhãn UI lấy từ member_kind hoặc theo vai trò (ví dụ Không khuyến mãi). Không tạo ngày giả 1900.',
 'dimension_constraints':'Ràng buộc key=0 tương ứng UNKNOWN, key=-1 tương ứng NOT_APPLICABLE, key>0 tương ứng NORMAL. Cột required_for_normal_member được CHECK theo member_kind. UK của BK chỉ trên NORMAL: Oracle dự kiến unique index trên CASE WHEN member_kind=NORMAL THEN từng cột BK END; không dùng UK ghép trực tiếp trên hai dòng đặc biệt có BK NULL. Iceberg kiểm tra cùng điều kiện bằng pipeline.',
 'bad_references':'NULL được xử lý theo từng cột; ID có giá trị nhưng không tìm thấy hoặc mâu thuẫn -> quarantine. Không đổi invalid reference thành 0/-1 để che lỗi.',
 'missing_measures':'Không tự NULL->0 cho tiền/lượng bắt buộc. 0 chỉ từ phép tính có ý nghĩa (không có closure, không USE), sau kiểm tra đủ dữ liệu.',
 'null_strings':'CSV nguồn dùng token \\N cho SQL NULL: giải mã ở ranh giới đọc CSV, không giữ thành chuỗi mã hoặc ngày. Đồng nhất chuỗi rỗng thành NULL trước cả hai nhánh; giữ nguyên nội dung mã nguồn khác rỗng. Whitespace-only trong mã bắt buộc -> lỗi. Không dùng sentinel rỗng cho BK.',
 'key_registry':'Registry dùng chung cả hai nhánh: (entity_id, canonical_natural_key) UNIQUE -> surrogate_key UNIQUE trong entity. Canonical key là JSON array có thứ tự, UTF-8, không ghép chuỗi bằng dấu phân cách. Lần đầu sort key rồi cấp 1..N; batch sau giữ mapping và chỉ cấp mới append. Không tái đánh số bằng ROW_NUMBER mỗi batch; không dùng hash cắt ngắn làm PK. Date YYYYMMDD; Meal mã 1..4 cố định. Registry được version/hash trong manifest.',
 'hash_canonicalization':'row_hash SHA256 của JSON array theo thứ tự cột nghiệp vụ hợp đồng, null là JSON null, date ISO, timestamp UTC microseconds, decimal chuỗi fixed-scale. Loại PK surrogate, audit, FK surrogate; dùng natural reference identities thay FK. Không phụ thuộc định dạng JSON hay số thực mặc định của engine.',
 'history':'V2 Type 1 cho danh mục, current snapshot cho fact; cập nhật sửa lại kỳ nghiệp vụ cũ. created_at/updated_at là thời điểm ETL, không phải valid_from/valid_to. Booking revisions là evidence đối soát, không là các lần bán bổ sung.',
 'scd2_extension':'Nếu mở rộng phải có source effective_from, lịch sử có thứ tự, nonoverlap [from,to), current flag, mỗi version có SK và fact lookup as-of. Không thêm cột SCD2 rỗng rồi gọi là đã lưu lịch sử.',
 'delete_policy':'Không suy hard delete từ file thiếu. Full snapshot phải có manifest đầy đủ; dựng candidate snapshot mới, so sánh thay đổi và xác nhận counts. Incremental cần tombstone/CDC rõ ràng. Giữ registry và audit; không xóa nguồn.',
 'late_data':'Lỗi thiếu parent chờ parent cùng cutoff rồi xử lý lại quarantine. Correction booking tính lại F01, các role/cohort F04/F05/F07 và facts liên quan; maintenance sửa cả old/new affected dates của F02/bridge; rental/closure tương tự F11/F10; movement cũ làm lại F15 từ ngày sửa đến cuối kỳ.',
 'aggregation':'Không có tỷ lệ materialized; tính ratio bằng tổng tử/mẫu, mẫu 0 trả NULL/BLANK. SUM tiền ở grain gốc; lượng SUM trong cùng base_unit; F15 số dư chỉ snapshot cùng ngày; weather không cộng khác site; các fact được aggregate riêng trước drill-across.',
 'physical_baseline':'Oracle PK/UK/FK và CHECK khi biểu diễn được; Iceberg kiểm tra tương đương bằng pipeline trước publish, không coi identifier fields là PK enforcement. Khởi đầu bảng không partition ở cả hai nhánh; đề xuất partition/index chỉ sau chốt phiên bản và đo workload. Không bật nén/parallel/partition phụ thuộc edition trước kiểm chứng môi trường.',
 'physical_names':'Tên bảng và cột lowercase snake_case, không quoted mixed-case identifiers. FactBooking -> fact_booking, DimCustomerProfile -> dim_customer_profile. Chọn schema/catalog riêng ở bước môi trường; tên entity trong sơ đồ là tên logic.',
 'publication':'Đề xuất: quarantine lỗi ảnh hưởng KPI và chặn publish toàn candidate batch; giữ bản đạt gần nhất. Dòng feed ngoài lỗi đã được lake quarantine đúng hợp đồng không chặn nếu chỉ làm đối soát và có kết quả expected quarantine. Source/contract/hash/cutoff thiếu hoặc lệch -> fail batch. Chưa có bản đạt thì hiển thị Chưa có dữ liệu đã nghiệm thu.',
 'cross_table_consistency':'Publication manifest chỉ trỏ bộ bảng đã kiểm tra và cùng snapshot nguồn; không giả định nhiều commit Iceberg là một transaction. Candidate namespace/tables hoặc manifest snapshot IDs; Oracle candidate schema/version và publish pointer. Cách hiện thực chọn ở bước môi trường/DDL.',
 'scope':'16 dimension, 16 fact/context bắt buộc + F15 aggregate tùy chọn, 2 bridge + 2 validation views. Chưa thêm fact membership/payment/menu/revision; các nguồn đó giữ ở lake để đối soát. Không đưa audit_only vào analytic contract.',
}

POLICY_LABELS={
 'architecture':'Kiến trúc', 'time':'Thời gian', 'capacity_period':'Kỳ tính công suất',
 'date_coverage':'Phạm vi lịch ngày', 'special_members':'Thành viên đặc biệt',
 'dimension_constraints':'Ràng buộc dimension', 'bad_references':'Tham chiếu không hợp lệ',
 'missing_measures':'Số đo bị thiếu', 'null_strings':'Chuỗi rỗng và giá trị NULL',
 'key_registry':'Cấp và giữ khóa', 'hash_canonicalization':'Chuẩn hóa trước khi tính hash',
 'history':'Lịch sử dữ liệu', 'scd2_extension':'Điều kiện mở rộng SCD2',
 'delete_policy':'Bản ghi biến mất và xóa dữ liệu', 'late_data':'Dữ liệu đến muộn và sửa đổi',
 'aggregation':'Quy tắc tổng hợp', 'physical_baseline':'Cấu hình vật lý ban đầu',
 'physical_names':'Tên vật lý', 'publication':'Công bố dữ liệu',
 'cross_table_consistency':'Tính nhất quán giữa các bảng', 'scope':'Phạm vi triển khai',
}
for table in tables:
    table['physical_name']=re.sub(r'(?<!^)(?=[A-Z])','_',table['name']).lower()

DECISIONS = [
 {'id':'Q01','topic':'Lịch sử dimension','status':'USER_CONFIRMED','confirmed_on':'2026-10-13','default':'SCD Type 2, v2 một phiên bản khởi tạo; không sinh thêm lịch sử.'},
 {'id':'Q02','topic':'Công bố batch có lỗi','status':'USER_CONFIRMED','confirmed_on':'2026-10-13','default':'Công bố phần hợp lệ, báo thiếu và ảnh hưởng KPI.'},
]
decision_path=ROOT/'config/warehouse_design_decisions_v1.json'
if decision_path.exists(): DECISIONS=json.loads(decision_path.read_text(encoding='utf-8'))
else: write('config/warehouse_design_decisions_v1.json',DECISIONS)

# User-confirmed refinement 1.1 supersedes the draft's Type 1 and strict publish.
# Preserve original source data, KPI formulas and diagram files as baselines.
SCD_COLUMNS=[
 col('valid_from_utc','UTC','Bắt đầu hiệu lực phiên bản, inclusive; mốc bootstrap v2 theo giả định.'),
 col('valid_to_utc','UTC','Kết thúc hiệu lực exclusive; NULL là chưa có điểm kết thúc.',True),
 col('is_current','FLAG','1 khi valid_to_utc NULL; tối đa một phiên bản current mỗi BK.'),
 col('version_no','COUNT','Số phiên bản tăng dần theo valid_from, bắt đầu 1 trong v2.'),
 col('effective_time_basis','CODE','BOOTSTRAP_ASSUMPTION, SOURCE_EFFECTIVE hoặc OBSERVED_AT; không đánh đồng thời điểm quan sát với hiệu lực thật.'),
]
for t in tables:
    if t.get('history_policy')!='SCD_TYPE2': continue
    bk=list(t['unique_keys'][0])
    t['business_key']=bk
    t['grain']='Một phiên bản có hiệu lực của một business key trong namespace nguồn.'
    t['unique_keys']=[bk+['valid_from_utc'],bk+['version_no']]
    t['conditional_unique_keys']=[dict(columns=bk,condition="member_kind='NORMAL' AND is_current=1")]
    t['unique_scope']='NORMAL rows; BK can repeat across nonoverlapping versions; special rows unique by SK'
    t['columns']=t['columns'][:-len(AUDIT)]+[dict(c) for c in SCD_COLUMNS]+t['columns'][-len(AUDIT):]
    t['update_policy']='Không đổi payload thì giữ SK; đổi thuộc tính theo dõi tại t thì đóng phiên bản cũ valid_to=t, is_current=0; thêm phiên bản mới có SK mới, valid_from=t, valid_to=NULL, is_current=1. Cùng batch replay không sinh thêm phiên bản.'
    t['tracked_attributes']=[c['name'] for c in t['columns'] if c.get('required_for_normal_member') is not None and c['name'] not in bk]
    t['checks'] += ['version_no>=1; is_current IN (0,1); is_current=1 iff valid_to_utc IS NULL.',
                   'valid_to NULL hoặc valid_from<valid_to; khoảng [valid_from,valid_to) của cùng BK không chồng nhau.',
                   'Dòng NORMAL cùng BK chỉ một current; cùng effective timestamp mà payload khác -> quarantine, không tự lấy dòng cuối.',
                   'Hai dòng đặc biệt 0/-1 không version hóa: version_no=1, current=1, valid_to=NULL.']
    t['checks']=[r.replace('site_id duy nhất trong hotel_ops.','site_id xác định BK trong hotel_ops; có thể lặp qua các phiên bản.') for r in t['checks']]

# Uniqueness of a physical room/day must survive replacement of its SCD SK.
DURABLE_GRAINS={
 'F02':('hotel_ops.rooms.room_id',['source_system','room_id','date_key']),
 'F03':('hotel_ops.rooms.room_id',['source_system','room_id','service_date_key']),
 'F08':('hotel_ops.outlets.outlet_id',['source_system','outlet_id','service_date_key','meal_key']),
 'F10':('entertainment_ops.activities.activity_id',['source_system','activity_id','date_key']),
 'F11':('entertainment_ops.vehicles.vehicle_id',['source_system','vehicle_id','date_key']),
 'F17':('hotel_ops.sites.site_id',['source_system','site_id','weather_date_key']),
}
ASOF={
 'F01':'booked_date_key tại 00:00 giờ Việt Nam; mọi dimension không phải Date theo thời điểm đặt.',
 'F02':'date_key tại 00:00 giờ Việt Nam.',
 'F03':'service_date_key tại 00:00 giờ Việt Nam.',
 'F04':'ordered_date_key cho service_site/centre/customer/ticket_channel; booking_site/referral_hotel/booking_channel kế thừa phiên bản booking tương ứng F01.',
 'F05':'pickup_date_key cho service_site/centre/customer/vehicle; booking_site/referral_hotel/booking_channel kế thừa phiên bản booking tương ứng F01.',
 'F06':'service_date_key tại 00:00 giờ Việt Nam.',
 'F07':'service_date_key cho service_site/service_hotel/customer/outlet; booking_hotel kế thừa phiên bản booking tương ứng F01.',
 'F08':'service_date_key tại 00:00 giờ Việt Nam.',
 'F09':'entered_at_utc chính xác, không chỉ ngày.',
 'F10':'date_key tại 00:00 giờ Việt Nam.',
 'F11':'date_key tại 00:00 giờ Việt Nam.',
 'F12':'ordered_date_key tại 00:00 giờ Việt Nam.',
 'F13':'received_date_key tại 00:00 giờ Việt Nam.',
 'F14':'movement_date_key tại 00:00 giờ Việt Nam.',
 'F15':'snapshot_date_key tại 00:00 giờ Việt Nam; số dư đo cuối ngày, phân loại danh mục tại đầu ngày.',
 'F16':'start_date_key tại 00:00 giờ Việt Nam; ngày ghi nhận KPI chi phí vẫn là end_date_key.',
 'F17':'weather_date_key tại 00:00 giờ Việt Nam.',
}
for t in tables:
    tid=t['id']
    if tid in DURABLE_GRAINS:
        ref, uk=DURABLE_GRAINS[tid]
        t['columns'].insert(2,scol(ref))
        t['unique_keys'][0]=uk
    if tid=='F15':
        t['columns'][2:2]=[scol('hotel_ops.hotels.hotel_id'),scol('hotel_ops.items.item_id')]
        t['unique_keys'][0]=['source_system','receipt_id','hotel_id','item_id','snapshot_date_key']
    if tid in ASOF:
        t['dimension_asof']=ASOF[tid]
        t['checks'].append('Lookup dimension NORMAL theo namespace + BK và valid_from <= t < valid_to (NULL là vô hạn); đúng một phiên bản. Thiếu/trùng phiên bản -> quarantine dòng phụ thuộc, không lấy current thay thế.')
    if tid=='L01':
        t['dimension_asof']='bookings.booked_on của booking liên quan, thống nhất F01.'
    if tid=='L02':
        t['columns'].insert(2,scol('hotel_ops.rooms.room_id'))
        t['primary_key']=t['unique_keys'][0]=['source_system','room_id','date_key','maintenance_id']
        t['dimension_asof']='date_key tại 00:00 giờ Việt Nam, thống nhất F02.'
    if tid=='F03':
        t['checks']=[r.replace('Không trùng room_key/service_date_key','Không trùng namespace/room_id/service_date_key') for r in t['checks']]

POLICIES.update({
 'dimension_constraints':'SCD2: PK là SK của phiên bản; UK NORMAL=(namespace,BK,valid_from) và (namespace,BK,version_no); UK có điều kiện cho BK với is_current=1. Oracle dùng unique index có CASE để loại dòng đặc biệt; Iceberg kiểm tra cùng quy tắc trước công bố. Kiểm tra nonoverlap riêng. D01/DimDate và D10/DimMeal giữ danh mục STATIC. Không đặt UNIQUE BK trên toàn bộ lịch sử.',
 'key_registry':'Registry dùng chung hai nhánh. Với SCD2, canonical key gồm entity_id, namespace, BK và valid_from_utc; mỗi phiên bản có SK riêng, không dùng row_hash vì thuộc tính có thể đổi A->B->A. Với fact, khóa tự nhiên dùng ID nguồn bền vững và ngày để không nhân bản grain khi dimension đổi phiên bản. Registry append-only, không tái đánh số. Date YYYYMMDD; Meal 1..4 cố định.',
 'hash_canonicalization':'SHA256 của payload nghiệp vụ canonical theo thứ tự cột; loại SK, audit và năm cột điều khiển SCD. Dimension hash chỉ tracked_attributes, NULL phân biệt giá trị; fact dùng BK của reference thay SK. Date ISO, timestamp UTC microseconds, decimal chuỗi fixed-scale. Hash không đổi thì không tạo version mới; cùng batch và effective time chạy lại idempotent.',
 'history':'14 dimension nghiệp vụ dùng SCD Type 2; DimDate và DimMeal STATIC. V2 chưa có sự kiện đổi danh mục nên mỗi BK chỉ có version_no=1, is_current=1; không sinh thêm dữ liệu. Cột effective_time_basis phân biệt giả định khởi tạo, hiệu lực từ nguồn và thời điểm quan sát. Fact vẫn lưu trạng thái cuối snapshot theo KPI contract; SCD2 dimension không biến fact thành event history.',
 'scd2_extension':'Bootstrap v2 giả định danh mục hiện hành áp dụng từ 2023-01-01 00:00 Asia/Ho_Chi_Minh (2022-12-31T17:00:00 UTC), valid_to=NULL, basis=BOOTSTRAP_ASSUMPTION; đây là giả định mô phỏng, không phải lịch sử nguồn. Dữ liệu trước mốc này phải được kiểm tra lại, không tự mở rộng. Batch sau dùng effective time đáng tin nếu có; không có thì dùng observed_at của snapshot trong manifest, basis=OBSERVED_AT, không lùi về ngày giao dịch. Đổi thuộc tính đóng/mở version; sự kiện đến muộn cần split interval, kiểm tra nonoverlap và rekey fact bị ảnh hưởng trong cùng candidate. Ngày-only được hiểu đầu ngày địa phương; thay đổi giữa ngày chưa đủ độ phân giải để phục hồi phân loại chính xác.',
 'late_data':'Giữ SK cũ cho fact thuộc phiên bản cũ; không rekey toàn lịch sử sang current. Khi sửa lịch sử có bằng chứng thì lookup as-of và tính lại fact/bridge đúng phạm vi thời gian; sửa movement cũ tính lại tồn từ ngày sửa. Dòng không lookup được parent/version bị quarantine và báo thiếu; batch sau khôi phục theo durable natural key, không nhân đôi giao dịch.',
 'publication':'USER_CONFIRMED: công bố tập hợp lệ với trạng thái COMPLETE hoặc PARTIAL. Dòng lỗi quarantine và loại cả dòng phụ thuộc không đủ điều kiện; không giữ tiền nhưng bỏ dimension sai để che lỗi. Mỗi report/visual có thời điểm nguồn, batch, trạng thái thiếu, số dòng bị loại và KPI/phạm vi ảnh hưởng. UNKNOWN amount không điền 0. Tỷ lệ tính trên tập hợp lệ phải gắn PARTIAL nếu tử hoặc mẫu bị ảnh hưởng; không tính được thì NULL và ghi Không đủ dữ liệu. Không tự trộn dữ liệu cũ với mới.',
 'cross_table_consistency':'PARTIAL vẫn phải nhất quán: các bảng hợp lệ được chốt theo cùng batch/cutoff; metadata chất lượng công bố cùng dữ liệu. Dùng publication manifest trỏ phiên bản của từng bảng, không coi nhiều commit Iceberg là transaction chung. Lỗi engine/ghi dữ liệu/cutoff không xác định thì batch FAILED vì không có tập hợp lệ tin cậy để công bố; giao diện vẫn hiển thị trạng thái nguồn thiếu hoặc bản trước với nhãn ngày cũ rõ ràng.',
 'quality_coverage':'Lưu input_count, accepted_count, quarantined_count, dependency_excluded_count theo entity/batch, các nhóm không chồng; discarded duplicate/replay và not_applicable riêng để không gọi lọc nghiệp vụ là lỗi. Tính completeness khi có expected count đáng tin; thiếu toàn file không biết số dòng -> UNKNOWN, không 0% hoặc 100% giả. Dùng phạm vi ngày/site/metric nếu nhận diện được; không biết scope thì cảnh báo toàn KPI phụ thuộc nguồn đó.',
 'evaluation':'So sánh warehouse/lakehouse trên cùng input, accepted set, quarantine/exclusion set và quality status. Bộ số liệu sạch kiểm tra KPI chuẩn; fixture lỗi kiểm tra báo cáo PARTIAL và cảnh báo chính xác. Cần fixture nhỏ SCD2 cho đổi thuộc tính, không đổi, replay, ranh giới hiệu lực, A->B->A và late correction; fixture tách khỏi seed v2. V2 chỉ một version không đủ chứng minh ETL SCD2 đã chạy đúng.',
})
POLICY_LABELS.update(quality_coverage='Độ đầy đủ và phạm vi ảnh hưởng',evaluation='Đánh giá hai giải pháp')
POLICIES['drill_across']='SCD SK là phiên bản, không phải định danh đối tượng xuyên thời gian. Join giữa fact/aggregate dùng namespace+BK bền vững theo grain đã chốt, aggregate riêng rồi nối. B06 gắn receipt về purchase_line và dùng phân loại dimension của dòng đặt mua cho cohort; B07 đối chiếu lô theo receipt_id/hotel_id/item_id. Không để cùng supplier hoặc room có hai SK bị coi là hai đối tượng nghiệp vụ. View current và view as-of phải đặt nhãn rõ; mặc định dùng vai trò as-of từng fact dưới đây.'
POLICY_LABELS['drill_across']='Nối và tổng hợp khi có nhiều phiên bản'

spec=dict(version='companye-warehouse-design-1.1',created_on='2026-10-13',
          status='COLUMN_LEVEL_DESIGN_NOT_IMPLEMENTED',base_model=model['version'],base_model_sha256=HASHES[INPUTS[0]],
          kpi_contract=kpi['version'],source_dataset='v2',types={k:dict(oracle=v[0],iceberg=v[1],rule=v[2]) for k,v in TYPES.items()},
          policies=POLICIES,decisions=DECISIONS,tables=tables,metric_mapping=model['metric_mapping'],
          supersedes=['Draft Type 1 policy','Draft strict publish gate'],
          baseline_note='Logical v1 and diagrams are frozen reference snapshots; dimension history and version-aware keys are refined by this 1.1 contract.',
          input_sha256=HASHES,technical_sources=[
            'https://docs.oracle.com/en/database/oracle/oracle-database/21/sqlqr/Data-Types.html',
            'https://iceberg.apache.org/docs/latest/schemas/', 'https://iceberg.apache.org/spec/'])

def validate():
    checks=[]
    def require(ok, message):
        if not ok: raise AssertionError(message)
        checks.append(message)
    require(len(tables)==37,'37 entities: 16 dimensions, 17 facts, 4 links')
    ids={t['id']:t for t in tables}
    source_count=0
    fk_count=0
    for t in tables:
        names=[c['name'] for c in t['columns']]
        require(len(names)==len(set(names)),t['id']+' unique column names')
        for key in [t['primary_key']]+t['unique_keys']:
            require(all(n in names for n in key),t['id']+' key columns exist: '+','.join(key))
        for c in t['columns']:
            require(c['type'] in TYPES,t['id']+'.'+c['name']+' type resolved')
            for ref in c['source_references']:
                require(ref in source,'source exists: '+ref); source_count+=1
            if 'dimension' in c:
                require(c['dimension'] in ids and c['references']==f'{c["dimension"]}.{DIM_PK[c["dimension"]]}','FK target '+t['id']+'.'+c['name'])
                require(not c['nullable'],'FK physically non-null '+t['id']+'.'+c['name'])
                if t['id'].startswith('F'): fk_count+=1
    require(fk_count==len(roles['foreign_key_roles'])==102,'102 role-specific fact dimension references preserved')
    require(len(spec['metric_mapping'])==47,'47 KPI mappings preserved')
    scd=[t for t in tables if t.get('history_policy')=='SCD_TYPE2']
    require(len(scd)==14,'14 SCD2 dimensions; 2 static dimensions')
    require(all(d['status']=='USER_CONFIRMED' for d in DECISIONS),'Both business decisions confirmed by user')
    for t in scd:
        names={c['name'] for c in t['columns']}
        require(all(c['name'] in names for c in SCD_COLUMNS),t['id']+' SCD2 lifecycle columns present')
        require(all('valid_from_utc' in key or 'version_no' in key for key in t['unique_keys']),t['id']+' business key can repeat across versions')
        require(t['conditional_unique_keys'][0]['columns']==t['business_key'],t['id']+' at most one current version per BK')
    for tid in list(DURABLE_GRAINS)+['F15']:
        require(not any(n in ['room_key','outlet_key','activity_key','vehicle_key','site_key','hotel_key','item_key'] for n in ids[tid]['unique_keys'][0]),tid+' grain uniqueness independent of changing SCD SK')
    require(all('dimension_asof' in ids[f['id']] for f in model['facts']),'17 facts have explicit SCD2 lookup times')
    for d in model['dimensions']:
        require(ids[d['id']]['name']==d['name'],'Dimension name unchanged '+d['id'])
    for f in model['facts']:
        require(ids[f['id']]['grain']==f['grain'],'Fact grain unchanged '+f['id'])
    for p,digest in HASHES.items(): require(sha(p)==digest,'Input unchanged '+p)
    # Source compatibility evidence, read only. This does not validate transformed rows.
    refs_by_table={}
    for t in tables:
        for c in t['columns']:
            for ref in c['source_references']:
                tab,field=ref.rsplit('.',1)
                refs_by_table.setdefault(tab,{}).setdefault(field,set()).add(c['type'])
    profile=[]
    dates=[]
    for ns,ts in contracts.items():
        for st in ts:
            tab=ns+'.'+st['name']; path=ROOT/'generated/v2'/ns/(st['name']+'.csv')
            cols=refs_by_table.get(tab,{})
            rows=0; maxlens={n:0 for n in cols}; minmax={}
            for row in csv.DictReader(path.open(encoding='utf-8-sig',newline='')):
                rows+=1
                for n,types in cols.items():
                    value=row[n]
                    if value in ['',r'\N']: continue
                    maxlens[n]=max(maxlens[n],len(value))
                    limits=[int(re.search(r'\((\d+) CHAR\)',TYPES[ty][0]).group(1)) for ty in types if 'CHAR)' in TYPES[ty][0]]
                    if value and limits and len(value)>min(limits): raise AssertionError(f'Text overflow {tab}.{n}')
                    for ty in types:
                        if ty in ['MONEY','QTY','VALUE','COUNT','KEY','INT','FLAG','DATEKEY']:
                            number=Decimal(value)
                            if ty in ['QTY','VALUE']:
                                precision=18 if ty=='QTY' else 38
                                if number!=number.quantize(Decimal('0.001')) or abs(number)>=Decimal(10)**(precision-3):
                                    raise AssertionError(f'Decimal overflow {tab}.{n}')
                            else:
                                if number!=number.to_integral_value(): raise AssertionError(f'Integer required {tab}.{n}')
                                if ty=='INT' and not -(2**31)<=number<2**31: raise AssertionError(f'INT overflow {tab}.{n}')
                                if ty=='MONEY' and abs(number)>=10**19: raise AssertionError(f'MONEY overflow {tab}.{n}')
                                if ty=='FLAG' and number not in [0,1]: raise AssertionError(f'FLAG invalid {tab}.{n}')
                for c in st['columns']:
                    if c['sql_type'] in ['DATE','TIMESTAMPTZ'] and row[c['name']] not in ['',r'\N']:
                        value=row[c['name']]
                        if c['sql_type']=='TIMESTAMPTZ':
                            value=datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(timezone(timedelta(hours=7))).date().isoformat()
                        else: value=date.fromisoformat(value).isoformat()
                        if c['name'] not in minmax: minmax[c['name']]=[value,value]
                        else: minmax[c['name']]=[min(minmax[c['name']][0],value),max(minmax[c['name']][1],value)]
            dates.extend(v for pair in minmax.values() for v in pair)
            profile.append(dict(table=tab,rows=rows,max_text_characters=maxlens,date_ranges=minmax))
    grain_checks=[]
    for ns,tab,key in [('hotel_ops','breakfast_entitlements',['booking_room_id','service_date']),
                       ('hotel_ops','meal_sessions',['outlet_id','service_date','meal']),
                       ('hotel_ops','weather_daily',['site_id','weather_date'])]:
        seen=set(); duplicates=0
        for r in csv.DictReader((ROOT/'generated/v2'/ns/(tab+'.csv')).open(encoding='utf-8-sig',newline='')):
            val=tuple(r[c] for c in key); duplicates+=val in seen; seen.add(val)
        grain_checks.append(dict(table=ns+'.'+tab,key=key,duplicate_count=duplicates))
        require(duplicates==0,'Observed source grain unique '+tab)
    require(min(dates)>='2023-01-01','Source dates covered by explicit SCD2 bootstrap assumption')
    return dict(status='PASSED_DESIGN_CHECKS',implemented_pipeline=False,assertions=len(checks),entity_count=len(tables),
                dimension_count=16,scd2_dimension_count=14,static_dimension_count=2,fact_count=17,link_count=4,column_count=sum(len(t['columns']) for t in tables),
                fact_dimension_fk_count=fk_count,source_reference_count=source_count,kpi_count=47,
                observed_source_date_min=min(dates),observed_source_date_max=max(dates),
                calendar_start=min(dates)[:4]+'-01-01',calendar_end_inclusive=max(dates)[:4]+'-12-31',
                grain_checks=grain_checks,source_profile=profile,input_sha256=HASHES,
                limitations=['No Oracle/Iceberg DDL executed.','No transformed-row correctness or KPI parity test performed.',
                             'Source field type compatibility and selected grains checked; not a full source quality re-audit.'],
                pending_decisions=[d['id'] for d in DECISIONS if d['status']=='PROPOSED_PENDING_USER'])

def document(report):
    out=['# Đặc tả chi tiết mô hình kho dữ liệu CompanyE','',
      'Phiên bản 1.1, ngày 13/10/2026. Thiết kế cột và quy tắc dùng chung cho Oracle warehouse và Spark Iceberg lakehouse trên nguồn v2. Hai quyết định đã chốt: SCD Type 2 và công bố phần dữ liệu hợp lệ kèm cảnh báo thiếu. Đây là đầu ra bước 1; chưa tạo bảng đích hoặc chạy ETL.', '',
      'Mô hình giữ nguyên 16 dimension, 17 fact gồm một aggregate tùy chọn và một fact thời tiết, cùng bốn bảng liên kết hoặc view kiểm chứng. Các bảng phục vụ 47 KPI B01–B08 đã chốt. Các mục dưới đây đủ để chuẩn bị mapping và DDL; cấu hình engine, partition, index và connector được chốt ở bước môi trường.', '',
      '## Quyết định nghiệp vụ','', '| Mã | Nội dung | Trạng thái | Quyết định hoặc mặc định đề xuất |','|---|---|---|---|']
    for d in DECISIONS: out.append(f'| {d["id"]} | {d["topic"]} | {d["status"]} | {d.get("decision",d["default"])} |')
    out += ['', 'Hai quyết định trên đã được người dùng chốt ngày 13/10/2026 và thay thế đề xuất Type 1 cùng chính sách chặn công bố của bản nháp. Không cần sinh thêm lịch sử vào v2.', '',
            '### Cách hiểu lịch sử dimension', '',
            'Ví dụ minh họa, chưa phải sự kiện trong v2: phòng P101 là Standard trong năm 2024 và được nâng cấp thành Deluxe từ 01/07/2025. Type 1 cập nhật một dòng danh mục thành Deluxe, nên các đêm ở cũ cũng được phân loại theo tên loại phòng hiện hành. Type 2 giữ hai phiên bản, mỗi phiên bản có khóa và khoảng hiệu lực riêng; đêm ở năm 2024 nối phiên bản Standard, đêm ở sau nâng cấp nối Deluxe.', '',
            'CompanyE chọn Type 2 vì trong thực tế các thuộc tính danh mục có thể thay đổi và cần phân tích giao dịch theo phiên bản đúng thời điểm. Dữ liệu tự sinh v2 được giản lược để tập trung vào data engineering: mỗi business key hiện chỉ có phiên bản đầu, không cần tạo sự kiện thay đổi giả. Thiết kế vẫn có đủ khoảng hiệu lực, khóa phiên bản và quy tắc cập nhật; chưa có thay đổi trong dữ liệu không có nghĩa cơ chế lưu phiên bản bị bỏ đi. Khi hiện thực, fixture SCD2 nhỏ tách riêng sẽ kiểm tra cơ chế này.', '',
            '### Cách hiểu công bố batch', '',
            'Batch là một đợt xử lý dữ liệu. Ví dụ đợt mới có 1.000 booking nhưng 20 dòng lỗi: công bố phần hợp lệ của 980 booking và gắn trạng thái PARTIAL. Báo cáo ghi Đã xử lý 980/1.000 booking, loại 20 dòng; các giá trị liên quan chỉ phản ánh phần hợp lệ. Nếu một dòng booking lỗi kéo theo stay hoặc dịch vụ không còn đủ tham chiếu, số dòng phụ thuộc bị loại cũng được ghi riêng.', '',
            'Cảnh báo đi tới từng KPI chịu ảnh hưởng, gồm kỳ/cơ sở khi xác định được. Không đủ tử hoặc mẫu để tính thì hiển thị Không đủ dữ liệu; tỷ lệ tính trên phần hợp lệ vẫn có nhãn thiếu, không coi là tỷ lệ đầy đủ của doanh nghiệp. Không tự bù số từ batch cũ. Lỗi raw đã được cách ly đúng kế hoạch được phân loại riêng với lỗi làm thiếu dữ liệu phân tích.', '',
            '## Quy ước thiết kế','']
    for key,value in POLICIES.items():
        if key=='capacity_period': value=f'{value["start"]} đến trước {value["end_exclusive"]}. {value["rule"]}'
        out += [f'**{POLICY_LABELS[key]}**: {value}', '']
    out += [f'Kiểm tra trực tiếp nguồn v2: ngày nhỏ nhất {report["observed_source_date_min"]}, lớn nhất {report["observed_source_date_max"]}. DimDate cần phủ {report["calendar_start"]} đến {report["calendar_end_inclusive"]}; lịch công suất vẫn chỉ trong kỳ mô phỏng.','',
            '## Kiểu dữ liệu và tính tương đương','', '| Kiểu chung | Oracle dự kiến | Iceberg | Quy tắc |','|---|---|---|---|']
    for key,(ora,ice,rule) in TYPES.items(): out.append(f'| {key} | `{ora}` | `{ice}` | {rule} |')
    out += ['', 'Oracle và Iceberg có kiểu decimal chính xác; giới hạn chuỗi và miền số được kiểm tra chung trước nạp. Thiết kế timestamp lưu giá trị UTC, chuyển sang giờ Việt Nam trước khi lấy ngày nghiệp vụ. Kiểu DATE của Oracle phải bị giới hạn phần giờ về nửa đêm. Tham khảo [Oracle Data Types](https://docs.oracle.com/en/database/oracle/oracle-database/21/sqlqr/Data-Types.html) và [Iceberg Schemas](https://iceberg.apache.org/docs/latest/schemas/).', '',
            'Iceberg identifier fields không bảo đảm tính duy nhất. PK, UK, quan hệ tham chiếu và kiểm tra grain vẫn cần kiểm tra bằng pipeline trước công bố. Xem [Iceberg specification](https://iceberg.apache.org/spec/).', '',
            '## Cột kiểm toán dùng chung','', '| Cột | Kiểu | NULL | Ý nghĩa |','|---|---|---|---|']
    for c in AUDIT: out.append(f'| `{c["name"]}` | {c["type"]} | Không | {c["description"]} |')
    out += ['', 'Năm cột này có trong hợp đồng của mọi entity; các view liên kết chiếu metadata từ input cùng batch. Không cộng metadata vào row_hash. Dòng không đổi có thể giữ source_batch_id cũ; publication manifest xác định phiên bản toàn bộ tập công bố.', '',
            '## Danh mục bảng và khóa','', '| Mã | Bảng hoặc view | Loại | Grain | Khóa duy nhất nghiệp vụ |','|---|---|---|---|']
    for t in tables: out.append(f'| {t["id"]} | {t["name"]} | {t["kind"]} | {t["grain"]} | '+ '; '.join(', '.join(x) for x in t['unique_keys'])+' |')
    out += ['', '## Từ điển cột theo từng bảng','',
            'NULL thể hiện khả năng lưu NULL vật lý. Đối với dimension, cột đánh dấu “bắt buộc NORMAL” phải có giá trị trên thành viên thật; chỉ hai dòng 0 và -1 được bỏ trống. Với SCD2, BK có thể lặp qua các phiên bản; duy nhất theo BK cùng valid_from hoặc version_no, và tối đa một current cho mỗi BK. Thuộc tính ID bên trong dimension là thuộc tính nguồn, không phải FK sang dimension khác.', '']
    audit_names={c['name'] for c in AUDIT}
    for t in tables:
        out += [f'### {t["id"]} {t["name"]}', '',f'**Tên vật lý:** `{t["physical_name"]}`. **Grain:** {t["grain"]}', '',
                '**PK:** `'+', '.join(t['primary_key'])+'`. **UK:** '+'; '.join('`'+', '.join(key)+'`' for key in t['unique_keys'])+'.', '',
                f'**Lịch sử:** {t["history_policy"]}. {t["update_policy"]}', '',
                '| Cột | Kiểu | NULL | Vai trò và quy tắc | Cách tổng hợp |','|---|---|---|---|---|']
        for c in t['columns']:
            if c['name'] in audit_names: continue
            desc=c['description']
            if c.get('required_for_normal_member'): desc+=' Bắt buộc NORMAL.'
            if 'references' in c: desc+=f' FK → {c["references"]}.'
            if 'missing_policy' in c: desc+=' '+c['missing_policy']
            if c['source_references']: desc+=' Nguồn: '+', '.join('`'+r+'`' for r in c['source_references'])+'.'
            out.append(f'| `{c["name"]}` | {c["type"]} | '+('Có' if c['nullable'] else 'Không')+f' | {desc} | {c["aggregation"]} |')
        out += ['', 'Năm cột kiểm toán dùng chung được bổ sung theo mục trên.', '', '**Ràng buộc và cách sử dụng:**','']
        if 'dimension_asof' in t: out += ['- Thời điểm chọn phiên bản dimension: '+t['dimension_asof']]
        if 'conditional_unique_keys' in t: out += ['- UK phiên bản hiện hành: '+', '.join(t['business_key'])+' với member_kind=NORMAL và is_current=1.', '- Thuộc tính theo dõi thay đổi: '+', '.join(t['tracked_attributes'])+'.']
        out += ['- '+r for r in t['checks']]
        out += ['']
    out += ['## Thay đổi dữ liệu và quản lý công bố','',
      'Dự kiến tách metadata vận hành khỏi mô hình nghiệp vụ. Các cấu trúc dưới đây là hợp đồng tối thiểu, chưa phải bảng đã triển khai.', '',
      '| Cấu trúc | Khóa và dữ liệu bắt buộc | Mục đích |','|---|---|---|',
      '| KeyRegistry | PK entity_id + canonical_natural_key; UK entity_id + surrogate_key; first_batch_id | Giữ khóa ổn định và giống nhau ở hai nhánh. |',
      '| BatchManifest | PK batch_id; source_manifest_sha256; source_cutoff; observed_at_utc; contract_version; transform_version; key_registry_sha256; status; started_at_utc; completed_at_utc | Status COMPLETE, PARTIAL hoặc FAILED; observed_at dùng ổn định khi replay SCD2. |',
      '| TablePublication | PK batch_id + branch + entity_id; location; snapshot_or_version; row_count; logical_payload_sha256; check_status | Chỉ cho công bố khi đủ tập bảng trong cùng batch. |',
      '| QuarantineRecord | PK batch_id + entity_id + source_record_key + rule_id; source_path; payload; reason; retry_status | Giữ lỗi để sửa và chạy lại; không sửa âm thầm dữ liệu. |',
      '| ValidationResult | PK batch_id + branch + rule_id + scope_key; expected; actual; status | Bằng chứng kiểm tra từng bước và đối chiếu hai nhánh. |',
      '| QualityCoverage | PK batch_id + branch + entity_id + scope_key; input_count; accepted_count; quarantined_count; dependency_excluded_count; expected_count nullable; completeness_status | Số lượng phần hợp lệ và phần thiếu, không cộng chồng nhóm loại. |',
      '| MetricQualityStatus | PK batch_id + branch + metric_id + scope_key; quality_status; affected_entities; reason; completeness nullable | COMPLETE, PARTIAL hoặc UNAVAILABLE; Power BI/web nhận cùng số KPI. |', '',
      'Batch PARTIAL được công bố khi phần hợp lệ thỏa grain, FK và quy tắc nghiệp vụ, đồng thời có metadata mô tả phần thiếu. Không yêu cầu toàn bộ input sạch trước khi xuất report. Phần không xác định được chất lượng hiển thị UNAVAILABLE, không ép bằng 0; không coi PARTIAL là COMPLETE. So sánh hai nhánh dùng cùng natural key, accepted/excluded set và metadata chất lượng; bỏ thời gian ETL và layout vật lý.', '',
      '## Kiểm chứng thiết kế và giới hạn','',
      f'Script đã kiểm tra {report["entity_count"]} entity, {report["column_count"]} cột gồm cột audit, 102 FK từ fact tới dimension và 47 ánh xạ KPI. Kiểm tra độ dài chuỗi trên dữ liệu nguồn và tính duy nhất của ba grain chưa có UNIQUE trong DB: quyền lợi sáng theo phòng/ngày, phiên buffet theo outlet/ngày/bữa, thời tiết theo site/ngày.', '',
      'Các kiểm tra này xác minh đặc tả và khả năng chứa dữ liệu nguồn; chưa chứng minh ETL đúng, DDL chạy được trên phiên bản được chọn hoặc KPI hai nhánh bằng nhau. Hợp đồng JSON có source_references để truy vết cột, nhưng mapping ETL đầy đủ gồm join path, điều kiện lọc, thứ tự nạp và biểu thức SQL là bước 2.', '',
      'Mã nguồn và seed sinh dữ liệu, schema nguồn, KPI contract và mô hình sơ đồ v1 được kiểm tra hash không đổi. Những bản v1 là baseline trước quyết định mới: đặc tả 1.1 này thay thế ghi chú Type 1 bằng SCD2 và bổ sung khóa grain dùng ID bền vững. Các sơ đồ giữ bố cục và quan hệ nhưng chưa vẽ các cột SCD2 mới. Công thức 47 KPI không đổi; chính sách PARTIAL ở đây thay thế ghi chú chặn chỉ tiêu khi nguồn lỗi trong đặc tả KPI cũ.', '',
      '## Cách tái tạo','', 'Chạy từ thư mục Project:', '', '```powershell','python -X utf8 scripts/build-warehouse-design.py','```','',
      'Đầu ra: `config/warehouse_design_v1.json`, `docs/CompanyE_Warehouse_Detailed_Design.md`, `reports/warehouse_design_v1_validation.json`. Quyết định nghiệp vụ lưu riêng tại `config/warehouse_design_decisions_v1.json`; chạy lại không ghi đè quyết định đã có.', '']
    return '\n'.join(out)

if __name__=='__main__':
    report=validate()
    write('config/warehouse_design_v1.json',spec)
    (ROOT/'docs/CompanyE_Warehouse_Detailed_Design.md').write_text(document(report),encoding='utf-8')
    report['output_sha256']={p:sha(p) for p in ['config/warehouse_design_v1.json','docs/CompanyE_Warehouse_Detailed_Design.md']}
    write('reports/warehouse_design_v1_validation.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ['source_profile','input_sha256','output_sha256']},ensure_ascii=False,indent=2))
