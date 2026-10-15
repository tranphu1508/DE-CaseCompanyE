# Power BI và web của Lakehouse B độc lập

Mốc nghiệm thu B: `b_5531e032ac7d45b6eb0b`. Mốc Oracle A đối chứng: `pub_3f41f8fafa4c913187af2cc3`. Các ID này là kết quả chạy, không phải giá trị để tự sửa trong dữ liệu nhằm vượt kiểm tra.

## Luồng xuất và mô hình

`Project/src/bi_migration/export_b.py` mở Reader của B, ghim publication và snapshot từng bảng, gia hạn lease rồi xuất CSV bất biến. Script kiểm trạng thái nghiệm thu trước khi xuất và kiểm số dòng với manifest. 32 entity được xuất; các bảng hồ sơ khách hàng và liên kết định danh không đưa vào BI. CSV giao dịch vẫn chỉ lưu local, được Git bỏ qua.

`scripts/migrate-bi.py build` dùng lại builder và công thức DAX đã kiểm chứng trong thư mục scratch. B dùng toàn bộ dimension/fact và surrogate key riêng. Không nối fact B với dimension Oracle. Adapter chỉ thay engine mặc định, đường dẫn CSV và attribution của publication; giữ công thức 47 KPI. Bản `Project/powerbi` lịch sử được bảo toàn; bản mới nằm ở `Project/powerbi-b/CompanyE-B.pbip`.

Power BI dùng Import từ CSV xuất theo snapshot, không phải DirectQuery tới Spark. Kết quả web gồm hai payload riêng theo engine và publication; Oracle là kết quả lịch sử đã chứng nhận, B là kết quả mới. Website không chạy truy vấn live.

## Chạy lại trên máy

Trước tiên hoàn tất runtime và nghiệm thu theo [runbook B](06-independent-lakehouse.md). Giai đoạn này yêu cầu publication trong `.work/lakehouse-b/reports` khớp bộ bằng chứng B đã đóng gói trong `Project/reports/lakehouse-b`. Batch khác cần được nghiệm thu riêng trước khi đưa lên BI; không sửa ID thủ công.

Từ gốc repo, khi Power BI B đã đóng:

```powershell
python -X utf8 scripts/migrate-bi.py export
python -X utf8 scripts/migrate-bi.py build
python -X utf8 scripts/migrate-bi.py prepare-tests
```

`export` cần Docker B đang chạy và hai JAR đã pin. `build` không cần Oracle; dùng thư mục `.work/bi-b` để tạo và làm giàu F01/F12 phục vụ DAX. CSV local được kiểm checksum trước build. Đường dẫn Import được dựng lại theo vị trí checkout hiện tại. Đừng chạy build trong khi đang chỉnh sửa report B trên Desktop vì Desktop có thể ghi đè bản vừa sinh.

Mở `Project/powerbi-b/CompanyE-B.pbip`, bấm Refresh để nạp dữ liệu. Khi lưu, chọn **Don't upgrade** nếu Desktop hỏi chuyển model sang TMDL; công cụ hiện dùng `model.bim`. Không Publish lên Power BI Service để chạy demo này.

Để chạy kiểm thử tự động, lấy cổng của phiên Desktop từ `msmdsrv.port.txt` trong `C:\Users\OEM\AppData\Local\Microsoft\Power BI Desktop\AnalysisServicesWorkspaces\...\Data`. Cổng và database ID thay đổi mỗi lần mở. `Project/scripts/query-powerbi.ps1` với `Project/reports/powerbi/catalog-query.txt` trả database ID. Phải chọn phiên B; xác nhận bằng measure `[Publication]` trước khi thao tác.

Dùng **Windows PowerShell 5.1** (`powershell.exe`), không phải PowerShell 7, vì thư viện ADOMD/TOM hiện tại thuộc .NET Framework của SSMS 20:

```powershell
# Thay <port> và <database> bằng thông tin của phiên B hiện tại.
powershell.exe -NoProfile -File scripts/refresh-bi-b.ps1 -Server localhost:<port> -Database <database> -Publication b_5531e032ac7d45b6eb0b
powershell.exe -NoProfile -File Project/scripts/query-powerbi.ps1 -Server localhost:<port> -Database <database> -VectorsFile Project/reports/bi-migration/dax-test-vectors.json -OutputFile Project/reports/bi-migration/dax-results.json
powershell.exe -NoProfile -File Project/scripts/query-powerbi.ps1 -Server localhost:<port> -Database <database> -VectorsFile Project/reports/bi-migration/chart-vectors.json -OutputFile Project/reports/bi-migration/chart-results.json
powershell.exe -NoProfile -File Project/scripts/query-powerbi.ps1 -Server localhost:<port> -Database <database> -VectorsFile Project/reports/bi-migration/acceptance-vectors.json -OutputFile Project/reports/bi-migration/acceptance-results.json
python -X utf8 scripts/migrate-bi.py verify
```

Refresh bằng TOM là lựa chọn thay thao tác Refresh trên giao diện. Script kiểm đúng publication B và expression của từng partition trước khi nạp, không sửa report A. Máy khác cần điều chỉnh đường dẫn thư viện SSMS nếu cài ở vị trí khác. Không đưa cổng/database phiên Desktop vào config cố định.

## Phạm vi đã kiểm chứng

- DAX: 101 truy vấn, 574 lượt kiểm KPI (tử, mẫu, giá trị, trạng thái), đối chiếu kết quả SQL B.
- Biểu đồ/thẻ số: 32 truy vấn, 232 giá trị; chuỗi tháng đối chiếu tổng hợp CSV độc lập, thẻ tiền đối chiếu baseline SQL. Có kiểm tháng ngoài kỳ, tháng không trọn vẹn, chọn nhiều kỳ và thiếu mặt hàng.
- Ba context SQL chưa hỗ trợ trong Desktop: hai bộ lọc thời tiết và ngày đánh giá B06 biến đổi. Đây là loại trừ được ghi trong báo cáo kiểm thử, không tính là đạt.
- QA trên Desktop mô phỏng COMPLETE, PARTIAL, UNAVAILABLE và mẫu số 0. Đây là dữ liệu kiểm thử riêng, không phải batch B đang thiếu dữ liệu.
- Giao diện được kiểm đại diện ở tổng quan, lọc tháng, QA, rồi mở lại bản lưu. Không tuyên bố đã bấm mọi tổ hợp slicer; DAX kiểm các context được liệt kê trong vectors.
- Web: đối chiếu riêng cả hai nguồn cho 104 context, 5.930 thành phần KPI và 48 dòng engine/tháng; kiểm UI tám nhóm nghiệp vụ, đổi engine, bộ lọc, cảnh báo và CSV.

B vẫn COMPLETE với 12 cảnh báo đối soát feed ngoài. Hai nguồn bằng số không chứng minh hiệu năng bằng nhau. Chưa thực hiện benchmark có kiểm soát.

## Xuất và triển khai web

```powershell
python -X utf8 Project/web/companye-demo/export.py
python -X utf8 Project/web/companye-demo/verify.py
node --check Project/web/companye-demo/dist/app.js
python -m http.server 5173 --bind 127.0.0.1 --directory Project/web/companye-demo/dist
```

Exporter dừng nếu nghiệm thu SQL/DAX/biểu đồ không đạt hoặc publication không khớp. Thông tin chất lượng ngoài phạm vi được ưu tiên trước cảnh báo mẫu số 0; NULL không đổi thành 0. CSV tải từ web ghi publication của nguồn đang chọn.

Push lên `main` kích hoạt `.github/workflows/pages.yml`; workflow kiểm payload rồi chỉ upload thư mục `dist`. URL chính: https://tranphu1508.github.io/DE-CaseCompanyE/. Vẫn giữ `noindex, nofollow, noarchive` ; robots cho phép crawler đọc thẻ noindex; đây không phải kiểm soát truy cập. Bằng chứng UI cũ được giữ nguyên, bằng chứng chuyển B ở `Project/reports/bi-migration`.
