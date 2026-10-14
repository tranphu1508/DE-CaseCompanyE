# Đặc tả chi tiết mô hình kho dữ liệu CompanyE

Phiên bản 1.1, ngày 13/10/2026. Thiết kế cột và quy tắc dùng chung cho Oracle warehouse và Spark Iceberg lakehouse trên nguồn v2. Hai quyết định đã chốt: SCD Type 2 và công bố phần dữ liệu hợp lệ kèm cảnh báo thiếu. Đây là đầu ra bước 1; chưa tạo bảng đích hoặc chạy ETL.

Mô hình giữ nguyên 16 dimension, 17 fact gồm một aggregate tùy chọn và một fact thời tiết, cùng bốn bảng liên kết hoặc view kiểm chứng. Các bảng phục vụ 47 KPI B01–B08 đã chốt. Các mục dưới đây đủ để chuẩn bị mapping và DDL; cấu hình engine, partition, index và connector được chốt ở bước môi trường.

## Quyết định nghiệp vụ

| Mã | Nội dung | Trạng thái | Quyết định hoặc mặc định đề xuất |
|---|---|---|---|
| Q01 | Lịch sử dimension | USER_CONFIRMED | Dùng SCD Type 2 để sẵn sàng cho thay đổi trong thực tế. Nguồn v2 giản lược không có lịch sử thay đổi nên mỗi business key chỉ có phiên bản đầu tiên, gắn giả định khởi tạo rõ ràng; không cần sinh thêm dữ liệu nghiệp vụ. |
| Q02 | Công bố batch có lỗi | USER_CONFIRMED | Vẫn xuất report từ phần dữ liệu hợp lệ khi có lỗi dữ liệu; hiển thị trạng thái thiếu, phạm vi và số lượng bị loại, thời điểm cập nhật và ảnh hưởng tới KPI. Không giả missing thành 0 hoặc tự trộn batch cũ với mới. |

Hai quyết định trên đã được người dùng chốt ngày 13/10/2026 và thay thế đề xuất Type 1 cùng chính sách chặn công bố của bản nháp. Không cần sinh thêm lịch sử vào v2.

### Cách hiểu lịch sử dimension

Ví dụ minh họa, chưa phải sự kiện trong v2: phòng P101 là Standard trong năm 2024 và được nâng cấp thành Deluxe từ 01/07/2025. Type 1 cập nhật một dòng danh mục thành Deluxe, nên các đêm ở cũ cũng được phân loại theo tên loại phòng hiện hành. Type 2 giữ hai phiên bản, mỗi phiên bản có khóa và khoảng hiệu lực riêng; đêm ở năm 2024 nối phiên bản Standard, đêm ở sau nâng cấp nối Deluxe.

CompanyE chọn Type 2 vì trong thực tế các thuộc tính danh mục có thể thay đổi và cần phân tích giao dịch theo phiên bản đúng thời điểm. Dữ liệu tự sinh v2 được giản lược để tập trung vào data engineering: mỗi business key hiện chỉ có phiên bản đầu, không cần tạo sự kiện thay đổi giả. Thiết kế vẫn có đủ khoảng hiệu lực, khóa phiên bản và quy tắc cập nhật; chưa có thay đổi trong dữ liệu không có nghĩa cơ chế lưu phiên bản bị bỏ đi. Khi hiện thực, fixture SCD2 nhỏ tách riêng sẽ kiểm tra cơ chế này.

### Cách hiểu công bố batch

Batch là một đợt xử lý dữ liệu. Ví dụ đợt mới có 1.000 booking nhưng 20 dòng lỗi: công bố phần hợp lệ của 980 booking và gắn trạng thái PARTIAL. Báo cáo ghi Đã xử lý 980/1.000 booking, loại 20 dòng; các giá trị liên quan chỉ phản ánh phần hợp lệ. Nếu một dòng booking lỗi kéo theo stay hoặc dịch vụ không còn đủ tham chiếu, số dòng phụ thuộc bị loại cũng được ghi riêng.

Cảnh báo đi tới từng KPI chịu ảnh hưởng, gồm kỳ/cơ sở khi xác định được. Không đủ tử hoặc mẫu để tính thì hiển thị Không đủ dữ liệu; tỷ lệ tính trên phần hợp lệ vẫn có nhãn thiếu, không coi là tỷ lệ đầy đủ của doanh nghiệp. Không tự bù số từ batch cũ. Lỗi raw đã được cách ly đúng kế hoạch được phân loại riêng với lỗi làm thiếu dữ liệu phân tích.

## Quy ước thiết kế

**Kiến trúc**: Fact constellation, star per fact; thuộc tính hotel_id/site_id trong dimension không trở thành FK dimension-to-dimension.

**Thời gian**: Ngày nghiệp vụ Asia/Ho_Chi_Minh; timestamp UTC ở cột _utc; mọi khoảng công suất/lưu trú [S,E).

**Kỳ tính công suất**: 2024-01-01 đến trước 2026-01-01. Danh mục phòng/hoạt động/xe tồn tại toàn kỳ mô phỏng. Không mở công suất từ ngày booked_on năm 2023.

**Phạm vi lịch ngày**: Lấy min/max của TẤT CẢ cột DATE và ngày địa phương của TIMESTAMPTZ trong hai DB v2; thêm ngày trước capacity start cho số dư đầu kỳ. Sinh liên tục từ 01/01 năm min tới 31/12 năm max; không sinh holiday/season khi chưa có rule version.

**Thành viên đặc biệt**: Mỗi dimension có key 0 UNKNOWN và -1 NOT_APPLICABLE; source_system=system; member_kind riêng; các thuộc tính NULL. Nhãn UI lấy từ member_kind hoặc theo vai trò (ví dụ Không khuyến mãi). Không tạo ngày giả 1900.

**Ràng buộc dimension**: SCD2: PK là SK của phiên bản; UK NORMAL=(namespace,BK,valid_from) và (namespace,BK,version_no); UK có điều kiện cho BK với is_current=1. Oracle dùng unique index có CASE để loại dòng đặc biệt; Iceberg kiểm tra cùng quy tắc trước công bố. Kiểm tra nonoverlap riêng. D01/DimDate và D10/DimMeal giữ danh mục STATIC. Không đặt UNIQUE BK trên toàn bộ lịch sử.

**Tham chiếu không hợp lệ**: NULL được xử lý theo từng cột; ID có giá trị nhưng không tìm thấy hoặc mâu thuẫn -> quarantine. Không đổi invalid reference thành 0/-1 để che lỗi.

**Số đo bị thiếu**: Không tự NULL->0 cho tiền/lượng bắt buộc. 0 chỉ từ phép tính có ý nghĩa (không có closure, không USE), sau kiểm tra đủ dữ liệu.

**Chuỗi rỗng và giá trị NULL**: CSV nguồn dùng token \N cho SQL NULL: giải mã ở ranh giới đọc CSV, không giữ thành chuỗi mã hoặc ngày. Đồng nhất chuỗi rỗng thành NULL trước cả hai nhánh; giữ nguyên nội dung mã nguồn khác rỗng. Whitespace-only trong mã bắt buộc -> lỗi. Không dùng sentinel rỗng cho BK.

**Cấp và giữ khóa**: Registry dùng chung hai nhánh. Với SCD2, canonical key gồm entity_id, namespace, BK và valid_from_utc; mỗi phiên bản có SK riêng, không dùng row_hash vì thuộc tính có thể đổi A->B->A. Với fact, khóa tự nhiên dùng ID nguồn bền vững và ngày để không nhân bản grain khi dimension đổi phiên bản. Registry append-only, không tái đánh số. Date YYYYMMDD; Meal 1..4 cố định.

**Chuẩn hóa trước khi tính hash**: SHA256 của payload nghiệp vụ canonical theo thứ tự cột; loại SK, audit và năm cột điều khiển SCD. Dimension hash chỉ tracked_attributes, NULL phân biệt giá trị; fact dùng BK của reference thay SK. Date ISO, timestamp UTC microseconds, decimal chuỗi fixed-scale. Hash không đổi thì không tạo version mới; cùng batch và effective time chạy lại idempotent.

**Lịch sử dữ liệu**: 14 dimension nghiệp vụ dùng SCD Type 2; DimDate và DimMeal STATIC. V2 chưa có sự kiện đổi danh mục nên mỗi BK chỉ có version_no=1, is_current=1; không sinh thêm dữ liệu. Cột effective_time_basis phân biệt giả định khởi tạo, hiệu lực từ nguồn và thời điểm quan sát. Fact vẫn lưu trạng thái cuối snapshot theo KPI contract; SCD2 dimension không biến fact thành event history.

**Điều kiện mở rộng SCD2**: Bootstrap v2 giả định danh mục hiện hành áp dụng từ 2023-01-01 00:00 Asia/Ho_Chi_Minh (2022-12-31T17:00:00 UTC), valid_to=NULL, basis=BOOTSTRAP_ASSUMPTION; đây là giả định mô phỏng, không phải lịch sử nguồn. Dữ liệu trước mốc này phải được kiểm tra lại, không tự mở rộng. Batch sau dùng effective time đáng tin nếu có; không có thì dùng observed_at của snapshot trong manifest, basis=OBSERVED_AT, không lùi về ngày giao dịch. Đổi thuộc tính đóng/mở version; sự kiện đến muộn cần split interval, kiểm tra nonoverlap và rekey fact bị ảnh hưởng trong cùng candidate. Ngày-only được hiểu đầu ngày địa phương; thay đổi giữa ngày chưa đủ độ phân giải để phục hồi phân loại chính xác.

**Bản ghi biến mất và xóa dữ liệu**: Không suy hard delete từ file thiếu. Full snapshot phải có manifest đầy đủ; dựng candidate snapshot mới, so sánh thay đổi và xác nhận counts. Incremental cần tombstone/CDC rõ ràng. Giữ registry và audit; không xóa nguồn.

**Dữ liệu đến muộn và sửa đổi**: Giữ SK cũ cho fact thuộc phiên bản cũ; không rekey toàn lịch sử sang current. Khi sửa lịch sử có bằng chứng thì lookup as-of và tính lại fact/bridge đúng phạm vi thời gian; sửa movement cũ tính lại tồn từ ngày sửa. Dòng không lookup được parent/version bị quarantine và báo thiếu; batch sau khôi phục theo durable natural key, không nhân đôi giao dịch.

**Quy tắc tổng hợp**: Không có tỷ lệ materialized; tính ratio bằng tổng tử/mẫu, mẫu 0 trả NULL/BLANK. SUM tiền ở grain gốc; lượng SUM trong cùng base_unit; F15 số dư chỉ snapshot cùng ngày; weather không cộng khác site; các fact được aggregate riêng trước drill-across.

**Cấu hình vật lý ban đầu**: Oracle PK/UK/FK và CHECK khi biểu diễn được; Iceberg kiểm tra tương đương bằng pipeline trước publish, không coi identifier fields là PK enforcement. Khởi đầu bảng không partition ở cả hai nhánh; đề xuất partition/index chỉ sau chốt phiên bản và đo workload. Không bật nén/parallel/partition phụ thuộc edition trước kiểm chứng môi trường.

**Tên vật lý**: Tên bảng và cột lowercase snake_case, không quoted mixed-case identifiers. FactBooking -> fact_booking, DimCustomerProfile -> dim_customer_profile. Chọn schema/catalog riêng ở bước môi trường; tên entity trong sơ đồ là tên logic.

**Công bố dữ liệu**: USER_CONFIRMED: công bố tập hợp lệ với trạng thái COMPLETE hoặc PARTIAL. Dòng lỗi quarantine và loại cả dòng phụ thuộc không đủ điều kiện; không giữ tiền nhưng bỏ dimension sai để che lỗi. Mỗi report/visual có thời điểm nguồn, batch, trạng thái thiếu, số dòng bị loại và KPI/phạm vi ảnh hưởng. UNKNOWN amount không điền 0. Tỷ lệ tính trên tập hợp lệ phải gắn PARTIAL nếu tử hoặc mẫu bị ảnh hưởng; không tính được thì NULL và ghi Không đủ dữ liệu. Không tự trộn dữ liệu cũ với mới.

**Tính nhất quán giữa các bảng**: PARTIAL vẫn phải nhất quán: các bảng hợp lệ được chốt theo cùng batch/cutoff; metadata chất lượng công bố cùng dữ liệu. Dùng publication manifest trỏ phiên bản của từng bảng, không coi nhiều commit Iceberg là transaction chung. Lỗi engine/ghi dữ liệu/cutoff không xác định thì batch FAILED vì không có tập hợp lệ tin cậy để công bố; giao diện vẫn hiển thị trạng thái nguồn thiếu hoặc bản trước với nhãn ngày cũ rõ ràng.

**Phạm vi triển khai**: 16 dimension, 16 fact/context bắt buộc + F15 aggregate tùy chọn, 2 bridge + 2 validation views. Chưa thêm fact membership/payment/menu/revision; các nguồn đó giữ ở lake để đối soát. Không đưa audit_only vào analytic contract.

**Độ đầy đủ và phạm vi ảnh hưởng**: Lưu input_count, accepted_count, quarantined_count, dependency_excluded_count theo entity/batch, các nhóm không chồng; discarded duplicate/replay và not_applicable riêng để không gọi lọc nghiệp vụ là lỗi. Tính completeness khi có expected count đáng tin; thiếu toàn file không biết số dòng -> UNKNOWN, không 0% hoặc 100% giả. Dùng phạm vi ngày/site/metric nếu nhận diện được; không biết scope thì cảnh báo toàn KPI phụ thuộc nguồn đó.

**Đánh giá hai giải pháp**: So sánh warehouse/lakehouse trên cùng input, accepted set, quarantine/exclusion set và quality status. Bộ số liệu sạch kiểm tra KPI chuẩn; fixture lỗi kiểm tra báo cáo PARTIAL và cảnh báo chính xác. Cần fixture nhỏ SCD2 cho đổi thuộc tính, không đổi, replay, ranh giới hiệu lực, A->B->A và late correction; fixture tách khỏi seed v2. V2 chỉ một version không đủ chứng minh ETL SCD2 đã chạy đúng.

**Nối và tổng hợp khi có nhiều phiên bản**: SCD SK là phiên bản, không phải định danh đối tượng xuyên thời gian. Join giữa fact/aggregate dùng namespace+BK bền vững theo grain đã chốt, aggregate riêng rồi nối. B06 gắn receipt về purchase_line và dùng phân loại dimension của dòng đặt mua cho cohort; B07 đối chiếu lô theo receipt_id/hotel_id/item_id. Không để cùng supplier hoặc room có hai SK bị coi là hai đối tượng nghiệp vụ. View current và view as-of phải đặt nhãn rõ; mặc định dùng vai trò as-of từng fact dưới đây.

Kiểm tra trực tiếp nguồn v2: ngày nhỏ nhất 2023-10-03, lớn nhất 2026-06-28. DimDate cần phủ 2023-01-01 đến 2026-12-31; lịch công suất vẫn chỉ trong kỳ mô phỏng.

## Kiểu dữ liệu và tính tương đương

| Kiểu chung | Oracle dự kiến | Iceberg | Quy tắc |
|---|---|---|---|
| KEY | `NUMBER(18,0)` | `long` | Khóa dương <= 999999999999999999; dành 0 và -1 cho dimension. |
| DATEKEY | `NUMBER(8,0)` | `int` | YYYYMMDD; 0 và -1 là thành viên đặc biệt. |
| COUNT | `NUMBER(18,0)` | `long` | Số nguyên không âm. |
| INT | `NUMBER(10,0)` | `int` | Số nguyên trong miền signed 32-bit. |
| FLAG | `NUMBER(1,0)` | `int` | 0 hoặc 1; không dùng BOOLEAN để giảm khác biệt driver. |
| MONEY | `NUMBER(19,0)` | `decimal(19,0)` | VND nguyên; không dùng float. |
| QTY | `NUMBER(18,3)` | `decimal(18,3)` | Lượng theo đơn vị cơ sở; không làm tròn âm thầm. |
| VALUE | `NUMBER(38,3)` | `decimal(38,3)` | Lượng nhân đơn giá, giữ 3 số lẻ đến lớp hiển thị. |
| DATE | `DATE` | `date` | Oracle DATE phải có giờ 00:00:00. |
| UTC | `TIMESTAMP(6)` | `timestamp` | Giá trị UTC không timezone; tên cột kết thúc _utc, session UTC. |
| ID | `VARCHAR2(128 CHAR)` | `string` | Mã nguồn giữ nguyên hoa/thường; không cắt hoặc chuẩn hóa tùy tiện. |
| CODE | `VARCHAR2(64 CHAR)` | `string` | Mã phân loại có danh mục kiểm soát. |
| TEXT | `VARCHAR2(512 CHAR)` | `string` | Unicode; Oracle dùng AL32UTF8. |
| HASH | `VARCHAR2(64 CHAR)` | `string` | SHA256 hex chữ thường, đúng 64 ký tự. |

Oracle và Iceberg có kiểu decimal chính xác; giới hạn chuỗi và miền số được kiểm tra chung trước nạp. Thiết kế timestamp lưu giá trị UTC, chuyển sang giờ Việt Nam trước khi lấy ngày nghiệp vụ. Kiểu DATE của Oracle phải bị giới hạn phần giờ về nửa đêm. Tham khảo [Oracle Data Types](https://docs.oracle.com/en/database/oracle/oracle-database/21/sqlqr/Data-Types.html) và [Iceberg Schemas](https://iceberg.apache.org/docs/latest/schemas/).

Iceberg identifier fields không bảo đảm tính duy nhất. PK, UK, quan hệ tham chiếu và kiểm tra grain vẫn cần kiểm tra bằng pipeline trước công bố. Xem [Iceberg specification](https://iceberg.apache.org/spec/).

## Cột kiểm toán dùng chung

| Cột | Kiểu | NULL | Ý nghĩa |
|---|---|---|---|
| `source_batch_id` | ID | Không | Batch của dữ liệu nguồn dùng tạo hoặc cập nhật dòng. |
| `transform_version` | CODE | Không | Phiên bản biến đổi, trỏ tới mã và cấu hình trong manifest. |
| `row_hash` | HASH | Không | Hash payload nghiệp vụ theo quy tắc canonical; loại khóa kỹ thuật và các cột audit. |
| `created_at_utc` | UTC | Không | Thời điểm tạo dòng đích; không phải ngày hiệu lực nghiệp vụ. |
| `updated_at_utc` | UTC | Không | Thời điểm cập nhật dòng đích gần nhất. |

Năm cột này có trong hợp đồng của mọi entity; các view liên kết chiếu metadata từ input cùng batch. Không cộng metadata vào row_hash. Dòng không đổi có thể giữ source_batch_id cũ; publication manifest xác định phiên bản toàn bộ tập công bố.

## Danh mục bảng và khóa

| Mã | Bảng hoặc view | Loại | Grain | Khóa duy nhất nghiệp vụ |
|---|---|---|---|
| D01 | DimDate | DIMENSION | Một thành viên hiện hành cho mỗi business key trong namespace. | calendar_date |
| D02 | DimSite | DIMENSION | Một phiên bản có hiệu lực của một business key trong namespace nguồn. | source_system, site_id, valid_from_utc; source_system, site_id, version_no |
| D03 | DimHotel | DIMENSION | Một phiên bản có hiệu lực của một business key trong namespace nguồn. | source_system, hotel_id, valid_from_utc; source_system, hotel_id, version_no |
| D04 | DimRoom | DIMENSION | Một phiên bản có hiệu lực của một business key trong namespace nguồn. | source_system, room_id, valid_from_utc; source_system, room_id, version_no |
| D05 | DimChannel | DIMENSION | Một phiên bản có hiệu lực của một business key trong namespace nguồn. | source_system, channel_code, valid_from_utc; source_system, channel_code, version_no |
| D06 | DimPromotion | DIMENSION | Một phiên bản có hiệu lực của một business key trong namespace nguồn. | source_system, promotion_id, valid_from_utc; source_system, promotion_id, version_no |
| D07 | DimCustomerProfile | DIMENSION | Một phiên bản có hiệu lực của một business key trong namespace nguồn. | source_system, source_customer_id, valid_from_utc; source_system, source_customer_id, version_no |
| D08 | DimRatePlan | DIMENSION | Một phiên bản có hiệu lực của một business key trong namespace nguồn. | source_system, rate_plan_id, valid_from_utc; source_system, rate_plan_id, version_no |
| D09 | DimOutlet | DIMENSION | Một phiên bản có hiệu lực của một business key trong namespace nguồn. | source_system, outlet_id, valid_from_utc; source_system, outlet_id, version_no |
| D10 | DimMeal | DIMENSION | Một thành viên hiện hành cho mỗi business key trong namespace. | meal_code |
| D11 | DimCentre | DIMENSION | Một phiên bản có hiệu lực của một business key trong namespace nguồn. | source_system, centre_id, valid_from_utc; source_system, centre_id, version_no |
| D12 | DimActivity | DIMENSION | Một phiên bản có hiệu lực của một business key trong namespace nguồn. | source_system, activity_id, valid_from_utc; source_system, activity_id, version_no |
| D13 | DimVehicle | DIMENSION | Một phiên bản có hiệu lực của một business key trong namespace nguồn. | source_system, vehicle_id, valid_from_utc; source_system, vehicle_id, version_no |
| D14 | DimSupplier | DIMENSION | Một phiên bản có hiệu lực của một business key trong namespace nguồn. | source_system, supplier_id, valid_from_utc; source_system, supplier_id, version_no |
| D15 | DimItem | DIMENSION | Một phiên bản có hiệu lực của một business key trong namespace nguồn. | source_system, item_id, valid_from_utc; source_system, item_id, version_no |
| D16 | DimAsset | DIMENSION | Một phiên bản có hiệu lực của một business key trong namespace nguồn. | source_system, asset_id, valid_from_utc; source_system, asset_id, version_no |
| F01 | FactBooking | CURRENT_TRANSACTION | Một booking ở trạng thái cuối của batch. | source_system, booking_id |
| F02 | FactRoomDay | PERIODIC_SNAPSHOT | Một phòng và một ngày danh mục. | source_system, room_id, date_key |
| F03 | FactStayNight | EXPANDED_EVENT | Một phòng và một đêm thực ở hợp lệ. | source_system, room_id, service_date_key |
| F04 | FactTicketOrder | CURRENT_TRANSACTION | Một đơn vé. | source_system, ticket_order_id |
| F05 | FactRental | CURRENT_TRANSACTION | Một hợp đồng thuê một xe. | source_system, rental_id |
| F06 | FactBreakfastEntitlement | TRANSACTION | Một quyền lợi phòng và ngày phục vụ. | source_system, entitlement_id; source_system, booking_room_id, service_date_key |
| F07 | FactDiningOrder | TRANSACTION | Một hóa đơn ăn uống, không phải dòng món. | source_system, dining_order_id |
| F08 | FactMealSession | PERIODIC_SNAPSHOT | Một outlet, ngày và bữa buffet. | source_system, outlet_id, service_date_key, meal_key; source_system, session_id |
| F09 | FactAdmission | TRANSACTION | Một lượt admission thực tế. | source_system, admission_id |
| F10 | FactActivityDay | PERIODIC_SNAPSHOT | Một hoạt động và ngày danh mục. | source_system, activity_id, date_key |
| F11 | FactVehicleDay | PERIODIC_SNAPSHOT | Một xe và ngày danh mục. | source_system, vehicle_id, date_key |
| F12 | FactPurchaseLine | TRANSACTION | Một dòng đặt mua. | source_system, purchase_line_id |
| F13 | FactReceipt | TRANSACTION | Một lần nhận của một dòng đặt mua. | source_system, receipt_id |
| F14 | FactStockMovement | TRANSACTION | Một chuyển động của một lô tại khách sạn. | source_system, movement_id |
| F15 | AggInventoryLotDay | OPTIONAL_AGGREGATE | Một lô, khách sạn, mặt hàng và ngày cuối ngày. | source_system, receipt_id, hotel_id, item_id, snapshot_date_key |
| F16 | FactMaintenanceWork | CURRENT_TRANSACTION | Một công việc bảo trì tài sản khách sạn. | source_system, maintenance_id |
| F17 | FactWeatherDay | CONTEXT | Một cụm và ngày thời tiết. | source_system, site_id, weather_date_key; source_system, weather_id |
| L01 | BridgeBookingRoom | BRIDGE | Một booking_room_id trong hotel_ops. | source_system, booking_room_id |
| L02 | BridgeRoomDayMaintenance | BRIDGE | Một phòng/ngày/công việc bảo trì. | source_system, room_id, date_key, maintenance_id |
| L03 | ValidatedBookingServiceLink | VALIDATION_VIEW | Một service_type/service_id có booking_ref hợp lệ. | service_source_system, service_type, service_id |
| L04 | SiteCrosswalk | VALIDATION_VIEW | Một centre ánh xạ đúng một site. | centre_source_system, centre_id |

## Từ điển cột theo từng bảng

NULL thể hiện khả năng lưu NULL vật lý. Đối với dimension, cột đánh dấu “bắt buộc NORMAL” phải có giá trị trên thành viên thật; chỉ hai dòng 0 và -1 được bỏ trống. Với SCD2, BK có thể lặp qua các phiên bản; duy nhất theo BK cùng valid_from hoặc version_no, và tối đa một current cho mỗi BK. Thuộc tính ID bên trong dimension là thuộc tính nguồn, không phải FK sang dimension khác.

### D01 DimDate

**Tên vật lý:** `dim_date`. **Grain:** Một thành viên hiện hành cho mỗi business key trong namespace.

**PK:** `date_key`. **UK:** `calendar_date`.

**Lịch sử:** STATIC. Upsert theo BK và registry; cập nhật khi row_hash thay đổi; không tự xóa thành viên vắng mặt.

| Cột | Kiểu | NULL | Vai trò và quy tắc | Cách tổng hợp |
|---|---|---|---|---|
| `date_key` | DATEKEY | Không | Khóa dimension dùng chung hai nhánh. | NONE |
| `source_system` | CODE | Không | Namespace nguồn; calendar/reference cho danh mục sinh. | NONE |
| `member_kind` | CODE | Không | NORMAL, UNKNOWN hoặc NOT_APPLICABLE. | NONE |
| `calendar_date` | DATE | Có | Ngày lịch Gregorian. Bắt buộc NORMAL. | NONE |
| `day` | INT | Có | Thuộc tính lịch sinh xác định. Bắt buộc NORMAL. | NONE |
| `day_of_week` | INT | Có | Thuộc tính lịch sinh xác định. Bắt buộc NORMAL. | NONE |
| `month` | INT | Có | Thuộc tính lịch sinh xác định. Bắt buộc NORMAL. | NONE |
| `quarter` | INT | Có | Thuộc tính lịch sinh xác định. Bắt buộc NORMAL. | NONE |
| `year` | INT | Có | Thuộc tính lịch sinh xác định. Bắt buộc NORMAL. | NONE |

Năm cột kiểm toán dùng chung được bổ sung theo mục trên.

**Ràng buộc và cách sử dụng:**

- calendar_date duy nhất trên dòng NORMAL; date_key=YYYYMMDD.
- day_of_week: Monday=1..Sunday=7; quarter=1..4; year/month/day lấy từ calendar_date.

### D02 DimSite

**Tên vật lý:** `dim_site`. **Grain:** Một phiên bản có hiệu lực của một business key trong namespace nguồn.

**PK:** `site_key`. **UK:** `source_system, site_id, valid_from_utc`; `source_system, site_id, version_no`.

**Lịch sử:** SCD_TYPE2. Không đổi payload thì giữ SK; đổi thuộc tính theo dõi tại t thì đóng phiên bản cũ valid_to=t, is_current=0; thêm phiên bản mới có SK mới, valid_from=t, valid_to=NULL, is_current=1. Cùng batch replay không sinh thêm phiên bản.

| Cột | Kiểu | NULL | Vai trò và quy tắc | Cách tổng hợp |
|---|---|---|---|---|
| `site_key` | KEY | Không | Khóa dimension dùng chung hai nhánh. | NONE |
| `source_system` | CODE | Không | Namespace nguồn; calendar/reference cho danh mục sinh. | NONE |
| `member_kind` | CODE | Không | NORMAL, UNKNOWN hoặc NOT_APPLICABLE. | NONE |
| `site_id` | ID | Có | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Bắt buộc NORMAL. Nguồn: `hotel_ops.sites.site_id`. | NONE |
| `site_name` | TEXT | Có | Tên địa điểm. Bắt buộc NORMAL. Nguồn: `hotel_ops.sites.site_name`. | NONE |
| `climate_region` | TEXT | Có | Nhóm khí hậu giả định. Bắt buộc NORMAL. Nguồn: `hotel_ops.sites.climate_region`. | NONE |
| `valid_from_utc` | UTC | Không | Bắt đầu hiệu lực phiên bản, inclusive; mốc bootstrap v2 theo giả định. | NONE |
| `valid_to_utc` | UTC | Có | Kết thúc hiệu lực exclusive; NULL là chưa có điểm kết thúc. | NONE |
| `is_current` | FLAG | Không | 1 khi valid_to_utc NULL; tối đa một phiên bản current mỗi BK. | NONE |
| `version_no` | COUNT | Không | Số phiên bản tăng dần theo valid_from, bắt đầu 1 trong v2. | NONE |
| `effective_time_basis` | CODE | Không | BOOTSTRAP_ASSUMPTION, SOURCE_EFFECTIVE hoặc OBSERVED_AT; không đánh đồng thời điểm quan sát với hiệu lực thật. | NONE |

Năm cột kiểm toán dùng chung được bổ sung theo mục trên.

**Ràng buộc và cách sử dụng:**

- UK phiên bản hiện hành: source_system, site_id với member_kind=NORMAL và is_current=1.
- Thuộc tính theo dõi thay đổi: site_name, climate_region.
- site_id xác định BK trong hotel_ops; có thể lặp qua các phiên bản.
- version_no>=1; is_current IN (0,1); is_current=1 iff valid_to_utc IS NULL.
- valid_to NULL hoặc valid_from<valid_to; khoảng [valid_from,valid_to) của cùng BK không chồng nhau.
- Dòng NORMAL cùng BK chỉ một current; cùng effective timestamp mà payload khác -> quarantine, không tự lấy dòng cuối.
- Hai dòng đặc biệt 0/-1 không version hóa: version_no=1, current=1, valid_to=NULL.

### D03 DimHotel

**Tên vật lý:** `dim_hotel`. **Grain:** Một phiên bản có hiệu lực của một business key trong namespace nguồn.

**PK:** `hotel_key`. **UK:** `source_system, hotel_id, valid_from_utc`; `source_system, hotel_id, version_no`.

**Lịch sử:** SCD_TYPE2. Không đổi payload thì giữ SK; đổi thuộc tính theo dõi tại t thì đóng phiên bản cũ valid_to=t, is_current=0; thêm phiên bản mới có SK mới, valid_from=t, valid_to=NULL, is_current=1. Cùng batch replay không sinh thêm phiên bản.

| Cột | Kiểu | NULL | Vai trò và quy tắc | Cách tổng hợp |
|---|---|---|---|---|
| `hotel_key` | KEY | Không | Khóa dimension dùng chung hai nhánh. | NONE |
| `source_system` | CODE | Không | Namespace nguồn; calendar/reference cho danh mục sinh. | NONE |
| `member_kind` | CODE | Không | NORMAL, UNKNOWN hoặc NOT_APPLICABLE. | NONE |
| `hotel_id` | ID | Có | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Bắt buộc NORMAL. Nguồn: `hotel_ops.hotels.hotel_id`. | NONE |
| `hotel_name` | TEXT | Có | Tên cơ sở. Bắt buộc NORMAL. Nguồn: `hotel_ops.hotels.hotel_name`. | NONE |
| `stars` | INT | Có | Hạng sao giả định. Bắt buộc NORMAL. Nguồn: `hotel_ops.hotels.stars`. | NONE |
| `site_id` | ID | Có | Tham chiếu bản ghi sites trong cùng database. Bắt buộc NORMAL. Nguồn: `hotel_ops.hotels.site_id`. | NONE |
| `website_channel` | TEXT | Có | Mã website chính thức riêng. Bắt buộc NORMAL. Nguồn: `hotel_ops.hotels.website_channel`. | NONE |
| `valid_from_utc` | UTC | Không | Bắt đầu hiệu lực phiên bản, inclusive; mốc bootstrap v2 theo giả định. | NONE |
| `valid_to_utc` | UTC | Có | Kết thúc hiệu lực exclusive; NULL là chưa có điểm kết thúc. | NONE |
| `is_current` | FLAG | Không | 1 khi valid_to_utc NULL; tối đa một phiên bản current mỗi BK. | NONE |
| `version_no` | COUNT | Không | Số phiên bản tăng dần theo valid_from, bắt đầu 1 trong v2. | NONE |
| `effective_time_basis` | CODE | Không | BOOTSTRAP_ASSUMPTION, SOURCE_EFFECTIVE hoặc OBSERVED_AT; không đánh đồng thời điểm quan sát với hiệu lực thật. | NONE |

Năm cột kiểm toán dùng chung được bổ sung theo mục trên.

**Ràng buộc và cách sử dụng:**

- UK phiên bản hiện hành: source_system, hotel_id với member_kind=NORMAL và is_current=1.
- Thuộc tính theo dõi thay đổi: hotel_name, stars, site_id, website_channel.
- stars IN (3,5); site_id phải tồn tại trong master sites.
- version_no>=1; is_current IN (0,1); is_current=1 iff valid_to_utc IS NULL.
- valid_to NULL hoặc valid_from<valid_to; khoảng [valid_from,valid_to) của cùng BK không chồng nhau.
- Dòng NORMAL cùng BK chỉ một current; cùng effective timestamp mà payload khác -> quarantine, không tự lấy dòng cuối.
- Hai dòng đặc biệt 0/-1 không version hóa: version_no=1, current=1, valid_to=NULL.

### D04 DimRoom

**Tên vật lý:** `dim_room`. **Grain:** Một phiên bản có hiệu lực của một business key trong namespace nguồn.

**PK:** `room_key`. **UK:** `source_system, room_id, valid_from_utc`; `source_system, room_id, version_no`.

**Lịch sử:** SCD_TYPE2. Không đổi payload thì giữ SK; đổi thuộc tính theo dõi tại t thì đóng phiên bản cũ valid_to=t, is_current=0; thêm phiên bản mới có SK mới, valid_from=t, valid_to=NULL, is_current=1. Cùng batch replay không sinh thêm phiên bản.

| Cột | Kiểu | NULL | Vai trò và quy tắc | Cách tổng hợp |
|---|---|---|---|---|
| `room_key` | KEY | Không | Khóa dimension dùng chung hai nhánh. | NONE |
| `source_system` | CODE | Không | Namespace nguồn; calendar/reference cho danh mục sinh. | NONE |
| `member_kind` | CODE | Không | NORMAL, UNKNOWN hoặc NOT_APPLICABLE. | NONE |
| `room_id` | ID | Có | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Bắt buộc NORMAL. Nguồn: `hotel_ops.rooms.room_id`. | NONE |
| `hotel_id` | ID | Có | Tham chiếu bản ghi hotels trong cùng database. Bắt buộc NORMAL. Nguồn: `hotel_ops.rooms.hotel_id`. | NONE |
| `room_type` | TEXT | Có | STANDARD hoặc DELUXE. Bắt buộc NORMAL. Nguồn: `hotel_ops.rooms.room_type`. | NONE |
| `capacity` | INT | Có | Số khách tối đa. Bắt buộc NORMAL. Nguồn: `hotel_ops.rooms.capacity`. | NONE |
| `base_rate_vnd` | MONEY | Có | Giá nền mỗi đêm trước điều chỉnh mùa. Số nguyên VND; không dùng float cho tiền. Bắt buộc NORMAL. Nguồn: `hotel_ops.rooms.base_rate_vnd`. | NONE |
| `valid_from_utc` | UTC | Không | Bắt đầu hiệu lực phiên bản, inclusive; mốc bootstrap v2 theo giả định. | NONE |
| `valid_to_utc` | UTC | Có | Kết thúc hiệu lực exclusive; NULL là chưa có điểm kết thúc. | NONE |
| `is_current` | FLAG | Không | 1 khi valid_to_utc NULL; tối đa một phiên bản current mỗi BK. | NONE |
| `version_no` | COUNT | Không | Số phiên bản tăng dần theo valid_from, bắt đầu 1 trong v2. | NONE |
| `effective_time_basis` | CODE | Không | BOOTSTRAP_ASSUMPTION, SOURCE_EFFECTIVE hoặc OBSERVED_AT; không đánh đồng thời điểm quan sát với hiệu lực thật. | NONE |

Năm cột kiểm toán dùng chung được bổ sung theo mục trên.

**Ràng buộc và cách sử dụng:**

- UK phiên bản hiện hành: source_system, room_id với member_kind=NORMAL và is_current=1.
- Thuộc tính theo dõi thay đổi: hotel_id, room_type, capacity, base_rate_vnd.
- capacity > 0; base_rate_vnd > 0; hotel_id hợp lệ.
- version_no>=1; is_current IN (0,1); is_current=1 iff valid_to_utc IS NULL.
- valid_to NULL hoặc valid_from<valid_to; khoảng [valid_from,valid_to) của cùng BK không chồng nhau.
- Dòng NORMAL cùng BK chỉ một current; cùng effective timestamp mà payload khác -> quarantine, không tự lấy dòng cuối.
- Hai dòng đặc biệt 0/-1 không version hóa: version_no=1, current=1, valid_to=NULL.

### D05 DimChannel

**Tên vật lý:** `dim_channel`. **Grain:** Một phiên bản có hiệu lực của một business key trong namespace nguồn.

**PK:** `channel_key`. **UK:** `source_system, channel_code, valid_from_utc`; `source_system, channel_code, version_no`.

**Lịch sử:** SCD_TYPE2. Không đổi payload thì giữ SK; đổi thuộc tính theo dõi tại t thì đóng phiên bản cũ valid_to=t, is_current=0; thêm phiên bản mới có SK mới, valid_from=t, valid_to=NULL, is_current=1. Cùng batch replay không sinh thêm phiên bản.

| Cột | Kiểu | NULL | Vai trò và quy tắc | Cách tổng hợp |
|---|---|---|---|---|
| `channel_key` | KEY | Không | Khóa dimension dùng chung hai nhánh. | NONE |
| `source_system` | CODE | Không | Namespace nguồn; calendar/reference cho danh mục sinh. | NONE |
| `member_kind` | CODE | Không | NORMAL, UNKNOWN hoặc NOT_APPLICABLE. | NONE |
| `channel_code` | ID | Có | Mã kênh nguồn. Bắt buộc NORMAL. Nguồn: `hotel_ops.channels.channel_id`, `entertainment_ops.ticket_orders.sales_channel`. | NONE |
| `channel_name` | TEXT | Có | Tên kênh hotel từ nguồn; entertainment dùng đúng sales_channel làm nhãn. Bắt buộc NORMAL. Nguồn: `hotel_ops.channels.channel_name`. | NONE |
| `channel_type` | TEXT | Có | Loại kênh hotel từ nguồn; entertainment đặt ENTERTAINMENT_SALES. Bắt buộc NORMAL. Nguồn: `hotel_ops.channels.channel_type`. | NONE |
| `commission_bps` | INT | Có | Hoa hồng giả định theo basis points. Nguồn: `hotel_ops.channels.commission_bps`. | NONE |
| `valid_from_utc` | UTC | Không | Bắt đầu hiệu lực phiên bản, inclusive; mốc bootstrap v2 theo giả định. | NONE |
| `valid_to_utc` | UTC | Có | Kết thúc hiệu lực exclusive; NULL là chưa có điểm kết thúc. | NONE |
| `is_current` | FLAG | Không | 1 khi valid_to_utc NULL; tối đa một phiên bản current mỗi BK. | NONE |
| `version_no` | COUNT | Không | Số phiên bản tăng dần theo valid_from, bắt đầu 1 trong v2. | NONE |
| `effective_time_basis` | CODE | Không | BOOTSTRAP_ASSUMPTION, SOURCE_EFFECTIVE hoặc OBSERVED_AT; không đánh đồng thời điểm quan sát với hiệu lực thật. | NONE |

Năm cột kiểm toán dùng chung được bổ sung theo mục trên.

**Ràng buộc và cách sử dụng:**

- UK phiên bản hiện hành: source_system, channel_code với member_kind=NORMAL và is_current=1.
- Thuộc tính theo dõi thay đổi: channel_name, channel_type, commission_bps.
- commission_bps 0..10000 nếu có; entertainment channel không có mức hoa hồng thì NULL, không điền 0.
- version_no>=1; is_current IN (0,1); is_current=1 iff valid_to_utc IS NULL.
- valid_to NULL hoặc valid_from<valid_to; khoảng [valid_from,valid_to) của cùng BK không chồng nhau.
- Dòng NORMAL cùng BK chỉ một current; cùng effective timestamp mà payload khác -> quarantine, không tự lấy dòng cuối.
- Hai dòng đặc biệt 0/-1 không version hóa: version_no=1, current=1, valid_to=NULL.

### D06 DimPromotion

**Tên vật lý:** `dim_promotion`. **Grain:** Một phiên bản có hiệu lực của một business key trong namespace nguồn.

**PK:** `promotion_key`. **UK:** `source_system, promotion_id, valid_from_utc`; `source_system, promotion_id, version_no`.

**Lịch sử:** SCD_TYPE2. Không đổi payload thì giữ SK; đổi thuộc tính theo dõi tại t thì đóng phiên bản cũ valid_to=t, is_current=0; thêm phiên bản mới có SK mới, valid_from=t, valid_to=NULL, is_current=1. Cùng batch replay không sinh thêm phiên bản.

| Cột | Kiểu | NULL | Vai trò và quy tắc | Cách tổng hợp |
|---|---|---|---|---|
| `promotion_key` | KEY | Không | Khóa dimension dùng chung hai nhánh. | NONE |
| `source_system` | CODE | Không | Namespace nguồn; calendar/reference cho danh mục sinh. | NONE |
| `member_kind` | CODE | Không | NORMAL, UNKNOWN hoặc NOT_APPLICABLE. | NONE |
| `promotion_id` | ID | Có | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Bắt buộc NORMAL. Nguồn: `hotel_ops.promotions.promotion_id`. | NONE |
| `promotion_name` | TEXT | Có | Tên chiến dịch. Bắt buộc NORMAL. Nguồn: `hotel_ops.promotions.promotion_name`. | NONE |
| `channel_id` | ID | Có | Tham chiếu bản ghi channels trong cùng database. Nguồn: `hotel_ops.promotions.channel_id`. | NONE |
| `site_id` | ID | Có | Tham chiếu bản ghi sites trong cùng database. Nguồn: `hotel_ops.promotions.site_id`. | NONE |
| `sale_from` | DATE | Có | Bắt đầu mở bán. Bắt buộc NORMAL. Nguồn: `hotel_ops.promotions.sale_from`. | NONE |
| `sale_to` | DATE | Có | Kết thúc mở bán. Bắt buộc NORMAL. Nguồn: `hotel_ops.promotions.sale_to`. | NONE |
| `stay_from` | DATE | Có | Bắt đầu khoảng lưu trú hợp lệ. Bắt buộc NORMAL. Nguồn: `hotel_ops.promotions.stay_from`. | NONE |
| `stay_to` | DATE | Có | Kết thúc khoảng lưu trú hợp lệ. Bắt buộc NORMAL. Nguồn: `hotel_ops.promotions.stay_to`. | NONE |
| `discount_bps` | INT | Có | Tỷ lệ giảm trên giá gói. Bắt buộc NORMAL. Nguồn: `hotel_ops.promotions.discount_bps`. | NONE |
| `partner_share_bps` | INT | Có | Tỷ lệ đối tác chịu trong phần giảm. Bắt buộc NORMAL. Nguồn: `hotel_ops.promotions.partner_share_bps`. | NONE |
| `cap_vnd` | MONEY | Có | Giới hạn giảm mỗi booking. Số nguyên VND; không dùng float cho tiền. Bắt buộc NORMAL. Nguồn: `hotel_ops.promotions.cap_vnd`. | NONE |
| `valid_from_utc` | UTC | Không | Bắt đầu hiệu lực phiên bản, inclusive; mốc bootstrap v2 theo giả định. | NONE |
| `valid_to_utc` | UTC | Có | Kết thúc hiệu lực exclusive; NULL là chưa có điểm kết thúc. | NONE |
| `is_current` | FLAG | Không | 1 khi valid_to_utc NULL; tối đa một phiên bản current mỗi BK. | NONE |
| `version_no` | COUNT | Không | Số phiên bản tăng dần theo valid_from, bắt đầu 1 trong v2. | NONE |
| `effective_time_basis` | CODE | Không | BOOTSTRAP_ASSUMPTION, SOURCE_EFFECTIVE hoặc OBSERVED_AT; không đánh đồng thời điểm quan sát với hiệu lực thật. | NONE |

Năm cột kiểm toán dùng chung được bổ sung theo mục trên.

**Ràng buộc và cách sử dụng:**

- UK phiên bản hiện hành: source_system, promotion_id với member_kind=NORMAL và is_current=1.
- Thuộc tính theo dõi thay đổi: promotion_name, channel_id, site_id, sale_from, sale_to, stay_from, stay_to, discount_bps, partner_share_bps, cap_vnd.
- discount_bps và partner_share_bps 0..10000; cap_vnd >= 0; sale_to>=sale_from; stay_to>=stay_from.
- NULL channel_id/site_id nghĩa là không giới hạn phạm vi tương ứng, không phải sai FK.
- version_no>=1; is_current IN (0,1); is_current=1 iff valid_to_utc IS NULL.
- valid_to NULL hoặc valid_from<valid_to; khoảng [valid_from,valid_to) của cùng BK không chồng nhau.
- Dòng NORMAL cùng BK chỉ một current; cùng effective timestamp mà payload khác -> quarantine, không tự lấy dòng cuối.
- Hai dòng đặc biệt 0/-1 không version hóa: version_no=1, current=1, valid_to=NULL.

### D07 DimCustomerProfile

**Tên vật lý:** `dim_customer_profile`. **Grain:** Một phiên bản có hiệu lực của một business key trong namespace nguồn.

**PK:** `customer_profile_key`. **UK:** `source_system, source_customer_id, valid_from_utc`; `source_system, source_customer_id, version_no`.

**Lịch sử:** SCD_TYPE2. Không đổi payload thì giữ SK; đổi thuộc tính theo dõi tại t thì đóng phiên bản cũ valid_to=t, is_current=0; thêm phiên bản mới có SK mới, valid_from=t, valid_to=NULL, is_current=1. Cùng batch replay không sinh thêm phiên bản.

| Cột | Kiểu | NULL | Vai trò và quy tắc | Cách tổng hợp |
|---|---|---|---|---|
| `customer_profile_key` | KEY | Không | Khóa dimension dùng chung hai nhánh. | NONE |
| `source_system` | CODE | Không | Namespace nguồn; calendar/reference cho danh mục sinh. | NONE |
| `member_kind` | CODE | Không | NORMAL, UNKNOWN hoặc NOT_APPLICABLE. | NONE |
| `source_customer_id` | ID | Có | ID hồ sơ trong từng nguồn. Bắt buộc NORMAL. Nguồn: `hotel_ops.guests.guest_id`, `entertainment_ops.customers.customer_id`. | NONE |
| `full_name` | TEXT | Có | Thuộc tính hồ sơ khách giả lập; không dùng làm khóa toàn doanh nghiệp. Bắt buộc NORMAL. Nguồn: `hotel_ops.guests.full_name`, `entertainment_ops.customers.full_name`. | NONE |
| `phone` | TEXT | Có | Thuộc tính hồ sơ khách giả lập; không dùng làm khóa toàn doanh nghiệp. Nguồn: `hotel_ops.guests.phone`, `entertainment_ops.customers.phone`. | NONE |
| `email` | TEXT | Có | Thuộc tính hồ sơ khách giả lập; không dùng làm khóa toàn doanh nghiệp. Nguồn: `hotel_ops.guests.email`, `entertainment_ops.customers.email`. | NONE |
| `member_card_ref` | ID | Có | Mã thẻ khách xuất trình; tham chiếu hợp lệ liên hệ thống. Nguồn: `entertainment_ops.customers.member_card_ref`. | NONE |
| `valid_from_utc` | UTC | Không | Bắt đầu hiệu lực phiên bản, inclusive; mốc bootstrap v2 theo giả định. | NONE |
| `valid_to_utc` | UTC | Có | Kết thúc hiệu lực exclusive; NULL là chưa có điểm kết thúc. | NONE |
| `is_current` | FLAG | Không | 1 khi valid_to_utc NULL; tối đa một phiên bản current mỗi BK. | NONE |
| `version_no` | COUNT | Không | Số phiên bản tăng dần theo valid_from, bắt đầu 1 trong v2. | NONE |
| `effective_time_basis` | CODE | Không | BOOTSTRAP_ASSUMPTION, SOURCE_EFFECTIVE hoặc OBSERVED_AT; không đánh đồng thời điểm quan sát với hiệu lực thật. | NONE |

Năm cột kiểm toán dùng chung được bổ sung theo mục trên.

**Ràng buộc và cách sử dụng:**

- UK phiên bản hiện hành: source_system, source_customer_id với member_kind=NORMAL và is_current=1.
- Thuộc tính theo dõi thay đổi: full_name, phone, email, member_card_ref.
- Không ghép hồ sơ khách theo tên/phone/email hoặc audit_only.
- member_card_ref NULL cho khách không có thẻ và hồ sơ hotel; không suy ra trạng thái hội viên đang hiệu lực.
- version_no>=1; is_current IN (0,1); is_current=1 iff valid_to_utc IS NULL.
- valid_to NULL hoặc valid_from<valid_to; khoảng [valid_from,valid_to) của cùng BK không chồng nhau.
- Dòng NORMAL cùng BK chỉ một current; cùng effective timestamp mà payload khác -> quarantine, không tự lấy dòng cuối.
- Hai dòng đặc biệt 0/-1 không version hóa: version_no=1, current=1, valid_to=NULL.

### D08 DimRatePlan

**Tên vật lý:** `dim_rate_plan`. **Grain:** Một phiên bản có hiệu lực của một business key trong namespace nguồn.

**PK:** `rate_plan_key`. **UK:** `source_system, rate_plan_id, valid_from_utc`; `source_system, rate_plan_id, version_no`.

**Lịch sử:** SCD_TYPE2. Không đổi payload thì giữ SK; đổi thuộc tính theo dõi tại t thì đóng phiên bản cũ valid_to=t, is_current=0; thêm phiên bản mới có SK mới, valid_from=t, valid_to=NULL, is_current=1. Cùng batch replay không sinh thêm phiên bản.

| Cột | Kiểu | NULL | Vai trò và quy tắc | Cách tổng hợp |
|---|---|---|---|---|
| `rate_plan_key` | KEY | Không | Khóa dimension dùng chung hai nhánh. | NONE |
| `source_system` | CODE | Không | Namespace nguồn; calendar/reference cho danh mục sinh. | NONE |
| `member_kind` | CODE | Không | NORMAL, UNKNOWN hoặc NOT_APPLICABLE. | NONE |
| `rate_plan_id` | ID | Có | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Bắt buộc NORMAL. Nguồn: `hotel_ops.rate_plans.rate_plan_id`. | NONE |
| `hotel_id` | ID | Có | Tham chiếu bản ghi hotels trong cùng database. Bắt buộc NORMAL. Nguồn: `hotel_ops.rate_plans.hotel_id`. | NONE |
| `channel_id` | ID | Có | Tham chiếu bản ghi channels trong cùng database. Bắt buộc NORMAL. Nguồn: `hotel_ops.rate_plans.channel_id`. | NONE |
| `plan_name` | TEXT | Có | Tên sản phẩm đặt phòng. Bắt buộc NORMAL. Nguồn: `hotel_ops.rate_plans.plan_name`. | NONE |
| `breakfast_included` | FLAG | Có | 1 gồm ăn sáng, 0 không gồm. Bắt buộc NORMAL. Nguồn: `hotel_ops.rate_plans.breakfast_included`. | NONE |
| `refundable` | FLAG | Có | 1 cho phép hoàn theo điều kiện. Bắt buộc NORMAL. Nguồn: `hotel_ops.rate_plans.refundable`. | NONE |
| `valid_from_utc` | UTC | Không | Bắt đầu hiệu lực phiên bản, inclusive; mốc bootstrap v2 theo giả định. | NONE |
| `valid_to_utc` | UTC | Có | Kết thúc hiệu lực exclusive; NULL là chưa có điểm kết thúc. | NONE |
| `is_current` | FLAG | Không | 1 khi valid_to_utc NULL; tối đa một phiên bản current mỗi BK. | NONE |
| `version_no` | COUNT | Không | Số phiên bản tăng dần theo valid_from, bắt đầu 1 trong v2. | NONE |
| `effective_time_basis` | CODE | Không | BOOTSTRAP_ASSUMPTION, SOURCE_EFFECTIVE hoặc OBSERVED_AT; không đánh đồng thời điểm quan sát với hiệu lực thật. | NONE |

Năm cột kiểm toán dùng chung được bổ sung theo mục trên.

**Ràng buộc và cách sử dụng:**

- UK phiên bản hiện hành: source_system, rate_plan_id với member_kind=NORMAL và is_current=1.
- Thuộc tính theo dõi thay đổi: hotel_id, channel_id, plan_name, breakfast_included, refundable.
- breakfast_included và refundable IN (0,1); hotel_id/channel_id hợp lệ.
- version_no>=1; is_current IN (0,1); is_current=1 iff valid_to_utc IS NULL.
- valid_to NULL hoặc valid_from<valid_to; khoảng [valid_from,valid_to) của cùng BK không chồng nhau.
- Dòng NORMAL cùng BK chỉ một current; cùng effective timestamp mà payload khác -> quarantine, không tự lấy dòng cuối.
- Hai dòng đặc biệt 0/-1 không version hóa: version_no=1, current=1, valid_to=NULL.

### D09 DimOutlet

**Tên vật lý:** `dim_outlet`. **Grain:** Một phiên bản có hiệu lực của một business key trong namespace nguồn.

**PK:** `outlet_key`. **UK:** `source_system, outlet_id, valid_from_utc`; `source_system, outlet_id, version_no`.

**Lịch sử:** SCD_TYPE2. Không đổi payload thì giữ SK; đổi thuộc tính theo dõi tại t thì đóng phiên bản cũ valid_to=t, is_current=0; thêm phiên bản mới có SK mới, valid_from=t, valid_to=NULL, is_current=1. Cùng batch replay không sinh thêm phiên bản.

| Cột | Kiểu | NULL | Vai trò và quy tắc | Cách tổng hợp |
|---|---|---|---|---|
| `outlet_key` | KEY | Không | Khóa dimension dùng chung hai nhánh. | NONE |
| `source_system` | CODE | Không | Namespace nguồn; calendar/reference cho danh mục sinh. | NONE |
| `member_kind` | CODE | Không | NORMAL, UNKNOWN hoặc NOT_APPLICABLE. | NONE |
| `outlet_id` | ID | Có | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Bắt buộc NORMAL. Nguồn: `hotel_ops.outlets.outlet_id`. | NONE |
| `hotel_id` | ID | Có | Tham chiếu bản ghi hotels trong cùng database. Bắt buộc NORMAL. Nguồn: `hotel_ops.outlets.hotel_id`. | NONE |
| `outlet_type` | TEXT | Có | RESTAURANT hoặc BAR. Bắt buộc NORMAL. Nguồn: `hotel_ops.outlets.outlet_type`. | NONE |
| `capacity` | INT | Có | Sức chứa. Bắt buộc NORMAL. Nguồn: `hotel_ops.outlets.capacity`. | NONE |
| `quality_profile` | INT | Có | Mức nền mô phỏng, không suy từ hạng sao. Bắt buộc NORMAL. Nguồn: `hotel_ops.outlets.quality_profile`. | NONE |
| `valid_from_utc` | UTC | Không | Bắt đầu hiệu lực phiên bản, inclusive; mốc bootstrap v2 theo giả định. | NONE |
| `valid_to_utc` | UTC | Có | Kết thúc hiệu lực exclusive; NULL là chưa có điểm kết thúc. | NONE |
| `is_current` | FLAG | Không | 1 khi valid_to_utc NULL; tối đa một phiên bản current mỗi BK. | NONE |
| `version_no` | COUNT | Không | Số phiên bản tăng dần theo valid_from, bắt đầu 1 trong v2. | NONE |
| `effective_time_basis` | CODE | Không | BOOTSTRAP_ASSUMPTION, SOURCE_EFFECTIVE hoặc OBSERVED_AT; không đánh đồng thời điểm quan sát với hiệu lực thật. | NONE |

Năm cột kiểm toán dùng chung được bổ sung theo mục trên.

**Ràng buộc và cách sử dụng:**

- UK phiên bản hiện hành: source_system, outlet_id với member_kind=NORMAL và is_current=1.
- Thuộc tính theo dõi thay đổi: hotel_id, outlet_type, capacity, quality_profile.
- outlet_type IN (RESTAURANT,BAR); capacity > 0; quality_profile là thang nguồn, không tự suy ra hạng sao.
- version_no>=1; is_current IN (0,1); is_current=1 iff valid_to_utc IS NULL.
- valid_to NULL hoặc valid_from<valid_to; khoảng [valid_from,valid_to) của cùng BK không chồng nhau.
- Dòng NORMAL cùng BK chỉ một current; cùng effective timestamp mà payload khác -> quarantine, không tự lấy dòng cuối.
- Hai dòng đặc biệt 0/-1 không version hóa: version_no=1, current=1, valid_to=NULL.

### D10 DimMeal

**Tên vật lý:** `dim_meal`. **Grain:** Một thành viên hiện hành cho mỗi business key trong namespace.

**PK:** `meal_key`. **UK:** `meal_code`.

**Lịch sử:** STATIC. Upsert theo BK và registry; cập nhật khi row_hash thay đổi; không tự xóa thành viên vắng mặt.

| Cột | Kiểu | NULL | Vai trò và quy tắc | Cách tổng hợp |
|---|---|---|---|---|
| `meal_key` | KEY | Không | Khóa dimension dùng chung hai nhánh. | NONE |
| `source_system` | CODE | Không | Namespace nguồn; calendar/reference cho danh mục sinh. | NONE |
| `member_kind` | CODE | Không | NORMAL, UNKNOWN hoặc NOT_APPLICABLE. | NONE |
| `meal_code` | CODE | Có | Mã bữa theo danh mục bốn giá trị. Bắt buộc NORMAL. | NONE |
| `meal_name` | TEXT | Có | Nhãn tiếng Việt tương ứng. Bắt buộc NORMAL. | NONE |

Năm cột kiểm toán dùng chung được bổ sung theo mục trên.

**Ràng buộc và cách sử dụng:**

- meal_code IN (BREAKFAST,LUNCH,DINNER,BAR); khóa danh mục cố định 1,2,3,4 theo đúng thứ tự này.

### D11 DimCentre

**Tên vật lý:** `dim_centre`. **Grain:** Một phiên bản có hiệu lực của một business key trong namespace nguồn.

**PK:** `centre_key`. **UK:** `source_system, centre_id, valid_from_utc`; `source_system, centre_id, version_no`.

**Lịch sử:** SCD_TYPE2. Không đổi payload thì giữ SK; đổi thuộc tính theo dõi tại t thì đóng phiên bản cũ valid_to=t, is_current=0; thêm phiên bản mới có SK mới, valid_from=t, valid_to=NULL, is_current=1. Cùng batch replay không sinh thêm phiên bản.

| Cột | Kiểu | NULL | Vai trò và quy tắc | Cách tổng hợp |
|---|---|---|---|---|
| `centre_key` | KEY | Không | Khóa dimension dùng chung hai nhánh. | NONE |
| `source_system` | CODE | Không | Namespace nguồn; calendar/reference cho danh mục sinh. | NONE |
| `member_kind` | CODE | Không | NORMAL, UNKNOWN hoặc NOT_APPLICABLE. | NONE |
| `centre_id` | ID | Có | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Bắt buộc NORMAL. Nguồn: `entertainment_ops.centres.centre_id`. | NONE |
| `centre_name` | TEXT | Có | Tên trung tâm. Bắt buộc NORMAL. Nguồn: `entertainment_ops.centres.centre_name`. | NONE |
| `site_code` | ID | Có | Mã cụm dùng trong thỏa thuận liên đơn vị. Bắt buộc NORMAL. Nguồn: `entertainment_ops.centres.site_code`. | NONE |
| `valid_from_utc` | UTC | Không | Bắt đầu hiệu lực phiên bản, inclusive; mốc bootstrap v2 theo giả định. | NONE |
| `valid_to_utc` | UTC | Có | Kết thúc hiệu lực exclusive; NULL là chưa có điểm kết thúc. | NONE |
| `is_current` | FLAG | Không | 1 khi valid_to_utc NULL; tối đa một phiên bản current mỗi BK. | NONE |
| `version_no` | COUNT | Không | Số phiên bản tăng dần theo valid_from, bắt đầu 1 trong v2. | NONE |
| `effective_time_basis` | CODE | Không | BOOTSTRAP_ASSUMPTION, SOURCE_EFFECTIVE hoặc OBSERVED_AT; không đánh đồng thời điểm quan sát với hiệu lực thật. | NONE |

Năm cột kiểm toán dùng chung được bổ sung theo mục trên.

**Ràng buộc và cách sử dụng:**

- UK phiên bản hiện hành: source_system, centre_id với member_kind=NORMAL và is_current=1.
- Thuộc tính theo dõi thay đổi: centre_name, site_code.
- site_code ánh xạ đúng một sites.site_id; tên giống nhau không phải bằng chứng ánh xạ.
- version_no>=1; is_current IN (0,1); is_current=1 iff valid_to_utc IS NULL.
- valid_to NULL hoặc valid_from<valid_to; khoảng [valid_from,valid_to) của cùng BK không chồng nhau.
- Dòng NORMAL cùng BK chỉ một current; cùng effective timestamp mà payload khác -> quarantine, không tự lấy dòng cuối.
- Hai dòng đặc biệt 0/-1 không version hóa: version_no=1, current=1, valid_to=NULL.

### D12 DimActivity

**Tên vật lý:** `dim_activity`. **Grain:** Một phiên bản có hiệu lực của một business key trong namespace nguồn.

**PK:** `activity_key`. **UK:** `source_system, activity_id, valid_from_utc`; `source_system, activity_id, version_no`.

**Lịch sử:** SCD_TYPE2. Không đổi payload thì giữ SK; đổi thuộc tính theo dõi tại t thì đóng phiên bản cũ valid_to=t, is_current=0; thêm phiên bản mới có SK mới, valid_from=t, valid_to=NULL, is_current=1. Cùng batch replay không sinh thêm phiên bản.

| Cột | Kiểu | NULL | Vai trò và quy tắc | Cách tổng hợp |
|---|---|---|---|---|
| `activity_key` | KEY | Không | Khóa dimension dùng chung hai nhánh. | NONE |
| `source_system` | CODE | Không | Namespace nguồn; calendar/reference cho danh mục sinh. | NONE |
| `member_kind` | CODE | Không | NORMAL, UNKNOWN hoặc NOT_APPLICABLE. | NONE |
| `activity_id` | ID | Có | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Bắt buộc NORMAL. Nguồn: `entertainment_ops.activities.activity_id`. | NONE |
| `centre_id` | ID | Có | Tham chiếu bản ghi centres trong cùng database. Bắt buộc NORMAL. Nguồn: `entertainment_ops.activities.centre_id`. | NONE |
| `activity_name` | TEXT | Có | Tên hoạt động. Bắt buộc NORMAL. Nguồn: `entertainment_ops.activities.activity_name`. | NONE |
| `outdoor` | FLAG | Có | 1 nếu phụ thuộc hoạt động ngoài trời. Bắt buộc NORMAL. Nguồn: `entertainment_ops.activities.outdoor`. | NONE |
| `capacity_per_day` | INT | Có | Sức chứa giả định mỗi ngày. Bắt buộc NORMAL. Nguồn: `entertainment_ops.activities.capacity_per_day`. | NONE |
| `valid_from_utc` | UTC | Không | Bắt đầu hiệu lực phiên bản, inclusive; mốc bootstrap v2 theo giả định. | NONE |
| `valid_to_utc` | UTC | Có | Kết thúc hiệu lực exclusive; NULL là chưa có điểm kết thúc. | NONE |
| `is_current` | FLAG | Không | 1 khi valid_to_utc NULL; tối đa một phiên bản current mỗi BK. | NONE |
| `version_no` | COUNT | Không | Số phiên bản tăng dần theo valid_from, bắt đầu 1 trong v2. | NONE |
| `effective_time_basis` | CODE | Không | BOOTSTRAP_ASSUMPTION, SOURCE_EFFECTIVE hoặc OBSERVED_AT; không đánh đồng thời điểm quan sát với hiệu lực thật. | NONE |

Năm cột kiểm toán dùng chung được bổ sung theo mục trên.

**Ràng buộc và cách sử dụng:**

- UK phiên bản hiện hành: source_system, activity_id với member_kind=NORMAL và is_current=1.
- Thuộc tính theo dõi thay đổi: centre_id, activity_name, outdoor, capacity_per_day.
- outdoor IN (0,1); capacity_per_day > 0.
- version_no>=1; is_current IN (0,1); is_current=1 iff valid_to_utc IS NULL.
- valid_to NULL hoặc valid_from<valid_to; khoảng [valid_from,valid_to) của cùng BK không chồng nhau.
- Dòng NORMAL cùng BK chỉ một current; cùng effective timestamp mà payload khác -> quarantine, không tự lấy dòng cuối.
- Hai dòng đặc biệt 0/-1 không version hóa: version_no=1, current=1, valid_to=NULL.

### D13 DimVehicle

**Tên vật lý:** `dim_vehicle`. **Grain:** Một phiên bản có hiệu lực của một business key trong namespace nguồn.

**PK:** `vehicle_key`. **UK:** `source_system, vehicle_id, valid_from_utc`; `source_system, vehicle_id, version_no`.

**Lịch sử:** SCD_TYPE2. Không đổi payload thì giữ SK; đổi thuộc tính theo dõi tại t thì đóng phiên bản cũ valid_to=t, is_current=0; thêm phiên bản mới có SK mới, valid_from=t, valid_to=NULL, is_current=1. Cùng batch replay không sinh thêm phiên bản.

| Cột | Kiểu | NULL | Vai trò và quy tắc | Cách tổng hợp |
|---|---|---|---|---|
| `vehicle_key` | KEY | Không | Khóa dimension dùng chung hai nhánh. | NONE |
| `source_system` | CODE | Không | Namespace nguồn; calendar/reference cho danh mục sinh. | NONE |
| `member_kind` | CODE | Không | NORMAL, UNKNOWN hoặc NOT_APPLICABLE. | NONE |
| `vehicle_id` | ID | Có | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Bắt buộc NORMAL. Nguồn: `entertainment_ops.vehicles.vehicle_id`. | NONE |
| `centre_id` | ID | Có | Tham chiếu bản ghi centres trong cùng database. Bắt buộc NORMAL. Nguồn: `entertainment_ops.vehicles.centre_id`. | NONE |
| `vehicle_type` | TEXT | Có | CAR hoặc MOTORBIKE. Bắt buộc NORMAL. Nguồn: `entertainment_ops.vehicles.vehicle_type`. | NONE |
| `daily_rate_vnd` | MONEY | Có | Giá một ngày thuê. Số nguyên VND; không dùng float cho tiền. Bắt buộc NORMAL. Nguồn: `entertainment_ops.vehicles.daily_rate_vnd`. | NONE |
| `valid_from_utc` | UTC | Không | Bắt đầu hiệu lực phiên bản, inclusive; mốc bootstrap v2 theo giả định. | NONE |
| `valid_to_utc` | UTC | Có | Kết thúc hiệu lực exclusive; NULL là chưa có điểm kết thúc. | NONE |
| `is_current` | FLAG | Không | 1 khi valid_to_utc NULL; tối đa một phiên bản current mỗi BK. | NONE |
| `version_no` | COUNT | Không | Số phiên bản tăng dần theo valid_from, bắt đầu 1 trong v2. | NONE |
| `effective_time_basis` | CODE | Không | BOOTSTRAP_ASSUMPTION, SOURCE_EFFECTIVE hoặc OBSERVED_AT; không đánh đồng thời điểm quan sát với hiệu lực thật. | NONE |

Năm cột kiểm toán dùng chung được bổ sung theo mục trên.

**Ràng buộc và cách sử dụng:**

- UK phiên bản hiện hành: source_system, vehicle_id với member_kind=NORMAL và is_current=1.
- Thuộc tính theo dõi thay đổi: centre_id, vehicle_type, daily_rate_vnd.
- daily_rate_vnd > 0; centre_id hợp lệ.
- version_no>=1; is_current IN (0,1); is_current=1 iff valid_to_utc IS NULL.
- valid_to NULL hoặc valid_from<valid_to; khoảng [valid_from,valid_to) của cùng BK không chồng nhau.
- Dòng NORMAL cùng BK chỉ một current; cùng effective timestamp mà payload khác -> quarantine, không tự lấy dòng cuối.
- Hai dòng đặc biệt 0/-1 không version hóa: version_no=1, current=1, valid_to=NULL.

### D14 DimSupplier

**Tên vật lý:** `dim_supplier`. **Grain:** Một phiên bản có hiệu lực của một business key trong namespace nguồn.

**PK:** `supplier_key`. **UK:** `source_system, supplier_id, valid_from_utc`; `source_system, supplier_id, version_no`.

**Lịch sử:** SCD_TYPE2. Không đổi payload thì giữ SK; đổi thuộc tính theo dõi tại t thì đóng phiên bản cũ valid_to=t, is_current=0; thêm phiên bản mới có SK mới, valid_from=t, valid_to=NULL, is_current=1. Cùng batch replay không sinh thêm phiên bản.

| Cột | Kiểu | NULL | Vai trò và quy tắc | Cách tổng hợp |
|---|---|---|---|---|
| `supplier_key` | KEY | Không | Khóa dimension dùng chung hai nhánh. | NONE |
| `source_system` | CODE | Không | Namespace nguồn; calendar/reference cho danh mục sinh. | NONE |
| `member_kind` | CODE | Không | NORMAL, UNKNOWN hoặc NOT_APPLICABLE. | NONE |
| `supplier_id` | ID | Có | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Bắt buộc NORMAL. Nguồn: `hotel_ops.suppliers.supplier_id`. | NONE |
| `supplier_name` | TEXT | Có | Tên thương hiệu thật hoặc thương nhân giả định. Bắt buộc NORMAL. Nguồn: `hotel_ops.suppliers.supplier_name`. | NONE |
| `category` | TEXT | Có | FOOD, EQUIPMENT hoặc MAINTENANCE. Bắt buộc NORMAL. Nguồn: `hotel_ops.suppliers.category`. | NONE |
| `site_id` | ID | Có | Tham chiếu bản ghi sites trong cùng database. Nguồn: `hotel_ops.suppliers.site_id`. | NONE |
| `delivery_format` | TEXT | Có | CSV, TEXT hoặc MIXED; giả định tích hợp. Bắt buộc NORMAL. Nguồn: `hotel_ops.suppliers.delivery_format`. | NONE |
| `valid_from_utc` | UTC | Không | Bắt đầu hiệu lực phiên bản, inclusive; mốc bootstrap v2 theo giả định. | NONE |
| `valid_to_utc` | UTC | Có | Kết thúc hiệu lực exclusive; NULL là chưa có điểm kết thúc. | NONE |
| `is_current` | FLAG | Không | 1 khi valid_to_utc NULL; tối đa một phiên bản current mỗi BK. | NONE |
| `version_no` | COUNT | Không | Số phiên bản tăng dần theo valid_from, bắt đầu 1 trong v2. | NONE |
| `effective_time_basis` | CODE | Không | BOOTSTRAP_ASSUMPTION, SOURCE_EFFECTIVE hoặc OBSERVED_AT; không đánh đồng thời điểm quan sát với hiệu lực thật. | NONE |

Năm cột kiểm toán dùng chung được bổ sung theo mục trên.

**Ràng buộc và cách sử dụng:**

- UK phiên bản hiện hành: source_system, supplier_id với member_kind=NORMAL và is_current=1.
- Thuộc tính theo dõi thay đổi: supplier_name, category, site_id, delivery_format.
- site_id NULL cho nhà cung cấp phạm vi toàn chuỗi; category không suy ra nhà thầu thực hiện bảo trì.
- version_no>=1; is_current IN (0,1); is_current=1 iff valid_to_utc IS NULL.
- valid_to NULL hoặc valid_from<valid_to; khoảng [valid_from,valid_to) của cùng BK không chồng nhau.
- Dòng NORMAL cùng BK chỉ một current; cùng effective timestamp mà payload khác -> quarantine, không tự lấy dòng cuối.
- Hai dòng đặc biệt 0/-1 không version hóa: version_no=1, current=1, valid_to=NULL.

### D15 DimItem

**Tên vật lý:** `dim_item`. **Grain:** Một phiên bản có hiệu lực của một business key trong namespace nguồn.

**PK:** `item_key`. **UK:** `source_system, item_id, valid_from_utc`; `source_system, item_id, version_no`.

**Lịch sử:** SCD_TYPE2. Không đổi payload thì giữ SK; đổi thuộc tính theo dõi tại t thì đóng phiên bản cũ valid_to=t, is_current=0; thêm phiên bản mới có SK mới, valid_from=t, valid_to=NULL, is_current=1. Cùng batch replay không sinh thêm phiên bản.

| Cột | Kiểu | NULL | Vai trò và quy tắc | Cách tổng hợp |
|---|---|---|---|---|
| `item_key` | KEY | Không | Khóa dimension dùng chung hai nhánh. | NONE |
| `source_system` | CODE | Không | Namespace nguồn; calendar/reference cho danh mục sinh. | NONE |
| `member_kind` | CODE | Không | NORMAL, UNKNOWN hoặc NOT_APPLICABLE. | NONE |
| `item_id` | ID | Có | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Bắt buộc NORMAL. Nguồn: `hotel_ops.items.item_id`. | NONE |
| `item_name` | TEXT | Có | Tên hàng chuẩn. Bắt buộc NORMAL. Nguồn: `hotel_ops.items.item_name`. | NONE |
| `specification` | TEXT | Có | Quy cách phân biệt mặt hàng. Bắt buộc NORMAL. Nguồn: `hotel_ops.items.specification`. | NONE |
| `base_unit` | TEXT | Có | kg, litre hoặc piece. Bắt buộc NORMAL. Nguồn: `hotel_ops.items.base_unit`. | NONE |
| `shelf_life_days` | INT | Có | Hạn dùng giả định sau nhận; 0 cho hàng bền. Bắt buộc NORMAL. Nguồn: `hotel_ops.items.shelf_life_days`. | NONE |
| `valid_from_utc` | UTC | Không | Bắt đầu hiệu lực phiên bản, inclusive; mốc bootstrap v2 theo giả định. | NONE |
| `valid_to_utc` | UTC | Có | Kết thúc hiệu lực exclusive; NULL là chưa có điểm kết thúc. | NONE |
| `is_current` | FLAG | Không | 1 khi valid_to_utc NULL; tối đa một phiên bản current mỗi BK. | NONE |
| `version_no` | COUNT | Không | Số phiên bản tăng dần theo valid_from, bắt đầu 1 trong v2. | NONE |
| `effective_time_basis` | CODE | Không | BOOTSTRAP_ASSUMPTION, SOURCE_EFFECTIVE hoặc OBSERVED_AT; không đánh đồng thời điểm quan sát với hiệu lực thật. | NONE |

Năm cột kiểm toán dùng chung được bổ sung theo mục trên.

**Ràng buộc và cách sử dụng:**

- UK phiên bản hiện hành: source_system, item_id với member_kind=NORMAL và is_current=1.
- Thuộc tính theo dõi thay đổi: item_name, specification, base_unit, shelf_life_days.
- base_unit phải giữ kèm quantity khi tổng hợp; shelf_life_days >= 0.
- version_no>=1; is_current IN (0,1); is_current=1 iff valid_to_utc IS NULL.
- valid_to NULL hoặc valid_from<valid_to; khoảng [valid_from,valid_to) của cùng BK không chồng nhau.
- Dòng NORMAL cùng BK chỉ một current; cùng effective timestamp mà payload khác -> quarantine, không tự lấy dòng cuối.
- Hai dòng đặc biệt 0/-1 không version hóa: version_no=1, current=1, valid_to=NULL.

### D16 DimAsset

**Tên vật lý:** `dim_asset`. **Grain:** Một phiên bản có hiệu lực của một business key trong namespace nguồn.

**PK:** `asset_key`. **UK:** `source_system, asset_id, valid_from_utc`; `source_system, asset_id, version_no`.

**Lịch sử:** SCD_TYPE2. Không đổi payload thì giữ SK; đổi thuộc tính theo dõi tại t thì đóng phiên bản cũ valid_to=t, is_current=0; thêm phiên bản mới có SK mới, valid_from=t, valid_to=NULL, is_current=1. Cùng batch replay không sinh thêm phiên bản.

| Cột | Kiểu | NULL | Vai trò và quy tắc | Cách tổng hợp |
|---|---|---|---|---|
| `asset_key` | KEY | Không | Khóa dimension dùng chung hai nhánh. | NONE |
| `source_system` | CODE | Không | Namespace nguồn; calendar/reference cho danh mục sinh. | NONE |
| `member_kind` | CODE | Không | NORMAL, UNKNOWN hoặc NOT_APPLICABLE. | NONE |
| `asset_id` | ID | Có | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Bắt buộc NORMAL. Nguồn: `hotel_ops.assets.asset_id`. | NONE |
| `hotel_id` | ID | Có | Tham chiếu bản ghi hotels trong cùng database. Bắt buộc NORMAL. Nguồn: `hotel_ops.assets.hotel_id`. | NONE |
| `room_id` | ID | Có | Tham chiếu bản ghi rooms trong cùng database. Nguồn: `hotel_ops.assets.room_id`. | NONE |
| `asset_type` | TEXT | Có | AC, LIFT hoặc COLD_STORAGE. Bắt buộc NORMAL. Nguồn: `hotel_ops.assets.asset_type`. | NONE |
| `supplier_id` | ID | Có | Tham chiếu bản ghi suppliers trong cùng database. Bắt buộc NORMAL. Nguồn: `hotel_ops.assets.supplier_id`. | NONE |
| `valid_from_utc` | UTC | Không | Bắt đầu hiệu lực phiên bản, inclusive; mốc bootstrap v2 theo giả định. | NONE |
| `valid_to_utc` | UTC | Có | Kết thúc hiệu lực exclusive; NULL là chưa có điểm kết thúc. | NONE |
| `is_current` | FLAG | Không | 1 khi valid_to_utc NULL; tối đa một phiên bản current mỗi BK. | NONE |
| `version_no` | COUNT | Không | Số phiên bản tăng dần theo valid_from, bắt đầu 1 trong v2. | NONE |
| `effective_time_basis` | CODE | Không | BOOTSTRAP_ASSUMPTION, SOURCE_EFFECTIVE hoặc OBSERVED_AT; không đánh đồng thời điểm quan sát với hiệu lực thật. | NONE |

Năm cột kiểm toán dùng chung được bổ sung theo mục trên.

**Ràng buộc và cách sử dụng:**

- UK phiên bản hiện hành: source_system, asset_id với member_kind=NORMAL và is_current=1.
- Thuộc tính theo dõi thay đổi: hotel_id, room_id, asset_type, supplier_id.
- room_id có thể NULL; nếu có phải thuộc hotel_id của asset; supplier_id là bên bán tài sản.
- version_no>=1; is_current IN (0,1); is_current=1 iff valid_to_utc IS NULL.
- valid_to NULL hoặc valid_from<valid_to; khoảng [valid_from,valid_to) của cùng BK không chồng nhau.
- Dòng NORMAL cùng BK chỉ một current; cùng effective timestamp mà payload khác -> quarantine, không tự lấy dòng cuối.
- Hai dòng đặc biệt 0/-1 không version hóa: version_no=1, current=1, valid_to=NULL.

### F01 FactBooking

**Tên vật lý:** `fact_booking`. **Grain:** Một booking ở trạng thái cuối của batch.

**PK:** `fact_key`. **UK:** `source_system, booking_id`.

**Lịch sử:** FINAL_SNAPSHOT_RESTATEMENT. Merge theo natural key; tính lại tập grain bị ảnh hưởng khi correction. Không append revision như giao dịch mới.

| Cột | Kiểu | NULL | Vai trò và quy tắc | Cách tổng hợp |
|---|---|---|---|---|
| `fact_key` | KEY | Không | Khóa kỹ thuật từ registry theo natural key; không thay ràng buộc grain. | NONE |
| `source_system` | CODE | Không | Namespace định danh các ID nguồn trong dòng. | NONE |
| `booked_date_key` | DATEKEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D01.date_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `arrival_date_key` | DATEKEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D01.date_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `departure_date_key` | DATEKEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D01.date_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `site_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D02.site_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `hotel_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D03.hotel_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `channel_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D05.channel_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `promotion_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D06.promotion_key. -1: booking không dùng promotion. | NONE |
| `customer_profile_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D07.customer_profile_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `booking_id` | ID | Không | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Nguồn: `hotel_ops.bookings.booking_id`. | NONE |
| `status` | TEXT | Không | COMPLETED, CANCELLED hoặc NO_SHOW. Nguồn: `hotel_ops.bookings.status`. | NONE |
| `source_updated_at_utc` | UTC | Không | Thời điểm phiên bản cuối trong snapshot. Múi giờ nguồn +07:00. Nguồn: `hotel_ops.bookings.updated_at`. | NONE |
| `gross_vnd` | MONEY | Không | Giá trị gói phòng trước giảm. Số nguyên VND; không dùng float cho tiền. Nguồn: `hotel_ops.bookings.gross_vnd`. | SUM |
| `discount_vnd` | MONEY | Không | Tổng giảm khách được hưởng. Số nguyên VND; không dùng float cho tiền. Nguồn: `hotel_ops.bookings.discount_vnd`. | SUM |
| `customer_due_vnd` | MONEY | Không | Giá khách trả trước hoàn tiền. Số nguyên VND; không dùng float cho tiền. Nguồn: `hotel_ops.bookings.customer_due_vnd`. | SUM |
| `company_share_vnd` | MONEY | Không | Phần giảm CompanyE chịu. Số nguyên VND; không dùng float cho tiền. Nguồn: `hotel_ops.bookings.company_share_vnd`. | SUM |
| `partner_share_vnd` | MONEY | Không | Phần giảm đối tác chịu. Số nguyên VND; không dùng float cho tiền. Nguồn: `hotel_ops.bookings.partner_share_vnd`. | SUM |
| `commission_vnd` | MONEY | Không | Phí phân phối trên cơ sở tính giả định đã chốt. Số nguyên VND; không dùng float cho tiền. Nguồn: `hotel_ops.bookings.commission_vnd`. | SUM |
| `booking_count` | COUNT | Không | Luôn bằng 1. | SUM |

Năm cột kiểm toán dùng chung được bổ sung theo mục trên.

**Ràng buộc và cách sử dụng:**

- Thời điểm chọn phiên bản dimension: booked_date_key tại 00:00 giờ Việt Nam; mọi dimension không phải Date theo thời điểm đặt.
- status IN (COMPLETED,CANCELLED,NO_SHOW).
- arrival < departure; booked_on <= arrival.
- discount_vnd=company_share_vnd+partner_share_vnd; customer_due_vnd=gross_vnd-discount_vnd; các khoản tiền >= 0.
- B02 chỉ COMPLETED; không nhân giá theo phòng, vé hoặc revision. Room type lọc booking qua EXISTS BridgeBookingRoom, không phân bổ tiền ngầm.
- Lookup dimension NORMAL theo namespace + BK và valid_from <= t < valid_to (NULL là vô hạn); đúng một phiên bản. Thiếu/trùng phiên bản -> quarantine dòng phụ thuộc, không lấy current thay thế.

### F02 FactRoomDay

**Tên vật lý:** `fact_room_day`. **Grain:** Một phòng và một ngày danh mục.

**PK:** `fact_key`. **UK:** `source_system, room_id, date_key`.

**Lịch sử:** FINAL_SNAPSHOT_RESTATEMENT. Merge theo natural key; tính lại tập grain bị ảnh hưởng khi correction. Không append revision như giao dịch mới.

| Cột | Kiểu | NULL | Vai trò và quy tắc | Cách tổng hợp |
|---|---|---|---|---|
| `fact_key` | KEY | Không | Khóa kỹ thuật từ registry theo natural key; không thay ràng buộc grain. | NONE |
| `source_system` | CODE | Không | Namespace định danh các ID nguồn trong dòng. | NONE |
| `room_id` | ID | Không | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Nguồn: `hotel_ops.rooms.room_id`. | NONE |
| `date_key` | DATEKEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D01.date_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `site_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D02.site_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `hotel_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D03.hotel_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `room_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D04.room_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `inventory_day` | FLAG | Không | 1 cho mỗi phòng thuộc danh mục trong kỳ công suất. | SUM |
| `blocked_day` | FLAG | Không | 1 nếu có ít nhất một bảo trì chặn ngày. | SUM |
| `available_day` | FLAG | Không | 1-blocked_day. | SUM |

Năm cột kiểm toán dùng chung được bổ sung theo mục trên.

**Ràng buộc và cách sử dụng:**

- Thời điểm chọn phiên bản dimension: date_key tại 00:00 giờ Việt Nam.
- inventory_day=1; blocked_day IN (0,1); available_day=inventory_day-blocked_day.
- Gộp union khoảng bảo trì trước khi tạo row; không đếm nhiều lần một room-day.
- Hợp DISTINCT mọi khoảng bảo trì [starts_on,ends_on). Dùng chung B01.02 và B08.03; không chịu bộ lọc kênh/khách hoặc loại công việc chi phí.
- Lookup dimension NORMAL theo namespace + BK và valid_from <= t < valid_to (NULL là vô hạn); đúng một phiên bản. Thiếu/trùng phiên bản -> quarantine dòng phụ thuộc, không lấy current thay thế.

### F03 FactStayNight

**Tên vật lý:** `fact_stay_night`. **Grain:** Một phòng và một đêm thực ở hợp lệ.

**PK:** `fact_key`. **UK:** `source_system, room_id, service_date_key`.

**Lịch sử:** FINAL_SNAPSHOT_RESTATEMENT. Merge theo natural key; tính lại tập grain bị ảnh hưởng khi correction. Không append revision như giao dịch mới.

| Cột | Kiểu | NULL | Vai trò và quy tắc | Cách tổng hợp |
|---|---|---|---|---|
| `fact_key` | KEY | Không | Khóa kỹ thuật từ registry theo natural key; không thay ràng buộc grain. | NONE |
| `source_system` | CODE | Không | Namespace định danh các ID nguồn trong dòng. | NONE |
| `room_id` | ID | Không | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Nguồn: `hotel_ops.rooms.room_id`. | NONE |
| `service_date_key` | DATEKEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D01.date_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `site_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D02.site_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `hotel_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D03.hotel_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `room_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D04.room_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `channel_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D05.channel_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `customer_profile_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D07.customer_profile_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `rate_plan_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D08.rate_plan_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `stay_id` | ID | Không | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Nguồn: `hotel_ops.stays.stay_id`. | NONE |
| `booking_room_id` | ID | Không | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Nguồn: `hotel_ops.booking_rooms.booking_room_id`. | NONE |
| `booking_id` | ID | Không | Tham chiếu bản ghi bookings trong cùng database. Nguồn: `hotel_ops.booking_rooms.booking_id`. | NONE |
| `occupied_night` | FLAG | Không | 1 cho mỗi đêm thực ở của booking COMPLETED. | SUM |

Năm cột kiểm toán dùng chung được bổ sung theo mục trên.

**Ràng buộc và cách sử dụng:**

- Thời điểm chọn phiên bản dimension: service_date_key tại 00:00 giờ Việt Nam.
- Không trùng namespace/room_id/service_date_key, kể cả khác stay_id; overlap phải báo lỗi trước DISTINCT.
- Đêm ở thuộc [checkin,checkout); không trùng ngày phòng bị chặn; phòng/rate plan/booking cùng hotel.
- Chỉ booking COMPLETED; overlap và ở trùng ngày ngừng bán là lỗi. Kênh có thể lọc đêm bán nhưng không tạo công suất theo kênh.
- Lookup dimension NORMAL theo namespace + BK và valid_from <= t < valid_to (NULL là vô hạn); đúng một phiên bản. Thiếu/trùng phiên bản -> quarantine dòng phụ thuộc, không lấy current thay thế.

### F04 FactTicketOrder

**Tên vật lý:** `fact_ticket_order`. **Grain:** Một đơn vé.

**PK:** `fact_key`. **UK:** `source_system, ticket_order_id`.

**Lịch sử:** FINAL_SNAPSHOT_RESTATEMENT. Merge theo natural key; tính lại tập grain bị ảnh hưởng khi correction. Không append revision như giao dịch mới.

| Cột | Kiểu | NULL | Vai trò và quy tắc | Cách tổng hợp |
|---|---|---|---|---|
| `fact_key` | KEY | Không | Khóa kỹ thuật từ registry theo natural key; không thay ràng buộc grain. | NONE |
| `source_system` | CODE | Không | Namespace định danh các ID nguồn trong dòng. | NONE |
| `ordered_date_key` | DATEKEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D01.date_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `cohort_departure_date_key` | DATEKEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D01.date_key. -1: dịch vụ độc lập không có booking_ref. | NONE |
| `service_site_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D02.site_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `booking_site_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D02.site_key. -1: dịch vụ độc lập không có booking_ref. | NONE |
| `referral_hotel_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D03.hotel_key. -1: dịch vụ độc lập không có booking_ref. | NONE |
| `ticket_channel_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D05.channel_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `booking_channel_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D05.channel_key. -1: dịch vụ độc lập không có booking_ref. | NONE |
| `customer_profile_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D07.customer_profile_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `centre_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D11.centre_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `ticket_order_id` | ID | Không | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Nguồn: `entertainment_ops.ticket_orders.ticket_order_id`. | NONE |
| `hotel_booking_ref` | ID | Có | Booking khách sạn khi bán liên kết; không có FK xuyên database. Nguồn: `entertainment_ops.ticket_orders.hotel_booking_ref`. | NONE |
| `gross_vnd` | MONEY | Không | Giá vé trước hoàn. Số nguyên VND; không dùng float cho tiền. Nguồn: `entertainment_ops.ticket_orders.gross_vnd`. | SUM |
| `refunded_vnd` | MONEY | Không | Phần đã hoàn. Số nguyên VND; không dùng float cho tiền. Nguồn: `entertainment_ops.ticket_orders.refunded_vnd`. | SUM |
| `net_ticket_vnd` | MONEY | Không | gross_vnd-refunded_vnd. | SUM |

Năm cột kiểm toán dùng chung được bổ sung theo mục trên.

**Ràng buộc và cách sử dụng:**

- Thời điểm chọn phiên bản dimension: ordered_date_key cho service_site/centre/customer/ticket_channel; booking_site/referral_hotel/booking_channel kế thừa phiên bản booking tương ứng F01.
- gross_vnd>=refunded_vnd>=0; net_ticket_vnd=gross_vnd-refunded_vnd.
- Tham chiếu booking có giá trị phải tồn tại; các khóa referral đồng loạt -1 khi không có booking_ref.
- B03 tổng riêng về booking. Không phân bổ giá đơn theo hoạt động nếu không có quy tắc. Đơn không ref là bán độc lập; vé UNUSED chưa hoàn vẫn là mua.
- Lookup dimension NORMAL theo namespace + BK và valid_from <= t < valid_to (NULL là vô hạn); đúng một phiên bản. Thiếu/trùng phiên bản -> quarantine dòng phụ thuộc, không lấy current thay thế.

### F05 FactRental

**Tên vật lý:** `fact_rental`. **Grain:** Một hợp đồng thuê một xe.

**PK:** `fact_key`. **UK:** `source_system, rental_id`.

**Lịch sử:** FINAL_SNAPSHOT_RESTATEMENT. Merge theo natural key; tính lại tập grain bị ảnh hưởng khi correction. Không append revision như giao dịch mới.

| Cột | Kiểu | NULL | Vai trò và quy tắc | Cách tổng hợp |
|---|---|---|---|---|
| `fact_key` | KEY | Không | Khóa kỹ thuật từ registry theo natural key; không thay ràng buộc grain. | NONE |
| `source_system` | CODE | Không | Namespace định danh các ID nguồn trong dòng. | NONE |
| `pickup_date_key` | DATEKEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D01.date_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `return_date_key` | DATEKEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D01.date_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `cohort_departure_date_key` | DATEKEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D01.date_key. -1: dịch vụ độc lập không có booking_ref. | NONE |
| `service_site_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D02.site_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `booking_site_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D02.site_key. -1: dịch vụ độc lập không có booking_ref. | NONE |
| `referral_hotel_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D03.hotel_key. -1: dịch vụ độc lập không có booking_ref. | NONE |
| `booking_channel_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D05.channel_key. -1: dịch vụ độc lập không có booking_ref. | NONE |
| `customer_profile_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D07.customer_profile_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `centre_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D11.centre_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `vehicle_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D13.vehicle_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `rental_id` | ID | Không | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Nguồn: `entertainment_ops.rentals.rental_id`. | NONE |
| `hotel_booking_ref` | ID | Có | Tham chiếu bán qua khách sạn. Nguồn: `entertainment_ops.rentals.hotel_booking_ref`. | NONE |
| `status` | TEXT | Không | COMPLETED hoặc CANCELLED. Nguồn: `entertainment_ops.rentals.status`. | NONE |
| `agreed_vnd` | MONEY | Không | Giá trị thỏa thuận. Số nguyên VND; không dùng float cho tiền. Nguồn: `entertainment_ops.rentals.agreed_vnd`. | SUM |

Năm cột kiểm toán dùng chung được bổ sung theo mục trên.

**Ràng buộc và cách sử dụng:**

- Thời điểm chọn phiên bản dimension: pickup_date_key cho service_site/centre/customer/vehicle; booking_site/referral_hotel/booking_channel kế thừa phiên bản booking tương ứng F01.
- status IN (COMPLETED,CANCELLED); pickup < return; agreed_vnd>=0.
- B03 chỉ dùng COMPLETED; không nhân agreed_vnd theo ngày xe.
- B03 chỉ COMPLETED; số tiền ghi một lần, không chép lên mỗi ngày xe. B05 lấy ngày từ F11, không cộng số hợp đồng thành ngày xe.
- Lookup dimension NORMAL theo namespace + BK và valid_from <= t < valid_to (NULL là vô hạn); đúng một phiên bản. Thiếu/trùng phiên bản -> quarantine dòng phụ thuộc, không lấy current thay thế.

### F06 FactBreakfastEntitlement

**Tên vật lý:** `fact_breakfast_entitlement`. **Grain:** Một quyền lợi phòng và ngày phục vụ.

**PK:** `fact_key`. **UK:** `source_system, entitlement_id`; `source_system, booking_room_id, service_date_key`.

**Lịch sử:** FINAL_SNAPSHOT_RESTATEMENT. Merge theo natural key; tính lại tập grain bị ảnh hưởng khi correction. Không append revision như giao dịch mới.

| Cột | Kiểu | NULL | Vai trò và quy tắc | Cách tổng hợp |
|---|---|---|---|---|
| `fact_key` | KEY | Không | Khóa kỹ thuật từ registry theo natural key; không thay ràng buộc grain. | NONE |
| `source_system` | CODE | Không | Namespace định danh các ID nguồn trong dòng. | NONE |
| `service_date_key` | DATEKEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D01.date_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `site_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D02.site_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `hotel_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D03.hotel_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `room_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D04.room_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `customer_profile_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D07.customer_profile_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `rate_plan_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D08.rate_plan_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `outlet_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D09.outlet_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `meal_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D10.meal_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `entitlement_id` | ID | Không | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Nguồn: `hotel_ops.breakfast_entitlements.entitlement_id`. | NONE |
| `booking_room_id` | ID | Không | Tham chiếu bản ghi booking_rooms trong cùng database. Nguồn: `hotel_ops.breakfast_entitlements.booking_room_id`. | NONE |
| `eligible_covers` | COUNT | Không | Suất được hưởng. Nguồn: `hotel_ops.breakfast_entitlements.eligible_covers`. | SUM |
| `redeemed_covers` | COUNT | Không | Suất thực dùng. Nguồn: `hotel_ops.breakfast_entitlements.redeemed_covers`. | SUM |

Năm cột kiểm toán dùng chung được bổ sung theo mục trên.

**Ràng buộc và cách sử dụng:**

- Thời điểm chọn phiên bản dimension: service_date_key tại 00:00 giờ Việt Nam.
- eligible_covers>=redeemed_covers>=0; booking COMPLETED; meal=BREAKFAST.
- Một booking_room/service_date duy nhất; đúng một RESTAURANT trong hotel; entitlement thuộc ngày phục vụ hợp lệ của lưu trú.
- Chỉ COMPLETED. Ánh xạ đúng một RESTAURANT mỗi khách sạn ở v2; nhiều hơn một phải báo lỗi thay vì chọn ngẫu nhiên.
- Lookup dimension NORMAL theo namespace + BK và valid_from <= t < valid_to (NULL là vô hạn); đúng một phiên bản. Thiếu/trùng phiên bản -> quarantine dòng phụ thuộc, không lấy current thay thế.

### F07 FactDiningOrder

**Tên vật lý:** `fact_dining_order`. **Grain:** Một hóa đơn ăn uống, không phải dòng món.

**PK:** `fact_key`. **UK:** `source_system, dining_order_id`.

**Lịch sử:** FINAL_SNAPSHOT_RESTATEMENT. Merge theo natural key; tính lại tập grain bị ảnh hưởng khi correction. Không append revision như giao dịch mới.

| Cột | Kiểu | NULL | Vai trò và quy tắc | Cách tổng hợp |
|---|---|---|---|---|
| `fact_key` | KEY | Không | Khóa kỹ thuật từ registry theo natural key; không thay ràng buộc grain. | NONE |
| `source_system` | CODE | Không | Namespace định danh các ID nguồn trong dòng. | NONE |
| `service_date_key` | DATEKEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D01.date_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `site_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D02.site_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `service_hotel_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D03.hotel_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `booking_hotel_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D03.hotel_key. -1: hóa đơn không gắn booking. | NONE |
| `customer_profile_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D07.customer_profile_key. 0: hóa đơn không xác định khách; không tự điền guest từ booking. | NONE |
| `outlet_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D09.outlet_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `meal_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D10.meal_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `dining_order_id` | ID | Không | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Nguồn: `hotel_ops.dining_orders.dining_order_id`. | NONE |
| `booking_id` | ID | Có | Tham chiếu bản ghi bookings trong cùng database. Nguồn: `hotel_ops.dining_orders.booking_id`. | NONE |
| `net_vnd` | MONEY | Không | Giá trị sau ưu đãi. Số nguyên VND; không dùng float cho tiền. Nguồn: `hotel_ops.dining_orders.net_vnd`. | SUM |
| `covers` | COUNT | Không | Số khách phục vụ. Nguồn: `hotel_ops.dining_orders.covers`. | SUM |
| `rating_sum` | COUNT | Không | rating nguồn trong 1..5; nguồn v2 bắt buộc có rating. Nguồn: `hotel_ops.dining_orders.rating`. | SUM |
| `rating_count` | COUNT | Không | 1 cho hóa đơn có rating hợp lệ; v2 luôn 1. | SUM |

Năm cột kiểm toán dùng chung được bổ sung theo mục trên.

**Ràng buộc và cách sử dụng:**

- Thời điểm chọn phiên bản dimension: service_date_key cho service_site/service_hotel/customer/outlet; booking_hotel kế thừa phiên bản booking tương ứng F01.
- net_vnd>=0; covers>=0; rating_sum BETWEEN 1 AND 5; rating_count=1.
- Không suy guest từ booking khi guest_id nguồn NULL; service_hotel lấy từ outlet, booking_hotel từ booking.
- Cơ sở phục vụ theo outlet, không theo booking. Rating có trọng số mỗi hóa đơn, không theo covers. Không có dimension món ăn từ schema hiện tại.
- Lookup dimension NORMAL theo namespace + BK và valid_from <= t < valid_to (NULL là vô hạn); đúng một phiên bản. Thiếu/trùng phiên bản -> quarantine dòng phụ thuộc, không lấy current thay thế.

### F08 FactMealSession

**Tên vật lý:** `fact_meal_session`. **Grain:** Một outlet, ngày và bữa buffet.

**PK:** `fact_key`. **UK:** `source_system, outlet_id, service_date_key, meal_key`; `source_system, session_id`.

**Lịch sử:** FINAL_SNAPSHOT_RESTATEMENT. Merge theo natural key; tính lại tập grain bị ảnh hưởng khi correction. Không append revision như giao dịch mới.

| Cột | Kiểu | NULL | Vai trò và quy tắc | Cách tổng hợp |
|---|---|---|---|---|
| `fact_key` | KEY | Không | Khóa kỹ thuật từ registry theo natural key; không thay ràng buộc grain. | NONE |
| `source_system` | CODE | Không | Namespace định danh các ID nguồn trong dòng. | NONE |
| `outlet_id` | ID | Không | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Nguồn: `hotel_ops.outlets.outlet_id`. | NONE |
| `service_date_key` | DATEKEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D01.date_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `site_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D02.site_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `hotel_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D03.hotel_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `outlet_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D09.outlet_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `meal_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D10.meal_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `session_id` | ID | Không | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Nguồn: `hotel_ops.meal_sessions.session_id`. | NONE |
| `actual_covers` | COUNT | Không | Tổng suất thực dùng. Nguồn: `hotel_ops.meal_sessions.actual_covers`. | SUM |
| `ingredient_cost_vnd` | MONEY | Không | Chi phí nguyên liệu phân bổ theo bữa; không phải chi phí tiêu thụ từng khách. Số nguyên VND; không dùng float cho tiền. Nguồn: `hotel_ops.meal_sessions.ingredient_cost_vnd`. | SUM |

Năm cột kiểm toán dùng chung được bổ sung theo mục trên.

**Ràng buộc và cách sử dụng:**

- Thời điểm chọn phiên bản dimension: service_date_key tại 00:00 giờ Việt Nam.
- meal IN (BREAKFAST,DINNER); actual_covers>=0; ingredient_cost_vnd>=0.
- Một outlet/ngày/bữa; không tự gộp hai session_id trùng grain.
- BREAKFAST/DINNER; không cộng actual_covers lần nữa vào B04.05. Không nối chi phí phiên với từng hóa đơn rồi SUM.
- Lookup dimension NORMAL theo namespace + BK và valid_from <= t < valid_to (NULL là vô hạn); đúng một phiên bản. Thiếu/trùng phiên bản -> quarantine dòng phụ thuộc, không lấy current thay thế.

### F09 FactAdmission

**Tên vật lý:** `fact_admission`. **Grain:** Một lượt admission thực tế.

**PK:** `fact_key`. **UK:** `source_system, admission_id`.

**Lịch sử:** FINAL_SNAPSHOT_RESTATEMENT. Merge theo natural key; tính lại tập grain bị ảnh hưởng khi correction. Không append revision như giao dịch mới.

| Cột | Kiểu | NULL | Vai trò và quy tắc | Cách tổng hợp |
|---|---|---|---|---|
| `fact_key` | KEY | Không | Khóa kỹ thuật từ registry theo natural key; không thay ràng buộc grain. | NONE |
| `source_system` | CODE | Không | Namespace định danh các ID nguồn trong dòng. | NONE |
| `admission_date_key` | DATEKEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D01.date_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `site_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D02.site_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `customer_profile_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D07.customer_profile_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `centre_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D11.centre_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `activity_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D12.activity_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `admission_id` | ID | Không | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Nguồn: `entertainment_ops.admissions.admission_id`. | NONE |
| `ticket_id` | ID | Không | Tham chiếu bản ghi tickets trong cùng database. Nguồn: `entertainment_ops.admissions.ticket_id`. | NONE |
| `entered_at_utc` | UTC | Không | Thời điểm vào thực tế. Múi giờ nguồn +07:00. Nguồn: `entertainment_ops.admissions.entered_at`. | NONE |
| `admission_count` | COUNT | Không | 1 cho mỗi admission, không phải một ticket. | SUM |

Năm cột kiểm toán dùng chung được bổ sung theo mục trên.

**Ràng buộc và cách sử dụng:**

- Thời điểm chọn phiên bản dimension: entered_at_utc chính xác, không chỉ ngày.
- Ngày vào lấy sau chuyển UTC sang Asia/Ho_Chi_Minh; không thay bằng valid_date.
- Activity và centre của ticket/order nhất quán; lượt vào ngày đóng cửa hoặc vượt capacity phải được kiểm tra.
- Không thay entered_at bằng valid_date hoặc chỉ nhận vé USED. Admission RESCHEDULED hợp lệ vẫn tính; vượt capacity/đóng cửa phải báo lỗi.
- Lookup dimension NORMAL theo namespace + BK và valid_from <= t < valid_to (NULL là vô hạn); đúng một phiên bản. Thiếu/trùng phiên bản -> quarantine dòng phụ thuộc, không lấy current thay thế.

### F10 FactActivityDay

**Tên vật lý:** `fact_activity_day`. **Grain:** Một hoạt động và ngày danh mục.

**PK:** `fact_key`. **UK:** `source_system, activity_id, date_key`.

**Lịch sử:** FINAL_SNAPSHOT_RESTATEMENT. Merge theo natural key; tính lại tập grain bị ảnh hưởng khi correction. Không append revision như giao dịch mới.

| Cột | Kiểu | NULL | Vai trò và quy tắc | Cách tổng hợp |
|---|---|---|---|---|
| `fact_key` | KEY | Không | Khóa kỹ thuật từ registry theo natural key; không thay ràng buộc grain. | NONE |
| `source_system` | CODE | Không | Namespace định danh các ID nguồn trong dòng. | NONE |
| `activity_id` | ID | Không | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Nguồn: `entertainment_ops.activities.activity_id`. | NONE |
| `date_key` | DATEKEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D01.date_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `site_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D02.site_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `centre_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D11.centre_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `activity_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D12.activity_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `nominal_capacity` | COUNT | Không | capacity_per_day của activity. Nguồn: `entertainment_ops.activities.capacity_per_day`. | SUM |
| `is_closed` | FLAG | Không | 1 nếu tồn tại closure cùng activity/date. | NONE |
| `available_capacity` | COUNT | Không | nominal_capacity*(1-is_closed). | SUM |

Năm cột kiểm toán dùng chung được bổ sung theo mục trên.

**Ràng buộc và cách sử dụng:**

- Thời điểm chọn phiên bản dimension: date_key tại 00:00 giờ Việt Nam.
- nominal_capacity>0; is_closed IN (0,1); available_capacity=nominal_capacity*(1-is_closed).
- Closure đóng trọn ngày; gộp nhiều lý do trước khi tính. Không có phân bổ capacity theo khách, kênh hoặc khách sạn giới thiệu.
- Lookup dimension NORMAL theo namespace + BK và valid_from <= t < valid_to (NULL là vô hạn); đúng một phiên bản. Thiếu/trùng phiên bản -> quarantine dòng phụ thuộc, không lấy current thay thế.

### F11 FactVehicleDay

**Tên vật lý:** `fact_vehicle_day`. **Grain:** Một xe và ngày danh mục.

**PK:** `fact_key`. **UK:** `source_system, vehicle_id, date_key`.

**Lịch sử:** FINAL_SNAPSHOT_RESTATEMENT. Merge theo natural key; tính lại tập grain bị ảnh hưởng khi correction. Không append revision như giao dịch mới.

| Cột | Kiểu | NULL | Vai trò và quy tắc | Cách tổng hợp |
|---|---|---|---|---|
| `fact_key` | KEY | Không | Khóa kỹ thuật từ registry theo natural key; không thay ràng buộc grain. | NONE |
| `source_system` | CODE | Không | Namespace định danh các ID nguồn trong dòng. | NONE |
| `vehicle_id` | ID | Không | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Nguồn: `entertainment_ops.vehicles.vehicle_id`. | NONE |
| `date_key` | DATEKEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D01.date_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `site_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D02.site_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `centre_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D11.centre_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `vehicle_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D13.vehicle_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `inventory_day` | FLAG | Không | 1 trong lịch công suất. | SUM |
| `maintenance_day` | FLAG | Không | 1 nếu thuộc union ngày bảo trì xe. | SUM |
| `available_day` | FLAG | Không | 1-maintenance_day. | SUM |
| `rented_day` | FLAG | Không | 1 nếu thuộc một rental COMPLETED. | SUM |

Năm cột kiểm toán dùng chung được bổ sung theo mục trên.

**Ràng buộc và cách sử dụng:**

- Thời điểm chọn phiên bản dimension: date_key tại 00:00 giờ Việt Nam.
- inventory_day=1; available_day=1-maintenance_day; rented_day<=available_day.
- Hai rental cùng vehicle-day là lỗi; không DISTINCT để che overlap.
- rented_day từ COMPLETED; overlap thuê hoặc thuê trong bảo trì là lỗi. Không chứa agreed_vnd nhân theo số ngày.
- Lookup dimension NORMAL theo namespace + BK và valid_from <= t < valid_to (NULL là vô hạn); đúng một phiên bản. Thiếu/trùng phiên bản -> quarantine dòng phụ thuộc, không lấy current thay thế.

### F12 FactPurchaseLine

**Tên vật lý:** `fact_purchase_line`. **Grain:** Một dòng đặt mua.

**PK:** `fact_key`. **UK:** `source_system, purchase_line_id`.

**Lịch sử:** FINAL_SNAPSHOT_RESTATEMENT. Merge theo natural key; tính lại tập grain bị ảnh hưởng khi correction. Không append revision như giao dịch mới.

| Cột | Kiểu | NULL | Vai trò và quy tắc | Cách tổng hợp |
|---|---|---|---|---|
| `fact_key` | KEY | Không | Khóa kỹ thuật từ registry theo natural key; không thay ràng buộc grain. | NONE |
| `source_system` | CODE | Không | Namespace định danh các ID nguồn trong dòng. | NONE |
| `ordered_date_key` | DATEKEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D01.date_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `expected_date_key` | DATEKEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D01.date_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `site_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D02.site_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `hotel_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D03.hotel_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `supplier_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D14.supplier_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `item_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D15.item_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `purchase_line_id` | ID | Không | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Nguồn: `hotel_ops.purchase_lines.purchase_line_id`. | NONE |
| `purchase_order_id` | ID | Không | Tham chiếu bản ghi purchase_orders trong cùng database. Nguồn: `hotel_ops.purchase_lines.purchase_order_id`. | NONE |
| `ordered_qty` | QTY | Không | Lượng đặt theo đơn vị chuẩn. Nguồn: `hotel_ops.purchase_lines.ordered_qty`. | SUM_SAME_UNIT |
| `unit_price_vnd` | MONEY | Không | Đơn giá thỏa thuận trên đơn vị chuẩn. Số nguyên VND; không dùng float cho tiền. Nguồn: `hotel_ops.purchase_lines.unit_price_vnd`. | NONE |

Năm cột kiểm toán dùng chung được bổ sung theo mục trên.

**Ràng buộc và cách sử dụng:**

- Thời điểm chọn phiên bản dimension: ordered_date_key tại 00:00 giờ Việt Nam.
- ordered_qty>0; unit_price_vnd>=0; ordered_date<=expected_date.
- B06 cohort theo expected_date và A; dòng chưa receipt vẫn tồn tại.
- Giữ dòng đến hạn không receipt. Ordered_qty tính một lần; không lặp theo từng lần giao. Mỗi A phải tổng lại receipt received_on<=A.
- Lookup dimension NORMAL theo namespace + BK và valid_from <= t < valid_to (NULL là vô hạn); đúng một phiên bản. Thiếu/trùng phiên bản -> quarantine dòng phụ thuộc, không lấy current thay thế.

### F13 FactReceipt

**Tên vật lý:** `fact_receipt`. **Grain:** Một lần nhận của một dòng đặt mua.

**PK:** `fact_key`. **UK:** `source_system, receipt_id`.

**Lịch sử:** FINAL_SNAPSHOT_RESTATEMENT. Merge theo natural key; tính lại tập grain bị ảnh hưởng khi correction. Không append revision như giao dịch mới.

| Cột | Kiểu | NULL | Vai trò và quy tắc | Cách tổng hợp |
|---|---|---|---|---|
| `fact_key` | KEY | Không | Khóa kỹ thuật từ registry theo natural key; không thay ràng buộc grain. | NONE |
| `source_system` | CODE | Không | Namespace định danh các ID nguồn trong dòng. | NONE |
| `received_date_key` | DATEKEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D01.date_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `expected_date_key` | DATEKEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D01.date_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `expires_date_key` | DATEKEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D01.date_key. 0: nguồn chưa cung cấp hạn dùng; không suy ra không hết hạn. | NONE |
| `site_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D02.site_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `hotel_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D03.hotel_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `supplier_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D14.supplier_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `item_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D15.item_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `receipt_id` | ID | Không | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Nguồn: `hotel_ops.receipts.receipt_id`. | NONE |
| `purchase_line_id` | ID | Không | Tham chiếu bản ghi purchase_lines trong cùng database. Nguồn: `hotel_ops.receipts.purchase_line_id`. | NONE |
| `accepted_qty` | QTY | Không | Lượng chấp nhận. Nguồn: `hotel_ops.receipts.accepted_qty`. | SUM_SAME_UNIT |
| `rejected_qty` | QTY | Không | Lượng từ chối. Nguồn: `hotel_ops.receipts.rejected_qty`. | SUM_SAME_UNIT |
| `late_accepted_qty` | QTY | Không | accepted_qty nếu received_date>expected_date, ngược lại 0. | SUM_SAME_UNIT |

Năm cột kiểm toán dùng chung được bổ sung theo mục trên.

**Ràng buộc và cách sử dụng:**

- Thời điểm chọn phiên bản dimension: received_date_key tại 00:00 giờ Việt Nam.
- accepted_qty>=0; rejected_qty>=0; late_accepted_qty IN (0,accepted_qty) theo ngày nhận/hẹn.
- Không cộng receipt feed bên ngoài; expires_on NULL là chưa biết hạn dùng (date_key=0).
- Feed ngoài là đối chiếu, không cộng thêm receipt. receipt_id cũng là định danh lô; rejected không nhập kho và không thành WASTE.
- Lookup dimension NORMAL theo namespace + BK và valid_from <= t < valid_to (NULL là vô hạn); đúng một phiên bản. Thiếu/trùng phiên bản -> quarantine dòng phụ thuộc, không lấy current thay thế.

### F14 FactStockMovement

**Tên vật lý:** `fact_stock_movement`. **Grain:** Một chuyển động của một lô tại khách sạn.

**PK:** `fact_key`. **UK:** `source_system, movement_id`.

**Lịch sử:** FINAL_SNAPSHOT_RESTATEMENT. Merge theo natural key; tính lại tập grain bị ảnh hưởng khi correction. Không append revision như giao dịch mới.

| Cột | Kiểu | NULL | Vai trò và quy tắc | Cách tổng hợp |
|---|---|---|---|---|
| `fact_key` | KEY | Không | Khóa kỹ thuật từ registry theo natural key; không thay ràng buộc grain. | NONE |
| `source_system` | CODE | Không | Namespace định danh các ID nguồn trong dòng. | NONE |
| `movement_date_key` | DATEKEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D01.date_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `site_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D02.site_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `hotel_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D03.hotel_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `supplier_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D14.supplier_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `item_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D15.item_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `movement_id` | ID | Không | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Nguồn: `hotel_ops.stock_movements.movement_id`. | NONE |
| `receipt_id` | ID | Không | Tham chiếu bản ghi receipts trong cùng database. Nguồn: `hotel_ops.stock_movements.receipt_id`. | NONE |
| `session_id` | ID | Có | Tham chiếu bản ghi meal_sessions trong cùng database. Nguồn: `hotel_ops.stock_movements.session_id`. | NONE |
| `movement_type` | TEXT | Không | IN, USE hoặc WASTE. Nguồn: `hotel_ops.stock_movements.movement_type`. | NONE |
| `usage_area` | TEXT | Không | BUFFET, KITCHEN_OTHER, HOUSEKEEPING hoặc WAREHOUSE. Nguồn: `hotel_ops.stock_movements.usage_area`. | NONE |
| `quantity` | QTY | Không | Số dương; chiều theo loại. Nguồn: `hotel_ops.stock_movements.quantity`. | SUM_SAME_UNIT |
| `signed_qty` | QTY | Không | +quantity nếu IN; -quantity nếu USE/WASTE. | SUM_SAME_UNIT |
| `in_qty` | QTY | Không | quantity nếu IN, ngược lại 0. | SUM_SAME_UNIT |
| `use_qty` | QTY | Không | quantity nếu USE, ngược lại 0. | SUM_SAME_UNIT |
| `waste_qty` | QTY | Không | quantity nếu WASTE, ngược lại 0. | SUM_SAME_UNIT |
| `unit_price_vnd` | MONEY | Không | Giá lô từ purchase_line của receipt. Nguồn: `hotel_ops.purchase_lines.unit_price_vnd`. | NONE |
| `movement_value_vnd` | VALUE | Không | quantity*unit_price_vnd; đây là trị tuyệt đối, lọc movement_type khi tính WASTE/IN. | SUM |

Năm cột kiểm toán dùng chung được bổ sung theo mục trên.

**Ràng buộc và cách sử dụng:**

- Thời điểm chọn phiên bản dimension: movement_date_key tại 00:00 giờ Việt Nam.
- movement_type IN (IN,USE,WASTE); quantity>=0; signed_qty=in_qty-use_qty-waste_qty.
- Hotel/item khớp lô receipt và purchase order; balance cộng dồn theo lô không âm.
- session_id optional; không suy usage_area thành dimension kho.
- Tồn đầu=sum trước S; cuối=sum trước E. Không có warehouse_id nên chưa tạo DimWarehouse vật lý. usage_area chỉ lọc lượng USE, không lọc tồn. session_id phục vụ drill-through có kiểm soát.
- Lookup dimension NORMAL theo namespace + BK và valid_from <= t < valid_to (NULL là vô hạn); đúng một phiên bản. Thiếu/trùng phiên bản -> quarantine dòng phụ thuộc, không lấy current thay thế.

### F15 AggInventoryLotDay

**Tên vật lý:** `agg_inventory_lot_day`. **Grain:** Một lô, khách sạn, mặt hàng và ngày cuối ngày.

**PK:** `fact_key`. **UK:** `source_system, receipt_id, hotel_id, item_id, snapshot_date_key`.

**Lịch sử:** FINAL_SNAPSHOT_RESTATEMENT. Merge theo natural key; tính lại tập grain bị ảnh hưởng khi correction. Không append revision như giao dịch mới.

| Cột | Kiểu | NULL | Vai trò và quy tắc | Cách tổng hợp |
|---|---|---|---|---|
| `fact_key` | KEY | Không | Khóa kỹ thuật từ registry theo natural key; không thay ràng buộc grain. | NONE |
| `source_system` | CODE | Không | Namespace định danh các ID nguồn trong dòng. | NONE |
| `hotel_id` | ID | Không | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Nguồn: `hotel_ops.hotels.hotel_id`. | NONE |
| `item_id` | ID | Không | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Nguồn: `hotel_ops.items.item_id`. | NONE |
| `snapshot_date_key` | DATEKEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D01.date_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `site_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D02.site_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `hotel_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D03.hotel_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `supplier_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D14.supplier_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `item_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D15.item_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `receipt_id` | ID | Không | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Nguồn: `hotel_ops.receipts.receipt_id`. | NONE |
| `closing_qty` | QTY | Không | SUM signed_qty tới hết snapshot_date. | SEMI_ADDITIVE_DATE_SAME_UNIT |
| `closing_value_vnd` | VALUE | Không | closing_qty*giá lô. | SEMI_ADDITIVE_DATE |
| `in_qty` | QTY | Không | Lượng của loại tương ứng trong đúng snapshot_date. | SUM_SAME_UNIT |
| `use_qty` | QTY | Không | Lượng của loại tương ứng trong đúng snapshot_date. | SUM_SAME_UNIT |
| `waste_qty` | QTY | Không | Lượng của loại tương ứng trong đúng snapshot_date. | SUM_SAME_UNIT |

Năm cột kiểm toán dùng chung được bổ sung theo mục trên.

**Ràng buộc và cách sử dụng:**

- Thời điểm chọn phiên bản dimension: snapshot_date_key tại 00:00 giờ Việt Nam; số dư đo cuối ngày, phân loại danh mục tại đầu ngày.
- closing_qty>=0; cuối ngày d=cuối ngày d-1+in_qty-use_qty-waste_qty.
- Giữ lô còn tồn cả ngày không biến động; không SUM số dư qua ngày hoặc cộng F14+F15.
- Tùy chọn vật hóa từ F14. Không cộng closing qua ngày; đầu kỳ lấy cuối ngày trước S hoặc lịch sử F14. Giữ lô còn tồn dù không có movement trong kỳ. Không cộng F14 và F15.
- Lookup dimension NORMAL theo namespace + BK và valid_from <= t < valid_to (NULL là vô hạn); đúng một phiên bản. Thiếu/trùng phiên bản -> quarantine dòng phụ thuộc, không lấy current thay thế.

### F16 FactMaintenanceWork

**Tên vật lý:** `fact_maintenance_work`. **Grain:** Một công việc bảo trì tài sản khách sạn.

**PK:** `fact_key`. **UK:** `source_system, maintenance_id`.

**Lịch sử:** FINAL_SNAPSHOT_RESTATEMENT. Merge theo natural key; tính lại tập grain bị ảnh hưởng khi correction. Không append revision như giao dịch mới.

| Cột | Kiểu | NULL | Vai trò và quy tắc | Cách tổng hợp |
|---|---|---|---|---|
| `fact_key` | KEY | Không | Khóa kỹ thuật từ registry theo natural key; không thay ràng buộc grain. | NONE |
| `source_system` | CODE | Không | Namespace định danh các ID nguồn trong dòng. | NONE |
| `start_date_key` | DATEKEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D01.date_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `end_date_key` | DATEKEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D01.date_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `site_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D02.site_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `hotel_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D03.hotel_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `room_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D04.room_key. -1: asset ở khu chung, không gắn phòng. | NONE |
| `asset_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D16.asset_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `maintenance_id` | ID | Không | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Nguồn: `hotel_ops.maintenance.maintenance_id`. | NONE |
| `work_type` | TEXT | Không | PLANNED hoặc BREAKDOWN. Nguồn: `hotel_ops.maintenance.work_type`. | NONE |
| `status` | TEXT | Không | COMPLETED. Nguồn: `hotel_ops.maintenance.status`. | NONE |
| `cost_vnd` | MONEY | Không | Chi phí ghi nhận của công việc. Số nguyên VND; không dùng float cho tiền. Nguồn: `hotel_ops.maintenance.cost_vnd`. | SUM |

Năm cột kiểm toán dùng chung được bổ sung theo mục trên.

**Ràng buộc và cách sử dụng:**

- Thời điểm chọn phiên bản dimension: start_date_key tại 00:00 giờ Việt Nam; ngày ghi nhận KPI chi phí vẫn là end_date_key.
- start_date<end_date; cost_vnd>=0; work_type IN (BREAKDOWN,PLANNED); v2 status=COMPLETED.
- KPI chi phí lấy COMPLETED theo end_date; room_key=-1 cho tài sản không thuộc phòng.
- Tiền ghi một lần, không nhân theo ngày. Supplier của asset là bên bán tài sản, không coi là vendor bảo trì. Ngày chặn phòng dùng F02 và bridge overlap.
- Lookup dimension NORMAL theo namespace + BK và valid_from <= t < valid_to (NULL là vô hạn); đúng một phiên bản. Thiếu/trùng phiên bản -> quarantine dòng phụ thuộc, không lấy current thay thế.

### F17 FactWeatherDay

**Tên vật lý:** `fact_weather_day`. **Grain:** Một cụm và ngày thời tiết.

**PK:** `fact_key`. **UK:** `source_system, site_id, weather_date_key`; `source_system, weather_id`.

**Lịch sử:** FINAL_SNAPSHOT_RESTATEMENT. Merge theo natural key; tính lại tập grain bị ảnh hưởng khi correction. Không append revision như giao dịch mới.

| Cột | Kiểu | NULL | Vai trò và quy tắc | Cách tổng hợp |
|---|---|---|---|---|
| `fact_key` | KEY | Không | Khóa kỹ thuật từ registry theo natural key; không thay ràng buộc grain. | NONE |
| `source_system` | CODE | Không | Namespace định danh các ID nguồn trong dòng. | NONE |
| `site_id` | ID | Không | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Nguồn: `hotel_ops.sites.site_id`. | NONE |
| `weather_date_key` | DATEKEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D01.date_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `site_key` | KEY | Không | Vai trò dimension theo sơ đồ đã chốt. FK → D02.site_key. Không cho khóa đặc biệt trên dữ liệu công bố. | NONE |
| `weather_id` | ID | Không | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Nguồn: `hotel_ops.weather_daily.weather_id`. | NONE |
| `provenance` | TEXT | Không | SYNTHETIC_CLIMATE_SCENARIO, không phải quan trắc thật. Nguồn: `hotel_ops.weather_daily.provenance`. | NONE |
| `temperature_c` | INT | Không | Nhiệt độ giả lập theo cụm/ngày. Nguồn: `hotel_ops.weather_daily.temperature_c`. | AVG_SITE_DAY |
| `rain_mm` | INT | Không | Lượng mưa ngày; chỉ cộng qua ngày trong cùng site. Nguồn: `hotel_ops.weather_daily.rain_mm`. | SUM_DATE_WITHIN_SITE |
| `severe_weather` | FLAG | Không | Cờ thời tiết cực đoan; dùng lọc, không cộng như lượng mưa. Nguồn: `hotel_ops.weather_daily.severe_weather`. | NONE |

Năm cột kiểm toán dùng chung được bổ sung theo mục trên.

**Ràng buộc và cách sử dụng:**

- Thời điểm chọn phiên bản dimension: weather_date_key tại 00:00 giờ Việt Nam.
- Duy nhất site/date trước join; rain_mm>=0; severe_weather IN (0,1).
- Không SUM nhiệt độ hoặc nhân bản weather khi join admission.
- Ngữ cảnh B05. Nối 1:1 site/date sau khi xác minh duy nhất hoặc semijoin bộ ngày; không nhân thời tiết theo admission rồi lấy SUM. Không kết luận nhân quả.
- Lookup dimension NORMAL theo namespace + BK và valid_from <= t < valid_to (NULL là vô hạn); đúng một phiên bản. Thiếu/trùng phiên bản -> quarantine dòng phụ thuộc, không lấy current thay thế.

### L01 BridgeBookingRoom

**Tên vật lý:** `bridge_booking_room`. **Grain:** Một booking_room_id trong hotel_ops.

**PK:** `source_system, booking_room_id`. **UK:** `source_system, booking_room_id`.

**Lịch sử:** CURRENT_VALIDATED_LINK. Tạo lại hoặc merge theo khóa từ cùng batch nguồn.

| Cột | Kiểu | NULL | Vai trò và quy tắc | Cách tổng hợp |
|---|---|---|---|---|
| `source_system` | CODE | Không | hotel_ops | NONE |
| `booking_room_id` | ID | Không | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Nguồn: `hotel_ops.booking_rooms.booking_room_id`. | NONE |
| `booking_id` | ID | Không | Tham chiếu bản ghi bookings trong cùng database. Nguồn: `hotel_ops.booking_rooms.booking_id`. | NONE |
| `room_key` | KEY | Không | Phòng của dòng booking. FK → D04.room_key. | NONE |
| `rate_plan_key` | KEY | Không | Gói giá của dòng booking. FK → D08.rate_plan_key. | NONE |

Năm cột kiểm toán dùng chung được bổ sung theo mục trên.

**Ràng buộc và cách sử dụng:**

- Thời điểm chọn phiên bản dimension: bookings.booked_on của booking liên quan, thống nhất F01.
- booking_id tồn tại ở booking nguồn; room và rate plan cùng hotel với booking.
- Dùng EXISTS hoặc COUNTD; không mang tiền booking và không cấp allocation weight.

### L02 BridgeRoomDayMaintenance

**Tên vật lý:** `bridge_room_day_maintenance`. **Grain:** Một phòng/ngày/công việc bảo trì.

**PK:** `source_system, room_id, date_key, maintenance_id`. **UK:** `source_system, room_id, date_key, maintenance_id`.

**Lịch sử:** CURRENT_VALIDATED_LINK. Tạo lại hoặc merge theo khóa từ cùng batch nguồn.

| Cột | Kiểu | NULL | Vai trò và quy tắc | Cách tổng hợp |
|---|---|---|---|---|
| `source_system` | CODE | Không | hotel_ops | NONE |
| `maintenance_id` | ID | Không | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Nguồn: `hotel_ops.maintenance.maintenance_id`. | NONE |
| `room_id` | ID | Không | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Nguồn: `hotel_ops.rooms.room_id`. | NONE |
| `room_key` | KEY | Không | Phòng chịu ảnh hưởng. FK → D04.room_key. | NONE |
| `date_key` | DATEKEY | Không | Ngày trong [starts_on,ends_on). FK → D01.date_key. | NONE |

Năm cột kiểm toán dùng chung được bổ sung theo mục trên.

**Ràng buộc và cách sử dụng:**

- Thời điểm chọn phiên bản dimension: date_key tại 00:00 giờ Việt Nam, thống nhất F02.
- Chỉ asset có room; mỗi cặp room/date/work đúng một lần.
- F02 dùng EXISTS trên room/date; không SUM cost qua bridge.

### L03 ValidatedBookingServiceLink

**Tên vật lý:** `validated_booking_service_link`. **Grain:** Một service_type/service_id có booking_ref hợp lệ.

**PK:** `service_source_system, service_type, service_id`. **UK:** `service_source_system, service_type, service_id`.

**Lịch sử:** CURRENT_VALIDATED_LINK. Tạo lại hoặc merge theo khóa từ cùng batch nguồn.

| Cột | Kiểu | NULL | Vai trò và quy tắc | Cách tổng hợp |
|---|---|---|---|---|
| `service_source_system` | CODE | Không | entertainment_ops | NONE |
| `service_type` | CODE | Không | TICKET_ORDER hoặc RENTAL | NONE |
| `service_id` | ID | Không | ID ticket_order hoặc rental. | NONE |
| `booking_source_system` | CODE | Không | hotel_ops | NONE |
| `booking_id` | ID | Không | Booking đích đã kiểm chứng. | NONE |

Năm cột kiểm toán dùng chung được bổ sung theo mục trên.

**Ràng buộc và cách sử dụng:**

- Mỗi dịch vụ tối đa một booking; thiếu ref không có dòng link; ref có giá trị nhưng sai đưa quarantine.
- Kiểm chứng tồn tại ref độc lập với eligibility B03; cohort B03 tiếp tục lọc booking COMPLETED.

### L04 SiteCrosswalk

**Tên vật lý:** `site_crosswalk`. **Grain:** Một centre ánh xạ đúng một site.

**PK:** `centre_source_system, centre_id`. **UK:** `centre_source_system, centre_id`.

**Lịch sử:** CURRENT_VALIDATED_LINK. Tạo lại hoặc merge theo khóa từ cùng batch nguồn.

| Cột | Kiểu | NULL | Vai trò và quy tắc | Cách tổng hợp |
|---|---|---|---|---|
| `centre_source_system` | CODE | Không | entertainment_ops | NONE |
| `centre_id` | ID | Không | Mã định danh trong hệ thống nguồn; không phải mã khách toàn doanh nghiệp. Nguồn: `entertainment_ops.centres.centre_id`. | NONE |
| `site_source_system` | CODE | Không | hotel_ops | NONE |
| `site_id` | ID | Không | centres.site_code trùng sites.site_id. Nguồn: `entertainment_ops.centres.site_code`, `hotel_ops.sites.site_id`. | NONE |

Năm cột kiểm toán dùng chung được bổ sung theo mục trên.

**Ràng buộc và cách sử dụng:**

- Không yêu cầu một site chỉ có một centre bằng UNIQUE; bốn centre/bốn site là dữ liệu case.
- Không suy ánh xạ bằng vị trí hoặc tên gần giống.

## Thay đổi dữ liệu và quản lý công bố

Dự kiến tách metadata vận hành khỏi mô hình nghiệp vụ. Các cấu trúc dưới đây là hợp đồng tối thiểu, chưa phải bảng đã triển khai.

| Cấu trúc | Khóa và dữ liệu bắt buộc | Mục đích |
|---|---|---|
| KeyRegistry | PK entity_id + canonical_natural_key; UK entity_id + surrogate_key; first_batch_id | Giữ khóa ổn định và giống nhau ở hai nhánh. |
| BatchManifest | PK batch_id; source_manifest_sha256; source_cutoff; observed_at_utc; contract_version; transform_version; key_registry_sha256; status; started_at_utc; completed_at_utc | Status COMPLETE, PARTIAL hoặc FAILED; observed_at dùng ổn định khi replay SCD2. |
| TablePublication | PK batch_id + branch + entity_id; location; snapshot_or_version; row_count; logical_payload_sha256; check_status | Chỉ cho công bố khi đủ tập bảng trong cùng batch. |
| QuarantineRecord | PK batch_id + entity_id + source_record_key + rule_id; source_path; payload; reason; retry_status | Giữ lỗi để sửa và chạy lại; không sửa âm thầm dữ liệu. |
| ValidationResult | PK batch_id + branch + rule_id + scope_key; expected; actual; status | Bằng chứng kiểm tra từng bước và đối chiếu hai nhánh. |
| QualityCoverage | PK batch_id + branch + entity_id + scope_key; input_count; accepted_count; quarantined_count; dependency_excluded_count; expected_count nullable; completeness_status | Số lượng phần hợp lệ và phần thiếu, không cộng chồng nhóm loại. |
| MetricQualityStatus | PK batch_id + branch + metric_id + scope_key; quality_status; affected_entities; reason; completeness nullable | COMPLETE, PARTIAL hoặc UNAVAILABLE; Power BI/web nhận cùng số KPI. |

Batch PARTIAL được công bố khi phần hợp lệ thỏa grain, FK và quy tắc nghiệp vụ, đồng thời có metadata mô tả phần thiếu. Không yêu cầu toàn bộ input sạch trước khi xuất report. Phần không xác định được chất lượng hiển thị UNAVAILABLE, không ép bằng 0; không coi PARTIAL là COMPLETE. So sánh hai nhánh dùng cùng natural key, accepted/excluded set và metadata chất lượng; bỏ thời gian ETL và layout vật lý.

## Kiểm chứng thiết kế và giới hạn

Script đã kiểm tra 37 entity, 631 cột gồm cột audit, 102 FK từ fact tới dimension và 47 ánh xạ KPI. Kiểm tra độ dài chuỗi trên dữ liệu nguồn và tính duy nhất của ba grain chưa có UNIQUE trong DB: quyền lợi sáng theo phòng/ngày, phiên buffet theo outlet/ngày/bữa, thời tiết theo site/ngày.

Các kiểm tra này xác minh đặc tả và khả năng chứa dữ liệu nguồn; chưa chứng minh ETL đúng, DDL chạy được trên phiên bản được chọn hoặc KPI hai nhánh bằng nhau. Hợp đồng JSON có source_references để truy vết cột, nhưng mapping ETL đầy đủ gồm join path, điều kiện lọc, thứ tự nạp và biểu thức SQL là bước 2.

Mã nguồn và seed sinh dữ liệu, schema nguồn, KPI contract và mô hình sơ đồ v1 được kiểm tra hash không đổi. Những bản v1 là baseline trước quyết định mới: đặc tả 1.1 này thay thế ghi chú Type 1 bằng SCD2 và bổ sung khóa grain dùng ID bền vững. Các sơ đồ giữ bố cục và quan hệ nhưng chưa vẽ các cột SCD2 mới. Công thức 47 KPI không đổi; chính sách PARTIAL ở đây thay thế ghi chú chặn chỉ tiêu khi nguồn lỗi trong đặc tả KPI cũ.

## Cách tái tạo

Chạy từ thư mục Project:

```powershell
python -X utf8 scripts/build-warehouse-design.py
```

Đầu ra: `config/warehouse_design_v1.json`, `docs/CompanyE_Warehouse_Detailed_Design.md`, `reports/warehouse_design_v1_validation.json`. Quyết định nghiệp vụ lưu riêng tại `config/warehouse_design_decisions_v1.json`; chạy lại không ghi đè quyết định đã có.
