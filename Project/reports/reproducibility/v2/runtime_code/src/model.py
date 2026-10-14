"""Source contracts. These are OLTP tables, not dimensional warehouse tables."""
from dataclasses import dataclass, field


@dataclass
class Table:
    name: str
    description: str
    grain: str
    columns: list
    checks: list = field(default_factory=list)
    owner: str = "CompanyE Operations"

    def ddl(self):
        cols = [f'"{n}" {t} {rules}' for n, t, rules, desc in self.columns]
        cols += [f"CHECK ({rule})" for rule in self.checks]
        return f'CREATE TABLE "{self.name}" (\n  ' + ',\n  '.join(cols) + '\n);'

    def contract(self):
        return {"name": self.name, "description": self.description, "grain": self.grain,
                "owner": self.owner, "checks": self.checks,
                "columns": [{"name": n, "sql_type": t, "constraints": r,
                             "nullable": not ("NOT NULL" in r or "PRIMARY KEY" in r),
                             "description": d,
                             "classification": "synthetic_contact" if n in ("phone", "email", "full_name") else "synthetic_internal",
                             "unit": "VND" if n.endswith('_vnd') else None}
                            for n,t,r,d in self.columns]}


def c(name, kind, description, ref=None, nullable=False, pk=False):
    rules = "PRIMARY KEY" if pk else ("" if nullable else "NOT NULL")
    if ref:
        rules += f" REFERENCES {ref}"
    return name, kind, rules, description


def key(name):
    return c(name, "TEXT", "Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp.", pk=True)


def fk(name, table, nullable=False):
    return c(name, "TEXT", f"Tham chiếu bản ghi {table} trong cùng database.", ref=f"{table}({name})", nullable=nullable)


def text(name, desc, nullable=False): return c(name,"TEXT",desc,nullable=nullable)
def integer(name, desc, nullable=False): return c(name,"INTEGER",desc,nullable=nullable)
def money(name, desc): return c(name,"BIGINT",desc + " Số nguyên VND; không dùng float cho tiền.")
def day(name, desc, nullable=False): return c(name,"DATE",desc,nullable=nullable)
def moment(name, desc): return c(name,"TIMESTAMPTZ",desc + " Múi giờ nguồn +07:00.")
def qty(name, desc): return c(name,"NUMERIC(12,3)",desc)


HOTEL = [
    Table("sites", "Bốn cụm du lịch.", "Một cụm.", [key("site_id"),text("site_name","Tên địa điểm."),text("climate_region","Nhóm khí hậu giả định.")]),
    Table("hotels", "Tám khách sạn CompanyE.", "Một khách sạn.", [key("hotel_id"),fk("site_id","sites"),text("hotel_name","Tên cơ sở."),integer("stars","Hạng sao giả định."),text("website_channel","Mã website chính thức riêng.")], ["stars IN (3,5)"]),
    Table("rooms", "Phòng vật lý thuộc khách sạn.", "Một phòng.", [key("room_id"),fk("hotel_id","hotels"),text("room_type","STANDARD hoặc DELUXE."),integer("capacity","Số khách tối đa."),money("base_rate_vnd","Giá nền mỗi đêm trước điều chỉnh mùa.")], ["capacity > 0", "base_rate_vnd > 0"]),
    Table("channels", "Kênh bán, độc lập phương thức thanh toán.", "Một kênh.", [key("channel_id"),text("channel_name","Tên kênh."),text("channel_type","DIRECT hoặc DISTRIBUTOR."),integer("commission_bps","Hoa hồng giả định theo basis points.")], ["commission_bps BETWEEN 0 AND 10000"]),
    Table("guests", "Hồ sơ khách của hệ thống khách sạn.", "Một hồ sơ khách địa phương.", [key("guest_id"),text("full_name","Tên khách hoàn toàn giả lập."),text("phone","Liên hệ giả lập, có thể khác định dạng giữa nguồn.",True),text("email","Email giả lập thuộc example.invalid.",True)]),
    Table("membership_plans", "Gói hội viên.", "Một gói.", [key("plan_id"),text("plan_name","E Member, E Plus hoặc E Family."),integer("duration_months","0 là không quy định hết hạn."),money("fee_vnd","Phí gói giả định.")]),
    Table("memberships", "Hợp đồng hội viên và thời hạn.", "Một lần đăng ký gói.", [key("membership_id"),fk("plan_id","membership_plans"),fk("guest_id","guests"),day("valid_from","Ngày bắt đầu."),day("valid_to","Ngày hết hạn nếu có.",True),money("paid_vnd","Tiền mua gói; không cộng lại vào từng lần dùng quyền lợi.")]),
    Table("member_cards", "Thẻ nhận diện của thành viên.", "Một thẻ gắn khách với gói.", [key("card_id"),fk("membership_id","memberships"),fk("guest_id","guests"),text("card_type","DIGITAL hoặc PHYSICAL.")]),
    Table("promotions", "Chính sách chiến dịch giả định.", "Một chiến dịch.", [key("promotion_id"),fk("channel_id","channels",True),fk("site_id","sites",True),text("promotion_name","Tên chiến dịch."),day("sale_from","Bắt đầu mở bán."),day("sale_to","Kết thúc mở bán."),day("stay_from","Bắt đầu khoảng lưu trú hợp lệ."),day("stay_to","Kết thúc khoảng lưu trú hợp lệ."),integer("discount_bps","Tỷ lệ giảm trên giá gói."),integer("partner_share_bps","Tỷ lệ đối tác chịu trong phần giảm."),money("cap_vnd","Giới hạn giảm mỗi booking.")], ["discount_bps BETWEEN 0 AND 10000","partner_share_bps BETWEEN 0 AND 10000","sale_to >= sale_from","stay_to >= stay_from"]),
    Table("rate_plans", "Gói giá theo khách sạn và kênh.", "Một gói giá có quyền lợi ăn sáng.", [key("rate_plan_id"),fk("hotel_id","hotels"),fk("channel_id","channels"),text("plan_name","Tên sản phẩm đặt phòng."),integer("breakfast_included","1 gồm ăn sáng, 0 không gồm."),integer("refundable","1 cho phép hoàn theo điều kiện." )], ["breakfast_included IN (0,1)","refundable IN (0,1)"]),
    Table("bookings", "Đặt phòng và điều kiện giá đã chốt.", "Một đơn đặt phòng, có thể nhiều phòng.", [key("booking_id"),fk("hotel_id","hotels"),fk("guest_id","guests"),fk("channel_id","channels"),fk("promotion_id","promotions",True),day("booked_on","Ngày đặt."),day("arrival","Ngày nhận phòng dự kiến."),day("departure","Ngày trả phòng dự kiến."),text("status","COMPLETED, CANCELLED hoặc NO_SHOW."),text("payment_method","Phương thức thanh toán, độc lập channel."),money("gross_vnd","Giá trị gói phòng trước giảm."),money("discount_vnd","Tổng giảm khách được hưởng."),money("company_share_vnd","Phần giảm CompanyE chịu."),money("partner_share_vnd","Phần giảm đối tác chịu."),money("customer_due_vnd","Giá khách trả trước hoàn tiền."),money("commission_vnd","Phí phân phối trên cơ sở tính giả định đã chốt."),moment("updated_at","Thời điểm phiên bản cuối trong snapshot.")], ["departure > arrival","booked_on <= arrival","discount_vnd = company_share_vnd + partner_share_vnd","customer_due_vnd = gross_vnd - discount_vnd","customer_due_vnd >= 0"]),
    Table("booking_rooms", "Phòng cụ thể trong booking.", "Một phòng trong một booking.", [key("booking_room_id"),fk("booking_id","bookings"),fk("room_id","rooms"),fk("rate_plan_id","rate_plans"),integer("adults","Số người lớn."),integer("children","Số trẻ em."),integer("breakfast_guests","Số người được hưởng ăn sáng mỗi ngày."),money("nightly_rate_vnd","Giá mỗi đêm đã chốt, gồm quyền lợi của gói.")], ["adults > 0","children >= 0","breakfast_guests >= 0"]),
    Table("stays", "Lưu trú đã thực hiện.", "Một lần ở của booking room.", [key("stay_id"),fk("booking_room_id","booking_rooms"),day("checkin_date","Ngày nhận thực tế."),day("checkout_date","Ngày trả thực tế.")], ["checkout_date > checkin_date"]),
    Table("breakfast_entitlements", "Quyền lợi buffet theo phòng và ngày.", "Một phòng booking và một ngày ăn.", [key("entitlement_id"),fk("booking_room_id","booking_rooms"),day("service_date","Ngày hưởng quyền lợi."),integer("eligible_covers","Suất được hưởng."),integer("redeemed_covers","Suất thực dùng." )], ["eligible_covers >= redeemed_covers","redeemed_covers >= 0"]),
    Table("outlets", "Nhà hàng và bar.", "Một điểm phục vụ.", [key("outlet_id"),fk("hotel_id","hotels"),text("outlet_type","RESTAURANT hoặc BAR."),integer("capacity","Sức chứa."),integer("quality_profile","Mức nền mô phỏng, không suy từ hạng sao.")]),
    Table("dining_orders", "Hóa đơn bữa trưa, buffet tối, bar và ăn sáng bán thêm.", "Một hóa đơn.", [key("dining_order_id"),fk("outlet_id","outlets"),fk("guest_id","guests",True),fk("booking_id","bookings",True),day("service_date","Ngày dùng dịch vụ."),text("meal","BREAKFAST, LUNCH, DINNER hoặc BAR."),integer("covers","Số khách phục vụ."),money("gross_vnd","Giá trị bán riêng; không gồm suất sáng đi kèm phòng."),money("discount_vnd","Ưu đãi áp dụng."),money("net_vnd","Giá trị sau ưu đãi."),integer("wait_minutes","Thời gian chờ giả lập."),integer("rating","Đánh giá 1 đến 5.")], ["net_vnd = gross_vnd - discount_vnd","rating BETWEEN 1 AND 5"]),
    Table("meal_sessions", "Bữa buffet và nguyên liệu sử dụng.", "Một nhà hàng, ngày và bữa.", [key("session_id"),fk("outlet_id","outlets"),day("service_date","Ngày phục vụ."),text("meal","BREAKFAST hoặc DINNER."),integer("actual_covers","Tổng suất thực dùng."),money("ingredient_cost_vnd","Chi phí nguyên liệu phân bổ theo bữa; không phải chi phí tiêu thụ từng khách.")]),
    Table("payments", "Dòng tiền khách sạn.", "Một lần thu hoặc hoàn cho booking.", [key("payment_id"),fk("booking_id","bookings"),moment("event_time","Thời điểm dòng tiền."),text("event_type","CHARGE hoặc REFUND."),money("amount_vnd","Số tiền dương; hướng theo event_type.")], ["amount_vnd >= 0", "event_type IN ('CHARGE','REFUND')"]),
    Table("settlements", "Đối soát tài trợ và hoa hồng.", "Một booking đối tác.", [key("settlement_id"),fk("booking_id","bookings"),money("sponsor_due_vnd","Tài trợ được hưởng sau trạng thái sử dụng."),money("sponsor_received_vnd","Tài trợ đã đối soát nhận."),money("commission_vnd","Hoa hồng sau hủy/hoàn."),text("status","MATCHED hoặc PENDING.")]),
    Table("suppliers", "Nhà cung cấp đầu vào; quan hệ thương mại giả định.", "Một đơn vị cung cấp.", [key("supplier_id"),text("supplier_name","Tên thương hiệu thật hoặc thương nhân giả định."),text("category","FOOD, EQUIPMENT hoặc MAINTENANCE."),fk("site_id","sites",True),text("delivery_format","CSV, TEXT hoặc MIXED; giả định tích hợp.")]),
    Table("items", "Danh mục nguyên liệu và vật tư chuẩn trong HotelOps.", "Một mặt hàng theo quy cách.", [key("item_id"),text("item_name","Tên hàng chuẩn."),text("specification","Quy cách phân biệt mặt hàng."),text("base_unit","kg, litre hoặc piece."),integer("shelf_life_days","Hạn dùng giả định sau nhận; 0 cho hàng bền."),money("reference_cost_vnd","Giá tham chiếu trên đơn vị chuẩn.")]),
    Table("purchase_orders", "Đơn mua hàng.", "Một đơn của cơ sở tới nhà cung cấp.", [key("purchase_order_id"),fk("hotel_id","hotels"),fk("supplier_id","suppliers"),day("ordered_on","Ngày đặt."),day("expected_on","Ngày hẹn giao.")]),
    Table("purchase_lines", "Dòng hàng của đơn mua.", "Một mặt hàng trên đơn.", [key("purchase_line_id"),fk("purchase_order_id","purchase_orders"),fk("item_id","items"),qty("ordered_qty","Lượng đặt theo đơn vị chuẩn."),money("unit_price_vnd","Đơn giá thỏa thuận trên đơn vị chuẩn.")], ["ordered_qty > 0"]),
    Table("receipts", "Lô hàng thực nhận.", "Một lần nhận của một dòng đơn.", [key("receipt_id"),fk("purchase_line_id","purchase_lines"),day("received_on","Ngày thực nhận."),qty("accepted_qty","Lượng chấp nhận."),qty("rejected_qty","Lượng từ chối."),day("expires_on","Hạn dùng nếu có.",True)], ["accepted_qty >= 0","rejected_qty >= 0"]),
    Table("stock_movements", "Sổ biến động kho theo lô.", "Một biến động một lô tại một khách sạn.", [key("movement_id"),fk("hotel_id","hotels"),fk("item_id","items"),fk("receipt_id","receipts"),fk("session_id","meal_sessions",True),day("movement_date","Ngày biến động."),text("movement_type","IN, USE hoặc WASTE."),text("usage_area","BUFFET, KITCHEN_OTHER, HOUSEKEEPING hoặc WAREHOUSE."),qty("quantity","Số dương; chiều theo loại." )], ["quantity >= 0","movement_type IN ('IN','USE','WASTE')"]),
    Table("assets", "Tài sản khách sạn.", "Một tài sản.", [key("asset_id"),fk("hotel_id","hotels"),fk("room_id","rooms",True),text("asset_type","AC, LIFT hoặc COLD_STORAGE."),fk("supplier_id","suppliers")]),
    Table("maintenance", "Công việc bảo dưỡng tài sản khách sạn.", "Một lần ngừng và xử lý.", [key("maintenance_id"),fk("asset_id","assets"),day("starts_on","Bắt đầu không sẵn sàng."),day("ends_on","Kết thúc, khoảng [start,end)."),text("work_type","PLANNED hoặc BREAKDOWN."),money("cost_vnd","Chi phí ghi nhận của công việc."),text("status","COMPLETED.")], ["ends_on > starts_on"]),
    Table("weather_daily", "Thời tiết giả lập dùng làm ngữ cảnh.", "Một cụm và ngày.", [key("weather_id"),fk("site_id","sites"),day("weather_date","Ngày địa phương."),integer("temperature_c","Nhiệt độ giả lập."),integer("rain_mm","Lượng mưa giả lập."),integer("severe_weather","1 là tình huống hạn chế ngoài trời."),text("provenance","SYNTHETIC_CLIMATE_SCENARIO, không phải quan trắc thật.")])
]

ENTERTAINMENT = [
    Table("centres", "Trung tâm giải trí độc lập HotelOps.", "Một trung tâm.", [key("centre_id"),text("site_code","Mã cụm dùng trong thỏa thuận liên đơn vị."),text("centre_name","Tên trung tâm.")]),
    Table("customers", "Hồ sơ khách EntertainmentOps.", "Một hồ sơ khách nguồn.", [key("customer_id"),text("full_name","Tên giả lập có thể không dấu."),text("phone","Điện thoại nguồn có định dạng khác.",True),text("email","Email có thể thiếu.",True),text("member_card_ref","Mã thẻ khách xuất trình; tham chiếu hợp lệ liên hệ thống.",True)]),
    Table("activities", "Hoạt động trong trung tâm.", "Một hoạt động.", [key("activity_id"),fk("centre_id","centres"),text("activity_name","Tên hoạt động."),integer("outdoor","1 nếu phụ thuộc hoạt động ngoài trời."),integer("capacity_per_day","Sức chứa giả định mỗi ngày."),money("ticket_price_vnd","Giá lượt chuẩn.")]),
    Table("closures", "Lịch đóng theo thời tiết hoặc bảo trì.", "Một hoạt động và ngày đóng.", [key("closure_id"),fk("activity_id","activities"),day("closed_on","Ngày không phục vụ."),text("reason","WEATHER hoặc MAINTENANCE.")]),
    Table("ticket_orders", "Đơn vé, dùng mã và vòng đời riêng.", "Một đơn mua vé.", [key("ticket_order_id"),fk("centre_id","centres"),fk("customer_id","customers"),text("hotel_booking_ref","Booking khách sạn khi bán liên kết; không có FK xuyên database.",True),day("ordered_on","Ngày mua."),text("sales_channel","HOTEL_RECEPTION hoặc GATE."),money("gross_vnd","Giá vé trước hoàn."),money("refunded_vnd","Phần đã hoàn." )], ["gross_vnd >= refunded_vnd", "refunded_vnd >= 0"]),
    Table("tickets", "Vé từng khách cho một hoạt động.", "Một vé cá nhân.", [key("ticket_id"),fk("ticket_order_id","ticket_orders"),fk("activity_id","activities"),day("original_date","Ngày sử dụng dự kiến ban đầu."),day("valid_date","Ngày sau điều chỉnh."),text("status","USED, UNUSED, REFUNDED hoặc RESCHEDULED."),money("price_vnd","Giá vé.")]),
    Table("admissions", "Lượt dùng thực tế.", "Một vé vào một hoạt động.", [key("admission_id"),fk("ticket_id","tickets"),moment("entered_at","Thời điểm vào thực tế.")]),
    Table("vehicles", "Đội phương tiện theo cụm.", "Một xe.", [key("vehicle_id"),fk("centre_id","centres"),text("vehicle_type","CAR hoặc MOTORBIKE."),money("daily_rate_vnd","Giá một ngày thuê.")]),
    Table("vehicle_maintenance", "Khoảng xe ngừng phục vụ.", "Một lần bảo trì xe.", [key("vehicle_work_id"),fk("vehicle_id","vehicles"),day("starts_on","Ngày bắt đầu."),day("ends_on","Ngày kết thúc, không gồm ngày này."),money("cost_vnd","Chi phí công việc.")], ["ends_on > starts_on"]),
    Table("rentals", "Hợp đồng thuê và thời gian thực hiện.", "Một lần thuê một xe.", [key("rental_id"),fk("vehicle_id","vehicles"),fk("customer_id","customers"),text("hotel_booking_ref","Tham chiếu bán qua khách sạn.",True),day("pickup_date","Ngày nhận."),day("return_date","Ngày trả, không gồm ngày này."),text("status","COMPLETED hoặc CANCELLED."),money("agreed_vnd","Giá trị thỏa thuận.")], ["return_date > pickup_date"]),
    Table("cash_events", "Thu hoàn của khối giải trí.", "Một sự kiện dòng tiền cho đơn vé hoặc thuê xe.", [key("cash_event_id"),fk("ticket_order_id","ticket_orders",True),fk("rental_id","rentals",True),moment("event_time","Thời điểm thu hoàn."),text("event_type","CHARGE hoặc REFUND."),money("amount_vnd","Số tiền dương.")], ["(ticket_order_id IS NULL) <> (rental_id IS NULL)","amount_vnd >= 0","event_type IN ('CHARGE','REFUND')"])
]

MODELS = {"hotel_ops": HOTEL, "entertainment_ops": ENTERTAINMENT}


def all_contracts():
    return {db: [t.contract() for t in tables] for db,tables in MODELS.items()}
