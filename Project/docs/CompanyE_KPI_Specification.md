# Đặc tả KPI CompanyE

**Phiên bản:** 1.0, ngày 12/10/2026. **Phạm vi nghiệp vụ:** B01–B08 đã chốt. **Dữ liệu áp dụng:** v2. **Trạng thái:** đặc tả triển khai, chưa phải kết quả nghiệm thu warehouse hoặc lakehouse.

Hai nhánh Oracle warehouse và Spark–Iceberg lakehouse phải thực hiện cùng các định nghĩa dưới đây. Power BI trình bày cùng kết quả nghiệp vụ, kể cả khi hai nhánh dùng cách lưu trữ hoặc tối ưu khác nhau. Tài liệu gồm 47 chỉ tiêu, trong đó có cả số cơ sở để giải thích tỷ lệ; không yêu cầu 47 biểu đồ hoặc 47 trang báo cáo.

## 1 Quy tắc áp dụng chung

### 1.1 Thời gian và trạng thái dữ liệu

- Múi giờ nghiệp vụ là `Asia/Ho_Chi_Minh`. Chuyển timestamp về múi giờ này trước khi lấy ngày; giữ timestamp UTC phục vụ truy vết.
- Khoảng lọc ngày là `[S,E)`: gồm ngày S, không gồm ngày E. Nếu giao diện cho chọn ngày cuối D, hệ thống chuyển thành E = D + 1 ngày.
- Đêm phòng, ngày xe thuê và ngày bảo trì cũng dùng khoảng nửa mở. Ví dụ nhận phòng 30/01, trả 02/02 tạo ba đêm: 30/01, 31/01, 01/02.
- Báo cáo chuẩn dùng **trạng thái cuối cùng của snapshot v2**, không giả vờ khôi phục toàn bộ điều người quản lý biết tại một ngày lịch sử. `updated_at` và lịch sử sửa giá của 160 booking chưa đủ để tái dựng mọi thay đổi trạng thái trong hai năm.
- Mỗi lần công bố kết quả phải có `source_batch_id`, hash manifest nguồn, `kpi_contract_version`, phiên bản mã xử lý, thời điểm hoàn tất và trạng thái kiểm tra. Hai nhánh so sánh cùng snapshot nguồn; không dùng một nhánh mới hơn nhánh kia.
- Phiên bản sửa đổi cập nhật lại kết quả lịch sử theo ngày nghiệp vụ gốc. Không cộng booking snapshot với các dòng `booking_revisions` như giao dịch mới. File nhận hàng ngoài là bản đối chiếu của receipt nguồn, không là mua hàng bổ sung.
- Lịch ngày phải phủ ngày nghiệp vụ thực tế của mọi nguồn; `booked_on` v2 bắt đầu 02/11/2023. Trang vận hành mặc định 01/01/2024–31/12/2025. Không tự bỏ ngày đặt năm 2023 khi phân tích thời gian đặt trước hoặc dòng tiền.
- Nhịp cập nhật thiết kế: batch hằng ngày sau khi nguồn hoàn tất; demo chạy theo yêu cầu với cùng batch cố định. Đây là mục tiêu vận hành, chưa có scheduler hoặc cam kết thời gian refresh đã triển khai.

### 1.2 Tiền, số lượng và tỷ lệ

- Tiền gốc là số nguyên VND. Phép tính lượng × đơn giá dùng decimal chính xác; không dùng float cho đối soát. Tổng giá trị có phần lẻ do đơn vị lượng được giữ chính xác trước khi định dạng về VND trên giao diện.
- Không suy diễn VAT, doanh thu theo chuẩn kế toán hoặc lợi nhuận ròng từ các trường hiện có. `net_vnd` là giá trị sau giảm của hóa đơn, không tự có nghĩa đã trừ thuế hoặc đã thu tiền.
- Tỷ lệ được lưu dưới dạng phân số 0–1, hiển thị %. Tính `SUM(tử số)/SUM(mẫu số)` tại ngữ cảnh lọc hiện tại; không lấy trung bình các tỷ lệ khách sạn/ngày.
- Mẫu số bằng 0 → `NULL/BLANK`, hiển thị “Không có cơ sở tính”; không biến thành 0%. Không chặn tỷ lệ sai về 100% để che lỗi dữ liệu.
- Nhóm có dữ liệu hợp lệ nhưng không có sự kiện → số đếm/tổng bằng 0. Thiếu nguồn, ngoài phạm vi lịch sử hoặc batch chưa hoàn tất → không trình bày 0 như đã xác minh.
- Không cộng kg với litre hoặc piece. Các KPI số lượng mua/kho chỉ tổng hợp khi cùng mặt hàng và đơn vị; tổng nhiều mặt hàng chỉ hiển thị lượng nếu có ý nghĩa nghiệp vụ rõ ràng. Tại cấp toàn chuỗi ưu tiên giá trị VND hoặc tỷ lệ theo số dòng đơn.
- Số dư kho là chỉ tiêu cộng được theo lô/mặt hàng phù hợp nhưng **không cộng được qua ngày**. Số đếm booking DISTINCT phải tính lại ở cấp tổng nếu booking xuất hiện ở nhiều nhóm.

### 1.3 Nối dữ liệu và phạm vi lọc

- Khóa kỹ thuật phải bao gồm hệ thống nguồn và mã nguồn. Không coi `guest_id` và `customer_id` là cùng miền định danh.
- Bán chéo dùng `hotel_booking_ref` được kiểm tra tồn tại; cụm dùng ánh xạ công khai `centres.site_code = sites.site_id` với SP/DN/DL/PQ. Không dùng `audit_only` hoặc bảng truth để nối dữ liệu khai thác.
- Tổng hợp từng bảng nhiều dòng về đúng grain trước khi nối. Không nối thẳng booking × booking_rooms × tickets × rentals × payments rồi SUM tiền.
- Các dimension không có lịch sử thay đổi trong v2 được coi là thuộc tính hiện hành cố định trong giai đoạn mô phỏng; không tạo lịch sử hạng sao, công suất hay ngày khai trương không có trong nguồn.
- Mỗi visual chỉ nhận bộ lọc tương thích với grain. Công suất toàn khách sạn không chia theo kênh bán hoặc hội viên khi chưa có phân bổ công suất theo những chiều đó. Nếu một slicer không áp dụng, vô hiệu hóa tương tác và ghi nhãn, không ngầm làm thay đổi mẫu số.
- Thời tiết là dữ liệu giả lập theo cụm/ngày. Chỉ nối vào ngày phục vụ tương ứng; kết quả mô tả mối liên hệ, không kết luận tác động nhân quả. Mùa cao/thấp điểm không phải cột nguồn: bản đầu dùng tháng/quý; muốn có mùa phải thêm bảng quy tắc theo cụm được quản lý phiên bản.

### 1.4 Ký hiệu công thức

`COUNTD` là đếm khóa phân biệt; `DIV(a,b)` trả BLANK nếu b = 0. “Trong kỳ” nghĩa là ngày nghiệp vụ nêu tại từng nhóm thuộc `[S,E)`. Các tổng chỉ dùng bản ghi hợp lệ của cùng snapshot. Những tập nền và biến ở mỗi nhóm là một phần của định nghĩa, không được bỏ qua khi triển khai công thức.

## 2 B01 Đánh giá hoạt động lưu trú

**Người dùng và quyết định:** quản lý khách sạn/quản lý doanh thu xem mức sử dụng phòng, điều chỉnh kế hoạch bán và xem xét tình trạng hủy/no-show. **Grain:** phòng × đêm cho công suất; booking cho trạng thái đặt phòng.

**Nguồn:** `hotel_ops.stays` → `booking_rooms` → `bookings`; `rooms` → `hotels` → `sites`; `assets` → `maintenance` để loại phòng ngừng bán.

**Tập nền:** ngày thực ở của booking COMPLETED lấy từ `[stays.checkin_date, stays.checkout_date)`. Danh sách phòng × ngày lấy từ `rooms` và lịch, trừ hợp DISTINCT ngày ngừng bán của tài sản có `room_id` khác NULL. V2 không có thời điểm mở/đóng phòng nên giả định danh mục phòng hoạt động toàn kỳ mô phỏng. Nếu completed stay thiếu hoặc mâu thuẫn nguồn thì chặn công bố chỉ tiêu liên quan, không lấy ngày dự kiến thay thế âm thầm.

| Mã | Chỉ tiêu | Công thức | Đơn vị và cách cộng |
|---|---|---|---|
| B01.01 | Đêm phòng thực ở | COUNTD(room_id, stay_date) trong kỳ từ stay của booking COMPLETED | Đêm phòng; cộng theo ngày/cơ sở không chồng |
| B01.02 | Đêm phòng khả dụng | COUNTD(room_id, date) trong kỳ không ngừng bán | Đêm phòng; cộng theo ngày/cơ sở |
| B01.03 | Công suất phòng | DIV(B01.01, B01.02) | %; tính lại từ tổng |
| B01.04 | Tỷ lệ booking hủy | COUNTD(booking_id có status CANCELLED)/COUNTD(booking_id) trong cohort ngày arrival thuộc kỳ | %; cả ba trạng thái đều vào mẫu số |
| B01.05 | Tỷ lệ booking no-show | COUNTD(booking_id có status NO_SHOW)/COUNTD(booking_id) trong cùng cohort arrival | %; không cộng no-show vào hủy |

**Chiều và hiển thị:** cơ sở, cụm, hạng sao, ngày/tháng; loại phòng cho công suất. Kênh bán chỉ áp dụng B01.04–05 và phân tích đêm đã bán, không mặc nhiên áp dụng mẫu số công suất. Với booking nhiều loại phòng, lọc loại phòng dùng EXISTS và COUNTD; subtotal theo loại phòng có thể chồng booking nên không cộng thành tổng.

**Nghiệm thu:** một booking COMPLETED có hai phòng, mỗi phòng hai đêm → bốn đêm; một CANCELLED và một NO_SHOW → tỷ lệ mỗi loại 1/3 trên ba booking. Hai phòng mở hai ngày, không bảo trì → khả dụng bốn, công suất 100%. Lưu trú qua tháng phải cắt đúng số đêm mỗi tháng. Room-day thực ở bị trùng hoặc trùng bảo trì là lỗi; không chỉ DISTINCT để che overlap.

## 3 B02 Đánh giá kênh bán và khuyến mãi

**Người dùng và quyết định:** kinh doanh/marketing/quản lý doanh thu so sánh giá trị giữ lại theo kênh và cơ cấu tài trợ. **Grain:** một booking hoàn thành ở trạng thái cuối cùng. **Ngày mặc định:** `bookings.departure`, toàn giá trị booking ghi vào kỳ trả phòng; đây là góc nhìn giao dịch hoàn thành, không phải phân bổ doanh thu theo đêm.

**Nguồn:** `bookings`, `channels`, `promotions`, `hotels`, `sites`; `settlements` phục vụ đối soát bổ sung. `booking_revisions` và `booking_room_revisions` phục vụ kiểm tra phiên bản; lấy `bookings` cuối cùng làm đầu vào chính, không cộng thêm các revision.

| Mã | Chỉ tiêu | Công thức trên booking COMPLETED có departure trong kỳ | Đơn vị |
|---|---|---|---|
| B02.01 | Giá trị gói phòng trước giảm | SUM(gross_vnd) | VND |
| B02.02 | Giá trị khách phải trả | SUM(customer_due_vnd) = SUM(gross_vnd − discount_vnd) | VND |
| B02.03 | Chi phí giảm giá CompanyE chịu | SUM(company_share_vnd) | VND |
| B02.04 | Phần giảm giá đối tác tài trợ | SUM(partner_share_vnd) | VND |
| B02.05 | Hoa hồng phân phối | SUM(commission_vnd) | VND |
| B02.06 | Giá trị giữ lại trước chi phí vận hành | B02.01 − B02.03 − B02.05 = B02.02 + B02.04 − B02.05 | VND |

**Chiều:** tháng trả phòng, khách sạn, cụm, hạng sao, kênh, chiến dịch; NULL promotion là “Không khuyến mãi”. Không chia các tổng booking theo room_type/rate_plan nếu chưa có phân bổ giá trị giữa các phòng. Mọi chỉ tiêu trên cộng được theo các nhóm booking rời nhau.

**Giới hạn:** B02.04 là tài trợ theo điều kiện giao dịch, không bảo đảm đã nhận. Kiểm tra `settlements.sponsor_due_vnd`, `sponsor_received_vnd`, `status` và hiển thị pending trong bảng chi tiết; không lấy tiền đã nhận thay cho phần tài trợ được hưởng. Dòng tiền từ `payments` có ngày event_time và có cả hủy/no-show, phải là báo cáo riêng nếu bổ sung; không đặt cùng tên với B02.02. Không có đủ chi phí để gọi B02.06 là lợi nhuận hoặc ROI chiến dịch; không chứng minh khuyến mãi làm tăng doanh số chỉ bằng dữ liệu mô phỏng.

**Nghiệm thu:** hai booking hoàn thành có gross 3.000.000, giảm tổng 300.000, CompanyE chịu 80.000, đối tác 220.000, hoa hồng 200.000 → khách phải trả 2.700.000 và giữ lại 2.720.000. Booking hủy không tham gia. Bản giá 2.000.000 sửa thành 2.050.000 chỉ đóng góp 2.050.000 vào gross; khoản thu bổ sung không được cộng thành doanh số lần nữa.

## 4 B03 Phân tích bán chéo khách sạn và giải trí

**Người dùng và quyết định:** quản lý cụm/kinh doanh đánh giá dịch vụ bán kèm và phối hợp khách sạn–trung tâm. **Grain:** một booking khách sạn làm grain gốc; đơn vé và hợp đồng xe được tổng hợp riêng về booking trước khi nối.

**Cohort:** booking COMPLETED với `departure` trong kỳ. Một booking có mua chéo khi có ít nhất một đơn vé liên kết có `gross_vnd − refunded_vnd > 0`, hoặc một hợp đồng xe liên kết COMPLETED có `agreed_vnd > 0`. Vé UNUSED chưa hoàn vẫn được tính là mua; đây là hành vi mua, không đồng nghĩa đã sử dụng dịch vụ. Vé hoàn toàn bộ và xe hủy không tạo mua chéo.

**Nguồn:** HotelOps `bookings`, `hotels`, `sites`; EntertainmentOps `ticket_orders.hotel_booking_ref`, `rentals.hotel_booking_ref`, `centres`, `vehicles`. Tham chiếu không tồn tại đưa vào kiểm tra chất lượng, không ghép theo tên/số thứ tự khách. Đơn vé không có tham chiếu là bán độc lập, không thuộc numerator hoặc doanh số gắn booking.

| Mã | Chỉ tiêu | Công thức | Đơn vị |
|---|---|---|---|
| B03.01 | Booking có mua chéo | COUNTD(booking_id trong cohort thỏa điều kiện mua chéo) | Booking; DISTINCT |
| B03.02 | Tỷ lệ booking có mua chéo | DIV(B03.01, COUNTD(booking_id COMPLETED trong cohort)) | % |
| B03.03 | Giá trị vé sau hoàn gắn booking | SUM(gross_vnd − refunded_vnd) của các ticket_order liên kết cohort | VND |
| B03.04 | Giá trị thuê xe hoàn thành gắn booking | SUM(agreed_vnd) của rental COMPLETED liên kết cohort | VND |
| B03.05 | Giá trị dịch vụ kết hợp của cohort | SUM(bookings.customer_due_vnd) trong cohort + B03.03 + B03.04 | VND |

**Chiều:** tháng trả phòng, khách sạn đặt phòng, cụm, hạng sao, kênh booking. Phân tích theo loại dịch vụ trình bày tỷ lệ mua vé/thuê xe với cùng mẫu số toàn cohort; không lọc mẫu số chỉ còn người đã mua. B03.01 DISTINCT ở tổng; booking mua cả vé và xe không được đếm hai lần. B03.05 không gồm nhà hàng, tài trợ hay hoa hồng; tên visual phải ghi “Phòng + vé + xe”. Không dùng nó như doanh thu dịch vụ phát sinh đúng trong kỳ, vì dịch vụ liên kết có thể ở ngày khác kỳ trả phòng.

**Nghiệm thu:** B1 có tiền phòng khách trả 2.000.000, hai đơn vé 100.000 và 200.000, một xe 400.000; B2 có phòng 1.000.000, không mua thêm → số mua chéo 1, tỷ lệ 50%, vé 300.000, xe 400.000, kết hợp 3.700.000. Nối nhiều-nhiều không được nhân tiền phòng hoặc xe. Thêm đơn vé hoàn toàn bộ vào B2 không tăng B03.01.

## 5 B04 Đánh giá buffet và nhà hàng

**Người dùng và quyết định:** quản lý nhà hàng/khách sạn lập kế hoạch phục vụ, theo dõi quyền lợi, chi phí buffet và phản hồi dịch vụ. **Ngày:** `service_date`. **Grain:** entitlement phòng/ngày; hóa đơn; phiên outlet/ngày/bữa là ba grain riêng, chỉ nối sau tổng hợp về outlet/ngày/bữa tương thích.

**Nguồn:** `breakfast_entitlements` → `booking_rooms` → `bookings` → khách sạn; `outlets`, `dining_orders`, `meal_sessions`. Ánh xạ entitlement sang nhà hàng trong cùng khách sạn phải duy nhất; v2 có một RESTAURANT mỗi khách sạn. Không tùy tiện chọn một outlet nếu tương lai có nhiều nhà hàng.

| Mã | Chỉ tiêu | Công thức trong kỳ phục vụ | Đơn vị |
|---|---|---|---|
| B04.01 | Suất sáng được hưởng | SUM(eligible_covers) từ entitlement của booking COMPLETED | Suất |
| B04.02 | Suất sáng quyền lợi thực dùng | SUM(redeemed_covers) trên cùng tập entitlement | Suất |
| B04.03 | Tỷ lệ sử dụng quyền lợi sáng | DIV(B04.02, B04.01) | % |
| B04.04 | Giá trị ăn uống bán riêng sau giảm | SUM(dining_orders.net_vnd) | VND |
| B04.05 | Lượt phục vụ ăn uống | SUM(dining_orders.covers) + SUM(redeemed_covers) áp đúng bữa/outlet | Lượt; không phải số khách duy nhất |
| B04.06 | Chi phí nguyên liệu buffet | SUM(meal_sessions.ingredient_cost_vnd) cho BREAKFAST/DINNER | VND |
| B04.07 | Chi phí nguyên liệu mỗi lượt buffet | DIV(B04.06, SUM(meal_sessions.actual_covers) cùng phiên) | VND/lượt |
| B04.08 | Điểm đánh giá trung bình theo hóa đơn | DIV(SUM(rating hợp lệ), COUNT(dining_order_id có rating hợp lệ)) | Điểm trên 5; mỗi hóa đơn một trọng số |

**Chiều:** thời gian phục vụ, cơ sở phục vụ, cụm, hạng sao cơ sở phục vụ, outlet, bữa. Tách nơi đặt phòng khỏi nơi ăn: khách ở E Stay có thể ăn tại E Grand. B04.01–03 chỉ áp dụng BREAKFAST; LUNCH/DINNER/BAR hiển thị không áp dụng, không gán quyền lợi vào những bữa này. B04.06–07 không áp dụng LUNCH/BAR vì nguồn chưa có đủ chi phí theo phiên tương ứng. Chiều kênh/hội viên không áp cho chi phí phiên khi chưa phân bổ.

**Quy tắc:** quyền lợi đi kèm phòng không tạo thêm doanh thu bán riêng. B04.05 dùng hóa đơn + entitlement; `meal_sessions.actual_covers` là số kiểm tra cho buffet, không cộng thêm lần thứ ba. Lượt BAR là lượt phục vụ theo hóa đơn, không phải suất buffet. B04.08 chỉ đại diện các hóa đơn có rating, không bao phủ mọi khách dùng buffet miễn phí. Chi phí nguyên liệu là phân bổ mô phỏng, chưa gồm lao động, điện nước hoặc toàn bộ giá vốn. Quyền lợi/bữa ăn v2 chủ yếu mô phỏng người lớn; không suy thêm suất trẻ em từ booking.

**Nghiệm thu:** ba suất được hưởng, dùng hai; hóa đơn sáng một suất giá 150.000, tối hai suất giá 900.000 → tỷ lệ dùng 2/3, doanh số bán riêng 1.050.000, lượt phục vụ năm. Chi phí phiên sáng 100.000 cho ba lượt, tối 200.000 cho hai lượt → chi phí/lượt tổng = 300.000/5 = 60.000; không lấy trung bình hai đơn giá phiên. Hai hóa đơn rating 4 và 2 → 3/5, bất kể số covers mỗi hóa đơn. Ngày có chi phí nhưng không có lượt buffet phải cảnh báo và trả BLANK cho đơn giá/lượt.

## 6 B05 Đánh giá giải trí và phương tiện

**Người dùng và quyết định:** quản lý trung tâm/đội xe điều chỉnh lịch hoạt động, bố trí xe và nhận diện công suất dư thừa. **Grain:** hoạt động × ngày; xe × ngày; mỗi admission là một lượt.

**Nguồn:** `activities`, `centres`, `closures`, `admissions` → `tickets`; `vehicles`, `vehicle_maintenance`, `rentals`; `weather_daily` qua cụm/ngày. Ngày lượt vào lấy `entered_at` ở +07:00, không dùng ngày bán hoặc original_date. Admission hợp lệ của vé RESCHEDULED vẫn tính; không chỉ đếm status USED.

| Mã | Chỉ tiêu | Công thức | Đơn vị |
|---|---|---|---|
| B05.01 | Lượt sử dụng hoạt động thực tế | COUNTD(admission_id) có ngày vào trong kỳ | Lượt hoạt động |
| B05.02 | Công suất hoạt động khả dụng | SUM(capacity_per_day) trên activity × date trong kỳ không có closure | Lượt công suất |
| B05.03 | Tỷ lệ sử dụng hoạt động | DIV(B05.01, B05.02) | % |
| B05.04 | Ngày xe được thuê | COUNTD(vehicle_id, date) mở rộng `[pickup_date,return_date)` của rental COMPLETED trong kỳ | Ngày xe |
| B05.05 | Ngày xe sẵn sàng | COUNTD(vehicle_id, date) toàn kỳ trừ hợp DISTINCT ngày bảo trì xe | Ngày xe |
| B05.06 | Tỷ lệ sử dụng đội xe | DIV(B05.04, B05.05) | % |

**Chiều:** cụm/trung tâm, ngày/tháng; hoạt động/outdoor cho B05.01–03; loại xe cho B05.04–06; thời tiết theo ngày tương ứng. Không gộp hai tỷ lệ thành “công suất tổng” vì đơn vị khác nhau. Số lượt vào nhiều hoạt động không phải số người duy nhất của trung tâm. Công suất không phân bổ theo sales_channel hoặc khách sạn giới thiệu; không dùng những slicer đó cho mẫu số mặc định.

**Giả định v2:** danh mục hoạt động/xe có hiệu lực toàn kỳ, công suất không đổi; closure là đóng trọn ngày. Không có dữ liệu giảm công suất một phần hoặc khai trương mới. Xe thuê trùng nhau/bảo trì và admission vào ngày đóng hoặc vượt capacity là lỗi cần báo, không âm thầm kẹp về 100%.

**Nghiệm thu:** hoạt động công suất 10/ngày, hai ngày nhưng đóng một ngày, ba lượt vào → 3/10 = 30%. Hai xe trong hai ngày, một xe bảo trì một ngày và có một ngày thuê → 1/3 = 33,333…%. Vé đổi sang ngày hôm sau phải được tính vào ngày admission thật. Toàn kỳ đóng cửa → tỷ lệ BLANK.

## 7 B06 Đánh giá giao hàng nhà cung cấp

**Người dùng và quyết định:** mua hàng/tiếp nhận so sánh mức đáp ứng, chất lượng hàng nhận và giao đúng hẹn. **Grain:** dòng đơn mua; các lần nhận được tổng hợp về dòng đơn trước khi nối.

**Nguồn:** `purchase_orders`, `purchase_lines`, `receipts`, `suppliers`, `items`, `hotels`. Receipt trong DB là nguồn nghiệp vụ chuẩn cho KPI. Feed bên ngoài dùng để kiểm tra/đối chiếu và xử lý phiên bản; không UNION ALL với receipt nguồn thành lượng nhận mới.

**Tập nền:** dòng đơn có `purchase_orders.expected_on` trong kỳ và đã đến hạn tại ngày đánh giá A. A mặc định là cuối ngày vận hành 31/12/2025 của v2; nếu xem A sớm hơn chỉ là tái tính theo ngày sự kiện hiện có, không phải khôi phục snapshot biết tại thời điểm đó. Chỉ nhận receipt có `received_on ≤ A`. Định nghĩa `O` = lượng đặt mỗi dòng; `G` = tổng accepted đến A; `R` = tổng rejected đến A; `L` = accepted có received_on > expected_on và ≤ A; `T` = accepted có received_on ≤ expected_on và ≤ A.

| Mã | Chỉ tiêu | Công thức trên tập dòng đến hạn | Đơn vị |
|---|---|---|---|
| B06.01 | Lượng đặt đến hạn | SUM(O), mỗi purchase_line đúng một lần | Đơn vị chuẩn của mặt hàng |
| B06.02 | Lượng nhận đạt | SUM(G) | Như trên |
| B06.03 | Lượng bị từ chối | SUM(R) | Như trên |
| B06.04 | Lượng nhận đạt nhưng trễ | SUM(L) | Như trên |
| B06.05 | Tỷ lệ đáp ứng lượng đạt | DIV(SUM(G), SUM(O)) | %; chỉ tổng hợp mặt hàng tương thích |
| B06.06 | Tỷ lệ từ chối lượng giao | DIV(SUM(R), SUM(G + R)) | %; chỉ tổng hợp mặt hàng tương thích |
| B06.07 | Tỷ lệ dòng được nhận đủ đạt đúng hạn | COUNTD(line_id có T ≥ O)/COUNTD(line_id đến hạn) | % dòng; dùng được khi có nhiều đơn vị |

**Chiều:** kỳ hẹn giao, nhà cung cấp, khách sạn nhận, cụm, mặt hàng/quy cách/đơn vị. B06.07 là OTIF ở mức dòng theo lượng chấp nhận, không gọi là tỷ lệ toàn đơn đúng hạn. Dòng đến hạn chưa có receipt phải giữ bằng LEFT JOIN: G = R = L = T = 0, vẫn vào mẫu số B06.05 và B06.07. Lượng thiếu đạt = O − G là số giải thích, không nhất thiết là hàng chưa giao vì có thể đã giao nhưng bị từ chối.

**Giới hạn:** v2 đóng lượng đặt bằng accepted + rejected, chưa có vòng đời backorder hoặc thay thế hàng từ chối đầy đủ. Giao trễ nghiệp vụ theo received_on khác với file đến lake muộn theo received_at. Không dùng độ trễ file thay cho độ trễ giao hàng.

**Nghiệm thu:** đặt 10 kg, đúng hạn nhận 6 đạt; hai ngày sau nhận 3 đạt, 1 từ chối → O=10, G=9, R=1, L=3, đáp ứng 90%, từ chối 10%, OTIF dòng 0%. Một dòng khác đến hạn chưa nhận phải hiện nhận đạt 0; không biến mất. Hai dòng giao lần lượt 10/10 đúng hạn và 10/10 trễ → OTIF dòng 50%, dù tổng đáp ứng là 100%. File replay không đổi bất kỳ KPI nào.

## 8 B07 Kiểm soát tồn kho và hao hụt

**Người dùng và quyết định:** quản lý kho/nhà hàng/mua hàng điều chỉnh đặt hàng và theo dõi lượng sử dụng, hủy. **Grain:** lô receipt × khách sạn × mặt hàng; chuyển động kho có ngày. **Nguồn:** `stock_movements` → `receipts` → `purchase_lines` → `items`, `hotels`; đơn giá lô lấy từ purchase_lines.

Đặt signed_qty = +quantity cho IN, −quantity cho USE/WASTE. `Q0` là tổng signed_qty trước S; `I`, `U`, `W` lần lượt là IN, USE, WASTE trong `[S,E)`. `Q1 = Q0 + I − U − W` tương đương tổng signed_qty trước E. V2 giả định tồn trước ngày đầu tiên mô phỏng bằng 0 và sổ chuyển động đầy đủ; không áp giả định này lên dữ liệu thật thiếu số dư đầu kỳ.

| Mã | Chỉ tiêu | Công thức | Đơn vị và cách cộng |
|---|---|---|---|
| B07.01 | Tồn đầu kỳ | SUM(Q0) | Đơn vị chuẩn; không cộng qua thời gian |
| B07.02 | Tồn cuối kỳ | SUM(Q1) | Đơn vị chuẩn; không cộng các tồn cuối ngày |
| B07.03 | Lượng sử dụng trong kỳ | SUM(U) | Đơn vị chuẩn |
| B07.04 | Lượng hủy trong kỳ | SUM(W) | Đơn vị chuẩn |
| B07.05 | Giá trị hao hụt trong kỳ | SUM(quantity × unit_price_vnd) của WASTE trong kỳ theo từng lô | VND; cộng được giữa mặt hàng |
| B07.06 | Tỷ lệ hao hụt theo giá trị sẵn có | DIV(giá trị WASTE trong kỳ, giá trị tồn đầu kỳ + giá trị IN trong kỳ), định giá từng lô | %; tính lại từ tổng giá trị |

**Chiều:** cơ sở kho, cụm, mặt hàng/quy cách/đơn vị, nhà cung cấp của lô, thời gian. B07.03 có thể xem theo usage_area; không dùng usage_area để lọc tồn kho vì IN/USE/WASTE có khu vực khác nhau. Danh mục lô phải giữ cả lô có tồn đầu kỳ nhưng không có chuyển động trong kỳ.

**Quy tắc:** giá trị tồn tính từ lượng còn lại × giá lô; chưa dùng FIFO bình quân hoặc cộng chi phí vận chuyển. Hàng từ chối không nhập kho, không tính lại thành WASTE. Tồn âm hoặc USE trước IN là lỗi. `expires_on` không tự là một giao dịch hủy; chỉ WASTE thật trong sổ mới giảm tồn. Chưa có điều chuyển và kiểm kê điều chỉnh đầy đủ trong v2.

**Nghiệm thu:** lô nhập 10, dùng 6, hủy 2, đơn giá 10.000 → tồn cuối 2, hao hụt 20.000, tỷ lệ hao hụt 20% nếu tồn đầu bằng 0. Kỳ sau có tồn đầu 2, nhập 0, hủy 1 → tồn cuối 1, tỷ lệ hao hụt 50%. Không tính tổng tồn 2 + 1 = 3 cho khoảng hai kỳ; tổng khoảng phải lấy tồn đầu đầu khoảng và tồn cuối cuối khoảng.

## 9 B08 Đánh giá bảo trì và khả năng cung cấp phòng

**Người dùng và quyết định:** kỹ thuật/quản lý khách sạn xem chi phí và mức ảnh hưởng bảo trì tới khả năng bán phòng. **Nguồn:** `maintenance` → `assets` → `rooms`/`hotels`. Chỉ tài sản có `room_id` mới xác định được phòng ngừng bán; tài sản chung không được tự suy ra đóng toàn khách sạn.

**Grain:** công việc bảo trì cho chi phí; room × date cho khả dụng. Chi phí ghi một lần vào `ends_on` của công việc COMPLETED, chọn kỳ theo ends_on. Không nhân chi phí theo số ngày và không phân bổ vào từng ngày khi chưa có quy tắc khác. Ngày ngừng bán cắt giao `[starts_on,ends_on)` với kỳ báo cáo và DISTINCT theo room/date.

| Mã | Chỉ tiêu | Công thức | Đơn vị |
|---|---|---|---|
| B08.01 | Chi phí bảo trì tài sản khách sạn hoàn tất | SUM(cost_vnd) mỗi maintenance_id COMPLETED có ends_on trong kỳ | VND |
| B08.02 | Ngày phòng ngừng bán do bảo trì | COUNTD(room_id, date) thuộc hợp các khoảng bảo trì trong kỳ | Ngày phòng |
| B08.03 | Ngày phòng khả dụng | COUNTD(room_id,date) danh mục trong kỳ − B08.02 | Ngày phòng; bằng B01.02 với cùng bộ lọc |
| B08.04 | Tỷ trọng ngày phòng ngừng bán | DIV(B08.02, COUNTD(room_id,date) danh mục trong kỳ) | % |

**Chiều:** khách sạn, cụm, hạng sao, tháng; loại tài sản và PLANNED/BREAKDOWN cho chi phí. Mặc định chỉ tiêu khả dụng phải trừ tất cả nguyên nhân bảo trì có ảnh hưởng, kể cả khi người dùng chọn một loại công việc trên biểu đồ chi phí. Muốn xem ảnh hưởng từng nguyên nhân dùng B08.02 riêng và tính lại DISTINCT ở tổng, không cộng các subtotal bị chồng. Chi phí gồm tài sản phòng và tài sản chung; không gồm vehicle_maintenance của mảng xe. Không suy số doanh thu mất đi bằng số ngày ngừng × giá phòng nếu chưa có mô hình nhu cầu.

**Nghiệm thu:** R1 bảo trì `[01/01,03/01)` và `[02/01,04/01)`, R2 không bảo trì. Kỳ `[01/01,04/01)` có sáu room-day danh mục, ba bị chặn, ba khả dụng, tỷ trọng 50%. Nếu hai công việc giá 100.000 và 200.000 thì chi phí hoàn tất trong kỳ này chỉ 100.000; công việc ends_on=04/01 thuộc kỳ sau. Chi phí cả hai công việc là 300.000 khi kỳ bao phủ cả hai ngày hoàn tất. Công việc tài sản chung 50.000 tăng chi phí nhưng không tự tăng room-day bị chặn.

## 10 Giao diện Power BI và hợp đồng dùng chung

Một trang tổng quan và tám trang nghiệp vụ B01–B08 là bố cục đề xuất. Mỗi trang có các thẻ KPI chính, xu hướng, bảng phân nhóm và bảng chi tiết để kiểm tra nguồn. Không cần dựng riêng 47 visual. Ngày lọc phải có nhãn rõ: ngày thực ở, ngày nhận phòng dự kiến, ngày trả phòng, ngày phục vụ, ngày hẹn giao hoặc ngày hoàn tất bảo trì.

| Trang | Bộ lọc chính | Đường xem chi tiết |
|---|---|---|
| B01 | Thời gian, cụm, khách sạn, hạng sao; hai vùng lọc ngày phục vụ và cohort arrival rõ ràng | Room-day → stay/booking; trạng thái booking |
| B02 | Kỳ departure, khách sạn, kênh, chiến dịch | Booking → giá cuối/phiên bản/đối soát |
| B03 | Kỳ departure, cụm/khách sạn đặt phòng, kênh | Booking → các đơn vé/xe liên kết |
| B04 | Service date, cơ sở phục vụ, outlet, bữa | Phiên buffet → entitlement/hóa đơn/chuyển động nguyên liệu |
| B05 | Ngày sử dụng, trung tâm, hoạt động/loại xe, thời tiết | Activity-day/vehicle-day → admission/rental/closure/bảo trì |
| B06 | Expected date, ngày đánh giá A, nhà cung cấp, mặt hàng, cơ sở | Purchase line → các lần receipt → bằng chứng file đối chiếu |
| B07 | Khoảng ngày, cơ sở, mặt hàng, nhà cung cấp lô | Lô → các chuyển động trước và trong kỳ |
| B08 | Khoảng ngày, cơ sở; bộ lọc công việc dành cho chi phí | Room-day → công việc/tài sản; chi phí theo ngày kết thúc |

Measure tỷ lệ dùng DIVIDE với alternate result BLANK; không dùng AVERAGE trên cột tỷ lệ đã tính trước. Số dư dùng ngày cuối khoảng được chọn; truy vấn vẫn phải đọc lịch sử trước S để lấy đầu kỳ. Người dùng có thể đổi nguồn báo cáo hoặc xem hai báo cáo cùng thiết kế; lựa chọn kỹ thuật được kiểm chứng khi kết nối Power BI.

Các view/bảng phục vụ hai nhánh phải có tên cột và ý nghĩa tương đương. Measure DAX chỉ làm phép tính trình bày cần thiết; không để một nhánh tính nghiệp vụ trong DAX và nhánh kia trong backend mà không ghi nhận khác biệt. Không dùng Import để kết luận tốc độ truy vấn Oracle/Spark từ thời gian click visual; đo riêng query engine, ETL, refresh và tương tác giao diện.

Khi dữ liệu đến trễ/sửa đổi làm thay đổi kết quả quá khứ, refresh đúng phạm vi dữ liệu hoặc toàn bộ mô hình phù hợp. Cả tám trang phải nhận cùng phiên bản batch đã hoàn tất; chưa thiết kế transaction đa bảng thì dùng quy trình công bố batch nhất quán ở tầng pipeline/ứng dụng.

## 11 Tiêu chí nghiệm thu

### 11.1 Đối chiếu hai nhánh

1. Cùng manifest v2 và phiên bản hợp đồng KPI; batch hoàn tất toàn bộ các bảng liên quan trước khi đối chiếu.
2. Khóa/grain duy nhất, quan hệ hợp lệ; không fan-out. So sánh cả kết quả toàn chuỗi và các lát cắt theo ngày/tháng, cơ sở, kênh, mặt hàng phù hợp.
3. Số đếm và tiền nguyên VND phải khớp chính xác; lượng và giá trị decimal so ở độ chính xác nguồn, không float. Tỷ lệ có cùng tử/mẫu/NULL; sai số cho biểu diễn số thực nếu cần ≤ 1e-9 trước khi hiển thị.
4. Mỗi nhóm chạy ít nhất một fixture tính tay ở các mục 2–9. Thử thêm mẫu số 0, ngày vượt ranh tháng, nhiều dòng con, hủy/hoàn, ghi lại cùng batch, sửa phiên bản, receipt đến trễ và bảo trì chồng nhau.
5. Retry cùng đầu vào không tăng số dòng nghiệp vụ hoặc tổng KPI. Sửa giá phải thay giá trị hiện hành; bản cũ đến sau bản mới không được hạ phiên bản. Receipt ngoài chưa xác minh không được tự tăng lượng nhập trong DB.
6. Kết quả Power BI phải đối chiếu với backend dưới cùng bộ lọc, kể cả tổng/subtotal và BLANK. Dùng fixtures trước, sau đó mới dữ liệu đầy đủ.

### 11.2 Quan hệ với kiểm thử tham chiếu cũ

`tests/fixtures/business_acceptance.json` là hợp đồng tham chiếu cũ, được giữ nguyên để bảo toàn bằng chứng 106 kiểm thử. Nó không bao phủ toàn bộ 47 chỉ tiêu hoặc các quy tắc thời gian của bản đặc tả này. B08 cũ cộng chi phí tất cả công việc fixture mà không lọc ngày hoàn tất; test warehouse mới phải bổ sung đúng quy tắc B08.01. B01 cũ dùng số nights cho trước; triển khai thật phải dùng stays. B03 cũ minh họa chống fan-out; cần thêm trạng thái, hoàn tiền và mẫu số cohort. Không coi việc test cũ đạt là KPI mới đã nghiệm thu.

### 11.3 Chất lượng nguồn và giới hạn

| Phạm vi | Có thể đặc tả trên v2 | Giới hạn phải giữ khi diễn giải |
|---|---|---|
| B01 và B08 | Có phòng, stays và khoảng bảo trì | Chưa có lịch mở/đóng phòng hoặc mọi nguyên nhân out-of-service |
| B02 | Có giá cuối, tài trợ, hoa hồng, đối soát | Không có đủ lợi nhuận, thuế hoặc lịch sử kế toán; lịch sử sửa giá chỉ cho tập chọn |
| B03 | Có booking_ref trực tiếp | Không suy mọi khách đa hệ thống thành một người; không đo causal uplift |
| B04 | Có quyền lợi, hóa đơn và chi phí phiên buffet | Chi phí trưa/bar và quyền lợi trẻ em chưa đầy đủ; rating theo hóa đơn |
| B05 | Có admission, closure, rental và bảo trì xe | Công suất danh mục cố định, không mô phỏng thay đổi theo giờ |
| B06 | Có đơn nhiều mặt hàng, giao nhiều đợt và từ chối | Không đủ backorder/thay thế; số lượng khác đơn vị không cộng chung |
| B07 | Có sổ theo lô và giá mua | Giả định tồn đầu mô phỏng bằng 0; chưa đủ điều chuyển/kiểm kê |

47 chỉ tiêu có thể triển khai từ v2 cùng lịch ngày và những quy tắc đã nêu. Khả năng tính từ nguồn không bảo đảm mọi kết quả đã đạt kiểm thử; báo cáo xác minh nguồn/công thức đính kèm chỉ kiểm tra đặc tả, chưa chạy Oracle/Iceberg/Power BI.

## 12 Hồ sơ liên quan

- `../config/kpi_contract_v1.json`: danh mục chỉ tiêu và ánh xạ cột nguồn, dùng để giữ nhất quán khi triển khai.
- `../reports/kpi_specification_v1_validation.json`: kiểm tra mã KPI, nhóm nghiệp vụ, cột nguồn, hash và các ví dụ tính tay.
- `../CompanyE_Mo_ta_case.md`: case, tám nhu cầu và quyết định warehouse vs lakehouse.
- `../src/model.py`, `../src/model_v2.py`: hợp đồng schema nguồn.
- `../src/generate.py`, `../src/generate_v2.py`: quy tắc mô phỏng đã đóng băng; không sửa trong bước đặc tả KPI.
