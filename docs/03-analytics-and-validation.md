# ETL, công bố batch, 47 KPI và ứng dụng

**Trạng thái kiến trúc:** [thiết kế A/B mới](05-architecture-alternatives.md) bổ sung Silver Iceberg và yêu cầu B chạy độc lập với Oracle. Các launcher và lệnh bên dưới mô tả runtime đã triển khai trước thay đổi; chưa phải runbook cho B mới. Migration cần tách reader/adapter, catalog và publication theo đặc tả, rồi kiểm chứng lại trước khi thay nguồn BI.

## Mã nguồn được bàn giao

| Giai đoạn | Mã chính | Bằng chứng lịch sử |
|---|---|---|
| Runtime Oracle/Spark/Iceberg | `Project/scripts/analytics-services.py`, `Project/src/analytics_runtime/session.py` | `Project/reports/analytics-runtime/verification.json` |
| Schema vật lý | `Project/config/analytics/ddl`, `Project/scripts/deploy-analytics-schema.py` | `Project/reports/schema-deployment/verification.json` |
| Dimension/SCD2 | `Project/src/analytics_runtime/dimensions.py`, `scd2.py`, `dimension_transform.py` | `Project/reports/dimension-etl/verification.json` |
| Fact/bridge | `Project/src/fact_etl` | `Project/reports/fact-etl/verification.json` |
| Công bố batch, snapshot, reader lease | `Project/src/publication` | `Project/reports/publication/verification.json` |
| SQL KPI và tham chiếu độc lập | `Project/src/semantic`, `Project/reports/semantic/sql` | `Project/reports/semantic/verification.json` |
| Power BI | `Project/powerbi`, `Project/scripts/build-powerbi*.py` | `Project/reports/powerbi` |
| Web | `Project/web/companye-demo` | `Project/reports/web-demo` |

Đọc quy tắc trong [source-target mapping](../Project/docs/CompanyE_Source_Target_Mapping.md) trước khi thay code. Thay đổi logic phải có phiên bản và đối soát lại; không sửa expected values để khớp một pipeline đang sai.

## Trình tự vận hành nhánh phân tích

Các lệnh sau phản ánh các launcher đã triển khai. Đây là runbook theo giai đoạn, **chưa phải một nút cold-start đã nghiệm thu toàn bộ trên máy mới**. Chạy trong một bản làm việc `Project` có lake v2/catalog của chính lần chạy đó; không lấy catalog lịch sử trong `evidence/lake` trỏ tới dữ liệu mới.

Không chạy trực tiếp trên bản gốc có publication đã đóng băng để thử schema lần đầu. Không chạy analytics trong shell còn đặt `COMPOSE_PROJECT_NAME` cho nền tảng; Compose analytics gốc dùng namespace `companye-analytics`, các cổng/volume cần tách riêng nếu trên cùng máy đã có một bản đang chạy.

```powershell
# Runtime và JAR
python -X utf8 scripts/analytics-services.py prepare
python -X utf8 scripts/analytics-services.py up
python -X utf8 scripts/analytics-services.py bootstrap
python -X utf8 scripts/analytics-services.py jars
python -X utf8 scripts/analytics-probe.py write
python -X utf8 scripts/analytics-probe.py verify

# Schema (dành cho namespace đích mới)
python -X utf8 scripts/deploy-analytics-schema.py oracle
python -X utf8 scripts/deploy-analytics-schema.py verify-oracle
python -X utf8 scripts/deploy-analytics-schema.py iceberg

# Dimension trước, fact sau
python -X utf8 scripts/dimension-pipeline.py bootstrap
python -X utf8 scripts/dimension-pipeline.py run
python -X utf8 scripts/dimension-pipeline.py verify
python -X utf8 scripts/dimension-pipeline.py fixtures
python -X utf8 scripts/fact-pipeline.py bootstrap
python -X utf8 scripts/fact-pipeline.py run
python -X utf8 scripts/fact-pipeline.py verify

# Publication, sau đó mới cho reader/KPI dùng batch
python -X utf8 scripts/publication.py bootstrap
python -X utf8 scripts/publication.py fixtures
python -X utf8 scripts/publication.py prepare
python -X utf8 scripts/publication.py publish
python -X utf8 scripts/publication.py verify

# KPI và các lát cắt nghiệp vụ
python -X utf8 scripts/kpi-pipeline.py baseline
python -X utf8 scripts/kpi-pipeline.py fixtures
python -X utf8 scripts/kpi-pipeline.py slices
```

Các lệnh `finalize-*.py` tập hợp chứng cứ, kiểm tra thêm và đóng băng mã của từng mốc. Chúng không thay thế pipeline/verification và có thể cần log, canonical payload hoặc runtime của lần chạy. Một số payload lớn và log không đóng gói trong Git; cần sinh lại trước khi gọi các lệnh này. Các script `verify-fact-etl.py`, `test-analytics-schema.py` chứa kiểm tra độc lập/fixture bổ sung; đọc phần CLI trước khi dùng trên runtime mới.

## Quy trình kiểm chứng KPI

1. Contract kiểm tra đủ B01–B08, 47 KPI, nguồn/cột, grain, công thức, bộ lọc và ví dụ tính tay.
2. ETL kiểm tra ràng buộc, tham chiếu, SCD2, replay, đối soát lượng/tiền; giữ quarantine và lineage.
3. Publication buộc reader nhìn cùng một publication của hai nhánh, kèm trạng thái chất lượng.
4. Semantic SQL so Oracle và Iceberg với tham chiếu đọc raw nghiệp vụ độc lập; không tái sử dụng truth của generator hoặc transformer làm đáp án.
5. Kiểm tra slices và fixture cho mẫu số 0, BLANK, dữ liệu thiếu, ngày nghiệp vụ, đơn vị, doanh thu suất ăn và các chính sách khác.
6. Power BI kiểm chứng DAX rồi kiểm tra filter, tổng, biểu đồ và cảnh báo UI. Web tiếp tục đối chiếu mọi thành phần số với kết quả đã lưu.

## Power BI và web

PBIP/PBIR và model BIM được giữ trong Git. CSV Import, `.pbi/cache.abf`, desktop session và thư viện cài sẵn được loại bỏ. Vì không có CSV, mở PBIP từ clone chưa thể refresh ngay. Model hiện còn đường dẫn của máy tạo; cần xuất dữ liệu rồi rebuild/rebase các nguồn M cho thư mục mới trước khi mở Desktop.

Các entrypoint: `scripts/export-powerbi.py` → `scripts/build-powerbi.py` → `scripts/build-powerbi-dashboard.py`. Dashboard đang khóa publication `pub_3f41f8fafa4c913187af2cc3` và các điều kiện chất lượng của bộ dữ liệu chuẩn; batch mới có ID khác cần một lần chuyển phiên bản có kiểm chứng. Không sửa assertion cho chạy qua. Các script DAX qua ADOMD dùng SSMS 20 ở đường dẫn Windows cụ thể và cần endpoint Desktop đang mở; đó không phải dịch vụ backend có thể chạy headless từ repo.

Để chạy validator PBIR ngoài môi trường cũ, cài `jsonschema` và `referencing` theo phiên bản yêu cầu/khả dụng rồi kiểm tra schema cache. Để dựng lại PDF sơ đồ cần ReportLab và font Windows được nêu trong script; PDF đã có sẵn để đọc, không cần dựng lại. Bộ dependency test chính có lock riêng trong `Project/testing`.

Web là HTML/CSS/JavaScript và snapshot JSON, có thể xem độc lập. Nó có 104 ngữ cảnh SQL đã lưu và 48 hàng kết quả theo engine/tháng; không giả lập mọi tổ hợp bộ lọc tùy ý. `verify.py` đối chiếu snapshot với semantic/DAX reports. Có `noindex`, nhưng đây không phải xác thực truy cập và không ảnh hưởng chế độ public của GitHub.

