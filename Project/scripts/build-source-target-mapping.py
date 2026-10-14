"""Generate and validate source-to-target engineering specifications.

This is a specification builder, not production Spark/Oracle ETL.
All input datasets and prior contracts are read only.
"""
from pathlib import Path
from datetime import date, timedelta, datetime, timezone
from decimal import Decimal
import hashlib
import csv
import json
import re

ROOT=Path(__file__).resolve().parents[1]
def read(p): return json.loads((ROOT/p).read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def save(p,obj): (ROOT/p).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
INPUTS=['config/warehouse_design_v1.json','config/warehouse_design_decisions_v1.json',
        'config/kpi_contract_v1.json','config/dimensional_model_v1.json','config/generation_v2.json',
        'generated/v2/contracts.json','lake/v2/catalog/catalog.json','src/generate.py','src/generate_v2.py',
        'generated/v2/hotel_ops/stays.csv','generated/v2/hotel_ops/breakfast_entitlements.csv',
        'src/model.py','src/model_v2.py','src/lake_job.py','src/lake_v2.py']
HASHES={p:sha(p) for p in INPUTS}
design=read(INPUTS[0]); contracts=read('generated/v2/contracts.json'); catalog=read('lake/v2/catalog/catalog.json')
source={f'{ns}.{t["name"]}.{c["name"]}':c for ns,ts in contracts.items() for t in ts for c in t['columns']}
source_tables={f'{ns}.{t["name"]}':t for ns,ts in contracts.items() for t in ts}
targets={t['id']:t for t in design['tables']}
RULES=[]
def rule(id,title,explanation,steps,example):
    RULES.append(dict(id=id,title=title,explanation=explanation,steps=steps,example=example))

rule('R01','Chọn snapshot và truy vết nguồn',
 'Đầu vào ETL phân tích là các bảng Parquet standardized của lake v2 được catalog chỉ rõ. Không đọc ngẫu nhiên file mới nhất và không trộn nguồn ở hai cutoff khác nhau. Mỗi lần chạy cần phân biệt source_batch_id với run_id kỹ thuật để replay cùng input không tạo giao dịch mới.',
 ['Đọc catalog và manifest; xác minh batch, phiên bản schema và hash; phân loại nguồn sẵn có, thiếu toàn bảng hoặc không tin cậy.',
  'Đóng băng danh sách input path, cutoff, code version và key registry version trước xử lý. Catalog hiện tại là bằng chứng snapshot, không phải đường dẫn cố định cho mọi batch sau.',
  'Chỉ đọc cột đã được khai báo. Metadata lake như _ingestion_batch dùng kiểm tra lineage, không là cột nghiệp vụ để tính KPI. Tuyệt đối không đọc audit_only/identity truth.',
  'Nguồn thiếu có thể làm báo cáo PARTIAL/UNAVAILABLE theo phạm vi; input không đủ nhận diện hoặc checksum sai phải được đánh dấu không tin cậy, không thay bằng một bảng rỗng đã kiểm chứng.'],
 'Hotel snapshot A và entertainment snapshot B không được ghép rồi gắn nhãn cùng batch A. Publication manifest ghi rõ bộ input được chọn cho cả hai nhánh.')
rule('R02','Chuẩn hóa giá trị và kiểu dữ liệu',
 'Chuẩn hóa phục vụ tương đương giữa Oracle và Iceberg, không sửa lại ý nghĩa nguồn. Dữ liệu tiền, lượng và mã phải giữ độ chính xác; chuẩn hóa mạnh có thể làm hai đối tượng khác nhau bị gộp.',
 ['CSV raw dùng token \\N cho NULL; lớp standardized đã có NULL thực. Chuỗi rỗng được coi là NULL chung ở biên ETL; không thay chuỗi mã có nội dung bằng uppercase hoặc trim rồi coi là mã khác.',
  'Mã bắt buộc NULL hoặc toàn khoảng trắng bị quarantine. Chuỗi vượt giới hạn đích bị quarantine, không cắt ngắn. Email/phone giữ nguyên, không dùng để hợp nhất khách.',
  'Dùng DECIMAL chính xác cho VND/lượng. Parse thất bại, số lẻ ở cột nguyên, vượt precision/scale hoặc miền giá trị đều tạo lỗi. Không COALESCE số tiền bắt buộc về 0.',
  'Kiểm tra row-level trước lookup; sai tham chiếu có nội dung khác với NULL được phép. Giữ payload nguồn và mã lỗi để chạy lại.'],
 'quantity=1.250 được giữ là DECIMAL với ba số lẻ; quantity=1.2504 không bị âm thầm làm tròn thành 1.250. promotion_id=NULL hợp lệ; promotion_id=P999 không tồn tại là lỗi.')
rule('R03','Ngày nghiệp vụ và khoảng thời gian',
 'Ngày nguồn DATE là ngày địa phương đã xác định, không dịch thêm múi giờ. Timestamp có offset được chuẩn hóa UTC để lưu, rồi chuyển Asia/Ho_Chi_Minh trước khi lấy ngày báo cáo. Khoảng lưu trú, thuê xe và bảo trì đều gồm đầu, loại cuối.',
 ['DATEKEY(d)=year(d)*10000+month(d)*100+day(d), phải lookup được DimDate. Timestamp không có offset khi contract yêu cầu TIMESTAMPTZ là lỗi, không đoán timezone.',
  'LOCAL_START(d) là d 00:00:00 tại +07:00 chuyển UTC, dùng lookup SCD cho nguồn chỉ có ngày. Admission dùng entered_at chính xác.',
  'EXPAND(start,end) sinh mỗi ngày start <= d < end; end <= start là lỗi. Kỳ công suất v2 [2024-01-01,2026-01-01); không dùng toàn DimDate làm lịch công suất.',
  'DimDate phủ các năm từ min đến max ngày nguồn hợp lệ: hiện 2023–2026. Ngày hạn dùng hoặc booked_on ngoài kỳ công suất vẫn cần thành viên Date; không tự tạo công suất ngoài kỳ.'],
 'Check-in 30/01, check-out 02/02 tạo 30/01,31/01,01/02. Admission 2024-01-01T18:30Z thuộc ngày 02/01/2024 tại Việt Nam.')
rule('R04','Nhận diện trùng lặp và lỗi join',
 'Cần phân biệt replay cùng sự kiện, trùng khóa nhưng khác nội dung và nhiều dòng hợp lệ ở grain khác nhau. DISTINCT toàn bảng hoặc lấy first/last không có quy tắc có thể che lỗi nghiệp vụ.',
 ['Mỗi input structured snapshot có PK duy nhất. Hai dòng cùng PK khác payload: quarantine cả nhóm; không chọn bên thắng bằng thời điểm đọc file.',
  'Replay cùng PK và payload chỉ được loại khi có bằng chứng delivery/ingestion; ghi discarded_replay riêng, không tính là quarantine hoặc giao dịch thêm.',
  'Join many-to-one phải kiểm tra số parent trước khi join. Parent count=0 với FK bắt buộc: dependency_excluded; >1: ambiguous_join, loại các dòng phụ thuộc.',
  'LEFT OPTIONAL: nếu child FK NULL thì xử lý special member; nếu FK có giá trị nhưng parent không tìm thấy thì lỗi. Không dùng INNER JOIN làm mất dòng mà không ghi nhận số lượng.'],
 'Một purchase_line có ba receipts là quan hệ 1:N hợp lệ; join rồi SUM ordered_qty là sai vì nhân lượng đặt lên ba lần.')
rule('R05','Khóa bền vững và thành viên đặc biệt',
 'Business key có namespace nhận diện đối tượng; surrogate key SCD nhận diện một phiên bản. Khóa fact phải bền vững khi phiên bản dimension thay đổi để replay và correction không tạo thêm dòng.',
 ['Đăng ký key registry dùng chung hai nhánh bằng canonical JSON array có thứ tự. Fact dùng unique_keys đầu tiên trong đặc tả; SCD dimension dùng namespace/BK/valid_from_utc.',
  'Không nối text bằng dấu phân cách tùy ý và không dùng ROW_NUMBER tái đánh số mỗi batch. Date dùng YYYYMMDD; Meal BREAKFAST/LUNCH/DINNER/BAR lần lượt 1/2/3/4.',
  'Mỗi dimension có key 0 UNKNOWN và -1 NOT_APPLICABLE. Những dòng này không tạo phiên bản mới; với SCD: version=1/current=1/valid_to=NULL, thời điểm khởi tạo giống bootstrap.',
  'FK có nội dung sai không được đổi thành special member. Dimension thuộc tính không biết có thể NULL nếu contract cho phép; không tự bịa tên, mã hay ngày 1900.'],
 'Hóa đơn walk-in không biết guest -> customer_profile_key=0. Booking không promotion -> promotion_key=-1. Receipt chưa biết expires_on -> expires_date_key=0.')
rule('R06','Khởi tạo SCD Type 2 trên dữ liệu giản lược',
 'CompanyE chọn SCD2 để hỗ trợ thay đổi thực tế, nhưng v2 chỉ có snapshot danh mục. Lần nạp đầu không chứng minh lịch sử thực; phải ghi rõ giả định mô phỏng. Các dimension nghiệp vụ dùng SCD2, riêng Date và Meal cố định.',
 ['Lần đầu mỗi BK hợp lệ tạo một phiên bản. valid_from_utc=2022-12-31T17:00:00Z, tương ứng 01/01/2023 00:00 Việt Nam; valid_to=NULL, is_current=1, version_no=1.',
  'effective_time_basis=BOOTSTRAP_ASSUMPTION; không lấy created_at ETL năm 2026 làm ngày bắt đầu vì sẽ không lookup được fact năm 2024.',
  'Giả định này chỉ áp cho snapshot v2 hiện tại. BK lần đầu xuất hiện ở batch tương lai dùng thời điểm hiệu lực/quan sát của batch đó, không tự lùi về 2023.',
  'Nếu nguồn có nghiệp vụ trước mốc bootstrap hoặc danh mục mở/đóng giữa kỳ, phải sửa hợp đồng phạm vi; không mở rộng giả định âm thầm.'],
 'Room R1 có một dòng version=1 bao phủ các đêm v2; không tạo hai phiên bản giống hệt chỉ để minh họa SCD2.')
rule('R07','Cập nhật và lookup phiên bản SCD2',
 'Payload hash của dimension chỉ gồm tracked_attributes đã khai báo. Đổi thuộc tính mới tạo phiên bản, còn việc đọc lại cùng dữ liệu không tạo thay đổi. Cần xét lịch sử có hiệu lực, không chỉ cờ is_current.',
 ['Từ manifest lấy effective timestamp đáng tin nếu nguồn có; nếu không, dùng observed_at_utc đã đóng băng và basis=OBSERVED_AT. Không lấy thời gian chạy lại làm effective time mới.',
  'Nếu payload không đổi tại thời điểm tương ứng: no-op. Nếu đổi ở thời điểm t sau phiên bản hiện tại: đóng old.valid_to=t, old.current=0; mở new.valid_from=t với SK khác. Một BK tối đa một current, intervals không chồng.',
  'Sự kiện đến muộn vào một interval cũ: dựng lại các ranh giới theo effective time trong candidate, split interval đúng chỗ, không làm mất thay đổi tương lai đã biết. Cùng BK và cùng effective time khác payload là conflict; quarantine tới khi có quy tắc correction đáng tin.',
  'version_no là thứ tự theo valid_from; khi chèn lịch sử có thể cần đánh lại ordinal trong candidate. SK bền vững theo BK+valid_from, không theo version_no. Nếu ranh giới đổi thì cấp SK mới và rekey các fact bị ảnh hưởng; giữ registry cũ để audit.',
  'LOOKUP_SCD yêu cầu đúng một interval valid_from<=t và (valid_to IS NULL hoặc t<valid_to). Không có hoặc nhiều interval -> loại dòng phụ thuộc và báo thiếu. Không tự lấy current.',
  'Close/open, rekey và metadata quality phải được công bố cùng bộ snapshot. Thiết kế không giả định transaction đa bảng của Iceberg.'],
 'Standard hiệu lực trước 01/07, Deluxe từ 01/07: giao dịch đúng 00:00 ngày 01/07 nối Deluxe. A->B->A tạo ba phiên bản khác SK; replay cùng sự kiện B không tạo phiên bản thứ tư.')
rule('R08','Lọc nghiệp vụ khác với loại dữ liệu lỗi',
 'Fact có thể giữ nhiều trạng thái để dùng cho các KPI khác nhau. Bộ lọc KPI không nhất thiết là bộ lọc khi nạp fact. Dòng không thuộc nghiệp vụ được ghi not_applicable, không gọi là dữ liệu thiếu.',
 ['F01 giữ COMPLETED/CANCELLED/NO_SHOW. Chỉ B02 và cohort B03 lọc COMPLETED; B01.04–05 giữ cả ba trạng thái trong mẫu số.',
  'F05 giữ rental COMPLETED/CANCELLED. F11 chỉ mở rộng COMPLETED; F03 và F06 chỉ từ booking COMPLETED. Các bộ lọc này là loại theo nghiệp vụ, không quarantine.',
  'Admission có chứng cứ vào thực tế vẫn tính kể cả ticket RESCHEDULED; không lọc chỉ USED. Ticket status khác không tự xóa admission; vi phạm đóng cửa/capacity được kiểm tra riêng.',
  'Một bảng nguồn rỗng đã xác nhận đầy đủ khác với bảng không nhận được. Không có sự kiện hợp lệ trong nguồn đầy đủ có thể suy 0, nguồn thiếu hoặc có sự kiện bị loại chỉ cho kết quả partial.'],
 'Booking CANCELLED vẫn cần cho tỷ lệ hủy, nhưng không tạo đêm ở và không cộng tiền B02. Đây không phải một booking bị lỗi.')
rule('R09','Tiền giao dịch và chống nhân bản',
 'Các khoản tiền được lưu ở đúng grain nguồn. Danh mục giá hay phần trăm promotion là thuộc tính phân tích, không thay thế giá đã thỏa thuận trong giao dịch.',
 ['F01 lấy tiền trực tiếp từ bookings final snapshot; đối chiếu gross-discount=customer_due và discount=company_share+partner_share. Không tính lại tiền từ giá phòng hiện hành hoặc discount_bps.',
  'Không cộng booking_revisions hoặc payments vào booking gross. Settlements chỉ đối soát phần tài trợ được hưởng/đã nhận; payments là dòng tiền riêng.',
  'F04 net_ticket=gross-refunded ở cấp đơn; không lặp giá đơn cho mỗi ticket/admission. F05 agreed_vnd ghi một lần mỗi hợp đồng, không nhân ngày xe.',
  'B03 aggregate F04 và F05 riêng về booking rồi LEFT JOIN cohort F01. Bộ lọc loại phòng dùng EXISTS BridgeBookingRoom, không join detail rồi SUM tiền.',
  'Giá trị B02 giữ lại trước vận hành không được gọi lợi nhuận; buffet kèm phòng không tạo thêm doanh thu.'],
 'Booking tiền phòng 2 triệu, hai đơn vé 100k+200k và một xe 400k -> tổng 2,7 triệu. Join vé x xe không được lặp lại tiền phòng.')
rule('R10','Ngày công suất và xung đột sử dụng',
 'Các fact room-day/activity-day/vehicle-day là lịch công suất, không phải danh sách các giao dịch có phát sinh. Phải giữ cả ngày không có khách để mẫu số không bị thu hẹp.',
 ['Dựng Cartesian danh mục hợp lệ với lịch kỳ công suất, sau đó lookup dimension tại đầu ngày. V2 giả định danh mục hoạt động toàn kỳ.',
  'Room-day blocked là EXISTS ngày nằm trong union khoảng bảo trì của asset thuộc phòng; xe tương tự. Nhiều công việc chồng nhau vẫn chặn một ngày. Closure hoạt động là toàn ngày, gộp nhiều lý do cùng activity/date.',
  'Phát hiện hai stays hoặc hai rentals cùng resource/day trước khi DISTINCT. Nhóm bị xung đột không chọn ngẫu nhiên một giao dịch; loại các dòng thuộc conflict scope và gắn cảnh báo.',
  'Nếu thiếu hoặc sai dữ liệu bảo trì/closure có thể làm không biết capacity, không tự đặt blocked=0/available=1. Chỉ công bố ngày tài nguyên xác định được; cảnh báo phạm vi còn thiếu.',
  'Admission vượt capacity hoặc vào ngày đóng: không kẹp tỷ lệ về 100%; loại cả nhóm vi phạm activity/day khỏi tập admission hợp lệ, ghi số lượt và lý do. Capacity đã xác định độc lập vẫn được giữ, tỷ lệ gắn PARTIAL.'],
 'R1 bị chặn [01,03) và [02,04) -> ba ngày chặn, không phải bốn. R2 cùng ba ngày không bảo trì -> tổng khả dụng 3 trên 6 room-day.')
rule('R11','Quyền lợi buffet và nhà hàng',
 'Entitlement, hóa đơn và phiên buffet là ba grain khác nhau; mapping phải bảo toàn vai trò của từng nguồn. Giá trị included breakfast đã nằm trong gói phòng.',
 ['F06 dùng entitlement nguồn của booking COMPLETED, kiểm tra 0<=redeemed<=eligible, duy nhất booking_room/service_date và tồn tại lưu trú hợp lệ ở ngày đó theo quy ước v2.',
  'Đọc rate_plan để xác nhận breakfast_included; không suy tất cả phòng 3 sao đều trả thêm hoặc tự sinh entitlement từ số khách. Mã sinh v2 tạo entitlement từ sáng sau ngày check-in tới sáng ngày checkout: checkin_date < service_date <= checkout_date, tương đương [checkin+1,checkout+1). Kiểm tra đêm đã ở là service_date-1, không phải service_date.',
  'Ánh xạ entitlement đến đúng một RESTAURANT thuộc hotel tại ngày phục vụ; 0 hoặc >1 outlet hợp lệ đều là lỗi mapping, không chọn MIN(outlet_id).',
  'F07 service hotel lấy từ outlet, booking hotel từ booking optional; khác hotel là hợp lệ. guest_id NULL không tự điền bằng guest booking.',
  'B04.05 cộng covers hóa đơn + redeemed entitlement; không cộng actual_covers lần ba. B04.07 dùng tổng chi phí/tổng actual_covers đúng tập phiên BREAKFAST/DINNER.',
  'Rating v2 bắt buộc 1..5; sai rating làm dòng F07 không đạt contract và được ghi lỗi, không tự coi là không có đánh giá. B04.08 mỗi hóa đơn một trọng số.'],
 'Quyền lợi dùng 2 suất, hóa đơn sáng 1 suất và tối 2 suất -> lượt phục vụ 5. Hai rating 4 và 2 -> trung bình 3, không nhân theo covers.')
rule('R12','Dòng mua hàng và nhận nhiều đợt',
 'F12 lưu lượng đặt một lần; F13 lưu mỗi lần nhận độc lập. Phải giữ dòng mua chưa nhận để đánh giá thiếu hàng và OTIF. Ngày giao hàng thực received_on khác với ngày file tới lake.',
 ['Nối receipt->purchase_line->purchase_order theo N:1, lấy supplier/hotel/item từ chuỗi này. Kiểm tra lượng không âm và ngày nhận hợp lệ; expires NULL dùng date_key=0, không tự tính từ shelf_life.',
  'late_accepted_qty=accepted_qty khi received_on>expected_on, ngược lại 0. Không loại receipt trễ khỏi fact; không dùng ingestion received_at thay received_on.',
  'B06 chọn dòng expected_on trong [S,E) và <=A; receipt có received_on<=A. G=sum accepted, R=sum rejected, L=sum late accepted, T=sum accepted nhận trước/đúng hẹn.',
  'LEFT JOIN tổng receipt về từng purchase_line. Chỉ COALESCE về 0 khi đã xác định nguồn receipt đủ và dòng không bị quarantine liên quan. Nếu receipt của dòng bị loại, G/R/L/T tính trên phần hợp lệ nhưng gắn PARTIAL, không tuyên bố chưa giao.',
  'Các nhóm B06 dùng phân loại dimension của F12 tại ngày đặt để cùng cohort. Không join trực tiếp SCD supplier_key của F13 sang F12 vì cùng supplier có thể khác phiên bản.',
  'Không cộng lượng khác base_unit; tỷ lệ dòng OTIF vẫn có thể tổng hợp xuyên đơn vị do đơn vị đếm là dòng.'],
 'Đặt 10 kg; đúng hạn nhận 6 đạt, trễ nhận 3 đạt+1 từ chối -> G=9,R=1,L=3,T=6, đáp ứng 90%, từ chối 10%, OTIF=0%.')
rule('R13','Kho và số dư theo lô',
 'Mỗi receipt_id là một lô trong v2. Stock ledger là nguồn thay đổi tồn; giá lô lấy từ purchase_line. Cần đầy đủ lịch sử trước kỳ để tính tồn đầu, không chỉ đọc movement trong khoảng đang xem.',
 ['signed_qty=+quantity cho IN, -quantity cho USE/WASTE. in/use/waste_qty chọn theo movement_type; movement_value=quantity*unit_price giữ DECIMAL(38,3).',
  'Kiểm tra hotel/item của movement khớp PO/line/receipt. Receipt rejected không nhập kho; expires_on không tự tạo WASTE.',
  'Tổng tồn theo lô/ngày phải không âm; nguồn chỉ có ngày nên không bịa thứ tự nội ngày. USE/WASTE có ngày trước IN hoặc tồn cuối ngày âm là lỗi; không dùng movement_id để giả timestamp.',
  'Nếu bất kỳ movement cần thiết bị loại hoặc nguồn ledger không đầy đủ, số dư lô từ ngày bị ảnh hưởng trở đi không đủ tin cậy. F14 có thể giữ các movement độc lập còn hợp lệ; F15 không công bố số dư của scope bị thiếu và B07 tồn gắn UNAVAILABLE/PARTIAL theo phạm vi.',
  'F15 tùy chọn dựng dense lot-day từ nhận hàng hợp lệ tới hết kỳ; giữ cả ngày không phát sinh và ngày số dư bằng 0 để dễ kiểm tra. Cuối ngày d=sum signed_qty<=d. Tồn đầu S lấy số dư S-1 hoặc lịch sử F14 trước S.',
  'Không SUM closing_qty qua ngày. Không dùng usage_area lọc tồn; chỉ dùng cho lượng USE. Không cộng F14+F15 thành hai nguồn tồn độc lập.'],
 'IN 10, USE 6, WASTE 2 ở giá 10.000 -> còn 2, hao hụt 20.000. Kỳ sau WASTE 1 trên tồn đầu 2 -> hao hụt 50%, không cộng số dư hai kỳ thành 3.')
rule('R14','Feed ngoài và nguồn đối soát',
 'Nguồn nghiệp vụ F13 là receipts trong DB. Feed thương nhân chứa phiên bản/replay và lỗi đơn vị giúp kiểm tra engineering; không đại diện một lần nhận hàng bổ sung.',
 ['Dùng bốn bảng derived của catalog: receipt_versions, receipt_latest, receipt_replays, receipt_quarantine. Không đọc raw và UNION thêm vào F13.',
  'Mã lake hiện hành đổi g/1000 sang kg, giữ kg; đơn vị khác bị quarantine. Đây là quy tắc feed hiện có, không áp đại trà lên lượng DB đã có base_unit. Nếu mở rộng đơn vị phải có conversion contract riêng.',
  'event_id lặp cùng payload là replay; khác payload là conflict. receipt_ref/revision trùng identity khác cũng là lỗi. latest chọn revision lớn nhất hợp lệ, không chọn file đến sau cùng.',
  'Đối chiếu latest.receipt_ref với receipt_id, purchase_line_ref, supplier_id, hotel_id, accepted_qty_kg và unit_price. DB vẫn là nguồn KPI khi mismatch; đánh dấu reconciliation issue, không tự sửa DB.',
  'Nếu phiên bản mới nhất nhận được bị quarantine, latest hợp lệ có thể là bản cũ; phải ghi chưa xác nhận phiên bản mới nhất. received_at chỉ đo độ trễ file, không dùng tính giao trễ B06.',
  'Payments/settlements/cash_events/booking_revisions giữ ở lake để đối soát; membership/card không làm Golden Customer và chưa tạo KPI membership ngoài phạm vi 47 chỉ tiêu.'],
 'Một receipt 10 kg gửi lại hai lần và có revision sửa 9 kg: replay không tăng lượng, DB receipt chỉ đóng góp một lần theo snapshot; chênh 9 và 10 được báo đối soát.')
rule('R15','Công bố báo cáo thiếu dữ liệu',
 'Người dùng đã chọn vẫn xuất report từ phần hợp lệ. Điều kiện là dữ liệu công bố còn lại phải giữ được grain, khóa và ý nghĩa, đồng thời mô tả rõ phần không đủ. PARTIAL là một trạng thái có chủ đích, không phải âm thầm bỏ lỗi.',
 ['Mỗi dòng input vào đúng một nhóm: accepted, quarantined trực tiếp, dependency_excluded, business_filtered hoặc replay_discarded. Một dòng nhiều lỗi có danh sách rule nhưng chỉ đếm một lần trong thống kê loại.',
  'QualityCoverage ghi expected/input/accepted counts và scope ngày/cơ sở nếu xác định được. Với fact mở rộng ngày, theo dõi riêng số dòng nguồn và số grain đích; không so số room-day với số stay để gọi tỷ lệ đầy đủ.',
  'Nếu một bảng input thiếu, expected_count không biết thì để NULL; không khẳng định đầy đủ 0% hoặc 100%. Lỗi không xác định được site/ngày phải lan cảnh báo tới toàn KPI phụ thuộc nguồn đó.',
  'MetricQualityStatus theo metric+filter scope: COMPLETE khi đủ; PARTIAL khi tính trên phần hợp lệ nhưng thiếu phần liên quan; UNAVAILABLE khi không thể tính có nghĩa. Mẫu số 0 trả BLANK theo KPI; số 0 chỉ khi đã xác nhận không phát sinh.',
  'Tỷ lệ PARTIAL có thể cao hoặc thấp hơn thật; không gọi lower bound hay upper bound trừ khi có chứng minh. Một KPI tổng hợp có thành phần PARTIAL/UNAVAILABLE không được gắn COMPLETE.',
  'Publish quality metadata cùng snapshot các bảng. Không trộn tự động dữ liệu batch cũ. Lỗi engine không tạo được snapshot nhất quán -> FAILED; giao diện vẫn có thông báo thiếu hoặc bản trước có nhãn thời gian cũ.'],
 '1.000 booking nguồn, 20 lỗi -> report hiển thị tổng của 980 booking và nhãn thiếu 20. Nếu mất toàn file booking, không hiển thị Doanh thu=0 mà hiển thị Không đủ dữ liệu.')
rule('R16','Tái chạy và sửa đổi',
 'Nạp incremental chưa thể chỉ dựa updated_at vì không phải bảng nào cũng có cột đó. Bản v2 dùng snapshot đầy đủ, xác định diff bằng business key và payload, sau đó cập nhật candidate theo đúng phạm vi ảnh hưởng.',
 ['Cùng input manifest, cùng transform version và registry phải tạo cùng tập khóa/payload nghiệp vụ; created/updated audit có thể khác lần chạy nhưng không dùng so sánh KPI.',
  'Booking sửa tiền cập nhật F01 một dòng; sửa ngày/referral tính lại role/cohort F04/F05/F07 và các bridge phụ thuộc. Dimension đổi không tự rekey mọi fact cũ sang current.',
  'Stay/rental/maintenance/closure sửa khoảng: tính lại union của khoảng cũ và mới; xóa dòng đích đã hết hiệu lực trong candidate, không chỉ append ngày mới.',
  'Stock correction tính lại F14 và F15 từ ngày sớm nhất ảnh hưởng tới cuối kỳ. Dữ liệu đến muộn được upsert natural key, có thể nâng trạng thái quality của báo cáo sau khi phục hồi.',
  'Không suy nguồn bị xóa từ file thiếu. Chỉ xử lý vắng mặt khi full snapshot được xác minh đầy đủ hoặc có tombstone; lưu evidence xóa/đổi và registry trước đó.'],
 'Một stay sửa checkout 03/01 thành 02/01: xóa đêm 02/01 ở candidate và giữ các đêm còn hợp lệ; chạy lại không tạo bản sao room-day.')
rule('R17','Quan hệ danh mục tại đúng thời điểm',
 'SCD2 không chỉ áp dụng cho nhãn hiển thị. Khi phòng đổi khách sạn quản lý hoặc khách sạn đổi cụm, quan hệ giữa các đối tượng cũng phải lấy từ phiên bản tại thời điểm fact; nếu lấy hotel_id/site_id từ snapshot hiện tại thì có thể phân loại sai quá khứ.',
 ['DIM_ATTR(D,BK,t,attribute) chọn đúng phiên bản D theo R07 rồi đọc thuộc tính nguồn trong phiên bản đó. Đây là bước resolve ETL, không tạo FK dimension-to-dimension trong mô hình công bố.',
  'Phòng -> hotel lấy từ DimRoom tại t; hotel -> site lấy từ DimHotel tại cùng t. Vehicle/activity -> centre và centre -> site tương tự. Asset -> hotel/room lấy từ DimAsset tại t.',
  'Các FK trực tiếp của giao dịch như bookings.hotel_id, purchase_orders.supplier_id là chứng cứ giao dịch; không ghi đè bằng danh mục current. Khi kiểm tra khớp room/rate/hotel phải so phiên bản đúng thời điểm.',
  'V2 chỉ một phiên bản nên đọc thuộc tính từ source snapshot cho cùng kết quả. Khi có lịch sử, join raw parent trong kế hoạch chỉ để truy vết/kiểm tra nguồn, biểu thức DIM_ATTR mới quyết định thuộc tính lịch sử.',
  'Entitlement tìm đúng một phiên bản DimOutlet NORMAL loại RESTAURANT có hotel_id tương ứng tại service_date. Thiếu/trùng mapping phải báo lỗi. Chính sách đổi outlet giữa kỳ cần effective history, không chọn ngẫu nhiên.',
  'Đơn giá lô, giá booking và lượng giao dịch không lấy từ DIM_ATTR giá hiện hành; vẫn giữ giá đã thỏa thuận ở dòng nguồn.'],
 'Hotel H từng thuộc site A, từ 01/07 thuộc B: booking 01/06 giữ site A dù file hotels mới đang ghi B. Hai nhánh phải dùng cùng lịch sử dimension để resolve.')

PLANS={}
def plan(id, sources, joins, selection, process, depends=()):
    PLANS[id]=dict(id=id,aliases=dict(sources),joins=joins,selection=selection,process=process,depends_on=list(depends))
def j(left, right, condition, cardinality='N:1', optional=False):
    return dict(left=left,right=right,condition=condition,cardinality=cardinality,
                join_type='LEFT_OPTIONAL_VALIDATED' if optional else 'REQUIRED_VALIDATED',
                on_error='NULL optional dùng special member; ref có giá trị sai -> dependency_excluded.' if optional else 'Parent thiếu/không duy nhất -> loại child và ghi dependency_excluded; không inner-drop im lặng.')

DIM_SINGLE={
 'D02':'hotel_ops.sites','D03':'hotel_ops.hotels','D04':'hotel_ops.rooms','D06':'hotel_ops.promotions',
 'D08':'hotel_ops.rate_plans','D09':'hotel_ops.outlets','D11':'entertainment_ops.centres',
 'D12':'entertainment_ops.activities','D13':'entertainment_ops.vehicles','D14':'hotel_ops.suppliers',
 'D15':'hotel_ops.items','D16':'hotel_ops.assets'}
for tid,tab in DIM_SINGLE.items():
    plan(tid,[('s',tab)],[], 'Mọi bản ghi danh mục đúng PK và miền giá trị; không lọc chỉ đối tượng có giao dịch.',
         ['Kiểm tra các tham chiếu danh mục trong snapshot nguồn; loại ID sai, không tạo dimension suy đoán.',
          'Giữ các thuộc tính nguồn khai báo trong design; chạy quy trình SCD2 R06–R07 trên từng namespace/BK.',
          'Thuộc tính ID bên trong dimension giữ là thuộc tính denormalized; không dựng snowflake FK dimension-to-dimension.'])
plan('D01',[],[], 'Lịch Gregorian liên tục 2023-01-01..2026-12-31 từ min/max ngày hợp lệ; thêm hai dòng đặc biệt.',
     ['Thu thập min/max DATE và LOCAL_DATE(TIMESTAMPTZ) từ cả hai DB theo R03.',
      'Lịch bao phủ mọi năm có ngày nguồn, nhưng khi tạo công suất phải dùng kỳ riêng 2024–2025.',
      'Sinh day/day_of_week Monday=1/month/quarter/year xác định; không suy mùa hoặc ngày lễ khi chưa có bộ quy tắc.'])
plan('D05',[('h','hotel_ops.channels'),('e','entertainment_ops.ticket_orders')],[],
     'UNION ALL hai namespace: từng hotel channel và DISTINCT sales_channel hợp lệ của entertainment.',
     ['Hotel giữ channel_id/name/type/commission_bps. Entertainment dùng sales_channel làm code và name, type=ENTERTAINMENT_SALES, commission_bps=NULL.',
      'DISTINCT chỉ tạo danh mục mã sales_channel, không loại đơn vé khỏi fact. GATE và HOTEL_RECEPTION được quan sát ở v2; mã mới cần xác nhận domain.',
      'Cùng chuỗi code ở hai namespace vẫn là hai BK riêng; không ghép theo tên vendor.'])
plan('D07',[('h','hotel_ops.guests'),('e','entertainment_ops.customers')],[],
     'UNION ALL hồ sơ hotel và entertainment, mỗi nguồn giữ ID riêng.',
     ['Giữ full_name/phone/email đúng nguồn; hotel member_card_ref=NULL vì bảng guests không có cột đó.',
      'Thẻ từ entertainment là tham chiếu nguồn, không là căn cứ gộp hai customer profile. Kiểm tra thẻ để đối soát riêng, không làm thay đổi PK hồ sơ.',
      'Không enrich membership validity vào profile hiện hành hoặc suy ra khách duy nhất toàn tập đoàn.'])
plan('D10',[],[], 'Bốn dòng danh mục cố định và hai thành viên đặc biệt.',
     ['BREAKFAST=1/Bữa sáng; LUNCH=2/Bữa trưa; DINNER=3/Bữa tối; BAR=4/Bar.',
      'Giá trị meal không thuộc danh mục là lỗi nguồn, không tự map về BAR hoặc UNKNOWN.'])

plan('F01',[('b','hotel_ops.bookings'),('h','hotel_ops.hotels')],[j('b','h','b.hotel_id=h.hotel_id')],
 'Giữ ba trạng thái booking hợp lệ; snapshot bookings là nguồn tiền cuối cùng.',
 ['Grain namespace+booking_id; không join booking_rooms/stays ở bước tạo tiền.',
  'Tra dimension theo booked_on. promotion=NULL -> -1; promotion sai -> loại booking, cảnh báo các KPI liên quan.',
  'Kiểm tra tiền cân bằng và ngày; trạng thái không thuộc domain là lỗi. Sửa giá không tạo thêm booking.'])
plan('F02',[('r','hotel_ops.rooms'),('h','hotel_ops.hotels'),('a','hotel_ops.assets'),('m','hotel_ops.maintenance')],
 [j('r','h','r.hotel_id=h.hotel_id'),j('m','a','m.asset_id=a.asset_id')],
 'Mọi phòng x ngày công suất hợp lệ; chỉ m có asset.room_id tạo phạm vi chặn.',
 ['Dựng room/day đầy đủ. Đọc m->a rồi expand maintenance [start,end), gộp room/day trước khi LEFT MATCH về lịch phòng.',
  'Không nối từng m trực tiếp vào lịch rồi SUM inventory_day. Chung phòng nhiều asset bảo trì vẫn chỉ blocked_day=1.',
  'Thiếu maintenance scope làm unknown capacity; loại ngày không xác định khỏi tập F02 hợp lệ và ghi coverage.'],['D01','D02','D03','D04','L02'])
plan('F03',[('s','hotel_ops.stays'),('br','hotel_ops.booking_rooms'),('b','hotel_ops.bookings'),('r','hotel_ops.rooms'),('h','hotel_ops.hotels'),('rp','hotel_ops.rate_plans')],
 [j('s','br','s.booking_room_id=br.booking_room_id'),j('br','b','br.booking_id=b.booking_id'),j('br','r','br.room_id=r.room_id'),j('r','h','r.hotel_id=h.hotel_id'),j('br','rp','br.rate_plan_id=rp.rate_plan_id')],
 'b.status=COMPLETED; expand [s.checkin_date,s.checkout_date), giữ date thật trước khi lọc kỳ report.',
 ['Kiểm tra r.hotel_id=b.hotel_id=rp.hotel_id và rp.channel_id=b.channel_id.',
  'Phát hiện overlap room/day trên mọi stays; nhóm trùng hoặc trùng ngày bảo trì -> loại các dòng lỗi, không DISTINCT che overlap.',
  'Không dùng ngày arrival/departure dự kiến thay stay thiếu. F02 thiếu coverage ở ngày ở -> không kết luận hợp lệ về availability.'],['F02'])
plan('F04',[('o','entertainment_ops.ticket_orders'),('c','entertainment_ops.centres'),('b','hotel_ops.bookings'),('h','hotel_ops.hotels')],
 [j('o','c','o.centre_id=c.centre_id'),j('o','b','o.hotel_booking_ref=b.booking_id',optional=True),j('b','h','b.hotel_id=h.hotel_id',optional=True)],
 'Mọi ticket_order hợp lệ, có hoặc không có booking_ref; đơn hoàn toàn bộ vẫn được lưu.',
 ['Gross/refund/net ở cấp order. Không join tickets để tính tiền.',
  'Không ref: các khóa booking/cohort=-1, DD hotel_booking_ref=NULL. Có ref hợp lệ: kế thừa F01 hotel/site/channel phiên bản và departure date.',
  'Có ref nhưng booking bị loại ở F01 -> dependency_excluded; không biến dịch vụ thành bán độc lập.'],['F01','L03'])
plan('F05',[('r','entertainment_ops.rentals'),('v','entertainment_ops.vehicles'),('c','entertainment_ops.centres'),('b','hotel_ops.bookings'),('h','hotel_ops.hotels')],
 [j('r','v','r.vehicle_id=v.vehicle_id'),j('v','c','v.centre_id=c.centre_id'),j('r','b','r.hotel_booking_ref=b.booking_id',optional=True),j('b','h','b.hotel_id=h.hotel_id',optional=True)],
 'Mọi rental đúng contract, gồm COMPLETED/CANCELLED; số tiền không nhân ngày.',
 ['Pickup/return là date roles. Dimension dịch vụ tra tại pickup; dimension booking kế thừa F01.',
  'Lỗi duration/overlap/bảo trì: kiểm tra theo R10 trước publish; rental tham gia conflict không được ghi là thuê hoàn tất hợp lệ.',
  'Booking_ref NULL là bán độc lập; ref có giá trị sai phải được loại và báo thiếu.'],['F01','L03'])
plan('F06',[('e','hotel_ops.breakfast_entitlements'),('br','hotel_ops.booking_rooms'),('b','hotel_ops.bookings'),('r','hotel_ops.rooms'),('h','hotel_ops.hotels'),('rp','hotel_ops.rate_plans'),('o','hotel_ops.outlets'),('s','hotel_ops.stays')],
 [j('e','br','e.booking_room_id=br.booking_room_id'),j('br','b','br.booking_id=b.booking_id'),j('br','r','br.room_id=r.room_id'),j('b','h','b.hotel_id=h.hotel_id'),j('br','rp','br.rate_plan_id=rp.rate_plan_id'),
  j('h','o',"h.hotel_id=o.hotel_id AND o.outlet_type='RESTAURANT'",'1:exactly1'),
  j('e','s','e.booking_room_id=s.booking_room_id AND s.checkin_date<e.service_date<=s.checkout_date','SEMI_EXISTS_EXACTLY1')],
 'Booking COMPLETED, breakfast_included=1, đúng một entitlement/booking_room/service_date.',
 ['Giữ eligible/redeemed nguồn; kiểm tra rate plan/hotel/room và một stay hợp lệ với checkin<service_date<=checkout, không nhân entitlement qua join nhiều stay. Nếu kiểm tra F03 thì lookup đêm service_date-1; không loại suất sáng checkout chỉ vì không có đêm ở vào chính ngày checkout.',
  'Meal cố định BREAKFAST. Outlet mapping duy nhất theo khách sạn phục vụ; v2 một RESTAURANT/hotel.',
  'Không dùng giá buffet để tạo doanh thu cho quyền lợi; không suy thêm suất trẻ em.'],['F03'])
plan('F07',[('d','hotel_ops.dining_orders'),('o','hotel_ops.outlets'),('h','hotel_ops.hotels'),('b','hotel_ops.bookings')],
 [j('d','o','d.outlet_id=o.outlet_id'),j('o','h','o.hotel_id=h.hotel_id'),j('d','b','d.booking_id=b.booking_id',optional=True)],
 'Mọi hóa đơn ăn uống đúng số tiền, covers, meal và rating.',
 ['Service_hotel/site theo outlet; booking_hotel theo ref booking nếu có; khách ăn ở hotel khác booking là hợp lệ.',
  'd.guest_id NULL -> customer_profile=0; d.booking_id NULL -> booking_hotel=-1; không đồng nhất hai loại thiếu này.',
  'F07 không join chi phí meal_sessions. Rating_sum=rating, rating_count=1 trên dòng hợp lệ.'],['F01'])
plan('F08',[('s','hotel_ops.meal_sessions'),('o','hotel_ops.outlets'),('h','hotel_ops.hotels')],
 [j('s','o','s.outlet_id=o.outlet_id'),j('o','h','o.hotel_id=h.hotel_id')],
 'Meal BREAKFAST hoặc DINNER; outlet RESTAURANT; một outlet/date/meal.',
 ['Giữ actual_covers và ingredient_cost_vnd nguồn. Một grain nhiều session_id là lỗi, không SUM gộp để che.',
  'Đối soát actual_covers với entitlement redeemed + dining covers theo outlet/date/meal sau aggregate.',
  'Không tạo phiên LUNCH/BAR và không chia chi phí phiên cho từng khách khi chưa có quy tắc.'])
plan('F09',[('a','entertainment_ops.admissions'),('t','entertainment_ops.tickets'),('o','entertainment_ops.ticket_orders'),('x','entertainment_ops.activities'),('c','entertainment_ops.centres')],
 [j('a','t','a.ticket_id=t.ticket_id'),j('t','o','t.ticket_order_id=o.ticket_order_id'),j('t','x','t.activity_id=x.activity_id'),j('x','c','x.centre_id=c.centre_id')],
 'Mọi admission có bằng chứng entered_at và quan hệ hợp lệ; không lọc tickets.status=USED.',
 ['Kiểm tra x.centre_id=o.centre_id; ngày địa phương từ entered_at.',
  'Tra customer/centre/activity/site tại entered_at chính xác. Kiểm tra activity/day với capacity F10.',
  'Ngày đóng hoặc vượt capacity xử lý theo nhóm R10. Không lọc admission theo valid_date khi đã có timestamp thật.'],['F10'])
plan('F10',[('a','entertainment_ops.activities'),('c','entertainment_ops.centres'),('cl','entertainment_ops.closures')],
 [j('a','c','a.centre_id=c.centre_id')],
 'Activity x ngày công suất; closure chỉ dùng EXISTS(activity_id,closed_on).',
 ['nominal_capacity lấy capacity_per_day phiên bản activity đúng ngày.',
  'is_closed=1 nếu closure hợp lệ tồn tại, available=nominal*(1-is_closed). Nhiều lý do đóng không nhân dòng.',
  'Không có closure chỉ suy open nếu coverage nguồn closures đầy đủ.'])
plan('F11',[('v','entertainment_ops.vehicles'),('c','entertainment_ops.centres'),('r','entertainment_ops.rentals'),('m','entertainment_ops.vehicle_maintenance')],
 [j('v','c','v.centre_id=c.centre_id')],
 'Vehicle x ngày công suất; rentals COMPLETED được expand độc lập; maintenance lấy union ngày.',
 ['Dựng inventory=1; maintenance_day từ EXISTS; available=1-maintenance.',
  'Kiểm tra số hợp đồng thuê mỗi vehicle/day<=1 và không trùng bảo trì; conflict làm scope vehicle/day không đạt, không kẹp rented về 1.',
  'rented_day từ rental vận hành có vehicle/duration/status hợp lệ; lỗi chỉ ở booking_ref của F05 không làm mất bằng chứng ngày xe vận hành, nhưng phải cảnh báo F05/B03 riêng. Không dùng F05 filtered như nguồn duy nhất cho F11.'])
plan('F12',[('l','hotel_ops.purchase_lines'),('p','hotel_ops.purchase_orders'),('h','hotel_ops.hotels')],
 [j('l','p','l.purchase_order_id=p.purchase_order_id'),j('p','h','p.hotel_id=h.hotel_id')],
 'Mọi dòng đặt mua hợp lệ; chưa áp cutoff A hoặc điều kiện đã nhận ở bước nạp.',
 ['Lấy quantity/unit_price ở l và date/supplier/hotel ở p; tra dimension tại ordered_on.',
  'Giữ ordered_qty một lần, không join detail receipts khi nạp F12.',
  'Lọc expected_on, cutoff A và aggregate receipt thực hiện ở lớp KPI B06.'])
plan('F13',[('r','hotel_ops.receipts'),('l','hotel_ops.purchase_lines'),('p','hotel_ops.purchase_orders'),('h','hotel_ops.hotels')],
 [j('r','l','r.purchase_line_id=l.purchase_line_id'),j('l','p','l.purchase_order_id=p.purchase_order_id'),j('p','h','p.hotel_id=h.hotel_id')],
 'Mỗi receipt DB hợp lệ một dòng, gồm nhiều lần giao cùng line; không áp A tại nạp.',
 ['Lấy supplier/hotel/item theo PO/line; dimension fact tra tại received_on.',
  'late_accepted=accepted khi received_on>expected_on. expires NULL->Date UNKNOWN.',
  'B06 đối chiếu về F12 qua purchase_line_id và dùng cohort F12; feed ngoài chỉ đối soát.'],['F12'])
plan('F14',[('m','hotel_ops.stock_movements'),('r','hotel_ops.receipts'),('l','hotel_ops.purchase_lines'),('p','hotel_ops.purchase_orders'),('h','hotel_ops.hotels')],
 [j('m','r','m.receipt_id=r.receipt_id'),j('r','l','r.purchase_line_id=l.purchase_line_id'),j('l','p','l.purchase_order_id=p.purchase_order_id'),j('m','h','m.hotel_id=h.hotel_id')],
 'Mọi movement hợp lệ, không cắt chỉ kỳ report; loại nguyên nhân IN/USE/WASTE ngoài domain.',
 ['Kiểm tra m.hotel_id=p.hotel_id và m.item_id=l.item_id; session_id có giá trị phải tồn tại đúng hotel/ngày khi đối soát.',
  'Giá lô l.unit_price_vnd; signed và ba lượng loại theo R13. Không dùng items.reference_cost_vnd.',
  'Kiểm tra diễn biến lô theo ngày và đánh dấu scope mất tính đầy đủ; không tự bù lượng âm.'],['F13'])
plan('F15',[('r','hotel_ops.receipts'),('l','hotel_ops.purchase_lines'),('p','hotel_ops.purchase_orders'),('h','hotel_ops.hotels')],
 [j('r','l','r.purchase_line_id=l.purchase_line_id'),j('l','p','l.purchase_order_id=p.purchase_order_id'),j('p','h','p.hotel_id=h.hotel_id')],
 'Tùy chọn vật hóa từ F14 đã công bố hợp lệ; chỉ lot-day có ledger đủ từ đầu kỳ mô phỏng tới ngày đó.',
 ['Sinh lot/day từ max(received_on,capacity_start) tới cuối kỳ; ngày không movement vẫn có số dư carry-forward.',
  'F14 aggregate theo namespace/receipt_id/hotel_id/item_id/day, tính prefix sum signed_qty. Định giá closing theo giá lô.',
  'F14 không lưu hotel_id/item_id dạng DD: giải mã qua dimension row mà FK trỏ tới để lấy BK; không lấy dimension current. Tra lại SCD cho ngày snapshot F15.',
  'Không giữ closing cho scope ledger thiếu; correction từ ngày d rebuild d..cuối kỳ.'],['F14'])
plan('F16',[('m','hotel_ops.maintenance'),('a','hotel_ops.assets'),('h','hotel_ops.hotels')],
 [j('m','a','m.asset_id=a.asset_id'),j('a','h','a.hotel_id=h.hotel_id')],
 'Mọi công việc hợp lệ; nguồn v2 chỉ có COMPLETED, work_type PLANNED/BREAKDOWN.',
 ['Giữ cost một lần, dimension tra tại starts_on; KPI chi phí lọc ends_on và COMPLETED.',
  'a.room_id NULL -> room_key=-1; không suy asset khu chung làm ngừng toàn hotel.',
  'Không dùng a.supplier_id như nhà thầu sửa chữa và không cộng vehicle_maintenance vào F16.'])
plan('F17',[('w','hotel_ops.weather_daily')],[],
 'Một site/weather_date duy nhất; giữ provenance synthetic từ nguồn.',
 ['weather_id vẫn là ID truy vết; trùng site/date không chọn average để che lỗi.',
  'Nhiệt độ không SUM; lượng mưa chỉ cộng ngày trong cùng site. severe flag dùng lọc.',
  'Khi dùng weather filter mà thiếu site/day, metric có lọc thời tiết phải báo thiếu; metric không dùng weather không tự giảm quality.'])
plan('L01',[('br','hotel_ops.booking_rooms'),('b','hotel_ops.bookings'),('r','hotel_ops.rooms'),('rp','hotel_ops.rate_plans')],
 [j('br','b','br.booking_id=b.booking_id'),j('br','r','br.room_id=r.room_id'),j('br','rp','br.rate_plan_id=rp.rate_plan_id')],
 'Một booking_room_id hợp lệ, bao gồm booking các trạng thái có trong F01.',
 ['Tra room/rate plan tại booked_on, khớp F01; giữ booking_id làm DD.',
  'Chỉ dùng EXISTS/COUNTD để lọc booking; không có allocation_weight hoặc tiền phân bổ.'],['F01'])
plan('L02',[('m','hotel_ops.maintenance'),('a','hotel_ops.assets'),('r','hotel_ops.rooms')],
 [j('m','a','m.asset_id=a.asset_id'),j('a','r','a.room_id=r.room_id',optional=True)],
 'Asset có room_id; expand [starts_on,ends_on) giao lịch công suất.',
 ['Một room/day/maintenance duy nhất; các maintenance khác được giữ riêng cho giải thích nguyên nhân.',
  'room_id NULL là business_filtered, không lỗi; room có giá trị sai là dependency_excluded.',
  'F02 dùng DISTINCT room/day của bridge, không SUM chi phí qua bridge.'])
plan('L03',[('o','entertainment_ops.ticket_orders'),('r','entertainment_ops.rentals'),('b','hotel_ops.bookings')],
 [j('o','b','o.hotel_booking_ref=b.booking_id',optional=True),j('r','b','r.hotel_booking_ref=b.booking_id',optional=True)],
 'UNION ALL TICKET_ORDER và RENTAL có booking_ref khác NULL và tham chiếu đúng.',
 ['service_type tách hai miền ID; mỗi service có tối đa một booking.',
  'View chỉ kiểm chứng ref nguồn, không phụ thuộc F04/F05 để tránh vòng load. Có ref nhưng F01 bị loại được xử lý tại fact consumer.',
  'Không bắt buộc booking COMPLETED tại view; điều kiện đó thuộc cohort KPI B03.'])
plan('L04',[('c','entertainment_ops.centres'),('s','hotel_ops.sites')],
 [j('c','s','c.site_code=s.site_id')],
 'Mỗi centre nguồn có đúng một site tồn tại.',
 ['So mã công khai tuyệt đối, không suy theo tên hay identity truth.',
  'Giữ namespace hai đầu, không thêm UNIQUE(site_id) vì mô hình có thể nhiều centre/site.',
  'Bảng hỗ trợ validation, không tạo quan hệ snowflake giữa DimCentre và DimSite.'])

# Explicit role maps: BK expression, time expression, optional-null behavior.
FK={}
def fk(tid, name, dim, bk, at, null=None, inherit=None):
    FK[(tid,name)]=dict(dimension=dim,business_key_expression=bk,asof_expression=at,
                       null_behavior=null or 'ERROR_REQUIRED',inherit_from=inherit)
def datefk(tid,name,expr,null=None): fk(tid,name,'D01',expr,'STATIC_DATE',null)
def service(tid,at,site,hotel=None,room=None,centre=None,activity=None,vehicle=None):
    fk(tid,'site_key' if tid not in ['F04','F05'] else 'service_site_key','D02',site,at)
    for n,d,x in [('hotel_key','D03',hotel),('room_key','D04',room),('centre_key','D11',centre),('activity_key','D12',activity),('vehicle_key','D13',vehicle)]:
        if x: fk(tid,n,d,x,at)
def referral(tid):
    for n,d,bk,parent in [('booking_site_key','D02','h.site_id','site_key'),('referral_hotel_key','D03','b.hotel_id','hotel_key'),('booking_channel_key','D05','b.channel_id','channel_key')]:
        fk(tid,n,d,bk,'LOCAL_START(b.booked_on)','NO_BOOKING_REF -> -1',f'F01.{parent} where booking_id=source.hotel_booking_ref')
    datefk(tid,'cohort_departure_date_key','b.departure','NO_BOOKING_REF -> -1')

for n,x in [('booked','booked_on'),('arrival','arrival'),('departure','departure')]: datefk('F01',n+'_date_key','b.'+x)
service('F01','LOCAL_START(b.booked_on)','h.site_id','b.hotel_id')
fk('F01','channel_key','D05','b.channel_id','LOCAL_START(b.booked_on)')
fk('F01','promotion_key','D06','b.promotion_id','LOCAL_START(b.booked_on)','NULL -> -1')
fk('F01','customer_profile_key','D07','b.guest_id','LOCAL_START(b.booked_on)')
datefk('F02','date_key','$day'); service('F02','LOCAL_START($day)','h.site_id','r.hotel_id','r.room_id')
datefk('F03','service_date_key','$day'); service('F03','LOCAL_START($day)','h.site_id','r.hotel_id','r.room_id')
for n,d,x in [('channel_key','D05','b.channel_id'),('customer_profile_key','D07','b.guest_id'),('rate_plan_key','D08','br.rate_plan_id')]: fk('F03',n,d,x,'LOCAL_START($day)')
datefk('F04','ordered_date_key','o.ordered_on'); service('F04','LOCAL_START(o.ordered_on)','c.site_code',centre='o.centre_id')
fk('F04','ticket_channel_key','D05','o.sales_channel','LOCAL_START(o.ordered_on)')
fk('F04','customer_profile_key','D07','o.customer_id','LOCAL_START(o.ordered_on)'); referral('F04')
datefk('F05','pickup_date_key','r.pickup_date');datefk('F05','return_date_key','r.return_date')
service('F05','LOCAL_START(r.pickup_date)','c.site_code',centre='v.centre_id',vehicle='r.vehicle_id')
fk('F05','customer_profile_key','D07','r.customer_id','LOCAL_START(r.pickup_date)');referral('F05')
datefk('F06','service_date_key','e.service_date'); service('F06','LOCAL_START(e.service_date)','h.site_id','b.hotel_id','br.room_id')
for n,d,x in [('customer_profile_key','D07','b.guest_id'),('rate_plan_key','D08','br.rate_plan_id'),('outlet_key','D09','o.outlet_id'),('meal_key','D10',"'BREAKFAST'")]: fk('F06',n,d,x,'LOCAL_START(e.service_date)')
datefk('F07','service_date_key','d.service_date');fk('F07','site_key','D02','h.site_id','LOCAL_START(d.service_date)')
fk('F07','service_hotel_key','D03','o.hotel_id','LOCAL_START(d.service_date)')
fk('F07','booking_hotel_key','D03','b.hotel_id','LOCAL_START(b.booked_on)','NULL_BOOKING -> -1','F01.hotel_key where booking_id=d.booking_id')
fk('F07','customer_profile_key','D07','d.guest_id','LOCAL_START(d.service_date)','NULL -> 0')
fk('F07','outlet_key','D09','d.outlet_id','LOCAL_START(d.service_date)');fk('F07','meal_key','D10','d.meal','STATIC_MEAL')
datefk('F08','service_date_key','s.service_date');service('F08','LOCAL_START(s.service_date)','h.site_id','o.hotel_id')
fk('F08','outlet_key','D09','s.outlet_id','LOCAL_START(s.service_date)');fk('F08','meal_key','D10','s.meal','STATIC_MEAL')
datefk('F09','admission_date_key','LOCAL_DATE(a.entered_at)');service('F09','UTC(a.entered_at)','c.site_code',centre='x.centre_id',activity='t.activity_id')
fk('F09','customer_profile_key','D07','o.customer_id','UTC(a.entered_at)')
datefk('F10','date_key','$day');service('F10','LOCAL_START($day)','c.site_code',centre='a.centre_id',activity='a.activity_id')
datefk('F11','date_key','$day');service('F11','LOCAL_START($day)','c.site_code',centre='v.centre_id',vehicle='v.vehicle_id')
for tid,anchor in [('F12','p.ordered_on'),('F13','r.received_on'),('F14','m.movement_date'),('F15','$day')]:
    service(tid,f'LOCAL_START({anchor})','h.site_id','p.hotel_id' if tid!='F14' else 'm.hotel_id')
    fk(tid,'supplier_key','D14','p.supplier_id',f'LOCAL_START({anchor})')
    fk(tid,'item_key','D15','l.item_id',f'LOCAL_START({anchor})')
datefk('F12','ordered_date_key','p.ordered_on');datefk('F12','expected_date_key','p.expected_on')
datefk('F13','received_date_key','r.received_on');datefk('F13','expected_date_key','p.expected_on');datefk('F13','expires_date_key','r.expires_on','NULL -> 0')
datefk('F14','movement_date_key','m.movement_date');datefk('F15','snapshot_date_key','$day')
datefk('F16','start_date_key','m.starts_on');datefk('F16','end_date_key','m.ends_on');service('F16','LOCAL_START(m.starts_on)','h.site_id','a.hotel_id')
fk('F16','room_key','D04','a.room_id','LOCAL_START(m.starts_on)','NULL -> -1');fk('F16','asset_key','D16','m.asset_id','LOCAL_START(m.starts_on)')
datefk('F17','weather_date_key','w.weather_date');fk('F17','site_key','D02','w.site_id','LOCAL_START(w.weather_date)')
fk('L01','room_key','D04','br.room_id','LOCAL_START(b.booked_on)');fk('L01','rate_plan_key','D08','br.rate_plan_id','LOCAL_START(b.booked_on)')
datefk('L02','date_key','$day');fk('L02','room_key','D04','a.room_id','LOCAL_START($day)')

def historical_bk(tid,expr,at):
    attr=lambda dim,bk,name:f"DIM_ATTR({dim},{bk},{at},'{name}')"
    if expr=='r.hotel_id' and tid in ['F02','F03']: return attr('D04','r.room_id','hotel_id')
    if expr=='o.hotel_id' and tid in ['F07','F08']:
        return attr('D09','d.outlet_id' if tid=='F07' else 's.outlet_id','hotel_id')
    if expr=='v.centre_id': return attr('D13','r.vehicle_id' if tid=='F05' else 'v.vehicle_id','centre_id')
    if expr=='x.centre_id': return attr('D12','t.activity_id','centre_id')
    if expr=='a.centre_id' and tid=='F10': return attr('D12','a.activity_id','centre_id')
    if expr in ['a.hotel_id','a.room_id'] and tid in ['F16','L02']:
        return attr('D16','m.asset_id',expr.split('.')[1])
    if expr=='h.site_id':
        hotel={'F01':'b.hotel_id','F02':'r.hotel_id','F03':'r.hotel_id','F06':'b.hotel_id','F07':'o.hotel_id','F08':'o.hotel_id',
               'F12':'p.hotel_id','F13':'p.hotel_id','F14':'m.hotel_id','F15':'p.hotel_id','F16':'a.hotel_id'}.get(tid)
        if hotel: return attr('D03',historical_bk(tid,hotel,at),'site_id')
    if expr=='c.site_code':
        centre={'F04':'o.centre_id','F05':'v.centre_id','F09':'x.centre_id','F10':'a.centre_id','F11':'v.centre_id'}[tid]
        return attr('D11',historical_bk(tid,centre,at),'site_code')
    return expr
for (tid,n),role in FK.items():
    if not role['inherit_from']:
        role['business_key_expression']=historical_bk(tid,role['business_key_expression'],role['asof_expression'])

EXPR={
 'F01':{'booking_count':'1'},
 'F02':{'inventory_day':'1','blocked_day':'EXISTS(L02 valid row with same namespace/room_id/$day)','available_day':'1 - blocked_day'},
 'F03':{'occupied_night':'1'},
 'F04':{'net_ticket_vnd':'o.gross_vnd - o.refunded_vnd'},
 'F07':{'rating_sum':'d.rating','rating_count':'1'},
 'F09':{'admission_count':'1'},
 'F10':{'nominal_capacity':'LOOKUP_SCD(D12,a.activity_id,LOCAL_START($day)).capacity_per_day','is_closed':'EXISTS(valid cl WHERE cl.activity_id=a.activity_id AND cl.closed_on=$day)','available_capacity':'nominal_capacity * (1 - is_closed)'},
 'F11':{'inventory_day':'1','maintenance_day':'EXISTS(valid m WHERE m.vehicle_id=v.vehicle_id AND m.starts_on<=$day<m.ends_on)','available_day':'1 - maintenance_day','rented_day':"COUNT(valid r WHERE r.vehicle_id=v.vehicle_id AND r.status='COMPLETED' AND r.pickup_date<=$day<r.return_date); require count<=1"},
 'F13':{'late_accepted_qty':'CASE WHEN r.received_on > p.expected_on THEN r.accepted_qty ELSE 0 END'},
 'F14':{'signed_qty':"CASE WHEN m.movement_type='IN' THEN m.quantity ELSE -m.quantity END",
        'in_qty':"CASE WHEN m.movement_type='IN' THEN m.quantity ELSE 0 END",'use_qty':"CASE WHEN m.movement_type='USE' THEN m.quantity ELSE 0 END",'waste_qty':"CASE WHEN m.movement_type='WASTE' THEN m.quantity ELSE 0 END",'movement_value_vnd':'CAST(m.quantity * l.unit_price_vnd AS VALUE)'},
 'F15':{'hotel_id':'p.hotel_id','item_id':'l.item_id','closing_qty':'SUM(F14.signed_qty WHERE same durable lot key AND movement_date <= $day)',
        'closing_value_vnd':'CAST(closing_qty * l.unit_price_vnd AS VALUE)',
        'in_qty':'SUM(F14.in_qty WHERE same durable lot key AND movement_date=$day)',
        'use_qty':'SUM(F14.use_qty WHERE same durable lot key AND movement_date=$day)',
        'waste_qty':'SUM(F14.waste_qty WHERE same durable lot key AND movement_date=$day)'},
 'F17':{'site_id':'w.site_id'},
 'L03':{'service_source_system':"'entertainment_ops'",'booking_source_system':"'hotel_ops'",'service_type':"UNION_BRANCH(o -> 'TICKET_ORDER', r -> 'RENTAL')",'service_id':'UNION_BRANCH(o.ticket_order_id, r.rental_id)','booking_id':'b.booking_id'},
 'L04':{'centre_source_system':"'entertainment_ops'",'site_source_system':"'hotel_ops'",'site_id':'c.site_code, validated equal to s.site_id'},
}
RULE_GROUP={
 'F01':['R08','R09'], 'F02':['R10'], 'F03':['R08','R10'], 'F04':['R08','R09'], 'F05':['R08','R09','R10'],
 'F06':['R08','R11'], 'F07':['R11'], 'F08':['R11'], 'F09':['R08','R10'], 'F10':['R10'], 'F11':['R08','R10'],
 'F12':['R12'], 'F13':['R12','R14'], 'F14':['R13'], 'F15':['R13'], 'F16':['R09','R10'], 'F17':['R03'],
 'L01':['R09'],'L02':['R10'],'L03':['R09'],'L04':['R04']}

def expression_refs(tid,expr):
    refs=[]
    for alias,field in re.findall(r'\b([a-z][a-z0-9_]*)\.([a-z][a-z0-9_]*)\b',expr):
        if alias not in PLANS[tid]['aliases']: continue
        ref=PLANS[tid]['aliases'][alias]+'.'+field
        if ref not in source: raise AssertionError('Invalid expression column '+tid+' '+ref)
        refs.append(ref)
    return sorted(set(refs))

def direct_expr(tid,c):
    refs=c['source_references']
    if len(refs)!=1: raise AssertionError('Explicit mapping missing '+tid+'.'+c['name'])
    tab,field=refs[0].rsplit('.',1)
    aliases=[a for a,t in PLANS[tid]['aliases'].items() if t==tab]
    if len(aliases)!=1: raise AssertionError('Source absent from plan '+tid+' '+refs[0])
    raw=aliases[0]+'.'+field
    return 'UTC('+raw+')' if c['type']=='UTC' else raw

AUDIT={
 'source_batch_id':('MANIFEST.source_batch_id','Batch nguồn đóng băng dùng tạo/cập nhật dòng; dòng không đổi giữ batch gốc, publication manifest xác định snapshot toàn bảng.'),
 'transform_version':('MANIFEST.transform_version','Hash hoặc version mã và cấu hình biến đổi; không dùng tên file tùy ý.'),
 'created_at_utc':('INSERT -> RUN.started_at_utc; UPDATE -> existing.created_at_utc','Đồng hồ ETL, không dùng cho thời gian nghiệp vụ hoặc hiệu lực SCD.'),
 'updated_at_utc':('PAYLOAD_OR_VALIDITY_CHANGED -> RUN.started_at_utc; NOOP -> existing.updated_at_utc','Đóng interval SCD cập nhật audit dù payload cũ không đổi; replay no-op giữ nguyên.'),
 'row_hash':('SHA256(CANONICAL_BUSINESS_PAYLOAD)','Dimension: tracked_attributes theo đúng thứ tự design. Fact/link: cột nghiệp vụ theo thứ tự design, FK thay bằng namespace/BK; loại SK, năm cột audit và năm cột SCD. NULL, decimal fixed-scale và timestamp UTC có serialization chung.'),
}
SCD={
 'valid_from_utc':('BOOTSTRAP ? 2022-12-31T17:00:00Z : trusted_effective_or_manifest_observed_at','Dùng R06–R07; source v2 chưa có effective timestamp. BK mới ở batch sau không mặc định lùi về bootstrap.'),
 'valid_to_utc':('NEXT_VERSION.valid_from_utc OR NULL','Khoảng hiệu lực loại cuối; current không có ngày cuối giả 9999. Close/open phải cùng candidate.'),
 'is_current':('CASE WHEN valid_to_utc IS NULL THEN 1 ELSE 0 END','Tối đa một current cho mỗi namespace/BK; kiểm tra overlap độc lập với current flag.'),
 'version_no':('ORDINAL_BY_VALID_FROM_PER_BUSINESS_KEY','V2=1. Ordinal tăng theo hiệu lực, có thể đổi khi chèn lịch sử; không dùng ordinal làm registry identity.'),
 'effective_time_basis':("BOOTSTRAP_ASSUMPTION | SOURCE_EFFECTIVE | OBSERVED_AT",'Ghi rõ nguồn của mốc hiệu lực; observed time không phải bằng chứng thay đổi nghiệp vụ thật.'),
}

def column_mapping(t,c):
    tid=t['id']; n=c['name']; refs=[]; note=''; extra={}
    common=['R01','R02','R04','R15','R16','R17']
    if n in AUDIT: expr,note=AUDIT[n]; kind='AUDIT'
    elif n in SCD: expr,note=SCD[n]; kind='SCD_CONTROL';common+=['R06','R07']
    elif (tid,n) in FK:
        role=FK[(tid,n)];extra.update(role);kind='DIMENSION_LOOKUP';common+=['R03','R05','R07']
        expr=(f'DATEKEY({role["business_key_expression"]})' if role['dimension']=='D01' else
              f'LOOKUP_MEAL({role["business_key_expression"]})' if role['dimension']=='D10' else
              f'LOOKUP_SCD({role["dimension"]}, namespace, {role["business_key_expression"]}, {role["asof_expression"]})')
        if role['inherit_from']:expr='INHERIT_VALIDATED('+role['inherit_from']+')'
        ns=('hotel_ops' if role['dimension'] not in ['D07','D05','D11','D12','D13'] else
            'entertainment_ops' if role['dimension'] in ['D11','D12','D13'] or (tid in ['F04','F05','F09'] and n in ['customer_profile_key','ticket_channel_key']) else 'hotel_ops')
        extra['lookup_namespace']='calendar' if role['dimension']=='D01' else 'reference' if role['dimension']=='D10' else ns
        refs=expression_refs(tid,role['business_key_expression']+' '+role['asof_expression'])
        note=f'Namespace {extra["lookup_namespace"]}; NULL: {role["null_behavior"]}. Giá trị có nội dung sai, thiếu parent hoặc lookup nhiều phiên bản -> dependency_excluded. '+c['description']
    elif t['kind']=='DIMENSION' and n==t['primary_key'][0]:
        expr='DATEKEY($calendar_date)' if tid=='D01' else 'MEAL_KEY_CONSTANT' if tid=='D10' else 'REGISTRY(entity_id, namespace, BK, valid_from_utc)'
        kind='SURROGATE_KEY';note='Không hash rút gọn hoặc tái đánh số mỗi batch; 0/-1 theo R05.';common+=['R05']
    elif n=='fact_key':
        expr='REGISTRY('+tid+', '+', '.join(t['unique_keys'][0])+')';kind='SURROGATE_KEY';note='Khóa grain dùng ID bền vững, không SCD SK; giữ nguyên qua correction/replay.';common+=['R05']
    elif n=='source_system':
        ns=t.get('namespace','hotel_ops')
        expr="UNION_BRANCH(h -> 'hotel_ops', e -> 'entertainment_ops')" if tid in ['D05','D07'] else repr(ns)
        kind='CONSTANT_OR_BRANCH';note='Namespace thuộc ID gốc, không đổi thành tên Oracle/Iceberg; dòng đặc biệt dimension dùng system.'
    elif n=='member_kind':expr="'NORMAL'; special rows 'UNKNOWN'/'NOT_APPLICABLE'";kind='CONSTANT';note='Hai dòng đặc biệt có các thuộc tính nghiệp vụ NULL; không gán BK giả.'
    elif tid=='D01':
        expr={'calendar_date':'$calendar_date','day':'DAY($calendar_date)','day_of_week':'ISO_WEEKDAY($calendar_date)','month':'MONTH($calendar_date)','quarter':'FLOOR((MONTH($calendar_date)-1)/3)+1','year':'YEAR($calendar_date)'}[n]
        kind='CALENDAR';note='Sinh xác định theo lịch Gregorian; dòng đặc biệt để NULL.';common+=['R03']
    elif tid=='D10':
        expr='REFERENCE_MEALS.'+n;kind='REFERENCE';note='Bảng mã BREAKFAST/Bữa sáng, LUNCH/Bữa trưa, DINNER/Bữa tối, BAR/Bar; không lấy tên bữa từ suy đoán.'
    elif tid=='D05':
        expr={'channel_code':'UNION_BRANCH(h.channel_id,e.sales_channel)','channel_name':'UNION_BRANCH(h.channel_name,e.sales_channel)',
              'channel_type':"UNION_BRANCH(h.channel_type,'ENTERTAINMENT_SALES')",'commission_bps':'UNION_BRANCH(h.commission_bps,NULL)'}[n]
        kind='UNION_BRANCH';note='Nhánh e lấy DISTINCT sales_channel để tạo danh mục; hoa hồng entertainment chưa có thì NULL, không 0.';refs=expression_refs(tid,expr)
    elif tid=='D07':
        expr={'source_customer_id':'UNION_BRANCH(h.guest_id,e.customer_id)','full_name':'UNION_BRANCH(h.full_name,e.full_name)','phone':'UNION_BRANCH(h.phone,e.phone)',
              'email':'UNION_BRANCH(h.email,e.email)','member_card_ref':'UNION_BRANCH(NULL,e.member_card_ref)'}[n]
        kind='UNION_BRANCH';note='Hai namespace riêng, không match tên/phone/email hoặc dùng identity truth; không suy khách hotel từ thẻ.';refs=expression_refs(tid,expr)
    elif n in EXPR.get(tid,{}):
        expr=EXPR[tid][n];kind='DERIVED';refs=expression_refs(tid,expr)
        note=c['description']+' Thực hiện sau các kiểm tra và bước tổng hợp của kế hoạch bảng; không coi vắng nguồn hoặc lỗi là 0.'
    else:
        expr=direct_expr(tid,c);refs=list(c['source_references']);kind='DIRECT_TYPED'
        note='Chép giá trị nguồn sau kiểm tra R02; '+c['description']+' Không tính lại bằng danh mục hiện hành.'
    if t['kind']=='DIMENSION' and t['history_policy']=='SCD_TYPE2':common+=['R06','R07']
    common+=RULE_GROUP.get(tid,[])
    if not refs: refs=expression_refs(tid,expr)
    return dict(target_column=n,type=c['type'],nullable=c['nullable'],required_for_normal_member=c.get('required_for_normal_member'),
                kind=kind,expression=expr,source_columns=sorted(set(refs)),explanation=note,
                rule_ids=list(dict.fromkeys(common)),aggregation=c['aggregation'],**extra)

ENTITIES=[]
for tid,t in targets.items():
    p=PLANS[tid]
    dims={c['dimension'] for c in t['columns'] if 'dimension' in c}
    for (owner,_),role in FK.items():
        if owner==tid: dims.update(re.findall(r'DIM_ATTR\((D\d\d),',role['business_key_expression']))
    p['depends_on']=sorted(set(p['depends_on'])|dims)
    ENTITIES.append(dict(**p,target_name=t['name'],target_physical_name=t['physical_name'],grain=t['grain'],
                         unique_keys=t['unique_keys'],target_checks=t['checks'],
                         columns=[column_mapping(t,c) for c in t['columns']]))

ERRORS=[
 ('INPUT_UNAVAILABLE','Nguồn thiếu toàn bảng/file hoặc sai checksum','Nguồn không được coi là rỗng; expected_count có thể NULL.','Mọi KPI phụ thuộc nguồn theo scope biết được.'),
 ('INVALID_VALUE','Parse, length, precision, miền giá trị hoặc số bắt buộc NULL','Quarantine bản ghi, giữ nguyên payload; không cắt/điền 0.','KPI dùng giá trị đó và dependency phía sau.'),
 ('DUPLICATE_ID_CONFLICT','Một PK nhiều payload','Quarantine cả nhóm; không last-wins tùy ý.','Phạm vi của toàn nhóm, không chọn một dòng làm đại diện.'),
 ('MISSING_PARENT','FK có giá trị nhưng không có parent hợp lệ','Dependency_excluded; FK optional chỉ được special khi giá trị nguồn NULL.','Fact/link con và KPI sử dụng.'),
 ('AMBIGUOUS_PARENT','Parent match nhiều dòng hoặc nhiều SCD interval','Loại child; sửa parent trước khi retry.','Không SUM dữ liệu đã bị fan-out.'),
 ('SCD_INTERVAL_CONFLICT','Trùng effective time khác payload hoặc interval overlap','Cách ly BK/interval; các phiên bản không liên quan có thể còn hợp lệ.','Fact thuộc khoảng hiệu lực bị ảnh hưởng.'),
 ('RESOURCE_OVERLAP','Hai stay/rental cùng resource/day','Loại mọi dòng conflict scope; giữ các ngày không xung đột nếu kiểm chứng được.','B01/B05 theo room hoặc vehicle/day; tiền rental liên quan gắn lỗi F05.'),
 ('SERVICE_WHILE_CLOSED','Stay/xe trong bảo trì hoặc admission lúc đóng','Loại nhóm sử dụng trái điều kiện; không xóa bản ghi đóng cửa để hợp thức hóa.','Tử số thiếu; capacity độc lập vẫn có thể hợp lệ, tỷ lệ PARTIAL.'),
 ('CAPACITY_EXCEEDED','Admission hợp lệ sơ bộ vượt capacity đã xác minh','Quarantine nhóm activity/day; không kẹp bằng capacity hoặc lấy N dòng đầu.','B05.01/03; số lượt bị loại được công bố.'),
 ('OUTLET_MAPPING_AMBIGUOUS','Entitlement không có đúng một nhà hàng hiệu lực','Loại entitlement khỏi F06, giữ lỗi để bổ sung mapping.','B04 quyền lợi và lượt phục vụ; không tạo suất ở outlet ngẫu nhiên.'),
 ('INCOMPLETE_LEDGER','Thiếu movement, balance âm hoặc USE trước IN','Không công bố số dư lot/day từ mốc không tin cậy; giữ movement độc lập còn đúng.','B07 số dư/giá trị và F15; quantity bị thiếu không là 0.'),
 ('RECONCILIATION_MISMATCH','DB receipt và feed latest không khớp','Giữ DB làm nguồn KPI; ghi mismatch và độ đầy đủ feed.','Nhãn đối soát; không tự đổi công thức lượng nhận chuẩn.'),
 ('REPLAY','Cùng identity, payload, có bằng chứng giao lại','Ghi discarded_replay, chỉ một sự kiện có đóng góp.','Không giảm completeness nghiệp vụ vì bản sao transport.'),
]

def load_order():
    remaining={e['id']:set(e['depends_on']) for e in ENTITIES}; levels=[]; done=set()
    while remaining:
        ready=sorted(k for k,v in remaining.items() if v<=done)
        if not ready: raise AssertionError('Dependency cycle: '+str(remaining))
        levels.append(ready);done.update(ready)
        for k in ready:del remaining[k]
    return levels

def source_inventory():
    catalog_by_id={t['dataset_id']:t for t in catalog['datasets']}
    recon={
      'hotel_ops.membership_plans':'Danh mục gói hội viên; chưa có KPI doanh thu hội viên trong B01–B08.',
      'hotel_ops.memberships':'Đối soát hiệu lực hội viên khi kiểm chứng thẻ; không suy Golden Customer.',
      'hotel_ops.member_cards':'Đối chiếu member_card_ref và owner; không tự hợp nhất guest/customer.',
      'hotel_ops.payments':'Đối soát dòng tiền booking; không cộng CHARGE/REFUND vào giá trị booking final.',
      'hotel_ops.settlements':'Đối soát tài trợ phải thu/đã thu và commission; không thay quyền hưởng tài trợ bằng tiền thực nhận.',
      'hotel_ops.booking_revisions':'Đối soát lịch sử sửa giá; không append thành booking mới.',
      'hotel_ops.booking_room_revisions':'Đối soát giá phòng sửa theo revision; không tạo đêm hoặc tiền mới.',
      'entertainment_ops.cash_events':'Đối soát tiền vé/xe và XOR ticket_order/rental; không tạo fact doanh thu ngoài phạm vi.'}
    out=[]
    for full in source_tables:
        users=[e['id'] for e in ENTITIES if full in e['aliases'].values()]
        c=catalog_by_id[full]
        out.append(dict(source_table=full,catalog_table=c['catalog_table'],standardized_path=c['standardized_path'],
                        dataset_row_count=c['row_count'],consumers=users,
                        purpose='TRANSFORM_OR_VALIDATE' if users else 'RECONCILIATION_ONLY',
                        note=recon.get(full,'Nguồn chính hoặc nguồn lookup theo kế hoạch bảng; không đưa toàn bộ cột nguồn vào warehouse chỉ để sao chép.')))
    return out

def source_validation_contracts():
    result=[]
    for tab,contract in source_tables.items():
        foreign=[]
        for c in contract['columns']:
            match=re.search(r'REFERENCES\s+(\w+)\((\w+)\)',c['constraints'])
            if match:
                ref=tab.split('.')[0]+'.'+match.group(1)+'.'+match.group(2)
                assert ref in source
                foreign.append(dict(column=c['name'],references=ref,optional_null=c['nullable'],
                                    rule='NULL giữ ý nghĩa nghiệp vụ nếu optional; ID có giá trị phải match đúng một parent cùng namespace/snapshot. Kiểm chứng lịch sử bổ sung theo R17.'))
        result.append(dict(source_table=tab,primary_key=[c['name'] for c in contract['columns'] if 'PRIMARY KEY' in c['constraints']],
                           required_columns=[c['name'] for c in contract['columns'] if not c['nullable']],
                           additional_unique_keys={'hotel_ops.booking_revisions':[['booking_id','revision_no']],
                                                   'hotel_ops.booking_room_revisions':[['revision_id','booking_room_id']]}.get(tab,[]),
                           declared_checks=contract['checks'],foreign_keys=foreign,
                           target_consumers=[e['id'] for e in ENTITIES if tab in e['aliases'].values()]))
    return result

def reference_examples():
    """Small independent reference calculations, not tests of production ETL."""
    examples=[]
    def check(id,description,actual,expected):
        assert actual==expected,(id,actual,expected)
        examples.append(dict(id=id,description=description,expected=expected,actual=actual,status='PASS_REFERENCE_CALCULATION'))
    def expand(start,end):
        a=date.fromisoformat(start);b=date.fromisoformat(end)
        return [(a+timedelta(days=i)).isoformat() for i in range((b-a).days)]
    check('E01','Khoảng lưu trú loại ngày trả phòng',expand('2024-01-30','2024-02-02'),['2024-01-30','2024-01-31','2024-02-01'])
    check('E02','Timestamp UTC sang ngày Việt Nam',datetime.fromisoformat('2024-01-01T18:30:00+00:00').astimezone(timezone(timedelta(hours=7))).date().isoformat(),'2024-01-02')
    blocked=set(expand('2024-01-01','2024-01-03'))|set(expand('2024-01-02','2024-01-04'))
    check('E03','Union bảo trì không nhân room-day',dict(blocked=len(blocked),inventory=6,available=6-len(blocked)),dict(blocked=3,inventory=6,available=3))
    intervals=[('R1','2023-01-01','2025-07-01',101),('R1','2025-07-01',None,102)]
    at='2025-07-01'
    check('E04','Ranh giới SCD chọn phiên bản mới',[sk for bk,start,end,sk in intervals if bk=='R1' and start<=at and (end is None or at<end)],[102])
    check('E05','SCD A rồi B rồi A cần ba identity',len({('R1',d) for d in ['2024-01-01','2024-03-01','2024-05-01']}),3)
    check('E06','Replay cùng BK và effective time không thêm identity',len({('R1','2024-03-01'),('R1','2024-03-01')}),1)
    check('E07','Không fan-out tiền booking',2000000+sum([100000,200000])+sum([400000]),2700000)
    check('E08','Tỷ lệ từ tổng thay vì trung bình tỷ lệ phiên',str(Decimal(100000+200000)/Decimal(3+2)),'60000')
    check('E09','Covers không cộng phiên lần ba',2+1+2,5)
    check('E10','B06 giao nhiều đợt',dict(O=10,G=6+3,R=1,L=3,T=6,otif=int(6>=10)),dict(O=10,G=9,R=1,L=3,T=6,otif=0))
    check('E11','Tồn theo lô và giá trị hao hụt',dict(closing=10-6-2,waste_value=2*10000),dict(closing=2,waste_value=20000))
    check('E12','Không cộng tồn cuối qua hai ngày',[2,1][-1],1)
    check('E13','Đơn vị feed g sang kg',str(Decimal('1500')/Decimal('1000')),'1.5')
    check('E14','PARTIAL còn 980 trên 1000',dict(accepted=1000-20,status='PARTIAL'),dict(accepted=980,status='PARTIAL'))
    def ratio(a,b):return None if b==0 else a/b
    check('E15','Mẫu số 0 không gán 0 phần trăm',ratio(0,0),None)
    def quality(deps):return 'UNAVAILABLE' if 'UNAVAILABLE' in deps else 'PARTIAL' if 'PARTIAL' in deps else 'COMPLETE'
    check('E16','Tử số thiếu không cho tỷ lệ COMPLETE',quality(['PARTIAL','COMPLETE']),'PARTIAL')
    check('E17','Thiếu toàn nguồn không phải số 0',quality(['UNAVAILABLE','COMPLETE']),'UNAVAILABLE')
    check('E18','Nhận 01/01 trả 03/01: quyền lợi sáng 02/01 và 03/01, gồm ngày checkout',expand('2024-01-02','2024-01-04'),['2024-01-02','2024-01-03'])
    return examples

def verify_breakfast_source():
    """Read-only evidence of the generator's breakfast boundary convention."""
    folder=ROOT/'generated/v2/hotel_ops'
    stays={}
    for row in csv.DictReader((folder/'stays.csv').open(encoding='utf-8-sig',newline='')):
        stays.setdefault(row['booking_room_id'],[]).append(row)
    checked=invalid=checkout_mornings=0
    for row in csv.DictReader((folder/'breakfast_entitlements.csv').open(encoding='utf-8-sig',newline='')):
        checked+=1
        matching=[s for s in stays.get(row['booking_room_id'],[]) if s['checkin_date']<row['service_date']<=s['checkout_date']]
        invalid+=len(matching)!=1
        checkout_mornings+=any(s['checkout_date']==row['service_date'] for s in matching)
    assert invalid==0,('Breakfast source convention mismatch',invalid)
    return dict(rule='checkin_date < service_date <= checkout_date',checked_entitlements=checked,invalid_count=invalid,checkout_morning_entitlements=checkout_mornings)

def validate():
    count=0
    def require(condition,message):
        nonlocal count
        assert condition,message
        count+=1
    require(len(ENTITIES)==37,'37 target entities')
    require(sum(len(e['columns']) for e in ENTITIES)==sum(len(t['columns']) for t in targets.values()),'All target columns mapped')
    ruleids={r['id'] for r in RULES}
    expected_roles={(t['id'],c['name']) for t in targets.values() for c in t['columns'] if 'dimension' in c}
    require(set(FK)==expected_roles,'All dimension role mappings match design, including bridges')
    refs=set();lookups=0
    for e in ENTITIES:
        tid=e['id'];columns=e['columns']
        require([c['target_column'] for c in columns]==[c['name'] for c in targets[tid]['columns']],tid+' ordered column coverage')
        for alias,tab in e['aliases'].items():require(tab in source_tables,tid+' source '+tab)
        for c in columns:
            require(bool(c['expression']) and bool(c['explanation']),tid+'.'+c['target_column']+' expression documented')
            require(set(c['rule_ids'])<=ruleids,tid+' rules resolve')
            for ref in c['source_columns']:
                require(ref in source,'Source column exists '+ref);refs.add(ref)
            if c['kind']=='DIMENSION_LOOKUP' and tid.startswith('F'):lookups+=1
            if c['kind']=='DIRECT_TYPED':require(bool(c['source_columns']),'Direct mapping has lineage')
        for join in e['joins']:
            require(join['left'] in e['aliases'] and join['right'] in e['aliases'],tid+' join aliases resolve')
            refs.update(expression_refs(tid,join['condition']))
        require(all(x in targets for x in e['depends_on']),tid+' dependencies resolve')
    require(lookups==102,'102 fact dimension roles mapped')
    inventory=source_inventory()
    require(len(inventory)==41,'All 41 source tables have a stated disposition')
    source_checks=source_validation_contracts()
    require(sum(len(x['foreign_keys']) for x in source_checks)==57,'57 declared source FK validation rules recorded')
    for p,h in HASHES.items():require(sha(p)==h,'Input unchanged '+p)
    examples=reference_examples()
    breakfast=verify_breakfast_source()
    return dict(status='PASSED_SPECIFICATION_VALIDATION',production_etl_executed=False,assertions=count,
                mapped_entity_count=len(ENTITIES),mapped_column_count=sum(len(e['columns']) for e in ENTITIES),
                source_table_count=len(inventory),unique_source_columns_referenced=len(refs),fact_dimension_roles=lookups,
                declared_source_fk_checks=57,
                transformation_rule_count=len(RULES),reference_example_count=len(examples),
                breakfast_boundary_source_check=breakfast,
                load_levels=load_order(),input_sha256=HASHES,
                limitations=['Expressions are relational pseudocode, not executable Oracle/Spark SQL.',
                             'Reference examples check intended arithmetic and semantics; production ETL and DDL have not been executed.',
                             'SCD2 lifecycle and partial-publication integration require implementation fixtures in the next phase.']),examples

GLOSSARY=[
 ('alias.column','Cột nguồn theo bảng alias trong kế hoạch của entity. Alias chỉ có phạm vi entity đó; r có thể là room, rental hoặc receipt tùy bảng.'),
 ('$day','$day là ngày sinh từ EXPAND khoảng hoặc lịch công suất; F15 là ngày chốt số dư. Không phải cột có sẵn trong source.'),
 ('$calendar_date','Ngày sinh liên tục cho DimDate, 2023–2026 ở snapshot hiện tại.'),
 ('DATEKEY / LOCAL_DATE / LOCAL_START / UTC','Phép biến đổi ngày theo R03; DATEKEY không được nhận NULL trừ nhánh special đã nêu.'),
 ('LOOKUP_SCD(D,namespace,BK,t)','Chọn đúng một dimension version theo namespace, BK và interval tại t. R07 định nghĩa xử lý thiếu/trùng.'),
 ('DIM_ATTR(D,BK,t,attribute)','Đọc thuộc tính quan hệ từ phiên bản dimension tại t theo R17, không lấy parent hiện hành.'),
 ('INHERIT_VALIDATED(F01.role)','Lấy khóa role từ booking fact hợp lệ cùng namespace/BK trong batch; không join F01 để nhân số tiền.'),
 ('UNION_BRANCH','Biểu thức theo nhánh UNION đã nêu. Hai nhánh không join hồ sơ khách với nhau; namespace là một phần BK.'),
 ('EXISTS / SEMI_EXISTS_EXACTLY1','EXISTS trả 0/1 sau xác minh coverage; semi-join dùng kiểm tra tồn tại, không nhân dòng parent vào kết quả.'),
 ('SUM / COUNT trong F15','Thực hiện trên đúng durable lot key và phạm vi ngày đã ghi, sau kiểm tra ledger completeness; ngày đủ dữ liệu không phát sinh mới trả 0.'),
 ('REGISTRY','Dịch vụ hoặc bảng cấp khóa dùng chung đã đặc tả; stable key không phụ thuộc thứ tự Spark partition.'),
 ('MANIFEST / RUN','Metadata batch đã đóng băng và metadata lần chạy; không lấy ngày hệ thống thay source cutoff.'),
]

def escape(s):return str(s).replace('|','∣').replace('\n',' ')
def build_document(report,examples):
    out=['# Mapping nguồn đến kho dữ liệu CompanyE','',
      'Phiên bản 1.0, ngày 13/10/2026. Đặc tả bước 2 chuyển dữ liệu lake v2 thành mô hình phân tích dùng chung cho Oracle warehouse và Spark Iceberg lakehouse. Kế thừa thiết kế cột 1.1: 14 dimension SCD Type 2, hai dimension cố định và báo cáo vẫn công bố phần hợp lệ kèm cảnh báo thiếu.', '',
      'Tài liệu chỉ rõ nguồn, đường nối, điều kiện lọc, phép tính và xử lý lỗi cho toàn bộ 37 entity và 631 cột đích. Biểu thức là pseudocode quan hệ để triển khai tương đương trên hai engine, chưa phải SQL đã chạy. Nguồn, seed và các hợp đồng trước đó được giữ nguyên.', '',
      '## Cách đọc và phạm vi','',
      'Đọc quy tắc R01–R17 trước, sau đó kế hoạch của từng entity. Mỗi entity có alias nguồn, join cardinality, bộ lọc và các bước biến đổi; bảng cột dùng những alias này. Năm cột audit và năm cột SCD được giải thích đầy đủ một lần trong mục dùng chung, đồng thời có mapping riêng cho từng entity trong JSON.', '',
      'Các công thức và phạm vi KPI đã chốt ở đặc tả KPI vẫn là chuẩn. Khi dữ liệu thiếu, chỉ thay trạng thái chất lượng/phạm vi được tính theo quyết định công bố PARTIAL, không tự sửa công thức để số nhìn hợp lý hơn. Những fixture diễn giải dưới đây không được trộn vào seed v2.', '',
      '**Điểm cần đọc kỹ khi triển khai:** R07 mô tả cả cập nhật SCD và late correction; R11 phân biệt ngày ăn sáng với đêm ở; R12 giữ dòng mua chưa nhận và phân biệt receipt thiếu do lỗi; R13 bảo vệ số dư khi ledger thiếu; R15 quy định báo cáo PARTIAL; R17 tránh nối giao dịch cũ với quan hệ danh mục hiện tại.', '',
      '| Ký hiệu | Ý nghĩa |','|---|---|']
    out += [f'| `{escape(a)}` | {escape(b)} |' for a,b in GLOSSARY]
    out += ['', '## Input lake và các nguồn đối soát','',
      f'Catalog đang đối chiếu: `lake/v2/catalog/catalog.json`, source batch `{catalog["batch_id"]}`. Khi chạy batch khác phải resolve lại catalog, không hard-code ID này. Đường `/workspace/...` là đường container trong catalog, tương ứng thư mục Project khi mount; không giả đó là đường tuyệt đối trên Windows.', '',
      '| Bảng nguồn | Bảng catalog standardized | Entity sử dụng | Vai trò |','|---|---|---|---|']
    for s in source_inventory():out.append(f'| `{s["source_table"]}` | `{s["catalog_table"]}` | '+(', '.join(s['consumers']) or 'Đối soát')+' | '+s['note']+' |')
    out += ['', 'Bốn dataset external đã chuẩn hóa gồm `companye_v2_external.receipt_versions`, `receipt_latest`, `receipt_replays`, `receipt_quarantine`. Các dataset này bổ sung bằng chứng chất lượng và đối soát, không UNION vào FactReceipt. Khác biệt giữa revision hợp lệ mới nhất và revision nhận được mới nhất được ghi theo R14.', '',
      'Hợp đồng JSON kèm source_validation_contracts cho cả 41 bảng: PK, cột bắt buộc, CHECK và 57 FK khai báo trong schema. Đây là kiểm tra đầu vào trước quy tắc nghiệp vụ; không thay thế các điều kiện overlap, ánh xạ liên DB hoặc grain chưa có UNIQUE trong nguồn. Hai UNIQUE bổ sung của revision là (booking_id,revision_no) và (revision_id,booking_room_id); cash_events có XOR ticket_order_id/rental_id theo CHECK nguồn.', '',
      '## Quy tắc biến đổi dùng chung','']
    for r in RULES:
        out += [f'### {r["id"]} {r["title"]}', '',r['explanation'],'']
        out += [f'{i}. {step}' for i,step in enumerate(r['steps'],1)]
        out += ['', '**Ví dụ:** '+r['example'],'']
    out += ['## Cột audit và điều khiển SCD','',
      'Các cột audit áp dụng cho đủ 37 entity. Với view, metadata được chiếu/tính từ input cùng batch hoặc publication manifest, không giả có một lần INSERT vật lý riêng. Cột SCD chỉ áp dụng D02–D09 và D11–D16; D01 và D10 không version hóa.', '',
      '| Cột | Biểu thức | Quy tắc đầy đủ |','|---|---|---|']
    for name,(expr,note) in {**AUDIT,**SCD}.items():out.append(f'| `{name}` | `{escape(expr)}` | {escape(note)} |')
    out += ['', '**Serialization cho hash:** UTF-8 JSON array không whitespace tùy ý; thứ tự trường theo design. NULL là JSON null; chuỗi giữ Unicode nguyên bản; integer dạng thập phân; decimal là chuỗi fixed-scale; timestamp là chuỗi UTC với 6 chữ số microsecond; date ISO YYYY-MM-DD. Oracle và Spark dùng cùng canonical routine hoặc tập kiểm thử xác nhận byte tương đương, không mặc định hai hàm JSON engine cho cùng hash.', '',
      '**Sửa lịch sử:** theo R07, SK gắn ranh giới hiệu lực, version_no chỉ là thứ tự. Không dùng version_no như khóa liên kết từ fact. Trường hợp late correction phải staging toàn lịch sử BK bị ảnh hưởng và công bố cùng rekey fact; đây là một ca kiểm thử cần thực hiện khi viết ETL.', '',
      '## Thứ tự nạp và phụ thuộc','',
      'Thứ tự dưới đây là DAG logic sau chuẩn hóa/quality gate nguồn. Các entity cùng mức không phụ thuộc nhau về target; triển khai có thể chạy tuần tự trên máy local để giảm RAM. Chưa cấu hình Spark job hoặc Oracle transaction tại bước này.', '']
    for i,level in enumerate(report['load_levels'],1):out.append(f'{i}. '+', '.join(f'{x} {targets[x]["name"]}' for x in level)+'.')
    out += ['', 'Trước mức đầu: đóng băng manifest, parse input, kiểm tra PK/domain/master refs, lập các scope lỗi, cấp special members và registry. Sau mức cuối: đối soát, tạo QualityCoverage/MetricQualityStatus, chạy KPI và publish manifest. F15 là tùy chọn; khi không vật hóa thì B07 dùng F14 với cùng công thức và quality rules.', '',
      'L03 chỉ kiểm chứng ref nguồn nên không phụ thuộc F04/F05; các fact dịch vụ mới kiểm tra ref đó có F01 hợp lệ. F11 có luồng validation vận hành riêng từ rental nguồn để lỗi booking_ref không tự làm biến mất ngày xe đã sử dụng.', '',
      '## Kế hoạch và mapping từng entity','']
    for e in ENTITIES:
        t=targets[e['id']]
        out += [f'### {e["id"]} {e["target_name"]}', '',f'**Đích:** `{e["target_physical_name"]}`. **Grain:** {e["grain"]}', '',
                '**Khóa nghiệp vụ đích:** '+'; '.join('`'+', '.join(key)+'`' for key in e['unique_keys'])+'.', '',
                '**Nguồn và alias:** '+('; '.join(f'`{alias}` = `{tab}`' for alias,tab in e['aliases'].items()) or 'Danh mục sinh xác định, không đọc một bảng giao dịch làm grain.')+'.', '',
                '**Điều kiện chọn:** '+e['selection'], '', '**Trình tự biến đổi:**','']
        out += [f'{i}. {step}' for i,step in enumerate(e['process'],1)]
        if e['joins']:
            out += ['', '**Đường nối và cardinality:**', '', '| Điều kiện | Quan hệ và cách nối | Khi không đạt |','|---|---|---|']
            for z in e['joins']:out.append(f'| `{escape(z["condition"])}` | {z["cardinality"]}; {z["join_type"]} | {z["on_error"]} |')
        else:out += ['', 'Không có join nhiều bảng ở grain đầu vào; lookup dimension và kiểm tra master reference vẫn áp dụng theo contract.']
        if t.get('dimension_asof'):out += ['', '**Mốc chọn phiên bản:** '+t['dimension_asof']]
        out += ['', '**Mapping cột nghiệp vụ:**','', '| Cột đích | Kiểu và NULL | Biểu thức biến đổi | Diễn giải |','|---|---|---|---|']
        for c in e['columns']:
            if c['target_column'] in AUDIT or c['target_column'] in SCD:continue
            null='NULL' if c['nullable'] else 'NOT NULL'
            if c['required_for_normal_member']:null+='; bắt buộc NORMAL'
            out.append(f'| `{c["target_column"]}` | {c["type"]}; {null} | `{escape(c["expression"])}` | {escape(c["explanation"])} |')
        out += ['', '**Cột dùng chung:** '+', '.join('`'+c['target_column']+'`' for c in e['columns'] if c['target_column'] in AUDIT or c['target_column'] in SCD)+'. Áp dụng đầy đủ mục audit/SCD ở trên; JSON vẫn chứa một mapping cho từng cột.', '',
                '**Ràng buộc và nghiệm thu:**', '']
        out += ['- '+check for check in e['target_checks']]
        out += ['- Quy tắc áp dụng: '+', '.join(sorted({r for c in e['columns'] for r in c['rule_ids']}))+'.','']
    out += ['## Lớp KPI sau khi nạp fact','',
      'Các phép tính dưới đây thực hiện trên snapshot đã công bố và cùng filter scope. Không chạy nhiều truy vấn mà mỗi truy vấn tự chọn latest batch. Mỗi kết quả trả kèm metric_id, source_batch_id, data_as_of, quality_status và missing_reason.', '',
      '| Nhóm | Phép tổng hợp và điều kiện | Điều cần tránh |','|---|---|---|',
      '| B01 | F03 đêm thực ở; F02 availability; tỷ lệ từ tổng. F01 hủy/no-show theo arrival cohort. | Không dùng kênh/khách lọc capacity chưa phân bổ; không xóa ngày không khách. |',
      '| B02 | F01 COMPLETED theo departure. Tiền giữ lại=gross-company_share-commission. | Không cộng revision/payment, không gọi lợi nhuận/ROI. |',
      '| B03 | Cohort F01 COMPLETED theo departure; aggregate F04 net và F05 COMPLETED riêng về booking. COUNTD booking mua vé net>0 hoặc rental agreed>0. | Không fan-out; không đếm booking mua hai dịch vụ hai lần; tiền gồm phòng+vé+xe đúng tên chỉ tiêu. |',
      '| B04 | F06/F07/F08 tổng riêng theo outlet/service_date/meal. Ratio từ tổng; rating_sum/rating_count. | Không cộng actual_covers lần ba, không tạo doanh thu included breakfast. |',
      '| B05 | F09 admission_date và F10 capacity; F11 rented/available. Weather chỉ join site/day sau xác minh uniqueness. | Không gộp tỷ lệ hoạt động và xe; không coi admission là người duy nhất hoặc lấy ngày bán thay ngày vào. |',
      '| B06 | F12 expected_on trong kỳ và <=A; F13 received_on<=A aggregate theo purchase_line rồi LEFT JOIN. A mặc định 2025-12-31. | Không mất dòng chưa giao; không COALESCE receipt bị lỗi thành 0; không cộng khác base_unit. |',
      '| B07 | Q0=sum signed trước S; Q1=sum signed trước E; U/W trong kỳ. Waste ratio=value waste/(opening value+IN value). | Không lọc bỏ lịch sử trước S, không SUM closing qua ngày, không dùng usage_area lọc tồn. |',
      '| B08 | F16 cost COMPLETED theo ends_on. F02 blocked/available; nguyên nhân riêng qua L02 rồi DISTINCT room/day. | Không nhân cost theo ngày và không để slicer work_type bỏ các nguyên nhân chặn khác khỏi availability. |', '',
      'Quality phải được lan theo đường sử dụng thực tế: B03 cần F01/F04/F05; B01 công suất cần cả F02/F03; B06 tỷ lệ cần F12/F13; B07 số dư cần lịch sử ledger đầy đủ. F17 chỉ ảnh hưởng B05 khi dùng bộ lọc/phân tích weather. Đối soát feed ngoài có cảnh báo riêng, không mặc định làm lượng nhận DB không hợp lệ.', '',
      '## Danh mục lỗi và phần dữ liệu thiếu','', '| Mã | Điều kiện | Xử lý | Ảnh hưởng |','|---|---|---|---|']
    out += ['| '+' | '.join(escape(x) for x in row)+' |' for row in ERRORS]
    out += ['', '**Ví dụ hiển thị báo cáo:** “Doanh thu trên phần dữ liệu hợp lệ — PARTIAL. Đã xử lý 980/1.000 booking; loại 20 dòng do sai tham chiếu khách sạn. Cập nhật theo batch …; chưa bao gồm các giao dịch bị loại.” Nếu chỉ biết nguồn thiếu mà chưa biết số dòng, ghi “Chưa xác định mức đầy đủ”, không hiển thị tỷ lệ coverage giả.', '',
      '**Nguồn lỗi và KPI:** số lượng quarantine theo bảng nguồn không được cộng cơ học qua bảng đích vì một booking lỗi có thể làm nhiều stay-night bị loại. Báo cáo chất lượng lưu cả source_record identity và affected target grain, đồng thời tách direct error với dependency exclusion.', '',
      '## Ví dụ kiểm tra tham chiếu','',
      'Các kết quả sau đã được tính bằng Python độc lập ở mức quy tắc tham chiếu. Chúng giúp chốt kỳ vọng để viết fixture ETL; chưa phải bằng chứng các biểu thức Oracle/Spark hoặc cơ chế SCD2 triển khai thật đã chạy đúng.', '',
      '| Mã | Tình huống | Kết quả kỳ vọng |','|---|---|---|']
    out += [f'| {x["id"]} | {x["description"]} | `{escape(json.dumps(x["expected"],ensure_ascii=False))}` |' for x in examples]
    out += ['', 'Khi triển khai phải bổ sung fixture tích hợp: SCD unchanged/change/A->B->A/late correction và transaction close-open; source thiếu toàn file; FK invalid so với optional NULL; outlet mapping 0/2; over-capacity; room/rental overlap; receipt replay và latest-invalid; ledger thiếu IN; correction interval xóa ngày cũ. Mỗi fixture chạy qua cả hai nhánh và so kết quả cùng quality status, không chỉ so tổng tiền.', '',
      '## Đầu ra và kiểm chứng','',
      f'Kiểm tra đặc tả đã đạt: {report["mapped_entity_count"]} entity, {report["mapped_column_count"]} cột đích, {report["fact_dimension_roles"]} vai trò FK fact-dimension, {report["transformation_rule_count"]} nhóm quy tắc, toàn bộ {report["source_table_count"]} bảng nguồn được phân loại vai trò, {report["reference_example_count"]} ví dụ tham chiếu. DAG load không có chu kỳ; tham chiếu cột và hash đầu vào được kiểm tra.', '',
      f'Kiểm tra đọc trực tiếp nguồn cho ranh giới buffet sáng: {report["breakfast_boundary_source_check"]["checked_entitlements"]} entitlement, không có dòng vi phạm checkin < service_date <= checkout; trong đó {report["breakfast_boundary_source_check"]["checkout_morning_entitlements"]} dòng phục vụ đúng sáng checkout. Điều này xác nhận không dùng điều kiện ngày đêm ở để loại suất sáng checkout.', '',
      'Biểu thức là pseudocode; chưa tạo bảng Oracle/Iceberg hoặc thực thi ETL phân tích. Chưa có nghiệm thu end-to-end, benchmark hoặc kiểm thử xử lý lỗi trên engine. Mapping JSON lưu đầy đủ cột, nguồn, biểu thức, rule IDs, các phụ thuộc và catalog path để dùng ở bước triển khai.', '',
      'Chạy lại từ Project:', '', '```powershell','python -X utf8 scripts/build-source-target-mapping.py','```','',
      'Đầu ra: `config/source_target_mapping_v1.json`, `docs/CompanyE_Source_Target_Mapping.md`, `reports/source_target_mapping_v1_validation.json`, `reports/source_target_mapping_reference_examples.json`. Script không sửa source DB, dữ liệu sinh, seed, lake hoặc design contract.', '']
    return '\n'.join(out)

if __name__=='__main__':
    report,examples=validate()
    mapping=dict(version='companye-source-target-mapping-1.0',created_on='2026-10-13',status='SPECIFICATION_NOT_EXECUTED_ETL',
                 design_contract=design['version'],design_sha256=HASHES[INPUTS[0]],source_batch_id=catalog['batch_id'],
                 source_inventory=source_inventory(),source_validation_contracts=source_validation_contracts(),external_reconciliation_inputs=[{k:x[k] for k in ['dataset_id','catalog_table','standardized_path','row_count']} for x in catalog['derived_datasets']],rules=RULES,error_catalog=[dict(zip(['code','condition','handling','impact'],x)) for x in ERRORS],
                 load_levels=report['load_levels'],entities=ENTITIES,metric_mapping=design['metric_mapping'],input_sha256=HASHES)
    save('config/source_target_mapping_v1.json',mapping)
    (ROOT/'docs/CompanyE_Source_Target_Mapping.md').write_text(build_document(report,examples),encoding='utf-8')
    save('reports/source_target_mapping_reference_examples.json',examples)
    report['output_sha256']={p:sha(p) for p in ['config/source_target_mapping_v1.json','docs/CompanyE_Source_Target_Mapping.md','reports/source_target_mapping_reference_examples.json']}
    save('reports/source_target_mapping_v1_validation.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ['input_sha256','output_sha256']},ensure_ascii=False,indent=2))
