"""CompanyE conceptual multidimensional model: shared PDF/draw.io scene graph.

Business concepts only; no PK/FK columns, SQL types or storage structures.
"""
from pathlib import Path
import json, hashlib, math, html
import xml.etree.ElementTree as ET
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
INPUTS=['config/dimensional_model_v1.json','config/warehouse_design_v1.json',
        'config/kpi_contract_v1.json','config/source_target_mapping_v1.json',
        'config/warehouse_design_decisions_v1.json']
def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def save(p,x):(ROOT/p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
HASHES={p:sha(p) for p in INPUTS}
model=read(INPUTS[0]);design=read(INPUTS[1]);kpi=read(INPUTS[2]);mapping=read(INPUTS[3])
facts={f['id']:f for f in model['facts']};dims={d['id']:d for d in model['dimensions']}
processes=model['enterprise_bus_matrix']['processes']
for process in processes:
    if process['id']=='P01':
        process['note']='Phòng và gói giá dùng để chọn booking có liên quan; chưa phân bổ giá trị booking xuống từng phòng.'
    elif process['id']=='P11':
        process['note']='Tồn cuối ngày là tổng hợp tùy chọn; không cộng số dư qua ngày hoặc phân bổ số dư theo khu vực sử dụng.'
for name,file in [('Arial','arial.ttf'),('Arial-Bold','arialbd.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(Path('C:/Windows/Fonts')/file)))
W,H=1600,1100
BLUE='#11129C';INK='#192B43';GRAY='#546476';LIGHT='#F1F5FB';TEAL='#087B7B';ORANGE='#B65E12'

DIM_NAMES={'D01':'Thời gian','D02':'Cụm du lịch','D03':'Khách sạn','D04':'Phòng',
 'D05':'Kênh bán','D06':'Khuyến mãi','D07':'Hồ sơ khách nguồn','D08':'Gói giá',
 'D09':'Điểm ăn uống','D10':'Bữa / dịch vụ ăn uống','D11':'Trung tâm giải trí',
 'D12':'Hoạt động giải trí','D13':'Phương tiện','D14':'Nhà cung cấp','D15':'Mặt hàng','D16':'Tài sản'}

# Measure labels describe concepts; A additive, U additive only within same unit,
# S semi-additive over time, N non-additive/context. Ratios live at KPI layer.
CONCEPTS={
 'F01':('ĐẶT PHÒNG','Một lần đặt phòng ở trạng thái cuối snapshot.',[
   ('Số booking','A'),('Giá trị trước giảm','A'),('Tổng giảm giá','A'),('Khách phải trả','A'),
   ('Giảm giá CompanyE chịu','A'),('Đối tác tài trợ','A'),('Hoa hồng phân phối','A')],
   'Giá trị giữ một lần mỗi booking. Phòng/gói giá chỉ lọc booking có liên quan; chưa phân bổ tiền xuống từng phòng.'),
 'F02':('PHÒNG KHẢ DỤNG','Một phòng trong một ngày công suất.',[
   ('Ngày phòng danh mục','A'),('Ngày phòng bị chặn','A'),('Ngày phòng khả dụng','A')],
   'Giữ cả ngày không có khách. Các khoảng bảo trì chồng nhau chỉ làm mất một room-day.'),
 'F03':('ĐÊM LƯU TRÚ','Một phòng trong một đêm thực ở hợp lệ.',[
   ('Đêm phòng thực ở','A')],
   'Đêm thực ở khác ngày dự kiến. Bộ lọc kênh/khách chỉ phân loại đêm bán, không chia mẫu số công suất.'),
 'F04':('ĐƠN VÉ GIẢI TRÍ','Một đơn mua vé.',[
   ('Giá trị vé trước hoàn','A'),('Tiền hoàn vé','A'),('Giá trị vé sau hoàn','A')],
   'Đơn vé có thể bán độc lập hoặc gắn booking. Giá đơn không lặp theo từng vé hoặc lượt vào.'),
 'F05':('HỢP ĐỒNG THUÊ XE','Một hợp đồng thuê một phương tiện.',[
   ('Giá trị thuê thỏa thuận','A')],
   'Số tiền một lần mỗi hợp đồng. Ngày sử dụng xe được đánh giá bằng khái niệm ngày xe ở hình bên cạnh.'),
 'F06':('QUYỀN LỢI SÁNG','Một quyền lợi của phòng đặt và ngày ăn sáng.',[
   ('Suất sáng được hưởng','A'),('Suất quyền lợi thực dùng','A')],
   'Included breakfast không tạo thêm doanh thu. Ngày ăn từ sáng sau check-in đến sáng checkout.'),
 'F07':('HÓA ĐƠN ĂN UỐNG','Một hóa đơn bán riêng, không phải dòng món.',[
   ('Giá trị bán riêng sau giảm','A'),('Lượt khách phục vụ','A'),('Tổng điểm đánh giá','A'),('Số hóa đơn có đánh giá','A')],
   'Nơi ăn có thể khác nơi đặt phòng. Điểm trung bình = tổng điểm / số hóa đơn, không lấy trọng số theo lượt khách.'),
 'F08':('PHIÊN BUFFET','Một nhà hàng, ngày phục vụ và bữa buffet.',[
   ('Lượt thực dùng của phiên','A'),('Chi phí nguyên liệu phiên','A')],
   'Chỉ bữa sáng và tối. Lượt phiên dùng tính chi phí/lượt, không cộng lại vào lượt hóa đơn + quyền lợi.'),
 'F09':('LƯỢT VÀO HOẠT ĐỘNG','Một lượt vào thực tế được ghi nhận.',[
   ('Số lượt sử dụng hoạt động','A')],
   'Ngày sử dụng lấy thời điểm vào. Một khách có thể có nhiều lượt; số lượt không phải số người duy nhất.'),
 'F10':('CÔNG SUẤT HOẠT ĐỘNG','Một hoạt động trong một ngày công suất.',[
   ('Công suất danh định','A'),('Cờ đóng cửa','N'),('Công suất khả dụng','A')],
   'Ngày đóng cửa có công suất khả dụng bằng 0. Công suất chưa được phân bổ theo khách hoặc kênh bán.'),
 'F11':('NGÀY XE','Một phương tiện trong một ngày công suất.',[
   ('Ngày xe danh mục','A'),('Ngày bảo trì','A'),('Ngày xe sẵn sàng','A'),('Ngày xe được thuê','A')],
   'Không đồng nhất hợp đồng với ngày xe. Ngày thuê/bảo trì trùng nhau là dữ liệu xung đột cần báo.'),
 'F12':('DÒNG ĐẶT MUA','Một dòng mặt hàng trong đơn mua.',[
   ('Lượng đặt','U'),('Đơn giá thỏa thuận','N')],
   'Một dòng có thể nhận nhiều đợt. Giữ cả dòng đến hạn chưa nhận; đơn giá không cộng như lượng mua.'),
 'F13':('LẦN NHẬN HÀNG','Một lần nhận của một dòng đặt mua; định danh lô.',[
   ('Lượng nhận đạt','U'),('Lượng bị từ chối','U'),('Lượng đạt nhưng nhận trễ','U')],
   'Ngày nhận hàng khác ngày file đến. Feed nhà cung cấp chỉ đối soát, không tăng thêm lượng nhận.'),
 'F14':('BIẾN ĐỘNG KHO','Một biến động của một lô hàng tại khách sạn.',[
   ('Lượng biến động','U'),('Lượng có dấu nhập / xuất','U'),('Lượng nhập','U'),('Lượng sử dụng','U'),('Lượng hủy','U'),('Giá trị biến động theo lô','A')],
   'Tồn được suy từ lịch sử nhập - dùng - hủy. Hàng bị từ chối chưa nhập kho không trở thành hao hụt kho.'),
 'F15':('TỒN CUỐI NGÀY','Một lô, khách sạn, mặt hàng tại cuối một ngày.',[
   ('Lượng tồn cuối ngày','S/U'),('Giá trị tồn cuối ngày','S'),('Lượng nhập trong ngày','U'),('Lượng dùng trong ngày','U'),('Lượng hủy trong ngày','U')],
   'Tổng hợp tùy chọn từ sổ kho. Số dư chỉ cộng các lô cùng thời điểm, không cộng qua nhiều ngày.'),
 'F16':('CÔNG VIỆC BẢO TRÌ','Một công việc bảo trì tài sản khách sạn.',[
   ('Chi phí công việc','A')],
   'Chi phí theo ngày hoàn tất. Tài sản khu chung không tự làm ngừng cả khách sạn; ảnh hưởng phòng thuộc P03.'),
 'F17':('THỜI TIẾT NGÀY','Một cụm du lịch trong một ngày quan sát giả lập.',[
   ('Nhiệt độ','N'),('Lượng mưa','N*'),('Cờ thời tiết cực đoan','N')],
   'Ngữ cảnh, không là quá trình giao dịch thứ 13. Mưa cộng qua ngày trong cùng cụm; không SUM nhiệt độ hoặc suy nhân quả.'),
}
ROLES={
 'F01':{'D01':'Ngày đặt / đến / trả','D03':'Khách sạn đặt','D05':'Kênh booking','D07':'Người đặt'},
 'F02':{'D01':'Ngày công suất'},'F03':{'D01':'Đêm thực ở'},
 'F04':{'D01':'Ngày bán / trả phòng*','D02':'Cụm phục vụ / booking*','D03':'Khách sạn giới thiệu*','D05':'Kênh vé / booking*','D07':'Người mua vé'},
 'F05':{'D01':'Ngày nhận / trả xe; cohort*','D02':'Cụm phục vụ / booking*','D03':'Khách sạn giới thiệu*','D05':'Kênh booking*','D07':'Người thuê'},
 'F06':{'D01':'Ngày ăn sáng','D03':'Khách sạn phục vụ','D09':'Nhà hàng ánh xạ','D10':'Chỉ BREAKFAST'},
 'F07':{'D01':'Ngày phục vụ','D03':'Nơi phục vụ / đặt phòng*','D07':'Khách ăn, có thể chưa biết'},
 'F08':{'D01':'Ngày phục vụ','D10':'Sáng / tối'},
 'F09':{'D01':'Ngày vào thực tế'},'F10':{'D01':'Ngày công suất'},'F11':{'D01':'Ngày xe'},
 'F12':{'D01':'Ngày đặt / hẹn giao','D03':'Khách sạn nhận'},
 'F13':{'D01':'Ngày nhận / hẹn / hạn*','D03':'Khách sạn nhận'},
 'F14':{'D01':'Ngày biến động','D03':'Khách sạn giữ kho'},
 'F15':{'D01':'Ngày chốt tồn','D03':'Khách sạn giữ kho'},
 'F16':{'D01':'Ngày bắt đầu / hoàn tất','D04':'Phòng nếu xác định được'},
 'F17':{'D01':'Ngày thời tiết'},
}

HIERARCHIES=[
 dict(id='H01',name='Thời gian',levels=['Ngày','Tháng trong năm','Quý trong năm','Năm'],kind='ROLLUP',
      rule='Tháng/quý phải kèm năm; không gộp tháng 1 của nhiều năm như một thành viên. Thứ trong tuần là thuộc tính phân nhóm; mùa du lịch chưa có quy tắc theo cụm.'),
 dict(id='H02',name='Phòng và địa điểm',levels=['Phòng','Khách sạn','Cụm du lịch','CompanyE'],kind='ROLLUP',
      rule='Mỗi phòng thuộc một khách sạn tại thời điểm phân tích. Hạng sao và loại phòng là nhánh phân loại riêng, không phải các cấp nằm giữa hotel và site.'),
 dict(id='H03',name='Điểm ăn uống',levels=['Điểm ăn uống','Khách sạn phục vụ','Cụm phục vụ','CompanyE'],kind='ROLLUP',
      rule='Nhà hàng/bar tổng hợp theo nơi phục vụ; khách sạn nơi đặt phòng là vai trò khác, không thay thế nơi phục vụ.'),
 dict(id='H04',name='Hoạt động giải trí',levels=['Hoạt động','Trung tâm','Cụm du lịch','CompanyE'],kind='ROLLUP',
      rule='Chỉ cộng công suất có cùng đơn vị lượt hoạt động; đây không phải số khách duy nhất toàn trung tâm.'),
 dict(id='H05',name='Phương tiện',levels=['Phương tiện','Trung tâm quản lý','Cụm du lịch','CompanyE'],kind='ROLLUP',
      rule='Loại xe là nhánh phân nhóm khác. Tỷ lệ đội xe phải tính lại từ tổng ngày thuê / tổng ngày sẵn sàng.'),
 dict(id='H06',name='Tài sản khách sạn',levels=['Tài sản','Khách sạn quản lý','Cụm du lịch','CompanyE'],kind='ROLLUP',
      rule='Không bắt buộc đi qua Phòng: có tài sản khu chung không thuộc phòng. Bên bán tài sản không mặc định là nhà thầu sửa chữa.'),
 dict(id='H07',name='Kênh bán',levels=['Kênh trong nguồn','Loại kênh','Tất cả kênh trong nguồn'],kind='CLASSIFICATION',
      rule='Kênh booking và kênh vé có miền định danh riêng. Không coi cùng tên là cùng một kênh toàn doanh nghiệp.'),
 dict(id='H08',name='Nhà cung cấp',levels=['Nhà cung cấp','Nhóm nhà cung cấp','Tất cả nhà cung cấp'],kind='CLASSIFICATION',
      rule='Cụm của supplier là phạm vi nhà cung cấp; cụm nhận hàng lấy từ khách sạn nhận, không thay bằng supplier site.'),
 dict(id='H09',name='Mặt hàng và đơn vị',levels=['Mặt hàng / quy cách','Đơn vị cơ sở'],kind='UNIT_GROUP',
      rule='Chỉ tổng lượng trong cùng đơn vị tương thích. Giá trị VND có thể cộng nhiều mặt hàng; không tạo tổng 10 kg + 5 cái = 15 đơn vị.'),
]

class Page:
    def __init__(self,name,title,subtitle):self.name=name;self.title=title;self.subtitle=subtitle;self.nodes=[];self.edges=[]
    def box(self,id,x,y,w,h,title='',body='',kind='box',size=20,fill='#FFFFFF',stroke=INK):
        assert x>=40 and y>=130 and x+w<=W-30 and y+h<=H-80,(id,x,y,w,h)
        obj=dict(id=id,x=x,y=y,w=w,h=h,title=title,body=body,kind=kind,size=size,fill=fill,stroke=stroke)
        self.nodes.append(obj);return obj
    def edge(self,src,dst,arrow=False,dashed=False):
        self.edges.append(dict(source=src['id'],target=dst['id'],arrow=arrow,dashed=dashed))

def wrap(text,width,size,font='Arial'):
    lines=[]
    for para in text.split('\n'):
        line=''
        for word in para.split():
            if line and pdfmetrics.stringWidth(line+' '+word,font,size)>width:lines.append(line);line=word
            else:line=(line+' '+word).strip()
        lines.append(line)
    return lines

PAGES=[]
p=Page('00-pham-vi','CompanyE - Mô hình ý niệm kho dữ liệu','Quá trình, số đo, chiều và cấp tổng hợp | Chốt phạm vi B01-B08 | 13/10/2026')
p.box('intro',65,155,1470,110,'Câu hỏi thiết kế','Doanh nghiệp cần quan sát điều gì, ở mức chi tiết nào, theo những góc nhìn nào? Mô hình này độc lập Oracle/Iceberg; chưa mô tả khóa kỹ thuật, kiểu dữ liệu hoặc cách lưu bảng.',size=21,fill=LIGHT)
groups=[('LƯU TRÚ VÀ BÁN HÀNG','P01 Đặt phòng\nP02 Thực hiện lưu trú\nP03 Phòng khả dụng\nB01, B02 và cohort B03'),
        ('DỊCH VỤ KHÁCH HÀNG','P04 Bán vé; P05 Sử dụng hoạt động\nP06 Thuê phương tiện\nP07 Quyền lợi sáng; P08 Ăn uống\nB03, B04, B05'),
        ('CUNG ỨNG VÀ VẬN HÀNH','P09 Đặt mua; P10 Nhận hàng\nP11 Biến động và tồn kho\nP12 Bảo trì tài sản\nB06, B07, B08')]
for i,(title,body) in enumerate(groups):p.box('group'+str(i),65+i*500,310,470,245,title,body,size=21,fill='#F7FAFE')
p.box('conformed',65,605,960,175,'GÓC NHÌN DÙNG CHUNG','Thời gian, cụm, khách sạn và các chiều nghiệp vụ được dùng nhất quán. Vai trò phục vụ, đặt phòng và giới thiệu phải phân biệt; hồ sơ khách hai nguồn chưa được hợp nhất thành một người duy nhất.',size=23,fill='#EFF9F7',stroke=TEAL)
p.box('context',1060,605,475,175,'NGỮ CẢNH THỜI TIẾT','Một cụm / ngày. Hỗ trợ phân tích B05; chưa định nghĩa mùa cao/thấp điểm và không chứng minh quan hệ nhân quả.',size=21)
p.box('legend',65,825,1470,135,'CÁCH ĐỌC CÁC SƠ ĐỒ','Hộp vuông: hiện tượng cần đo. Hộp bo góc: chiều phân tích. Mũi tên cấp tổng hợp: chi tiết → khái quát. A: cộng được; U: chỉ cộng cùng đơn vị; S: không cộng số dư qua ngày; N: không cộng hoặc là ngữ cảnh. F/P/D chỉ để truy vết các tài liệu, không phải cột dữ liệu.',size=20)
PAGES.append(p)

def hierarchy_page(name,title,ids):
    p=Page(name,title,'Mũi tên từ mức chi tiết đến mức khái quát; quan hệ xét tại đúng thời điểm nghiệp vụ.')
    for row,hid in enumerate(ids):
        h=next(z for z in HIERARCHIES if z['id']==hid);y=175+row*260
        p.box(hid+'name',65,y,260,70,h['name'],'',size=23,fill=LIGHT)
        previous=None
        count=len(h['levels']);bw=245 if count==4 else 320
        for i,label in enumerate(h['levels']):
            node=p.box(hid+str(i),355+i*(bw+45),y,bw,70,label,'',kind='round',size=22)
            if previous:p.edge(previous,node,arrow=True)
            previous=node
        p.box(hid+'rule',355,y+92,1150,100,'',h['rule'],kind='note',size=22,fill='#FFFFFF',stroke='#FFFFFF')
    return p
PAGES.append(hierarchy_page('01-cap-thoi-gian-dia-diem','Cấp tổng hợp - Thời gian và khách sạn',['H01','H02','H06']))
PAGES.append(hierarchy_page('02-cap-dich-vu','Cấp tổng hợp - Ăn uống, giải trí và xe',['H03','H04','H05']))
p=hierarchy_page('03-phan-loai','Phân nhóm bổ sung và giới hạn tổng hợp',['H07','H08','H09'])
p.box('flat',65,960,1470,55,'','Hồ sơ khách, khuyến mãi, gói giá và bữa chưa có phân cấp chuẩn bổ sung; giữ là các chiều phẳng với thuộc tính mô tả.',kind='note',size=18,fill=LIGHT)
PAGES.append(p)

def draw_fact(p,fid,x,width):
    title,grain,measures,note=CONCEPTS[fid];single=width>1000
    dimids=list(facts[fid]['dimension_roles'])
    dw=310 if single else 175
    fw=440 if single else 300
    fx=x+(width-fw)/2
    box=p.box(fid,fx,325,fw,370,title,'\n'.join(f'[{kind}] {name}' for name,kind in measures),kind='fact',size=24 if single else 19,fill='#F0F4FE',stroke=BLUE)
    for i,did in enumerate(dimids):
        side=i%2;idx=i//2;num=(len(dimids)+1-side)//2
        yy=205+idx*(490/max(num-1,1)) if num>1 else 450
        xx=x+10 if side==0 else x+width-dw-10
        role=ROLES.get(fid,{}).get(did,'')
        node=p.box(fid+did,xx,yy,dw,118,DIM_NAMES[did],role,kind='round',size=23 if single else 16)
        p.edge(box,node)
    p.box(fid+'grain',x+10,815,width-20,145,'GRAIN: '+grain,note,kind='note',size=21 if single else 18,fill=LIGHT)

for process in processes:
    req=', '.join(process['requirements'])
    p=Page(process['id'],process['id']+' - '+process['name'],f'Nhu cầu {req} | Mỗi hộp fact có một grain riêng; đường nối chỉ mô tả góc nhìn phân tích.')
    ff=process['facts']
    if len(ff)==1:draw_fact(p,ff[0],60,1480)
    else:
        draw_fact(p,ff[0],50,740);draw_fact(p,ff[1],810,740)
    p.box('process-note',65,975,1470,42,'',process['note'],kind='note',size=17,fill='#FFFFFF',stroke='#FFFFFF')
    PAGES.append(p)
p=Page('C01','Ngữ cảnh - Thời tiết theo cụm và ngày','Hỗ trợ B05 khi phân tích theo thời tiết; không làm thay đổi grain lượt vào hoặc công suất.')
draw_fact(p,'F17',60,1480);PAGES.append(p)

p=Page('coverage','Từ nhu cầu quyết định đến các khái niệm','Tám nhu cầu và 47 KPI đã chốt được truy vết; không tạo thêm nhu cầu nghiệp vụ.')
for i,r in enumerate(kpi['requirements']):
    y=160+i*92
    needed=sorted({f for m in design['metric_mapping'] if m['id'].startswith(r['id']+'.') for key in ['primary_facts','supporting_facts','optional_facts'] for f in m[key]})
    label=', '.join(f+' '+CONCEPTS[f][0].lower() for f in needed)
    p.box(r['id'],65,y,510,80,r['id']+' - '+r['name'],str(len(r['metrics']))+' KPI',size=19,fill=LIGHT)
    p.box(r['id']+'facts',600,y,935,80,'',label,kind='note',size=20,fill='#FFFFFF',stroke='#FFFFFF')
p.box('coverage-note',65,925,1470,85,'','B05 còn dùng thời tiết làm ngữ cảnh tùy bộ lọc. F15 là tổng hợp tùy chọn của F14; không có F15 vẫn tính được B07. Mã KPI và công thức chi tiết giữ trong hợp đồng KPI hiện có.',kind='note',size=21,fill='#EFF9F7')
PAGES.append(p)

p=Page('rules','Quy tắc ý niệm cần giữ khi triển khai','Ràng buộc ý nghĩa và tổng hợp; chưa quyết định schema vật lý hoặc cấu trúc lưu trữ.')
notes=[
 ('Đúng grain trước khi cộng','Booking, đêm phòng, hóa đơn, phiên buffet và lượt vào là các sự kiện khác nhau. Tổng hợp từng nguồn về cùng mức trước khi so sánh; không nối nhiều fact chi tiết rồi cộng tiền.'),
 ('Tỷ lệ tính lại từ các số cơ sở','Công suất, tỷ lệ dùng quyền lợi, đáp ứng hàng và hao hụt đều là số đo không cộng được. Tính tổng tử / tổng mẫu; mẫu số 0 để trống, không gán 0%.'),
 ('Số dư theo thời điểm và đơn vị','Tồn cuối ngày không cộng qua nhiều ngày. Lượng chỉ cộng khi đơn vị tương thích; giá trị VND cộng được giữa các mặt hàng. Giá danh mục không thay giá giao dịch.'),
 ('Giữ ngữ cảnh lịch sử','Phân loại giao dịch theo thuộc tính và quan hệ tại thời điểm nghiệp vụ. Đã chọn giữ phiên bản; v2 hiện có một phiên bản khởi tạo theo giả định mô phỏng.'),
 ('Báo cáo phần hợp lệ và nói rõ phần thiếu','Khi còn lỗi, báo cáo vẫn dùng tập hợp lệ với nhãn thiếu và phạm vi ảnh hưởng. Không đủ dữ liệu khác với không phát sinh; không tự thay giá trị thiếu bằng 0.'),
 ('Phạm vi và giới hạn của mô hình','Chưa bổ sung KPI hội viên, dòng tiền, ROI, lợi nhuận đầy đủ hay định danh khách toàn chuỗi. Chưa suy mùa du lịch, tỉnh/vùng hành chính hoặc kho vật lý riêng từ nguồn không có thuộc tính đó.'),
]
for i,(title,body) in enumerate(notes):
    x=65+(i%2)*755;y=170+(i//2)*235
    p.box('rule'+str(i),x,y,715,205,title,body,size=21,fill=LIGHT if i%2==0 else '#FFFFFF')
p.box('reference',65,900,1470,110,'CƠ SỞ TRÌNH BÀY','CO5173 Chapter 2: trang 65 (Dimensions), 66 (Facts), 68 (Fact scheme); trang 56 (tính cộng được). Ký hiệu được điều chỉnh cho CompanyE. Conceptual model này là đầu vào để cập nhật sơ đồ luận lý ở bước tiếp theo; không tự thay đổi DDL, seed hoặc nguồn.',size=19,fill='#EFF9F7')
PAGES.append(p)

def endpoints(a,b):
    ax=a['x']+a['w']/2;ay=a['y']+a['h']/2;bx=b['x']+b['w']/2;by=b['y']+b['h']/2
    def point(n,cx,cy,dx,dy):
        scale=min((n['w']/2)/abs(dx) if dx else 1e20,(n['h']/2)/abs(dy) if dy else 1e20)
        return cx+dx*scale,cy+dy*scale
    return point(a,ax,ay,bx-ax,by-ay),point(b,bx,by,ax-bx,ay-by)

def node_lines(n):
    size=n['size'];pad=16
    title=wrap(n['title'],n['w']-2*pad,size,'Arial-Bold') if n['title'] else []
    body=wrap(n['body'],n['w']-2*pad,size-1) if n['body'] else []
    total=len(title)*size*1.2 + (12 if title and body else 0)+len(body)*(size-1)*1.25
    assert total<=n['h']-20,('Text overflow',n['id'],total,n['h'],n['title'])
    return title,body,total

def create_pdf():
    c=canvas.Canvas(str(ROOT/'docs/CompanyE_Conceptual_Warehouse_Model.pdf'),pagesize=(W,H))
    c.setTitle('CompanyE - Mô hình ý niệm kho dữ liệu')
    for index,p in enumerate(PAGES,1):
        c.setFillColor(HexColor('#FFFFFF'));c.rect(0,0,W,H,fill=1,stroke=0)
        c.setFillColor(HexColor(BLUE));c.rect(0,0,26,H,fill=1,stroke=0)
        c.setFont('Arial',36);c.drawString(65,H-69,p.title)
        c.setStrokeColor(HexColor(BLUE));c.line(54,H-92,W-35,H-92)
        c.setFillColor(HexColor(GRAY));c.setFont('Arial',18);c.drawString(65,H-125,p.subtitle)
        byid={n['id']:n for n in p.nodes}
        for edge in p.edges:
            start,end=endpoints(byid[edge['source']],byid[edge['target']]);sx,sy=start;tx,ty=end
            c.setStrokeColor(HexColor(INK));c.setLineWidth(1.6)
            c.setDash(5,4) if edge['dashed'] else c.setDash()
            c.line(sx,H-sy,tx,H-ty)
            if edge['arrow']:
                angle=math.atan2(ty-sy,tx-sx)
                for delta in [-.45,.45]:c.line(tx,H-ty,tx-11*math.cos(angle+delta),H-(ty-11*math.sin(angle+delta)))
        c.setDash()
        for n in p.nodes:
            c.setFillColor(HexColor(n['fill']));c.setStrokeColor(HexColor(n['stroke']));c.setLineWidth(1.3)
            if n['kind']=='round':c.roundRect(n['x'],H-n['y']-n['h'],n['w'],n['h'],13,fill=1,stroke=1)
            else:c.rect(n['x'],H-n['y']-n['h'],n['w'],n['h'],fill=1,stroke=1)
            titles,bodies,total=node_lines(n);yy=n['y']+(n['h']-total)/2
            c.setFillColor(HexColor(INK))
            for text in titles:
                c.setFont('Arial-Bold',n['size']);c.drawString(n['x']+16,H-yy-n['size'],text);yy+=n['size']*1.2
            if titles and bodies:yy+=12
            for text in bodies:
                c.setFont('Arial',n['size']-1);c.drawString(n['x']+16,H-yy-(n['size']-1),text);yy+=(n['size']-1)*1.25
        c.setFont('Arial',14);c.setFillColor(HexColor(GRAY))
        c.drawString(65,37,'CompanyE | Thiết kế ý niệm | A / U / S / N: xem chú giải trang 1 | *: vai trò có thể không áp dụng hoặc chưa biết')
        c.drawRightString(W-45,37,f'{index:02d} / {len(PAGES):02d}')
        c.showPage()
    c.save()

def create_drawio():
    mx=ET.Element('mxfile',host='app.diagrams.net',type='device')
    for i,p in enumerate(PAGES):
        diagram=ET.SubElement(mx,'diagram',id='conceptual-'+str(i),name=p.name)
        graph=ET.SubElement(diagram,'mxGraphModel',dx=str(W),dy=str(H),grid='1',page='1',pageWidth=str(W),pageHeight=str(H))
        root=ET.SubElement(graph,'root');ET.SubElement(root,'mxCell',id='0');ET.SubElement(root,'mxCell',id='1',parent='0')
        for uid,text,x,y,w,h,size,color in [('title',p.title,65,30,1470,55,36,BLUE),('subtitle',p.subtitle,65,98,1470,34,18,GRAY)]:
            cell=ET.SubElement(root,'mxCell',id=uid,value=text,style=f'text;html=0;align=left;fontFamily=Arial;fontSize={size};fontColor={color};',vertex='1',parent='1')
            ET.SubElement(cell,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),attrib={'as':'geometry'})
        for n in p.nodes:
            value=('<b>'+html.escape(n['title'])+'</b><br><br>' if n['title'] and n['body'] else '<b>'+html.escape(n['title'])+'</b>' if n['title'] else '')+html.escape(n['body']).replace('\n','<br>')
            style=f'rounded={1 if n["kind"]=="round" else 0};whiteSpace=wrap;html=1;align=left;verticalAlign=middle;spacing=16;fontFamily=Arial;fontSize={n["size"]};fillColor={n["fill"]};strokeColor={n["stroke"]};'
            cell=ET.SubElement(root,'mxCell',id=n['id'],value=value,style=style,vertex='1',parent='1')
            ET.SubElement(cell,'mxGeometry',x=str(n['x']),y=str(n['y']),width=str(n['w']),height=str(n['h']),attrib={'as':'geometry'})
        for j,e in enumerate(p.edges):
            style=f'edgeStyle=none;rounded=0;html=1;endArrow={"classic" if e["arrow"] else "none"};strokeColor={INK};dashed={int(e["dashed"])};'
            cell=ET.SubElement(root,'mxCell',id='edge-'+str(j),edge='1',parent='1',source=e['source'],target=e['target'],style=style)
            ET.SubElement(cell,'mxGeometry',relative='1',attrib={'as':'geometry'})
    ET.ElementTree(mx).write(ROOT/'docs/CompanyE_Conceptual_Warehouse_Model.drawio',encoding='utf-8',xml_declaration=True)

def validate():
    assert len(CONCEPTS)==17 and set(CONCEPTS)==set(facts)
    assert set(DIM_NAMES)==set(dims)
    assert len(PAGES)==19
    for p in PAGES:
        ids=[n['id'] for n in p.nodes];assert len(ids)==len(set(ids))
        for n in p.nodes:node_lines(n)
        for e in p.edges:assert e['source'] in ids and e['target'] in ids
    for path,digest in HASHES.items():assert sha(path)==digest
    assert len(design['metric_mapping'])==47

if __name__=='__main__':
    validate();create_pdf();create_drawio()
    pdf=PdfReader(ROOT/'docs/CompanyE_Conceptual_Warehouse_Model.pdf')
    text='\n'.join(p.extract_text() for p in pdf.pages)
    assert len(pdf.pages)==19
    for concept in CONCEPTS.values():assert concept[0] in text,concept[0]
    for d in DIM_NAMES.values():assert d in text,d
    for r in kpi['requirements']:assert r['id'] in text
    document=dict(version='companye-conceptual-warehouse-1.0',created_on='2026-10-13',status='CONCEPTUAL_DESIGN',
      scope='DBMS-independent business concepts; existing requirements and KPI definitions retained.',
      business_processes=processes,context_concepts=['F17'],
      facts=[dict(id=f,title=v[0],grain=v[1],measures=[dict(name=n,aggregation=a) for n,a in v[2]],note=v[3],
                  dimensions=[dict(id=d,name=DIM_NAMES[d],role=ROLES.get(f,{}).get(d,'')) for d in facts[f]['dimension_roles']]) for f,v in CONCEPTS.items()],
      dimensions=[dict(id=d,name=n) for d,n in DIM_NAMES.items()],hierarchies=HIERARCHIES,
      requirements=[dict(id=r['id'],name=r['name'],metrics=[m['id'] for m in r['metrics']]) for r in kpi['requirements']],
      metric_mapping=design['metric_mapping'],business_constraints=[dict(title=t,rule=b) for t,b in notes],
      reference_slides={'course':'CO5173 Chapter 2','pages':[56,65,66,68]},input_sha256=HASHES)
    save('config/conceptual_warehouse_model_v1.json',document)
    report=dict(status='PASSED_STRUCTURAL_CHECKS',visual_review='PENDING',pages=len(PAGES),processes=12,concepts=17,dimensions=16,
                hierarchies=len(HIERARCHIES),requirements=8,kpis=47,input_sha256=HASHES,
                page_index=[p.name for p in PAGES],limitations=['Native draw.io XML generated and endpoints checked; not tested in draw.io UI.','Conceptual design only; no changes to logical diagrams or physical schema.'],
                output_sha256={p:sha(p) for p in ['docs/CompanyE_Conceptual_Warehouse_Model.pdf','docs/CompanyE_Conceptual_Warehouse_Model.drawio','config/conceptual_warehouse_model_v1.json']})
    save('reports/conceptual_warehouse_model_v1_validation.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ['input_sha256','output_sha256']},ensure_ascii=False,indent=2))
