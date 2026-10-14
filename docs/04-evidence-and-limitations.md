# Bằng chứng kiểm chứng và giới hạn

## Lakehouse B độc lập

Bằng chứng mới được lưu riêng tại [reports/lakehouse-b/summary.json](../Project/reports/lakehouse-b/summary.json): Silver/Gold manifest và snapshot, 47 KPI baseline, 96 slices, SQL/policy/SCD/publication fixtures, cùng trạng thái trước/ngắt/sau công bố. Đáp án KPI đọc raw độc lập; Oracle được đối chiếu bằng kết quả lịch sử, không có truy vấn Oracle mới trong runtime B. [Runbook B](06-independent-lakehouse.md) mô tả cách tái lập và giới hạn. Không dùng kết quả này để thay thế nghiệm thu Power BI hoặc benchmark.

## Kết quả lịch sử được giữ nguyên

| Lớp | Kết quả đã lưu | File kiểm tra chính |
|---|---|---|
| Nguồn/lake | 106 ca test thành công trong lần chạy v2 đã chốt | [summary](../Project/reports/testing/20261012T092133914051Z/summary.json), [cases](../Project/reports/testing/20261012T092133914051Z/cases.jsonl) |
| Dimension | 16 dimension, có fixture SCD2 | [verification](../Project/reports/dimension-etl/verification.json) |
| Fact ETL | 16 fact, 2 bridge, 2 helper; 48 đối chứng độc lập; 771.564 dòng logic/nhánh gồm dimension | [verification](../Project/reports/fact-etl/verification.json) |
| Publication | Cơ chế công bố, snapshot và reader lease với fault fixtures | [verification](../Project/reports/publication/verification.json), [fixtures](../Project/reports/publication/fixtures.json) |
| KPI | 47 so sánh baseline; 96 slices/546 so sánh; 20 SQL fixture/117 kiểm tra; 15 policy check | [verification](../Project/reports/semantic/verification.json), [KPI Results](../Project/reports/semantic/KPI_Results.md) |
| Power BI DAX | 202 truy vấn, 1.148 phép kiểm tra giá trị | [DAX verification](../Project/reports/powerbi/dax-verification.json) |
| Dashboard | 57 truy vấn, 457 phép kiểm tra giá trị biểu đồ | [verification](../Project/reports/powerbi/dashboard/verification.json), [UI](../Project/reports/powerbi/dashboard/ui-verification.json) |
| Web | Đối chiếu snapshot và kiểm tra giao diện đã triển khai | [verification](../Project/web/companye-demo/verification.json), [online verification](../Project/reports/web-demo/online-verification.json) |

Những kết quả trên có timestamp và ID của lần chạy lịch sử. Mỗi lớp chỉ chứng minh phạm vi của nó: test nguồn không chứng minh 47 KPI đúng; kiểm tra JSON schema không chứng minh UI/DAX đúng; đối soát số liệu không phải benchmark.

## Kiểm tra khi đóng gói repo

Ngày 14/10/2026, gói mới đã dựng nguồn và lake v2 trong Docker namespace riêng, kiểm tra lại seed, rồi dựng tiền điều kiện lake v1 và chạy **106/106 ca nguồn/lake thành công**. Cùng lần đóng gói còn chạy 16 fixture fact và 3.138 kiểm tra web. Xem [tổng kết tái lập mới](../evidence/reproduction/summary.json) và [kiểm tra bổ sung](../evidence/reproduction/packaging-checks.json). Lỗi thiếu tiền điều kiện v1 ở lần test đầu được giữ tại `evidence/reproduction/initial-test-attempt`; bản sửa chỉ thêm bước chuẩn bị môi trường, không đổi test hay dữ liệu kỳ vọng.

Chạy `python -X utf8 scripts/verify-repository.py` để kiểm tra file copy theo SHA-256, parse Python và phát hiện một số dấu hiệu credential phổ biến. Công cụ không bảo đảm phát hiện mọi loại bí mật; lúc đóng gói còn đối chiếu nội dung với credential local đã biết, không ghi giá trị bí mật ra báo cáo.

`evidence/assembly-inventory.json` ghi file giữ lại và file loại ra, kèm lý do/checksum khi thích hợp. Không ghi danh sách/hash các secret file. `evidence/repository-adaptations.json` ghi các file có điều chỉnh sau khi copy; không âm thầm cập nhật hash gốc. File PDF, draw.io, mã sinh và kết quả lịch sử được giữ nguyên byte.

Lần sinh lại trong gói kiểm tra tất cả file v2 và payload nghiệp vụ v1 so với bản gốc. Audit v1 có khác biệt duy nhất ở trường phiên bản Python 3.11.9 → 3.12.14; được ghi riêng, không gọi đó là toàn bộ file giống từng byte. Kết quả mới được lưu riêng dưới `evidence/reproduction/`, còn bản chạy chi tiết ở `.work/platform/Project/reports`.

## Không bao gồm trong Git

- `.env`, `.secrets`, token hosting, Git repo vận chuyển của dịch vụ web, cấu hình session/cache trên máy.
- DB dump, CSV/raw/Parquet có thể sinh lại, volume Docker, dependency cài sẵn, Power BI cache/import CSV.
- Một số payload row-level lớn, log runtime và các test run cũ trước lần v2 đã chốt. Hash/đường dẫn có thể vẫn xuất hiện trong report gốc để truy vết. Thiếu file trong clone không có nghĩa report đã bị sửa; xem inventory hoặc sinh lại.
- Slide, giáo trình, đề bài gốc và danh sách sinh viên của môn học. Tài liệu project vẫn có thể dẫn tên/đường dẫn tài liệu tham khảo trên máy tác giả; đường dẫn đó không có trong clone.

## Giới hạn cần công bố khi đánh giá

- Phân bố dữ liệu là giả định mô phỏng. Không suy ra tác động nhân quả hoặc hiệu quả kinh doanh thật từ dữ liệu này.
- Nguồn “phân tán” được mô phỏng qua miền nghiệp vụ, ID, file, revision và chất lượng; chưa dựng mạng nhiều địa điểm.
- Một số transform thu dữ liệu về driver và giới hạn 100.000 dòng/bảng nguồn; chưa phải pipeline phân tán ở quy mô doanh nghiệp lớn.
- SCD2 và publication có fixture, nhưng không đồng nghĩa đã có vận hành CDC/incremental production hoàn chỉnh.
- Dashboard Import được chứng nhận với publication COMPLETE đã chốt. QA có mô phỏng PARTIAL; chưa tự refresh một publication PARTIAL bất kỳ thành báo cáo chính thức.
- Web dùng snapshot; Power BI Import đo tương tác trong engine BI, không dùng tốc độ UI để kết luận Oracle nhanh hơn Spark hoặc ngược lại.
- Chưa hoàn tất benchmark có kiểm soát, đánh giá hỗ trợ quyết định, và hồ sơ nộp cuối môn.
- Gói nền tảng có kiểm tra riêng; không tuyên bố đã tái lập cold-start toàn bộ Oracle/Iceberg/Power BI trên máy mới.
