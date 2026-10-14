# Bản đồ tài liệu và phạm vi CompanyE

## Case và tám nhu cầu đã chốt

[CompanyE_Mo_ta_case.md](../Project/CompanyE_Mo_ta_case.md) là mô tả doanh nghiệp của project này. CompanyX thuộc môn học khác, không phải tên thay thế và không đưa backup CompanyX vào repo.

| Mã | Phạm vi nghiệp vụ | Trọng tâm phân tích |
|---|---|---|
| B01 | Lưu trú | Công suất, đêm phòng và hiệu quả doanh thu lưu trú |
| B02 | Kênh bán và khuyến mãi | Kết quả kênh bán, tài trợ discount, hoa hồng và đối soát |
| B03 | Tương tác khách sạn – giải trí | Bán chéo dịch vụ trong hệ sinh thái |
| B04 | Buffet và nhà hàng | Sử dụng suất ăn, doanh thu và chi phí theo quy tắc gói phòng |
| B05 | Giải trí và phương tiện | Khai thác dịch vụ, lượt sử dụng và doanh thu |
| B06 | Giao hàng nhà cung cấp | Lượng đặt/nhận/từ chối, giao đúng hạn và đủ hàng |
| B07 | Tồn kho và hao hụt | Biến động kho, tồn tại thời điểm và đơn vị hàng hóa |
| B08 | Bảo trì và khả năng cung cấp phòng | Chi phí bảo trì và thời gian ngừng khai thác |

Tên KPI, công thức, ngày đo và bộ lọc chuẩn nằm trong [đặc tả KPI](../Project/docs/CompanyE_KPI_Specification.md) và [contract máy đọc](../Project/config/kpi_contract_v1.json). Bảng trên là chỉ mục đọc, không thay thế đặc tả.

## Từ ý niệm tới vật lý

| Tầng thiết kế | Tài liệu / sơ đồ |
|---|---|
| Tổng quan quy trình và dimension dùng chung | [Bus matrix PDF](../Project/docs/CompanyE_Bus_Matrix.pdf), [ma trận chi tiết](../Project/docs/CompanyE_Dimensional_Matrices.md) |
| Nguồn nghiệp vụ | [Enterprise/source ERD PDF](../Project/docs/CompanyE_Enterprise_Source_ERD.pdf), [draw.io](../Project/docs/CompanyE_Enterprise_Source_ERD.drawio) |
| Ý niệm warehouse | [Conceptual PDF](../Project/docs/CompanyE_Conceptual_Warehouse_Model.pdf), [draw.io](../Project/docs/CompanyE_Conceptual_Warehouse_Model.drawio) |
| Dimensional model | [PDF](../Project/docs/CompanyE_Dimensional_Model.pdf), [draw.io](../Project/docs/CompanyE_Dimensional_Model.drawio) |
| Luận lý v1.1 | [PDF](../Project/docs/CompanyE_Logical_Model_v1_1.pdf), [draw.io](../Project/docs/CompanyE_Logical_Model_v1_1.drawio), [JSON](../Project/config/logical_model_v1_1.json) |
| Thiết kế chi tiết | [Warehouse detailed design](../Project/docs/CompanyE_Warehouse_Detailed_Design.md) |
| Biến đổi nguồn → đích | [Source-target mapping](../Project/docs/CompanyE_Source_Target_Mapping.md), [JSON](../Project/config/source_target_mapping_v1.json) |
| Vật lý | [Physical design](../Project/docs/CompanyE_Physical_Design.md), [DDL](../Project/config/analytics/ddl/) |

Các file PDF là bản trình bày; draw.io là bản có thể sửa; JSON được dùng cho validation và triển khai. File XLSX ma trận cũ được giữ để truy vết, còn bản trình bày chính là PDF.

## Quyết định cần giữ khi phát triển tiếp

- Cùng dữ liệu, grain, KPI và phạm vi lọc khi so Oracle warehouse với Iceberg lakehouse.
- Dimension có chính sách SCD Type 2 dù bản nguồn hiện tại chủ yếu là danh mục hiện hành. Fixture riêng kiểm tra phiên bản, hiệu lực, replay; không tự bịa lịch sử thay đổi vào dữ liệu gốc.
- Có thể công bố tập dữ liệu hợp lệ khi một phần bị lỗi, nhưng phải báo PARTIAL/thiếu và ảnh hưởng KPI. Không âm thầm lấy dữ liệu cũ lấp chỗ thiếu của batch mới.
- Buffet kèm phòng không làm phát sinh doanh thu lần hai. Tỷ lệ tính từ tổng tử/mẫu; mẫu số 0 trả BLANK. Tồn kho không cộng qua ngày; số lượng khác đơn vị không cộng chung.
- File vendor là biểu diễn/phiên bản của nghiệp vụ nguồn, không phải giao dịch mới để cộng lần nữa. Quarantine và lịch sử sửa đổi được giữ để đối soát.
- Web là ứng dụng trung tính; không gắn nhãn đối tượng người chấm/người tuyển dụng trong giao diện.

