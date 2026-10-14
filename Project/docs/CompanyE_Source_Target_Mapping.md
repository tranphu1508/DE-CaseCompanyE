# Mapping nguồn đến kho dữ liệu CompanyE

Phiên bản 1.0, ngày 13/10/2026. Đặc tả bước 2 chuyển dữ liệu lake v2 thành mô hình phân tích dùng chung cho Oracle warehouse và Spark Iceberg lakehouse. Kế thừa thiết kế cột 1.1: 14 dimension SCD Type 2, hai dimension cố định và báo cáo vẫn công bố phần hợp lệ kèm cảnh báo thiếu.

Tài liệu chỉ rõ nguồn, đường nối, điều kiện lọc, phép tính và xử lý lỗi cho toàn bộ 37 entity và 631 cột đích. Biểu thức là pseudocode quan hệ để triển khai tương đương trên hai engine, chưa phải SQL đã chạy. Nguồn, seed và các hợp đồng trước đó được giữ nguyên.

## Cách đọc và phạm vi

Đọc quy tắc R01–R17 trước, sau đó kế hoạch của từng entity. Mỗi entity có alias nguồn, join cardinality, bộ lọc và các bước biến đổi; bảng cột dùng những alias này. Năm cột audit và năm cột SCD được giải thích đầy đủ một lần trong mục dùng chung, đồng thời có mapping riêng cho từng entity trong JSON.

Các công thức và phạm vi KPI đã chốt ở đặc tả KPI vẫn là chuẩn. Khi dữ liệu thiếu, chỉ thay trạng thái chất lượng/phạm vi được tính theo quyết định công bố PARTIAL, không tự sửa công thức để số nhìn hợp lý hơn. Những fixture diễn giải dưới đây không được trộn vào seed v2.

**Điểm cần đọc kỹ khi triển khai:** R07 mô tả cả cập nhật SCD và late correction; R11 phân biệt ngày ăn sáng với đêm ở; R12 giữ dòng mua chưa nhận và phân biệt receipt thiếu do lỗi; R13 bảo vệ số dư khi ledger thiếu; R15 quy định báo cáo PARTIAL; R17 tránh nối giao dịch cũ với quan hệ danh mục hiện tại.

| Ký hiệu | Ý nghĩa |
|---|---|
| `alias.column` | Cột nguồn theo bảng alias trong kế hoạch của entity. Alias chỉ có phạm vi entity đó; r có thể là room, rental hoặc receipt tùy bảng. |
| `$day` | $day là ngày sinh từ EXPAND khoảng hoặc lịch công suất; F15 là ngày chốt số dư. Không phải cột có sẵn trong source. |
| `$calendar_date` | Ngày sinh liên tục cho DimDate, 2023–2026 ở snapshot hiện tại. |
| `DATEKEY / LOCAL_DATE / LOCAL_START / UTC` | Phép biến đổi ngày theo R03; DATEKEY không được nhận NULL trừ nhánh special đã nêu. |
| `LOOKUP_SCD(D,namespace,BK,t)` | Chọn đúng một dimension version theo namespace, BK và interval tại t. R07 định nghĩa xử lý thiếu/trùng. |
| `DIM_ATTR(D,BK,t,attribute)` | Đọc thuộc tính quan hệ từ phiên bản dimension tại t theo R17, không lấy parent hiện hành. |
| `INHERIT_VALIDATED(F01.role)` | Lấy khóa role từ booking fact hợp lệ cùng namespace/BK trong batch; không join F01 để nhân số tiền. |
| `UNION_BRANCH` | Biểu thức theo nhánh UNION đã nêu. Hai nhánh không join hồ sơ khách với nhau; namespace là một phần BK. |
| `EXISTS / SEMI_EXISTS_EXACTLY1` | EXISTS trả 0/1 sau xác minh coverage; semi-join dùng kiểm tra tồn tại, không nhân dòng parent vào kết quả. |
| `SUM / COUNT trong F15` | Thực hiện trên đúng durable lot key và phạm vi ngày đã ghi, sau kiểm tra ledger completeness; ngày đủ dữ liệu không phát sinh mới trả 0. |
| `REGISTRY` | Dịch vụ hoặc bảng cấp khóa dùng chung đã đặc tả; stable key không phụ thuộc thứ tự Spark partition. |
| `MANIFEST / RUN` | Metadata batch đã đóng băng và metadata lần chạy; không lấy ngày hệ thống thay source cutoff. |

## Input lake và các nguồn đối soát

Catalog đang đối chiếu: `lake/v2/catalog/catalog.json`, source batch `v2_20261012T092023738754Z`. Khi chạy batch khác phải resolve lại catalog, không hard-code ID này. Đường `/workspace/...` là đường container trong catalog, tương ứng thư mục Project khi mount; không giả đó là đường tuyệt đối trên Windows.

| Bảng nguồn | Bảng catalog standardized | Entity sử dụng | Vai trò |
|---|---|---|---|
| `hotel_ops.sites` | `companye_v2_hotel.sites` | D02, L04 | Nguồn chính hoặc nguồn lookup theo kế hoạch bảng; không đưa toàn bộ cột nguồn vào warehouse chỉ để sao chép. |
| `hotel_ops.hotels` | `companye_v2_hotel.hotels` | D03, F01, F02, F03, F04, F05, F06, F07, F08, F12, F13, F14, F15, F16 | Nguồn chính hoặc nguồn lookup theo kế hoạch bảng; không đưa toàn bộ cột nguồn vào warehouse chỉ để sao chép. |
| `hotel_ops.rooms` | `companye_v2_hotel.rooms` | D04, F02, F03, F06, L01, L02 | Nguồn chính hoặc nguồn lookup theo kế hoạch bảng; không đưa toàn bộ cột nguồn vào warehouse chỉ để sao chép. |
| `hotel_ops.channels` | `companye_v2_hotel.channels` | D05 | Nguồn chính hoặc nguồn lookup theo kế hoạch bảng; không đưa toàn bộ cột nguồn vào warehouse chỉ để sao chép. |
| `hotel_ops.guests` | `companye_v2_hotel.guests` | D07 | Nguồn chính hoặc nguồn lookup theo kế hoạch bảng; không đưa toàn bộ cột nguồn vào warehouse chỉ để sao chép. |
| `hotel_ops.membership_plans` | `companye_v2_hotel.membership_plans` | Đối soát | Danh mục gói hội viên; chưa có KPI doanh thu hội viên trong B01–B08. |
| `hotel_ops.memberships` | `companye_v2_hotel.memberships` | Đối soát | Đối soát hiệu lực hội viên khi kiểm chứng thẻ; không suy Golden Customer. |
| `hotel_ops.member_cards` | `companye_v2_hotel.member_cards` | Đối soát | Đối chiếu member_card_ref và owner; không tự hợp nhất guest/customer. |
| `hotel_ops.promotions` | `companye_v2_hotel.promotions` | D06 | Nguồn chính hoặc nguồn lookup theo kế hoạch bảng; không đưa toàn bộ cột nguồn vào warehouse chỉ để sao chép. |
| `hotel_ops.rate_plans` | `companye_v2_hotel.rate_plans` | D08, F03, F06, L01 | Nguồn chính hoặc nguồn lookup theo kế hoạch bảng; không đưa toàn bộ cột nguồn vào warehouse chỉ để sao chép. |
| `hotel_ops.bookings` | `companye_v2_hotel.bookings` | F01, F03, F04, F05, F06, F07, L01, L03 | Nguồn chính hoặc nguồn lookup theo kế hoạch bảng; không đưa toàn bộ cột nguồn vào warehouse chỉ để sao chép. |
| `hotel_ops.booking_rooms` | `companye_v2_hotel.booking_rooms` | F03, F06, L01 | Nguồn chính hoặc nguồn lookup theo kế hoạch bảng; không đưa toàn bộ cột nguồn vào warehouse chỉ để sao chép. |
| `hotel_ops.stays` | `companye_v2_hotel.stays` | F03, F06 | Nguồn chính hoặc nguồn lookup theo kế hoạch bảng; không đưa toàn bộ cột nguồn vào warehouse chỉ để sao chép. |
| `hotel_ops.breakfast_entitlements` | `companye_v2_hotel.breakfast_entitlements` | F06 | Nguồn chính hoặc nguồn lookup theo kế hoạch bảng; không đưa toàn bộ cột nguồn vào warehouse chỉ để sao chép. |
| `hotel_ops.outlets` | `companye_v2_hotel.outlets` | D09, F06, F07, F08 | Nguồn chính hoặc nguồn lookup theo kế hoạch bảng; không đưa toàn bộ cột nguồn vào warehouse chỉ để sao chép. |
| `hotel_ops.dining_orders` | `companye_v2_hotel.dining_orders` | F07 | Nguồn chính hoặc nguồn lookup theo kế hoạch bảng; không đưa toàn bộ cột nguồn vào warehouse chỉ để sao chép. |
| `hotel_ops.meal_sessions` | `companye_v2_hotel.meal_sessions` | F08 | Nguồn chính hoặc nguồn lookup theo kế hoạch bảng; không đưa toàn bộ cột nguồn vào warehouse chỉ để sao chép. |
| `hotel_ops.payments` | `companye_v2_hotel.payments` | Đối soát | Đối soát dòng tiền booking; không cộng CHARGE/REFUND vào giá trị booking final. |
| `hotel_ops.settlements` | `companye_v2_hotel.settlements` | Đối soát | Đối soát tài trợ phải thu/đã thu và commission; không thay quyền hưởng tài trợ bằng tiền thực nhận. |
| `hotel_ops.suppliers` | `companye_v2_hotel.suppliers` | D14 | Nguồn chính hoặc nguồn lookup theo kế hoạch bảng; không đưa toàn bộ cột nguồn vào warehouse chỉ để sao chép. |
| `hotel_ops.items` | `companye_v2_hotel.items` | D15 | Nguồn chính hoặc nguồn lookup theo kế hoạch bảng; không đưa toàn bộ cột nguồn vào warehouse chỉ để sao chép. |
| `hotel_ops.purchase_orders` | `companye_v2_hotel.purchase_orders` | F12, F13, F14, F15 | Nguồn chính hoặc nguồn lookup theo kế hoạch bảng; không đưa toàn bộ cột nguồn vào warehouse chỉ để sao chép. |
| `hotel_ops.purchase_lines` | `companye_v2_hotel.purchase_lines` | F12, F13, F14, F15 | Nguồn chính hoặc nguồn lookup theo kế hoạch bảng; không đưa toàn bộ cột nguồn vào warehouse chỉ để sao chép. |
| `hotel_ops.receipts` | `companye_v2_hotel.receipts` | F13, F14, F15 | Nguồn chính hoặc nguồn lookup theo kế hoạch bảng; không đưa toàn bộ cột nguồn vào warehouse chỉ để sao chép. |
| `hotel_ops.stock_movements` | `companye_v2_hotel.stock_movements` | F14 | Nguồn chính hoặc nguồn lookup theo kế hoạch bảng; không đưa toàn bộ cột nguồn vào warehouse chỉ để sao chép. |
| `hotel_ops.assets` | `companye_v2_hotel.assets` | D16, F02, F16, L02 | Nguồn chính hoặc nguồn lookup theo kế hoạch bảng; không đưa toàn bộ cột nguồn vào warehouse chỉ để sao chép. |
| `hotel_ops.maintenance` | `companye_v2_hotel.maintenance` | F02, F16, L02 | Nguồn chính hoặc nguồn lookup theo kế hoạch bảng; không đưa toàn bộ cột nguồn vào warehouse chỉ để sao chép. |
| `hotel_ops.weather_daily` | `companye_v2_hotel.weather_daily` | F17 | Nguồn chính hoặc nguồn lookup theo kế hoạch bảng; không đưa toàn bộ cột nguồn vào warehouse chỉ để sao chép. |
| `hotel_ops.booking_revisions` | `companye_v2_hotel.booking_revisions` | Đối soát | Đối soát lịch sử sửa giá; không append thành booking mới. |
| `hotel_ops.booking_room_revisions` | `companye_v2_hotel.booking_room_revisions` | Đối soát | Đối soát giá phòng sửa theo revision; không tạo đêm hoặc tiền mới. |
| `entertainment_ops.centres` | `companye_v2_entertainment.centres` | D11, F04, F05, F09, F10, F11, L04 | Nguồn chính hoặc nguồn lookup theo kế hoạch bảng; không đưa toàn bộ cột nguồn vào warehouse chỉ để sao chép. |
| `entertainment_ops.customers` | `companye_v2_entertainment.customers` | D07 | Nguồn chính hoặc nguồn lookup theo kế hoạch bảng; không đưa toàn bộ cột nguồn vào warehouse chỉ để sao chép. |
| `entertainment_ops.activities` | `companye_v2_entertainment.activities` | D12, F09, F10 | Nguồn chính hoặc nguồn lookup theo kế hoạch bảng; không đưa toàn bộ cột nguồn vào warehouse chỉ để sao chép. |
| `entertainment_ops.closures` | `companye_v2_entertainment.closures` | F10 | Nguồn chính hoặc nguồn lookup theo kế hoạch bảng; không đưa toàn bộ cột nguồn vào warehouse chỉ để sao chép. |
| `entertainment_ops.ticket_orders` | `companye_v2_entertainment.ticket_orders` | D05, F04, F09, L03 | Nguồn chính hoặc nguồn lookup theo kế hoạch bảng; không đưa toàn bộ cột nguồn vào warehouse chỉ để sao chép. |
| `entertainment_ops.tickets` | `companye_v2_entertainment.tickets` | F09 | Nguồn chính hoặc nguồn lookup theo kế hoạch bảng; không đưa toàn bộ cột nguồn vào warehouse chỉ để sao chép. |
| `entertainment_ops.admissions` | `companye_v2_entertainment.admissions` | F09 | Nguồn chính hoặc nguồn lookup theo kế hoạch bảng; không đưa toàn bộ cột nguồn vào warehouse chỉ để sao chép. |
| `entertainment_ops.vehicles` | `companye_v2_entertainment.vehicles` | D13, F05, F11 | Nguồn chính hoặc nguồn lookup theo kế hoạch bảng; không đưa toàn bộ cột nguồn vào warehouse chỉ để sao chép. |
| `entertainment_ops.vehicle_maintenance` | `companye_v2_entertainment.vehicle_maintenance` | F11 | Nguồn chính hoặc nguồn lookup theo kế hoạch bảng; không đưa toàn bộ cột nguồn vào warehouse chỉ để sao chép. |
| `entertainment_ops.rentals` | `companye_v2_entertainment.rentals` | F05, F11, L03 | Nguồn chính hoặc nguồn lookup theo kế hoạch bảng; không đưa toàn bộ cột nguồn vào warehouse chỉ để sao chép. |
| `entertainment_ops.cash_events` | `companye_v2_entertainment.cash_events` | Đối soát | Đối soát tiền vé/xe và XOR ticket_order/rental; không tạo fact doanh thu ngoài phạm vi. |

Bốn dataset external đã chuẩn hóa gồm `companye_v2_external.receipt_versions`, `receipt_latest`, `receipt_replays`, `receipt_quarantine`. Các dataset này bổ sung bằng chứng chất lượng và đối soát, không UNION vào FactReceipt. Khác biệt giữa revision hợp lệ mới nhất và revision nhận được mới nhất được ghi theo R14.

Hợp đồng JSON kèm source_validation_contracts cho cả 41 bảng: PK, cột bắt buộc, CHECK và 57 FK khai báo trong schema. Đây là kiểm tra đầu vào trước quy tắc nghiệp vụ; không thay thế các điều kiện overlap, ánh xạ liên DB hoặc grain chưa có UNIQUE trong nguồn. Hai UNIQUE bổ sung của revision là (booking_id,revision_no) và (revision_id,booking_room_id); cash_events có XOR ticket_order_id/rental_id theo CHECK nguồn.

## Quy tắc biến đổi dùng chung

### R01 Chọn snapshot và truy vết nguồn

Đầu vào ETL phân tích là các bảng Parquet standardized của lake v2 được catalog chỉ rõ. Không đọc ngẫu nhiên file mới nhất và không trộn nguồn ở hai cutoff khác nhau. Mỗi lần chạy cần phân biệt source_batch_id với run_id kỹ thuật để replay cùng input không tạo giao dịch mới.

1. Đọc catalog và manifest; xác minh batch, phiên bản schema và hash; phân loại nguồn sẵn có, thiếu toàn bảng hoặc không tin cậy.
2. Đóng băng danh sách input path, cutoff, code version và key registry version trước xử lý. Catalog hiện tại là bằng chứng snapshot, không phải đường dẫn cố định cho mọi batch sau.
3. Chỉ đọc cột đã được khai báo. Metadata lake như _ingestion_batch dùng kiểm tra lineage, không là cột nghiệp vụ để tính KPI. Tuyệt đối không đọc audit_only/identity truth.
4. Nguồn thiếu có thể làm báo cáo PARTIAL/UNAVAILABLE theo phạm vi; input không đủ nhận diện hoặc checksum sai phải được đánh dấu không tin cậy, không thay bằng một bảng rỗng đã kiểm chứng.

**Ví dụ:** Hotel snapshot A và entertainment snapshot B không được ghép rồi gắn nhãn cùng batch A. Publication manifest ghi rõ bộ input được chọn cho cả hai nhánh.

### R02 Chuẩn hóa giá trị và kiểu dữ liệu

Chuẩn hóa phục vụ tương đương giữa Oracle và Iceberg, không sửa lại ý nghĩa nguồn. Dữ liệu tiền, lượng và mã phải giữ độ chính xác; chuẩn hóa mạnh có thể làm hai đối tượng khác nhau bị gộp.

1. CSV raw dùng token \N cho NULL; lớp standardized đã có NULL thực. Chuỗi rỗng được coi là NULL chung ở biên ETL; không thay chuỗi mã có nội dung bằng uppercase hoặc trim rồi coi là mã khác.
2. Mã bắt buộc NULL hoặc toàn khoảng trắng bị quarantine. Chuỗi vượt giới hạn đích bị quarantine, không cắt ngắn. Email/phone giữ nguyên, không dùng để hợp nhất khách.
3. Dùng DECIMAL chính xác cho VND/lượng. Parse thất bại, số lẻ ở cột nguyên, vượt precision/scale hoặc miền giá trị đều tạo lỗi. Không COALESCE số tiền bắt buộc về 0.
4. Kiểm tra row-level trước lookup; sai tham chiếu có nội dung khác với NULL được phép. Giữ payload nguồn và mã lỗi để chạy lại.

**Ví dụ:** quantity=1.250 được giữ là DECIMAL với ba số lẻ; quantity=1.2504 không bị âm thầm làm tròn thành 1.250. promotion_id=NULL hợp lệ; promotion_id=P999 không tồn tại là lỗi.

### R03 Ngày nghiệp vụ và khoảng thời gian

Ngày nguồn DATE là ngày địa phương đã xác định, không dịch thêm múi giờ. Timestamp có offset được chuẩn hóa UTC để lưu, rồi chuyển Asia/Ho_Chi_Minh trước khi lấy ngày báo cáo. Khoảng lưu trú, thuê xe và bảo trì đều gồm đầu, loại cuối.

1. DATEKEY(d)=year(d)*10000+month(d)*100+day(d), phải lookup được DimDate. Timestamp không có offset khi contract yêu cầu TIMESTAMPTZ là lỗi, không đoán timezone.
2. LOCAL_START(d) là d 00:00:00 tại +07:00 chuyển UTC, dùng lookup SCD cho nguồn chỉ có ngày. Admission dùng entered_at chính xác.
3. EXPAND(start,end) sinh mỗi ngày start <= d < end; end <= start là lỗi. Kỳ công suất v2 [2024-01-01,2026-01-01); không dùng toàn DimDate làm lịch công suất.
4. DimDate phủ các năm từ min đến max ngày nguồn hợp lệ: hiện 2023–2026. Ngày hạn dùng hoặc booked_on ngoài kỳ công suất vẫn cần thành viên Date; không tự tạo công suất ngoài kỳ.

**Ví dụ:** Check-in 30/01, check-out 02/02 tạo 30/01,31/01,01/02. Admission 2024-01-01T18:30Z thuộc ngày 02/01/2024 tại Việt Nam.

### R04 Nhận diện trùng lặp và lỗi join

Cần phân biệt replay cùng sự kiện, trùng khóa nhưng khác nội dung và nhiều dòng hợp lệ ở grain khác nhau. DISTINCT toàn bảng hoặc lấy first/last không có quy tắc có thể che lỗi nghiệp vụ.

1. Mỗi input structured snapshot có PK duy nhất. Hai dòng cùng PK khác payload: quarantine cả nhóm; không chọn bên thắng bằng thời điểm đọc file.
2. Replay cùng PK và payload chỉ được loại khi có bằng chứng delivery/ingestion; ghi discarded_replay riêng, không tính là quarantine hoặc giao dịch thêm.
3. Join many-to-one phải kiểm tra số parent trước khi join. Parent count=0 với FK bắt buộc: dependency_excluded; >1: ambiguous_join, loại các dòng phụ thuộc.
4. LEFT OPTIONAL: nếu child FK NULL thì xử lý special member; nếu FK có giá trị nhưng parent không tìm thấy thì lỗi. Không dùng INNER JOIN làm mất dòng mà không ghi nhận số lượng.

**Ví dụ:** Một purchase_line có ba receipts là quan hệ 1:N hợp lệ; join rồi SUM ordered_qty là sai vì nhân lượng đặt lên ba lần.

### R05 Khóa bền vững và thành viên đặc biệt

Business key có namespace nhận diện đối tượng; surrogate key SCD nhận diện một phiên bản. Khóa fact phải bền vững khi phiên bản dimension thay đổi để replay và correction không tạo thêm dòng.

1. Đăng ký key registry dùng chung hai nhánh bằng canonical JSON array có thứ tự. Fact dùng unique_keys đầu tiên trong đặc tả; SCD dimension dùng namespace/BK/valid_from_utc.
2. Không nối text bằng dấu phân cách tùy ý và không dùng ROW_NUMBER tái đánh số mỗi batch. Date dùng YYYYMMDD; Meal BREAKFAST/LUNCH/DINNER/BAR lần lượt 1/2/3/4.
3. Mỗi dimension có key 0 UNKNOWN và -1 NOT_APPLICABLE. Những dòng này không tạo phiên bản mới; với SCD: version=1/current=1/valid_to=NULL, thời điểm khởi tạo giống bootstrap.
4. FK có nội dung sai không được đổi thành special member. Dimension thuộc tính không biết có thể NULL nếu contract cho phép; không tự bịa tên, mã hay ngày 1900.

**Ví dụ:** Hóa đơn walk-in không biết guest -> customer_profile_key=0. Booking không promotion -> promotion_key=-1. Receipt chưa biết expires_on -> expires_date_key=0.

### R06 Khởi tạo SCD Type 2 trên dữ liệu giản lược

CompanyE chọn SCD2 để hỗ trợ thay đổi thực tế, nhưng v2 chỉ có snapshot danh mục. Lần nạp đầu không chứng minh lịch sử thực; phải ghi rõ giả định mô phỏng. Các dimension nghiệp vụ dùng SCD2, riêng Date và Meal cố định.

1. Lần đầu mỗi BK hợp lệ tạo một phiên bản. valid_from_utc=2022-12-31T17:00:00Z, tương ứng 01/01/2023 00:00 Việt Nam; valid_to=NULL, is_current=1, version_no=1.
2. effective_time_basis=BOOTSTRAP_ASSUMPTION; không lấy created_at ETL năm 2026 làm ngày bắt đầu vì sẽ không lookup được fact năm 2024.
3. Giả định này chỉ áp cho snapshot v2 hiện tại. BK lần đầu xuất hiện ở batch tương lai dùng thời điểm hiệu lực/quan sát của batch đó, không tự lùi về 2023.
4. Nếu nguồn có nghiệp vụ trước mốc bootstrap hoặc danh mục mở/đóng giữa kỳ, phải sửa hợp đồng phạm vi; không mở rộng giả định âm thầm.

**Ví dụ:** Room R1 có một dòng version=1 bao phủ các đêm v2; không tạo hai phiên bản giống hệt chỉ để minh họa SCD2.

### R07 Cập nhật và lookup phiên bản SCD2

Payload hash của dimension chỉ gồm tracked_attributes đã khai báo. Đổi thuộc tính mới tạo phiên bản, còn việc đọc lại cùng dữ liệu không tạo thay đổi. Cần xét lịch sử có hiệu lực, không chỉ cờ is_current.

1. Từ manifest lấy effective timestamp đáng tin nếu nguồn có; nếu không, dùng observed_at_utc đã đóng băng và basis=OBSERVED_AT. Không lấy thời gian chạy lại làm effective time mới.
2. Nếu payload không đổi tại thời điểm tương ứng: no-op. Nếu đổi ở thời điểm t sau phiên bản hiện tại: đóng old.valid_to=t, old.current=0; mở new.valid_from=t với SK khác. Một BK tối đa một current, intervals không chồng.
3. Sự kiện đến muộn vào một interval cũ: dựng lại các ranh giới theo effective time trong candidate, split interval đúng chỗ, không làm mất thay đổi tương lai đã biết. Cùng BK và cùng effective time khác payload là conflict; quarantine tới khi có quy tắc correction đáng tin.
4. version_no là thứ tự theo valid_from; khi chèn lịch sử có thể cần đánh lại ordinal trong candidate. SK bền vững theo BK+valid_from, không theo version_no. Nếu ranh giới đổi thì cấp SK mới và rekey các fact bị ảnh hưởng; giữ registry cũ để audit.
5. LOOKUP_SCD yêu cầu đúng một interval valid_from<=t và (valid_to IS NULL hoặc t<valid_to). Không có hoặc nhiều interval -> loại dòng phụ thuộc và báo thiếu. Không tự lấy current.
6. Close/open, rekey và metadata quality phải được công bố cùng bộ snapshot. Thiết kế không giả định transaction đa bảng của Iceberg.

**Ví dụ:** Standard hiệu lực trước 01/07, Deluxe từ 01/07: giao dịch đúng 00:00 ngày 01/07 nối Deluxe. A->B->A tạo ba phiên bản khác SK; replay cùng sự kiện B không tạo phiên bản thứ tư.

### R08 Lọc nghiệp vụ khác với loại dữ liệu lỗi

Fact có thể giữ nhiều trạng thái để dùng cho các KPI khác nhau. Bộ lọc KPI không nhất thiết là bộ lọc khi nạp fact. Dòng không thuộc nghiệp vụ được ghi not_applicable, không gọi là dữ liệu thiếu.

1. F01 giữ COMPLETED/CANCELLED/NO_SHOW. Chỉ B02 và cohort B03 lọc COMPLETED; B01.04–05 giữ cả ba trạng thái trong mẫu số.
2. F05 giữ rental COMPLETED/CANCELLED. F11 chỉ mở rộng COMPLETED; F03 và F06 chỉ từ booking COMPLETED. Các bộ lọc này là loại theo nghiệp vụ, không quarantine.
3. Admission có chứng cứ vào thực tế vẫn tính kể cả ticket RESCHEDULED; không lọc chỉ USED. Ticket status khác không tự xóa admission; vi phạm đóng cửa/capacity được kiểm tra riêng.
4. Một bảng nguồn rỗng đã xác nhận đầy đủ khác với bảng không nhận được. Không có sự kiện hợp lệ trong nguồn đầy đủ có thể suy 0, nguồn thiếu hoặc có sự kiện bị loại chỉ cho kết quả partial.

**Ví dụ:** Booking CANCELLED vẫn cần cho tỷ lệ hủy, nhưng không tạo đêm ở và không cộng tiền B02. Đây không phải một booking bị lỗi.

### R09 Tiền giao dịch và chống nhân bản

Các khoản tiền được lưu ở đúng grain nguồn. Danh mục giá hay phần trăm promotion là thuộc tính phân tích, không thay thế giá đã thỏa thuận trong giao dịch.

1. F01 lấy tiền trực tiếp từ bookings final snapshot; đối chiếu gross-discount=customer_due và discount=company_share+partner_share. Không tính lại tiền từ giá phòng hiện hành hoặc discount_bps.
2. Không cộng booking_revisions hoặc payments vào booking gross. Settlements chỉ đối soát phần tài trợ được hưởng/đã nhận; payments là dòng tiền riêng.
3. F04 net_ticket=gross-refunded ở cấp đơn; không lặp giá đơn cho mỗi ticket/admission. F05 agreed_vnd ghi một lần mỗi hợp đồng, không nhân ngày xe.
4. B03 aggregate F04 và F05 riêng về booking rồi LEFT JOIN cohort F01. Bộ lọc loại phòng dùng EXISTS BridgeBookingRoom, không join detail rồi SUM tiền.
5. Giá trị B02 giữ lại trước vận hành không được gọi lợi nhuận; buffet kèm phòng không tạo thêm doanh thu.

**Ví dụ:** Booking tiền phòng 2 triệu, hai đơn vé 100k+200k và một xe 400k -> tổng 2,7 triệu. Join vé x xe không được lặp lại tiền phòng.

### R10 Ngày công suất và xung đột sử dụng

Các fact room-day/activity-day/vehicle-day là lịch công suất, không phải danh sách các giao dịch có phát sinh. Phải giữ cả ngày không có khách để mẫu số không bị thu hẹp.

1. Dựng Cartesian danh mục hợp lệ với lịch kỳ công suất, sau đó lookup dimension tại đầu ngày. V2 giả định danh mục hoạt động toàn kỳ.
2. Room-day blocked là EXISTS ngày nằm trong union khoảng bảo trì của asset thuộc phòng; xe tương tự. Nhiều công việc chồng nhau vẫn chặn một ngày. Closure hoạt động là toàn ngày, gộp nhiều lý do cùng activity/date.
3. Phát hiện hai stays hoặc hai rentals cùng resource/day trước khi DISTINCT. Nhóm bị xung đột không chọn ngẫu nhiên một giao dịch; loại các dòng thuộc conflict scope và gắn cảnh báo.
4. Nếu thiếu hoặc sai dữ liệu bảo trì/closure có thể làm không biết capacity, không tự đặt blocked=0/available=1. Chỉ công bố ngày tài nguyên xác định được; cảnh báo phạm vi còn thiếu.
5. Admission vượt capacity hoặc vào ngày đóng: không kẹp tỷ lệ về 100%; loại cả nhóm vi phạm activity/day khỏi tập admission hợp lệ, ghi số lượt và lý do. Capacity đã xác định độc lập vẫn được giữ, tỷ lệ gắn PARTIAL.

**Ví dụ:** R1 bị chặn [01,03) và [02,04) -> ba ngày chặn, không phải bốn. R2 cùng ba ngày không bảo trì -> tổng khả dụng 3 trên 6 room-day.

### R11 Quyền lợi buffet và nhà hàng

Entitlement, hóa đơn và phiên buffet là ba grain khác nhau; mapping phải bảo toàn vai trò của từng nguồn. Giá trị included breakfast đã nằm trong gói phòng.

1. F06 dùng entitlement nguồn của booking COMPLETED, kiểm tra 0<=redeemed<=eligible, duy nhất booking_room/service_date và tồn tại lưu trú hợp lệ ở ngày đó theo quy ước v2.
2. Đọc rate_plan để xác nhận breakfast_included; không suy tất cả phòng 3 sao đều trả thêm hoặc tự sinh entitlement từ số khách. Mã sinh v2 tạo entitlement từ sáng sau ngày check-in tới sáng ngày checkout: checkin_date < service_date <= checkout_date, tương đương [checkin+1,checkout+1). Kiểm tra đêm đã ở là service_date-1, không phải service_date.
3. Ánh xạ entitlement đến đúng một RESTAURANT thuộc hotel tại ngày phục vụ; 0 hoặc >1 outlet hợp lệ đều là lỗi mapping, không chọn MIN(outlet_id).
4. F07 service hotel lấy từ outlet, booking hotel từ booking optional; khác hotel là hợp lệ. guest_id NULL không tự điền bằng guest booking.
5. B04.05 cộng covers hóa đơn + redeemed entitlement; không cộng actual_covers lần ba. B04.07 dùng tổng chi phí/tổng actual_covers đúng tập phiên BREAKFAST/DINNER.
6. Rating v2 bắt buộc 1..5; sai rating làm dòng F07 không đạt contract và được ghi lỗi, không tự coi là không có đánh giá. B04.08 mỗi hóa đơn một trọng số.

**Ví dụ:** Quyền lợi dùng 2 suất, hóa đơn sáng 1 suất và tối 2 suất -> lượt phục vụ 5. Hai rating 4 và 2 -> trung bình 3, không nhân theo covers.

### R12 Dòng mua hàng và nhận nhiều đợt

F12 lưu lượng đặt một lần; F13 lưu mỗi lần nhận độc lập. Phải giữ dòng mua chưa nhận để đánh giá thiếu hàng và OTIF. Ngày giao hàng thực received_on khác với ngày file tới lake.

1. Nối receipt->purchase_line->purchase_order theo N:1, lấy supplier/hotel/item từ chuỗi này. Kiểm tra lượng không âm và ngày nhận hợp lệ; expires NULL dùng date_key=0, không tự tính từ shelf_life.
2. late_accepted_qty=accepted_qty khi received_on>expected_on, ngược lại 0. Không loại receipt trễ khỏi fact; không dùng ingestion received_at thay received_on.
3. B06 chọn dòng expected_on trong [S,E) và <=A; receipt có received_on<=A. G=sum accepted, R=sum rejected, L=sum late accepted, T=sum accepted nhận trước/đúng hẹn.
4. LEFT JOIN tổng receipt về từng purchase_line. Chỉ COALESCE về 0 khi đã xác định nguồn receipt đủ và dòng không bị quarantine liên quan. Nếu receipt của dòng bị loại, G/R/L/T tính trên phần hợp lệ nhưng gắn PARTIAL, không tuyên bố chưa giao.
5. Các nhóm B06 dùng phân loại dimension của F12 tại ngày đặt để cùng cohort. Không join trực tiếp SCD supplier_key của F13 sang F12 vì cùng supplier có thể khác phiên bản.
6. Không cộng lượng khác base_unit; tỷ lệ dòng OTIF vẫn có thể tổng hợp xuyên đơn vị do đơn vị đếm là dòng.

**Ví dụ:** Đặt 10 kg; đúng hạn nhận 6 đạt, trễ nhận 3 đạt+1 từ chối -> G=9,R=1,L=3,T=6, đáp ứng 90%, từ chối 10%, OTIF=0%.

### R13 Kho và số dư theo lô

Mỗi receipt_id là một lô trong v2. Stock ledger là nguồn thay đổi tồn; giá lô lấy từ purchase_line. Cần đầy đủ lịch sử trước kỳ để tính tồn đầu, không chỉ đọc movement trong khoảng đang xem.

1. signed_qty=+quantity cho IN, -quantity cho USE/WASTE. in/use/waste_qty chọn theo movement_type; movement_value=quantity*unit_price giữ DECIMAL(38,3).
2. Kiểm tra hotel/item của movement khớp PO/line/receipt. Receipt rejected không nhập kho; expires_on không tự tạo WASTE.
3. Tổng tồn theo lô/ngày phải không âm; nguồn chỉ có ngày nên không bịa thứ tự nội ngày. USE/WASTE có ngày trước IN hoặc tồn cuối ngày âm là lỗi; không dùng movement_id để giả timestamp.
4. Nếu bất kỳ movement cần thiết bị loại hoặc nguồn ledger không đầy đủ, số dư lô từ ngày bị ảnh hưởng trở đi không đủ tin cậy. F14 có thể giữ các movement độc lập còn hợp lệ; F15 không công bố số dư của scope bị thiếu và B07 tồn gắn UNAVAILABLE/PARTIAL theo phạm vi.
5. F15 tùy chọn dựng dense lot-day từ nhận hàng hợp lệ tới hết kỳ; giữ cả ngày không phát sinh và ngày số dư bằng 0 để dễ kiểm tra. Cuối ngày d=sum signed_qty<=d. Tồn đầu S lấy số dư S-1 hoặc lịch sử F14 trước S.
6. Không SUM closing_qty qua ngày. Không dùng usage_area lọc tồn; chỉ dùng cho lượng USE. Không cộng F14+F15 thành hai nguồn tồn độc lập.

**Ví dụ:** IN 10, USE 6, WASTE 2 ở giá 10.000 -> còn 2, hao hụt 20.000. Kỳ sau WASTE 1 trên tồn đầu 2 -> hao hụt 50%, không cộng số dư hai kỳ thành 3.

### R14 Feed ngoài và nguồn đối soát

Nguồn nghiệp vụ F13 là receipts trong DB. Feed thương nhân chứa phiên bản/replay và lỗi đơn vị giúp kiểm tra engineering; không đại diện một lần nhận hàng bổ sung.

1. Dùng bốn bảng derived của catalog: receipt_versions, receipt_latest, receipt_replays, receipt_quarantine. Không đọc raw và UNION thêm vào F13.
2. Mã lake hiện hành đổi g/1000 sang kg, giữ kg; đơn vị khác bị quarantine. Đây là quy tắc feed hiện có, không áp đại trà lên lượng DB đã có base_unit. Nếu mở rộng đơn vị phải có conversion contract riêng.
3. event_id lặp cùng payload là replay; khác payload là conflict. receipt_ref/revision trùng identity khác cũng là lỗi. latest chọn revision lớn nhất hợp lệ, không chọn file đến sau cùng.
4. Đối chiếu latest.receipt_ref với receipt_id, purchase_line_ref, supplier_id, hotel_id, accepted_qty_kg và unit_price. DB vẫn là nguồn KPI khi mismatch; đánh dấu reconciliation issue, không tự sửa DB.
5. Nếu phiên bản mới nhất nhận được bị quarantine, latest hợp lệ có thể là bản cũ; phải ghi chưa xác nhận phiên bản mới nhất. received_at chỉ đo độ trễ file, không dùng tính giao trễ B06.
6. Payments/settlements/cash_events/booking_revisions giữ ở lake để đối soát; membership/card không làm Golden Customer và chưa tạo KPI membership ngoài phạm vi 47 chỉ tiêu.

**Ví dụ:** Một receipt 10 kg gửi lại hai lần và có revision sửa 9 kg: replay không tăng lượng, DB receipt chỉ đóng góp một lần theo snapshot; chênh 9 và 10 được báo đối soát.

### R15 Công bố báo cáo thiếu dữ liệu

Người dùng đã chọn vẫn xuất report từ phần hợp lệ. Điều kiện là dữ liệu công bố còn lại phải giữ được grain, khóa và ý nghĩa, đồng thời mô tả rõ phần không đủ. PARTIAL là một trạng thái có chủ đích, không phải âm thầm bỏ lỗi.

1. Mỗi dòng input vào đúng một nhóm: accepted, quarantined trực tiếp, dependency_excluded, business_filtered hoặc replay_discarded. Một dòng nhiều lỗi có danh sách rule nhưng chỉ đếm một lần trong thống kê loại.
2. QualityCoverage ghi expected/input/accepted counts và scope ngày/cơ sở nếu xác định được. Với fact mở rộng ngày, theo dõi riêng số dòng nguồn và số grain đích; không so số room-day với số stay để gọi tỷ lệ đầy đủ.
3. Nếu một bảng input thiếu, expected_count không biết thì để NULL; không khẳng định đầy đủ 0% hoặc 100%. Lỗi không xác định được site/ngày phải lan cảnh báo tới toàn KPI phụ thuộc nguồn đó.
4. MetricQualityStatus theo metric+filter scope: COMPLETE khi đủ; PARTIAL khi tính trên phần hợp lệ nhưng thiếu phần liên quan; UNAVAILABLE khi không thể tính có nghĩa. Mẫu số 0 trả BLANK theo KPI; số 0 chỉ khi đã xác nhận không phát sinh.
5. Tỷ lệ PARTIAL có thể cao hoặc thấp hơn thật; không gọi lower bound hay upper bound trừ khi có chứng minh. Một KPI tổng hợp có thành phần PARTIAL/UNAVAILABLE không được gắn COMPLETE.
6. Publish quality metadata cùng snapshot các bảng. Không trộn tự động dữ liệu batch cũ. Lỗi engine không tạo được snapshot nhất quán -> FAILED; giao diện vẫn có thông báo thiếu hoặc bản trước có nhãn thời gian cũ.

**Ví dụ:** 1.000 booking nguồn, 20 lỗi -> report hiển thị tổng của 980 booking và nhãn thiếu 20. Nếu mất toàn file booking, không hiển thị Doanh thu=0 mà hiển thị Không đủ dữ liệu.

### R16 Tái chạy và sửa đổi

Nạp incremental chưa thể chỉ dựa updated_at vì không phải bảng nào cũng có cột đó. Bản v2 dùng snapshot đầy đủ, xác định diff bằng business key và payload, sau đó cập nhật candidate theo đúng phạm vi ảnh hưởng.

1. Cùng input manifest, cùng transform version và registry phải tạo cùng tập khóa/payload nghiệp vụ; created/updated audit có thể khác lần chạy nhưng không dùng so sánh KPI.
2. Booking sửa tiền cập nhật F01 một dòng; sửa ngày/referral tính lại role/cohort F04/F05/F07 và các bridge phụ thuộc. Dimension đổi không tự rekey mọi fact cũ sang current.
3. Stay/rental/maintenance/closure sửa khoảng: tính lại union của khoảng cũ và mới; xóa dòng đích đã hết hiệu lực trong candidate, không chỉ append ngày mới.
4. Stock correction tính lại F14 và F15 từ ngày sớm nhất ảnh hưởng tới cuối kỳ. Dữ liệu đến muộn được upsert natural key, có thể nâng trạng thái quality của báo cáo sau khi phục hồi.
5. Không suy nguồn bị xóa từ file thiếu. Chỉ xử lý vắng mặt khi full snapshot được xác minh đầy đủ hoặc có tombstone; lưu evidence xóa/đổi và registry trước đó.

**Ví dụ:** Một stay sửa checkout 03/01 thành 02/01: xóa đêm 02/01 ở candidate và giữ các đêm còn hợp lệ; chạy lại không tạo bản sao room-day.

### R17 Quan hệ danh mục tại đúng thời điểm

SCD2 không chỉ áp dụng cho nhãn hiển thị. Khi phòng đổi khách sạn quản lý hoặc khách sạn đổi cụm, quan hệ giữa các đối tượng cũng phải lấy từ phiên bản tại thời điểm fact; nếu lấy hotel_id/site_id từ snapshot hiện tại thì có thể phân loại sai quá khứ.

1. DIM_ATTR(D,BK,t,attribute) chọn đúng phiên bản D theo R07 rồi đọc thuộc tính nguồn trong phiên bản đó. Đây là bước resolve ETL, không tạo FK dimension-to-dimension trong mô hình công bố.
2. Phòng -> hotel lấy từ DimRoom tại t; hotel -> site lấy từ DimHotel tại cùng t. Vehicle/activity -> centre và centre -> site tương tự. Asset -> hotel/room lấy từ DimAsset tại t.
3. Các FK trực tiếp của giao dịch như bookings.hotel_id, purchase_orders.supplier_id là chứng cứ giao dịch; không ghi đè bằng danh mục current. Khi kiểm tra khớp room/rate/hotel phải so phiên bản đúng thời điểm.
4. V2 chỉ một phiên bản nên đọc thuộc tính từ source snapshot cho cùng kết quả. Khi có lịch sử, join raw parent trong kế hoạch chỉ để truy vết/kiểm tra nguồn, biểu thức DIM_ATTR mới quyết định thuộc tính lịch sử.
5. Entitlement tìm đúng một phiên bản DimOutlet NORMAL loại RESTAURANT có hotel_id tương ứng tại service_date. Thiếu/trùng mapping phải báo lỗi. Chính sách đổi outlet giữa kỳ cần effective history, không chọn ngẫu nhiên.
6. Đơn giá lô, giá booking và lượng giao dịch không lấy từ DIM_ATTR giá hiện hành; vẫn giữ giá đã thỏa thuận ở dòng nguồn.

**Ví dụ:** Hotel H từng thuộc site A, từ 01/07 thuộc B: booking 01/06 giữ site A dù file hotels mới đang ghi B. Hai nhánh phải dùng cùng lịch sử dimension để resolve.

## Cột audit và điều khiển SCD

Các cột audit áp dụng cho đủ 37 entity. Với view, metadata được chiếu/tính từ input cùng batch hoặc publication manifest, không giả có một lần INSERT vật lý riêng. Cột SCD chỉ áp dụng D02–D09 và D11–D16; D01 và D10 không version hóa.

| Cột | Biểu thức | Quy tắc đầy đủ |
|---|---|---|
| `source_batch_id` | `MANIFEST.source_batch_id` | Batch nguồn đóng băng dùng tạo/cập nhật dòng; dòng không đổi giữ batch gốc, publication manifest xác định snapshot toàn bảng. |
| `transform_version` | `MANIFEST.transform_version` | Hash hoặc version mã và cấu hình biến đổi; không dùng tên file tùy ý. |
| `created_at_utc` | `INSERT -> RUN.started_at_utc; UPDATE -> existing.created_at_utc` | Đồng hồ ETL, không dùng cho thời gian nghiệp vụ hoặc hiệu lực SCD. |
| `updated_at_utc` | `PAYLOAD_OR_VALIDITY_CHANGED -> RUN.started_at_utc; NOOP -> existing.updated_at_utc` | Đóng interval SCD cập nhật audit dù payload cũ không đổi; replay no-op giữ nguyên. |
| `row_hash` | `SHA256(CANONICAL_BUSINESS_PAYLOAD)` | Dimension: tracked_attributes theo đúng thứ tự design. Fact/link: cột nghiệp vụ theo thứ tự design, FK thay bằng namespace/BK; loại SK, năm cột audit và năm cột SCD. NULL, decimal fixed-scale và timestamp UTC có serialization chung. |
| `valid_from_utc` | `BOOTSTRAP ? 2022-12-31T17:00:00Z : trusted_effective_or_manifest_observed_at` | Dùng R06–R07; source v2 chưa có effective timestamp. BK mới ở batch sau không mặc định lùi về bootstrap. |
| `valid_to_utc` | `NEXT_VERSION.valid_from_utc OR NULL` | Khoảng hiệu lực loại cuối; current không có ngày cuối giả 9999. Close/open phải cùng candidate. |
| `is_current` | `CASE WHEN valid_to_utc IS NULL THEN 1 ELSE 0 END` | Tối đa một current cho mỗi namespace/BK; kiểm tra overlap độc lập với current flag. |
| `version_no` | `ORDINAL_BY_VALID_FROM_PER_BUSINESS_KEY` | V2=1. Ordinal tăng theo hiệu lực, có thể đổi khi chèn lịch sử; không dùng ordinal làm registry identity. |
| `effective_time_basis` | `BOOTSTRAP_ASSUMPTION ∣ SOURCE_EFFECTIVE ∣ OBSERVED_AT` | Ghi rõ nguồn của mốc hiệu lực; observed time không phải bằng chứng thay đổi nghiệp vụ thật. |

**Serialization cho hash:** UTF-8 JSON array không whitespace tùy ý; thứ tự trường theo design. NULL là JSON null; chuỗi giữ Unicode nguyên bản; integer dạng thập phân; decimal là chuỗi fixed-scale; timestamp là chuỗi UTC với 6 chữ số microsecond; date ISO YYYY-MM-DD. Oracle và Spark dùng cùng canonical routine hoặc tập kiểm thử xác nhận byte tương đương, không mặc định hai hàm JSON engine cho cùng hash.

**Sửa lịch sử:** theo R07, SK gắn ranh giới hiệu lực, version_no chỉ là thứ tự. Không dùng version_no như khóa liên kết từ fact. Trường hợp late correction phải staging toàn lịch sử BK bị ảnh hưởng và công bố cùng rekey fact; đây là một ca kiểm thử cần thực hiện khi viết ETL.

## Thứ tự nạp và phụ thuộc

Thứ tự dưới đây là DAG logic sau chuẩn hóa/quality gate nguồn. Các entity cùng mức không phụ thuộc nhau về target; triển khai có thể chạy tuần tự trên máy local để giảm RAM. Chưa cấu hình Spark job hoặc Oracle transaction tại bước này.

1. D01 DimDate, D02 DimSite, D03 DimHotel, D04 DimRoom, D05 DimChannel, D06 DimPromotion, D07 DimCustomerProfile, D08 DimRatePlan, D09 DimOutlet, D10 DimMeal, D11 DimCentre, D12 DimActivity, D13 DimVehicle, D14 DimSupplier, D15 DimItem, D16 DimAsset, L03 ValidatedBookingServiceLink, L04 SiteCrosswalk.
2. F01 FactBooking, F08 FactMealSession, F10 FactActivityDay, F11 FactVehicleDay, F12 FactPurchaseLine, F16 FactMaintenanceWork, F17 FactWeatherDay, L02 BridgeRoomDayMaintenance.
3. F02 FactRoomDay, F04 FactTicketOrder, F05 FactRental, F07 FactDiningOrder, F09 FactAdmission, F13 FactReceipt, L01 BridgeBookingRoom.
4. F03 FactStayNight, F14 FactStockMovement.
5. F06 FactBreakfastEntitlement, F15 AggInventoryLotDay.

Trước mức đầu: đóng băng manifest, parse input, kiểm tra PK/domain/master refs, lập các scope lỗi, cấp special members và registry. Sau mức cuối: đối soát, tạo QualityCoverage/MetricQualityStatus, chạy KPI và publish manifest. F15 là tùy chọn; khi không vật hóa thì B07 dùng F14 với cùng công thức và quality rules.

L03 chỉ kiểm chứng ref nguồn nên không phụ thuộc F04/F05; các fact dịch vụ mới kiểm tra ref đó có F01 hợp lệ. F11 có luồng validation vận hành riêng từ rental nguồn để lỗi booking_ref không tự làm biến mất ngày xe đã sử dụng.

## Kế hoạch và mapping từng entity

### D01 DimDate

**Đích:** `dim_date`. **Grain:** Một thành viên hiện hành cho mỗi business key trong namespace.

**Khóa nghiệp vụ đích:** `calendar_date`.

**Nguồn và alias:** Danh mục sinh xác định, không đọc một bảng giao dịch làm grain..

**Điều kiện chọn:** Lịch Gregorian liên tục 2023-01-01..2026-12-31 từ min/max ngày hợp lệ; thêm hai dòng đặc biệt.

**Trình tự biến đổi:**

1. Thu thập min/max DATE và LOCAL_DATE(TIMESTAMPTZ) từ cả hai DB theo R03.
2. Lịch bao phủ mọi năm có ngày nguồn, nhưng khi tạo công suất phải dùng kỳ riêng 2024–2025.
3. Sinh day/day_of_week Monday=1/month/quarter/year xác định; không suy mùa hoặc ngày lễ khi chưa có bộ quy tắc.

Không có join nhiều bảng ở grain đầu vào; lookup dimension và kiểm tra master reference vẫn áp dụng theo contract.

**Mapping cột nghiệp vụ:**

| Cột đích | Kiểu và NULL | Biểu thức biến đổi | Diễn giải |
|---|---|---|---|
| `date_key` | DATEKEY; NOT NULL | `DATEKEY($calendar_date)` | Không hash rút gọn hoặc tái đánh số mỗi batch; 0/-1 theo R05. |
| `source_system` | CODE; NOT NULL | `'calendar'` | Namespace thuộc ID gốc, không đổi thành tên Oracle/Iceberg; dòng đặc biệt dimension dùng system. |
| `member_kind` | CODE; NOT NULL | `'NORMAL'; special rows 'UNKNOWN'/'NOT_APPLICABLE'` | Hai dòng đặc biệt có các thuộc tính nghiệp vụ NULL; không gán BK giả. |
| `calendar_date` | DATE; NULL; bắt buộc NORMAL | `$calendar_date` | Sinh xác định theo lịch Gregorian; dòng đặc biệt để NULL. |
| `day` | INT; NULL; bắt buộc NORMAL | `DAY($calendar_date)` | Sinh xác định theo lịch Gregorian; dòng đặc biệt để NULL. |
| `day_of_week` | INT; NULL; bắt buộc NORMAL | `ISO_WEEKDAY($calendar_date)` | Sinh xác định theo lịch Gregorian; dòng đặc biệt để NULL. |
| `month` | INT; NULL; bắt buộc NORMAL | `MONTH($calendar_date)` | Sinh xác định theo lịch Gregorian; dòng đặc biệt để NULL. |
| `quarter` | INT; NULL; bắt buộc NORMAL | `FLOOR((MONTH($calendar_date)-1)/3)+1` | Sinh xác định theo lịch Gregorian; dòng đặc biệt để NULL. |
| `year` | INT; NULL; bắt buộc NORMAL | `YEAR($calendar_date)` | Sinh xác định theo lịch Gregorian; dòng đặc biệt để NULL. |

**Cột dùng chung:** `source_batch_id`, `transform_version`, `row_hash`, `created_at_utc`, `updated_at_utc`. Áp dụng đầy đủ mục audit/SCD ở trên; JSON vẫn chứa một mapping cho từng cột.

**Ràng buộc và nghiệm thu:**

- calendar_date duy nhất trên dòng NORMAL; date_key=YYYYMMDD.
- day_of_week: Monday=1..Sunday=7; quarter=1..4; year/month/day lấy từ calendar_date.
- Quy tắc áp dụng: R01, R02, R03, R04, R05, R15, R16, R17.

### D02 DimSite

**Đích:** `dim_site`. **Grain:** Một phiên bản có hiệu lực của một business key trong namespace nguồn.

**Khóa nghiệp vụ đích:** `source_system, site_id, valid_from_utc`; `source_system, site_id, version_no`.

**Nguồn và alias:** `s` = `hotel_ops.sites`.

**Điều kiện chọn:** Mọi bản ghi danh mục đúng PK và miền giá trị; không lọc chỉ đối tượng có giao dịch.

**Trình tự biến đổi:**

1. Kiểm tra các tham chiếu danh mục trong snapshot nguồn; loại ID sai, không tạo dimension suy đoán.
2. Giữ các thuộc tính nguồn khai báo trong design; chạy quy trình SCD2 R06–R07 trên từng namespace/BK.
3. Thuộc tính ID bên trong dimension giữ là thuộc tính denormalized; không dựng snowflake FK dimension-to-dimension.

Không có join nhiều bảng ở grain đầu vào; lookup dimension và kiểm tra master reference vẫn áp dụng theo contract.

**Mapping cột nghiệp vụ:**

| Cột đích | Kiểu và NULL | Biểu thức biến đổi | Diễn giải |
|---|---|---|---|
| `site_key` | KEY; NOT NULL | `REGISTRY(entity_id, namespace, BK, valid_from_utc)` | Không hash rút gọn hoặc tái đánh số mỗi batch; 0/-1 theo R05. |
| `source_system` | CODE; NOT NULL | `'hotel_ops'` | Namespace thuộc ID gốc, không đổi thành tên Oracle/Iceberg; dòng đặc biệt dimension dùng system. |
| `member_kind` | CODE; NOT NULL | `'NORMAL'; special rows 'UNKNOWN'/'NOT_APPLICABLE'` | Hai dòng đặc biệt có các thuộc tính nghiệp vụ NULL; không gán BK giả. |
| `site_id` | ID; NULL; bắt buộc NORMAL | `s.site_id` | Chép giá trị nguồn sau kiểm tra R02; Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Không tính lại bằng danh mục hiện hành. |
| `site_name` | TEXT; NULL; bắt buộc NORMAL | `s.site_name` | Chép giá trị nguồn sau kiểm tra R02; Tên địa điểm. Không tính lại bằng danh mục hiện hành. |
| `climate_region` | TEXT; NULL; bắt buộc NORMAL | `s.climate_region` | Chép giá trị nguồn sau kiểm tra R02; Nhóm khí hậu giả định. Không tính lại bằng danh mục hiện hành. |

**Cột dùng chung:** `valid_from_utc`, `valid_to_utc`, `is_current`, `version_no`, `effective_time_basis`, `source_batch_id`, `transform_version`, `row_hash`, `created_at_utc`, `updated_at_utc`. Áp dụng đầy đủ mục audit/SCD ở trên; JSON vẫn chứa một mapping cho từng cột.

**Ràng buộc và nghiệm thu:**

- site_id xác định BK trong hotel_ops; có thể lặp qua các phiên bản.
- version_no>=1; is_current IN (0,1); is_current=1 iff valid_to_utc IS NULL.
- valid_to NULL hoặc valid_from<valid_to; khoảng [valid_from,valid_to) của cùng BK không chồng nhau.
- Dòng NORMAL cùng BK chỉ một current; cùng effective timestamp mà payload khác -> quarantine, không tự lấy dòng cuối.
- Hai dòng đặc biệt 0/-1 không version hóa: version_no=1, current=1, valid_to=NULL.
- Quy tắc áp dụng: R01, R02, R04, R05, R06, R07, R15, R16, R17.

### D03 DimHotel

**Đích:** `dim_hotel`. **Grain:** Một phiên bản có hiệu lực của một business key trong namespace nguồn.

**Khóa nghiệp vụ đích:** `source_system, hotel_id, valid_from_utc`; `source_system, hotel_id, version_no`.

**Nguồn và alias:** `s` = `hotel_ops.hotels`.

**Điều kiện chọn:** Mọi bản ghi danh mục đúng PK và miền giá trị; không lọc chỉ đối tượng có giao dịch.

**Trình tự biến đổi:**

1. Kiểm tra các tham chiếu danh mục trong snapshot nguồn; loại ID sai, không tạo dimension suy đoán.
2. Giữ các thuộc tính nguồn khai báo trong design; chạy quy trình SCD2 R06–R07 trên từng namespace/BK.
3. Thuộc tính ID bên trong dimension giữ là thuộc tính denormalized; không dựng snowflake FK dimension-to-dimension.

Không có join nhiều bảng ở grain đầu vào; lookup dimension và kiểm tra master reference vẫn áp dụng theo contract.

**Mapping cột nghiệp vụ:**

| Cột đích | Kiểu và NULL | Biểu thức biến đổi | Diễn giải |
|---|---|---|---|
| `hotel_key` | KEY; NOT NULL | `REGISTRY(entity_id, namespace, BK, valid_from_utc)` | Không hash rút gọn hoặc tái đánh số mỗi batch; 0/-1 theo R05. |
| `source_system` | CODE; NOT NULL | `'hotel_ops'` | Namespace thuộc ID gốc, không đổi thành tên Oracle/Iceberg; dòng đặc biệt dimension dùng system. |
| `member_kind` | CODE; NOT NULL | `'NORMAL'; special rows 'UNKNOWN'/'NOT_APPLICABLE'` | Hai dòng đặc biệt có các thuộc tính nghiệp vụ NULL; không gán BK giả. |
| `hotel_id` | ID; NULL; bắt buộc NORMAL | `s.hotel_id` | Chép giá trị nguồn sau kiểm tra R02; Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Không tính lại bằng danh mục hiện hành. |
| `hotel_name` | TEXT; NULL; bắt buộc NORMAL | `s.hotel_name` | Chép giá trị nguồn sau kiểm tra R02; Tên cơ sở. Không tính lại bằng danh mục hiện hành. |
| `stars` | INT; NULL; bắt buộc NORMAL | `s.stars` | Chép giá trị nguồn sau kiểm tra R02; Hạng sao giả định. Không tính lại bằng danh mục hiện hành. |
| `site_id` | ID; NULL; bắt buộc NORMAL | `s.site_id` | Chép giá trị nguồn sau kiểm tra R02; Tham chiếu bản ghi sites trong cùng database. Không tính lại bằng danh mục hiện hành. |
| `website_channel` | TEXT; NULL; bắt buộc NORMAL | `s.website_channel` | Chép giá trị nguồn sau kiểm tra R02; Mã website chính thức riêng. Không tính lại bằng danh mục hiện hành. |

**Cột dùng chung:** `valid_from_utc`, `valid_to_utc`, `is_current`, `version_no`, `effective_time_basis`, `source_batch_id`, `transform_version`, `row_hash`, `created_at_utc`, `updated_at_utc`. Áp dụng đầy đủ mục audit/SCD ở trên; JSON vẫn chứa một mapping cho từng cột.

**Ràng buộc và nghiệm thu:**

- stars IN (3,5); site_id phải tồn tại trong master sites.
- version_no>=1; is_current IN (0,1); is_current=1 iff valid_to_utc IS NULL.
- valid_to NULL hoặc valid_from<valid_to; khoảng [valid_from,valid_to) của cùng BK không chồng nhau.
- Dòng NORMAL cùng BK chỉ một current; cùng effective timestamp mà payload khác -> quarantine, không tự lấy dòng cuối.
- Hai dòng đặc biệt 0/-1 không version hóa: version_no=1, current=1, valid_to=NULL.
- Quy tắc áp dụng: R01, R02, R04, R05, R06, R07, R15, R16, R17.

### D04 DimRoom

**Đích:** `dim_room`. **Grain:** Một phiên bản có hiệu lực của một business key trong namespace nguồn.

**Khóa nghiệp vụ đích:** `source_system, room_id, valid_from_utc`; `source_system, room_id, version_no`.

**Nguồn và alias:** `s` = `hotel_ops.rooms`.

**Điều kiện chọn:** Mọi bản ghi danh mục đúng PK và miền giá trị; không lọc chỉ đối tượng có giao dịch.

**Trình tự biến đổi:**

1. Kiểm tra các tham chiếu danh mục trong snapshot nguồn; loại ID sai, không tạo dimension suy đoán.
2. Giữ các thuộc tính nguồn khai báo trong design; chạy quy trình SCD2 R06–R07 trên từng namespace/BK.
3. Thuộc tính ID bên trong dimension giữ là thuộc tính denormalized; không dựng snowflake FK dimension-to-dimension.

Không có join nhiều bảng ở grain đầu vào; lookup dimension và kiểm tra master reference vẫn áp dụng theo contract.

**Mapping cột nghiệp vụ:**

| Cột đích | Kiểu và NULL | Biểu thức biến đổi | Diễn giải |
|---|---|---|---|
| `room_key` | KEY; NOT NULL | `REGISTRY(entity_id, namespace, BK, valid_from_utc)` | Không hash rút gọn hoặc tái đánh số mỗi batch; 0/-1 theo R05. |
| `source_system` | CODE; NOT NULL | `'hotel_ops'` | Namespace thuộc ID gốc, không đổi thành tên Oracle/Iceberg; dòng đặc biệt dimension dùng system. |
| `member_kind` | CODE; NOT NULL | `'NORMAL'; special rows 'UNKNOWN'/'NOT_APPLICABLE'` | Hai dòng đặc biệt có các thuộc tính nghiệp vụ NULL; không gán BK giả. |
| `room_id` | ID; NULL; bắt buộc NORMAL | `s.room_id` | Chép giá trị nguồn sau kiểm tra R02; Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Không tính lại bằng danh mục hiện hành. |
| `hotel_id` | ID; NULL; bắt buộc NORMAL | `s.hotel_id` | Chép giá trị nguồn sau kiểm tra R02; Tham chiếu bản ghi hotels trong cùng database. Không tính lại bằng danh mục hiện hành. |
| `room_type` | TEXT; NULL; bắt buộc NORMAL | `s.room_type` | Chép giá trị nguồn sau kiểm tra R02; STANDARD hoặc DELUXE. Không tính lại bằng danh mục hiện hành. |
| `capacity` | INT; NULL; bắt buộc NORMAL | `s.capacity` | Chép giá trị nguồn sau kiểm tra R02; Số khách tối đa. Không tính lại bằng danh mục hiện hành. |
| `base_rate_vnd` | MONEY; NULL; bắt buộc NORMAL | `s.base_rate_vnd` | Chép giá trị nguồn sau kiểm tra R02; Giá nền mỗi đêm trước điều chỉnh mùa. Số nguyên VND; không dùng float cho tiền. Không tính lại bằng danh mục hiện hành. |

**Cột dùng chung:** `valid_from_utc`, `valid_to_utc`, `is_current`, `version_no`, `effective_time_basis`, `source_batch_id`, `transform_version`, `row_hash`, `created_at_utc`, `updated_at_utc`. Áp dụng đầy đủ mục audit/SCD ở trên; JSON vẫn chứa một mapping cho từng cột.

**Ràng buộc và nghiệm thu:**

- capacity > 0; base_rate_vnd > 0; hotel_id hợp lệ.
- version_no>=1; is_current IN (0,1); is_current=1 iff valid_to_utc IS NULL.
- valid_to NULL hoặc valid_from<valid_to; khoảng [valid_from,valid_to) của cùng BK không chồng nhau.
- Dòng NORMAL cùng BK chỉ một current; cùng effective timestamp mà payload khác -> quarantine, không tự lấy dòng cuối.
- Hai dòng đặc biệt 0/-1 không version hóa: version_no=1, current=1, valid_to=NULL.
- Quy tắc áp dụng: R01, R02, R04, R05, R06, R07, R15, R16, R17.

### D05 DimChannel

**Đích:** `dim_channel`. **Grain:** Một phiên bản có hiệu lực của một business key trong namespace nguồn.

**Khóa nghiệp vụ đích:** `source_system, channel_code, valid_from_utc`; `source_system, channel_code, version_no`.

**Nguồn và alias:** `h` = `hotel_ops.channels`; `e` = `entertainment_ops.ticket_orders`.

**Điều kiện chọn:** UNION ALL hai namespace: từng hotel channel và DISTINCT sales_channel hợp lệ của entertainment.

**Trình tự biến đổi:**

1. Hotel giữ channel_id/name/type/commission_bps. Entertainment dùng sales_channel làm code và name, type=ENTERTAINMENT_SALES, commission_bps=NULL.
2. DISTINCT chỉ tạo danh mục mã sales_channel, không loại đơn vé khỏi fact. GATE và HOTEL_RECEPTION được quan sát ở v2; mã mới cần xác nhận domain.
3. Cùng chuỗi code ở hai namespace vẫn là hai BK riêng; không ghép theo tên vendor.

Không có join nhiều bảng ở grain đầu vào; lookup dimension và kiểm tra master reference vẫn áp dụng theo contract.

**Mapping cột nghiệp vụ:**

| Cột đích | Kiểu và NULL | Biểu thức biến đổi | Diễn giải |
|---|---|---|---|
| `channel_key` | KEY; NOT NULL | `REGISTRY(entity_id, namespace, BK, valid_from_utc)` | Không hash rút gọn hoặc tái đánh số mỗi batch; 0/-1 theo R05. |
| `source_system` | CODE; NOT NULL | `UNION_BRANCH(h -> 'hotel_ops', e -> 'entertainment_ops')` | Namespace thuộc ID gốc, không đổi thành tên Oracle/Iceberg; dòng đặc biệt dimension dùng system. |
| `member_kind` | CODE; NOT NULL | `'NORMAL'; special rows 'UNKNOWN'/'NOT_APPLICABLE'` | Hai dòng đặc biệt có các thuộc tính nghiệp vụ NULL; không gán BK giả. |
| `channel_code` | ID; NULL; bắt buộc NORMAL | `UNION_BRANCH(h.channel_id,e.sales_channel)` | Nhánh e lấy DISTINCT sales_channel để tạo danh mục; hoa hồng entertainment chưa có thì NULL, không 0. |
| `channel_name` | TEXT; NULL; bắt buộc NORMAL | `UNION_BRANCH(h.channel_name,e.sales_channel)` | Nhánh e lấy DISTINCT sales_channel để tạo danh mục; hoa hồng entertainment chưa có thì NULL, không 0. |
| `channel_type` | TEXT; NULL; bắt buộc NORMAL | `UNION_BRANCH(h.channel_type,'ENTERTAINMENT_SALES')` | Nhánh e lấy DISTINCT sales_channel để tạo danh mục; hoa hồng entertainment chưa có thì NULL, không 0. |
| `commission_bps` | INT; NULL | `UNION_BRANCH(h.commission_bps,NULL)` | Nhánh e lấy DISTINCT sales_channel để tạo danh mục; hoa hồng entertainment chưa có thì NULL, không 0. |

**Cột dùng chung:** `valid_from_utc`, `valid_to_utc`, `is_current`, `version_no`, `effective_time_basis`, `source_batch_id`, `transform_version`, `row_hash`, `created_at_utc`, `updated_at_utc`. Áp dụng đầy đủ mục audit/SCD ở trên; JSON vẫn chứa một mapping cho từng cột.

**Ràng buộc và nghiệm thu:**

- commission_bps 0..10000 nếu có; entertainment channel không có mức hoa hồng thì NULL, không điền 0.
- version_no>=1; is_current IN (0,1); is_current=1 iff valid_to_utc IS NULL.
- valid_to NULL hoặc valid_from<valid_to; khoảng [valid_from,valid_to) của cùng BK không chồng nhau.
- Dòng NORMAL cùng BK chỉ một current; cùng effective timestamp mà payload khác -> quarantine, không tự lấy dòng cuối.
- Hai dòng đặc biệt 0/-1 không version hóa: version_no=1, current=1, valid_to=NULL.
- Quy tắc áp dụng: R01, R02, R04, R05, R06, R07, R15, R16, R17.

### D06 DimPromotion

**Đích:** `dim_promotion`. **Grain:** Một phiên bản có hiệu lực của một business key trong namespace nguồn.

**Khóa nghiệp vụ đích:** `source_system, promotion_id, valid_from_utc`; `source_system, promotion_id, version_no`.

**Nguồn và alias:** `s` = `hotel_ops.promotions`.

**Điều kiện chọn:** Mọi bản ghi danh mục đúng PK và miền giá trị; không lọc chỉ đối tượng có giao dịch.

**Trình tự biến đổi:**

1. Kiểm tra các tham chiếu danh mục trong snapshot nguồn; loại ID sai, không tạo dimension suy đoán.
2. Giữ các thuộc tính nguồn khai báo trong design; chạy quy trình SCD2 R06–R07 trên từng namespace/BK.
3. Thuộc tính ID bên trong dimension giữ là thuộc tính denormalized; không dựng snowflake FK dimension-to-dimension.

Không có join nhiều bảng ở grain đầu vào; lookup dimension và kiểm tra master reference vẫn áp dụng theo contract.

**Mapping cột nghiệp vụ:**

| Cột đích | Kiểu và NULL | Biểu thức biến đổi | Diễn giải |
|---|---|---|---|
| `promotion_key` | KEY; NOT NULL | `REGISTRY(entity_id, namespace, BK, valid_from_utc)` | Không hash rút gọn hoặc tái đánh số mỗi batch; 0/-1 theo R05. |
| `source_system` | CODE; NOT NULL | `'hotel_ops'` | Namespace thuộc ID gốc, không đổi thành tên Oracle/Iceberg; dòng đặc biệt dimension dùng system. |
| `member_kind` | CODE; NOT NULL | `'NORMAL'; special rows 'UNKNOWN'/'NOT_APPLICABLE'` | Hai dòng đặc biệt có các thuộc tính nghiệp vụ NULL; không gán BK giả. |
| `promotion_id` | ID; NULL; bắt buộc NORMAL | `s.promotion_id` | Chép giá trị nguồn sau kiểm tra R02; Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Không tính lại bằng danh mục hiện hành. |
| `promotion_name` | TEXT; NULL; bắt buộc NORMAL | `s.promotion_name` | Chép giá trị nguồn sau kiểm tra R02; Tên chiến dịch. Không tính lại bằng danh mục hiện hành. |
| `channel_id` | ID; NULL | `s.channel_id` | Chép giá trị nguồn sau kiểm tra R02; Tham chiếu bản ghi channels trong cùng database. Không tính lại bằng danh mục hiện hành. |
| `site_id` | ID; NULL | `s.site_id` | Chép giá trị nguồn sau kiểm tra R02; Tham chiếu bản ghi sites trong cùng database. Không tính lại bằng danh mục hiện hành. |
| `sale_from` | DATE; NULL; bắt buộc NORMAL | `s.sale_from` | Chép giá trị nguồn sau kiểm tra R02; Bắt đầu mở bán. Không tính lại bằng danh mục hiện hành. |
| `sale_to` | DATE; NULL; bắt buộc NORMAL | `s.sale_to` | Chép giá trị nguồn sau kiểm tra R02; Kết thúc mở bán. Không tính lại bằng danh mục hiện hành. |
| `stay_from` | DATE; NULL; bắt buộc NORMAL | `s.stay_from` | Chép giá trị nguồn sau kiểm tra R02; Bắt đầu khoảng lưu trú hợp lệ. Không tính lại bằng danh mục hiện hành. |
| `stay_to` | DATE; NULL; bắt buộc NORMAL | `s.stay_to` | Chép giá trị nguồn sau kiểm tra R02; Kết thúc khoảng lưu trú hợp lệ. Không tính lại bằng danh mục hiện hành. |
| `discount_bps` | INT; NULL; bắt buộc NORMAL | `s.discount_bps` | Chép giá trị nguồn sau kiểm tra R02; Tỷ lệ giảm trên giá gói. Không tính lại bằng danh mục hiện hành. |
| `partner_share_bps` | INT; NULL; bắt buộc NORMAL | `s.partner_share_bps` | Chép giá trị nguồn sau kiểm tra R02; Tỷ lệ đối tác chịu trong phần giảm. Không tính lại bằng danh mục hiện hành. |
| `cap_vnd` | MONEY; NULL; bắt buộc NORMAL | `s.cap_vnd` | Chép giá trị nguồn sau kiểm tra R02; Giới hạn giảm mỗi booking. Số nguyên VND; không dùng float cho tiền. Không tính lại bằng danh mục hiện hành. |

**Cột dùng chung:** `valid_from_utc`, `valid_to_utc`, `is_current`, `version_no`, `effective_time_basis`, `source_batch_id`, `transform_version`, `row_hash`, `created_at_utc`, `updated_at_utc`. Áp dụng đầy đủ mục audit/SCD ở trên; JSON vẫn chứa một mapping cho từng cột.

**Ràng buộc và nghiệm thu:**

- discount_bps và partner_share_bps 0..10000; cap_vnd >= 0; sale_to>=sale_from; stay_to>=stay_from.
- NULL channel_id/site_id nghĩa là không giới hạn phạm vi tương ứng, không phải sai FK.
- version_no>=1; is_current IN (0,1); is_current=1 iff valid_to_utc IS NULL.
- valid_to NULL hoặc valid_from<valid_to; khoảng [valid_from,valid_to) của cùng BK không chồng nhau.
- Dòng NORMAL cùng BK chỉ một current; cùng effective timestamp mà payload khác -> quarantine, không tự lấy dòng cuối.
- Hai dòng đặc biệt 0/-1 không version hóa: version_no=1, current=1, valid_to=NULL.
- Quy tắc áp dụng: R01, R02, R04, R05, R06, R07, R15, R16, R17.

### D07 DimCustomerProfile

**Đích:** `dim_customer_profile`. **Grain:** Một phiên bản có hiệu lực của một business key trong namespace nguồn.

**Khóa nghiệp vụ đích:** `source_system, source_customer_id, valid_from_utc`; `source_system, source_customer_id, version_no`.

**Nguồn và alias:** `h` = `hotel_ops.guests`; `e` = `entertainment_ops.customers`.

**Điều kiện chọn:** UNION ALL hồ sơ hotel và entertainment, mỗi nguồn giữ ID riêng.

**Trình tự biến đổi:**

1. Giữ full_name/phone/email đúng nguồn; hotel member_card_ref=NULL vì bảng guests không có cột đó.
2. Thẻ từ entertainment là tham chiếu nguồn, không là căn cứ gộp hai customer profile. Kiểm tra thẻ để đối soát riêng, không làm thay đổi PK hồ sơ.
3. Không enrich membership validity vào profile hiện hành hoặc suy ra khách duy nhất toàn tập đoàn.

Không có join nhiều bảng ở grain đầu vào; lookup dimension và kiểm tra master reference vẫn áp dụng theo contract.

**Mapping cột nghiệp vụ:**

| Cột đích | Kiểu và NULL | Biểu thức biến đổi | Diễn giải |
|---|---|---|---|
| `customer_profile_key` | KEY; NOT NULL | `REGISTRY(entity_id, namespace, BK, valid_from_utc)` | Không hash rút gọn hoặc tái đánh số mỗi batch; 0/-1 theo R05. |
| `source_system` | CODE; NOT NULL | `UNION_BRANCH(h -> 'hotel_ops', e -> 'entertainment_ops')` | Namespace thuộc ID gốc, không đổi thành tên Oracle/Iceberg; dòng đặc biệt dimension dùng system. |
| `member_kind` | CODE; NOT NULL | `'NORMAL'; special rows 'UNKNOWN'/'NOT_APPLICABLE'` | Hai dòng đặc biệt có các thuộc tính nghiệp vụ NULL; không gán BK giả. |
| `source_customer_id` | ID; NULL; bắt buộc NORMAL | `UNION_BRANCH(h.guest_id,e.customer_id)` | Hai namespace riêng, không match tên/phone/email hoặc dùng identity truth; không suy khách hotel từ thẻ. |
| `full_name` | TEXT; NULL; bắt buộc NORMAL | `UNION_BRANCH(h.full_name,e.full_name)` | Hai namespace riêng, không match tên/phone/email hoặc dùng identity truth; không suy khách hotel từ thẻ. |
| `phone` | TEXT; NULL | `UNION_BRANCH(h.phone,e.phone)` | Hai namespace riêng, không match tên/phone/email hoặc dùng identity truth; không suy khách hotel từ thẻ. |
| `email` | TEXT; NULL | `UNION_BRANCH(h.email,e.email)` | Hai namespace riêng, không match tên/phone/email hoặc dùng identity truth; không suy khách hotel từ thẻ. |
| `member_card_ref` | ID; NULL | `UNION_BRANCH(NULL,e.member_card_ref)` | Hai namespace riêng, không match tên/phone/email hoặc dùng identity truth; không suy khách hotel từ thẻ. |

**Cột dùng chung:** `valid_from_utc`, `valid_to_utc`, `is_current`, `version_no`, `effective_time_basis`, `source_batch_id`, `transform_version`, `row_hash`, `created_at_utc`, `updated_at_utc`. Áp dụng đầy đủ mục audit/SCD ở trên; JSON vẫn chứa một mapping cho từng cột.

**Ràng buộc và nghiệm thu:**

- Không ghép hồ sơ khách theo tên/phone/email hoặc audit_only.
- member_card_ref NULL cho khách không có thẻ và hồ sơ hotel; không suy ra trạng thái hội viên đang hiệu lực.
- version_no>=1; is_current IN (0,1); is_current=1 iff valid_to_utc IS NULL.
- valid_to NULL hoặc valid_from<valid_to; khoảng [valid_from,valid_to) của cùng BK không chồng nhau.
- Dòng NORMAL cùng BK chỉ một current; cùng effective timestamp mà payload khác -> quarantine, không tự lấy dòng cuối.
- Hai dòng đặc biệt 0/-1 không version hóa: version_no=1, current=1, valid_to=NULL.
- Quy tắc áp dụng: R01, R02, R04, R05, R06, R07, R15, R16, R17.

### D08 DimRatePlan

**Đích:** `dim_rate_plan`. **Grain:** Một phiên bản có hiệu lực của một business key trong namespace nguồn.

**Khóa nghiệp vụ đích:** `source_system, rate_plan_id, valid_from_utc`; `source_system, rate_plan_id, version_no`.

**Nguồn và alias:** `s` = `hotel_ops.rate_plans`.

**Điều kiện chọn:** Mọi bản ghi danh mục đúng PK và miền giá trị; không lọc chỉ đối tượng có giao dịch.

**Trình tự biến đổi:**

1. Kiểm tra các tham chiếu danh mục trong snapshot nguồn; loại ID sai, không tạo dimension suy đoán.
2. Giữ các thuộc tính nguồn khai báo trong design; chạy quy trình SCD2 R06–R07 trên từng namespace/BK.
3. Thuộc tính ID bên trong dimension giữ là thuộc tính denormalized; không dựng snowflake FK dimension-to-dimension.

Không có join nhiều bảng ở grain đầu vào; lookup dimension và kiểm tra master reference vẫn áp dụng theo contract.

**Mapping cột nghiệp vụ:**

| Cột đích | Kiểu và NULL | Biểu thức biến đổi | Diễn giải |
|---|---|---|---|
| `rate_plan_key` | KEY; NOT NULL | `REGISTRY(entity_id, namespace, BK, valid_from_utc)` | Không hash rút gọn hoặc tái đánh số mỗi batch; 0/-1 theo R05. |
| `source_system` | CODE; NOT NULL | `'hotel_ops'` | Namespace thuộc ID gốc, không đổi thành tên Oracle/Iceberg; dòng đặc biệt dimension dùng system. |
| `member_kind` | CODE; NOT NULL | `'NORMAL'; special rows 'UNKNOWN'/'NOT_APPLICABLE'` | Hai dòng đặc biệt có các thuộc tính nghiệp vụ NULL; không gán BK giả. |
| `rate_plan_id` | ID; NULL; bắt buộc NORMAL | `s.rate_plan_id` | Chép giá trị nguồn sau kiểm tra R02; Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Không tính lại bằng danh mục hiện hành. |
| `hotel_id` | ID; NULL; bắt buộc NORMAL | `s.hotel_id` | Chép giá trị nguồn sau kiểm tra R02; Tham chiếu bản ghi hotels trong cùng database. Không tính lại bằng danh mục hiện hành. |
| `channel_id` | ID; NULL; bắt buộc NORMAL | `s.channel_id` | Chép giá trị nguồn sau kiểm tra R02; Tham chiếu bản ghi channels trong cùng database. Không tính lại bằng danh mục hiện hành. |
| `plan_name` | TEXT; NULL; bắt buộc NORMAL | `s.plan_name` | Chép giá trị nguồn sau kiểm tra R02; Tên sản phẩm đặt phòng. Không tính lại bằng danh mục hiện hành. |
| `breakfast_included` | FLAG; NULL; bắt buộc NORMAL | `s.breakfast_included` | Chép giá trị nguồn sau kiểm tra R02; 1 gồm ăn sáng, 0 không gồm. Không tính lại bằng danh mục hiện hành. |
| `refundable` | FLAG; NULL; bắt buộc NORMAL | `s.refundable` | Chép giá trị nguồn sau kiểm tra R02; 1 cho phép hoàn theo điều kiện. Không tính lại bằng danh mục hiện hành. |

**Cột dùng chung:** `valid_from_utc`, `valid_to_utc`, `is_current`, `version_no`, `effective_time_basis`, `source_batch_id`, `transform_version`, `row_hash`, `created_at_utc`, `updated_at_utc`. Áp dụng đầy đủ mục audit/SCD ở trên; JSON vẫn chứa một mapping cho từng cột.

**Ràng buộc và nghiệm thu:**

- breakfast_included và refundable IN (0,1); hotel_id/channel_id hợp lệ.
- version_no>=1; is_current IN (0,1); is_current=1 iff valid_to_utc IS NULL.
- valid_to NULL hoặc valid_from<valid_to; khoảng [valid_from,valid_to) của cùng BK không chồng nhau.
- Dòng NORMAL cùng BK chỉ một current; cùng effective timestamp mà payload khác -> quarantine, không tự lấy dòng cuối.
- Hai dòng đặc biệt 0/-1 không version hóa: version_no=1, current=1, valid_to=NULL.
- Quy tắc áp dụng: R01, R02, R04, R05, R06, R07, R15, R16, R17.

### D09 DimOutlet

**Đích:** `dim_outlet`. **Grain:** Một phiên bản có hiệu lực của một business key trong namespace nguồn.

**Khóa nghiệp vụ đích:** `source_system, outlet_id, valid_from_utc`; `source_system, outlet_id, version_no`.

**Nguồn và alias:** `s` = `hotel_ops.outlets`.

**Điều kiện chọn:** Mọi bản ghi danh mục đúng PK và miền giá trị; không lọc chỉ đối tượng có giao dịch.

**Trình tự biến đổi:**

1. Kiểm tra các tham chiếu danh mục trong snapshot nguồn; loại ID sai, không tạo dimension suy đoán.
2. Giữ các thuộc tính nguồn khai báo trong design; chạy quy trình SCD2 R06–R07 trên từng namespace/BK.
3. Thuộc tính ID bên trong dimension giữ là thuộc tính denormalized; không dựng snowflake FK dimension-to-dimension.

Không có join nhiều bảng ở grain đầu vào; lookup dimension và kiểm tra master reference vẫn áp dụng theo contract.

**Mapping cột nghiệp vụ:**

| Cột đích | Kiểu và NULL | Biểu thức biến đổi | Diễn giải |
|---|---|---|---|
| `outlet_key` | KEY; NOT NULL | `REGISTRY(entity_id, namespace, BK, valid_from_utc)` | Không hash rút gọn hoặc tái đánh số mỗi batch; 0/-1 theo R05. |
| `source_system` | CODE; NOT NULL | `'hotel_ops'` | Namespace thuộc ID gốc, không đổi thành tên Oracle/Iceberg; dòng đặc biệt dimension dùng system. |
| `member_kind` | CODE; NOT NULL | `'NORMAL'; special rows 'UNKNOWN'/'NOT_APPLICABLE'` | Hai dòng đặc biệt có các thuộc tính nghiệp vụ NULL; không gán BK giả. |
| `outlet_id` | ID; NULL; bắt buộc NORMAL | `s.outlet_id` | Chép giá trị nguồn sau kiểm tra R02; Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Không tính lại bằng danh mục hiện hành. |
| `hotel_id` | ID; NULL; bắt buộc NORMAL | `s.hotel_id` | Chép giá trị nguồn sau kiểm tra R02; Tham chiếu bản ghi hotels trong cùng database. Không tính lại bằng danh mục hiện hành. |
| `outlet_type` | TEXT; NULL; bắt buộc NORMAL | `s.outlet_type` | Chép giá trị nguồn sau kiểm tra R02; RESTAURANT hoặc BAR. Không tính lại bằng danh mục hiện hành. |
| `capacity` | INT; NULL; bắt buộc NORMAL | `s.capacity` | Chép giá trị nguồn sau kiểm tra R02; Sức chứa. Không tính lại bằng danh mục hiện hành. |
| `quality_profile` | INT; NULL; bắt buộc NORMAL | `s.quality_profile` | Chép giá trị nguồn sau kiểm tra R02; Mức nền mô phỏng, không suy từ hạng sao. Không tính lại bằng danh mục hiện hành. |

**Cột dùng chung:** `valid_from_utc`, `valid_to_utc`, `is_current`, `version_no`, `effective_time_basis`, `source_batch_id`, `transform_version`, `row_hash`, `created_at_utc`, `updated_at_utc`. Áp dụng đầy đủ mục audit/SCD ở trên; JSON vẫn chứa một mapping cho từng cột.

**Ràng buộc và nghiệm thu:**

- outlet_type IN (RESTAURANT,BAR); capacity > 0; quality_profile là thang nguồn, không tự suy ra hạng sao.
- version_no>=1; is_current IN (0,1); is_current=1 iff valid_to_utc IS NULL.
- valid_to NULL hoặc valid_from<valid_to; khoảng [valid_from,valid_to) của cùng BK không chồng nhau.
- Dòng NORMAL cùng BK chỉ một current; cùng effective timestamp mà payload khác -> quarantine, không tự lấy dòng cuối.
- Hai dòng đặc biệt 0/-1 không version hóa: version_no=1, current=1, valid_to=NULL.
- Quy tắc áp dụng: R01, R02, R04, R05, R06, R07, R15, R16, R17.

### D10 DimMeal

**Đích:** `dim_meal`. **Grain:** Một thành viên hiện hành cho mỗi business key trong namespace.

**Khóa nghiệp vụ đích:** `meal_code`.

**Nguồn và alias:** Danh mục sinh xác định, không đọc một bảng giao dịch làm grain..

**Điều kiện chọn:** Bốn dòng danh mục cố định và hai thành viên đặc biệt.

**Trình tự biến đổi:**

1. BREAKFAST=1/Bữa sáng; LUNCH=2/Bữa trưa; DINNER=3/Bữa tối; BAR=4/Bar.
2. Giá trị meal không thuộc danh mục là lỗi nguồn, không tự map về BAR hoặc UNKNOWN.

Không có join nhiều bảng ở grain đầu vào; lookup dimension và kiểm tra master reference vẫn áp dụng theo contract.

**Mapping cột nghiệp vụ:**

| Cột đích | Kiểu và NULL | Biểu thức biến đổi | Diễn giải |
|---|---|---|---|
| `meal_key` | KEY; NOT NULL | `MEAL_KEY_CONSTANT` | Không hash rút gọn hoặc tái đánh số mỗi batch; 0/-1 theo R05. |
| `source_system` | CODE; NOT NULL | `'reference'` | Namespace thuộc ID gốc, không đổi thành tên Oracle/Iceberg; dòng đặc biệt dimension dùng system. |
| `member_kind` | CODE; NOT NULL | `'NORMAL'; special rows 'UNKNOWN'/'NOT_APPLICABLE'` | Hai dòng đặc biệt có các thuộc tính nghiệp vụ NULL; không gán BK giả. |
| `meal_code` | CODE; NULL; bắt buộc NORMAL | `REFERENCE_MEALS.meal_code` | Bảng mã BREAKFAST/Bữa sáng, LUNCH/Bữa trưa, DINNER/Bữa tối, BAR/Bar; không lấy tên bữa từ suy đoán. |
| `meal_name` | TEXT; NULL; bắt buộc NORMAL | `REFERENCE_MEALS.meal_name` | Bảng mã BREAKFAST/Bữa sáng, LUNCH/Bữa trưa, DINNER/Bữa tối, BAR/Bar; không lấy tên bữa từ suy đoán. |

**Cột dùng chung:** `source_batch_id`, `transform_version`, `row_hash`, `created_at_utc`, `updated_at_utc`. Áp dụng đầy đủ mục audit/SCD ở trên; JSON vẫn chứa một mapping cho từng cột.

**Ràng buộc và nghiệm thu:**

- meal_code IN (BREAKFAST,LUNCH,DINNER,BAR); khóa danh mục cố định 1,2,3,4 theo đúng thứ tự này.
- Quy tắc áp dụng: R01, R02, R04, R05, R15, R16, R17.

### D11 DimCentre

**Đích:** `dim_centre`. **Grain:** Một phiên bản có hiệu lực của một business key trong namespace nguồn.

**Khóa nghiệp vụ đích:** `source_system, centre_id, valid_from_utc`; `source_system, centre_id, version_no`.

**Nguồn và alias:** `s` = `entertainment_ops.centres`.

**Điều kiện chọn:** Mọi bản ghi danh mục đúng PK và miền giá trị; không lọc chỉ đối tượng có giao dịch.

**Trình tự biến đổi:**

1. Kiểm tra các tham chiếu danh mục trong snapshot nguồn; loại ID sai, không tạo dimension suy đoán.
2. Giữ các thuộc tính nguồn khai báo trong design; chạy quy trình SCD2 R06–R07 trên từng namespace/BK.
3. Thuộc tính ID bên trong dimension giữ là thuộc tính denormalized; không dựng snowflake FK dimension-to-dimension.

Không có join nhiều bảng ở grain đầu vào; lookup dimension và kiểm tra master reference vẫn áp dụng theo contract.

**Mapping cột nghiệp vụ:**

| Cột đích | Kiểu và NULL | Biểu thức biến đổi | Diễn giải |
|---|---|---|---|
| `centre_key` | KEY; NOT NULL | `REGISTRY(entity_id, namespace, BK, valid_from_utc)` | Không hash rút gọn hoặc tái đánh số mỗi batch; 0/-1 theo R05. |
| `source_system` | CODE; NOT NULL | `'entertainment_ops'` | Namespace thuộc ID gốc, không đổi thành tên Oracle/Iceberg; dòng đặc biệt dimension dùng system. |
| `member_kind` | CODE; NOT NULL | `'NORMAL'; special rows 'UNKNOWN'/'NOT_APPLICABLE'` | Hai dòng đặc biệt có các thuộc tính nghiệp vụ NULL; không gán BK giả. |
| `centre_id` | ID; NULL; bắt buộc NORMAL | `s.centre_id` | Chép giá trị nguồn sau kiểm tra R02; Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Không tính lại bằng danh mục hiện hành. |
| `centre_name` | TEXT; NULL; bắt buộc NORMAL | `s.centre_name` | Chép giá trị nguồn sau kiểm tra R02; Tên trung tâm. Không tính lại bằng danh mục hiện hành. |
| `site_code` | ID; NULL; bắt buộc NORMAL | `s.site_code` | Chép giá trị nguồn sau kiểm tra R02; Mã cụm dùng trong thỏa thuận liên đơn vị. Không tính lại bằng danh mục hiện hành. |

**Cột dùng chung:** `valid_from_utc`, `valid_to_utc`, `is_current`, `version_no`, `effective_time_basis`, `source_batch_id`, `transform_version`, `row_hash`, `created_at_utc`, `updated_at_utc`. Áp dụng đầy đủ mục audit/SCD ở trên; JSON vẫn chứa một mapping cho từng cột.

**Ràng buộc và nghiệm thu:**

- site_code ánh xạ đúng một sites.site_id; tên giống nhau không phải bằng chứng ánh xạ.
- version_no>=1; is_current IN (0,1); is_current=1 iff valid_to_utc IS NULL.
- valid_to NULL hoặc valid_from<valid_to; khoảng [valid_from,valid_to) của cùng BK không chồng nhau.
- Dòng NORMAL cùng BK chỉ một current; cùng effective timestamp mà payload khác -> quarantine, không tự lấy dòng cuối.
- Hai dòng đặc biệt 0/-1 không version hóa: version_no=1, current=1, valid_to=NULL.
- Quy tắc áp dụng: R01, R02, R04, R05, R06, R07, R15, R16, R17.

### D12 DimActivity

**Đích:** `dim_activity`. **Grain:** Một phiên bản có hiệu lực của một business key trong namespace nguồn.

**Khóa nghiệp vụ đích:** `source_system, activity_id, valid_from_utc`; `source_system, activity_id, version_no`.

**Nguồn và alias:** `s` = `entertainment_ops.activities`.

**Điều kiện chọn:** Mọi bản ghi danh mục đúng PK và miền giá trị; không lọc chỉ đối tượng có giao dịch.

**Trình tự biến đổi:**

1. Kiểm tra các tham chiếu danh mục trong snapshot nguồn; loại ID sai, không tạo dimension suy đoán.
2. Giữ các thuộc tính nguồn khai báo trong design; chạy quy trình SCD2 R06–R07 trên từng namespace/BK.
3. Thuộc tính ID bên trong dimension giữ là thuộc tính denormalized; không dựng snowflake FK dimension-to-dimension.

Không có join nhiều bảng ở grain đầu vào; lookup dimension và kiểm tra master reference vẫn áp dụng theo contract.

**Mapping cột nghiệp vụ:**

| Cột đích | Kiểu và NULL | Biểu thức biến đổi | Diễn giải |
|---|---|---|---|
| `activity_key` | KEY; NOT NULL | `REGISTRY(entity_id, namespace, BK, valid_from_utc)` | Không hash rút gọn hoặc tái đánh số mỗi batch; 0/-1 theo R05. |
| `source_system` | CODE; NOT NULL | `'entertainment_ops'` | Namespace thuộc ID gốc, không đổi thành tên Oracle/Iceberg; dòng đặc biệt dimension dùng system. |
| `member_kind` | CODE; NOT NULL | `'NORMAL'; special rows 'UNKNOWN'/'NOT_APPLICABLE'` | Hai dòng đặc biệt có các thuộc tính nghiệp vụ NULL; không gán BK giả. |
| `activity_id` | ID; NULL; bắt buộc NORMAL | `s.activity_id` | Chép giá trị nguồn sau kiểm tra R02; Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Không tính lại bằng danh mục hiện hành. |
| `centre_id` | ID; NULL; bắt buộc NORMAL | `s.centre_id` | Chép giá trị nguồn sau kiểm tra R02; Tham chiếu bản ghi centres trong cùng database. Không tính lại bằng danh mục hiện hành. |
| `activity_name` | TEXT; NULL; bắt buộc NORMAL | `s.activity_name` | Chép giá trị nguồn sau kiểm tra R02; Tên hoạt động. Không tính lại bằng danh mục hiện hành. |
| `outdoor` | FLAG; NULL; bắt buộc NORMAL | `s.outdoor` | Chép giá trị nguồn sau kiểm tra R02; 1 nếu phụ thuộc hoạt động ngoài trời. Không tính lại bằng danh mục hiện hành. |
| `capacity_per_day` | INT; NULL; bắt buộc NORMAL | `s.capacity_per_day` | Chép giá trị nguồn sau kiểm tra R02; Sức chứa giả định mỗi ngày. Không tính lại bằng danh mục hiện hành. |

**Cột dùng chung:** `valid_from_utc`, `valid_to_utc`, `is_current`, `version_no`, `effective_time_basis`, `source_batch_id`, `transform_version`, `row_hash`, `created_at_utc`, `updated_at_utc`. Áp dụng đầy đủ mục audit/SCD ở trên; JSON vẫn chứa một mapping cho từng cột.

**Ràng buộc và nghiệm thu:**

- outdoor IN (0,1); capacity_per_day > 0.
- version_no>=1; is_current IN (0,1); is_current=1 iff valid_to_utc IS NULL.
- valid_to NULL hoặc valid_from<valid_to; khoảng [valid_from,valid_to) của cùng BK không chồng nhau.
- Dòng NORMAL cùng BK chỉ một current; cùng effective timestamp mà payload khác -> quarantine, không tự lấy dòng cuối.
- Hai dòng đặc biệt 0/-1 không version hóa: version_no=1, current=1, valid_to=NULL.
- Quy tắc áp dụng: R01, R02, R04, R05, R06, R07, R15, R16, R17.

### D13 DimVehicle

**Đích:** `dim_vehicle`. **Grain:** Một phiên bản có hiệu lực của một business key trong namespace nguồn.

**Khóa nghiệp vụ đích:** `source_system, vehicle_id, valid_from_utc`; `source_system, vehicle_id, version_no`.

**Nguồn và alias:** `s` = `entertainment_ops.vehicles`.

**Điều kiện chọn:** Mọi bản ghi danh mục đúng PK và miền giá trị; không lọc chỉ đối tượng có giao dịch.

**Trình tự biến đổi:**

1. Kiểm tra các tham chiếu danh mục trong snapshot nguồn; loại ID sai, không tạo dimension suy đoán.
2. Giữ các thuộc tính nguồn khai báo trong design; chạy quy trình SCD2 R06–R07 trên từng namespace/BK.
3. Thuộc tính ID bên trong dimension giữ là thuộc tính denormalized; không dựng snowflake FK dimension-to-dimension.

Không có join nhiều bảng ở grain đầu vào; lookup dimension và kiểm tra master reference vẫn áp dụng theo contract.

**Mapping cột nghiệp vụ:**

| Cột đích | Kiểu và NULL | Biểu thức biến đổi | Diễn giải |
|---|---|---|---|
| `vehicle_key` | KEY; NOT NULL | `REGISTRY(entity_id, namespace, BK, valid_from_utc)` | Không hash rút gọn hoặc tái đánh số mỗi batch; 0/-1 theo R05. |
| `source_system` | CODE; NOT NULL | `'entertainment_ops'` | Namespace thuộc ID gốc, không đổi thành tên Oracle/Iceberg; dòng đặc biệt dimension dùng system. |
| `member_kind` | CODE; NOT NULL | `'NORMAL'; special rows 'UNKNOWN'/'NOT_APPLICABLE'` | Hai dòng đặc biệt có các thuộc tính nghiệp vụ NULL; không gán BK giả. |
| `vehicle_id` | ID; NULL; bắt buộc NORMAL | `s.vehicle_id` | Chép giá trị nguồn sau kiểm tra R02; Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Không tính lại bằng danh mục hiện hành. |
| `centre_id` | ID; NULL; bắt buộc NORMAL | `s.centre_id` | Chép giá trị nguồn sau kiểm tra R02; Tham chiếu bản ghi centres trong cùng database. Không tính lại bằng danh mục hiện hành. |
| `vehicle_type` | TEXT; NULL; bắt buộc NORMAL | `s.vehicle_type` | Chép giá trị nguồn sau kiểm tra R02; CAR hoặc MOTORBIKE. Không tính lại bằng danh mục hiện hành. |
| `daily_rate_vnd` | MONEY; NULL; bắt buộc NORMAL | `s.daily_rate_vnd` | Chép giá trị nguồn sau kiểm tra R02; Giá một ngày thuê. Số nguyên VND; không dùng float cho tiền. Không tính lại bằng danh mục hiện hành. |

**Cột dùng chung:** `valid_from_utc`, `valid_to_utc`, `is_current`, `version_no`, `effective_time_basis`, `source_batch_id`, `transform_version`, `row_hash`, `created_at_utc`, `updated_at_utc`. Áp dụng đầy đủ mục audit/SCD ở trên; JSON vẫn chứa một mapping cho từng cột.

**Ràng buộc và nghiệm thu:**

- daily_rate_vnd > 0; centre_id hợp lệ.
- version_no>=1; is_current IN (0,1); is_current=1 iff valid_to_utc IS NULL.
- valid_to NULL hoặc valid_from<valid_to; khoảng [valid_from,valid_to) của cùng BK không chồng nhau.
- Dòng NORMAL cùng BK chỉ một current; cùng effective timestamp mà payload khác -> quarantine, không tự lấy dòng cuối.
- Hai dòng đặc biệt 0/-1 không version hóa: version_no=1, current=1, valid_to=NULL.
- Quy tắc áp dụng: R01, R02, R04, R05, R06, R07, R15, R16, R17.

### D14 DimSupplier

**Đích:** `dim_supplier`. **Grain:** Một phiên bản có hiệu lực của một business key trong namespace nguồn.

**Khóa nghiệp vụ đích:** `source_system, supplier_id, valid_from_utc`; `source_system, supplier_id, version_no`.

**Nguồn và alias:** `s` = `hotel_ops.suppliers`.

**Điều kiện chọn:** Mọi bản ghi danh mục đúng PK và miền giá trị; không lọc chỉ đối tượng có giao dịch.

**Trình tự biến đổi:**

1. Kiểm tra các tham chiếu danh mục trong snapshot nguồn; loại ID sai, không tạo dimension suy đoán.
2. Giữ các thuộc tính nguồn khai báo trong design; chạy quy trình SCD2 R06–R07 trên từng namespace/BK.
3. Thuộc tính ID bên trong dimension giữ là thuộc tính denormalized; không dựng snowflake FK dimension-to-dimension.

Không có join nhiều bảng ở grain đầu vào; lookup dimension và kiểm tra master reference vẫn áp dụng theo contract.

**Mapping cột nghiệp vụ:**

| Cột đích | Kiểu và NULL | Biểu thức biến đổi | Diễn giải |
|---|---|---|---|
| `supplier_key` | KEY; NOT NULL | `REGISTRY(entity_id, namespace, BK, valid_from_utc)` | Không hash rút gọn hoặc tái đánh số mỗi batch; 0/-1 theo R05. |
| `source_system` | CODE; NOT NULL | `'hotel_ops'` | Namespace thuộc ID gốc, không đổi thành tên Oracle/Iceberg; dòng đặc biệt dimension dùng system. |
| `member_kind` | CODE; NOT NULL | `'NORMAL'; special rows 'UNKNOWN'/'NOT_APPLICABLE'` | Hai dòng đặc biệt có các thuộc tính nghiệp vụ NULL; không gán BK giả. |
| `supplier_id` | ID; NULL; bắt buộc NORMAL | `s.supplier_id` | Chép giá trị nguồn sau kiểm tra R02; Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Không tính lại bằng danh mục hiện hành. |
| `supplier_name` | TEXT; NULL; bắt buộc NORMAL | `s.supplier_name` | Chép giá trị nguồn sau kiểm tra R02; Tên thương hiệu thật hoặc thương nhân giả định. Không tính lại bằng danh mục hiện hành. |
| `category` | TEXT; NULL; bắt buộc NORMAL | `s.category` | Chép giá trị nguồn sau kiểm tra R02; FOOD, EQUIPMENT hoặc MAINTENANCE. Không tính lại bằng danh mục hiện hành. |
| `site_id` | ID; NULL | `s.site_id` | Chép giá trị nguồn sau kiểm tra R02; Tham chiếu bản ghi sites trong cùng database. Không tính lại bằng danh mục hiện hành. |
| `delivery_format` | TEXT; NULL; bắt buộc NORMAL | `s.delivery_format` | Chép giá trị nguồn sau kiểm tra R02; CSV, TEXT hoặc MIXED; giả định tích hợp. Không tính lại bằng danh mục hiện hành. |

**Cột dùng chung:** `valid_from_utc`, `valid_to_utc`, `is_current`, `version_no`, `effective_time_basis`, `source_batch_id`, `transform_version`, `row_hash`, `created_at_utc`, `updated_at_utc`. Áp dụng đầy đủ mục audit/SCD ở trên; JSON vẫn chứa một mapping cho từng cột.

**Ràng buộc và nghiệm thu:**

- site_id NULL cho nhà cung cấp phạm vi toàn chuỗi; category không suy ra nhà thầu thực hiện bảo trì.
- version_no>=1; is_current IN (0,1); is_current=1 iff valid_to_utc IS NULL.
- valid_to NULL hoặc valid_from<valid_to; khoảng [valid_from,valid_to) của cùng BK không chồng nhau.
- Dòng NORMAL cùng BK chỉ một current; cùng effective timestamp mà payload khác -> quarantine, không tự lấy dòng cuối.
- Hai dòng đặc biệt 0/-1 không version hóa: version_no=1, current=1, valid_to=NULL.
- Quy tắc áp dụng: R01, R02, R04, R05, R06, R07, R15, R16, R17.

### D15 DimItem

**Đích:** `dim_item`. **Grain:** Một phiên bản có hiệu lực của một business key trong namespace nguồn.

**Khóa nghiệp vụ đích:** `source_system, item_id, valid_from_utc`; `source_system, item_id, version_no`.

**Nguồn và alias:** `s` = `hotel_ops.items`.

**Điều kiện chọn:** Mọi bản ghi danh mục đúng PK và miền giá trị; không lọc chỉ đối tượng có giao dịch.

**Trình tự biến đổi:**

1. Kiểm tra các tham chiếu danh mục trong snapshot nguồn; loại ID sai, không tạo dimension suy đoán.
2. Giữ các thuộc tính nguồn khai báo trong design; chạy quy trình SCD2 R06–R07 trên từng namespace/BK.
3. Thuộc tính ID bên trong dimension giữ là thuộc tính denormalized; không dựng snowflake FK dimension-to-dimension.

Không có join nhiều bảng ở grain đầu vào; lookup dimension và kiểm tra master reference vẫn áp dụng theo contract.

**Mapping cột nghiệp vụ:**

| Cột đích | Kiểu và NULL | Biểu thức biến đổi | Diễn giải |
|---|---|---|---|
| `item_key` | KEY; NOT NULL | `REGISTRY(entity_id, namespace, BK, valid_from_utc)` | Không hash rút gọn hoặc tái đánh số mỗi batch; 0/-1 theo R05. |
| `source_system` | CODE; NOT NULL | `'hotel_ops'` | Namespace thuộc ID gốc, không đổi thành tên Oracle/Iceberg; dòng đặc biệt dimension dùng system. |
| `member_kind` | CODE; NOT NULL | `'NORMAL'; special rows 'UNKNOWN'/'NOT_APPLICABLE'` | Hai dòng đặc biệt có các thuộc tính nghiệp vụ NULL; không gán BK giả. |
| `item_id` | ID; NULL; bắt buộc NORMAL | `s.item_id` | Chép giá trị nguồn sau kiểm tra R02; Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Không tính lại bằng danh mục hiện hành. |
| `item_name` | TEXT; NULL; bắt buộc NORMAL | `s.item_name` | Chép giá trị nguồn sau kiểm tra R02; Tên hàng chuẩn. Không tính lại bằng danh mục hiện hành. |
| `specification` | TEXT; NULL; bắt buộc NORMAL | `s.specification` | Chép giá trị nguồn sau kiểm tra R02; Quy cách phân biệt mặt hàng. Không tính lại bằng danh mục hiện hành. |
| `base_unit` | TEXT; NULL; bắt buộc NORMAL | `s.base_unit` | Chép giá trị nguồn sau kiểm tra R02; kg, litre hoặc piece. Không tính lại bằng danh mục hiện hành. |
| `shelf_life_days` | INT; NULL; bắt buộc NORMAL | `s.shelf_life_days` | Chép giá trị nguồn sau kiểm tra R02; Hạn dùng giả định sau nhận; 0 cho hàng bền. Không tính lại bằng danh mục hiện hành. |

**Cột dùng chung:** `valid_from_utc`, `valid_to_utc`, `is_current`, `version_no`, `effective_time_basis`, `source_batch_id`, `transform_version`, `row_hash`, `created_at_utc`, `updated_at_utc`. Áp dụng đầy đủ mục audit/SCD ở trên; JSON vẫn chứa một mapping cho từng cột.

**Ràng buộc và nghiệm thu:**

- base_unit phải giữ kèm quantity khi tổng hợp; shelf_life_days >= 0.
- version_no>=1; is_current IN (0,1); is_current=1 iff valid_to_utc IS NULL.
- valid_to NULL hoặc valid_from<valid_to; khoảng [valid_from,valid_to) của cùng BK không chồng nhau.
- Dòng NORMAL cùng BK chỉ một current; cùng effective timestamp mà payload khác -> quarantine, không tự lấy dòng cuối.
- Hai dòng đặc biệt 0/-1 không version hóa: version_no=1, current=1, valid_to=NULL.
- Quy tắc áp dụng: R01, R02, R04, R05, R06, R07, R15, R16, R17.

### D16 DimAsset

**Đích:** `dim_asset`. **Grain:** Một phiên bản có hiệu lực của một business key trong namespace nguồn.

**Khóa nghiệp vụ đích:** `source_system, asset_id, valid_from_utc`; `source_system, asset_id, version_no`.

**Nguồn và alias:** `s` = `hotel_ops.assets`.

**Điều kiện chọn:** Mọi bản ghi danh mục đúng PK và miền giá trị; không lọc chỉ đối tượng có giao dịch.

**Trình tự biến đổi:**

1. Kiểm tra các tham chiếu danh mục trong snapshot nguồn; loại ID sai, không tạo dimension suy đoán.
2. Giữ các thuộc tính nguồn khai báo trong design; chạy quy trình SCD2 R06–R07 trên từng namespace/BK.
3. Thuộc tính ID bên trong dimension giữ là thuộc tính denormalized; không dựng snowflake FK dimension-to-dimension.

Không có join nhiều bảng ở grain đầu vào; lookup dimension và kiểm tra master reference vẫn áp dụng theo contract.

**Mapping cột nghiệp vụ:**

| Cột đích | Kiểu và NULL | Biểu thức biến đổi | Diễn giải |
|---|---|---|---|
| `asset_key` | KEY; NOT NULL | `REGISTRY(entity_id, namespace, BK, valid_from_utc)` | Không hash rút gọn hoặc tái đánh số mỗi batch; 0/-1 theo R05. |
| `source_system` | CODE; NOT NULL | `'hotel_ops'` | Namespace thuộc ID gốc, không đổi thành tên Oracle/Iceberg; dòng đặc biệt dimension dùng system. |
| `member_kind` | CODE; NOT NULL | `'NORMAL'; special rows 'UNKNOWN'/'NOT_APPLICABLE'` | Hai dòng đặc biệt có các thuộc tính nghiệp vụ NULL; không gán BK giả. |
| `asset_id` | ID; NULL; bắt buộc NORMAL | `s.asset_id` | Chép giá trị nguồn sau kiểm tra R02; Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Không tính lại bằng danh mục hiện hành. |
| `hotel_id` | ID; NULL; bắt buộc NORMAL | `s.hotel_id` | Chép giá trị nguồn sau kiểm tra R02; Tham chiếu bản ghi hotels trong cùng database. Không tính lại bằng danh mục hiện hành. |
| `room_id` | ID; NULL | `s.room_id` | Chép giá trị nguồn sau kiểm tra R02; Tham chiếu bản ghi rooms trong cùng database. Không tính lại bằng danh mục hiện hành. |
| `asset_type` | TEXT; NULL; bắt buộc NORMAL | `s.asset_type` | Chép giá trị nguồn sau kiểm tra R02; AC, LIFT hoặc COLD_STORAGE. Không tính lại bằng danh mục hiện hành. |
| `supplier_id` | ID; NULL; bắt buộc NORMAL | `s.supplier_id` | Chép giá trị nguồn sau kiểm tra R02; Tham chiếu bản ghi suppliers trong cùng database. Không tính lại bằng danh mục hiện hành. |

**Cột dùng chung:** `valid_from_utc`, `valid_to_utc`, `is_current`, `version_no`, `effective_time_basis`, `source_batch_id`, `transform_version`, `row_hash`, `created_at_utc`, `updated_at_utc`. Áp dụng đầy đủ mục audit/SCD ở trên; JSON vẫn chứa một mapping cho từng cột.

**Ràng buộc và nghiệm thu:**

- room_id có thể NULL; nếu có phải thuộc hotel_id của asset; supplier_id là bên bán tài sản.
- version_no>=1; is_current IN (0,1); is_current=1 iff valid_to_utc IS NULL.
- valid_to NULL hoặc valid_from<valid_to; khoảng [valid_from,valid_to) của cùng BK không chồng nhau.
- Dòng NORMAL cùng BK chỉ một current; cùng effective timestamp mà payload khác -> quarantine, không tự lấy dòng cuối.
- Hai dòng đặc biệt 0/-1 không version hóa: version_no=1, current=1, valid_to=NULL.
- Quy tắc áp dụng: R01, R02, R04, R05, R06, R07, R15, R16, R17.

### F01 FactBooking

**Đích:** `fact_booking`. **Grain:** Một booking ở trạng thái cuối của batch.

**Khóa nghiệp vụ đích:** `source_system, booking_id`.

**Nguồn và alias:** `b` = `hotel_ops.bookings`; `h` = `hotel_ops.hotels`.

**Điều kiện chọn:** Giữ ba trạng thái booking hợp lệ; snapshot bookings là nguồn tiền cuối cùng.

**Trình tự biến đổi:**

1. Grain namespace+booking_id; không join booking_rooms/stays ở bước tạo tiền.
2. Tra dimension theo booked_on. promotion=NULL -> -1; promotion sai -> loại booking, cảnh báo các KPI liên quan.
3. Kiểm tra tiền cân bằng và ngày; trạng thái không thuộc domain là lỗi. Sửa giá không tạo thêm booking.

**Đường nối và cardinality:**

| Điều kiện | Quan hệ và cách nối | Khi không đạt |
|---|---|---|
| `b.hotel_id=h.hotel_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |

**Mốc chọn phiên bản:** booked_date_key tại 00:00 giờ Việt Nam; mọi dimension không phải Date theo thời điểm đặt.

**Mapping cột nghiệp vụ:**

| Cột đích | Kiểu và NULL | Biểu thức biến đổi | Diễn giải |
|---|---|---|---|
| `fact_key` | KEY; NOT NULL | `REGISTRY(F01, source_system, booking_id)` | Khóa grain dùng ID bền vững, không SCD SK; giữ nguyên qua correction/replay. |
| `source_system` | CODE; NOT NULL | `'hotel_ops'` | Namespace thuộc ID gốc, không đổi thành tên Oracle/Iceberg; dòng đặc biệt dimension dùng system. |
| `booked_date_key` | DATEKEY; NOT NULL | `DATEKEY(b.booked_on)` | Namespace calendar; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `arrival_date_key` | DATEKEY; NOT NULL | `DATEKEY(b.arrival)` | Namespace calendar; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `departure_date_key` | DATEKEY; NOT NULL | `DATEKEY(b.departure)` | Namespace calendar; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `site_key` | KEY; NOT NULL | `LOOKUP_SCD(D02, namespace, DIM_ATTR(D03,b.hotel_id,LOCAL_START(b.booked_on),'site_id'), LOCAL_START(b.booked_on))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `hotel_key` | KEY; NOT NULL | `LOOKUP_SCD(D03, namespace, b.hotel_id, LOCAL_START(b.booked_on))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `channel_key` | KEY; NOT NULL | `LOOKUP_SCD(D05, namespace, b.channel_id, LOCAL_START(b.booked_on))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `promotion_key` | KEY; NOT NULL | `LOOKUP_SCD(D06, namespace, b.promotion_id, LOCAL_START(b.booked_on))` | Namespace hotel_ops; NULL: NULL -> -1. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `customer_profile_key` | KEY; NOT NULL | `LOOKUP_SCD(D07, namespace, b.guest_id, LOCAL_START(b.booked_on))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `booking_id` | ID; NOT NULL | `b.booking_id` | Chép giá trị nguồn sau kiểm tra R02; Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Không tính lại bằng danh mục hiện hành. |
| `status` | TEXT; NOT NULL | `b.status` | Chép giá trị nguồn sau kiểm tra R02; COMPLETED, CANCELLED hoặc NO_SHOW. Không tính lại bằng danh mục hiện hành. |
| `source_updated_at_utc` | UTC; NOT NULL | `UTC(b.updated_at)` | Chép giá trị nguồn sau kiểm tra R02; Thời điểm phiên bản cuối trong snapshot. Múi giờ nguồn +07:00. Không tính lại bằng danh mục hiện hành. |
| `gross_vnd` | MONEY; NOT NULL | `b.gross_vnd` | Chép giá trị nguồn sau kiểm tra R02; Giá trị gói phòng trước giảm. Số nguyên VND; không dùng float cho tiền. Không tính lại bằng danh mục hiện hành. |
| `discount_vnd` | MONEY; NOT NULL | `b.discount_vnd` | Chép giá trị nguồn sau kiểm tra R02; Tổng giảm khách được hưởng. Số nguyên VND; không dùng float cho tiền. Không tính lại bằng danh mục hiện hành. |
| `customer_due_vnd` | MONEY; NOT NULL | `b.customer_due_vnd` | Chép giá trị nguồn sau kiểm tra R02; Giá khách trả trước hoàn tiền. Số nguyên VND; không dùng float cho tiền. Không tính lại bằng danh mục hiện hành. |
| `company_share_vnd` | MONEY; NOT NULL | `b.company_share_vnd` | Chép giá trị nguồn sau kiểm tra R02; Phần giảm CompanyE chịu. Số nguyên VND; không dùng float cho tiền. Không tính lại bằng danh mục hiện hành. |
| `partner_share_vnd` | MONEY; NOT NULL | `b.partner_share_vnd` | Chép giá trị nguồn sau kiểm tra R02; Phần giảm đối tác chịu. Số nguyên VND; không dùng float cho tiền. Không tính lại bằng danh mục hiện hành. |
| `commission_vnd` | MONEY; NOT NULL | `b.commission_vnd` | Chép giá trị nguồn sau kiểm tra R02; Phí phân phối trên cơ sở tính giả định đã chốt. Số nguyên VND; không dùng float cho tiền. Không tính lại bằng danh mục hiện hành. |
| `booking_count` | COUNT; NOT NULL | `1` | Luôn bằng 1. Thực hiện sau các kiểm tra và bước tổng hợp của kế hoạch bảng; không coi vắng nguồn hoặc lỗi là 0. |

**Cột dùng chung:** `source_batch_id`, `transform_version`, `row_hash`, `created_at_utc`, `updated_at_utc`. Áp dụng đầy đủ mục audit/SCD ở trên; JSON vẫn chứa một mapping cho từng cột.

**Ràng buộc và nghiệm thu:**

- status IN (COMPLETED,CANCELLED,NO_SHOW).
- arrival < departure; booked_on <= arrival.
- discount_vnd=company_share_vnd+partner_share_vnd; customer_due_vnd=gross_vnd-discount_vnd; các khoản tiền >= 0.
- B02 chỉ COMPLETED; không nhân giá theo phòng, vé hoặc revision. Room type lọc booking qua EXISTS BridgeBookingRoom, không phân bổ tiền ngầm.
- Lookup dimension NORMAL theo namespace + BK và valid_from <= t < valid_to (NULL là vô hạn); đúng một phiên bản. Thiếu/trùng phiên bản -> quarantine dòng phụ thuộc, không lấy current thay thế.
- Quy tắc áp dụng: R01, R02, R03, R04, R05, R07, R08, R09, R15, R16, R17.

### F02 FactRoomDay

**Đích:** `fact_room_day`. **Grain:** Một phòng và một ngày danh mục.

**Khóa nghiệp vụ đích:** `source_system, room_id, date_key`.

**Nguồn và alias:** `r` = `hotel_ops.rooms`; `h` = `hotel_ops.hotels`; `a` = `hotel_ops.assets`; `m` = `hotel_ops.maintenance`.

**Điều kiện chọn:** Mọi phòng x ngày công suất hợp lệ; chỉ m có asset.room_id tạo phạm vi chặn.

**Trình tự biến đổi:**

1. Dựng room/day đầy đủ. Đọc m->a rồi expand maintenance [start,end), gộp room/day trước khi LEFT MATCH về lịch phòng.
2. Không nối từng m trực tiếp vào lịch rồi SUM inventory_day. Chung phòng nhiều asset bảo trì vẫn chỉ blocked_day=1.
3. Thiếu maintenance scope làm unknown capacity; loại ngày không xác định khỏi tập F02 hợp lệ và ghi coverage.

**Đường nối và cardinality:**

| Điều kiện | Quan hệ và cách nối | Khi không đạt |
|---|---|---|
| `r.hotel_id=h.hotel_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |
| `m.asset_id=a.asset_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |

**Mốc chọn phiên bản:** date_key tại 00:00 giờ Việt Nam.

**Mapping cột nghiệp vụ:**

| Cột đích | Kiểu và NULL | Biểu thức biến đổi | Diễn giải |
|---|---|---|---|
| `fact_key` | KEY; NOT NULL | `REGISTRY(F02, source_system, room_id, date_key)` | Khóa grain dùng ID bền vững, không SCD SK; giữ nguyên qua correction/replay. |
| `source_system` | CODE; NOT NULL | `'hotel_ops'` | Namespace thuộc ID gốc, không đổi thành tên Oracle/Iceberg; dòng đặc biệt dimension dùng system. |
| `room_id` | ID; NOT NULL | `r.room_id` | Chép giá trị nguồn sau kiểm tra R02; Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Không tính lại bằng danh mục hiện hành. |
| `date_key` | DATEKEY; NOT NULL | `DATEKEY($day)` | Namespace calendar; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `site_key` | KEY; NOT NULL | `LOOKUP_SCD(D02, namespace, DIM_ATTR(D03,DIM_ATTR(D04,r.room_id,LOCAL_START($day),'hotel_id'),LOCAL_START($day),'site_id'), LOCAL_START($day))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `hotel_key` | KEY; NOT NULL | `LOOKUP_SCD(D03, namespace, DIM_ATTR(D04,r.room_id,LOCAL_START($day),'hotel_id'), LOCAL_START($day))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `room_key` | KEY; NOT NULL | `LOOKUP_SCD(D04, namespace, r.room_id, LOCAL_START($day))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `inventory_day` | FLAG; NOT NULL | `1` | 1 cho mỗi phòng thuộc danh mục trong kỳ công suất. Thực hiện sau các kiểm tra và bước tổng hợp của kế hoạch bảng; không coi vắng nguồn hoặc lỗi là 0. |
| `blocked_day` | FLAG; NOT NULL | `EXISTS(L02 valid row with same namespace/room_id/$day)` | 1 nếu có ít nhất một bảo trì chặn ngày. Thực hiện sau các kiểm tra và bước tổng hợp của kế hoạch bảng; không coi vắng nguồn hoặc lỗi là 0. |
| `available_day` | FLAG; NOT NULL | `1 - blocked_day` | 1-blocked_day. Thực hiện sau các kiểm tra và bước tổng hợp của kế hoạch bảng; không coi vắng nguồn hoặc lỗi là 0. |

**Cột dùng chung:** `source_batch_id`, `transform_version`, `row_hash`, `created_at_utc`, `updated_at_utc`. Áp dụng đầy đủ mục audit/SCD ở trên; JSON vẫn chứa một mapping cho từng cột.

**Ràng buộc và nghiệm thu:**

- inventory_day=1; blocked_day IN (0,1); available_day=inventory_day-blocked_day.
- Gộp union khoảng bảo trì trước khi tạo row; không đếm nhiều lần một room-day.
- Hợp DISTINCT mọi khoảng bảo trì [starts_on,ends_on). Dùng chung B01.02 và B08.03; không chịu bộ lọc kênh/khách hoặc loại công việc chi phí.
- Lookup dimension NORMAL theo namespace + BK và valid_from <= t < valid_to (NULL là vô hạn); đúng một phiên bản. Thiếu/trùng phiên bản -> quarantine dòng phụ thuộc, không lấy current thay thế.
- Quy tắc áp dụng: R01, R02, R03, R04, R05, R07, R10, R15, R16, R17.

### F03 FactStayNight

**Đích:** `fact_stay_night`. **Grain:** Một phòng và một đêm thực ở hợp lệ.

**Khóa nghiệp vụ đích:** `source_system, room_id, service_date_key`.

**Nguồn và alias:** `s` = `hotel_ops.stays`; `br` = `hotel_ops.booking_rooms`; `b` = `hotel_ops.bookings`; `r` = `hotel_ops.rooms`; `h` = `hotel_ops.hotels`; `rp` = `hotel_ops.rate_plans`.

**Điều kiện chọn:** b.status=COMPLETED; expand [s.checkin_date,s.checkout_date), giữ date thật trước khi lọc kỳ report.

**Trình tự biến đổi:**

1. Kiểm tra r.hotel_id=b.hotel_id=rp.hotel_id và rp.channel_id=b.channel_id.
2. Phát hiện overlap room/day trên mọi stays; nhóm trùng hoặc trùng ngày bảo trì -> loại các dòng lỗi, không DISTINCT che overlap.
3. Không dùng ngày arrival/departure dự kiến thay stay thiếu. F02 thiếu coverage ở ngày ở -> không kết luận hợp lệ về availability.

**Đường nối và cardinality:**

| Điều kiện | Quan hệ và cách nối | Khi không đạt |
|---|---|---|
| `s.booking_room_id=br.booking_room_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |
| `br.booking_id=b.booking_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |
| `br.room_id=r.room_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |
| `r.hotel_id=h.hotel_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |
| `br.rate_plan_id=rp.rate_plan_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |

**Mốc chọn phiên bản:** service_date_key tại 00:00 giờ Việt Nam.

**Mapping cột nghiệp vụ:**

| Cột đích | Kiểu và NULL | Biểu thức biến đổi | Diễn giải |
|---|---|---|---|
| `fact_key` | KEY; NOT NULL | `REGISTRY(F03, source_system, room_id, service_date_key)` | Khóa grain dùng ID bền vững, không SCD SK; giữ nguyên qua correction/replay. |
| `source_system` | CODE; NOT NULL | `'hotel_ops'` | Namespace thuộc ID gốc, không đổi thành tên Oracle/Iceberg; dòng đặc biệt dimension dùng system. |
| `room_id` | ID; NOT NULL | `r.room_id` | Chép giá trị nguồn sau kiểm tra R02; Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Không tính lại bằng danh mục hiện hành. |
| `service_date_key` | DATEKEY; NOT NULL | `DATEKEY($day)` | Namespace calendar; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `site_key` | KEY; NOT NULL | `LOOKUP_SCD(D02, namespace, DIM_ATTR(D03,DIM_ATTR(D04,r.room_id,LOCAL_START($day),'hotel_id'),LOCAL_START($day),'site_id'), LOCAL_START($day))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `hotel_key` | KEY; NOT NULL | `LOOKUP_SCD(D03, namespace, DIM_ATTR(D04,r.room_id,LOCAL_START($day),'hotel_id'), LOCAL_START($day))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `room_key` | KEY; NOT NULL | `LOOKUP_SCD(D04, namespace, r.room_id, LOCAL_START($day))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `channel_key` | KEY; NOT NULL | `LOOKUP_SCD(D05, namespace, b.channel_id, LOCAL_START($day))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `customer_profile_key` | KEY; NOT NULL | `LOOKUP_SCD(D07, namespace, b.guest_id, LOCAL_START($day))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `rate_plan_key` | KEY; NOT NULL | `LOOKUP_SCD(D08, namespace, br.rate_plan_id, LOCAL_START($day))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `stay_id` | ID; NOT NULL | `s.stay_id` | Chép giá trị nguồn sau kiểm tra R02; Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Không tính lại bằng danh mục hiện hành. |
| `booking_room_id` | ID; NOT NULL | `br.booking_room_id` | Chép giá trị nguồn sau kiểm tra R02; Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Không tính lại bằng danh mục hiện hành. |
| `booking_id` | ID; NOT NULL | `br.booking_id` | Chép giá trị nguồn sau kiểm tra R02; Tham chiếu bản ghi bookings trong cùng database. Không tính lại bằng danh mục hiện hành. |
| `occupied_night` | FLAG; NOT NULL | `1` | 1 cho mỗi đêm thực ở của booking COMPLETED. Thực hiện sau các kiểm tra và bước tổng hợp của kế hoạch bảng; không coi vắng nguồn hoặc lỗi là 0. |

**Cột dùng chung:** `source_batch_id`, `transform_version`, `row_hash`, `created_at_utc`, `updated_at_utc`. Áp dụng đầy đủ mục audit/SCD ở trên; JSON vẫn chứa một mapping cho từng cột.

**Ràng buộc và nghiệm thu:**

- Không trùng namespace/room_id/service_date_key, kể cả khác stay_id; overlap phải báo lỗi trước DISTINCT.
- Đêm ở thuộc [checkin,checkout); không trùng ngày phòng bị chặn; phòng/rate plan/booking cùng hotel.
- Chỉ booking COMPLETED; overlap và ở trùng ngày ngừng bán là lỗi. Kênh có thể lọc đêm bán nhưng không tạo công suất theo kênh.
- Lookup dimension NORMAL theo namespace + BK và valid_from <= t < valid_to (NULL là vô hạn); đúng một phiên bản. Thiếu/trùng phiên bản -> quarantine dòng phụ thuộc, không lấy current thay thế.
- Quy tắc áp dụng: R01, R02, R03, R04, R05, R07, R08, R10, R15, R16, R17.

### F04 FactTicketOrder

**Đích:** `fact_ticket_order`. **Grain:** Một đơn vé.

**Khóa nghiệp vụ đích:** `source_system, ticket_order_id`.

**Nguồn và alias:** `o` = `entertainment_ops.ticket_orders`; `c` = `entertainment_ops.centres`; `b` = `hotel_ops.bookings`; `h` = `hotel_ops.hotels`.

**Điều kiện chọn:** Mọi ticket_order hợp lệ, có hoặc không có booking_ref; đơn hoàn toàn bộ vẫn được lưu.

**Trình tự biến đổi:**

1. Gross/refund/net ở cấp order. Không join tickets để tính tiền.
2. Không ref: các khóa booking/cohort=-1, DD hotel_booking_ref=NULL. Có ref hợp lệ: kế thừa F01 hotel/site/channel phiên bản và departure date.
3. Có ref nhưng booking bị loại ở F01 -> dependency_excluded; không biến dịch vụ thành bán độc lập.

**Đường nối và cardinality:**

| Điều kiện | Quan hệ và cách nối | Khi không đạt |
|---|---|---|
| `o.centre_id=c.centre_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |
| `o.hotel_booking_ref=b.booking_id` | N:1; LEFT_OPTIONAL_VALIDATED | NULL optional dùng special member; ref có giá trị sai -> dependency_excluded. |
| `b.hotel_id=h.hotel_id` | N:1; LEFT_OPTIONAL_VALIDATED | NULL optional dùng special member; ref có giá trị sai -> dependency_excluded. |

**Mốc chọn phiên bản:** ordered_date_key cho service_site/centre/customer/ticket_channel; booking_site/referral_hotel/booking_channel kế thừa phiên bản booking tương ứng F01.

**Mapping cột nghiệp vụ:**

| Cột đích | Kiểu và NULL | Biểu thức biến đổi | Diễn giải |
|---|---|---|---|
| `fact_key` | KEY; NOT NULL | `REGISTRY(F04, source_system, ticket_order_id)` | Khóa grain dùng ID bền vững, không SCD SK; giữ nguyên qua correction/replay. |
| `source_system` | CODE; NOT NULL | `'entertainment_ops'` | Namespace thuộc ID gốc, không đổi thành tên Oracle/Iceberg; dòng đặc biệt dimension dùng system. |
| `ordered_date_key` | DATEKEY; NOT NULL | `DATEKEY(o.ordered_on)` | Namespace calendar; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `cohort_departure_date_key` | DATEKEY; NOT NULL | `DATEKEY(b.departure)` | Namespace calendar; NULL: NO_BOOKING_REF -> -1. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `service_site_key` | KEY; NOT NULL | `LOOKUP_SCD(D02, namespace, DIM_ATTR(D11,o.centre_id,LOCAL_START(o.ordered_on),'site_code'), LOCAL_START(o.ordered_on))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `booking_site_key` | KEY; NOT NULL | `INHERIT_VALIDATED(F01.site_key where booking_id=source.hotel_booking_ref)` | Namespace hotel_ops; NULL: NO_BOOKING_REF -> -1. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `referral_hotel_key` | KEY; NOT NULL | `INHERIT_VALIDATED(F01.hotel_key where booking_id=source.hotel_booking_ref)` | Namespace hotel_ops; NULL: NO_BOOKING_REF -> -1. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `ticket_channel_key` | KEY; NOT NULL | `LOOKUP_SCD(D05, namespace, o.sales_channel, LOCAL_START(o.ordered_on))` | Namespace entertainment_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `booking_channel_key` | KEY; NOT NULL | `INHERIT_VALIDATED(F01.channel_key where booking_id=source.hotel_booking_ref)` | Namespace hotel_ops; NULL: NO_BOOKING_REF -> -1. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `customer_profile_key` | KEY; NOT NULL | `LOOKUP_SCD(D07, namespace, o.customer_id, LOCAL_START(o.ordered_on))` | Namespace entertainment_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `centre_key` | KEY; NOT NULL | `LOOKUP_SCD(D11, namespace, o.centre_id, LOCAL_START(o.ordered_on))` | Namespace entertainment_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `ticket_order_id` | ID; NOT NULL | `o.ticket_order_id` | Chép giá trị nguồn sau kiểm tra R02; Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Không tính lại bằng danh mục hiện hành. |
| `hotel_booking_ref` | ID; NULL | `o.hotel_booking_ref` | Chép giá trị nguồn sau kiểm tra R02; Booking khách sạn khi bán liên kết; không có FK xuyên database. Không tính lại bằng danh mục hiện hành. |
| `gross_vnd` | MONEY; NOT NULL | `o.gross_vnd` | Chép giá trị nguồn sau kiểm tra R02; Giá vé trước hoàn. Số nguyên VND; không dùng float cho tiền. Không tính lại bằng danh mục hiện hành. |
| `refunded_vnd` | MONEY; NOT NULL | `o.refunded_vnd` | Chép giá trị nguồn sau kiểm tra R02; Phần đã hoàn. Số nguyên VND; không dùng float cho tiền. Không tính lại bằng danh mục hiện hành. |
| `net_ticket_vnd` | MONEY; NOT NULL | `o.gross_vnd - o.refunded_vnd` | gross_vnd-refunded_vnd. Thực hiện sau các kiểm tra và bước tổng hợp của kế hoạch bảng; không coi vắng nguồn hoặc lỗi là 0. |

**Cột dùng chung:** `source_batch_id`, `transform_version`, `row_hash`, `created_at_utc`, `updated_at_utc`. Áp dụng đầy đủ mục audit/SCD ở trên; JSON vẫn chứa một mapping cho từng cột.

**Ràng buộc và nghiệm thu:**

- gross_vnd>=refunded_vnd>=0; net_ticket_vnd=gross_vnd-refunded_vnd.
- Tham chiếu booking có giá trị phải tồn tại; các khóa referral đồng loạt -1 khi không có booking_ref.
- B03 tổng riêng về booking. Không phân bổ giá đơn theo hoạt động nếu không có quy tắc. Đơn không ref là bán độc lập; vé UNUSED chưa hoàn vẫn là mua.
- Lookup dimension NORMAL theo namespace + BK và valid_from <= t < valid_to (NULL là vô hạn); đúng một phiên bản. Thiếu/trùng phiên bản -> quarantine dòng phụ thuộc, không lấy current thay thế.
- Quy tắc áp dụng: R01, R02, R03, R04, R05, R07, R08, R09, R15, R16, R17.

### F05 FactRental

**Đích:** `fact_rental`. **Grain:** Một hợp đồng thuê một xe.

**Khóa nghiệp vụ đích:** `source_system, rental_id`.

**Nguồn và alias:** `r` = `entertainment_ops.rentals`; `v` = `entertainment_ops.vehicles`; `c` = `entertainment_ops.centres`; `b` = `hotel_ops.bookings`; `h` = `hotel_ops.hotels`.

**Điều kiện chọn:** Mọi rental đúng contract, gồm COMPLETED/CANCELLED; số tiền không nhân ngày.

**Trình tự biến đổi:**

1. Pickup/return là date roles. Dimension dịch vụ tra tại pickup; dimension booking kế thừa F01.
2. Lỗi duration/overlap/bảo trì: kiểm tra theo R10 trước publish; rental tham gia conflict không được ghi là thuê hoàn tất hợp lệ.
3. Booking_ref NULL là bán độc lập; ref có giá trị sai phải được loại và báo thiếu.

**Đường nối và cardinality:**

| Điều kiện | Quan hệ và cách nối | Khi không đạt |
|---|---|---|
| `r.vehicle_id=v.vehicle_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |
| `v.centre_id=c.centre_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |
| `r.hotel_booking_ref=b.booking_id` | N:1; LEFT_OPTIONAL_VALIDATED | NULL optional dùng special member; ref có giá trị sai -> dependency_excluded. |
| `b.hotel_id=h.hotel_id` | N:1; LEFT_OPTIONAL_VALIDATED | NULL optional dùng special member; ref có giá trị sai -> dependency_excluded. |

**Mốc chọn phiên bản:** pickup_date_key cho service_site/centre/customer/vehicle; booking_site/referral_hotel/booking_channel kế thừa phiên bản booking tương ứng F01.

**Mapping cột nghiệp vụ:**

| Cột đích | Kiểu và NULL | Biểu thức biến đổi | Diễn giải |
|---|---|---|---|
| `fact_key` | KEY; NOT NULL | `REGISTRY(F05, source_system, rental_id)` | Khóa grain dùng ID bền vững, không SCD SK; giữ nguyên qua correction/replay. |
| `source_system` | CODE; NOT NULL | `'entertainment_ops'` | Namespace thuộc ID gốc, không đổi thành tên Oracle/Iceberg; dòng đặc biệt dimension dùng system. |
| `pickup_date_key` | DATEKEY; NOT NULL | `DATEKEY(r.pickup_date)` | Namespace calendar; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `return_date_key` | DATEKEY; NOT NULL | `DATEKEY(r.return_date)` | Namespace calendar; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `cohort_departure_date_key` | DATEKEY; NOT NULL | `DATEKEY(b.departure)` | Namespace calendar; NULL: NO_BOOKING_REF -> -1. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `service_site_key` | KEY; NOT NULL | `LOOKUP_SCD(D02, namespace, DIM_ATTR(D11,DIM_ATTR(D13,r.vehicle_id,LOCAL_START(r.pickup_date),'centre_id'),LOCAL_START(r.pickup_date),'site_code'), LOCAL_START(r.pickup_date))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `booking_site_key` | KEY; NOT NULL | `INHERIT_VALIDATED(F01.site_key where booking_id=source.hotel_booking_ref)` | Namespace hotel_ops; NULL: NO_BOOKING_REF -> -1. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `referral_hotel_key` | KEY; NOT NULL | `INHERIT_VALIDATED(F01.hotel_key where booking_id=source.hotel_booking_ref)` | Namespace hotel_ops; NULL: NO_BOOKING_REF -> -1. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `booking_channel_key` | KEY; NOT NULL | `INHERIT_VALIDATED(F01.channel_key where booking_id=source.hotel_booking_ref)` | Namespace hotel_ops; NULL: NO_BOOKING_REF -> -1. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `customer_profile_key` | KEY; NOT NULL | `LOOKUP_SCD(D07, namespace, r.customer_id, LOCAL_START(r.pickup_date))` | Namespace entertainment_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `centre_key` | KEY; NOT NULL | `LOOKUP_SCD(D11, namespace, DIM_ATTR(D13,r.vehicle_id,LOCAL_START(r.pickup_date),'centre_id'), LOCAL_START(r.pickup_date))` | Namespace entertainment_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `vehicle_key` | KEY; NOT NULL | `LOOKUP_SCD(D13, namespace, r.vehicle_id, LOCAL_START(r.pickup_date))` | Namespace entertainment_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `rental_id` | ID; NOT NULL | `r.rental_id` | Chép giá trị nguồn sau kiểm tra R02; Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Không tính lại bằng danh mục hiện hành. |
| `hotel_booking_ref` | ID; NULL | `r.hotel_booking_ref` | Chép giá trị nguồn sau kiểm tra R02; Tham chiếu bán qua khách sạn. Không tính lại bằng danh mục hiện hành. |
| `status` | TEXT; NOT NULL | `r.status` | Chép giá trị nguồn sau kiểm tra R02; COMPLETED hoặc CANCELLED. Không tính lại bằng danh mục hiện hành. |
| `agreed_vnd` | MONEY; NOT NULL | `r.agreed_vnd` | Chép giá trị nguồn sau kiểm tra R02; Giá trị thỏa thuận. Số nguyên VND; không dùng float cho tiền. Không tính lại bằng danh mục hiện hành. |

**Cột dùng chung:** `source_batch_id`, `transform_version`, `row_hash`, `created_at_utc`, `updated_at_utc`. Áp dụng đầy đủ mục audit/SCD ở trên; JSON vẫn chứa một mapping cho từng cột.

**Ràng buộc và nghiệm thu:**

- status IN (COMPLETED,CANCELLED); pickup < return; agreed_vnd>=0.
- B03 chỉ dùng COMPLETED; không nhân agreed_vnd theo ngày xe.
- B03 chỉ COMPLETED; số tiền ghi một lần, không chép lên mỗi ngày xe. B05 lấy ngày từ F11, không cộng số hợp đồng thành ngày xe.
- Lookup dimension NORMAL theo namespace + BK và valid_from <= t < valid_to (NULL là vô hạn); đúng một phiên bản. Thiếu/trùng phiên bản -> quarantine dòng phụ thuộc, không lấy current thay thế.
- Quy tắc áp dụng: R01, R02, R03, R04, R05, R07, R08, R09, R10, R15, R16, R17.

### F06 FactBreakfastEntitlement

**Đích:** `fact_breakfast_entitlement`. **Grain:** Một quyền lợi phòng và ngày phục vụ.

**Khóa nghiệp vụ đích:** `source_system, entitlement_id`; `source_system, booking_room_id, service_date_key`.

**Nguồn và alias:** `e` = `hotel_ops.breakfast_entitlements`; `br` = `hotel_ops.booking_rooms`; `b` = `hotel_ops.bookings`; `r` = `hotel_ops.rooms`; `h` = `hotel_ops.hotels`; `rp` = `hotel_ops.rate_plans`; `o` = `hotel_ops.outlets`; `s` = `hotel_ops.stays`.

**Điều kiện chọn:** Booking COMPLETED, breakfast_included=1, đúng một entitlement/booking_room/service_date.

**Trình tự biến đổi:**

1. Giữ eligible/redeemed nguồn; kiểm tra rate plan/hotel/room và một stay hợp lệ với checkin<service_date<=checkout, không nhân entitlement qua join nhiều stay. Nếu kiểm tra F03 thì lookup đêm service_date-1; không loại suất sáng checkout chỉ vì không có đêm ở vào chính ngày checkout.
2. Meal cố định BREAKFAST. Outlet mapping duy nhất theo khách sạn phục vụ; v2 một RESTAURANT/hotel.
3. Không dùng giá buffet để tạo doanh thu cho quyền lợi; không suy thêm suất trẻ em.

**Đường nối và cardinality:**

| Điều kiện | Quan hệ và cách nối | Khi không đạt |
|---|---|---|
| `e.booking_room_id=br.booking_room_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |
| `br.booking_id=b.booking_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |
| `br.room_id=r.room_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |
| `b.hotel_id=h.hotel_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |
| `br.rate_plan_id=rp.rate_plan_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |
| `h.hotel_id=o.hotel_id AND o.outlet_type='RESTAURANT'` | 1:exactly1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |
| `e.booking_room_id=s.booking_room_id AND s.checkin_date<e.service_date<=s.checkout_date` | SEMI_EXISTS_EXACTLY1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |

**Mốc chọn phiên bản:** service_date_key tại 00:00 giờ Việt Nam.

**Mapping cột nghiệp vụ:**

| Cột đích | Kiểu và NULL | Biểu thức biến đổi | Diễn giải |
|---|---|---|---|
| `fact_key` | KEY; NOT NULL | `REGISTRY(F06, source_system, entitlement_id)` | Khóa grain dùng ID bền vững, không SCD SK; giữ nguyên qua correction/replay. |
| `source_system` | CODE; NOT NULL | `'hotel_ops'` | Namespace thuộc ID gốc, không đổi thành tên Oracle/Iceberg; dòng đặc biệt dimension dùng system. |
| `service_date_key` | DATEKEY; NOT NULL | `DATEKEY(e.service_date)` | Namespace calendar; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `site_key` | KEY; NOT NULL | `LOOKUP_SCD(D02, namespace, DIM_ATTR(D03,b.hotel_id,LOCAL_START(e.service_date),'site_id'), LOCAL_START(e.service_date))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `hotel_key` | KEY; NOT NULL | `LOOKUP_SCD(D03, namespace, b.hotel_id, LOCAL_START(e.service_date))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `room_key` | KEY; NOT NULL | `LOOKUP_SCD(D04, namespace, br.room_id, LOCAL_START(e.service_date))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `customer_profile_key` | KEY; NOT NULL | `LOOKUP_SCD(D07, namespace, b.guest_id, LOCAL_START(e.service_date))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `rate_plan_key` | KEY; NOT NULL | `LOOKUP_SCD(D08, namespace, br.rate_plan_id, LOCAL_START(e.service_date))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `outlet_key` | KEY; NOT NULL | `LOOKUP_SCD(D09, namespace, o.outlet_id, LOCAL_START(e.service_date))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `meal_key` | KEY; NOT NULL | `LOOKUP_MEAL('BREAKFAST')` | Namespace reference; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `entitlement_id` | ID; NOT NULL | `e.entitlement_id` | Chép giá trị nguồn sau kiểm tra R02; Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Không tính lại bằng danh mục hiện hành. |
| `booking_room_id` | ID; NOT NULL | `e.booking_room_id` | Chép giá trị nguồn sau kiểm tra R02; Tham chiếu bản ghi booking_rooms trong cùng database. Không tính lại bằng danh mục hiện hành. |
| `eligible_covers` | COUNT; NOT NULL | `e.eligible_covers` | Chép giá trị nguồn sau kiểm tra R02; Suất được hưởng. Không tính lại bằng danh mục hiện hành. |
| `redeemed_covers` | COUNT; NOT NULL | `e.redeemed_covers` | Chép giá trị nguồn sau kiểm tra R02; Suất thực dùng. Không tính lại bằng danh mục hiện hành. |

**Cột dùng chung:** `source_batch_id`, `transform_version`, `row_hash`, `created_at_utc`, `updated_at_utc`. Áp dụng đầy đủ mục audit/SCD ở trên; JSON vẫn chứa một mapping cho từng cột.

**Ràng buộc và nghiệm thu:**

- eligible_covers>=redeemed_covers>=0; booking COMPLETED; meal=BREAKFAST.
- Một booking_room/service_date duy nhất; đúng một RESTAURANT trong hotel; entitlement thuộc ngày phục vụ hợp lệ của lưu trú.
- Chỉ COMPLETED. Ánh xạ đúng một RESTAURANT mỗi khách sạn ở v2; nhiều hơn một phải báo lỗi thay vì chọn ngẫu nhiên.
- Lookup dimension NORMAL theo namespace + BK và valid_from <= t < valid_to (NULL là vô hạn); đúng một phiên bản. Thiếu/trùng phiên bản -> quarantine dòng phụ thuộc, không lấy current thay thế.
- Quy tắc áp dụng: R01, R02, R03, R04, R05, R07, R08, R11, R15, R16, R17.

### F07 FactDiningOrder

**Đích:** `fact_dining_order`. **Grain:** Một hóa đơn ăn uống, không phải dòng món.

**Khóa nghiệp vụ đích:** `source_system, dining_order_id`.

**Nguồn và alias:** `d` = `hotel_ops.dining_orders`; `o` = `hotel_ops.outlets`; `h` = `hotel_ops.hotels`; `b` = `hotel_ops.bookings`.

**Điều kiện chọn:** Mọi hóa đơn ăn uống đúng số tiền, covers, meal và rating.

**Trình tự biến đổi:**

1. Service_hotel/site theo outlet; booking_hotel theo ref booking nếu có; khách ăn ở hotel khác booking là hợp lệ.
2. d.guest_id NULL -> customer_profile=0; d.booking_id NULL -> booking_hotel=-1; không đồng nhất hai loại thiếu này.
3. F07 không join chi phí meal_sessions. Rating_sum=rating, rating_count=1 trên dòng hợp lệ.

**Đường nối và cardinality:**

| Điều kiện | Quan hệ và cách nối | Khi không đạt |
|---|---|---|
| `d.outlet_id=o.outlet_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |
| `o.hotel_id=h.hotel_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |
| `d.booking_id=b.booking_id` | N:1; LEFT_OPTIONAL_VALIDATED | NULL optional dùng special member; ref có giá trị sai -> dependency_excluded. |

**Mốc chọn phiên bản:** service_date_key cho service_site/service_hotel/customer/outlet; booking_hotel kế thừa phiên bản booking tương ứng F01.

**Mapping cột nghiệp vụ:**

| Cột đích | Kiểu và NULL | Biểu thức biến đổi | Diễn giải |
|---|---|---|---|
| `fact_key` | KEY; NOT NULL | `REGISTRY(F07, source_system, dining_order_id)` | Khóa grain dùng ID bền vững, không SCD SK; giữ nguyên qua correction/replay. |
| `source_system` | CODE; NOT NULL | `'hotel_ops'` | Namespace thuộc ID gốc, không đổi thành tên Oracle/Iceberg; dòng đặc biệt dimension dùng system. |
| `service_date_key` | DATEKEY; NOT NULL | `DATEKEY(d.service_date)` | Namespace calendar; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `site_key` | KEY; NOT NULL | `LOOKUP_SCD(D02, namespace, DIM_ATTR(D03,DIM_ATTR(D09,d.outlet_id,LOCAL_START(d.service_date),'hotel_id'),LOCAL_START(d.service_date),'site_id'), LOCAL_START(d.service_date))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `service_hotel_key` | KEY; NOT NULL | `LOOKUP_SCD(D03, namespace, DIM_ATTR(D09,d.outlet_id,LOCAL_START(d.service_date),'hotel_id'), LOCAL_START(d.service_date))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `booking_hotel_key` | KEY; NOT NULL | `INHERIT_VALIDATED(F01.hotel_key where booking_id=d.booking_id)` | Namespace hotel_ops; NULL: NULL_BOOKING -> -1. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `customer_profile_key` | KEY; NOT NULL | `LOOKUP_SCD(D07, namespace, d.guest_id, LOCAL_START(d.service_date))` | Namespace hotel_ops; NULL: NULL -> 0. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `outlet_key` | KEY; NOT NULL | `LOOKUP_SCD(D09, namespace, d.outlet_id, LOCAL_START(d.service_date))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `meal_key` | KEY; NOT NULL | `LOOKUP_MEAL(d.meal)` | Namespace reference; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `dining_order_id` | ID; NOT NULL | `d.dining_order_id` | Chép giá trị nguồn sau kiểm tra R02; Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Không tính lại bằng danh mục hiện hành. |
| `booking_id` | ID; NULL | `d.booking_id` | Chép giá trị nguồn sau kiểm tra R02; Tham chiếu bản ghi bookings trong cùng database. Không tính lại bằng danh mục hiện hành. |
| `net_vnd` | MONEY; NOT NULL | `d.net_vnd` | Chép giá trị nguồn sau kiểm tra R02; Giá trị sau ưu đãi. Số nguyên VND; không dùng float cho tiền. Không tính lại bằng danh mục hiện hành. |
| `covers` | COUNT; NOT NULL | `d.covers` | Chép giá trị nguồn sau kiểm tra R02; Số khách phục vụ. Không tính lại bằng danh mục hiện hành. |
| `rating_sum` | COUNT; NOT NULL | `d.rating` | rating nguồn trong 1..5; nguồn v2 bắt buộc có rating. Thực hiện sau các kiểm tra và bước tổng hợp của kế hoạch bảng; không coi vắng nguồn hoặc lỗi là 0. |
| `rating_count` | COUNT; NOT NULL | `1` | 1 cho hóa đơn có rating hợp lệ; v2 luôn 1. Thực hiện sau các kiểm tra và bước tổng hợp của kế hoạch bảng; không coi vắng nguồn hoặc lỗi là 0. |

**Cột dùng chung:** `source_batch_id`, `transform_version`, `row_hash`, `created_at_utc`, `updated_at_utc`. Áp dụng đầy đủ mục audit/SCD ở trên; JSON vẫn chứa một mapping cho từng cột.

**Ràng buộc và nghiệm thu:**

- net_vnd>=0; covers>=0; rating_sum BETWEEN 1 AND 5; rating_count=1.
- Không suy guest từ booking khi guest_id nguồn NULL; service_hotel lấy từ outlet, booking_hotel từ booking.
- Cơ sở phục vụ theo outlet, không theo booking. Rating có trọng số mỗi hóa đơn, không theo covers. Không có dimension món ăn từ schema hiện tại.
- Lookup dimension NORMAL theo namespace + BK và valid_from <= t < valid_to (NULL là vô hạn); đúng một phiên bản. Thiếu/trùng phiên bản -> quarantine dòng phụ thuộc, không lấy current thay thế.
- Quy tắc áp dụng: R01, R02, R03, R04, R05, R07, R11, R15, R16, R17.

### F08 FactMealSession

**Đích:** `fact_meal_session`. **Grain:** Một outlet, ngày và bữa buffet.

**Khóa nghiệp vụ đích:** `source_system, outlet_id, service_date_key, meal_key`; `source_system, session_id`.

**Nguồn và alias:** `s` = `hotel_ops.meal_sessions`; `o` = `hotel_ops.outlets`; `h` = `hotel_ops.hotels`.

**Điều kiện chọn:** Meal BREAKFAST hoặc DINNER; outlet RESTAURANT; một outlet/date/meal.

**Trình tự biến đổi:**

1. Giữ actual_covers và ingredient_cost_vnd nguồn. Một grain nhiều session_id là lỗi, không SUM gộp để che.
2. Đối soát actual_covers với entitlement redeemed + dining covers theo outlet/date/meal sau aggregate.
3. Không tạo phiên LUNCH/BAR và không chia chi phí phiên cho từng khách khi chưa có quy tắc.

**Đường nối và cardinality:**

| Điều kiện | Quan hệ và cách nối | Khi không đạt |
|---|---|---|
| `s.outlet_id=o.outlet_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |
| `o.hotel_id=h.hotel_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |

**Mốc chọn phiên bản:** service_date_key tại 00:00 giờ Việt Nam.

**Mapping cột nghiệp vụ:**

| Cột đích | Kiểu và NULL | Biểu thức biến đổi | Diễn giải |
|---|---|---|---|
| `fact_key` | KEY; NOT NULL | `REGISTRY(F08, source_system, outlet_id, service_date_key, meal_key)` | Khóa grain dùng ID bền vững, không SCD SK; giữ nguyên qua correction/replay. |
| `source_system` | CODE; NOT NULL | `'hotel_ops'` | Namespace thuộc ID gốc, không đổi thành tên Oracle/Iceberg; dòng đặc biệt dimension dùng system. |
| `outlet_id` | ID; NOT NULL | `o.outlet_id` | Chép giá trị nguồn sau kiểm tra R02; Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Không tính lại bằng danh mục hiện hành. |
| `service_date_key` | DATEKEY; NOT NULL | `DATEKEY(s.service_date)` | Namespace calendar; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `site_key` | KEY; NOT NULL | `LOOKUP_SCD(D02, namespace, DIM_ATTR(D03,DIM_ATTR(D09,s.outlet_id,LOCAL_START(s.service_date),'hotel_id'),LOCAL_START(s.service_date),'site_id'), LOCAL_START(s.service_date))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `hotel_key` | KEY; NOT NULL | `LOOKUP_SCD(D03, namespace, DIM_ATTR(D09,s.outlet_id,LOCAL_START(s.service_date),'hotel_id'), LOCAL_START(s.service_date))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `outlet_key` | KEY; NOT NULL | `LOOKUP_SCD(D09, namespace, s.outlet_id, LOCAL_START(s.service_date))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `meal_key` | KEY; NOT NULL | `LOOKUP_MEAL(s.meal)` | Namespace reference; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `session_id` | ID; NOT NULL | `s.session_id` | Chép giá trị nguồn sau kiểm tra R02; Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Không tính lại bằng danh mục hiện hành. |
| `actual_covers` | COUNT; NOT NULL | `s.actual_covers` | Chép giá trị nguồn sau kiểm tra R02; Tổng suất thực dùng. Không tính lại bằng danh mục hiện hành. |
| `ingredient_cost_vnd` | MONEY; NOT NULL | `s.ingredient_cost_vnd` | Chép giá trị nguồn sau kiểm tra R02; Chi phí nguyên liệu phân bổ theo bữa; không phải chi phí tiêu thụ từng khách. Số nguyên VND; không dùng float cho tiền. Không tính lại bằng danh mục hiện hành. |

**Cột dùng chung:** `source_batch_id`, `transform_version`, `row_hash`, `created_at_utc`, `updated_at_utc`. Áp dụng đầy đủ mục audit/SCD ở trên; JSON vẫn chứa một mapping cho từng cột.

**Ràng buộc và nghiệm thu:**

- meal IN (BREAKFAST,DINNER); actual_covers>=0; ingredient_cost_vnd>=0.
- Một outlet/ngày/bữa; không tự gộp hai session_id trùng grain.
- BREAKFAST/DINNER; không cộng actual_covers lần nữa vào B04.05. Không nối chi phí phiên với từng hóa đơn rồi SUM.
- Lookup dimension NORMAL theo namespace + BK và valid_from <= t < valid_to (NULL là vô hạn); đúng một phiên bản. Thiếu/trùng phiên bản -> quarantine dòng phụ thuộc, không lấy current thay thế.
- Quy tắc áp dụng: R01, R02, R03, R04, R05, R07, R11, R15, R16, R17.

### F09 FactAdmission

**Đích:** `fact_admission`. **Grain:** Một lượt admission thực tế.

**Khóa nghiệp vụ đích:** `source_system, admission_id`.

**Nguồn và alias:** `a` = `entertainment_ops.admissions`; `t` = `entertainment_ops.tickets`; `o` = `entertainment_ops.ticket_orders`; `x` = `entertainment_ops.activities`; `c` = `entertainment_ops.centres`.

**Điều kiện chọn:** Mọi admission có bằng chứng entered_at và quan hệ hợp lệ; không lọc tickets.status=USED.

**Trình tự biến đổi:**

1. Kiểm tra x.centre_id=o.centre_id; ngày địa phương từ entered_at.
2. Tra customer/centre/activity/site tại entered_at chính xác. Kiểm tra activity/day với capacity F10.
3. Ngày đóng hoặc vượt capacity xử lý theo nhóm R10. Không lọc admission theo valid_date khi đã có timestamp thật.

**Đường nối và cardinality:**

| Điều kiện | Quan hệ và cách nối | Khi không đạt |
|---|---|---|
| `a.ticket_id=t.ticket_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |
| `t.ticket_order_id=o.ticket_order_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |
| `t.activity_id=x.activity_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |
| `x.centre_id=c.centre_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |

**Mốc chọn phiên bản:** entered_at_utc chính xác, không chỉ ngày.

**Mapping cột nghiệp vụ:**

| Cột đích | Kiểu và NULL | Biểu thức biến đổi | Diễn giải |
|---|---|---|---|
| `fact_key` | KEY; NOT NULL | `REGISTRY(F09, source_system, admission_id)` | Khóa grain dùng ID bền vững, không SCD SK; giữ nguyên qua correction/replay. |
| `source_system` | CODE; NOT NULL | `'entertainment_ops'` | Namespace thuộc ID gốc, không đổi thành tên Oracle/Iceberg; dòng đặc biệt dimension dùng system. |
| `admission_date_key` | DATEKEY; NOT NULL | `DATEKEY(LOCAL_DATE(a.entered_at))` | Namespace calendar; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `site_key` | KEY; NOT NULL | `LOOKUP_SCD(D02, namespace, DIM_ATTR(D11,DIM_ATTR(D12,t.activity_id,UTC(a.entered_at),'centre_id'),UTC(a.entered_at),'site_code'), UTC(a.entered_at))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `customer_profile_key` | KEY; NOT NULL | `LOOKUP_SCD(D07, namespace, o.customer_id, UTC(a.entered_at))` | Namespace entertainment_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `centre_key` | KEY; NOT NULL | `LOOKUP_SCD(D11, namespace, DIM_ATTR(D12,t.activity_id,UTC(a.entered_at),'centre_id'), UTC(a.entered_at))` | Namespace entertainment_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `activity_key` | KEY; NOT NULL | `LOOKUP_SCD(D12, namespace, t.activity_id, UTC(a.entered_at))` | Namespace entertainment_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `admission_id` | ID; NOT NULL | `a.admission_id` | Chép giá trị nguồn sau kiểm tra R02; Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Không tính lại bằng danh mục hiện hành. |
| `ticket_id` | ID; NOT NULL | `a.ticket_id` | Chép giá trị nguồn sau kiểm tra R02; Tham chiếu bản ghi tickets trong cùng database. Không tính lại bằng danh mục hiện hành. |
| `entered_at_utc` | UTC; NOT NULL | `UTC(a.entered_at)` | Chép giá trị nguồn sau kiểm tra R02; Thời điểm vào thực tế. Múi giờ nguồn +07:00. Không tính lại bằng danh mục hiện hành. |
| `admission_count` | COUNT; NOT NULL | `1` | 1 cho mỗi admission, không phải một ticket. Thực hiện sau các kiểm tra và bước tổng hợp của kế hoạch bảng; không coi vắng nguồn hoặc lỗi là 0. |

**Cột dùng chung:** `source_batch_id`, `transform_version`, `row_hash`, `created_at_utc`, `updated_at_utc`. Áp dụng đầy đủ mục audit/SCD ở trên; JSON vẫn chứa một mapping cho từng cột.

**Ràng buộc và nghiệm thu:**

- Ngày vào lấy sau chuyển UTC sang Asia/Ho_Chi_Minh; không thay bằng valid_date.
- Activity và centre của ticket/order nhất quán; lượt vào ngày đóng cửa hoặc vượt capacity phải được kiểm tra.
- Không thay entered_at bằng valid_date hoặc chỉ nhận vé USED. Admission RESCHEDULED hợp lệ vẫn tính; vượt capacity/đóng cửa phải báo lỗi.
- Lookup dimension NORMAL theo namespace + BK và valid_from <= t < valid_to (NULL là vô hạn); đúng một phiên bản. Thiếu/trùng phiên bản -> quarantine dòng phụ thuộc, không lấy current thay thế.
- Quy tắc áp dụng: R01, R02, R03, R04, R05, R07, R08, R10, R15, R16, R17.

### F10 FactActivityDay

**Đích:** `fact_activity_day`. **Grain:** Một hoạt động và ngày danh mục.

**Khóa nghiệp vụ đích:** `source_system, activity_id, date_key`.

**Nguồn và alias:** `a` = `entertainment_ops.activities`; `c` = `entertainment_ops.centres`; `cl` = `entertainment_ops.closures`.

**Điều kiện chọn:** Activity x ngày công suất; closure chỉ dùng EXISTS(activity_id,closed_on).

**Trình tự biến đổi:**

1. nominal_capacity lấy capacity_per_day phiên bản activity đúng ngày.
2. is_closed=1 nếu closure hợp lệ tồn tại, available=nominal*(1-is_closed). Nhiều lý do đóng không nhân dòng.
3. Không có closure chỉ suy open nếu coverage nguồn closures đầy đủ.

**Đường nối và cardinality:**

| Điều kiện | Quan hệ và cách nối | Khi không đạt |
|---|---|---|
| `a.centre_id=c.centre_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |

**Mốc chọn phiên bản:** date_key tại 00:00 giờ Việt Nam.

**Mapping cột nghiệp vụ:**

| Cột đích | Kiểu và NULL | Biểu thức biến đổi | Diễn giải |
|---|---|---|---|
| `fact_key` | KEY; NOT NULL | `REGISTRY(F10, source_system, activity_id, date_key)` | Khóa grain dùng ID bền vững, không SCD SK; giữ nguyên qua correction/replay. |
| `source_system` | CODE; NOT NULL | `'entertainment_ops'` | Namespace thuộc ID gốc, không đổi thành tên Oracle/Iceberg; dòng đặc biệt dimension dùng system. |
| `activity_id` | ID; NOT NULL | `a.activity_id` | Chép giá trị nguồn sau kiểm tra R02; Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Không tính lại bằng danh mục hiện hành. |
| `date_key` | DATEKEY; NOT NULL | `DATEKEY($day)` | Namespace calendar; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `site_key` | KEY; NOT NULL | `LOOKUP_SCD(D02, namespace, DIM_ATTR(D11,DIM_ATTR(D12,a.activity_id,LOCAL_START($day),'centre_id'),LOCAL_START($day),'site_code'), LOCAL_START($day))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `centre_key` | KEY; NOT NULL | `LOOKUP_SCD(D11, namespace, DIM_ATTR(D12,a.activity_id,LOCAL_START($day),'centre_id'), LOCAL_START($day))` | Namespace entertainment_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `activity_key` | KEY; NOT NULL | `LOOKUP_SCD(D12, namespace, a.activity_id, LOCAL_START($day))` | Namespace entertainment_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `nominal_capacity` | COUNT; NOT NULL | `LOOKUP_SCD(D12,a.activity_id,LOCAL_START($day)).capacity_per_day` | capacity_per_day của activity. Thực hiện sau các kiểm tra và bước tổng hợp của kế hoạch bảng; không coi vắng nguồn hoặc lỗi là 0. |
| `is_closed` | FLAG; NOT NULL | `EXISTS(valid cl WHERE cl.activity_id=a.activity_id AND cl.closed_on=$day)` | 1 nếu tồn tại closure cùng activity/date. Thực hiện sau các kiểm tra và bước tổng hợp của kế hoạch bảng; không coi vắng nguồn hoặc lỗi là 0. |
| `available_capacity` | COUNT; NOT NULL | `nominal_capacity * (1 - is_closed)` | nominal_capacity*(1-is_closed). Thực hiện sau các kiểm tra và bước tổng hợp của kế hoạch bảng; không coi vắng nguồn hoặc lỗi là 0. |

**Cột dùng chung:** `source_batch_id`, `transform_version`, `row_hash`, `created_at_utc`, `updated_at_utc`. Áp dụng đầy đủ mục audit/SCD ở trên; JSON vẫn chứa một mapping cho từng cột.

**Ràng buộc và nghiệm thu:**

- nominal_capacity>0; is_closed IN (0,1); available_capacity=nominal_capacity*(1-is_closed).
- Closure đóng trọn ngày; gộp nhiều lý do trước khi tính. Không có phân bổ capacity theo khách, kênh hoặc khách sạn giới thiệu.
- Lookup dimension NORMAL theo namespace + BK và valid_from <= t < valid_to (NULL là vô hạn); đúng một phiên bản. Thiếu/trùng phiên bản -> quarantine dòng phụ thuộc, không lấy current thay thế.
- Quy tắc áp dụng: R01, R02, R03, R04, R05, R07, R10, R15, R16, R17.

### F11 FactVehicleDay

**Đích:** `fact_vehicle_day`. **Grain:** Một xe và ngày danh mục.

**Khóa nghiệp vụ đích:** `source_system, vehicle_id, date_key`.

**Nguồn và alias:** `v` = `entertainment_ops.vehicles`; `c` = `entertainment_ops.centres`; `r` = `entertainment_ops.rentals`; `m` = `entertainment_ops.vehicle_maintenance`.

**Điều kiện chọn:** Vehicle x ngày công suất; rentals COMPLETED được expand độc lập; maintenance lấy union ngày.

**Trình tự biến đổi:**

1. Dựng inventory=1; maintenance_day từ EXISTS; available=1-maintenance.
2. Kiểm tra số hợp đồng thuê mỗi vehicle/day<=1 và không trùng bảo trì; conflict làm scope vehicle/day không đạt, không kẹp rented về 1.
3. rented_day từ rental vận hành có vehicle/duration/status hợp lệ; lỗi chỉ ở booking_ref của F05 không làm mất bằng chứng ngày xe vận hành, nhưng phải cảnh báo F05/B03 riêng. Không dùng F05 filtered như nguồn duy nhất cho F11.

**Đường nối và cardinality:**

| Điều kiện | Quan hệ và cách nối | Khi không đạt |
|---|---|---|
| `v.centre_id=c.centre_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |

**Mốc chọn phiên bản:** date_key tại 00:00 giờ Việt Nam.

**Mapping cột nghiệp vụ:**

| Cột đích | Kiểu và NULL | Biểu thức biến đổi | Diễn giải |
|---|---|---|---|
| `fact_key` | KEY; NOT NULL | `REGISTRY(F11, source_system, vehicle_id, date_key)` | Khóa grain dùng ID bền vững, không SCD SK; giữ nguyên qua correction/replay. |
| `source_system` | CODE; NOT NULL | `'entertainment_ops'` | Namespace thuộc ID gốc, không đổi thành tên Oracle/Iceberg; dòng đặc biệt dimension dùng system. |
| `vehicle_id` | ID; NOT NULL | `v.vehicle_id` | Chép giá trị nguồn sau kiểm tra R02; Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Không tính lại bằng danh mục hiện hành. |
| `date_key` | DATEKEY; NOT NULL | `DATEKEY($day)` | Namespace calendar; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `site_key` | KEY; NOT NULL | `LOOKUP_SCD(D02, namespace, DIM_ATTR(D11,DIM_ATTR(D13,v.vehicle_id,LOCAL_START($day),'centre_id'),LOCAL_START($day),'site_code'), LOCAL_START($day))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `centre_key` | KEY; NOT NULL | `LOOKUP_SCD(D11, namespace, DIM_ATTR(D13,v.vehicle_id,LOCAL_START($day),'centre_id'), LOCAL_START($day))` | Namespace entertainment_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `vehicle_key` | KEY; NOT NULL | `LOOKUP_SCD(D13, namespace, v.vehicle_id, LOCAL_START($day))` | Namespace entertainment_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `inventory_day` | FLAG; NOT NULL | `1` | 1 trong lịch công suất. Thực hiện sau các kiểm tra và bước tổng hợp của kế hoạch bảng; không coi vắng nguồn hoặc lỗi là 0. |
| `maintenance_day` | FLAG; NOT NULL | `EXISTS(valid m WHERE m.vehicle_id=v.vehicle_id AND m.starts_on<=$day<m.ends_on)` | 1 nếu thuộc union ngày bảo trì xe. Thực hiện sau các kiểm tra và bước tổng hợp của kế hoạch bảng; không coi vắng nguồn hoặc lỗi là 0. |
| `available_day` | FLAG; NOT NULL | `1 - maintenance_day` | 1-maintenance_day. Thực hiện sau các kiểm tra và bước tổng hợp của kế hoạch bảng; không coi vắng nguồn hoặc lỗi là 0. |
| `rented_day` | FLAG; NOT NULL | `COUNT(valid r WHERE r.vehicle_id=v.vehicle_id AND r.status='COMPLETED' AND r.pickup_date<=$day<r.return_date); require count<=1` | 1 nếu thuộc một rental COMPLETED. Thực hiện sau các kiểm tra và bước tổng hợp của kế hoạch bảng; không coi vắng nguồn hoặc lỗi là 0. |

**Cột dùng chung:** `source_batch_id`, `transform_version`, `row_hash`, `created_at_utc`, `updated_at_utc`. Áp dụng đầy đủ mục audit/SCD ở trên; JSON vẫn chứa một mapping cho từng cột.

**Ràng buộc và nghiệm thu:**

- inventory_day=1; available_day=1-maintenance_day; rented_day<=available_day.
- Hai rental cùng vehicle-day là lỗi; không DISTINCT để che overlap.
- rented_day từ COMPLETED; overlap thuê hoặc thuê trong bảo trì là lỗi. Không chứa agreed_vnd nhân theo số ngày.
- Lookup dimension NORMAL theo namespace + BK và valid_from <= t < valid_to (NULL là vô hạn); đúng một phiên bản. Thiếu/trùng phiên bản -> quarantine dòng phụ thuộc, không lấy current thay thế.
- Quy tắc áp dụng: R01, R02, R03, R04, R05, R07, R08, R10, R15, R16, R17.

### F12 FactPurchaseLine

**Đích:** `fact_purchase_line`. **Grain:** Một dòng đặt mua.

**Khóa nghiệp vụ đích:** `source_system, purchase_line_id`.

**Nguồn và alias:** `l` = `hotel_ops.purchase_lines`; `p` = `hotel_ops.purchase_orders`; `h` = `hotel_ops.hotels`.

**Điều kiện chọn:** Mọi dòng đặt mua hợp lệ; chưa áp cutoff A hoặc điều kiện đã nhận ở bước nạp.

**Trình tự biến đổi:**

1. Lấy quantity/unit_price ở l và date/supplier/hotel ở p; tra dimension tại ordered_on.
2. Giữ ordered_qty một lần, không join detail receipts khi nạp F12.
3. Lọc expected_on, cutoff A và aggregate receipt thực hiện ở lớp KPI B06.

**Đường nối và cardinality:**

| Điều kiện | Quan hệ và cách nối | Khi không đạt |
|---|---|---|
| `l.purchase_order_id=p.purchase_order_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |
| `p.hotel_id=h.hotel_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |

**Mốc chọn phiên bản:** ordered_date_key tại 00:00 giờ Việt Nam.

**Mapping cột nghiệp vụ:**

| Cột đích | Kiểu và NULL | Biểu thức biến đổi | Diễn giải |
|---|---|---|---|
| `fact_key` | KEY; NOT NULL | `REGISTRY(F12, source_system, purchase_line_id)` | Khóa grain dùng ID bền vững, không SCD SK; giữ nguyên qua correction/replay. |
| `source_system` | CODE; NOT NULL | `'hotel_ops'` | Namespace thuộc ID gốc, không đổi thành tên Oracle/Iceberg; dòng đặc biệt dimension dùng system. |
| `ordered_date_key` | DATEKEY; NOT NULL | `DATEKEY(p.ordered_on)` | Namespace calendar; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `expected_date_key` | DATEKEY; NOT NULL | `DATEKEY(p.expected_on)` | Namespace calendar; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `site_key` | KEY; NOT NULL | `LOOKUP_SCD(D02, namespace, DIM_ATTR(D03,p.hotel_id,LOCAL_START(p.ordered_on),'site_id'), LOCAL_START(p.ordered_on))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `hotel_key` | KEY; NOT NULL | `LOOKUP_SCD(D03, namespace, p.hotel_id, LOCAL_START(p.ordered_on))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `supplier_key` | KEY; NOT NULL | `LOOKUP_SCD(D14, namespace, p.supplier_id, LOCAL_START(p.ordered_on))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `item_key` | KEY; NOT NULL | `LOOKUP_SCD(D15, namespace, l.item_id, LOCAL_START(p.ordered_on))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `purchase_line_id` | ID; NOT NULL | `l.purchase_line_id` | Chép giá trị nguồn sau kiểm tra R02; Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Không tính lại bằng danh mục hiện hành. |
| `purchase_order_id` | ID; NOT NULL | `l.purchase_order_id` | Chép giá trị nguồn sau kiểm tra R02; Tham chiếu bản ghi purchase_orders trong cùng database. Không tính lại bằng danh mục hiện hành. |
| `ordered_qty` | QTY; NOT NULL | `l.ordered_qty` | Chép giá trị nguồn sau kiểm tra R02; Lượng đặt theo đơn vị chuẩn. Không tính lại bằng danh mục hiện hành. |
| `unit_price_vnd` | MONEY; NOT NULL | `l.unit_price_vnd` | Chép giá trị nguồn sau kiểm tra R02; Đơn giá thỏa thuận trên đơn vị chuẩn. Số nguyên VND; không dùng float cho tiền. Không tính lại bằng danh mục hiện hành. |

**Cột dùng chung:** `source_batch_id`, `transform_version`, `row_hash`, `created_at_utc`, `updated_at_utc`. Áp dụng đầy đủ mục audit/SCD ở trên; JSON vẫn chứa một mapping cho từng cột.

**Ràng buộc và nghiệm thu:**

- ordered_qty>0; unit_price_vnd>=0; ordered_date<=expected_date.
- B06 cohort theo expected_date và A; dòng chưa receipt vẫn tồn tại.
- Giữ dòng đến hạn không receipt. Ordered_qty tính một lần; không lặp theo từng lần giao. Mỗi A phải tổng lại receipt received_on<=A.
- Lookup dimension NORMAL theo namespace + BK và valid_from <= t < valid_to (NULL là vô hạn); đúng một phiên bản. Thiếu/trùng phiên bản -> quarantine dòng phụ thuộc, không lấy current thay thế.
- Quy tắc áp dụng: R01, R02, R03, R04, R05, R07, R12, R15, R16, R17.

### F13 FactReceipt

**Đích:** `fact_receipt`. **Grain:** Một lần nhận của một dòng đặt mua.

**Khóa nghiệp vụ đích:** `source_system, receipt_id`.

**Nguồn và alias:** `r` = `hotel_ops.receipts`; `l` = `hotel_ops.purchase_lines`; `p` = `hotel_ops.purchase_orders`; `h` = `hotel_ops.hotels`.

**Điều kiện chọn:** Mỗi receipt DB hợp lệ một dòng, gồm nhiều lần giao cùng line; không áp A tại nạp.

**Trình tự biến đổi:**

1. Lấy supplier/hotel/item theo PO/line; dimension fact tra tại received_on.
2. late_accepted=accepted khi received_on>expected_on. expires NULL->Date UNKNOWN.
3. B06 đối chiếu về F12 qua purchase_line_id và dùng cohort F12; feed ngoài chỉ đối soát.

**Đường nối và cardinality:**

| Điều kiện | Quan hệ và cách nối | Khi không đạt |
|---|---|---|
| `r.purchase_line_id=l.purchase_line_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |
| `l.purchase_order_id=p.purchase_order_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |
| `p.hotel_id=h.hotel_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |

**Mốc chọn phiên bản:** received_date_key tại 00:00 giờ Việt Nam.

**Mapping cột nghiệp vụ:**

| Cột đích | Kiểu và NULL | Biểu thức biến đổi | Diễn giải |
|---|---|---|---|
| `fact_key` | KEY; NOT NULL | `REGISTRY(F13, source_system, receipt_id)` | Khóa grain dùng ID bền vững, không SCD SK; giữ nguyên qua correction/replay. |
| `source_system` | CODE; NOT NULL | `'hotel_ops'` | Namespace thuộc ID gốc, không đổi thành tên Oracle/Iceberg; dòng đặc biệt dimension dùng system. |
| `received_date_key` | DATEKEY; NOT NULL | `DATEKEY(r.received_on)` | Namespace calendar; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `expected_date_key` | DATEKEY; NOT NULL | `DATEKEY(p.expected_on)` | Namespace calendar; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `expires_date_key` | DATEKEY; NOT NULL | `DATEKEY(r.expires_on)` | Namespace calendar; NULL: NULL -> 0. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `site_key` | KEY; NOT NULL | `LOOKUP_SCD(D02, namespace, DIM_ATTR(D03,p.hotel_id,LOCAL_START(r.received_on),'site_id'), LOCAL_START(r.received_on))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `hotel_key` | KEY; NOT NULL | `LOOKUP_SCD(D03, namespace, p.hotel_id, LOCAL_START(r.received_on))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `supplier_key` | KEY; NOT NULL | `LOOKUP_SCD(D14, namespace, p.supplier_id, LOCAL_START(r.received_on))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `item_key` | KEY; NOT NULL | `LOOKUP_SCD(D15, namespace, l.item_id, LOCAL_START(r.received_on))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `receipt_id` | ID; NOT NULL | `r.receipt_id` | Chép giá trị nguồn sau kiểm tra R02; Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Không tính lại bằng danh mục hiện hành. |
| `purchase_line_id` | ID; NOT NULL | `r.purchase_line_id` | Chép giá trị nguồn sau kiểm tra R02; Tham chiếu bản ghi purchase_lines trong cùng database. Không tính lại bằng danh mục hiện hành. |
| `accepted_qty` | QTY; NOT NULL | `r.accepted_qty` | Chép giá trị nguồn sau kiểm tra R02; Lượng chấp nhận. Không tính lại bằng danh mục hiện hành. |
| `rejected_qty` | QTY; NOT NULL | `r.rejected_qty` | Chép giá trị nguồn sau kiểm tra R02; Lượng từ chối. Không tính lại bằng danh mục hiện hành. |
| `late_accepted_qty` | QTY; NOT NULL | `CASE WHEN r.received_on > p.expected_on THEN r.accepted_qty ELSE 0 END` | accepted_qty nếu received_date>expected_date, ngược lại 0. Thực hiện sau các kiểm tra và bước tổng hợp của kế hoạch bảng; không coi vắng nguồn hoặc lỗi là 0. |

**Cột dùng chung:** `source_batch_id`, `transform_version`, `row_hash`, `created_at_utc`, `updated_at_utc`. Áp dụng đầy đủ mục audit/SCD ở trên; JSON vẫn chứa một mapping cho từng cột.

**Ràng buộc và nghiệm thu:**

- accepted_qty>=0; rejected_qty>=0; late_accepted_qty IN (0,accepted_qty) theo ngày nhận/hẹn.
- Không cộng receipt feed bên ngoài; expires_on NULL là chưa biết hạn dùng (date_key=0).
- Feed ngoài là đối chiếu, không cộng thêm receipt. receipt_id cũng là định danh lô; rejected không nhập kho và không thành WASTE.
- Lookup dimension NORMAL theo namespace + BK và valid_from <= t < valid_to (NULL là vô hạn); đúng một phiên bản. Thiếu/trùng phiên bản -> quarantine dòng phụ thuộc, không lấy current thay thế.
- Quy tắc áp dụng: R01, R02, R03, R04, R05, R07, R12, R14, R15, R16, R17.

### F14 FactStockMovement

**Đích:** `fact_stock_movement`. **Grain:** Một chuyển động của một lô tại khách sạn.

**Khóa nghiệp vụ đích:** `source_system, movement_id`.

**Nguồn và alias:** `m` = `hotel_ops.stock_movements`; `r` = `hotel_ops.receipts`; `l` = `hotel_ops.purchase_lines`; `p` = `hotel_ops.purchase_orders`; `h` = `hotel_ops.hotels`.

**Điều kiện chọn:** Mọi movement hợp lệ, không cắt chỉ kỳ report; loại nguyên nhân IN/USE/WASTE ngoài domain.

**Trình tự biến đổi:**

1. Kiểm tra m.hotel_id=p.hotel_id và m.item_id=l.item_id; session_id có giá trị phải tồn tại đúng hotel/ngày khi đối soát.
2. Giá lô l.unit_price_vnd; signed và ba lượng loại theo R13. Không dùng items.reference_cost_vnd.
3. Kiểm tra diễn biến lô theo ngày và đánh dấu scope mất tính đầy đủ; không tự bù lượng âm.

**Đường nối và cardinality:**

| Điều kiện | Quan hệ và cách nối | Khi không đạt |
|---|---|---|
| `m.receipt_id=r.receipt_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |
| `r.purchase_line_id=l.purchase_line_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |
| `l.purchase_order_id=p.purchase_order_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |
| `m.hotel_id=h.hotel_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |

**Mốc chọn phiên bản:** movement_date_key tại 00:00 giờ Việt Nam.

**Mapping cột nghiệp vụ:**

| Cột đích | Kiểu và NULL | Biểu thức biến đổi | Diễn giải |
|---|---|---|---|
| `fact_key` | KEY; NOT NULL | `REGISTRY(F14, source_system, movement_id)` | Khóa grain dùng ID bền vững, không SCD SK; giữ nguyên qua correction/replay. |
| `source_system` | CODE; NOT NULL | `'hotel_ops'` | Namespace thuộc ID gốc, không đổi thành tên Oracle/Iceberg; dòng đặc biệt dimension dùng system. |
| `movement_date_key` | DATEKEY; NOT NULL | `DATEKEY(m.movement_date)` | Namespace calendar; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `site_key` | KEY; NOT NULL | `LOOKUP_SCD(D02, namespace, DIM_ATTR(D03,m.hotel_id,LOCAL_START(m.movement_date),'site_id'), LOCAL_START(m.movement_date))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `hotel_key` | KEY; NOT NULL | `LOOKUP_SCD(D03, namespace, m.hotel_id, LOCAL_START(m.movement_date))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `supplier_key` | KEY; NOT NULL | `LOOKUP_SCD(D14, namespace, p.supplier_id, LOCAL_START(m.movement_date))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `item_key` | KEY; NOT NULL | `LOOKUP_SCD(D15, namespace, l.item_id, LOCAL_START(m.movement_date))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `movement_id` | ID; NOT NULL | `m.movement_id` | Chép giá trị nguồn sau kiểm tra R02; Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Không tính lại bằng danh mục hiện hành. |
| `receipt_id` | ID; NOT NULL | `m.receipt_id` | Chép giá trị nguồn sau kiểm tra R02; Tham chiếu bản ghi receipts trong cùng database. Không tính lại bằng danh mục hiện hành. |
| `session_id` | ID; NULL | `m.session_id` | Chép giá trị nguồn sau kiểm tra R02; Tham chiếu bản ghi meal_sessions trong cùng database. Không tính lại bằng danh mục hiện hành. |
| `movement_type` | TEXT; NOT NULL | `m.movement_type` | Chép giá trị nguồn sau kiểm tra R02; IN, USE hoặc WASTE. Không tính lại bằng danh mục hiện hành. |
| `usage_area` | TEXT; NOT NULL | `m.usage_area` | Chép giá trị nguồn sau kiểm tra R02; BUFFET, KITCHEN_OTHER, HOUSEKEEPING hoặc WAREHOUSE. Không tính lại bằng danh mục hiện hành. |
| `quantity` | QTY; NOT NULL | `m.quantity` | Chép giá trị nguồn sau kiểm tra R02; Số dương; chiều theo loại. Không tính lại bằng danh mục hiện hành. |
| `signed_qty` | QTY; NOT NULL | `CASE WHEN m.movement_type='IN' THEN m.quantity ELSE -m.quantity END` | +quantity nếu IN; -quantity nếu USE/WASTE. Thực hiện sau các kiểm tra và bước tổng hợp của kế hoạch bảng; không coi vắng nguồn hoặc lỗi là 0. |
| `in_qty` | QTY; NOT NULL | `CASE WHEN m.movement_type='IN' THEN m.quantity ELSE 0 END` | quantity nếu IN, ngược lại 0. Thực hiện sau các kiểm tra và bước tổng hợp của kế hoạch bảng; không coi vắng nguồn hoặc lỗi là 0. |
| `use_qty` | QTY; NOT NULL | `CASE WHEN m.movement_type='USE' THEN m.quantity ELSE 0 END` | quantity nếu USE, ngược lại 0. Thực hiện sau các kiểm tra và bước tổng hợp của kế hoạch bảng; không coi vắng nguồn hoặc lỗi là 0. |
| `waste_qty` | QTY; NOT NULL | `CASE WHEN m.movement_type='WASTE' THEN m.quantity ELSE 0 END` | quantity nếu WASTE, ngược lại 0. Thực hiện sau các kiểm tra và bước tổng hợp của kế hoạch bảng; không coi vắng nguồn hoặc lỗi là 0. |
| `unit_price_vnd` | MONEY; NOT NULL | `l.unit_price_vnd` | Chép giá trị nguồn sau kiểm tra R02; Giá lô từ purchase_line của receipt. Không tính lại bằng danh mục hiện hành. |
| `movement_value_vnd` | VALUE; NOT NULL | `CAST(m.quantity * l.unit_price_vnd AS VALUE)` | quantity*unit_price_vnd; đây là trị tuyệt đối, lọc movement_type khi tính WASTE/IN. Thực hiện sau các kiểm tra và bước tổng hợp của kế hoạch bảng; không coi vắng nguồn hoặc lỗi là 0. |

**Cột dùng chung:** `source_batch_id`, `transform_version`, `row_hash`, `created_at_utc`, `updated_at_utc`. Áp dụng đầy đủ mục audit/SCD ở trên; JSON vẫn chứa một mapping cho từng cột.

**Ràng buộc và nghiệm thu:**

- movement_type IN (IN,USE,WASTE); quantity>=0; signed_qty=in_qty-use_qty-waste_qty.
- Hotel/item khớp lô receipt và purchase order; balance cộng dồn theo lô không âm.
- session_id optional; không suy usage_area thành dimension kho.
- Tồn đầu=sum trước S; cuối=sum trước E. Không có warehouse_id nên chưa tạo DimWarehouse vật lý. usage_area chỉ lọc lượng USE, không lọc tồn. session_id phục vụ drill-through có kiểm soát.
- Lookup dimension NORMAL theo namespace + BK và valid_from <= t < valid_to (NULL là vô hạn); đúng một phiên bản. Thiếu/trùng phiên bản -> quarantine dòng phụ thuộc, không lấy current thay thế.
- Quy tắc áp dụng: R01, R02, R03, R04, R05, R07, R13, R15, R16, R17.

### F15 AggInventoryLotDay

**Đích:** `agg_inventory_lot_day`. **Grain:** Một lô, khách sạn, mặt hàng và ngày cuối ngày.

**Khóa nghiệp vụ đích:** `source_system, receipt_id, hotel_id, item_id, snapshot_date_key`.

**Nguồn và alias:** `r` = `hotel_ops.receipts`; `l` = `hotel_ops.purchase_lines`; `p` = `hotel_ops.purchase_orders`; `h` = `hotel_ops.hotels`.

**Điều kiện chọn:** Tùy chọn vật hóa từ F14 đã công bố hợp lệ; chỉ lot-day có ledger đủ từ đầu kỳ mô phỏng tới ngày đó.

**Trình tự biến đổi:**

1. Sinh lot/day từ max(received_on,capacity_start) tới cuối kỳ; ngày không movement vẫn có số dư carry-forward.
2. F14 aggregate theo namespace/receipt_id/hotel_id/item_id/day, tính prefix sum signed_qty. Định giá closing theo giá lô.
3. F14 không lưu hotel_id/item_id dạng DD: giải mã qua dimension row mà FK trỏ tới để lấy BK; không lấy dimension current. Tra lại SCD cho ngày snapshot F15.
4. Không giữ closing cho scope ledger thiếu; correction từ ngày d rebuild d..cuối kỳ.

**Đường nối và cardinality:**

| Điều kiện | Quan hệ và cách nối | Khi không đạt |
|---|---|---|
| `r.purchase_line_id=l.purchase_line_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |
| `l.purchase_order_id=p.purchase_order_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |
| `p.hotel_id=h.hotel_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |

**Mốc chọn phiên bản:** snapshot_date_key tại 00:00 giờ Việt Nam; số dư đo cuối ngày, phân loại danh mục tại đầu ngày.

**Mapping cột nghiệp vụ:**

| Cột đích | Kiểu và NULL | Biểu thức biến đổi | Diễn giải |
|---|---|---|---|
| `fact_key` | KEY; NOT NULL | `REGISTRY(F15, source_system, receipt_id, hotel_id, item_id, snapshot_date_key)` | Khóa grain dùng ID bền vững, không SCD SK; giữ nguyên qua correction/replay. |
| `source_system` | CODE; NOT NULL | `'hotel_ops'` | Namespace thuộc ID gốc, không đổi thành tên Oracle/Iceberg; dòng đặc biệt dimension dùng system. |
| `hotel_id` | ID; NOT NULL | `p.hotel_id` | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Thực hiện sau các kiểm tra và bước tổng hợp của kế hoạch bảng; không coi vắng nguồn hoặc lỗi là 0. |
| `item_id` | ID; NOT NULL | `l.item_id` | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Thực hiện sau các kiểm tra và bước tổng hợp của kế hoạch bảng; không coi vắng nguồn hoặc lỗi là 0. |
| `snapshot_date_key` | DATEKEY; NOT NULL | `DATEKEY($day)` | Namespace calendar; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `site_key` | KEY; NOT NULL | `LOOKUP_SCD(D02, namespace, DIM_ATTR(D03,p.hotel_id,LOCAL_START($day),'site_id'), LOCAL_START($day))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `hotel_key` | KEY; NOT NULL | `LOOKUP_SCD(D03, namespace, p.hotel_id, LOCAL_START($day))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `supplier_key` | KEY; NOT NULL | `LOOKUP_SCD(D14, namespace, p.supplier_id, LOCAL_START($day))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `item_key` | KEY; NOT NULL | `LOOKUP_SCD(D15, namespace, l.item_id, LOCAL_START($day))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `receipt_id` | ID; NOT NULL | `r.receipt_id` | Chép giá trị nguồn sau kiểm tra R02; Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Không tính lại bằng danh mục hiện hành. |
| `closing_qty` | QTY; NOT NULL | `SUM(F14.signed_qty WHERE same durable lot key AND movement_date <= $day)` | SUM signed_qty tới hết snapshot_date. Thực hiện sau các kiểm tra và bước tổng hợp của kế hoạch bảng; không coi vắng nguồn hoặc lỗi là 0. |
| `closing_value_vnd` | VALUE; NOT NULL | `CAST(closing_qty * l.unit_price_vnd AS VALUE)` | closing_qty*giá lô. Thực hiện sau các kiểm tra và bước tổng hợp của kế hoạch bảng; không coi vắng nguồn hoặc lỗi là 0. |
| `in_qty` | QTY; NOT NULL | `SUM(F14.in_qty WHERE same durable lot key AND movement_date=$day)` | Lượng của loại tương ứng trong đúng snapshot_date. Thực hiện sau các kiểm tra và bước tổng hợp của kế hoạch bảng; không coi vắng nguồn hoặc lỗi là 0. |
| `use_qty` | QTY; NOT NULL | `SUM(F14.use_qty WHERE same durable lot key AND movement_date=$day)` | Lượng của loại tương ứng trong đúng snapshot_date. Thực hiện sau các kiểm tra và bước tổng hợp của kế hoạch bảng; không coi vắng nguồn hoặc lỗi là 0. |
| `waste_qty` | QTY; NOT NULL | `SUM(F14.waste_qty WHERE same durable lot key AND movement_date=$day)` | Lượng của loại tương ứng trong đúng snapshot_date. Thực hiện sau các kiểm tra và bước tổng hợp của kế hoạch bảng; không coi vắng nguồn hoặc lỗi là 0. |

**Cột dùng chung:** `source_batch_id`, `transform_version`, `row_hash`, `created_at_utc`, `updated_at_utc`. Áp dụng đầy đủ mục audit/SCD ở trên; JSON vẫn chứa một mapping cho từng cột.

**Ràng buộc và nghiệm thu:**

- closing_qty>=0; cuối ngày d=cuối ngày d-1+in_qty-use_qty-waste_qty.
- Giữ lô còn tồn cả ngày không biến động; không SUM số dư qua ngày hoặc cộng F14+F15.
- Tùy chọn vật hóa từ F14. Không cộng closing qua ngày; đầu kỳ lấy cuối ngày trước S hoặc lịch sử F14. Giữ lô còn tồn dù không có movement trong kỳ. Không cộng F14 và F15.
- Lookup dimension NORMAL theo namespace + BK và valid_from <= t < valid_to (NULL là vô hạn); đúng một phiên bản. Thiếu/trùng phiên bản -> quarantine dòng phụ thuộc, không lấy current thay thế.
- Quy tắc áp dụng: R01, R02, R03, R04, R05, R07, R13, R15, R16, R17.

### F16 FactMaintenanceWork

**Đích:** `fact_maintenance_work`. **Grain:** Một công việc bảo trì tài sản khách sạn.

**Khóa nghiệp vụ đích:** `source_system, maintenance_id`.

**Nguồn và alias:** `m` = `hotel_ops.maintenance`; `a` = `hotel_ops.assets`; `h` = `hotel_ops.hotels`.

**Điều kiện chọn:** Mọi công việc hợp lệ; nguồn v2 chỉ có COMPLETED, work_type PLANNED/BREAKDOWN.

**Trình tự biến đổi:**

1. Giữ cost một lần, dimension tra tại starts_on; KPI chi phí lọc ends_on và COMPLETED.
2. a.room_id NULL -> room_key=-1; không suy asset khu chung làm ngừng toàn hotel.
3. Không dùng a.supplier_id như nhà thầu sửa chữa và không cộng vehicle_maintenance vào F16.

**Đường nối và cardinality:**

| Điều kiện | Quan hệ và cách nối | Khi không đạt |
|---|---|---|
| `m.asset_id=a.asset_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |
| `a.hotel_id=h.hotel_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |

**Mốc chọn phiên bản:** start_date_key tại 00:00 giờ Việt Nam; ngày ghi nhận KPI chi phí vẫn là end_date_key.

**Mapping cột nghiệp vụ:**

| Cột đích | Kiểu và NULL | Biểu thức biến đổi | Diễn giải |
|---|---|---|---|
| `fact_key` | KEY; NOT NULL | `REGISTRY(F16, source_system, maintenance_id)` | Khóa grain dùng ID bền vững, không SCD SK; giữ nguyên qua correction/replay. |
| `source_system` | CODE; NOT NULL | `'hotel_ops'` | Namespace thuộc ID gốc, không đổi thành tên Oracle/Iceberg; dòng đặc biệt dimension dùng system. |
| `start_date_key` | DATEKEY; NOT NULL | `DATEKEY(m.starts_on)` | Namespace calendar; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `end_date_key` | DATEKEY; NOT NULL | `DATEKEY(m.ends_on)` | Namespace calendar; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `site_key` | KEY; NOT NULL | `LOOKUP_SCD(D02, namespace, DIM_ATTR(D03,DIM_ATTR(D16,m.asset_id,LOCAL_START(m.starts_on),'hotel_id'),LOCAL_START(m.starts_on),'site_id'), LOCAL_START(m.starts_on))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `hotel_key` | KEY; NOT NULL | `LOOKUP_SCD(D03, namespace, DIM_ATTR(D16,m.asset_id,LOCAL_START(m.starts_on),'hotel_id'), LOCAL_START(m.starts_on))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `room_key` | KEY; NOT NULL | `LOOKUP_SCD(D04, namespace, DIM_ATTR(D16,m.asset_id,LOCAL_START(m.starts_on),'room_id'), LOCAL_START(m.starts_on))` | Namespace hotel_ops; NULL: NULL -> -1. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `asset_key` | KEY; NOT NULL | `LOOKUP_SCD(D16, namespace, m.asset_id, LOCAL_START(m.starts_on))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `maintenance_id` | ID; NOT NULL | `m.maintenance_id` | Chép giá trị nguồn sau kiểm tra R02; Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Không tính lại bằng danh mục hiện hành. |
| `work_type` | TEXT; NOT NULL | `m.work_type` | Chép giá trị nguồn sau kiểm tra R02; PLANNED hoặc BREAKDOWN. Không tính lại bằng danh mục hiện hành. |
| `status` | TEXT; NOT NULL | `m.status` | Chép giá trị nguồn sau kiểm tra R02; COMPLETED. Không tính lại bằng danh mục hiện hành. |
| `cost_vnd` | MONEY; NOT NULL | `m.cost_vnd` | Chép giá trị nguồn sau kiểm tra R02; Chi phí ghi nhận của công việc. Số nguyên VND; không dùng float cho tiền. Không tính lại bằng danh mục hiện hành. |

**Cột dùng chung:** `source_batch_id`, `transform_version`, `row_hash`, `created_at_utc`, `updated_at_utc`. Áp dụng đầy đủ mục audit/SCD ở trên; JSON vẫn chứa một mapping cho từng cột.

**Ràng buộc và nghiệm thu:**

- start_date<end_date; cost_vnd>=0; work_type IN (BREAKDOWN,PLANNED); v2 status=COMPLETED.
- KPI chi phí lấy COMPLETED theo end_date; room_key=-1 cho tài sản không thuộc phòng.
- Tiền ghi một lần, không nhân theo ngày. Supplier của asset là bên bán tài sản, không coi là vendor bảo trì. Ngày chặn phòng dùng F02 và bridge overlap.
- Lookup dimension NORMAL theo namespace + BK và valid_from <= t < valid_to (NULL là vô hạn); đúng một phiên bản. Thiếu/trùng phiên bản -> quarantine dòng phụ thuộc, không lấy current thay thế.
- Quy tắc áp dụng: R01, R02, R03, R04, R05, R07, R09, R10, R15, R16, R17.

### F17 FactWeatherDay

**Đích:** `fact_weather_day`. **Grain:** Một cụm và ngày thời tiết.

**Khóa nghiệp vụ đích:** `source_system, site_id, weather_date_key`; `source_system, weather_id`.

**Nguồn và alias:** `w` = `hotel_ops.weather_daily`.

**Điều kiện chọn:** Một site/weather_date duy nhất; giữ provenance synthetic từ nguồn.

**Trình tự biến đổi:**

1. weather_id vẫn là ID truy vết; trùng site/date không chọn average để che lỗi.
2. Nhiệt độ không SUM; lượng mưa chỉ cộng ngày trong cùng site. severe flag dùng lọc.
3. Khi dùng weather filter mà thiếu site/day, metric có lọc thời tiết phải báo thiếu; metric không dùng weather không tự giảm quality.

Không có join nhiều bảng ở grain đầu vào; lookup dimension và kiểm tra master reference vẫn áp dụng theo contract.

**Mốc chọn phiên bản:** weather_date_key tại 00:00 giờ Việt Nam.

**Mapping cột nghiệp vụ:**

| Cột đích | Kiểu và NULL | Biểu thức biến đổi | Diễn giải |
|---|---|---|---|
| `fact_key` | KEY; NOT NULL | `REGISTRY(F17, source_system, site_id, weather_date_key)` | Khóa grain dùng ID bền vững, không SCD SK; giữ nguyên qua correction/replay. |
| `source_system` | CODE; NOT NULL | `'hotel_ops'` | Namespace thuộc ID gốc, không đổi thành tên Oracle/Iceberg; dòng đặc biệt dimension dùng system. |
| `site_id` | ID; NOT NULL | `w.site_id` | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Thực hiện sau các kiểm tra và bước tổng hợp của kế hoạch bảng; không coi vắng nguồn hoặc lỗi là 0. |
| `weather_date_key` | DATEKEY; NOT NULL | `DATEKEY(w.weather_date)` | Namespace calendar; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `site_key` | KEY; NOT NULL | `LOOKUP_SCD(D02, namespace, w.site_id, LOCAL_START(w.weather_date))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Vai trò dimension theo sơ đồ đã chốt. |
| `weather_id` | ID; NOT NULL | `w.weather_id` | Chép giá trị nguồn sau kiểm tra R02; Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Không tính lại bằng danh mục hiện hành. |
| `provenance` | TEXT; NOT NULL | `w.provenance` | Chép giá trị nguồn sau kiểm tra R02; SYNTHETIC_CLIMATE_SCENARIO, không phải quan trắc thật. Không tính lại bằng danh mục hiện hành. |
| `temperature_c` | INT; NOT NULL | `w.temperature_c` | Chép giá trị nguồn sau kiểm tra R02; Nhiệt độ giả lập theo cụm/ngày. Không tính lại bằng danh mục hiện hành. |
| `rain_mm` | INT; NOT NULL | `w.rain_mm` | Chép giá trị nguồn sau kiểm tra R02; Lượng mưa ngày; chỉ cộng qua ngày trong cùng site. Không tính lại bằng danh mục hiện hành. |
| `severe_weather` | FLAG; NOT NULL | `w.severe_weather` | Chép giá trị nguồn sau kiểm tra R02; Cờ thời tiết cực đoan; dùng lọc, không cộng như lượng mưa. Không tính lại bằng danh mục hiện hành. |

**Cột dùng chung:** `source_batch_id`, `transform_version`, `row_hash`, `created_at_utc`, `updated_at_utc`. Áp dụng đầy đủ mục audit/SCD ở trên; JSON vẫn chứa một mapping cho từng cột.

**Ràng buộc và nghiệm thu:**

- Duy nhất site/date trước join; rain_mm>=0; severe_weather IN (0,1).
- Không SUM nhiệt độ hoặc nhân bản weather khi join admission.
- Ngữ cảnh B05. Nối 1:1 site/date sau khi xác minh duy nhất hoặc semijoin bộ ngày; không nhân thời tiết theo admission rồi lấy SUM. Không kết luận nhân quả.
- Lookup dimension NORMAL theo namespace + BK và valid_from <= t < valid_to (NULL là vô hạn); đúng một phiên bản. Thiếu/trùng phiên bản -> quarantine dòng phụ thuộc, không lấy current thay thế.
- Quy tắc áp dụng: R01, R02, R03, R04, R05, R07, R15, R16, R17.

### L01 BridgeBookingRoom

**Đích:** `bridge_booking_room`. **Grain:** Một booking_room_id trong hotel_ops.

**Khóa nghiệp vụ đích:** `source_system, booking_room_id`.

**Nguồn và alias:** `br` = `hotel_ops.booking_rooms`; `b` = `hotel_ops.bookings`; `r` = `hotel_ops.rooms`; `rp` = `hotel_ops.rate_plans`.

**Điều kiện chọn:** Một booking_room_id hợp lệ, bao gồm booking các trạng thái có trong F01.

**Trình tự biến đổi:**

1. Tra room/rate plan tại booked_on, khớp F01; giữ booking_id làm DD.
2. Chỉ dùng EXISTS/COUNTD để lọc booking; không có allocation_weight hoặc tiền phân bổ.

**Đường nối và cardinality:**

| Điều kiện | Quan hệ và cách nối | Khi không đạt |
|---|---|---|
| `br.booking_id=b.booking_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |
| `br.room_id=r.room_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |
| `br.rate_plan_id=rp.rate_plan_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |

**Mốc chọn phiên bản:** bookings.booked_on của booking liên quan, thống nhất F01.

**Mapping cột nghiệp vụ:**

| Cột đích | Kiểu và NULL | Biểu thức biến đổi | Diễn giải |
|---|---|---|---|
| `source_system` | CODE; NOT NULL | `'hotel_ops'` | Namespace thuộc ID gốc, không đổi thành tên Oracle/Iceberg; dòng đặc biệt dimension dùng system. |
| `booking_room_id` | ID; NOT NULL | `br.booking_room_id` | Chép giá trị nguồn sau kiểm tra R02; Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Không tính lại bằng danh mục hiện hành. |
| `booking_id` | ID; NOT NULL | `br.booking_id` | Chép giá trị nguồn sau kiểm tra R02; Tham chiếu bản ghi bookings trong cùng database. Không tính lại bằng danh mục hiện hành. |
| `room_key` | KEY; NOT NULL | `LOOKUP_SCD(D04, namespace, br.room_id, LOCAL_START(b.booked_on))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Phòng của dòng booking. |
| `rate_plan_key` | KEY; NOT NULL | `LOOKUP_SCD(D08, namespace, br.rate_plan_id, LOCAL_START(b.booked_on))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Gói giá của dòng booking. |

**Cột dùng chung:** `source_batch_id`, `transform_version`, `row_hash`, `created_at_utc`, `updated_at_utc`. Áp dụng đầy đủ mục audit/SCD ở trên; JSON vẫn chứa một mapping cho từng cột.

**Ràng buộc và nghiệm thu:**

- booking_id tồn tại ở booking nguồn; room và rate plan cùng hotel với booking.
- Dùng EXISTS hoặc COUNTD; không mang tiền booking và không cấp allocation weight.
- Quy tắc áp dụng: R01, R02, R03, R04, R05, R07, R09, R15, R16, R17.

### L02 BridgeRoomDayMaintenance

**Đích:** `bridge_room_day_maintenance`. **Grain:** Một phòng/ngày/công việc bảo trì.

**Khóa nghiệp vụ đích:** `source_system, room_id, date_key, maintenance_id`.

**Nguồn và alias:** `m` = `hotel_ops.maintenance`; `a` = `hotel_ops.assets`; `r` = `hotel_ops.rooms`.

**Điều kiện chọn:** Asset có room_id; expand [starts_on,ends_on) giao lịch công suất.

**Trình tự biến đổi:**

1. Một room/day/maintenance duy nhất; các maintenance khác được giữ riêng cho giải thích nguyên nhân.
2. room_id NULL là business_filtered, không lỗi; room có giá trị sai là dependency_excluded.
3. F02 dùng DISTINCT room/day của bridge, không SUM chi phí qua bridge.

**Đường nối và cardinality:**

| Điều kiện | Quan hệ và cách nối | Khi không đạt |
|---|---|---|
| `m.asset_id=a.asset_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |
| `a.room_id=r.room_id` | N:1; LEFT_OPTIONAL_VALIDATED | NULL optional dùng special member; ref có giá trị sai -> dependency_excluded. |

**Mốc chọn phiên bản:** date_key tại 00:00 giờ Việt Nam, thống nhất F02.

**Mapping cột nghiệp vụ:**

| Cột đích | Kiểu và NULL | Biểu thức biến đổi | Diễn giải |
|---|---|---|---|
| `source_system` | CODE; NOT NULL | `'hotel_ops'` | Namespace thuộc ID gốc, không đổi thành tên Oracle/Iceberg; dòng đặc biệt dimension dùng system. |
| `maintenance_id` | ID; NOT NULL | `m.maintenance_id` | Chép giá trị nguồn sau kiểm tra R02; Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Không tính lại bằng danh mục hiện hành. |
| `room_id` | ID; NOT NULL | `r.room_id` | Chép giá trị nguồn sau kiểm tra R02; Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Không tính lại bằng danh mục hiện hành. |
| `room_key` | KEY; NOT NULL | `LOOKUP_SCD(D04, namespace, DIM_ATTR(D16,m.asset_id,LOCAL_START($day),'room_id'), LOCAL_START($day))` | Namespace hotel_ops; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Phòng chịu ảnh hưởng. |
| `date_key` | DATEKEY; NOT NULL | `DATEKEY($day)` | Namespace calendar; NULL: ERROR_REQUIRED. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. Ngày trong [starts_on,ends_on). |

**Cột dùng chung:** `source_batch_id`, `transform_version`, `row_hash`, `created_at_utc`, `updated_at_utc`. Áp dụng đầy đủ mục audit/SCD ở trên; JSON vẫn chứa một mapping cho từng cột.

**Ràng buộc và nghiệm thu:**

- Chỉ asset có room; mỗi cặp room/date/work đúng một lần.
- F02 dùng EXISTS trên room/date; không SUM cost qua bridge.
- Quy tắc áp dụng: R01, R02, R03, R04, R05, R07, R10, R15, R16, R17.

### L03 ValidatedBookingServiceLink

**Đích:** `validated_booking_service_link`. **Grain:** Một service_type/service_id có booking_ref hợp lệ.

**Khóa nghiệp vụ đích:** `service_source_system, service_type, service_id`.

**Nguồn và alias:** `o` = `entertainment_ops.ticket_orders`; `r` = `entertainment_ops.rentals`; `b` = `hotel_ops.bookings`.

**Điều kiện chọn:** UNION ALL TICKET_ORDER và RENTAL có booking_ref khác NULL và tham chiếu đúng.

**Trình tự biến đổi:**

1. service_type tách hai miền ID; mỗi service có tối đa một booking.
2. View chỉ kiểm chứng ref nguồn, không phụ thuộc F04/F05 để tránh vòng load. Có ref nhưng F01 bị loại được xử lý tại fact consumer.
3. Không bắt buộc booking COMPLETED tại view; điều kiện đó thuộc cohort KPI B03.

**Đường nối và cardinality:**

| Điều kiện | Quan hệ và cách nối | Khi không đạt |
|---|---|---|
| `o.hotel_booking_ref=b.booking_id` | N:1; LEFT_OPTIONAL_VALIDATED | NULL optional dùng special member; ref có giá trị sai -> dependency_excluded. |
| `r.hotel_booking_ref=b.booking_id` | N:1; LEFT_OPTIONAL_VALIDATED | NULL optional dùng special member; ref có giá trị sai -> dependency_excluded. |

**Mapping cột nghiệp vụ:**

| Cột đích | Kiểu và NULL | Biểu thức biến đổi | Diễn giải |
|---|---|---|---|
| `service_source_system` | CODE; NOT NULL | `'entertainment_ops'` | entertainment_ops Thực hiện sau các kiểm tra và bước tổng hợp của kế hoạch bảng; không coi vắng nguồn hoặc lỗi là 0. |
| `service_type` | CODE; NOT NULL | `UNION_BRANCH(o -> 'TICKET_ORDER', r -> 'RENTAL')` | TICKET_ORDER hoặc RENTAL Thực hiện sau các kiểm tra và bước tổng hợp của kế hoạch bảng; không coi vắng nguồn hoặc lỗi là 0. |
| `service_id` | ID; NOT NULL | `UNION_BRANCH(o.ticket_order_id, r.rental_id)` | ID ticket_order hoặc rental. Thực hiện sau các kiểm tra và bước tổng hợp của kế hoạch bảng; không coi vắng nguồn hoặc lỗi là 0. |
| `booking_source_system` | CODE; NOT NULL | `'hotel_ops'` | hotel_ops Thực hiện sau các kiểm tra và bước tổng hợp của kế hoạch bảng; không coi vắng nguồn hoặc lỗi là 0. |
| `booking_id` | ID; NOT NULL | `b.booking_id` | Booking đích đã kiểm chứng. Thực hiện sau các kiểm tra và bước tổng hợp của kế hoạch bảng; không coi vắng nguồn hoặc lỗi là 0. |

**Cột dùng chung:** `source_batch_id`, `transform_version`, `row_hash`, `created_at_utc`, `updated_at_utc`. Áp dụng đầy đủ mục audit/SCD ở trên; JSON vẫn chứa một mapping cho từng cột.

**Ràng buộc và nghiệm thu:**

- Mỗi dịch vụ tối đa một booking; thiếu ref không có dòng link; ref có giá trị nhưng sai đưa quarantine.
- Kiểm chứng tồn tại ref độc lập với eligibility B03; cohort B03 tiếp tục lọc booking COMPLETED.
- Quy tắc áp dụng: R01, R02, R04, R09, R15, R16, R17.

### L04 SiteCrosswalk

**Đích:** `site_crosswalk`. **Grain:** Một centre ánh xạ đúng một site.

**Khóa nghiệp vụ đích:** `centre_source_system, centre_id`.

**Nguồn và alias:** `c` = `entertainment_ops.centres`; `s` = `hotel_ops.sites`.

**Điều kiện chọn:** Mỗi centre nguồn có đúng một site tồn tại.

**Trình tự biến đổi:**

1. So mã công khai tuyệt đối, không suy theo tên hay identity truth.
2. Giữ namespace hai đầu, không thêm UNIQUE(site_id) vì mô hình có thể nhiều centre/site.
3. Bảng hỗ trợ validation, không tạo quan hệ snowflake giữa DimCentre và DimSite.

**Đường nối và cardinality:**

| Điều kiện | Quan hệ và cách nối | Khi không đạt |
|---|---|---|
| `c.site_code=s.site_id` | N:1; REQUIRED_VALIDATED | Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng. |

**Mapping cột nghiệp vụ:**

| Cột đích | Kiểu và NULL | Biểu thức biến đổi | Diễn giải |
|---|---|---|---|
| `centre_source_system` | CODE; NOT NULL | `'entertainment_ops'` | entertainment_ops Thực hiện sau các kiểm tra và bước tổng hợp của kế hoạch bảng; không coi vắng nguồn hoặc lỗi là 0. |
| `centre_id` | ID; NOT NULL | `c.centre_id` | Chép giá trị nguồn sau kiểm tra R02; Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Không tính lại bằng danh mục hiện hành. |
| `site_source_system` | CODE; NOT NULL | `'hotel_ops'` | hotel_ops Thực hiện sau các kiểm tra và bước tổng hợp của kế hoạch bảng; không coi vắng nguồn hoặc lỗi là 0. |
| `site_id` | ID; NOT NULL | `c.site_code, validated equal to s.site_id` | centres.site_code trùng sites.site_id. Thực hiện sau các kiểm tra và bước tổng hợp của kế hoạch bảng; không coi vắng nguồn hoặc lỗi là 0. |

**Cột dùng chung:** `source_batch_id`, `transform_version`, `row_hash`, `created_at_utc`, `updated_at_utc`. Áp dụng đầy đủ mục audit/SCD ở trên; JSON vẫn chứa một mapping cho từng cột.

**Ràng buộc và nghiệm thu:**

- Không yêu cầu một site chỉ có một centre bằng UNIQUE; bốn centre/bốn site là dữ liệu case.
- Không suy ánh xạ bằng vị trí hoặc tên gần giống.
- Quy tắc áp dụng: R01, R02, R04, R15, R16, R17.

## Lớp KPI sau khi nạp fact

Các phép tính dưới đây thực hiện trên snapshot đã công bố và cùng filter scope. Không chạy nhiều truy vấn mà mỗi truy vấn tự chọn latest batch. Mỗi kết quả trả kèm metric_id, source_batch_id, data_as_of, quality_status và missing_reason.

| Nhóm | Phép tổng hợp và điều kiện | Điều cần tránh |
|---|---|---|
| B01 | F03 đêm thực ở; F02 availability; tỷ lệ từ tổng. F01 hủy/no-show theo arrival cohort. | Không dùng kênh/khách lọc capacity chưa phân bổ; không xóa ngày không khách. |
| B02 | F01 COMPLETED theo departure. Tiền giữ lại=gross-company_share-commission. | Không cộng revision/payment, không gọi lợi nhuận/ROI. |
| B03 | Cohort F01 COMPLETED theo departure; aggregate F04 net và F05 COMPLETED riêng về booking. COUNTD booking mua vé net>0 hoặc rental agreed>0. | Không fan-out; không đếm booking mua hai dịch vụ hai lần; tiền gồm phòng+vé+xe đúng tên chỉ tiêu. |
| B04 | F06/F07/F08 tổng riêng theo outlet/service_date/meal. Ratio từ tổng; rating_sum/rating_count. | Không cộng actual_covers lần ba, không tạo doanh thu included breakfast. |
| B05 | F09 admission_date và F10 capacity; F11 rented/available. Weather chỉ join site/day sau xác minh uniqueness. | Không gộp tỷ lệ hoạt động và xe; không coi admission là người duy nhất hoặc lấy ngày bán thay ngày vào. |
| B06 | F12 expected_on trong kỳ và <=A; F13 received_on<=A aggregate theo purchase_line rồi LEFT JOIN. A mặc định 2025-12-31. | Không mất dòng chưa giao; không COALESCE receipt bị lỗi thành 0; không cộng khác base_unit. |
| B07 | Q0=sum signed trước S; Q1=sum signed trước E; U/W trong kỳ. Waste ratio=value waste/(opening value+IN value). | Không lọc bỏ lịch sử trước S, không SUM closing qua ngày, không dùng usage_area lọc tồn. |
| B08 | F16 cost COMPLETED theo ends_on. F02 blocked/available; nguyên nhân riêng qua L02 rồi DISTINCT room/day. | Không nhân cost theo ngày và không để slicer work_type bỏ các nguyên nhân chặn khác khỏi availability. |

Quality phải được lan theo đường sử dụng thực tế: B03 cần F01/F04/F05; B01 công suất cần cả F02/F03; B06 tỷ lệ cần F12/F13; B07 số dư cần lịch sử ledger đầy đủ. F17 chỉ ảnh hưởng B05 khi dùng bộ lọc/phân tích weather. Đối soát feed ngoài có cảnh báo riêng, không mặc định làm lượng nhận DB không hợp lệ.

## Danh mục lỗi và phần dữ liệu thiếu

| Mã | Điều kiện | Xử lý | Ảnh hưởng |
|---|---|---|---|
| INPUT_UNAVAILABLE | Nguồn thiếu toàn bảng/file hoặc sai checksum | Nguồn không được coi là rỗng; expected_count có thể NULL. | Mọi KPI phụ thuộc nguồn theo scope biết được. |
| INVALID_VALUE | Parse, length, precision, miền giá trị hoặc số bắt buộc NULL | Quarantine bản ghi, giữ nguyên payload; không cắt/điền 0. | KPI dùng giá trị đó và dependency phía sau. |
| DUPLICATE_ID_CONFLICT | Một PK nhiều payload | Quarantine cả nhóm; không last-wins tùy ý. | Phạm vi của toàn nhóm, không chọn một dòng làm đại diện. |
| MISSING_PARENT | FK có giá trị nhưng không có parent hợp lệ | Dependency_excluded; FK optional chỉ được special khi giá trị nguồn NULL. | Fact/link con và KPI sử dụng. |
| AMBIGUOUS_PARENT | Parent match nhiều dòng hoặc nhiều SCD interval | Loại child; sửa parent trước khi retry. | Không SUM dữ liệu đã bị fan-out. |
| SCD_INTERVAL_CONFLICT | Trùng effective time khác payload hoặc interval overlap | Cách ly BK/interval; các phiên bản không liên quan có thể còn hợp lệ. | Fact thuộc khoảng hiệu lực bị ảnh hưởng. |
| RESOURCE_OVERLAP | Hai stay/rental cùng resource/day | Loại mọi dòng conflict scope; giữ các ngày không xung đột nếu kiểm chứng được. | B01/B05 theo room hoặc vehicle/day; tiền rental liên quan gắn lỗi F05. |
| SERVICE_WHILE_CLOSED | Stay/xe trong bảo trì hoặc admission lúc đóng | Loại nhóm sử dụng trái điều kiện; không xóa bản ghi đóng cửa để hợp thức hóa. | Tử số thiếu; capacity độc lập vẫn có thể hợp lệ, tỷ lệ PARTIAL. |
| CAPACITY_EXCEEDED | Admission hợp lệ sơ bộ vượt capacity đã xác minh | Quarantine nhóm activity/day; không kẹp bằng capacity hoặc lấy N dòng đầu. | B05.01/03; số lượt bị loại được công bố. |
| OUTLET_MAPPING_AMBIGUOUS | Entitlement không có đúng một nhà hàng hiệu lực | Loại entitlement khỏi F06, giữ lỗi để bổ sung mapping. | B04 quyền lợi và lượt phục vụ; không tạo suất ở outlet ngẫu nhiên. |
| INCOMPLETE_LEDGER | Thiếu movement, balance âm hoặc USE trước IN | Không công bố số dư lot/day từ mốc không tin cậy; giữ movement độc lập còn đúng. | B07 số dư/giá trị và F15; quantity bị thiếu không là 0. |
| RECONCILIATION_MISMATCH | DB receipt và feed latest không khớp | Giữ DB làm nguồn KPI; ghi mismatch và độ đầy đủ feed. | Nhãn đối soát; không tự đổi công thức lượng nhận chuẩn. |
| REPLAY | Cùng identity, payload, có bằng chứng giao lại | Ghi discarded_replay, chỉ một sự kiện có đóng góp. | Không giảm completeness nghiệp vụ vì bản sao transport. |

**Ví dụ hiển thị báo cáo:** “Doanh thu trên phần dữ liệu hợp lệ — PARTIAL. Đã xử lý 980/1.000 booking; loại 20 dòng do sai tham chiếu khách sạn. Cập nhật theo batch …; chưa bao gồm các giao dịch bị loại.” Nếu chỉ biết nguồn thiếu mà chưa biết số dòng, ghi “Chưa xác định mức đầy đủ”, không hiển thị tỷ lệ coverage giả.

**Nguồn lỗi và KPI:** số lượng quarantine theo bảng nguồn không được cộng cơ học qua bảng đích vì một booking lỗi có thể làm nhiều stay-night bị loại. Báo cáo chất lượng lưu cả source_record identity và affected target grain, đồng thời tách direct error với dependency exclusion.

## Ví dụ kiểm tra tham chiếu

Các kết quả sau đã được tính bằng Python độc lập ở mức quy tắc tham chiếu. Chúng giúp chốt kỳ vọng để viết fixture ETL; chưa phải bằng chứng các biểu thức Oracle/Spark hoặc cơ chế SCD2 triển khai thật đã chạy đúng.

| Mã | Tình huống | Kết quả kỳ vọng |
|---|---|---|
| E01 | Khoảng lưu trú loại ngày trả phòng | `["2024-01-30", "2024-01-31", "2024-02-01"]` |
| E02 | Timestamp UTC sang ngày Việt Nam | `"2024-01-02"` |
| E03 | Union bảo trì không nhân room-day | `{"blocked": 3, "inventory": 6, "available": 3}` |
| E04 | Ranh giới SCD chọn phiên bản mới | `[102]` |
| E05 | SCD A rồi B rồi A cần ba identity | `3` |
| E06 | Replay cùng BK và effective time không thêm identity | `1` |
| E07 | Không fan-out tiền booking | `2700000` |
| E08 | Tỷ lệ từ tổng thay vì trung bình tỷ lệ phiên | `"60000"` |
| E09 | Covers không cộng phiên lần ba | `5` |
| E10 | B06 giao nhiều đợt | `{"O": 10, "G": 9, "R": 1, "L": 3, "T": 6, "otif": 0}` |
| E11 | Tồn theo lô và giá trị hao hụt | `{"closing": 2, "waste_value": 20000}` |
| E12 | Không cộng tồn cuối qua hai ngày | `1` |
| E13 | Đơn vị feed g sang kg | `"1.5"` |
| E14 | PARTIAL còn 980 trên 1000 | `{"accepted": 980, "status": "PARTIAL"}` |
| E15 | Mẫu số 0 không gán 0 phần trăm | `null` |
| E16 | Tử số thiếu không cho tỷ lệ COMPLETE | `"PARTIAL"` |
| E17 | Thiếu toàn nguồn không phải số 0 | `"UNAVAILABLE"` |
| E18 | Nhận 01/01 trả 03/01: quyền lợi sáng 02/01 và 03/01, gồm ngày checkout | `["2024-01-02", "2024-01-03"]` |

Khi triển khai phải bổ sung fixture tích hợp: SCD unchanged/change/A->B->A/late correction và transaction close-open; source thiếu toàn file; FK invalid so với optional NULL; outlet mapping 0/2; over-capacity; room/rental overlap; receipt replay và latest-invalid; ledger thiếu IN; correction interval xóa ngày cũ. Mỗi fixture chạy qua cả hai nhánh và so kết quả cùng quality status, không chỉ so tổng tiền.

## Đầu ra và kiểm chứng

Kiểm tra đặc tả đã đạt: 37 entity, 631 cột đích, 102 vai trò FK fact-dimension, 17 nhóm quy tắc, toàn bộ 41 bảng nguồn được phân loại vai trò, 18 ví dụ tham chiếu. DAG load không có chu kỳ; tham chiếu cột và hash đầu vào được kiểm tra.

Kiểm tra đọc trực tiếp nguồn cho ranh giới buffet sáng: 52979 entitlement, không có dòng vi phạm checkin < service_date <= checkout; trong đó 22183 dòng phục vụ đúng sáng checkout. Điều này xác nhận không dùng điều kiện ngày đêm ở để loại suất sáng checkout.

Biểu thức là pseudocode; chưa tạo bảng Oracle/Iceberg hoặc thực thi ETL phân tích. Chưa có nghiệm thu end-to-end, benchmark hoặc kiểm thử xử lý lỗi trên engine. Mapping JSON lưu đầy đủ cột, nguồn, biểu thức, rule IDs, các phụ thuộc và catalog path để dùng ở bước triển khai.

Chạy lại từ Project:

```powershell
python -X utf8 scripts/build-source-target-mapping.py
```

Đầu ra: `config/source_target_mapping_v1.json`, `docs/CompanyE_Source_Target_Mapping.md`, `reports/source_target_mapping_v1_validation.json`, `reports/source_target_mapping_reference_examples.json`. Script không sửa source DB, dữ liệu sinh, seed, lake hoặc design contract.
