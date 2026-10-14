# Nghiệm thu lakehouse B độc lập

Publication: `b_5531e032ac7d45b6eb0b`. Batch nguồn: `v2_20261014T124040450684Z`.

| Kiểm tra | Kết quả |
|---|---|
| Silver | 45 bảng; 41 bảng nghiệp vụ và 4 bảng chứng từ |
| Gold | 36 bảng, 771,564 dòng logic |
| KPI baseline | 47 phép so sánh đạt |
| Bộ lọc | 96 ngữ cảnh, 546 phép so sánh đạt |
| SQL fixture tính tay | 20 ca, 117 phép kiểm tra đạt |
| Chính sách | 15 ca đạt |
| Publication/SCD | 10 ca đạt |
| Lỗi trước công bố | PREPARED, active pointer vẫn rỗng; chạy lại công bố thành công |
| Oracle | Không kết nối; đối chiếu báo cáo Oracle lịch sử và raw độc lập |

Đọc [summary.json](summary.json) để xem hash code/config/report và log lỗi chủ động. [silver.json](silver.json) và [gold.json](gold.json) ghi schema, count, content hash và snapshot ID của từng bảng. [fixtures.json](fixtures.json) ghi rõ từng ca; [verification.json](verification.json) ghi phạm vi kiểm chứng.

Các báo cáo ở đây không thay thế bằng chứng Power BI/web lịch sử hoặc benchmark. Runtime dùng initial batch và retry; chưa chứng nhận CDC hay vận hành ở quy mô phân tán. Xem [runbook](../../../docs/06-independent-lakehouse.md).
