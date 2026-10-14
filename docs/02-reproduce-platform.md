# Gói tái lập nền tảng: seed → nguồn → data lake/catalog

## Phạm vi và điều kiện

Gói nền tảng gồm mã sinh v1/v2, seed/config, schema nguồn, external feed, PostgreSQL, Spark, Parquet, catalog Hive/Derby, metadata, quarantine và bộ kiểm thử. Oracle/Iceberg nằm ở giai đoạn tiếp theo, không cần bật để chạy phần này.

- Python 3.11 hoặc 3.12 trên host; generator dùng thư viện chuẩn. Bản lịch sử dùng 3.11.9; lần đóng gói đã đối chiếu trên 3.12.14.
- Docker Engine/Desktop với Linux containers và Docker Compose v2. Các image cần tải ở lần đầu.
- Cấu hình nền tảng giới hạn PostgreSQL 1 GB, Spark 3 GB; bộ test dùng PostgreSQL 1 GB và tester 4 GB. Đây là giới hạn container, chưa bao gồm Docker/OS và các dịch vụ khác. Không chạy benchmark song song với hệ thống đang dùng.
- Chuẩn bị vài GB trống cho dữ liệu sinh, lake và báo cáo, thêm dung lượng cho Docker images. Không coi kích thước repo là dung lượng chạy.
- Cổng PostgreSQL của gói mới mặc định `127.0.0.1:55433`. Nếu bận, chọn `--port 55434` ngay từ lần chuẩn bị đầu tiên và dùng nhất quán.

Trên máy đã chuyển Docker sang ổ E, named volumes mới dùng vị trí lưu của Docker hiện tại. Repo không đổi Docker disk location hoặc hard-code ổ E trên máy khác.

## Thứ tự chạy

Từ root repo:

```powershell
# 1. Kiểm tra file đóng gói (không cần Docker)
python -X utf8 scripts/verify-repository.py

# 2. Tạo workspace riêng và sinh hai phiên bản nguồn
python -X utf8 scripts/platform.py generate
python -X utf8 scripts/platform.py verify-seed

# 3. PostgreSQL và Spark riêng
python -X utf8 scripts/platform.py up

# 4. Hai database v2; không drop database đang tồn tại
python -X utf8 scripts/platform.py load

# 5. COPY snapshot và nhận external feed thành raw batch mới
python -X utf8 scripts/platform.py ingest

# 6. Chuẩn hóa, xử lý replay/revision, quarantine và catalog
python -X utf8 scripts/platform.py lake
python -X utf8 scripts/platform.py verify

# 7. Bộ kiểm thử độc lập: nguồn v1/v2 + Spark + GX + đối chứng
python -X utf8 scripts/platform.py test

# 8. Dừng dịch vụ của gói, giữ dữ liệu để xem lại
python -X utf8 scripts/platform.py stop
```

`all` tương đương generate → up → load → ingest → lake → verify, nhưng không bao gồm `test`. `test` còn tự dựng lake v1 và golden aggregates trong cùng workspace nếu chưa có, vì các ca lake/GX gốc dùng snapshot v1 làm đầu vào. Mỗi lần `ingest` tạo batch mới với timestamp mới. Không kỳ vọng batch ID, metadata thời gian hoặc snapshot ID khớp bản lịch sử.

Script root chép nguyên byte mã sinh và cấu hình vào `.work/platform/Project`; lock tại `.work/platform/inputs.json` ngăn đổi input âm thầm trong cùng lần tái lập. Compose project có tên riêng theo đường dẫn workspace. `test` dùng project hậu tố `-tests`, không mở cổng DB ra host, và dọn container test sau khi kết thúc. `stop` không xóa volume.

Nếu lock/input khác, script dừng. Giữ lại workspace và chạy từ một clone/worktree mới để thử phiên bản khác. Không đổi seed rồi ghi đè manifest/baseline cũ.

## Đầu ra

Mọi đường dẫn dưới đây tương đối với `.work/platform/Project`:

| Đầu ra | Ý nghĩa |
|---|---|
| `generated/v1`, `generated/v2` | CSV, schema, load SQL, feed, manifest và audit-only |
| `databases/*.dump` | Backup PostgreSQL sinh trong lần chạy; không đưa vào Git |
| `lake/v2/raw/<batch>` | Raw bất biến, checksum, nguồn và thời điểm nhận |
| `lake/v2/standardized` | Parquet đã xử lý |
| `lake/v2/catalog/catalog.json` | Danh mục dataset, schema, lineage, row count và trạng thái chất lượng |
| `lake/v2/catalog/hive_state` | Metastore embedded của Spark SQL |
| `reports/source_v2_validation.json` | Ràng buộc nguồn và đối soát |
| `reports/lake_v2_validation.json` | Kiểm chứng lake/catalog |
| `reports/repository-seed-check.json` | So sánh seed mới với bản lịch sử |
| `reports/testing/<run>` | Kết quả test mới, JUnit XML, cases JSONL và summary |

Catalog v2 có 30 bảng hotel, 11 bảng entertainment, 4 bảng external và 4 bảng metadata. Trong bản chuẩn, external feed có 267 dòng → 252 phiên bản hợp lệ + 12 quarantine + 3 replay; còn 228 phiếu hiện hành và 24 phiên bản lịch sử. Không dùng `audit_only` làm đầu vào ETL.

## Tái lập có nghĩa gì ở đây?

Giữ seed, config, mã sinh và dữ liệu đối chứng. Manifest lưu SHA-256 của các file sinh; mã sinh cũng được băm và đóng băng trong `Project/reports/reproducibility`. `.gitattributes` không tự đổi line ending khi clone, vì đổi CRLF/LF cũng có thể phá checksum mã sinh.

Phép kiểm tra của gói chấp nhận đúng một khác biệt metadata đã biết: `python_version` trong audit v1 khi dùng Python khác 3.11.9. Nó vẫn yêu cầu tất cả payload nghiệp vụ, schema, config, mã sinh và các trường audit còn lại khớp. Nếu có khác biệt khác, dừng và điều tra; không tự sửa kỳ vọng.

PostgreSQL/Spark của gói nền dùng tag trong Compose gốc. Image ID/digest đã dùng trước đây có trong hồ sơ reproducibility; tag có thể thay đổi theo thời gian. Đây không phải cam kết tái lập byte toàn bộ hệ điều hành/container. Nhánh analytics có image/JAR pin riêng trong cấu hình.

