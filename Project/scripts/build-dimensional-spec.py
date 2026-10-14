"""Build reviewable logical matrices from explicit design choices and the frozen KPI contract.
Does not load, modify or generate operational data.
"""
import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
read = lambda p: json.loads((ROOT / p).read_text(encoding='utf-8-sig'))
kpi = read('config/kpi_contract_v1.json')
schema = {f'{db}.{t["name"]}': {c['name'] for c in t['columns']}
          for db, tables in read('generated/v2/contracts.json').items() for t in tables}
dimensions = []
facts = []

def dim(id, name, key, attributes, sources, policy):
    dimensions.append(dict(id=id, name=name, business_key=key, attributes=attributes,
                           source_columns=sources, history_policy=policy))

CURRENT = 'V2: thuộc tính hiện hành cố định; Type 1. Không bịa lịch sử trước snapshot. Thiết kế SCD2 tương lai cần effective timestamp và hợp đồng mới.'
dim('D01','DimDate','calendar_date','Ngày, tháng, quý, năm, thứ; ngày lễ/mùa chỉ thêm khi có bộ quy tắc có phiên bản.',{},'Lịch sinh xác định; phủ mọi ngày nguồn kể cả booked_on năm 2023; cùng khóa YYYYMMDD ở hai nhánh.')
dim('D02','DimSite','hotel_ops.sites.site_id','Tên cụm, vùng khí hậu.',{'hotel_ops.sites':['site_id','site_name','climate_region'],'entertainment_ops.centres':['site_code']},CURRENT)
dim('D03','DimHotel','hotel_ops + hotel_id','Tên, hạng sao, site_key, website_channel.',{'hotel_ops.hotels':['hotel_id','hotel_name','site_id','stars','website_channel']},CURRENT)
dim('D04','DimRoom','hotel_ops + room_id','Loại phòng, sức chứa, khách sạn; giá niêm yết không thay giá giao dịch.',{'hotel_ops.rooms':['room_id','hotel_id','room_type','capacity','base_rate_vnd']},CURRENT)
dim('D05','DimChannel','source_namespace + channel_code','Tên và loại kênh. Kênh đặt phòng khác kênh bán vé.',{'hotel_ops.channels':['channel_id','channel_name','channel_type','commission_bps'],'entertainment_ops.ticket_orders':['sales_channel']},CURRENT)
dim('D06','DimPromotion','hotel_ops + promotion_id','Chiến dịch, phạm vi bán/lưu trú, mức giảm, tỷ lệ đối tác tài trợ.',{'hotel_ops.promotions':['promotion_id','promotion_name','channel_id','site_id','sale_from','sale_to','stay_from','stay_to','discount_bps','partner_share_bps','cap_vnd']},CURRENT)
dim('D07','DimCustomerProfile','source_system + source_customer_id','Hồ sơ khách nguồn; giữ riêng guest_id và customer_id, không mặc định cùng người.',{'hotel_ops.guests':['guest_id','full_name','phone','email'],'entertainment_ops.customers':['customer_id','full_name','phone','email','member_card_ref']},'Type 1 hồ sơ nguồn; chưa tạo Golden Customer. Không dùng audit_only để hợp nhất khách.')
dim('D08','DimRatePlan','hotel_ops + rate_plan_id','Gói giá, bao gồm sáng, hoàn hủy, khách sạn và kênh áp dụng.',{'hotel_ops.rate_plans':['rate_plan_id','hotel_id','channel_id','plan_name','breakfast_included','refundable']},CURRENT)
dim('D09','DimOutlet','hotel_ops + outlet_id','Loại điểm ăn uống, sức chứa, quality_profile, khách sạn phục vụ.',{'hotel_ops.outlets':['outlet_id','hotel_id','outlet_type','capacity','quality_profile']},CURRENT)
dim('D10','DimMeal','meal_code','BREAKFAST, LUNCH, DINNER, BAR; BREAKFAST cho quyền lợi sáng.',{'hotel_ops.dining_orders':['meal'],'hotel_ops.meal_sessions':['meal']},'Danh mục chuẩn có kiểm soát; không đồng nhất BAR với buffet.')
dim('D11','DimCentre','entertainment_ops + centre_id','Tên trung tâm và site_key qua site_code.',{'entertainment_ops.centres':['centre_id','centre_name','site_code']},CURRENT)
dim('D12','DimActivity','entertainment_ops + activity_id','Tên hoạt động, outdoor, capacity_per_day, trung tâm.',{'entertainment_ops.activities':['activity_id','centre_id','activity_name','outdoor','capacity_per_day']},CURRENT)
dim('D13','DimVehicle','entertainment_ops + vehicle_id','Loại xe, trung tâm, giá niêm yết.',{'entertainment_ops.vehicles':['vehicle_id','centre_id','vehicle_type','daily_rate_vnd']},CURRENT)
dim('D14','DimSupplier','hotel_ops + supplier_id','Tên, nhóm, cụm nhà cung cấp và định dạng giao dữ liệu.',{'hotel_ops.suppliers':['supplier_id','supplier_name','category','site_id','delivery_format']},CURRENT)
dim('D15','DimItem','hotel_ops + item_id','Tên, quy cách, base_unit, hạn dùng; không cộng chéo đơn vị.',{'hotel_ops.items':['item_id','item_name','specification','base_unit','shelf_life_days']},CURRENT)
dim('D16','DimAsset','hotel_ops + asset_id','Loại tài sản, khách sạn, room_id có thể NULL, nhà cung cấp tài sản.',{'hotel_ops.assets':['asset_id','hotel_id','room_id','asset_type','supplier_id']},CURRENT)

def fact(id,name,grain,keys,measures,dates,dims,sources,rules,scope='CORE'):
    facts.append(dict(id=id,name=name,grain=grain,unique_key=keys,measures=measures,
                      date_roles=dates,dimension_roles=dims,source_columns=sources,rules=rules,scope=scope))
fact('F01','FactBooking','Một booking ở trạng thái cuối của batch.','source_system + booking_id',
 'booking_count=1; gross, discount, customer_due, company_share, partner_share, commission; giữ status.',
 'booked_on; arrival cho B01.04–05; departure cho B02–B03.',
 {'D01':'R: đặt/đến/trả','D02':'cụm đặt phòng','D03':'khách sạn đặt','D05':'kênh booking','D06':'chiến dịch','D07':'hồ sơ đặt'},
 {'hotel_ops.bookings':['booking_id','hotel_id','guest_id','channel_id','promotion_id','booked_on','arrival','departure','status','gross_vnd','discount_vnd','customer_due_vnd','company_share_vnd','partner_share_vnd','commission_vnd','updated_at']},
 'B02 chỉ COMPLETED; không nhân giá theo phòng, vé hoặc revision. Room type lọc booking qua EXISTS BridgeBookingRoom, không phân bổ tiền ngầm.')
fact('F02','FactRoomDay','Một phòng và một ngày danh mục.','room_key + date_key','inventory_day=1; blocked_day 0/1; available_day=1-blocked_day.',
 'calendar_date trong [S,E).',{'D01':'ngày khả dụng','D02':'cụm','D03':'khách sạn','D04':'phòng'},
 {'hotel_ops.rooms':['room_id','hotel_id'],'hotel_ops.assets':['asset_id','room_id'],'hotel_ops.maintenance':['maintenance_id','asset_id','starts_on','ends_on']},
 'Hợp DISTINCT mọi khoảng bảo trì [starts_on,ends_on). Dùng chung B01.02 và B08.03; không chịu bộ lọc kênh/khách hoặc loại công việc chi phí.')
fact('F03','FactStayNight','Một phòng và một đêm thực ở hợp lệ.','room_key + service_date_key','occupied_night=1; booking_id, booking_room_id và stay_id để truy vết.',
 'Mở rộng [checkin_date,checkout_date) thực tế.',{'D01':'ngày thực ở','D02':'cụm','D03':'khách sạn','D04':'phòng','D05':'kênh booking','D07':'khách nguồn','D08':'gói giá'},
 {'hotel_ops.stays':['stay_id','booking_room_id','checkin_date','checkout_date'],'hotel_ops.booking_rooms':['booking_room_id','booking_id','room_id','rate_plan_id'],'hotel_ops.bookings':['booking_id','status','channel_id','guest_id']},
 'Chỉ booking COMPLETED; overlap và ở trùng ngày ngừng bán là lỗi. Kênh có thể lọc đêm bán nhưng không tạo công suất theo kênh.')
fact('F04','FactTicketOrder','Một đơn vé.','entertainment_ops + ticket_order_id','gross_vnd; refunded_vnd; net_ticket_vnd; validated hotel_booking_ref nullable.',
 'ordered_on; departure booking khi tính cohort B03.',{'D01':'R: bán/cohort','D02':'R: cụm phục vụ/đặt','D03':'khách sạn giới thiệu nullable','D05':'R: kênh vé/kênh booking','D07':'khách mua vé','D11':'trung tâm phục vụ'},
 {'entertainment_ops.ticket_orders':['ticket_order_id','centre_id','customer_id','hotel_booking_ref','ordered_on','sales_channel','gross_vnd','refunded_vnd']},
 'B03 tổng riêng về booking. Không phân bổ giá đơn theo hoạt động nếu không có quy tắc. Đơn không ref là bán độc lập; vé UNUSED chưa hoàn vẫn là mua.')
fact('F05','FactRental','Một hợp đồng thuê một xe.','entertainment_ops + rental_id','agreed_vnd; status; hotel_booking_ref nullable.',
 'pickup_date, return_date; departure booking cho B03.',{'D01':'R: nhận/trả/cohort','D02':'R: cụm phục vụ/đặt','D03':'khách sạn giới thiệu nullable','D05':'kênh booking qua ref','D07':'khách thuê','D11':'trung tâm','D13':'xe'},
 {'entertainment_ops.rentals':['rental_id','vehicle_id','customer_id','hotel_booking_ref','pickup_date','return_date','status','agreed_vnd']},
 'B03 chỉ COMPLETED; số tiền ghi một lần, không chép lên mỗi ngày xe. B05 lấy ngày từ F11, không cộng số hợp đồng thành ngày xe.')
fact('F06','FactBreakfastEntitlement','Một quyền lợi phòng và ngày phục vụ.','hotel_ops + entitlement_id; kiểm tra booking_room_id + service_date','eligible_covers; redeemed_covers; không tạo doanh thu mới.',
 'service_date.',{'D01':'ngày ăn','D02':'cụm','D03':'khách sạn phục vụ','D04':'phòng','D07':'khách đặt','D08':'gói giá','D09':'nhà hàng ánh xạ','D10':'BREAKFAST'},
 {'hotel_ops.breakfast_entitlements':['entitlement_id','booking_room_id','service_date','eligible_covers','redeemed_covers'],'hotel_ops.booking_rooms':['booking_room_id','booking_id','room_id','rate_plan_id'],'hotel_ops.bookings':['booking_id','hotel_id','guest_id','status'],'hotel_ops.outlets':['outlet_id','hotel_id','outlet_type']},
 'Chỉ COMPLETED. Ánh xạ đúng một RESTAURANT mỗi khách sạn ở v2; nhiều hơn một phải báo lỗi thay vì chọn ngẫu nhiên.')
fact('F07','FactDiningOrder','Một hóa đơn ăn uống, không phải dòng món.','hotel_ops + dining_order_id','net_vnd; covers; rating_sum=rating hợp lệ; rating_count; booking_id nullable.',
 'service_date.',{'D01':'ngày ăn','D02':'cụm phục vụ','D03':'R: phục vụ/đặt nullable','D07':'khách ăn nullable','D09':'điểm ăn uống','D10':'bữa'},
 {'hotel_ops.dining_orders':['dining_order_id','outlet_id','guest_id','booking_id','service_date','meal','covers','net_vnd','rating']},
 'Cơ sở phục vụ theo outlet, không theo booking. Rating có trọng số mỗi hóa đơn, không theo covers. Không có dimension món ăn từ schema hiện tại.')
fact('F08','FactMealSession','Một outlet, ngày và bữa buffet.','outlet_key + service_date_key + meal_key','actual_covers; ingredient_cost_vnd.',
 'service_date.',{'D01':'ngày ăn','D02':'cụm phục vụ','D03':'khách sạn phục vụ','D09':'outlet','D10':'bữa'},
 {'hotel_ops.meal_sessions':['session_id','outlet_id','service_date','meal','actual_covers','ingredient_cost_vnd']},
 'BREAKFAST/DINNER; không cộng actual_covers lần nữa vào B04.05. Không nối chi phí phiên với từng hóa đơn rồi SUM.')
fact('F09','FactAdmission','Một lượt admission thực tế.','entertainment_ops + admission_id','admission_count=1; ticket_id để truy vết.',
 'DATE(entered_at tại Asia/Ho_Chi_Minh).',{'D01':'ngày thực dùng','D02':'cụm','D07':'khách đơn vé','D11':'trung tâm','D12':'hoạt động'},
 {'entertainment_ops.admissions':['admission_id','ticket_id','entered_at'],'entertainment_ops.tickets':['ticket_id','ticket_order_id','activity_id','status'],'entertainment_ops.ticket_orders':['ticket_order_id','customer_id']},
 'Không thay entered_at bằng valid_date hoặc chỉ nhận vé USED. Admission RESCHEDULED hợp lệ vẫn tính; vượt capacity/đóng cửa phải báo lỗi.')
fact('F10','FactActivityDay','Một hoạt động và ngày danh mục.','activity_key + date_key','nominal_capacity; is_closed; available_capacity.',
 'calendar_date.',{'D01':'ngày hoạt động','D02':'cụm','D11':'trung tâm','D12':'hoạt động'},
 {'entertainment_ops.activities':['activity_id','centre_id','capacity_per_day'],'entertainment_ops.closures':['closure_id','activity_id','closed_on','reason']},
 'Closure đóng trọn ngày; gộp nhiều lý do trước khi tính. Không có phân bổ capacity theo khách, kênh hoặc khách sạn giới thiệu.')
fact('F11','FactVehicleDay','Một xe và ngày danh mục.','vehicle_key + date_key','inventory_day=1; maintenance_day; available_day; rented_day.',
 'calendar_date; khoảng thuê và bảo trì [start,end).',{'D01':'ngày xe','D02':'cụm','D11':'trung tâm','D13':'xe'},
 {'entertainment_ops.vehicles':['vehicle_id','centre_id'],'entertainment_ops.rentals':['rental_id','vehicle_id','pickup_date','return_date','status'],'entertainment_ops.vehicle_maintenance':['vehicle_work_id','vehicle_id','starts_on','ends_on']},
 'rented_day từ COMPLETED; overlap thuê hoặc thuê trong bảo trì là lỗi. Không chứa agreed_vnd nhân theo số ngày.')
fact('F12','FactPurchaseLine','Một dòng đặt mua.','hotel_ops + purchase_line_id','ordered_qty; unit_price_vnd; purchase_order_id.',
 'ordered_on; expected_on cho cohort B06; ngày đánh giá A là tham số.',{'D01':'R: đặt/hẹn','D02':'cụm nhận','D03':'khách sạn nhận','D14':'nhà cung cấp','D15':'mặt hàng'},
 {'hotel_ops.purchase_lines':['purchase_line_id','purchase_order_id','item_id','ordered_qty','unit_price_vnd'],'hotel_ops.purchase_orders':['purchase_order_id','hotel_id','supplier_id','ordered_on','expected_on']},
 'Giữ dòng đến hạn không receipt. Ordered_qty tính một lần; không lặp theo từng lần giao. Mỗi A phải tổng lại receipt received_on<=A.')
fact('F13','FactReceipt','Một lần nhận của một dòng đặt mua.','hotel_ops + receipt_id','accepted_qty; rejected_qty; late_accepted_qty theo expected_on; purchase_line_id.',
 'received_on; expected_on để đối chiếu; expires_on là ngày hạn dùng.',{'D01':'R: nhận/hẹn/hạn','D02':'cụm nhận','D03':'khách sạn nhận','D14':'nhà cung cấp','D15':'mặt hàng'},
 {'hotel_ops.receipts':['receipt_id','purchase_line_id','received_on','accepted_qty','rejected_qty','expires_on'],'hotel_ops.purchase_lines':['purchase_line_id','purchase_order_id','item_id','unit_price_vnd'],'hotel_ops.purchase_orders':['purchase_order_id','supplier_id','hotel_id','expected_on']},
 'Feed ngoài là đối chiếu, không cộng thêm receipt. receipt_id cũng là định danh lô; rejected không nhập kho và không thành WASTE.')
fact('F14','FactStockMovement','Một chuyển động của một lô tại khách sạn.','hotel_ops + movement_id','quantity; signed_qty; in/use/waste_qty; quantity*giá lô; movement_type, usage_area, receipt_id.',
 'movement_date; lấy lịch sử trước S cho đầu kỳ.',{'D01':'ngày biến động','D02':'cụm kho','D03':'khách sạn quản lý kho','D14':'nhà cung cấp lô','D15':'mặt hàng'},
 {'hotel_ops.stock_movements':['movement_id','hotel_id','item_id','receipt_id','session_id','movement_date','movement_type','usage_area','quantity'],'hotel_ops.receipts':['receipt_id','purchase_line_id'],'hotel_ops.purchase_lines':['purchase_line_id','purchase_order_id','unit_price_vnd'],'hotel_ops.purchase_orders':['purchase_order_id','supplier_id']},
 'Tồn đầu=sum trước S; cuối=sum trước E. Không có warehouse_id nên chưa tạo DimWarehouse vật lý. usage_area chỉ lọc lượng USE, không lọc tồn. session_id phục vụ drill-through có kiểm soát.')
fact('F15','AggInventoryLotDay','Một lô, khách sạn, mặt hàng và ngày cuối ngày.','receipt_id + hotel_key + item_key + date_key','closing_qty; closing_value_vnd; in/use/waste trong ngày.',
 'snapshot_date, cuối ngày.',{'D01':'ngày chốt tồn','D02':'cụm kho','D03':'khách sạn kho','D14':'nhà cung cấp lô','D15':'mặt hàng'},
 {'hotel_ops.stock_movements':['movement_id','receipt_id','hotel_id','item_id','movement_date','movement_type','quantity']},
 'Tùy chọn vật hóa từ F14. Không cộng closing qua ngày; đầu kỳ lấy cuối ngày trước S hoặc lịch sử F14. Giữ lô còn tồn dù không có movement trong kỳ. Không cộng F14 và F15.', 'OPTIONAL_AGGREGATE')
fact('F16','FactMaintenanceWork','Một công việc bảo trì tài sản khách sạn.','hotel_ops + maintenance_id','cost_vnd; work_type; status; maintenance_id.',
 'starts_on, ends_on; chi phí theo ends_on và COMPLETED.',{'D01':'R: bắt đầu/kết thúc','D02':'cụm','D03':'khách sạn','D04':'phòng nullable','D16':'tài sản'},
 {'hotel_ops.maintenance':['maintenance_id','asset_id','starts_on','ends_on','work_type','cost_vnd','status'],'hotel_ops.assets':['asset_id','hotel_id','room_id','asset_type','supplier_id']},
 'Tiền ghi một lần, không nhân theo ngày. Supplier của asset là bên bán tài sản, không coi là vendor bảo trì. Ngày chặn phòng dùng F02 và bridge overlap.')
fact('F17','FactWeatherDay','Một cụm và ngày thời tiết.','site_key + date_key','temperature_c; rain_mm; severe_weather; provenance.',
 'weather_date.',{'D01':'ngày thời tiết','D02':'cụm'},
 {'hotel_ops.weather_daily':['weather_id','site_id','weather_date','temperature_c','rain_mm','severe_weather','provenance']},
 'Ngữ cảnh B05. Nối 1:1 site/date sau khi xác minh duy nhất hoặc semijoin bộ ngày; không nhân thời tiết theo admission rồi lấy SUM. Không kết luận nhân quả.', 'CONTEXT')

# Exact KPI-to-fact mappings. D = direct measure, S = supporting/cohort, O = optional aggregate.
mapping = {}
def link(ids, primary, supporting=(), optional=()):
    for id in ids.split(): mapping[id] = dict(primary_facts=primary.split(),supporting_facts=list(supporting),optional_facts=list(optional))
link('B01.01','F03'); link('B01.02','F02'); link('B01.03','F03 F02'); link('B01.04 B01.05','F01')
link('B02.01 B02.02 B02.03 B02.04 B02.05 B02.06','F01')
link('B03.01 B03.02','F04 F05',('F01',)); link('B03.03','F04',('F01',)); link('B03.04','F05',('F01',)); link('B03.05','F01 F04 F05')
link('B04.01 B04.02 B04.03','F06'); link('B04.04 B04.08','F07'); link('B04.05','F06 F07'); link('B04.06 B04.07','F08')
link('B05.01','F09'); link('B05.02','F10'); link('B05.03','F09 F10'); link('B05.04 B05.05 B05.06','F11')
link('B06.01','F12'); link('B06.02 B06.03 B06.04','F13',('F12',)); link('B06.05 B06.07','F12 F13'); link('B06.06','F13',('F12',))
link('B07.01 B07.02 B07.03 B07.04 B07.05 B07.06','F14',(),('F15',))
link('B08.01','F16'); link('B08.02 B08.03 B08.04','F02')
metrics = [dict(id=m['id'],name=m['name'],date_role=m['date_role'],formula=m['formula'],**mapping[m['id']])
           for r in kpi['requirements'] for m in r['metrics']]
requirements = []
for r in kpi['requirements']:
    usage = {}
    for m in metrics:
        if m['id'].startswith(r['id']+'.'):
            for key,label in [('primary_facts','D'),('supporting_facts','S'),('optional_facts','O')]:
                for f in m[key]:
                    if f not in usage or label=='D': usage[f]=label
    if r['id']=='B05': usage.update(F05='S',F17='C')
    if r['id']=='B08': usage['F16']='D'
    requirements.append(dict(id=r['id'],name=r['name'],fact_usage=usage))

links = [
 dict(name='BridgeBookingRoom',grain='Một booking_room_id',sources=['hotel_ops.booking_rooms'],keys='booking_id, room_key, rate_plan_key',rule='EXISTS/COUNTD cho bộ lọc loại phòng của booking; không copy giá F01 lên bridge.'),
 dict(name='BridgeRoomDayMaintenance',grain='Một room_key, date_key, maintenance_id',sources=['hotel_ops.maintenance','hotel_ops.assets'],keys='room_key, date_key, maintenance_id',rule='Giải thích lý do ngừng phòng; F02 lấy hợp DISTINCT. Không SUM cost sau khi nối bridge.'),
 dict(name='ValidatedBookingServiceLink',grain='Một service_type, service_id với booking_ref hợp lệ',sources=['entertainment_ops.ticket_orders','entertainment_ops.rentals','hotel_ops.bookings'],keys='service_type, service_id, booking_id',rule='Liên kết n:1 về booking; có thể là view kiểm tra, không bắt buộc bảng bridge vật lý. Bán độc lập giữ NULL; ref sai quarantine.'),
 dict(name='SiteCrosswalk',grain='Một centre_id → một site_id',sources=['entertainment_ops.centres','hotel_ops.sites'],keys='centres.site_code = sites.site_id',rule='Chỉ ánh xạ công khai trong nguồn; không dùng identity truth hoặc suy theo tên khách.')
]
# Enterprise-level rows are business processes, not report IDs or fact-table names.
process_specs = [
 ('P01','Tiếp nhận đặt phòng','F01','B01 B02 B03',['D04','D08'],'Phòng và gói giá qua BridgeBookingRoom; chỉ lọc EXISTS, không phân bổ tiền booking.'),
 ('P02','Thực hiện lưu trú','F03','B01',[],'Đêm thực ở; phân biệt kênh của đêm bán với mẫu số công suất.'),
 ('P03','Theo dõi phòng khả dụng','F02','B01 B08',[],'Room-day dùng chung cho lưu trú và ảnh hưởng bảo trì.'),
 ('P04','Bán vé giải trí','F04','B03',[],'Khách sạn/kênh booking chỉ có khi có tham chiếu booking hợp lệ.'),
 ('P05','Tiếp nhận lượt dùng hoạt động','F09 F10','B05',[],'Lượt dùng và capacity có grain riêng; chiều khách không lọc capacity.'),
 ('P06','Cho thuê phương tiện','F05 F11','B03 B05',[],'Hợp đồng và ngày xe có grain riêng; khách/kênh không lọc ngày xe sẵn sàng.'),
 ('P07','Cấp và sử dụng quyền lợi sáng','F06','B04',[],'Quyền lợi đi kèm phòng không tạo thêm doanh thu ăn uống.'),
 ('P08','Bán và phục vụ ăn uống','F07 F08','B04',[],'Hóa đơn và phiên buffet có grain riêng; khách không lọc chi phí phiên.'),
 ('P09','Đặt mua hàng','F12','B06',[],'Một dòng đặt mua; giữ lượng đặt một lần khi nối nhiều lần nhận.'),
 ('P10','Tiếp nhận hàng mua','F13','B06',[],'Một lần nhận của một dòng đặt mua; file ngoài chỉ đối chiếu.'),
 ('P11','Ghi nhận nhập xuất và tồn kho','F14 F15','B07',[],'F15 tùy chọn; số dư không cộng qua ngày hoặc lọc theo usage_area.'),
 ('P12','Bảo trì tài sản khách sạn','F16','B08',[],'Bên cung cấp tài sản không mặc định là nhà thầu bảo trì. Ngày phòng khả dụng ở P03.'),
]
fact_index={f['id']:f for f in facts}
processes=[]
for id,name,fs,rs,extra,note in process_specs:
    fact_ids=fs.split()
    process_dimensions=set(extra).union(*(set(fact_index[f]['dimension_roles']) for f in fact_ids))
    processes.append(dict(id=id,name=name,facts=fact_ids,requirements=rs.split(),
                          dimensions=sorted(process_dimensions),additional_dimensions=extra,note=note))
overview=dict(version='companye-enterprise-bus-1.0',
              reference='CO5173 Chapter 2, slide 89, Figure 5.1',
              rows='business processes',columns='conformed dimension candidates',
              marker='X',processes=processes,
              context_facts=['F17'],
              context_note='F17 là dữ liệu thời tiết theo cụm/ngày hỗ trợ B05, không phải quá trình giao dịch riêng. Tồn theo ngày F15 nằm trong P11 và là tùy chọn.')
model = dict(version='companye-dimensional-1.0',created_on='2026-10-12',status='LOGICAL_DESIGN_NOT_IMPLEMENTED',
             kpi_contract=kpi['version'],source_dataset='v2',dimensions=dimensions,facts=facts,
             requirements=requirements,metric_mapping=metrics,links=links,enterprise_bus_matrix=overview)
all_metrics={m['id'] for r in kpi['requirements'] for m in r['metrics']}
assert set(mapping)==all_metrics and len(all_metrics)==47
fids={f['id'] for f in facts}; dids={d['id'] for d in dimensions}
refs=0
for obj in dimensions+facts:
    for table,columns in obj['source_columns'].items():
        assert table in schema,table
        assert set(columns)<=schema[table],(table,set(columns)-schema[table])
        refs+=len(columns)
for f in facts: assert set(f['dimension_roles'])<=dids
for m in metrics:
    assert m['primary_facts']
    assert set(m['primary_facts']+m['supporting_facts']+m['optional_facts'])<=fids
for r in requirements: assert set(r['fact_usage'])<=fids
for x in links: assert set(x['sources'])<=set(schema)
assert len({p['id'] for p in processes})==len(processes)==12
assert {r for p in processes for r in p['requirements']}=={r['id'] for r in requirements}
assert {f for p in processes for f in p['facts']}==fids-set(overview['context_facts'])
for p in processes:
    assert set(p['dimensions'])<=dids
    assert set(p['facts'])<=fids
    assert set(p['additional_dimensions'])<=set(p['dimensions'])
manifest=read('generated/v2/manifest.json')
for filename,digest in manifest['generator_sha256'].items():
    assert hashlib.sha256((ROOT/'src'/filename).read_bytes()).hexdigest()==digest
out=ROOT/'config/dimensional_model_v1.json'
out.write_text(json.dumps(model,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def table(headers, rows):
    safe=lambda x:str(x).replace('|',' / ').replace('\n',' ')
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+
                     ['| '+' | '.join(safe(x) for x in row)+' |' for row in rows])
parts=['# Ma trận nghiệp vụ và mô hình chiều CompanyE',
 'Phiên bản 1.0 ngày 12/10/2026. Thiết kế logic cho cùng 47 KPI trên Oracle warehouse và Spark–Iceberg lakehouse. Chưa tạo DDL hoặc nạp fact/dimension.',
 '## Cách đọc và phạm vi',
 'Ma trận 1 ánh xạ B01–B08 đến fact. D = đo trực tiếp; S = nguồn hỗ trợ/cohort; C = ngữ cảnh thời tiết; O = bảng tổng hợp tùy chọn. Ô trống nghĩa là không dùng cho KPI v1. Có 16 dimension và 17 fact/bảng tổng hợp được mô tả; F15 là tùy chọn, F17 là ngữ cảnh. Không nhất thiết tạo 17 bảng vật lý ngay.',
 'Ma trận 2 ánh xạ fact đến dimension. X = khóa chiều một vai trò; R = nhiều vai trò phải đặt tên FK riêng. Role-playing date/hotel/site/channel không có nghĩa tạo nhiều định nghĩa dimension. Ma trận là bản thiết kế; khóa surrogate, precision và DDL còn được cụ thể hóa ở bước tiếp theo.',
 '## Bus matrix tổng quan theo quá trình nghiệp vụ',
 'Theo cấu trúc slide 89, Chương 2 CO5173, Figure 5.1: hàng là quá trình nghiệp vụ, cột là dimension dùng chung, ô liên quan đánh dấu X. Đây là ma trận tổng quan trong phạm vi B01–B08; không phải toàn bộ mọi hoạt động của doanh nghiệp. Các bảng B01–B08 đến fact và KPI đến fact bên dưới là ma trận truy vết, không thay thế bus matrix này.',
 'Mỗi X nghĩa là dimension có liên quan tới ít nhất một phần của quá trình. Nó không cho phép áp mọi bộ lọc lên mọi số đo. Khi một hàng có nhiều fact hoặc nhiều vai trò ngày/cơ sở, grain và vai trò cụ thể nằm ở ma trận triển khai. Riêng P01 dùng thêm Room và RatePlan qua BridgeBookingRoom. D07 là hồ sơ khách nguồn, chưa phải khách hợp nhất giữa hai hệ thống.',
 table(['Quá trình nghiệp vụ']+[d['id'] for d in dimensions],[[p['id']+' '+p['name']]+['X' if d['id'] in p['dimensions'] else '' for d in dimensions] for p in processes]),
 table(['Dimension','Tên'],[[d['id'],d['name']] for d in dimensions]),
 '### Liên hệ giữa quá trình và mô hình triển khai',
 table(['Quá trình','Fact','Nhu cầu','Giới hạn áp dụng'],[[p['id'],', '.join(p['facts']),', '.join(p['requirements']),p['note']] for p in processes]),
 overview['context_note'],
 'Nguồn mẫu: [slide Chương 2 CO5173](../../slides/Data%20Engineering%20-%20Chapter%202%20-%20Data%20Warehouse%20%20and%20Data%20Management%20Architecture%20Design.pdf), trang 89. Trang 84–88 hướng dẫn chọn quá trình, xác định grain, chọn dimension và xác định số đo. Tên quá trình, các dimension và dấu X là thiết kế cho CompanyE dựa trên schema v2.',
 '## Ma trận 1 B01 đến B08 và fact',
 table(['Fact']+[r['id'] for r in requirements],[[f['id']+' '+f['name']]+[r['fact_usage'].get(f['id'],'') for r in requirements] for f in facts]),
 table(['Nhu cầu','Tên'],[[r['id'],r['name']] for r in requirements]),
 '## Ma trận 2 Fact và dimension dùng chung']
for start,end,label in [(0,8,'Chiều thời gian, cơ sở và thương mại'),(8,16,'Chiều dịch vụ và vận hành')]:
    ds=dimensions[start:end]
    parts += ['### '+label,table(['Fact']+[d['id'] for d in ds],[[f['id']]+[('R' if f['dimension_roles'][d['id']].startswith('R:') else 'X') if d['id'] in f['dimension_roles'] else '' for d in ds] for f in facts])]
parts += ['## Danh mục dimension',table(['Mã và tên','Khóa nghiệp vụ','Thuộc tính','Chính sách lịch sử'],[[d['id']+' '+d['name'],d['business_key'],d['attributes'],d['history_policy']] for d in dimensions]),
 '## Danh mục fact và grain']
for f in facts:
    parts += ['### '+f['id']+' '+f['name'],
              '**Grain:** '+f['grain']+' **Khóa duy nhất:** '+f['unique_key']+'.',
              '**Số đo:** '+f['measures'], '**Vai trò ngày:** '+f['date_roles'],
              '**Dimension:** '+ '; '.join(k+' '+v for k,v in f['dimension_roles'].items())+'.',
              '**Nguồn:** '+ '; '.join(t+'('+', '.join(cols)+')' for t,cols in f['source_columns'].items())+'.',f['rules']]
parts += ['## Ma trận 3 Ánh xạ toàn bộ KPI',table(['KPI','Chỉ tiêu','Fact trực tiếp','Hỗ trợ','Tùy chọn','Ngày nghiệp vụ'],[[m['id'],m['name'],', '.join(m['primary_facts']),', '.join(m['supporting_facts']),', '.join(m['optional_facts']),m['date_role']] for m in metrics]),
 '## Liên kết và chống nhân đôi',table(['Liên kết','Grain','Khóa','Quy tắc'],[[l['name'],l['grain'],l['keys'],l['rule']] for l in links]),
 '## Quy tắc dùng chung giữa hai nhánh',
 '1. Dùng cùng snapshot v2, cùng phiên bản KPI, manifest hash và ánh xạ natural key. Surrogate ID có thể khác giữa hai engine nhưng phải đối chiếu theo natural key và cùng ý nghĩa. Mỗi fact lưu batch_id và nguồn truy vết; nếu giữ nhiều snapshot thì thêm batch_id vào khóa lưu trữ và view chuẩn chỉ đọc một batch đã công bố.',
 '2. Key 0 = Unknown cho quan hệ thiếu chưa xác minh; key -1 = Not applicable cho không khuyến mãi, tài sản chung hoặc bán độc lập. Giữ source ID gốc và lý do. Một ref booking có giá trị nhưng sai không được đổi thành bán độc lập hợp lệ. Thiếu quan hệ bắt buộc phải quarantine hoặc chặn công bố KPI bị ảnh hưởng.',
 '3. Không ghép F01 × F04 × F05 trực tiếp rồi SUM. Tổng vé và xe riêng về booking, LEFT JOIN về cohort COMPLETED. Booking không mua phải còn trong mẫu số B03.02.',
 '4. F06, F07, F08 chỉ tổng hợp về outlet/ngày/bữa trước khi đối chiếu. Chi phí buffet và actual_covers không được nhân theo hóa đơn. B04.05 = redeemed entitlement + covers hóa đơn, không cộng thêm actual_covers.',
 '5. B06 bắt đầu ở dòng đơn đến hạn F12, tổng receipt đến A rồi LEFT JOIN. OTIF theo dòng, không theo đơn hoặc receipt. B07 lấy F14 hoặc F15 có quy tắc thời điểm, không cộng cả hai.',
 '6. Ngày khả dụng B01/B08 cùng F02. Phân rã nguyên nhân qua bridge chỉ dùng DISTINCT room/date, không cộng các nhóm nguyên nhân chồng nhau. Chi phí F16 theo ngày ends_on, không theo ngày chặn phòng.',
 '7. Mọi tỷ lệ dùng tổng tử/tổng mẫu; mẫu 0 = NULL/BLANK. Tiền và lượng dùng decimal; tồn không SUM qua ngày. DimItem chứa base_unit; lượng khác đơn vị không tổng chung.',
 '8. Power BI ưu tiên quan hệ 1:n từ dimension tới fact và một chiều lọc. Các vai trò ngày/cơ sở dùng FK hoặc alias rõ ràng; không bật lọc hai chiều hàng loạt để giải quyết fact-to-fact. Bộ lọc khách/kênh không tác động capacity, usage_area không tác động tồn, work_type chi phí không làm thay đổi tổng phòng khả dụng.',
 '9. Mỗi dim phải nhất quán theo nguồn nhưng không phải dimension nào cũng có mặt ở mọi fact. Không gộp supplier thương mại với OTA chỉ vì cùng gọi vendor. DimSupplier là bên cung ứng; OTA nằm trong DimChannel. Khoản tài trợ CompanyE/đối tác ở F01, chưa cần fact tài trợ nhiều bên vì nguồn v2 chỉ có hai thành phần.',
 '## Những phần không suy diễn từ nguồn',
 'Không tạo DimMenuItem hay fact dòng món từ dining_orders; không tạo nhiều kho khi nguồn chỉ có hotel_id; không coi assets.supplier_id là nhà thầu bảo trì; không hợp nhất khách bằng audit_only. Hội viên/thẻ có trong raw nhưng chưa là chiều bắt buộc của 47 KPI: phân tích lịch sử hội viên cần thêm quy tắc hiệu lực và xử lý nhiều gói, tránh nhân booking. Payments, cash_events, settlements và revisions giữ làm dữ liệu truy vết/đối soát, chưa đưa thành KPI dòng tiền ngoài phạm vi đã chốt.',
 '## Kiểm tra và bước tiếp theo',
 'Kiểm tra tự động bao phủ 47 mã KPI, các mã fact/dimension, tham chiếu bảng/cột nguồn và checksum mã sinh v2. Đây là kiểm tra đặc tả, không phải nghiệm thu phép tính trên Oracle/Iceberg. Tiếp theo chốt kiểu dữ liệu, nullability và ERD vật lý; triển khai ETL; chạy fixture KPI qua từng engine.',
 '## Hồ sơ liên quan',
 '- [Đặc tả KPI](CompanyE_KPI_Specification.md)\n- [Hợp đồng mô hình có thể kiểm tra bằng máy](../config/dimensional_model_v1.json)\n- [Kết quả kiểm tra đặc tả](../reports/dimensional_model_v1_validation.json)\n- Nguồn schema: generated/v2/contracts.json. Mã tái tạo tài liệu: scripts/build-dimensional-spec.py.']
(ROOT/'docs/CompanyE_Dimensional_Matrices.md').write_text('\n\n'.join(parts)+'\n',encoding='utf-8')
report=dict(status='PASSED',scope='Specification integrity only; no warehouse/lakehouse execution',business_processes=len(processes),bus_matrix_cells=len(processes)*len(dimensions),requirements=len(requirements),metrics=len(metrics),facts=len(facts),dimensions=len(dimensions),source_column_references=refs,generator_hashes_unchanged=True,model_sha256=hashlib.sha256(out.read_bytes()).hexdigest())
(ROOT/'reports/dimensional_model_v1_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
