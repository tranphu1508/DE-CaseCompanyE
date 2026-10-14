# Môi trường thử nghiệm CompanyE trên máy cá nhân

Cập nhật 13/10/2026 sau chuyển Docker: VHDX chính đã nằm tại `E:/DockerDesktopData/DockerDesktopWSL/disk/docker_data.vhdx`. E còn 312.38 GiB, C còn 95.89 GiB và D còn 9.01 GiB. [Biên bản chuyển và đối chiếu](../reports/docker-storage-migration-20261013/verification.json) đạt PASSED. [Thiết kế vật lý hiện hành](CompanyE_Physical_Design.md) dùng named volume trên E cho output/staging/shuffle; nguồn lake trên D được analytics mount chỉ đọc. Phần dưới giữ số đo và đề xuất ngày 12/10 để truy vết; dùng số đo mới khi provision.

Đánh giá ngày 12/10/2026: CPU và RAM phù hợp để phát triển, chạy demo và benchmark giới hạn trên một máy. Có thể stress test pipeline bằng Docker và WSL2 trên chính máy này sau khi chuẩn bị đủ dung lượng. Hiện ổ D chứa project còn khoảng 10,1 GiB nên chưa phù hợp để mở rộng dữ liệu hoặc cài thêm toàn bộ stack. Đây là đánh giá cấu hình và phương án đo, chưa phải kết quả stress test.

## Cấu hình đo được

| Thành phần | Kết quả | Ý nghĩa với project |
|---|---|---|
| CPU | Intel Core i7-14700F, 20 nhân, 28 bộ xử lý logic | Đủ cho ETL, SQL và hai nhánh chạy lần lượt. Không coi 28 luồng là 28 nhân hiệu năng tương đương. |
| RAM hệ điều hành nhìn thấy | 63,83 GiB, tương ứng máy khoảng 64 GB RAM | Đủ cho bản thử một máy với giới hạn container. |
| RAM trống tại lần đo | 32,12 GiB | Là số tức thời, cần đo lại trước benchmark. |
| GPU | NVIDIA RTX 4070 SUPER, 12.282 MiB VRAM, xấp xỉ 12 GiB | Pipeline PostgreSQL, Oracle và Spark SQL hiện tại chưa cấu hình tăng tốc GPU. GPU không quyết định khả năng chạy workload này. |
| Ổ vật lý | Samsung SSD 990 PRO 1 TB, NVMe | Các phân vùng cùng thiết bị vẫn cạnh tranh I/O. |
| C | 295,11 GiB tổng; 82,32 GiB trống | Có nhiều khoảng trống hơn D; chưa đổi đường lưu Docker hay di chuyển dữ liệu. |
| D chứa project | 146,48 GiB tổng; 10,07 GiB trống | Hạn chế chính cho mở rộng raw, staging, shuffle, snapshot và log. |
| E | 488,28 GiB tổng; 35,96 GiB trống | Khoảng trống vẫn cần tính theo tổng footprint, không chỉ dung lượng CSV. |
| Docker Desktop | 28 CPU logic, khoảng 31,26 GiB RAM nhìn thấy trong VM | Đây là tổng tài nguyên VM, không phải ngân sách riêng của Spark. |
| PostgreSQL CompanyE | Giới hạn container 1 GiB | Đang chạy, healthy ở lần kiểm tra. |
| Spark CompanyE | Giới hạn container 3 GiB | Nâng RAM máy không tự nâng giới hạn này. |
| WSL | 2.7.8.0 | Môi trường Linux qua WSL đang hoạt động. |

Số VRAM lấy từ `nvidia-smi`; không lấy trường `Win32_VideoController.AdapterRAM` vì trường này chỉ trả xấp xỉ 4 GB trên máy hiện tại. CPU toàn máy có tải khoảng 43% tại lần ghi nhận, và còn container của project khác đang chạy. Không dùng thời điểm này như một phép đo máy rảnh. Không dừng ứng dụng hoặc container ngoài CompanyE trong bước kiểm tra.

Nguồn số đo: [báo cáo máy](../reports/local_environment.json). Có thể chạy lại `scripts/inspect-local-environment.ps1` để cập nhật; lệnh chỉ đọc cấu hình và ghi báo cáo, không thay giới hạn tài nguyên.

## Ngân sách tài nguyên đề xuất

Các giá trị dưới đây là cấu hình bắt đầu để thử nghiệm, không phải yêu cầu tối thiểu của nhà cung cấp hoặc cấu hình đã áp dụng.

| Mục đích | CPU quota mỗi engine | RAM container | Cách chạy |
|---|---:|---:|---|
| Phát triển Spark và lakehouse | 4 | 6 GiB, driver heap ban đầu 3 GiB | Một job, `local[4]`; chừa RAM ngoài heap cho Python, JVM và bộ đệm. |
| Phát triển Oracle Free | 2 | 4 GiB | Database Free vẫn chịu giới hạn nội bộ; 4 GiB container không nâng SGA/PGA lên 4 GiB. |
| So sánh ngân sách container tương đương | 2 | 4 GiB mỗi engine | Chạy lần lượt, Spark `local[2]`, driver heap ban đầu 2 GiB; giữ cùng dữ liệu và ngân sách tiến trình phụ. |
| Khảo sát mở rộng Spark riêng | 4 rồi 8 | 6 rồi 12 GiB | Chỉ chạy khi disk/RAM đủ; báo cáo thành khảo sát riêng, không so trực tiếp với Oracle Free như hai hệ thống cùng tài nguyên. |
| PostgreSQL nguồn | 1–2 | 1–2 GiB | Chốt cấu hình trước mỗi series; tách thời gian extract khỏi xử lý khi cần. |

Giữ tổng ngân sách workload đang hoạt động khoảng 20 GiB hoặc thấp hơn trong VM hiện tại, dành phần còn lại cho Docker/WSL, catalog và hệ điều hành khách. Trên Windows, kiểm tra còn tối thiểu 12 GiB RAM khả dụng trước khi chạy bài đo lớn. Đây là ngưỡng vận hành bảo thủ cho project; cần điều chỉnh sau lần đo nền.

Oracle Free hiện giới hạn 2 CPU cho foreground processes, 2 GB SGA/PGA và 12 GB dữ liệu người dùng. Vì vậy, máy mạnh hơn không giúp bản Free vượt giới hạn edition. Hai container có cùng CPU/RAM quota vẫn không có cùng cơ chế dùng bộ nhớ; báo cáo phải ghi rõ khác biệt. [Oracle Database Free FAQ](https://www.oracle.com/uk/database/free/faq/)

Thử `local[N]` kiểm soát số luồng Spark; phải đặt driver memory lúc khởi chạy và lưu toàn bộ cấu hình thực tế. Container limit không đồng nghĩa toàn bộ phần đó là Java heap. [Spark 3.5.7 configuration](https://spark.apache.org/docs/3.5.7/configuration.html)

## Điều kiện lưu trữ trước stress test

- Tách thư mục, database, catalog và Docker project benchmark khỏi `companye` vận hành. Đọc snapshot v2 và cấu hình seed theo chế độ chỉ đọc, ghi output vào vùng thử nghiệm riêng.
- Trước khi mở rộng, dành tối thiểu 50 GiB trống cho vùng thử nghiệm nhỏ/vừa, ưu tiên 80–100 GiB khi thử nhiều quy mô. Đây là ngân sách khởi đầu, không bảo đảm đủ cho mọi quy mô. Dùng lần chạy nhỏ để đo bytes đầu vào, output, index, temp/shuffle, log và snapshot, rồi tính lại ngân sách cho lần kế tiếp.
- Kiểm tra cả volume chứa dữ liệu benchmark và volume vật lý chứa Docker VHDX; chưa xác định vị trí VHDX từ phép đo hiện tại. `df` bên trong Linux không thay thế kiểm tra dung lượng trống trên phân vùng Windows chứa VHDX.
- Khởi chạy chỉ khi dung lượng trống lớn hơn dự báo footprint bổ sung cộng ít nhất 20 GiB dự phòng. Dừng việc tăng tải nếu host volume xuống dưới 20 GiB, container bị OOM, swap tăng kéo dài, hoặc kết quả kiểm tra đúng dữ liệu thất bại.
- Với 10,07 GiB còn lại ở D, điều kiện trên chưa đạt. Không tự xóa snapshot/báo cáo, thay phân vùng hoặc di chuyển dữ liệu để lấy chỗ.
- Với workload nặng I/O, cân nhắc dữ liệu nóng và shuffle trong Linux filesystem hoặc Docker volume thay cho Windows bind mount. Hai nhánh phải ghi rõ kiểu lưu trữ, tránh so Oracle trong volume với Iceberg trên Windows bind mount rồi quy toàn bộ khác biệt cho engine. [Docker WSL2 best practices](https://docs.docker.com/desktop/features/wsl/best-practices/)

## Kế hoạch stress test pipeline

| Bước | Tải và thao tác | Bằng chứng cần giữ |
|---|---|---|
| 1 Kiểm tra nền | Chạy snapshot v2 một lần trên môi trường thử riêng; kiểm tra 47 KPI khi hai nhánh đã triển khai. | Seed, manifest, code hash, image digest, schema/KPI version, kết quả đối soát. |
| 2 Đo lặp nền | Một lần làm nóng; ít nhất 5 lần đo cùng bộ truy vấn. Đổi thứ tự Oracle/Iceberg giữa series. | Mỗi lần đo riêng, median/min/max; với chỉ 5 mẫu không coi p95 là ước lượng ổn định. |
| 3 Tăng dung lượng | Lần lượt 1x, 2x, 5x, 10x nếu đủ disk và Oracle chưa chạm 12 GB user data. | Số dòng từng bảng, bytes thực tế và footprint temp. 591.242 dòng v2 là mốc, không bảo đảm mọi bảng tăng tuyến tính. |
| 4 Tăng đồng thời | Một writer pipeline; truy vấn reader 1, 2, 4, rồi 8 nếu ổn định. | Throughput, latency, lỗi/timeouts, CPU, RAM peak, I/O, spill và GC. |
| 5 Thử lỗi và phục hồi | Batch lặp, receipt đến trễ, revision sai thứ tự, lỗi giữa bước ghi/publish trong sandbox. | Không nhân đôi, giữ batch chưa hoàn tất khỏi consumer, thời gian recovery và đối soát lại. |
| 6 So sánh giao diện | Refresh Power BI và thao tác web đo riêng sau backend. | Thời gian query engine, ETL, refresh và UI thành các cột riêng. |

Tăng quy mô phải dùng cấu hình sinh riêng có seed và namespace khóa, giữ quan hệ và sức chứa hợp lệ. Không nhân bản booking bằng UNION ALL hoặc tăng khách mà giữ nguyên phòng/xe rồi tạo overlap. Tách kiểm thử mở rộng nghiệp vụ khỏi replay kỹ thuật. Chưa có generator scale và benchmark harness mới được triển khai ở bước này.

Nếu đo cold cache, ghi rõ cache nào được làm lạnh. Khởi động lại container chưa chứng minh đã xóa cache của WSL/Windows; không đặt tên cold cache cho một phép đo chưa kiểm soát được. Với CPU có các loại nhân khác nhau và ứng dụng nền, giữ cấu hình/quota ổn định, ghi tải nền và chạy lặp thay vì coi một lần đo là kết luận.

## Kết luận triển khai

Máy phù hợp cho môi trường học phần với Oracle, Spark–Iceberg, Power BI và web demo. Stress test trên máy có thể kiểm tra tính đúng, độ bền pipeline và ngưỡng tài nguyên của bản triển khai một máy. Kết quả không chứng minh khả năng scale-out, chịu lỗi nhiều node hay năng lực phục vụ tập đoàn ở môi trường thật. Hai nhánh warehouse/lakehouse chưa được dựng, nên hiện chỉ có bằng chứng chạy nguồn/lake và kiểm tra cấu hình, chưa có bằng chứng stress test toàn pipeline.
