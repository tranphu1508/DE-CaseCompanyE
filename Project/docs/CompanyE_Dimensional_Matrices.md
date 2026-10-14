# Ma trận nghiệp vụ và mô hình chiều CompanyE

Phiên bản 1.0 ngày 12/10/2026. Thiết kế logic cho cùng 47 KPI trên Oracle warehouse và Spark–Iceberg lakehouse. Chưa tạo DDL hoặc nạp fact/dimension.

## Cách đọc và phạm vi

Ma trận 1 ánh xạ B01–B08 đến fact. D = đo trực tiếp; S = nguồn hỗ trợ/cohort; C = ngữ cảnh thời tiết; O = bảng tổng hợp tùy chọn. Ô trống nghĩa là không dùng cho KPI v1. Có 16 dimension và 17 fact/bảng tổng hợp được mô tả; F15 là tùy chọn, F17 là ngữ cảnh. Không nhất thiết tạo 17 bảng vật lý ngay.

Ma trận 2 ánh xạ fact đến dimension. X = khóa chiều một vai trò; R = nhiều vai trò phải đặt tên FK riêng. Role-playing date/hotel/site/channel không có nghĩa tạo nhiều định nghĩa dimension. Ma trận là bản thiết kế; khóa surrogate, precision và DDL còn được cụ thể hóa ở bước tiếp theo.

## Bus matrix tổng quan theo quá trình nghiệp vụ

Theo cấu trúc slide 89, Chương 2 CO5173, Figure 5.1: hàng là quá trình nghiệp vụ, cột là dimension dùng chung, ô liên quan đánh dấu X. Đây là ma trận tổng quan trong phạm vi B01–B08; không phải toàn bộ mọi hoạt động của doanh nghiệp. Các bảng B01–B08 đến fact và KPI đến fact bên dưới là ma trận truy vết, không thay thế bus matrix này.

Mỗi X nghĩa là dimension có liên quan tới ít nhất một phần của quá trình. Nó không cho phép áp mọi bộ lọc lên mọi số đo. Khi một hàng có nhiều fact hoặc nhiều vai trò ngày/cơ sở, grain và vai trò cụ thể nằm ở ma trận triển khai. Riêng P01 dùng thêm Room và RatePlan qua BridgeBookingRoom. D07 là hồ sơ khách nguồn, chưa phải khách hợp nhất giữa hai hệ thống.

| Quá trình nghiệp vụ | D01 | D02 | D03 | D04 | D05 | D06 | D07 | D08 | D09 | D10 | D11 | D12 | D13 | D14 | D15 | D16 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P01 Tiếp nhận đặt phòng | X | X | X | X | X | X | X | X |  |  |  |  |  |  |  |  |
| P02 Thực hiện lưu trú | X | X | X | X | X |  | X | X |  |  |  |  |  |  |  |  |
| P03 Theo dõi phòng khả dụng | X | X | X | X |  |  |  |  |  |  |  |  |  |  |  |  |
| P04 Bán vé giải trí | X | X | X |  | X |  | X |  |  |  | X |  |  |  |  |  |
| P05 Tiếp nhận lượt dùng hoạt động | X | X |  |  |  |  | X |  |  |  | X | X |  |  |  |  |
| P06 Cho thuê phương tiện | X | X | X |  | X |  | X |  |  |  | X |  | X |  |  |  |
| P07 Cấp và sử dụng quyền lợi sáng | X | X | X | X |  |  | X | X | X | X |  |  |  |  |  |  |
| P08 Bán và phục vụ ăn uống | X | X | X |  |  |  | X |  | X | X |  |  |  |  |  |  |
| P09 Đặt mua hàng | X | X | X |  |  |  |  |  |  |  |  |  |  | X | X |  |
| P10 Tiếp nhận hàng mua | X | X | X |  |  |  |  |  |  |  |  |  |  | X | X |  |
| P11 Ghi nhận nhập xuất và tồn kho | X | X | X |  |  |  |  |  |  |  |  |  |  | X | X |  |
| P12 Bảo trì tài sản khách sạn | X | X | X | X |  |  |  |  |  |  |  |  |  |  |  | X |

| Dimension | Tên |
|---|---|
| D01 | DimDate |
| D02 | DimSite |
| D03 | DimHotel |
| D04 | DimRoom |
| D05 | DimChannel |
| D06 | DimPromotion |
| D07 | DimCustomerProfile |
| D08 | DimRatePlan |
| D09 | DimOutlet |
| D10 | DimMeal |
| D11 | DimCentre |
| D12 | DimActivity |
| D13 | DimVehicle |
| D14 | DimSupplier |
| D15 | DimItem |
| D16 | DimAsset |

### Liên hệ giữa quá trình và mô hình triển khai

| Quá trình | Fact | Nhu cầu | Giới hạn áp dụng |
|---|---|---|---|
| P01 | F01 | B01, B02, B03 | Phòng và gói giá qua BridgeBookingRoom; chỉ lọc EXISTS, không phân bổ tiền booking. |
| P02 | F03 | B01 | Đêm thực ở; phân biệt kênh của đêm bán với mẫu số công suất. |
| P03 | F02 | B01, B08 | Room-day dùng chung cho lưu trú và ảnh hưởng bảo trì. |
| P04 | F04 | B03 | Khách sạn/kênh booking chỉ có khi có tham chiếu booking hợp lệ. |
| P05 | F09, F10 | B05 | Lượt dùng và capacity có grain riêng; chiều khách không lọc capacity. |
| P06 | F05, F11 | B03, B05 | Hợp đồng và ngày xe có grain riêng; khách/kênh không lọc ngày xe sẵn sàng. |
| P07 | F06 | B04 | Quyền lợi đi kèm phòng không tạo thêm doanh thu ăn uống. |
| P08 | F07, F08 | B04 | Hóa đơn và phiên buffet có grain riêng; khách không lọc chi phí phiên. |
| P09 | F12 | B06 | Một dòng đặt mua; giữ lượng đặt một lần khi nối nhiều lần nhận. |
| P10 | F13 | B06 | Một lần nhận của một dòng đặt mua; file ngoài chỉ đối chiếu. |
| P11 | F14, F15 | B07 | F15 tùy chọn; số dư không cộng qua ngày hoặc lọc theo usage_area. |
| P12 | F16 | B08 | Bên cung cấp tài sản không mặc định là nhà thầu bảo trì. Ngày phòng khả dụng ở P03. |

F17 là dữ liệu thời tiết theo cụm/ngày hỗ trợ B05, không phải quá trình giao dịch riêng. Tồn theo ngày F15 nằm trong P11 và là tùy chọn.

Nguồn mẫu: [slide Chương 2 CO5173](../../slides/Data%20Engineering%20-%20Chapter%202%20-%20Data%20Warehouse%20%20and%20Data%20Management%20Architecture%20Design.pdf), trang 89. Trang 84–88 hướng dẫn chọn quá trình, xác định grain, chọn dimension và xác định số đo. Tên quá trình, các dimension và dấu X là thiết kế cho CompanyE dựa trên schema v2.

## Ma trận 1 B01 đến B08 và fact

| Fact | B01 | B02 | B03 | B04 | B05 | B06 | B07 | B08 |
|---|---|---|---|---|---|---|---|---|
| F01 FactBooking | D | D | D |  |  |  |  |  |
| F02 FactRoomDay | D |  |  |  |  |  |  | D |
| F03 FactStayNight | D |  |  |  |  |  |  |  |
| F04 FactTicketOrder |  |  | D |  |  |  |  |  |
| F05 FactRental |  |  | D |  | S |  |  |  |
| F06 FactBreakfastEntitlement |  |  |  | D |  |  |  |  |
| F07 FactDiningOrder |  |  |  | D |  |  |  |  |
| F08 FactMealSession |  |  |  | D |  |  |  |  |
| F09 FactAdmission |  |  |  |  | D |  |  |  |
| F10 FactActivityDay |  |  |  |  | D |  |  |  |
| F11 FactVehicleDay |  |  |  |  | D |  |  |  |
| F12 FactPurchaseLine |  |  |  |  |  | D |  |  |
| F13 FactReceipt |  |  |  |  |  | D |  |  |
| F14 FactStockMovement |  |  |  |  |  |  | D |  |
| F15 AggInventoryLotDay |  |  |  |  |  |  | O |  |
| F16 FactMaintenanceWork |  |  |  |  |  |  |  | D |
| F17 FactWeatherDay |  |  |  |  | C |  |  |  |

| Nhu cầu | Tên |
|---|---|
| B01 | Đánh giá hoạt động lưu trú |
| B02 | Đánh giá kênh bán và khuyến mãi |
| B03 | Phân tích bán chéo khách sạn và giải trí |
| B04 | Đánh giá buffet và nhà hàng |
| B05 | Đánh giá giải trí và phương tiện |
| B06 | Đánh giá giao hàng nhà cung cấp |
| B07 | Kiểm soát tồn kho và hao hụt |
| B08 | Đánh giá bảo trì và khả năng cung cấp phòng |

## Ma trận 2 Fact và dimension dùng chung

### Chiều thời gian, cơ sở và thương mại

| Fact | D01 | D02 | D03 | D04 | D05 | D06 | D07 | D08 |
|---|---|---|---|---|---|---|---|---|
| F01 | R | X | X |  | X | X | X |  |
| F02 | X | X | X | X |  |  |  |  |
| F03 | X | X | X | X | X |  | X | X |
| F04 | R | R | X |  | R |  | X |  |
| F05 | R | R | X |  | X |  | X |  |
| F06 | X | X | X | X |  |  | X | X |
| F07 | X | X | R |  |  |  | X |  |
| F08 | X | X | X |  |  |  |  |  |
| F09 | X | X |  |  |  |  | X |  |
| F10 | X | X |  |  |  |  |  |  |
| F11 | X | X |  |  |  |  |  |  |
| F12 | R | X | X |  |  |  |  |  |
| F13 | R | X | X |  |  |  |  |  |
| F14 | X | X | X |  |  |  |  |  |
| F15 | X | X | X |  |  |  |  |  |
| F16 | R | X | X | X |  |  |  |  |
| F17 | X | X |  |  |  |  |  |  |

### Chiều dịch vụ và vận hành

| Fact | D09 | D10 | D11 | D12 | D13 | D14 | D15 | D16 |
|---|---|---|---|---|---|---|---|---|
| F01 |  |  |  |  |  |  |  |  |
| F02 |  |  |  |  |  |  |  |  |
| F03 |  |  |  |  |  |  |  |  |
| F04 |  |  | X |  |  |  |  |  |
| F05 |  |  | X |  | X |  |  |  |
| F06 | X | X |  |  |  |  |  |  |
| F07 | X | X |  |  |  |  |  |  |
| F08 | X | X |  |  |  |  |  |  |
| F09 |  |  | X | X |  |  |  |  |
| F10 |  |  | X | X |  |  |  |  |
| F11 |  |  | X |  | X |  |  |  |
| F12 |  |  |  |  |  | X | X |  |
| F13 |  |  |  |  |  | X | X |  |
| F14 |  |  |  |  |  | X | X |  |
| F15 |  |  |  |  |  | X | X |  |
| F16 |  |  |  |  |  |  |  | X |
| F17 |  |  |  |  |  |  |  |  |

## Danh mục dimension

| Mã và tên | Khóa nghiệp vụ | Thuộc tính | Chính sách lịch sử |
|---|---|---|---|
| D01 DimDate | calendar_date | Ngày, tháng, quý, năm, thứ; ngày lễ/mùa chỉ thêm khi có bộ quy tắc có phiên bản. | Lịch sinh xác định; phủ mọi ngày nguồn kể cả booked_on năm 2023; cùng khóa YYYYMMDD ở hai nhánh. |
| D02 DimSite | hotel_ops.sites.site_id | Tên cụm, vùng khí hậu. | V2: thuộc tính hiện hành cố định; Type 1. Không bịa lịch sử trước snapshot. Thiết kế SCD2 tương lai cần effective timestamp và hợp đồng mới. |
| D03 DimHotel | hotel_ops + hotel_id | Tên, hạng sao, site_key, website_channel. | V2: thuộc tính hiện hành cố định; Type 1. Không bịa lịch sử trước snapshot. Thiết kế SCD2 tương lai cần effective timestamp và hợp đồng mới. |
| D04 DimRoom | hotel_ops + room_id | Loại phòng, sức chứa, khách sạn; giá niêm yết không thay giá giao dịch. | V2: thuộc tính hiện hành cố định; Type 1. Không bịa lịch sử trước snapshot. Thiết kế SCD2 tương lai cần effective timestamp và hợp đồng mới. |
| D05 DimChannel | source_namespace + channel_code | Tên và loại kênh. Kênh đặt phòng khác kênh bán vé. | V2: thuộc tính hiện hành cố định; Type 1. Không bịa lịch sử trước snapshot. Thiết kế SCD2 tương lai cần effective timestamp và hợp đồng mới. |
| D06 DimPromotion | hotel_ops + promotion_id | Chiến dịch, phạm vi bán/lưu trú, mức giảm, tỷ lệ đối tác tài trợ. | V2: thuộc tính hiện hành cố định; Type 1. Không bịa lịch sử trước snapshot. Thiết kế SCD2 tương lai cần effective timestamp và hợp đồng mới. |
| D07 DimCustomerProfile | source_system + source_customer_id | Hồ sơ khách nguồn; giữ riêng guest_id và customer_id, không mặc định cùng người. | Type 1 hồ sơ nguồn; chưa tạo Golden Customer. Không dùng audit_only để hợp nhất khách. |
| D08 DimRatePlan | hotel_ops + rate_plan_id | Gói giá, bao gồm sáng, hoàn hủy, khách sạn và kênh áp dụng. | V2: thuộc tính hiện hành cố định; Type 1. Không bịa lịch sử trước snapshot. Thiết kế SCD2 tương lai cần effective timestamp và hợp đồng mới. |
| D09 DimOutlet | hotel_ops + outlet_id | Loại điểm ăn uống, sức chứa, quality_profile, khách sạn phục vụ. | V2: thuộc tính hiện hành cố định; Type 1. Không bịa lịch sử trước snapshot. Thiết kế SCD2 tương lai cần effective timestamp và hợp đồng mới. |
| D10 DimMeal | meal_code | BREAKFAST, LUNCH, DINNER, BAR; BREAKFAST cho quyền lợi sáng. | Danh mục chuẩn có kiểm soát; không đồng nhất BAR với buffet. |
| D11 DimCentre | entertainment_ops + centre_id | Tên trung tâm và site_key qua site_code. | V2: thuộc tính hiện hành cố định; Type 1. Không bịa lịch sử trước snapshot. Thiết kế SCD2 tương lai cần effective timestamp và hợp đồng mới. |
| D12 DimActivity | entertainment_ops + activity_id | Tên hoạt động, outdoor, capacity_per_day, trung tâm. | V2: thuộc tính hiện hành cố định; Type 1. Không bịa lịch sử trước snapshot. Thiết kế SCD2 tương lai cần effective timestamp và hợp đồng mới. |
| D13 DimVehicle | entertainment_ops + vehicle_id | Loại xe, trung tâm, giá niêm yết. | V2: thuộc tính hiện hành cố định; Type 1. Không bịa lịch sử trước snapshot. Thiết kế SCD2 tương lai cần effective timestamp và hợp đồng mới. |
| D14 DimSupplier | hotel_ops + supplier_id | Tên, nhóm, cụm nhà cung cấp và định dạng giao dữ liệu. | V2: thuộc tính hiện hành cố định; Type 1. Không bịa lịch sử trước snapshot. Thiết kế SCD2 tương lai cần effective timestamp và hợp đồng mới. |
| D15 DimItem | hotel_ops + item_id | Tên, quy cách, base_unit, hạn dùng; không cộng chéo đơn vị. | V2: thuộc tính hiện hành cố định; Type 1. Không bịa lịch sử trước snapshot. Thiết kế SCD2 tương lai cần effective timestamp và hợp đồng mới. |
| D16 DimAsset | hotel_ops + asset_id | Loại tài sản, khách sạn, room_id có thể NULL, nhà cung cấp tài sản. | V2: thuộc tính hiện hành cố định; Type 1. Không bịa lịch sử trước snapshot. Thiết kế SCD2 tương lai cần effective timestamp và hợp đồng mới. |

## Danh mục fact và grain

### F01 FactBooking

**Grain:** Một booking ở trạng thái cuối của batch. **Khóa duy nhất:** source_system + booking_id.

**Số đo:** booking_count=1; gross, discount, customer_due, company_share, partner_share, commission; giữ status.

**Vai trò ngày:** booked_on; arrival cho B01.04–05; departure cho B02–B03.

**Dimension:** D01 R: đặt/đến/trả; D02 cụm đặt phòng; D03 khách sạn đặt; D05 kênh booking; D06 chiến dịch; D07 hồ sơ đặt.

**Nguồn:** hotel_ops.bookings(booking_id, hotel_id, guest_id, channel_id, promotion_id, booked_on, arrival, departure, status, gross_vnd, discount_vnd, customer_due_vnd, company_share_vnd, partner_share_vnd, commission_vnd, updated_at).

B02 chỉ COMPLETED; không nhân giá theo phòng, vé hoặc revision. Room type lọc booking qua EXISTS BridgeBookingRoom, không phân bổ tiền ngầm.

### F02 FactRoomDay

**Grain:** Một phòng và một ngày danh mục. **Khóa duy nhất:** room_key + date_key.

**Số đo:** inventory_day=1; blocked_day 0/1; available_day=1-blocked_day.

**Vai trò ngày:** calendar_date trong [S,E).

**Dimension:** D01 ngày khả dụng; D02 cụm; D03 khách sạn; D04 phòng.

**Nguồn:** hotel_ops.rooms(room_id, hotel_id); hotel_ops.assets(asset_id, room_id); hotel_ops.maintenance(maintenance_id, asset_id, starts_on, ends_on).

Hợp DISTINCT mọi khoảng bảo trì [starts_on,ends_on). Dùng chung B01.02 và B08.03; không chịu bộ lọc kênh/khách hoặc loại công việc chi phí.

### F03 FactStayNight

**Grain:** Một phòng và một đêm thực ở hợp lệ. **Khóa duy nhất:** room_key + service_date_key.

**Số đo:** occupied_night=1; booking_id, booking_room_id và stay_id để truy vết.

**Vai trò ngày:** Mở rộng [checkin_date,checkout_date) thực tế.

**Dimension:** D01 ngày thực ở; D02 cụm; D03 khách sạn; D04 phòng; D05 kênh booking; D07 khách nguồn; D08 gói giá.

**Nguồn:** hotel_ops.stays(stay_id, booking_room_id, checkin_date, checkout_date); hotel_ops.booking_rooms(booking_room_id, booking_id, room_id, rate_plan_id); hotel_ops.bookings(booking_id, status, channel_id, guest_id).

Chỉ booking COMPLETED; overlap và ở trùng ngày ngừng bán là lỗi. Kênh có thể lọc đêm bán nhưng không tạo công suất theo kênh.

### F04 FactTicketOrder

**Grain:** Một đơn vé. **Khóa duy nhất:** entertainment_ops + ticket_order_id.

**Số đo:** gross_vnd; refunded_vnd; net_ticket_vnd; validated hotel_booking_ref nullable.

**Vai trò ngày:** ordered_on; departure booking khi tính cohort B03.

**Dimension:** D01 R: bán/cohort; D02 R: cụm phục vụ/đặt; D03 khách sạn giới thiệu nullable; D05 R: kênh vé/kênh booking; D07 khách mua vé; D11 trung tâm phục vụ.

**Nguồn:** entertainment_ops.ticket_orders(ticket_order_id, centre_id, customer_id, hotel_booking_ref, ordered_on, sales_channel, gross_vnd, refunded_vnd).

B03 tổng riêng về booking. Không phân bổ giá đơn theo hoạt động nếu không có quy tắc. Đơn không ref là bán độc lập; vé UNUSED chưa hoàn vẫn là mua.

### F05 FactRental

**Grain:** Một hợp đồng thuê một xe. **Khóa duy nhất:** entertainment_ops + rental_id.

**Số đo:** agreed_vnd; status; hotel_booking_ref nullable.

**Vai trò ngày:** pickup_date, return_date; departure booking cho B03.

**Dimension:** D01 R: nhận/trả/cohort; D02 R: cụm phục vụ/đặt; D03 khách sạn giới thiệu nullable; D05 kênh booking qua ref; D07 khách thuê; D11 trung tâm; D13 xe.

**Nguồn:** entertainment_ops.rentals(rental_id, vehicle_id, customer_id, hotel_booking_ref, pickup_date, return_date, status, agreed_vnd).

B03 chỉ COMPLETED; số tiền ghi một lần, không chép lên mỗi ngày xe. B05 lấy ngày từ F11, không cộng số hợp đồng thành ngày xe.

### F06 FactBreakfastEntitlement

**Grain:** Một quyền lợi phòng và ngày phục vụ. **Khóa duy nhất:** hotel_ops + entitlement_id; kiểm tra booking_room_id + service_date.

**Số đo:** eligible_covers; redeemed_covers; không tạo doanh thu mới.

**Vai trò ngày:** service_date.

**Dimension:** D01 ngày ăn; D02 cụm; D03 khách sạn phục vụ; D04 phòng; D07 khách đặt; D08 gói giá; D09 nhà hàng ánh xạ; D10 BREAKFAST.

**Nguồn:** hotel_ops.breakfast_entitlements(entitlement_id, booking_room_id, service_date, eligible_covers, redeemed_covers); hotel_ops.booking_rooms(booking_room_id, booking_id, room_id, rate_plan_id); hotel_ops.bookings(booking_id, hotel_id, guest_id, status); hotel_ops.outlets(outlet_id, hotel_id, outlet_type).

Chỉ COMPLETED. Ánh xạ đúng một RESTAURANT mỗi khách sạn ở v2; nhiều hơn một phải báo lỗi thay vì chọn ngẫu nhiên.

### F07 FactDiningOrder

**Grain:** Một hóa đơn ăn uống, không phải dòng món. **Khóa duy nhất:** hotel_ops + dining_order_id.

**Số đo:** net_vnd; covers; rating_sum=rating hợp lệ; rating_count; booking_id nullable.

**Vai trò ngày:** service_date.

**Dimension:** D01 ngày ăn; D02 cụm phục vụ; D03 R: phục vụ/đặt nullable; D07 khách ăn nullable; D09 điểm ăn uống; D10 bữa.

**Nguồn:** hotel_ops.dining_orders(dining_order_id, outlet_id, guest_id, booking_id, service_date, meal, covers, net_vnd, rating).

Cơ sở phục vụ theo outlet, không theo booking. Rating có trọng số mỗi hóa đơn, không theo covers. Không có dimension món ăn từ schema hiện tại.

### F08 FactMealSession

**Grain:** Một outlet, ngày và bữa buffet. **Khóa duy nhất:** outlet_key + service_date_key + meal_key.

**Số đo:** actual_covers; ingredient_cost_vnd.

**Vai trò ngày:** service_date.

**Dimension:** D01 ngày ăn; D02 cụm phục vụ; D03 khách sạn phục vụ; D09 outlet; D10 bữa.

**Nguồn:** hotel_ops.meal_sessions(session_id, outlet_id, service_date, meal, actual_covers, ingredient_cost_vnd).

BREAKFAST/DINNER; không cộng actual_covers lần nữa vào B04.05. Không nối chi phí phiên với từng hóa đơn rồi SUM.

### F09 FactAdmission

**Grain:** Một lượt admission thực tế. **Khóa duy nhất:** entertainment_ops + admission_id.

**Số đo:** admission_count=1; ticket_id để truy vết.

**Vai trò ngày:** DATE(entered_at tại Asia/Ho_Chi_Minh).

**Dimension:** D01 ngày thực dùng; D02 cụm; D07 khách đơn vé; D11 trung tâm; D12 hoạt động.

**Nguồn:** entertainment_ops.admissions(admission_id, ticket_id, entered_at); entertainment_ops.tickets(ticket_id, ticket_order_id, activity_id, status); entertainment_ops.ticket_orders(ticket_order_id, customer_id).

Không thay entered_at bằng valid_date hoặc chỉ nhận vé USED. Admission RESCHEDULED hợp lệ vẫn tính; vượt capacity/đóng cửa phải báo lỗi.

### F10 FactActivityDay

**Grain:** Một hoạt động và ngày danh mục. **Khóa duy nhất:** activity_key + date_key.

**Số đo:** nominal_capacity; is_closed; available_capacity.

**Vai trò ngày:** calendar_date.

**Dimension:** D01 ngày hoạt động; D02 cụm; D11 trung tâm; D12 hoạt động.

**Nguồn:** entertainment_ops.activities(activity_id, centre_id, capacity_per_day); entertainment_ops.closures(closure_id, activity_id, closed_on, reason).

Closure đóng trọn ngày; gộp nhiều lý do trước khi tính. Không có phân bổ capacity theo khách, kênh hoặc khách sạn giới thiệu.

### F11 FactVehicleDay

**Grain:** Một xe và ngày danh mục. **Khóa duy nhất:** vehicle_key + date_key.

**Số đo:** inventory_day=1; maintenance_day; available_day; rented_day.

**Vai trò ngày:** calendar_date; khoảng thuê và bảo trì [start,end).

**Dimension:** D01 ngày xe; D02 cụm; D11 trung tâm; D13 xe.

**Nguồn:** entertainment_ops.vehicles(vehicle_id, centre_id); entertainment_ops.rentals(rental_id, vehicle_id, pickup_date, return_date, status); entertainment_ops.vehicle_maintenance(vehicle_work_id, vehicle_id, starts_on, ends_on).

rented_day từ COMPLETED; overlap thuê hoặc thuê trong bảo trì là lỗi. Không chứa agreed_vnd nhân theo số ngày.

### F12 FactPurchaseLine

**Grain:** Một dòng đặt mua. **Khóa duy nhất:** hotel_ops + purchase_line_id.

**Số đo:** ordered_qty; unit_price_vnd; purchase_order_id.

**Vai trò ngày:** ordered_on; expected_on cho cohort B06; ngày đánh giá A là tham số.

**Dimension:** D01 R: đặt/hẹn; D02 cụm nhận; D03 khách sạn nhận; D14 nhà cung cấp; D15 mặt hàng.

**Nguồn:** hotel_ops.purchase_lines(purchase_line_id, purchase_order_id, item_id, ordered_qty, unit_price_vnd); hotel_ops.purchase_orders(purchase_order_id, hotel_id, supplier_id, ordered_on, expected_on).

Giữ dòng đến hạn không receipt. Ordered_qty tính một lần; không lặp theo từng lần giao. Mỗi A phải tổng lại receipt received_on<=A.

### F13 FactReceipt

**Grain:** Một lần nhận của một dòng đặt mua. **Khóa duy nhất:** hotel_ops + receipt_id.

**Số đo:** accepted_qty; rejected_qty; late_accepted_qty theo expected_on; purchase_line_id.

**Vai trò ngày:** received_on; expected_on để đối chiếu; expires_on là ngày hạn dùng.

**Dimension:** D01 R: nhận/hẹn/hạn; D02 cụm nhận; D03 khách sạn nhận; D14 nhà cung cấp; D15 mặt hàng.

**Nguồn:** hotel_ops.receipts(receipt_id, purchase_line_id, received_on, accepted_qty, rejected_qty, expires_on); hotel_ops.purchase_lines(purchase_line_id, purchase_order_id, item_id, unit_price_vnd); hotel_ops.purchase_orders(purchase_order_id, supplier_id, hotel_id, expected_on).

Feed ngoài là đối chiếu, không cộng thêm receipt. receipt_id cũng là định danh lô; rejected không nhập kho và không thành WASTE.

### F14 FactStockMovement

**Grain:** Một chuyển động của một lô tại khách sạn. **Khóa duy nhất:** hotel_ops + movement_id.

**Số đo:** quantity; signed_qty; in/use/waste_qty; quantity*giá lô; movement_type, usage_area, receipt_id.

**Vai trò ngày:** movement_date; lấy lịch sử trước S cho đầu kỳ.

**Dimension:** D01 ngày biến động; D02 cụm kho; D03 khách sạn quản lý kho; D14 nhà cung cấp lô; D15 mặt hàng.

**Nguồn:** hotel_ops.stock_movements(movement_id, hotel_id, item_id, receipt_id, session_id, movement_date, movement_type, usage_area, quantity); hotel_ops.receipts(receipt_id, purchase_line_id); hotel_ops.purchase_lines(purchase_line_id, purchase_order_id, unit_price_vnd); hotel_ops.purchase_orders(purchase_order_id, supplier_id).

Tồn đầu=sum trước S; cuối=sum trước E. Không có warehouse_id nên chưa tạo DimWarehouse vật lý. usage_area chỉ lọc lượng USE, không lọc tồn. session_id phục vụ drill-through có kiểm soát.

### F15 AggInventoryLotDay

**Grain:** Một lô, khách sạn, mặt hàng và ngày cuối ngày. **Khóa duy nhất:** receipt_id + hotel_key + item_key + date_key.

**Số đo:** closing_qty; closing_value_vnd; in/use/waste trong ngày.

**Vai trò ngày:** snapshot_date, cuối ngày.

**Dimension:** D01 ngày chốt tồn; D02 cụm kho; D03 khách sạn kho; D14 nhà cung cấp lô; D15 mặt hàng.

**Nguồn:** hotel_ops.stock_movements(movement_id, receipt_id, hotel_id, item_id, movement_date, movement_type, quantity).

Tùy chọn vật hóa từ F14. Không cộng closing qua ngày; đầu kỳ lấy cuối ngày trước S hoặc lịch sử F14. Giữ lô còn tồn dù không có movement trong kỳ. Không cộng F14 và F15.

### F16 FactMaintenanceWork

**Grain:** Một công việc bảo trì tài sản khách sạn. **Khóa duy nhất:** hotel_ops + maintenance_id.

**Số đo:** cost_vnd; work_type; status; maintenance_id.

**Vai trò ngày:** starts_on, ends_on; chi phí theo ends_on và COMPLETED.

**Dimension:** D01 R: bắt đầu/kết thúc; D02 cụm; D03 khách sạn; D04 phòng nullable; D16 tài sản.

**Nguồn:** hotel_ops.maintenance(maintenance_id, asset_id, starts_on, ends_on, work_type, cost_vnd, status); hotel_ops.assets(asset_id, hotel_id, room_id, asset_type, supplier_id).

Tiền ghi một lần, không nhân theo ngày. Supplier của asset là bên bán tài sản, không coi là vendor bảo trì. Ngày chặn phòng dùng F02 và bridge overlap.

### F17 FactWeatherDay

**Grain:** Một cụm và ngày thời tiết. **Khóa duy nhất:** site_key + date_key.

**Số đo:** temperature_c; rain_mm; severe_weather; provenance.

**Vai trò ngày:** weather_date.

**Dimension:** D01 ngày thời tiết; D02 cụm.

**Nguồn:** hotel_ops.weather_daily(weather_id, site_id, weather_date, temperature_c, rain_mm, severe_weather, provenance).

Ngữ cảnh B05. Nối 1:1 site/date sau khi xác minh duy nhất hoặc semijoin bộ ngày; không nhân thời tiết theo admission rồi lấy SUM. Không kết luận nhân quả.

## Ma trận 3 Ánh xạ toàn bộ KPI

| KPI | Chỉ tiêu | Fact trực tiếp | Hỗ trợ | Tùy chọn | Ngày nghiệp vụ |
|---|---|---|---|---|---|
| B01.01 | Đêm phòng thực ở | F03 |  |  | stay_date |
| B01.02 | Đêm phòng khả dụng | F02 |  |  | calendar_date |
| B01.03 | Công suất phòng | F03, F02 |  |  | stay_date/calendar_date |
| B01.04 | Tỷ lệ booking hủy | F01 |  |  | bookings.arrival cohort |
| B01.05 | Tỷ lệ booking no-show | F01 |  |  | bookings.arrival cohort |
| B02.01 | Giá trị gói phòng trước giảm | F01 |  |  | bookings.departure |
| B02.02 | Giá trị khách phải trả | F01 |  |  | bookings.departure |
| B02.03 | Chi phí giảm giá CompanyE chịu | F01 |  |  | bookings.departure |
| B02.04 | Phần giảm giá đối tác tài trợ | F01 |  |  | bookings.departure |
| B02.05 | Hoa hồng phân phối | F01 |  |  | bookings.departure |
| B02.06 | Giá trị giữ lại trước chi phí vận hành | F01 |  |  | bookings.departure |
| B03.01 | Booking có mua chéo | F04, F05 | F01 |  | hotel bookings.departure cohort |
| B03.02 | Tỷ lệ booking có mua chéo | F04, F05 | F01 |  | hotel bookings.departure cohort |
| B03.03 | Giá trị vé sau hoàn gắn booking | F04 | F01 |  | hotel bookings.departure cohort |
| B03.04 | Giá trị thuê xe hoàn thành gắn booking | F05 | F01 |  | hotel bookings.departure cohort |
| B03.05 | Giá trị dịch vụ kết hợp của cohort | F01, F04, F05 |  |  | hotel bookings.departure cohort |
| B04.01 | Suất sáng được hưởng | F06 |  |  | service_date |
| B04.02 | Suất sáng quyền lợi thực dùng | F06 |  |  | service_date |
| B04.03 | Tỷ lệ sử dụng quyền lợi sáng | F06 |  |  | service_date |
| B04.04 | Giá trị ăn uống bán riêng sau giảm | F07 |  |  | service_date |
| B04.05 | Lượt phục vụ ăn uống | F06, F07 |  |  | service_date |
| B04.06 | Chi phí nguyên liệu buffet | F08 |  |  | service_date |
| B04.07 | Chi phí nguyên liệu mỗi lượt buffet | F08 |  |  | service_date |
| B04.08 | Điểm đánh giá trung bình theo hóa đơn | F07 |  |  | service_date |
| B05.01 | Lượt sử dụng hoạt động thực tế | F09 |  |  | local date of admissions.entered_at |
| B05.02 | Công suất hoạt động khả dụng | F10 |  |  | calendar_date |
| B05.03 | Tỷ lệ sử dụng hoạt động | F09, F10 |  |  | admission_date/calendar_date |
| B05.04 | Ngày xe được thuê | F11 |  |  | expanded pickup_date to return_date exclusive |
| B05.05 | Ngày xe sẵn sàng | F11 |  |  | calendar_date |
| B05.06 | Tỷ lệ sử dụng đội xe | F11 |  |  | rental_date/calendar_date |
| B06.01 | Lượng đặt đến hạn | F12 |  |  | purchase_orders.expected_on cohort, receipt received_on <= assessment_date |
| B06.02 | Lượng nhận đạt | F13 | F12 |  | purchase_orders.expected_on cohort, receipt received_on <= assessment_date |
| B06.03 | Lượng bị từ chối | F13 | F12 |  | purchase_orders.expected_on cohort, receipt received_on <= assessment_date |
| B06.04 | Lượng nhận đạt nhưng trễ | F13 | F12 |  | purchase_orders.expected_on cohort, receipt received_on <= assessment_date |
| B06.05 | Tỷ lệ đáp ứng lượng đạt | F12, F13 |  |  | purchase_orders.expected_on cohort, receipt received_on <= assessment_date |
| B06.06 | Tỷ lệ từ chối lượng giao | F13 | F12 |  | purchase_orders.expected_on cohort, receipt received_on <= assessment_date |
| B06.07 | Tỷ lệ dòng được nhận đủ đạt đúng hạn | F12, F13 |  |  | purchase_orders.expected_on cohort, receipt received_on <= assessment_date |
| B07.01 | Tồn đầu kỳ | F14 |  | F15 | movement_date; opening before S, closing before E |
| B07.02 | Tồn cuối kỳ | F14 |  | F15 | movement_date; opening before S, closing before E |
| B07.03 | Lượng sử dụng trong kỳ | F14 |  | F15 | movement_date; opening before S, closing before E |
| B07.04 | Lượng hủy trong kỳ | F14 |  | F15 | movement_date; opening before S, closing before E |
| B07.05 | Giá trị hao hụt trong kỳ | F14 |  | F15 | movement_date; opening before S, closing before E |
| B07.06 | Tỷ lệ hao hụt theo giá trị sẵn có | F14 |  | F15 | movement_date; opening before S, closing before E |
| B08.01 | Chi phí bảo trì tài sản khách sạn hoàn tất | F16 |  |  | maintenance.ends_on |
| B08.02 | Ngày phòng ngừng bán do bảo trì | F02 |  |  | maintenance interval intersection with calendar_date |
| B08.03 | Ngày phòng khả dụng | F02 |  |  | calendar_date |
| B08.04 | Tỷ trọng ngày phòng ngừng bán | F02 |  |  | calendar_date |

## Liên kết và chống nhân đôi

| Liên kết | Grain | Khóa | Quy tắc |
|---|---|---|---|
| BridgeBookingRoom | Một booking_room_id | booking_id, room_key, rate_plan_key | EXISTS/COUNTD cho bộ lọc loại phòng của booking; không copy giá F01 lên bridge. |
| BridgeRoomDayMaintenance | Một room_key, date_key, maintenance_id | room_key, date_key, maintenance_id | Giải thích lý do ngừng phòng; F02 lấy hợp DISTINCT. Không SUM cost sau khi nối bridge. |
| ValidatedBookingServiceLink | Một service_type, service_id với booking_ref hợp lệ | service_type, service_id, booking_id | Liên kết n:1 về booking; có thể là view kiểm tra, không bắt buộc bảng bridge vật lý. Bán độc lập giữ NULL; ref sai quarantine. |
| SiteCrosswalk | Một centre_id → một site_id | centres.site_code = sites.site_id | Chỉ ánh xạ công khai trong nguồn; không dùng identity truth hoặc suy theo tên khách. |

## Quy tắc dùng chung giữa hai nhánh

1. Dùng cùng snapshot v2, cùng phiên bản KPI, manifest hash và ánh xạ natural key. Surrogate ID có thể khác giữa hai engine nhưng phải đối chiếu theo natural key và cùng ý nghĩa. Mỗi fact lưu batch_id và nguồn truy vết; nếu giữ nhiều snapshot thì thêm batch_id vào khóa lưu trữ và view chuẩn chỉ đọc một batch đã công bố.

2. Key 0 = Unknown cho quan hệ thiếu chưa xác minh; key -1 = Not applicable cho không khuyến mãi, tài sản chung hoặc bán độc lập. Giữ source ID gốc và lý do. Một ref booking có giá trị nhưng sai không được đổi thành bán độc lập hợp lệ. Thiếu quan hệ bắt buộc phải quarantine hoặc chặn công bố KPI bị ảnh hưởng.

3. Không ghép F01 × F04 × F05 trực tiếp rồi SUM. Tổng vé và xe riêng về booking, LEFT JOIN về cohort COMPLETED. Booking không mua phải còn trong mẫu số B03.02.

4. F06, F07, F08 chỉ tổng hợp về outlet/ngày/bữa trước khi đối chiếu. Chi phí buffet và actual_covers không được nhân theo hóa đơn. B04.05 = redeemed entitlement + covers hóa đơn, không cộng thêm actual_covers.

5. B06 bắt đầu ở dòng đơn đến hạn F12, tổng receipt đến A rồi LEFT JOIN. OTIF theo dòng, không theo đơn hoặc receipt. B07 lấy F14 hoặc F15 có quy tắc thời điểm, không cộng cả hai.

6. Ngày khả dụng B01/B08 cùng F02. Phân rã nguyên nhân qua bridge chỉ dùng DISTINCT room/date, không cộng các nhóm nguyên nhân chồng nhau. Chi phí F16 theo ngày ends_on, không theo ngày chặn phòng.

7. Mọi tỷ lệ dùng tổng tử/tổng mẫu; mẫu 0 = NULL/BLANK. Tiền và lượng dùng decimal; tồn không SUM qua ngày. DimItem chứa base_unit; lượng khác đơn vị không tổng chung.

8. Power BI ưu tiên quan hệ 1:n từ dimension tới fact và một chiều lọc. Các vai trò ngày/cơ sở dùng FK hoặc alias rõ ràng; không bật lọc hai chiều hàng loạt để giải quyết fact-to-fact. Bộ lọc khách/kênh không tác động capacity, usage_area không tác động tồn, work_type chi phí không làm thay đổi tổng phòng khả dụng.

9. Mỗi dim phải nhất quán theo nguồn nhưng không phải dimension nào cũng có mặt ở mọi fact. Không gộp supplier thương mại với OTA chỉ vì cùng gọi vendor. DimSupplier là bên cung ứng; OTA nằm trong DimChannel. Khoản tài trợ CompanyE/đối tác ở F01, chưa cần fact tài trợ nhiều bên vì nguồn v2 chỉ có hai thành phần.

## Những phần không suy diễn từ nguồn

Không tạo DimMenuItem hay fact dòng món từ dining_orders; không tạo nhiều kho khi nguồn chỉ có hotel_id; không coi assets.supplier_id là nhà thầu bảo trì; không hợp nhất khách bằng audit_only. Hội viên/thẻ có trong raw nhưng chưa là chiều bắt buộc của 47 KPI: phân tích lịch sử hội viên cần thêm quy tắc hiệu lực và xử lý nhiều gói, tránh nhân booking. Payments, cash_events, settlements và revisions giữ làm dữ liệu truy vết/đối soát, chưa đưa thành KPI dòng tiền ngoài phạm vi đã chốt.

## Kiểm tra và bước tiếp theo

Kiểm tra tự động bao phủ 47 mã KPI, các mã fact/dimension, tham chiếu bảng/cột nguồn và checksum mã sinh v2. Đây là kiểm tra đặc tả, không phải nghiệm thu phép tính trên Oracle/Iceberg. Tiếp theo chốt kiểu dữ liệu, nullability và ERD vật lý; triển khai ETL; chạy fixture KPI qua từng engine.

## Hồ sơ liên quan

- [Đặc tả KPI](CompanyE_KPI_Specification.md)
- [Hợp đồng mô hình có thể kiểm tra bằng máy](../config/dimensional_model_v1.json)
- [Kết quả kiểm tra đặc tả](../reports/dimensional_model_v1_validation.json)
- Nguồn schema: generated/v2/contracts.json. Mã tái tạo tài liệu: scripts/build-dimensional-spec.py.
