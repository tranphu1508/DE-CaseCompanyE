# Chạy lakehouse B độc lập

Entrypoint mới là `scripts/lakehouse.py`, chạy từ **gốc repository**, không phải thư mục `Project`. Mã triển khai nằm trong `Project/src/lakehouse_b`. Runtime lịch sử và các báo cáo Oracle/Power BI được giữ nguyên để đối chiếu.

## Chuẩn bị và chạy từng bước

Cần Python 3.11/3.12 trên máy chủ, Docker Desktop Linux containers, dữ liệu raw v2 và catalog của chính lần ingest đó. Launcher dùng thư viện chuẩn Python; Spark và các thư viện xử lý chạy trong container. Image và SHA-256 của JAR được lấy từ `Project/config/analytics_runtime_lock_v1.json`. B không cài Oracle JDBC.

Nếu chưa có raw, làm theo [runbook nền tảng](02-reproduce-platform.md) và chạy `scripts/platform.py all`. B chỉ lấy raw cùng catalog từ kết quả đó; không lấy standardized Parquet. Khi chạy riêng B lâu dài, các dịch vụ nền tảng có thể dừng sau ingest.

```powershell
python -X utf8 scripts/lakehouse.py prepare
python -X utf8 scripts/lakehouse.py up
python -X utf8 scripts/lakehouse.py ingest
python -X utf8 scripts/lakehouse.py silver
python -X utf8 scripts/lakehouse.py explore
python -X utf8 scripts/lakehouse.py gold
python -X utf8 scripts/lakehouse.py publish
python -X utf8 scripts/lakehouse.py verify
python -X utf8 scripts/lakehouse.py fixtures
```

`all` chạy các bước trên theo thứ tự và dừng ngay khi một bước lỗi. `status` xem dịch vụ; `stop` dừng container nhưng giữ volume. Có thể dùng `prepare --source-lake <đường-dẫn-lake-v2>` để chọn raw/catalog khác. Đây là **lựa chọn input ban đầu**; CLI không tự thay một batch đã ingest bằng batch khác.

Compose project cố định là `ce-lakehouse-b`. Không chạy hai clone với cùng project name trên một Docker daemon. Cấu hình, secret được tự sinh và log nằm trong `.work/lakehouse-b`, bị Git bỏ qua. Không sao chép secret vào báo cáo hoặc repo. Giữ secret cùng môi trường đang chạy; xóa `.work` nhưng giữ metadata volume sẽ làm mất thông tin đăng nhập của volume đó.

| Thành phần | Vị trí hoặc cấu hình |
|---|---|
| Dữ liệu nghiệp vụ B | Volume `ce-lakehouse-b_lakehouse`, mount `/companye-lakehouse` |
| Catalog/control | PostgreSQL, volume `ce-lakehouse-b_metadata` |
| Engine | Spark local[2], driver 2 GiB, container tối đa 4 GiB/2 CPU |
| Metadata resource | Container tối đa 512 MiB |
| Mạng | Compose network riêng; không mở cổng dịch vụ ra host |
| Raw input | Chỉ container ingest có mount `/seed-input` read-only |
| Code/config | Spark mount read-only; không mount lake cũ hoặc secret Oracle |
| Đối chứng | `/baseline` read-only chứa báo cáo lịch sử; chỉ validator dùng |
| Log và báo cáo mới | `.work/lakehouse-b/reports` |

## Contract và biến đổi

### Ingest

`ingest.py` kiểm đường dẫn trong catalog, checksum từng file rồi đưa raw vào storage root B. File đã tồn tại phải có cùng hash; khác nội dung hoặc batch khác thì dừng để tránh sửa lịch sử. Catalog mới chỉ liệt kê raw nghiệp vụ/file đối tác. Việc có hai bản raw trong môi trường so sánh là chi phí dựng hai phương án thử nghiệm, không phải yêu cầu B vận hành cùng một lake bên ngoài.

### Silver

Schema và cột của 41 bảng lấy từ catalog nguồn; contract khóa/kiểu/NULL/CHECK/tham chiếu lấy từ `source_target_mapping_v1.json`. Dùng lại `analytics_runtime.dimension_transform.read_sources` để giữ cùng quy tắc với A. Các bản ghi không đạt được ghi vào quality/quarantine; không âm thầm sửa giá trị để đạt KPI.

| Input | Output qua Iceberg catalog | Grain và xử lý |
|---|---|---|
| `hotel_ops.<table>` | `ce.silver_hotel.<table>` | Giữ cột và grain nguồn; thêm `_source_batch_id`, `_source_system`, `_source_sha256` |
| `entertainment_ops.<table>` | `ce.silver_entertainment.<table>` | Như miền khách sạn; không nối hay tổng hợp sớm |
| Chứng từ hợp lệ | `ce.silver_external.receipt_versions` | Giữ các revision hợp lệ của chứng từ |
| Chứng từ lỗi | `ce.silver_external.receipt_quarantine` | Giữ dữ liệu và lý do không chuẩn hóa được |
| Gửi lại cùng sự kiện | `ce.silver_external.receipt_replays` | Nhận diện replay, không cộng thêm vào nghiệp vụ |
| Revision hợp lệ mới nhất | `ce.silver_external.receipt_latest` | Một revision được chọn cho mỗi receipt_ref |

External dùng lại `lake_v2.receipt_events`, nhưng đọc **CSV raw**, không lấy Parquet đã xử lý từ lake A. Các bảng external giữ metadata delivery/path có trong transform và thêm batch/source system. Manifest raw liên kết đường dẫn với checksum. Receipt ngoài chỉ đối soát với DB, không sinh thêm fact mua hàng để tránh đếm đôi.

Mỗi bảng được đọc lại sau ghi để so schema và hash toàn bộ nội dung. Manifest Silver lưu tên bảng, snapshot ID, schema, count, checksum nội dung và chất lượng. Chỉ cập nhật `silver-active.json` sau khi mọi bảng hoàn tất. Gold đọc snapshot trong manifest này; không dùng latest ngầm định hoặc fallback về raw.

`explore` đọc booking Silver theo snapshot và đếm từng trạng thái booking. Chạy lệnh này trước Gold để chứng minh có thể phân tích chi tiết mà không cần dimensional mart. Lần chạy sau có thể ghi đè report local, vì vậy bằng chứng nghiệm thu ban đầu được lưu riêng trong repo.

### Gold

Giữ dimensional model, grain, mapping, công thức và các quy tắc nghiệp vụ đã chốt. 16 dimension được xây trước 20 fact/bridge/helper đang bật; F15 vẫn là phần tùy chọn chưa bật. L03/L04 được materialize bằng Iceberg. Không tạo một bộ canonical Parquet bắt buộc làm đầu vào trung gian thứ hai.

Dimension SCD2 sử dụng reducer và quy tắc khoảng hiệu lực hiện có. Nguồn ban đầu chỉ có trạng thái hiện hành: mỗi business key có phiên bản bootstrap, thêm thành viên UNKNOWN/NOT_APPLICABLE. Không suy diễn rằng các thay đổi danh mục đã thật sự xảy ra. Registry surrogate key riêng của B được lưu bền vững trong metadata; khóa có thể khác A, so sánh KPI theo nghiệp vụ thay vì so số surrogate key.

Namespace Gold có dạng `ce.gold_b_<fingerprint>`, chứa các tên bảng vật lý trong DDL. Fingerprint kết hợp hash manifest Silver và phiên bản code/config. Ghi lại cùng ứng viên phải đúng schema và nội dung; khác thì dừng. Không overwrite bảng đang được publication dùng. Các ứng viên dở dang được giữ để phục hồi và kiểm tra, chưa có job tự xóa.

Sau biến đổi: kiểm PK/UK/FK, lượng/tiền, đối soát meal session, chuỗi tồn kho và chứng từ ngoài. Chất lượng lan truyền theo dependency. Dữ liệu hợp lệ vẫn có thể được công bố PARTIAL; trạng thái, phạm vi thiếu và lý do đi cùng kết quả. Không lấy số từ batch cũ để che phần thiếu.

## Publication và reader

PostgreSQL `ce_b` lưu registry, publication manifest, active pointer và reader lease. PREPARED chưa được reader chính thức nhìn thấy. Sau kiểm tra đủ snapshot, schema, hash, quality và 47 metric contracts, transaction cập nhật trạng thái PUBLISHED và active pointer. Compare-and-swap từ chối ghi đè pointer đã thay đổi bởi tiến trình khác. Advisory lock tránh hai writer của CLI chạy đồng thời.

Reader lấy publication và tạo lease trong transaction, sau đó tạo temp view ghim snapshot từng bảng. Mọi truy vấn trong phiên dùng các view đó. Reader cũ tiếp tục đọc snapshot cũ khi có publication mới. Lease hết hạn bị từ chối; lease được gia hạn trước truy vấn. Prototype chưa triển khai snapshot expiration/GC; nếu bổ sung phải tôn trọng lease và publication được giữ lại.

Đây là nhất quán ở lớp ứng dụng trên nhiều bảng. Không diễn giải transaction một bảng của Iceberg thành giao dịch nguyên tử cho toàn bộ warehouse. Quyền hiện tại là tài khoản catalog/control quản trị trong mạng local; chưa phân tách role writer/reader như môi trường production.

Hash manifest được chuẩn hóa thứ tự khóa JSON trước khi tính, vì PostgreSQL JSONB có thể đổi thứ tự khóa. Publication còn kiểm fingerprint code/config hiện hành với ứng viên Gold; nếu code đã đổi trong lúc xây, phải chạy lại Silver/Gold thay vì công bố ứng viên cũ.

## Kiểm chứng và phục hồi

`verify` chạy 47 KPI baseline và 96 ngữ cảnh lọc (546 metric comparisons), kiểm cả tử số/mẫu số và trạng thái/BLANK. Đáp án độc lập đọc raw; kết quả còn được đối chiếu với báo cáo Oracle lịch sử đã chốt. Validator không kết nối Oracle và kiểm hostname `oracle` không khả dụng trong mạng B. Đây không phải một lần chạy Oracle mới hay benchmark hiệu năng.

`fixtures` kiểm SQL tính tay, chính sách lọc/chất lượng, SCD2 và publication. Các fixture thay snapshot/schema/pointer dùng namespace và control schema riêng, không sửa bảng hoặc active pointer nghiệp vụ.

Có fault injection để thử gián đoạn thực tế:

```powershell
python -X utf8 scripts/lakehouse.py silver --fail-after 2
# Lỗi chủ động sau 2 bảng; chạy lại không truyền --fail-after.
python -X utf8 scripts/lakehouse.py silver
python -X utf8 scripts/lakehouse.py gold --fail-after 2
python -X utf8 scripts/lakehouse.py gold
python -X utf8 scripts/lakehouse.py publish --fail-after 1
python -X utf8 scripts/lakehouse.py publish
```

Thử Silver/Gold fault trên ứng viên chưa hoàn tất; nếu manifest đã tồn tại thì lệnh đi vào nhánh replay và không cố tình tạo lại lỗi. Lưu log lỗi trước khi chạy lại vì log local cùng phase sẽ bị thay. Không sửa raw, manifest hoặc bảng để buộc test chạy. `publish --fail-after 1` dừng sau PREPARED và trước transaction pointer; batch đang phục vụ phải giữ nguyên.

`scripts/lakehouse-state.py <label>` chụp metadata/control và các mount/resource được chọn, không ghi secret hay đường dẫn mount host. Các label gồm `before-publish`, `publish-interrupted`, `published`, `restarted`. Sau một lượt nghiệm thu đầu tiên có đủ log fault injection và report, `scripts/finalize-lakehouse.py` kiểm lại điều kiện và đóng gói bằng chứng vào `Project/reports/lakehouse-b`. Finalizer phục vụ mốc nghiệm thu này; không bắt mỗi lần vận hành bình thường phải tạo lại các ca lỗi.

## Giới hạn cần giữ khi đánh giá

- Đây là initial load và retry/replay của một batch bất biến. Chưa phải CDC, nạp nhiều batch tăng dần, tự động cập nhật SCD2 từ các event mới hay lịch chạy production.
- Adapter dùng lại giới hạn 100.000 dòng/bảng nguồn và thu thập dữ liệu Python vào driver. Kết quả local không chứng minh khả năng xử lý dữ liệu tập đoàn ở scale lớn; cần đổi sang transformation phân tán trước stress test vượt phạm vi đó.
- Có raw, Silver, Gold và snapshot/ứng viên trong cùng storage root; không gọi là zero-copy. Không tự dọn snapshot hoặc ứng viên dở dang.
- Các bảng được tạo ở những lần thử sớm có thể giữ codec mặc định; code hiện tạo bảng mới bằng Snappy. Trước benchmark cần kiểm kê codec, file size, partition và retention của cả A/B, không suy ra công bằng vật lý từ việc KPI bằng nhau.
- Power BI và bộ số web lịch sử có publication riêng. Không đổi nhãn chúng thành kết quả của B mới. Việc thay nguồn dashboard cần xuất dữ liệu, kiểm DAX và UI lại; cập nhật mô tả kiến trúc không thay thế bước nghiệm thu này.
- Mạng tách khỏi Oracle chứng minh không phụ thuộc dịch vụ đó, nhưng chưa mô phỏng lỗi mạng phân tán, mất host hay restore disaster recovery. Docker volume vẫn phải được sao lưu theo nhu cầu.
