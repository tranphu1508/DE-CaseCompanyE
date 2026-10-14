# Mô tả case doanh nghiệp CompanyE

**Phiên bản:** 1.3  
**Ngày chốt:** 12/10/2026  
**Phạm vi:** Bối cảnh doanh nghiệp, điều kiện vận hành và đặc điểm nguồn dữ liệu cho project môn Kỹ thuật dữ liệu.

CompanyE là doanh nghiệp giả định kinh doanh lưu trú, ăn uống, giải trí và cho thuê phương tiện tại bốn điểm đến của Việt Nam. Doanh nghiệp có nhiều cơ sở phân tán, phục vụ nhiều phân khúc khách hàng và làm việc với cả nền tảng phân phối lớn lẫn nhà cung cấp địa phương. Hoạt động kinh doanh phát sinh dữ liệu tại các hệ thống nghiệp vụ và qua nhiều loại file, chứng từ bên ngoài. CompanyE tiếp nhận các nguồn này vào data lake, xử lý và tích hợp những dữ liệu cần thiết vào một kho dữ liệu chung.

Toàn bộ cơ sở của CompanyE, hợp đồng, giao dịch và dữ liệu kinh doanh trong case đều được mô phỏng. Sa Pa, Đà Nẵng, Đà Lạt, Phú Quốc và các thương hiệu đối tác được nêu là có thật; quan hệ hợp tác, điều kiện thương mại và khả năng tích hợp với CompanyE là giả định phục vụ project. Các đặc điểm mùa và khí hậu chỉ làm nền cho kịch bản, không đại diện cho kết quả kinh doanh thực tế của địa phương hay thương hiệu.

Bản mô tả này chốt điều kiện vận hành và **tám nhu cầu nghiệp vụ phục vụ phân tích B01–B08**, được người dùng xác nhận ngày 12/10/2026. Danh sách chính thức nằm ở mục 18; công thức KPI, grain, ngày nghiệp vụ và tiêu chí nghiệm thu phiên bản 1.0 được ghi trong `docs/CompanyE_KPI_Specification.md` để làm đầu vào thiết kế warehouse/lakehouse và ứng dụng.

## 1 Quy mô và tổ chức doanh nghiệp

CompanyE tổ chức hoạt động thành bốn cụm du lịch. Mỗi cụm có một trung tâm giải trí, một khách sạn 5 sao mang thương hiệu **E Grand** và một khách sạn 3 sao mang thương hiệu **E Stay**. Hai khách sạn nằm gần trung tâm giải trí để khách có thể sử dụng nhiều dịch vụ trong cùng chuyến đi. Bốn cụm nằm cách xa nhau và có bộ máy vận hành địa phương.

| Cụm du lịch | Trung tâm giải trí | Khách sạn 5 sao | Khách sạn 3 sao |
|---|---|---|---|
| Sa Pa | E Núi Mây | E Grand Sa Pa | E Stay Sa Pa |
| Đà Nẵng | E Sóng Biển | E Grand Đà Nẵng | E Stay Đà Nẵng |
| Đà Lạt | E Vườn Thông | E Grand Đà Lạt | E Stay Đà Lạt |
| Phú Quốc | E Đảo Ngọc | E Grand Phú Quốc | E Stay Phú Quốc |

Toàn hệ thống có **4 trung tâm giải trí và 8 khách sạn, gồm 4 khách sạn 5 sao và 4 khách sạn 3 sao**. Mỗi khách sạn có nhà hàng phục vụ buffet sáng, ăn trưa và buffet tối, cùng một bar. Mỗi cụm có bộ phận cho thuê phương tiện phục vụ khách trong khu vực.

Trụ sở chính quản lý thương hiệu, chương trình hội viên, các chiến dịch khuyến mãi toàn chuỗi, hợp đồng khung với đối tác và kết quả kinh doanh tổng hợp. Ban quản lý từng cụm phụ trách vận hành, chất lượng phục vụ và phối hợp giữa các cơ sở. Quản lý khách sạn, nhà hàng, trung tâm giải trí, đội phương tiện, mua hàng, kho và kỹ thuật trực tiếp ghi nhận các nghiệp vụ thuộc phạm vi của mình.

Các cơ sở được điều chỉnh thực đơn, lịch hoạt động và chương trình bán hàng địa phương trong phạm vi chính sách đã được phê duyệt. Quy mô phòng, sức chứa, đội xe, mức giá và định mức nguyên liệu sẽ được lượng hóa khi thiết kế dữ liệu, theo các quy tắc vận hành trong case.

## 2 Địa điểm và tính mùa vụ

| Địa điểm | Bối cảnh khí hậu tham khảo | Đặc trưng hoạt động giả định của CompanyE |
|---|---|---|
| Sa Pa | Vùng núi mát, có sương mù và mùa đông lạnh; mùa xuân và mùa thu có những giai đoạn thuận lợi cho tham quan. [Vietnam Tourism](https://vietnam.travel/places-to-go/northern-midlands-mountains/sapa) | E Núi Mây có khu cảnh quan, trải nghiệm văn hóa, trò chơi gia đình và hoạt động trong nhà. Nhà hàng phục vụ món vùng cao; phương tiện cho thuê chủ yếu là ô tô phục vụ nhóm khách. |
| Đà Nẵng | Khí hậu có giai đoạn khô nóng và giai đoạn mưa vào cuối năm; du lịch hè là một mùa hoạt động đáng chú ý. [Vietnam Tourism](https://vietnam.travel/things-to-do/da-nang-travel-guides) | E Sóng Biển có công viên nước, trò chơi ngoài trời, khu trong nhà và biểu diễn buổi tối. Nhà hàng có buffet hải sản; dịch vụ phương tiện gồm xe máy và ô tô. |
| Đà Lạt | Khí hậu cao nguyên mát; khoảng tháng 12–3 thường khô, tháng 5–10 có nhiều mưa hơn. [Vietnam Tourism](https://vietnam.travel/node/100) | E Vườn Thông có vườn cảnh quan, trải nghiệm ngoài trời, hoạt động sáng tạo và khu trẻ em. Nhà hàng nhấn mạnh rau củ và món địa phương; cung cấp xe máy và ô tô. |
| Phú Quốc | Khoảng tháng 11–4 thường khô và biển êm hơn; tháng 5–10 thường có nhiều mưa và biển động hơn. [Vietnam Tourism](https://vietnam.travel/places-to-go/mekong-delta/phu-quoc) | E Đảo Ngọc có khu vui chơi chủ đề biển, hồ bơi, biểu diễn và khu trong nhà. Nhà hàng có buffet hải sản, bar ngoài trời; cung cấp xe máy và ô tô. |

Mỗi cụm có lịch cao điểm và thấp điểm riêng. Trong kịch bản mô phỏng, Đà Nẵng có thể tăng khách gia đình vào mùa hè; Phú Quốc tăng nhu cầu nghỉ dưỡng trong giai đoạn thuận lợi cho hoạt động biển; Sa Pa có khách tìm kiếm trải nghiệm mùa lạnh; Đà Lạt vẫn có nhu cầu tránh nóng vào thời kỳ xuất hiện nhiều mưa.

Đây là giả định về hành vi kinh doanh, không phải quy luật cố định. Lượng khách còn chịu ảnh hưởng của cuối tuần, ngày lễ, kỳ nghỉ, sự kiện, giá bán, kênh phân phối và khuyến mãi. Ngày mưa vẫn có thể xuất hiện trong mùa khô, và một ngày thời tiết đẹp không bảo đảm cơ sở đông khách.

CompanyE ghi nhận điều kiện thời tiết theo địa điểm và ngày, cùng những lần đóng hoặc hạn chế hoạt động thực tế. Mùa du lịch, thời tiết trong ngày và sự kiện địa phương được phân biệt khi mô phỏng. Mưa không mặc nhiên làm tất cả dịch vụ ngừng hoạt động; khách có thể chuyển sang ăn uống hoặc vui chơi trong nhà.

## 3 Khách hàng và các dịch vụ liên kết

E Grand hướng đến khách yêu cầu cao về tiện nghi và phục vụ; E Stay hướng đến khách ưu tiên ngân sách và muốn lựa chọn linh hoạt dịch vụ bổ sung. CompanyE phục vụ khách cá nhân, gia đình, nhóm bạn, khách đoàn, khách doanh nghiệp và người dân địa phương.

Khách lưu trú không bị giới hạn sử dụng dịch vụ tại khách sạn mình ở. Khách E Stay có thể ăn buffet tối hoặc đến bar của E Grand. Khách ở ngoài hệ thống có thể đến nhà hàng, mua vé giải trí hoặc thuê phương tiện. Một khách hàng cũng có thể sử dụng dịch vụ của CompanyE tại nhiều cụm trong những chuyến đi khác nhau.

Người đặt dịch vụ, người thanh toán và người sử dụng có thể khác nhau. Một người có thể đặt nhiều phòng cho cả gia đình hoặc đoàn khách. Không quy toàn bộ lượt sử dụng của một nhóm cho riêng người đứng tên booking; giao dịch thiếu thông tin người sử dụng vẫn được giữ ở mức nhận diện mà nguồn cung cấp.

CompanyE bán dịch vụ riêng lẻ và gói kết hợp như phòng kèm vé giải trí, phòng kèm buffet tối, hoặc phòng kèm vé và thuê xe. Mỗi gói phải xác định các thành phần, số lượng, thời gian sử dụng, đơn vị thực hiện và điều kiện đổi/hủy.

## 4 Đặt phòng và quyền lợi buffet sáng

Mỗi khách sạn có nhiều loại phòng với sức chứa, tiện nghi và giá bán khác nhau. Cùng một loại phòng có thể có nhiều gói giá, khác nhau về quyền lợi, điều kiện thanh toán, đổi/hủy, kênh phân phối hoặc chương trình áp dụng.

Một booking có thể gồm nhiều phòng; từng phòng có gói giá và số khách được hưởng quyền lợi riêng. Quyền lợi được xác nhận theo điều kiện tại thời điểm đặt. Thay đổi hợp đồng vendor hoặc khuyến mãi sau đó không tự động sửa booking đã xác nhận. Nếu khách đổi booking và chấp nhận điều kiện mới, hệ thống ghi nhận sự thay đổi đó.

| Nội dung | E Grand 5 sao | E Stay 3 sao |
|---|---|---|
| Chính sách cơ bản | Giá phòng luôn bao gồm buffet sáng cho số khách được quy định trong gói phòng | Buffet sáng tính thêm, trừ khi gói đặt phòng đã bao gồm |
| Loại phòng và gói giá | Có thể khác số người được hưởng và quyền lợi bổ sung | Một số loại phòng hoặc gói giá có ăn sáng; một số chỉ có phòng |
| Đặt qua đối tác | Vẫn giữ quyền lợi buffet sáng cơ bản của gói phòng | Tùy gói cụ thể và thỏa thuận với đối tác; không suy ra chỉ từ tên đối tác |
| Người ngoài phạm vi quyền lợi | Mua thêm suất hoặc áp dụng phụ thu tương ứng | Mua bổ sung hoặc dùng quyền lợi hợp lệ khác |
| Không sử dụng bữa đi kèm | Không tự động được hoàn tiền | Không tự động được hoàn tiền đối với phần đã bao gồm |

“Bao gồm một buffet sáng” được hiểu là **một bữa sáng cho mỗi khách đủ điều kiện vào mỗi ngày được hưởng quyền lợi**, theo số người và số đêm của gói phòng. Thông thường, quyền lợi bắt đầu từ sáng sau đêm đầu tiên và bao gồm sáng ngày trả phòng. Ví dụ, một phòng cho hai người lớn trong hai đêm, có ăn sáng cho cả hai, tạo ra bốn lượt buffet sáng được hưởng.

Chính sách trẻ em và khách bổ sung quy định riêng điều kiện được hưởng và phụ thu. Quyền lợi ăn sáng mặc định sử dụng tại khách sạn lưu trú; chỉ dùng tại cơ sở khác nếu gói có quy định.

Nhà hàng ghi nhận lượt ăn thực tế kể cả khi buffet đã nằm trong giá phòng, nhưng không thu tiền lần nữa. Số khách có quyền lợi và số khách đến ăn được phân biệt. Khách không được cấp hai quyền lợi trùng cho cùng người, cùng bữa chỉ vì đồng thời có gói phòng và một ưu đãi ăn sáng khác.

## 5 Nhà hàng và bar

| Dịch vụ | Cách phục vụ |
|---|---|
| Buffet sáng | Phục vụ khách có quyền lợi từ phòng, gói dịch vụ, hội viên hoặc khách mua riêng |
| Ăn trưa | Gọi món hoặc thực đơn theo suất, thu tiền theo sản phẩm đã đặt |
| Buffet tối | Bán theo suất người lớn và trẻ em; có thể nằm trong gói du lịch hoặc chương trình ưu đãi |
| Bar | Bán đồ uống và món ăn nhẹ; áp dụng voucher hoặc ưu đãi đủ điều kiện |

Nhà hàng và bar đón khách của chính khách sạn, khách từ cơ sở khác trong chuỗi và khách bên ngoài. Mỗi nơi có thực đơn, mức giá, sức chứa và thời gian phục vụ riêng. Hóa đơn có thể do khách thanh toán trực tiếp hoặc được chuyển vào tài khoản lưu trú khi chính sách cho phép; hai cách ghi nhận phải liên kết để không tính trùng.

Chất lượng nhà hàng được phản ánh qua món ăn, vệ sinh, thái độ phục vụ, thời gian chờ và phản hồi khách hàng. Hạng sao khách sạn không thay thế cho các thông tin này. Trong mô phỏng, nhà hàng E Grand có thể có thực đơn phong phú nhưng bị quá tải vào giờ cao điểm; nhà hàng E Stay có thể ít lựa chọn hơn nhưng nhận đánh giá tốt về phục vụ.

Khác biệt về chất lượng có thể thay đổi theo thời gian, nguyên liệu, nhân sự và lượng khách. Case không gán cố định mọi nhà hàng 5 sao tốt hơn mọi nhà hàng 3 sao.

## 6 Trung tâm giải trí và cho thuê phương tiện

Trung tâm giải trí bán vé vào cửa, vé hoạt động riêng và gói nhiều hoạt động. Khách mua tại cổng, trên kênh trực tiếp, qua đối tác hoặc lễ tân khách sạn. Vé bán ra, lượt vào cổng và lượt sử dụng từng hoạt động là những sự kiện khác nhau.

Mỗi hoạt động có lịch vận hành và sức chứa. Thời tiết, bảo trì hoặc sự cố có thể làm hoạt động tạm đóng, giảm công suất hoặc đổi lịch. Khách được xử lý theo điều kiện sản phẩm đã mua: đổi ngày, chuyển hoạt động hoặc hoàn tiền phù hợp. Hủy vé giải trí không mặc nhiên hủy phần lưu trú của cùng chuyến đi.

Bộ phận cho thuê phương tiện của từng cụm phục vụ khách lưu trú và khách bên ngoài. Mỗi hợp đồng xác định người thuê, loại xe, thời gian dự kiến, đơn vị giao xe và mức giá. Khi thực hiện, nhân viên ghi nhận xe được giao, thời gian giao/trả thực tế, tình trạng phương tiện và các khoản phát sinh như gia hạn.

Xe đang bảo dưỡng hoặc không đủ điều kiện khai thác không được tính là xe sẵn sàng. Đặt thuê chưa đồng nghĩa nhận xe. Các cụm ở xa nhau nên không giả định việc điều chuyển đội xe diễn ra tức thời.

## 7 Kênh đặt phòng và đối tác phân phối

Mỗi khách sạn có một website chính thức riêng, tạo thành tám kênh đặt phòng trực tiếp. Website cung cấp thông tin khách sạn, phòng trống, gói dịch vụ, khuyến mãi và chức năng ghi nhận hội viên. Khách còn có thể đặt qua điện thoại, email hoặc lễ tân; nhân viên nhập booking tương ứng vào hệ thống.

Tám website có giao diện và chương trình theo cơ sở nhưng đưa booking về Hotel Operations. Case không yêu cầu một database riêng cho mỗi website.

| Đối tác phân phối | Vai trò giả định trong case |
|---|---|
| Agoda | Phân phối phòng và gói lưu trú |
| Booking.com | Phân phối phòng với các gói giá, quyền lợi và điều kiện riêng |
| be | Phân phối một số gói lưu trú, du lịch và ưu đãi kết hợp |
| MoMo | Phân phối một số gói lưu trú, voucher du lịch và ưu đãi trên nền tảng |

Giả định cả tám khách sạn đều có thể nhận booking từ bốn đối tác. Danh mục phòng, gói giá và chiến dịch được bán phụ thuộc từng hợp đồng; không mặc định mọi đối tác bán mọi sản phẩm ở mọi thời điểm. Một đối tác có thể đồng thời bán gói chỉ phòng và gói có buffet sáng tại E Stay.

**Kênh đặt phòng và phương thức thanh toán được ghi riêng.** Khách đặt tại website E Grand rồi trả bằng MoMo vẫn thuộc kênh website. MoMo chỉ là đối tác phân phối của booking khi khách đặt qua kênh phân phối MoMo trong mô hình giả định. Ưu đãi thanh toán cũng không mặc nhiên là ưu đãi của kênh bán.

## 8 Khuyến mãi theo mùa và cơ chế tài trợ

CompanyE tổ chức chiến dịch toàn chuỗi hoặc theo cụm, khách sạn, nhóm dịch vụ. Các chương trình giả định gồm du lịch hè gia đình, nghỉ dưỡng ngày thường, trải nghiệm mùa lạnh Sa Pa, kỳ nghỉ biển đảo Phú Quốc, đặt sớm và ưu đãi qua đối tác.

Mỗi chương trình quy định thời gian mở bán và thời gian sử dụng riêng; các giới hạn về cơ sở, loại phòng, gói giá, khách hàng, ngày trong tuần, số đêm tối thiểu, ngày loại trừ, mức giảm tối đa, số lượt sử dụng và ngân sách. Ưu đãi có thể là giảm tiền, giảm theo tỷ lệ hoặc tặng quyền lợi dịch vụ.

| Cơ chế | Bên chịu phần ưu đãi |
|---|---|
| CompanyE tài trợ | CompanyE chịu toàn bộ phần giảm theo chương trình |
| Đối tác tài trợ | Đối tác chịu toàn bộ phần giảm cho khách theo thỏa thuận |
| Đồng tài trợ | CompanyE và đối tác chia phần giảm theo tỷ lệ hoặc số tiền đã thỏa thuận |

Chính sách tài trợ được xác định theo từng chiến dịch, không cố định cho mọi giao dịch với một đối tác. Một booking có thể áp dụng nhiều ưu đãi nếu được phép; phải xác định thứ tự tính, điều kiện cộng dồn, số tiền và bên tài trợ của từng ưu đãi.

Ví dụ dưới đây dùng cùng một gói giá 1.000.000 đồng và mức giảm 200.000 đồng. Các con số chỉ minh họa cơ chế tài trợ, chưa xét thuế, hoa hồng, phí thanh toán và điều kiện ghi nhận doanh thu.

| Cơ chế | Khách trả | Đối tác tài trợ | CompanyE chịu | Giá trị CompanyE được hưởng trước các khoản phí khác |
|---|---:|---:|---:|---:|
| Đối tác tài trợ toàn bộ | 800.000 | 200.000 | 0 | 1.000.000 |
| CompanyE tài trợ toàn bộ | 800.000 | 0 | 200.000 | 800.000 |
| Đồng tài trợ | 800.000 | 120.000 | 80.000 | 920.000 |

Khoản đối tác tài trợ có thể được thanh toán hoặc bù trừ ở kỳ đối soát sau. Khoản được hưởng, khoản được xác nhận và khoản thực nhận có thể khác nhau tại một thời điểm. Hoa hồng phân phối được ghi riêng với tài trợ khuyến mãi; một đối tác có thể vừa tài trợ ưu đãi vừa thu hoa hồng theo hợp đồng.

Chương trình tặng buffet hoặc vé giải trí ghi rõ quyền lợi và bên chịu giá trị hỗ trợ đã thỏa thuận. Giá bán lẻ của quyền lợi không mặc nhiên bằng chi phí cung cấp. Trong phạm vi ban đầu, ví dụ giảm tiền là giảm ngay khi mua; chương trình hoàn tiền sau mua, nếu được mô phỏng, phải có sự kiện chi trả riêng, không coi là khoản đã giảm lúc đặt.

Điều kiện áp dụng được lưu theo booking đã xác nhận. Khi khách đổi hoặc hủy một phần, khoản giảm và tài trợ được điều chỉnh theo chính sách chiến dịch. Hoàn tiền khách và điều chỉnh tài trợ đối tác có thể diễn ra vào những thời điểm khác nhau.

## 9 Hội viên và thẻ hội viên

CompanyE có chương trình hội viên dùng chung tại bốn cụm. Gói hội viên quy định quyền lợi; thẻ hội viên là phương tiện nhận diện và sử dụng quyền lợi, không phải thẻ thanh toán trả trước.

| Gói | Đối tượng và thời hạn | Quyền lợi giả định |
|---|---|---|
| E Member | Cá nhân đăng ký miễn phí | Tích điểm trên giao dịch đủ điều kiện và tiếp cận ưu đãi hội viên |
| E Plus | Cá nhân mua gói 12 tháng | Quyền lợi E Member, ưu đãi giá và một số voucher dịch vụ có thời hạn |
| E Family | Gói 12 tháng cho nhóm thành viên gia đình đăng ký trước | Quyền lợi cho thành viên đủ điều kiện và ưu đãi gói gia đình |

Thẻ điện tử và thẻ vật lý cùng liên kết đến hồ sơ hội viên. Thành viên E Family có mã nhận diện cá nhân, liên kết với một gói gia đình; quyền lợi dùng chung và quyền lợi cá nhân được phân biệt. Khi thay thẻ, lịch sử không được biến thành một khách hàng mới chỉ vì số thẻ thay đổi.

Khi khách xuất trình mã hội viên, hệ thống kiểm tra thời hạn, quyền lợi còn lại và điều kiện kết hợp ưu đãi. Không mặc định mọi giao dịch qua đối tác được tích điểm. Điểm được cộng sau khi giao dịch đủ điều kiện hoàn tất và được điều chỉnh nếu hoàn tiền; voucher có thời hạn, phạm vi và số lần dùng riêng.

Khách E Stay có thể dùng voucher ăn sáng hợp lệ khi gói phòng chưa bao gồm bữa sáng. Khách E Grand đã có ăn sáng không nhận thêm quyền lợi trùng cho cùng người và bữa. Việc mua, gia hạn, thay đổi hoặc hết hạn gói hội viên được ghi nhận riêng với giao dịch sử dụng dịch vụ và đổi điểm.

Hội viên tạo điều kiện liên kết lịch sử khách hàng, nhưng không bảo đảm mọi giao dịch có mã chung. Khách có thể không xuất trình thẻ hoặc thông tin đối tác gửi về không có mã hội viên.

## 10 Nhà cung cấp hàng hóa và dịch vụ đầu vào

CompanyE phân biệt **đối tác phân phối**, là bên bán dịch vụ của CompanyE, với **nhà cung cấp**, là bên bán hàng hóa hoặc dịch vụ đầu vào cho CompanyE. Trụ sở chính ký hợp đồng khung; từng cơ sở đặt, nhận và kiểm tra hàng theo nhu cầu. Các cụm còn có nhà cung cấp địa phương để phục vụ thực đơn vùng miền và bổ sung hàng.

Các thương hiệu thật sau được chọn làm nền cho quan hệ cung ứng giả định:

| Thương hiệu hoặc nhà cung cấp | Hàng hóa hoặc dịch vụ | Phạm vi giả định |
|---|---|---|
| Everon | Chăn, ga, gối, đệm và đồ vải phòng ngủ. [Danh mục chính thức](https://everon.com/) | Tám khách sạn sử dụng các quy cách phù hợp từng phân khúc |
| Minh Long | Chén, đĩa, tách và đồ sứ nhà hàng. [Danh mục nhà hàng và khách sạn](https://product.minhlong.com/documents/catalogue/minhlong/hrccatalogue01lifestyle25032026.pdf) | Cung cấp dụng cụ cho nhà hàng và phục vụ buffet |
| MM Mega Market | Thực phẩm và hàng tiêu dùng phục vụ nhà hàng, khách sạn. [Thông tin nhà cung cấp](https://mmvietnam.com/cac-chinh-sach-chung/) | Nguồn cung định kỳ và bổ sung khi nguồn khác giao thiếu |
| Vinamilk | Sữa và sản phẩm từ sữa. [Danh mục sản phẩm](https://www.vinamilk.com.vn/products/sua-dau-nanh-vinamilk-super-soy-gap-doi-canxi) | Phục vụ buffet, nhà hàng và bar |
| Đà Lạt GAP | Rau, củ, quả. [Thông tin doanh nghiệp](https://www.dalatgap.com/gioi-thieu/) | Cung ứng theo hợp đồng, ưu tiên cụm Đà Lạt trong case |
| Daikin | Bảo trì, sửa chữa và linh kiện điều hòa. [Dịch vụ chính thức](https://www.daikin.com.vn/index.php/dich-vu) | Các khách sạn sử dụng thiết bị Daikin tương ứng |
| Schindler | Bảo trì và sửa chữa thang máy. [Dịch vụ chính thức](https://www.schindler.vn/vi/services.html) | Các khách sạn sử dụng thang máy Schindler tương ứng |

CompanyE có thể mua trực tiếp hoặc qua nhà phân phối, đơn vị dịch vụ được chỉ định. Đơn vị ký hợp đồng và xuất chứng từ phải được nhận diện riêng với thương hiệu sản phẩm. Các nguồn tham khảo xác nhận loại sản phẩm hoặc dịch vụ; không xác nhận quan hệ với CompanyE, vùng giao hàng, mức giá hay khả năng cung cấp API trong mô hình.

Mỗi khách sạn có nhiều nhà cung cấp, và một nhà cung cấp có thể phục vụ nhiều cơ sở. Cùng một mặt hàng có thể được mua từ nhiều nguồn; E Grand và E Stay có thể chọn quy cách hoặc chất lượng đầu vào khác nhau.

Nhóm thương nhân địa phương dưới đây hoàn toàn giả định. Đặc điểm không có hệ thống tích hợp và dữ liệu chưa chuẩn hóa được đặt cho nhóm này.

| Cụm | Nhà cung cấp địa phương | Mặt hàng chính |
|---|---|---|
| Sa Pa | Đầu mối Rau Núi Bắc; Cơ sở Cá Nước Lạnh S01 | Rau theo mùa; cá nước lạnh |
| Đà Nẵng | Vựa Hải sản D01; Đầu mối Rau D02 | Hải sản; rau, củ, quả |
| Đà Lạt | Hộ cung ứng Rau L01; Đầu mối Trái cây L02 | Rau theo ngày; trái cây |
| Phú Quốc | Vựa Hải sản P01; Đầu mối Thực phẩm P02 | Hải sản; rau củ và thực phẩm bổ sung |

Hai khách sạn trong cùng cụm có thể đặt cùng một thương nhân nhưng lập đơn riêng. Các thương nhân gửi báo giá, xác nhận đơn, phiếu giao hàng hoặc công nợ bằng Excel, email, nội dung trao đổi được lưu lại, PDF, ảnh hoặc chứng từ giấy. CompanyE không thể gọi API để lấy dữ liệu từ nhóm này.

## 11 Mua hàng và quản lý kho

Bộ phận buồng phòng đề nghị đồ vải và vật dụng; nhà hàng, bar đề nghị thực phẩm, đồ uống; bộ phận kỹ thuật đề nghị vật tư thay thế. Nhu cầu được lập từ tồn kho, kế hoạch phục vụ, số khách dự kiến và lịch thay thế. Một chiến dịch khuyến mãi tăng booking có thể làm nhu cầu mua thực phẩm và vật dụng tăng theo.

Quy trình mua hàng gồm:

1. Bộ phận sử dụng lập đề nghị mua, nêu mặt hàng, quy cách, số lượng và thời điểm cần.
2. Bộ phận mua hàng chọn nguồn cung theo hợp đồng có sẵn hoặc lấy báo giá, phê duyệt theo quy định nội bộ.
3. Đơn đặt hàng xác định giá thỏa thuận, số lượng, nơi giao và lịch giao dự kiến.
4. Người nhận kiểm tra thực giao, ghi số lượng chấp nhận, từ chối và lý do.
5. Hàng được nhập kho hoặc cấp thẳng cho bộ phận sử dụng, nhưng vẫn có ghi nhận tiếp nhận.
6. Kế toán đối chiếu đơn đặt, hàng nhận và chứng từ, sau đó xác nhận khoản phải thanh toán và theo dõi thanh toán.

Một đơn có thể được giao nhiều lần; một hóa đơn có thể gộp nhiều lần giao. Hàng có thể đến trước chứng từ. Giao thiếu, giao muộn, trả hàng, thay hàng và điều chỉnh giá đều tạo các sự kiện liên quan đến giao dịch gốc.

Kho đặt tại từng cụm hoặc khách sạn. Điều chuyển giữa hai khách sạn cùng cụm có phiếu xuất và nhận tương ứng; không ghi thành doanh thu bán ra bên ngoài hoặc một lần mua mới của toàn công ty. Điều chuyển liên cụm phải tính đến thời gian vận chuyển, không giả định diễn ra tức thời.

Thực phẩm được quản lý theo mặt hàng, quy cách, lô nhận, nhà cung cấp, ngày nhận, hạn sử dụng khi có, lượng nhập và lượng xuất. Hàng hỏng, hết hạn, hao hụt và trả lại được ghi riêng. Đồ vải và dụng cụ được ghi nhận nhập, cấp phát, thay thế, mất hoặc hỏng theo bộ phận. Hàng tiêu hao và tài sản sử dụng nhiều kỳ được phân biệt.

Buffet sáng nằm trong giá phòng vẫn phát sinh tiêu thụ nguyên liệu. Kế hoạch nhà hàng xét khách có quyền lợi, khách mua thêm, đoàn đặt trước, buffet tối, ăn trưa và bar. Số suất được hưởng, số suất thực phục vụ và lượng nguyên liệu sử dụng không đồng nhất.

Với buffet, nguyên liệu được ghi nhận theo bếp, ca hoặc bữa phục vụ. Case không giả định biết chính xác từng khách đã ăn bao nhiêu nguyên liệu. Nếu phân bổ chi phí theo suất, đó là phương pháp phân bổ được công bố, không phải quan sát tiêu thụ trực tiếp từng người.

## 12 Bảo dưỡng và tình trạng tài sản

Mỗi khách sạn có danh mục tài sản như điều hòa, thang máy, tủ lạnh, thiết bị bếp và giặt là. Trung tâm giải trí và đội phương tiện cũng ghi nhận tình trạng sẵn sàng của tài sản phục vụ hoạt động tương ứng.

Bảo dưỡng theo kế hoạch gồm kiểm tra, vệ sinh, thay vật tư và bảo trì định kỳ. Bảo dưỡng do sự cố bắt đầu từ báo lỗi hoặc thiết bị hoạt động không đạt yêu cầu. Công việc có thể do nhân viên nội bộ hoặc nhà cung cấp bên ngoài thực hiện.

Mỗi yêu cầu xác định tài sản, cơ sở, vị trí, thời điểm báo lỗi, đơn vị xử lý, nội dung, linh kiện, thời gian ngừng hoạt động và kết quả nghiệm thu. Một công việc có thể nằm trong hợp đồng định kỳ, thuộc bảo hành hoặc phát sinh phí riêng; không mặc định mỗi lượt xử lý đều có khoản thanh toán mới.

Tình trạng tài sản có tác động đến năng lực phục vụ. Phòng có thiết bị hỏng có thể tạm ngừng bán; thiết bị bếp hỏng có thể giảm khả năng phục vụ; xe bảo trì không sẵn sàng cho thuê; một trò chơi có thể đóng trong thời gian sửa chữa. Tài nguyên ngừng hoạt động phải được phân biệt với tài nguyên sẵn sàng nhưng không có khách sử dụng.

## 13 Giao dịch liên đơn vị và đối soát

Một dịch vụ có thể có ba đơn vị khác nhau tham gia: đơn vị bán, đơn vị cung cấp và đơn vị thu tiền. Ví dụ, vendor bán gói phòng kèm vé, khách sạn tiếp nhận booking và trung tâm giải trí phục vụ phần vé. Bản ghi ở các hệ thống phản ánh các sự kiện khác nhau của cùng giao dịch, không phải luôn là những khoản doanh thu độc lập.

Các quy tắc vận hành chung được chốt như sau:

| Nội dung | Quy tắc |
|---|---|
| Đặt và sử dụng | Đặt phòng không đồng nghĩa đã ở; mua vé không đồng nghĩa đã vào cổng; đặt thuê không đồng nghĩa đã nhận xe |
| Các mốc thời gian | Ngày đặt, ngày cung cấp dịch vụ, ngày thu tiền, ngày hoàn tiền và ngày đối soát có thể khác nhau |
| Gói kết hợp | Mỗi thành phần có đơn vị cung cấp và cách phân bổ giá trị; không cộng tổng gói thêm lần nữa vào các thành phần |
| Dịch vụ đi kèm | Vẫn ghi lượt dùng và tiêu thụ tài nguyên nhưng không tự tạo khoản bán thêm |
| Thanh toán | Phân biệt giá trị đặt mua, giá trị dịch vụ thực hiện, tiền đã thu, tiền hoàn và khoản còn chờ đối soát |
| Ưu đãi và hội viên | Ghi nguồn quyền lợi, giá trị giảm, bên tài trợ và điều kiện kết hợp; không cấp trùng quyền lợi |
| Đổi và hủy | Xử lý theo thành phần và điều kiện đã mua; giữ liên kết tới giao dịch gốc |
| Chi phí đầu vào | Đơn mua, hàng nhận, hàng sử dụng, hóa đơn và thanh toán là các sự kiện riêng; tiền mua hàng không tự động bằng chi phí sử dụng trong kỳ |
| Công nợ | Khoản đối tác hoặc nhà cung cấp xác nhận có thể khác thời điểm thực thu, thực chi |

Tiền mua hoặc gia hạn gói hội viên cũng được phân biệt với các lượt dùng quyền lợi của gói. Việc phân bổ khoản này theo thời gian hoặc dịch vụ, nếu được chọn để phân tích, phải có quy tắc riêng; không cộng lại tiền gói mỗi lần hội viên dùng voucher.

Case có dữ liệu chi phí mua hàng, tiêu thụ đầu vào và bảo dưỡng, nhưng chưa mô hình hóa đầy đủ lương, khấu hao, thuế và mọi chi phí chung. Các phân tích sau này chỉ được gọi là lợi nhuận toàn doanh nghiệp khi có đủ phạm vi và quy tắc; ở phạm vi hiện tại, có thể xem xét doanh thu, chi phí đã thu thập hoặc phần chênh lệch tương ứng được định nghĩa rõ.

## 14 Hệ thống vận hành và nguồn dữ liệu

CompanyE sử dụng hai hệ thống nghiệp vụ chính. Mỗi hệ thống có cơ sở dữ liệu riêng; các cơ sở cập nhật theo phạm vi vận hành của mình.

| Hệ thống | Phạm vi | Nhóm dữ liệu chính |
|---|---|---|
| Hotel Operations | Tám khách sạn, nhà hàng, bar và hoạt động hỗ trợ khách sạn | Khách, booking, phòng, lưu trú, quyền lợi ăn sáng, hóa đơn ăn uống, hội viên, khuyến mãi, giao dịch từ đối tác, mua hàng, kho, bảo dưỡng và chứng từ liên quan |
| Entertainment Operations | Bốn trung tâm giải trí và các đội phương tiện | Khách, vé, lượt vào, lượt dùng hoạt động, lịch vận hành, hợp đồng thuê xe, giao/trả xe, tình trạng tài sản, đổi/hủy và giao dịch liên quan |

Trong mô hình, Hotel Operations giữ hồ sơ gốc của chương trình hội viên và các chính sách chung. Entertainment Operations nhận thông tin cần thiết để kiểm tra quyền lợi và trả về các sự kiện sử dụng; cập nhật giữa hai bên có thể chậm. Các phân hệ không nhất thiết lưu cùng một mã khách hàng địa phương.

Tám website là kênh giao dịch của Hotel Operations, không phải tám database độc lập. Bốn cụm phân tán được thể hiện qua mã cơ sở, thời gian ghi nhận, lô đồng bộ và trường hợp dữ liệu cập nhật muộn. Ngoài hai database chính còn có nguồn file và chứng từ từ đối tác, nhà cung cấp; vì vậy tổng số nguồn dữ liệu không bị giới hạn ở hai.

| Nguồn ngoài database | Dữ liệu tiếp nhận | Hình thức giả định |
|---|---|---|
| Đối tác phân phối | Booking, hủy/đổi, bảng đối soát, hoa hồng và tài trợ khuyến mãi | Dữ liệu tích hợp được mô phỏng, CSV, JSON hoặc bảng xuất từ đối tác |
| Nhà cung cấp có tổ chức | Danh mục, báo giá, giao hàng, hóa đơn, công nợ, báo cáo dịch vụ | File bảng, chứng từ điện tử, PDF; chỉ dùng API khi giả định tích hợp có quy định |
| Thương nhân địa phương | Báo giá, xác nhận đơn, phiếu giao, điều chỉnh và công nợ | Excel thủ công, văn bản trao đổi, PDF, ảnh hoặc bản số hóa giấy |
| Bộ phận nội bộ | Kiểm kê, phản hồi khách, biên bản nhận hàng và nghiệm thu | Biểu mẫu, bảng tổng hợp và tệp đính kèm |
| Dữ liệu ngữ cảnh | Thời tiết theo ngày, ngày lễ, cuối tuần và sự kiện giả định | Bảng tham chiếu hoặc file mô phỏng có nhãn nguồn rõ ràng |

Thông tin giao dịch, danh tính đối tác và quyền lợi vẫn được kiểm tra trong quy trình vận hành. Việc nhận file vào kho dữ liệu không tự động đồng nghĩa đã phê duyệt hàng nhận, nghĩa vụ thanh toán hay quyền lợi khách hàng.

## 15 Data lake và dữ liệu chưa chuẩn hóa

Data lake là nơi tiếp nhận bản trích xuất và file thô trước khi xử lý cho mục đích phân tích. Dữ liệu gốc vẫn phát sinh tại hệ thống vận hành hoặc bên cung cấp chứng từ; lake không thay thế database dùng để đặt phòng, kiểm tra phòng trống hoặc xử lý giao dịch tức thời.

Luồng tích hợp của case là: **hai database nghiệp vụ và các nguồn file → data lake lưu dữ liệu thô → trích xuất, chuẩn hóa, đối chiếu và kiểm tra → kho dữ liệu CompanyE**. Dữ liệu của hai mảng khách sạn và giải trí được đưa về cùng một warehouse cùng những dữ liệu đầu vào liên quan.

Data lake giữ file hoặc bản trích xuất ban đầu cùng nguồn gửi, cơ sở liên quan, tên file, thời điểm nhận, lô tiếp nhận và phiên bản. Nội dung được làm sạch không ghi đè chứng từ gốc. Mỗi kết quả chuẩn hóa giữ liên kết về nguồn để truy lại và giải thích sai lệch.

Nhóm thương nhân địa phương tạo ra các tình huống thiếu chuẩn như sau:

| Vấn đề | Ví dụ mô phỏng | Nguyên tắc xử lý nghiệp vụ |
|---|---|---|
| Tên hàng khác nhau | Tên đầy đủ, viết tắt, không dấu hoặc tên địa phương | Đối chiếu danh mục và quy cách; không gộp chỉ vì tên gần giống |
| Khác quy cách | Cá hồi nguyên con, phi lê hoặc đông lạnh | Giữ các mặt hàng khác nhau nếu khác đặc tính mua và sử dụng |
| Đơn vị không thống nhất | kg, gram, chai, thùng, bó, sọt | Chỉ quy đổi khi có căn cứ; số chai trong một thùng phụ thuộc quy cách |
| Cách ghi tiền khác nhau | 25.000, 25000, 25k | Chuẩn hóa khi đủ ngữ cảnh về đơn giá, đơn vị và tiền tệ |
| Thiếu nhận diện | Không có mã đơn hoặc không rõ khách sạn nhận | Đối chiếu thông tin còn lại hoặc chuyển xác minh |
| File không theo mẫu | Ô gộp, đổi tên cột, nhiều bảng, dòng tổng xen dữ liệu | Tách nội dung nghiệp vụ, giữ bản gốc và ghi nhận lỗi |
| Chứng từ dạng ảnh | Viết tay, mờ hoặc thiếu một phần trang | Trích xuất và kiểm tra; không tự đoán trường quan trọng còn thiếu |
| Trùng hoặc sửa đổi | Gửi lại file hoặc bản sửa không có số phiên bản | Xác định bản trùng, bản thay thế và lịch sử điều chỉnh |
| Chậm dữ liệu | Giao hôm trước nhưng hôm sau mới gửi chứng từ | Tách thời điểm phát sinh và thời điểm tiếp nhận |

Khác biệt nguồn không đồng nghĩa mọi dữ liệu đều sai. Dữ liệu có cấu trúc vẫn có thể thiếu trường, trùng giao dịch hoặc cập nhật chậm; dữ liệu từ thương nhân có thể đúng về nghiệp vụ nhưng chưa có định dạng thống nhất.

Ảnh và PDF có thể được trích xuất tự động kết hợp kiểm tra thủ công. Bản ghi chưa đủ căn cứ được giữ ở trạng thái cần xác minh, không âm thầm đi vào báo cáo như dữ liệu đã xác nhận. Thiếu tên hàng, số lượng, đơn vị hay nhà cung cấp không được xử lý bằng cách đoán cho đủ trường.

Các vấn đề phân tán khác gồm khách có mã khác nhau giữa hai hệ thống, số điện thoại nhiều định dạng, người mua khác người dùng, giao dịch gói xuất hiện ở nhiều nơi, thay đổi đến sau báo cáo ngày và phản hồi chỉ liên kết được tới một cơ sở. Không ép mọi giao dịch khách vãng lai vào một hồ sơ khách hàng duy nhất khi thiếu bằng chứng.

## 16 Tình huống vận hành xuyên suốt

Một gia đình có gói E Family đặt hai phòng trong ba đêm tại E Stay Đà Nẵng qua MoMo. Gói đặt phòng đã bao gồm buffet sáng. Booking áp dụng chiến dịch du lịch hè được CompanyE và MoMo đồng tài trợ; điều kiện cho phép ghi nhận hội viên nhưng không cộng thêm ưu đãi giảm phòng khác.

Trong chuyến đi, gia đình mua buffet tối tại E Grand Đà Nẵng, đặt vé E Sóng Biển qua lễ tân và thuê một ô tô trong một ngày. Nhà hàng ghi nhận buffet sáng đã sử dụng mà không thu tiền thêm. Vé và hợp đồng thuê có tham chiếu tới giao dịch bán qua khách sạn, trong khi việc thực hiện được cập nhật tại Entertainment Operations.

Một ngày có thời tiết xấu, trung tâm dừng một hoạt động ngoài trời. Gia đình đổi ngày dùng một phần vé và nhận hoàn tiền cho phần dịch vụ không được cung cấp theo chính sách. Phòng vẫn được sử dụng bình thường. Khoản hoàn tiền và phần điều chỉnh tài trợ khuyến mãi, nếu có, được xử lý theo điều kiện của từng thành phần, không tự áp dụng cho toàn bộ booking.

Đồng thời, khách tăng theo chiến dịch làm nhà hàng đặt bổ sung thực phẩm. Một nhà cung cấp giao thiếu nên khách sạn mua thêm từ Vựa Hải sản D01. Phiếu giao bổ sung là ảnh chụp, ghi tên hàng tắt, và đến data lake ngày hôm sau. Nhân viên nhận hàng đã ghi nhận số lượng thực nhận trong hệ thống vận hành để đối chiếu.

Một tủ lạnh cần sửa chữa khiến một phần nguyên liệu được chuyển sang kho của khách sạn còn lại trong cụm. Nghiệp vụ tạo ra yêu cầu bảo dưỡng, phiếu điều chuyển và biên bản nghiệm thu. Các dữ liệu này có liên quan tới khả năng phục vụ và nguyên liệu sử dụng nhưng không phải các giao dịch bán thêm cho gia đình.

Tình huống phát sinh booking, quyền lợi, chương trình tài trợ, lượt ăn, vé, hợp đồng thuê, hoàn tiền, đơn mua, nhận hàng, điều chuyển, bảo dưỡng và đối soát. Mỗi nguồn ghi nhận một phần sự việc, với thời điểm cập nhật và mức độ chuẩn hóa khác nhau. Dữ liệu tích hợp phải nối được các quan hệ có căn cứ và giữ riêng những giao dịch độc lập.

## 17 Phạm vi dữ liệu mô phỏng và công việc tiếp theo

Dữ liệu được tự sinh dựa trên các quy tắc đã chốt. Các bảng và chứng từ phải tạo thành chuỗi nghiệp vụ có liên hệ, thay vì là các tập số ngẫu nhiên độc lập. Khách chỉ dùng quyền lợi phù hợp; lượt nhận hàng liên hệ đơn mua khi có đơn; thay đổi và hoàn tiền liên hệ giao dịch gốc; lịch ngừng hoạt động phải phù hợp với khả năng cung cấp dịch vụ.

Mô phỏng có biến động theo địa điểm, phân khúc, mùa, ngày trong tuần, thời tiết và chiến dịch. Những quan hệ này có ngoại lệ và độ biến thiên; không gán cứng khách 5 sao luôn chi tiêu cao, mùa mưa luôn ít khách hay nhà cung cấp cụ thể luôn giao muộn.

Các lỗi dữ liệu được tạo có kiểm soát: trùng, thiếu, sai định dạng, khác mã, đến muộn và sửa đổi. Thông tin đúng dùng để đánh giá bộ sinh và kiểm tra kết quả được giữ riêng; quá trình tích hợp chỉ sử dụng những mã tham chiếu và bằng chứng thực sự có trong nguồn nghiệp vụ, không được cấp một mã bí mật để giải sẵn mọi trường hợp đối chiếu.

Thời tiết được mô phỏng phải được ghi rõ là dữ liệu giả lập. Nếu dùng dữ liệu thời tiết thật ở bước sau, cần ghi nguồn và phạm vi tương ứng. Không dùng số liệu giả lập để kết luận về kết quả kinh doanh thực tế của địa phương hoặc đối tác.

Phạm vi nền đã bao gồm dịch vụ khách hàng, phân phối, hội viên, khuyến mãi, tài trợ, mua hàng, kho và bảo dưỡng. Chưa mở rộng thành hệ thống kế toán, nhân sự hoặc chuỗi cung ứng hoàn chỉnh. Nguồn dữ liệu và lake v2 đã được triển khai; thiết kế warehouse và ứng dụng sẽ bám theo **tám nhu cầu nghiệp vụ đã chốt** bên dưới. Mô tả vận hành là bối cảnh doanh nghiệp; không mặc nhiên khẳng định mọi tình huống trong case đều đã được bộ sinh hiện thực. Các giới hạn dữ liệu được ghi trong README và hồ sơ tái lập.

## 18 Tám nhu cầu nghiệp vụ đã chốt

| Mã | Nhu cầu | Người dùng chính dự kiến | Câu hỏi và đầu ra cần phục vụ |
|---|---|---|---|
| B01 | Đánh giá hoạt động lưu trú | Quản lý khách sạn, quản lý doanh thu | Đêm phòng thực ở, công suất phòng, tỷ lệ hủy và no-show theo thời gian, địa điểm, phân khúc 3–5 sao |
| B02 | Đánh giá kênh bán và khuyến mãi | Kinh doanh, marketing, quản lý doanh thu | So sánh kênh trực tiếp và đối tác; giá trị bán, tiền khách phải trả, tài trợ từng bên, hoa hồng và giá trị giữ lại trước chi phí vận hành |
| B03 | Phân tích bán chéo khách sạn và giải trí | Quản lý cụm, kinh doanh | Tỷ lệ booking mua thêm vé hoặc thuê xe, giá trị các dịch vụ gắn booking và so sánh giữa các cụm |
| B04 | Đánh giá hoạt động buffet và nhà hàng | Quản lý nhà hàng, quản lý khách sạn | Suất được hưởng/thực dùng, lượt phục vụ, doanh số bán riêng, chi phí nguyên liệu trên lượt phục vụ |
| B05 | Đánh giá mức sử dụng giải trí và phương tiện | Quản lý trung tâm giải trí, đội xe | Lượt vào thực tế, công suất khả dụng, tỷ lệ sử dụng hoạt động và ngày xe được thuê/ngày xe sẵn sàng theo mùa và thời tiết |
| B06 | Đánh giá chất lượng giao hàng của nhà cung cấp | Mua hàng, tiếp nhận hàng | Lượng đặt, nhận đạt, từ chối, nhận trễ và mức đáp ứng đơn hàng có nhiều lần giao |
| B07 | Kiểm soát tồn kho và hao hụt | Quản lý kho, nhà hàng, mua hàng | Nhập–xuất–tồn theo kỳ, lượng sử dụng/hủy và giá trị hao hụt theo lô, mặt hàng và cơ sở |
| B08 | Đánh giá bảo trì và khả năng cung cấp phòng | Kỹ thuật, quản lý khách sạn | Chi phí bảo trì, số ngày phòng ngừng bán và khả dụng, tránh cộng trùng các khoảng bảo trì |

Các nguyên tắc đã thống nhất: không ghi thêm doanh thu cho buffet đã bao gồm trong giá phòng; không gọi giá trị giữ lại sau khuyến mãi/hoa hồng là lợi nhuận; bán chéo ưu tiên tham chiếu booking có căn cứ; không nhân đôi giao dịch khi nối bảng chi tiết hoặc xử lý file gửi lại. Phân tích mùa vụ/thời tiết mô tả dữ liệu giả lập, không chứng minh tác động nhân quả ngoài thực tế.

`tests/fixtures/business_acceptance.json` giữ các fixture B01–B08 và đáp án tham chiếu. Việc chốt nhu cầu ở đây không biến kết quả kiểm thử tham chiếu thành nghiệm thu warehouse; cần chạy các ca qua pipeline và truy vấn warehouse thật sau khi triển khai.

Đặc tả chi tiết hiện hành: [Đặc tả KPI CompanyE](docs/CompanyE_KPI_Specification.md), phiên bản 1.0 với 47 chỉ tiêu. Các khác biệt so với fixture cũ, nhất là thời điểm ghi nhận chi phí bảo trì, được nêu rõ trong đặc tả; không sửa hồi tố bằng chứng kiểm thử cũ.

## 19 Hướng triển khai và so sánh đã chốt

Ngày 12/10/2026, người dùng chốt so sánh **warehouse với lakehouse**, dùng **Power BI để trực quan hóa** và **triển khai bản thử trên web**.

- Nhánh warehouse: lake v2 → Spark → Oracle staging/warehouse → Power BI.
- Nhánh lakehouse: lake v2 → Spark → bảng Apache Iceberg → lớp truy vấn Spark SQL → Power BI.
- Hai nhánh phục vụ cùng B01–B08, dùng cùng snapshot nguồn, grain, mô hình fact/dimension, quy tắc lịch sử và định nghĩa KPI. Không chọn khác schema làm biến so sánh chính.
- Ứng dụng web trình bày các báo cáo tương tác, bộ lọc và khả năng xem chi tiết phục vụ người dùng đã xác định; cơ chế Power BI Service/nhúng và kết nối được kiểm chứng khi triển khai.
- Đánh giá tính đúng xuyên suốt, hiệu năng xử lý/truy vấn và hiệu quả khai thác qua ứng dụng. Nếu Power BI dùng Import, đo refresh và truy vấn backend riêng với tương tác biểu đồ.

Đây là quyết định kiến trúc mục tiêu, chưa phải xác nhận hai nhánh phân tích và ứng dụng đã hoàn thành. Chi tiết triển khai, giới hạn và công việc tiếp theo được cập nhật trong README.
