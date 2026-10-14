"""Render the logical model from design 1.1 without changing its contracts.

Shared PDF/draw.io scene; every target column and role-specific FK is checked.
This generates documentation, not physical DDL or engine-side constraints.
"""
from pathlib import Path
import json, hashlib, html, math
import xml.etree.ElementTree as ET
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
INPUTS=['config/warehouse_design_v1.json','config/conceptual_warehouse_model_v1.json',
        'config/source_target_mapping_v1.json','config/kpi_contract_v1.json',
        'config/dimensional_model_v1.json','config/warehouse_design_decisions_v1.json']
def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
def digest(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def save(p,data):(ROOT/p).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
HASHES={p:digest(p) for p in INPUTS}
design,concept,mapping,kpi,baseline,decisions=[read(p) for p in INPUTS]
assert design['version']=='companye-warehouse-design-1.1'
tables={t['id']:t for t in design['tables']}
dims={i:t for i,t in tables.items() if i.startswith('D')}
facts={i:t for i,t in tables.items() if i.startswith('F')}
links={i:t for i,t in tables.items() if i.startswith('L')}
for name,file in [('Arial','arial.ttf'),('Arial-Bold','arialbd.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(Path('C:/Windows/Fonts')/file)))
W,H=1800,1250
BLUE='#15109F';INK='#20334B';MUTED='#516479';PALE='#EDF4FB';TEAL='#087D91'
AUDIT={'source_batch_id','transform_version','row_hash','created_at_utc','updated_at_utc'}
HISTORY={'valid_from_utc','valid_to_utc','is_current','version_no','effective_time_basis'}
AGG={'SUM':'M','SUM_SAME_UNIT':'MU','SEMI_ADDITIVE_DATE':'MS',
     'SEMI_ADDITIVE_DATE_SAME_UNIT':'MSU','AVG_SITE_DAY':'MN','SUM_DATE_WITHIN_SITE':'MT'}
DOMAIN={'KEY':'Khóa số nguyên; gồm 0/-1 cho dimension.', 'DATEKEY':'Mã ngày YYYYMMDD; 0/-1 là thành viên đặc biệt.',
 'COUNT':'Số nguyên đếm không âm.', 'INT':'Số nguyên có dấu.', 'FLAG':'Cờ 0 hoặc 1.',
 'MONEY':'Số tiền VND nguyên, chính xác.', 'QTY':'Số lượng chính xác, 3 chữ số thập phân.',
 'VALUE':'Giá trị lượng x đơn giá, giữ 3 số lẻ.', 'DATE':'Ngày lịch, không kèm giờ.',
 'UTC':'Thời điểm UTC, độ chính xác microsecond.', 'ID':'Định danh nguồn; giữ namespace và nội dung mã.',
 'CODE':'Mã phân loại có danh mục.', 'TEXT':'Văn bản Unicode.', 'HASH':'SHA256, 64 ký tự hex chữ thường.'}

def wrap(text,width,size=18,bold=False):
    out=[];font='Arial-Bold' if bold else 'Arial'
    for para in str(text).split('\n'):
        line=''
        for word in para.split():
            assert pdfmetrics.stringWidth(word,font,size)<=width,('word overflow',word,width,size)
            trial=(line+' '+word).strip()
            if line and pdfmetrics.stringWidth(trial,font,size)>width:out.append(line);line=word
            else:line=trial
        out.append(line)
    return out

class Page:
    def __init__(self,name,title,subtitle):
        self.name=name;self.title=title;self.subtitle=subtitle;self.boxes=[];self.notes=[];self.edges=[]
    def note(self,uid,x,y,w,h,title,body,size=20,fill='#FFFFFF'):
        titlelines=wrap(title,w-32,size,True) if title else []
        lines=wrap(body,w-32,size)
        used=30+len(titlelines)*size*1.3+(12 if titlelines else 0)+len(lines)*size*1.3
        assert used<=h,(self.name,uid,used,h)
        n=dict(id=uid,x=x,y=y,w=w,h=h,title=title,body=body,size=size,fill=fill)
        self.notes.append(n);return n
    def box(self,uid,x,y,w,title,rows,kind='dim',font=17,rh=27):
        assert pdfmetrics.stringWidth(title,'Arial-Bold',font+1)<=w-24,(title,w)
        for row in rows:assert pdfmetrics.stringWidth(row,'Arial',font)<=w-24,(self.name,row,w,font)
        b=dict(id=uid,x=x,y=y,w=w,h=38+len(rows)*rh,title=title,rows=rows,kind=kind,font=font,rh=rh)
        self.boxes.append(b);return b
    def edge(self,source,sr,target,tr,side='left',lane=0,dashed=False,semantic='FK'):
        sx=source['x']+source['w'] if side=='left' else source['x']
        tx=target['x'] if side=='left' else target['x']+target['w']
        sy=source['y']+38+(sr+.5)*source['rh'];ty=target['y']+38+(tr+.5)*target['rh']
        mid=(sx+tx)/2+lane
        self.edges.append(dict(source=source['id'],sr=sr,target=target['id'],tr=tr,
            points=[(sx,sy),(mid,sy),(mid,ty),(tx,ty)],side=side,dashed=dashed,semantic=semantic))

PAGES=[];COLUMNS=[];FK_ROLES=[]
DIM_PAGE={did:22+i//2 for i,did in enumerate(dims)}
FACT_PAGE={fid:5+i for i,fid in enumerate(facts)}
def coltext(t,c):
    name=c['name'];tags=[]
    if name in t['primary_key']:tags.append('PK')
    if c.get('references'):tags.append('FK')
    if name in t.get('business_key',[]):tags.append('BK')
    if name in HISTORY:tags.append('H')
    if name in AUDIT:tags.append('A')
    if c['aggregation']!='NONE':tags.append(AGG[c['aggregation']])
    if name in t.get('tracked_attributes',[]):tags.append('T')
    tag='/'.join(tags) or 'AT'
    null='!' if not c['nullable'] else 'N!' if c.get('required_for_normal_member') else '?'
    special=' [S]' if c.get('missing_policy') and c['missing_policy']!='Không cho khóa đặc biệt trên dữ liệu công bố.' else ''
    return f'{tag}  {name} : {c["type"]} {null}{special}'

def entity_box(p,tid,x,y,w,font=17,rh=26):
    t=tables[tid];rows=[coltext(t,c) for c in t['columns']]
    b=p.box(tid,x,y,w,tid+'  '+t['name'],rows,'fact' if tid.startswith('F') else 'bridge' if tid.startswith('L') else 'dim',font,rh)
    COLUMNS.extend((tid,c['name']) for c in t['columns']);return b

def compact_dim(p,did,x,y,w=370):
    t=dims[did];hist='SCD TYPE 2 - SK theo phiên bản' if t['history_policy']=='SCD_TYPE2' else 'STATIC - danh mục cố định'
    return p.box(did,x,y,w,did+'  '+t['name'],['PK  '+t['primary_key'][0],hist,f'Đủ thuộc tính và UK: trang {DIM_PAGE[did]:02d}'],'dim',16,29)

def uks(t):return '\n'.join('UK'+str(i+1)+': '+', '.join(u) for i,u in enumerate(t['unique_keys']))

# 01: architecture and reading order.
p=Page('01 - Tong the','CompanyE - Thiết kế luận lý 1.1','Fact constellation cho toàn hệ thống; từng fact có star và grain riêng. Nguồn chuẩn: warehouse_design_v1.json, phiên bản 1.1.')
groups=[('Lưu trú | B01-B03',['F01','F02','F03']),('Ăn uống | B04',['F06','F07','F08']),
 ('Vé và hoạt động | B03, B05',['F04','F09','F10']),('Phương tiện | B03, B05',['F05','F11']),
 ('Mua và nhận hàng | B06',['F12','F13']),('Tồn kho | B07',['F14','F15']),
 ('Bảo trì | B08',['F16']),('Ngữ cảnh | B05',['F17'])]
for i,(title,ff) in enumerate(groups):
    rows=[f'{f} {facts[f]["name"]} - tr. {FACT_PAGE[f]:02d}' for f in ff]
    dd=sorted({c['dimension'] for f in ff for c in facts[f]['columns'] if c.get('dimension')})
    rows+=['Dùng chung: '+', '.join(dd[:6])]
    if len(dd)>6:rows.append('                     '+', '.join(dd[6:]))
    p.box('g'+str(i),70+(i%3)*565,185+(i//3)*255,530,title,rows,'group',17,32)
p.note('counts',1200,720,530,235,'Phạm vi đã chốt','16 dimension; 17 fact/context/aggregate; 2 bridge; 2 validation view.\n631 cột; 102 FK fact-dimension.\nF15 tùy chọn, F17 là ngữ cảnh.',20,PALE)
p.note('read',70,985,1660,150,'Cách đọc tài liệu','Trang 02-04: ký hiệu, lịch sử và chiều dùng chung. Trang 05-21: từng star với đủ cột fact. Trang 22-29: đủ cột dimension. Trang 30-33: bridge/view. Trang 34-35: đối chiếu B01-B08.\nCác hộp dimension lặp trên nhiều trang là cùng một bảng; mã cha trong dimension vẫn là thuộc tính, không tạo snowflake FK.',20,PALE)
PAGES.append(p)

# 02: logical domains, nullability and relationship semantics.
p=Page('02 - Ky hieu','Ký hiệu, miền dữ liệu và lực lượng quan hệ','Các miền bên dưới độc lập hệ quản trị. Ánh xạ kiểu Oracle/Iceberg và cơ chế ràng buộc vật lý được chốt ở bước sau.')
left='PK: khóa chính. FK: tham chiếu PK dimension. BK: định danh nghiệp vụ trong namespace. UK: ràng buộc duy nhất (ghi theo nhóm cột). DD: mã giao dịch. SK: khóa thay thế.\nT: thuộc tính theo dõi thay đổi. H: cột điều khiển lịch sử. A: audit/lineage. AT: thuộc tính còn lại.\n!: NOT NULL. ?: cho NULL. N!: bắt buộc với member_kind=NORMAL; cho NULL ở thành viên đặc biệt.\n[S]: FK có chính sách thành viên đặc biệt. Giá trị 0/-1 vẫn tham chiếu một dòng dimension; FK công bố không trở thành NULL.\nM: SUM. MU: SUM cùng đơn vị. MS: số dư không cộng qua ngày. MSU: kết hợp hai hạn chế. MN: nhiệt độ lấy trung bình theo site/ngày. MT: mưa cộng qua ngày trong cùng site.'
p.note('legend',70,180,810,640,'Thuộc tính và số đo',left,21,PALE)
p.note('card',70,845,810,280,'Quan hệ 1 - 0..N','Mỗi dòng fact/bridge có FK tham chiếu đúng một dòng dimension, gồm cả dòng đặc biệt được phép. Một phiên bản dimension có thể được 0 đến nhiều dòng fact tham chiếu.\nNét liền: FK đã khai báo. Nét đứt: đối chiếu nghiệp vụ có kiểm soát, không phải FK hay đường cộng tiền mặc định.',21,PALE)
p.box('domains',930,180,800,'MIỀN DỮ LIỆU LOGIC',[key+' - '+val for key,val in DOMAIN.items()],'group',19,44)
p.note('namespace',930,870,800,250,'Namespace và dữ liệu thiếu','source_system là thành phần định danh, không phải nhãn trang trí. Hồ sơ khách ở hai nguồn chưa được hợp nhất thành khách duy nhất toàn chuỗi.\nID có giá trị nhưng sai hoặc không tìm được phiên bản phải được cách ly; không thay bằng UNKNOWN để che lỗi. Báo cáo công bố phần hợp lệ kèm nhãn thiếu.',21,PALE)
PAGES.append(p)

# 03: versioned identity example; values are illustrations, never new seed rows.
p=Page('03 - SCD Type 2','Lịch sử dimension - khóa đối tượng và khóa phiên bản','14 dimension dùng SCD Type 2; D01 DimDate và D10 DimMeal STATIC. Ví dụ dưới chỉ minh họa, không phải dữ liệu v2 mới.')
p.box('old',70,190,800,'D03 DimHotel - phiên bản trước',[
 'PK hotel_key = 701', 'BK (source_system, hotel_id) = (hotel_ops, HOTEL_DEMO)',
 'hotel_name = E Demo; stars = 3', 'valid_from_utc = 2022-12-31 17:00:00',
 'valid_to_utc = 2025-05-31 17:00:00', 'is_current = 0; version_no = 1'],'dim',20,39)
p.box('new',930,190,800,'D03 DimHotel - phiên bản sau',[
 'PK hotel_key = 702', 'BK (source_system, hotel_id) = (hotel_ops, HOTEL_DEMO)',
 'hotel_name = E Demo; stars = 5', 'valid_from_utc = 2025-05-31 17:00:00',
 'valid_to_utc = NULL', 'is_current = 1; version_no = 2'],'dim',20,39)
p.note('lookup',70,510,1660,160,'Tra cứu tại thời điểm nghiệp vụ','Nếu t < 2025-05-31 17:00:00 UTC trong khoảng phiên bản cũ, fact giữ hotel_key=701. Từ đúng ranh giới này, dùng hotel_key=702. Điều kiện: valid_from_utc <= t AND (t < valid_to_utc OR valid_to_utc IS NULL).\nKhông thay khóa của toàn bộ giao dịch cũ bằng current. Thời điểm t cụ thể được ghi ở từng trang fact.',21,PALE)
p.note('constraint',70,685,800,435,'Ràng buộc trên dòng NORMAL','BK = namespace + mã nghiệp vụ. BK được lặp ở nhiều phiên bản.\nUK1 = BK + valid_from_utc.\nUK2 = BK + version_no.\nUK có điều kiện = BK khi is_current=1.\nCác khoảng [valid_from, valid_to) không chồng nhau. is_current=1 khi và chỉ khi valid_to_utc=NULL.\nHai dòng 0/-1 không phiên bản hóa.\nversion_no là thứ tự thời gian, không phải khóa bền vững; chèn lịch sử có thể làm đổi thứ tự.',21,PALE)
p.note('bootstrap',930,685,800,435,'Áp dụng cho dữ liệu tự sinh v2','Mỗi BK hiện có một phiên bản khởi tạo, từ 2023-01-01 00:00 giờ Việt Nam, tương đương 2022-12-31 17:00:00 UTC.\neffective_time_basis=BOOTSTRAP_ASSUMPTION ghi rõ đây là giả định mô phỏng.\nHash không đổi thì không tạo phiên bản mới. Replay phải giữ nguyên khóa. Thay đổi đến muộn cần tách khoảng và tra lại các fact bị ảnh hưởng.\nFixture kiểm thử nhiều phiên bản sẽ tách khỏi seed v2. Tài liệu này chưa chứng minh ETL SCD2 đã chạy.',21,PALE)
PAGES.append(p)

# 04: actual shared dimensions, not an implied fact-to-fact aggregation join.
p=Page('04 - Chieu dung chung','Hai fact dùng chung dimension - B06','FactPurchaseLine và FactReceipt có grain riêng; mọi vai trò ngày đều tham chiếu cùng DimDate.')
a=p.box('F12mini',70,220,550,'F12 FactPurchaseLine',[
 'PK fact_key','FK ordered_date_key','FK expected_date_key','FK site_key','FK hotel_key','FK supplier_key','FK item_key',
 'DD purchase_line_id; purchase_order_id','MU ordered_qty; AT unit_price_vnd (không SUM)'],'fact',19,37)
b=p.box('F13mini',1180,220,550,'F13 FactReceipt',[
 'PK fact_key','FK received_date_key','FK expected_date_key','FK expires_date_key [S]','FK site_key','FK hotel_key','FK supplier_key','FK item_key',
 'DD receipt_id; purchase_line_id','MU accepted_qty; rejected_qty; late_accepted_qty'],'fact',19,37)
for i,did in enumerate(['D01','D02','D03','D14','D15']):
    d=dims[did];db=p.box('shared'+did,750,180+i*153,300,did+' '+d['name'],['PK '+d['primary_key'][0]],'dim',18,34)
    ar={'D01':[1,2],'D02':[3],'D03':[4],'D14':[5],'D15':[6]}[did]
    br={'D01':[1,2,3],'D02':[4],'D03':[5],'D14':[6],'D15':[7]}[did]
    for row in ar:p.edge(db,0,a,row,'right',lane=i*8)
    for row in br:p.edge(db,0,b,row,'left',lane=i*8)
p.note('grainleft',70,710,550,235,'Một dòng đặt mua','Tiền/lượng đặt chỉ giữ một lần. Cùng purchase_line_id có thể có nhiều lần nhận.\nPhân loại supplier/item/hotel theo thời điểm đặt.',21,PALE)
p.note('grainright',1180,710,550,235,'Một lần nhận hàng','Phân loại supplier/item/hotel theo thời điểm nhận. Cùng đối tượng có thể mang SK khác nếu đã đổi phiên bản.',21,PALE)
p.note('across',70,990,1660,160,'Drill-across và chống nhân bản','Tổng hợp receipt về (namespace, purchase_line_id), rồi đối chiếu dòng mua; giữ cả dòng đến hạn chưa nhận. B06 dùng phân loại của dòng đặt mua cho cohort. Không nối trực tiếp hai fact chi tiết rồi SUM.\nSK nhận diện phiên bản. Khi đối chiếu xuyên thời gian, dùng mã nghiệp vụ bền vững và grain đã chốt; không coi hai SK của cùng đối tượng là hai nhà cung cấp khác nhau.',21,PALE)
PAGES.append(p)

# 05-21: full fact schemas with compact dimension references.
for fid,t in facts.items():
    reqs=[r['id'] for r in baseline['requirements'] if fid in r['fact_usage']]
    p=Page(fid+' - '+t['name'],fid+' - '+t['name'],', '.join(reqs)+' | '+t['kind']+' | Đầy đủ '+str(len(t['columns']))+' cột; hộp chiều được rút gọn, xem trang tham chiếu.')
    fb=entity_box(p,fid,610,190,580,16,25)
    dd=list(dict.fromkeys(c['dimension'] for c in t['columns'] if c.get('dimension')))
    nleft=math.ceil(len(dd)/2)
    for i,did in enumerate(dd):
        left=i<nleft;ix=i if left else i-nleft
        db=compact_dim(p,did,70 if left else 1360,180+ix*180)
        for row,c in enumerate(t['columns']):
            if c.get('dimension')==did:
                p.edge(db,0,fb,row,'left' if left else 'right',lane=(ix-1.5)*17)
                FK_ROLES.append({'entity':fid,'column':c['name'],'dimension':did,'references':c['references'],'nullable':c['nullable'],'missing_policy':c.get('missing_policy')})
    p.note('grainuk',70,935,800,205,'Grain và khóa duy nhất',t['grain']+'\n'+uks(t),19,PALE)
    p.note('asof',920,935,810,205,'Thời điểm chọn phiên bản dimension',t['dimension_asof'],20,PALE)
    # Keep the common technical columns explicit while clarifying that identifiers
    # such as room_id still participate in the durable natural key.
    p.note('logical',70,855,1660,60,'','PK fact_key là khóa kỹ thuật; UK bảo vệ grain bằng mã nguồn bền vững. Các thuộc tính *_id chưa khai báo FK không phải đường JOIN dimension.',18)
    PAGES.append(p)

# 22-29: all dimension columns, paired but never merged into one schema.
for i in range(0,len(dims),2):
    ids=list(dims)[i:i+2]
    p=Page('Dimensions '+','.join(ids),'Thuộc tính dimension - '+' và '.join(ids),'Mỗi hộp là một bảng logic riêng. N!: bắt buộc ở dòng NORMAL; T: thuộc tính thay đổi tạo phiên bản mới.')
    for j,did in enumerate(ids):
        t=dims[did];x=70+j*860
        entity_box(p,did,x,180,800,18,26)
        if t['history_policy']=='SCD_TYPE2':
            body='BK: '+', '.join(t['business_key'])+'\n'+uks(t)+'\nUK current: BK khi NORMAL và is_current=1.\nKhoảng hiệu lực không chồng; chỉ một current/BK.\nCác UK phiên bản chỉ áp dụng dòng NORMAL; xem trang 03.'
        else:body=uks(t)+'\n'+t['grain']+'\nSTATIC; không thêm khoảng hiệu lực.\nHai thành viên đặc biệt 0/-1 theo member_kind.'
        p.note(did+'keyrules',x,875,800,270,'Lịch sử: '+t['history_policy'],body,19,PALE)
    PAGES.append(p)

# 30-33: complete bridge/view schemas; source refs are not fake SQL foreign keys.
LINK_NOTES={
 'L01':('F01 lọc qua booking_id', 'Dùng EXISTS theo (source_system, booking_id). Một booking có nhiều phòng; không mang tiền booking lên từng dòng bridge. room_key và rate_plan_key chọn phiên bản tại ngày đặt của F01. Không có allocation weight.',
        'booking_id được kiểm chứng ở nguồn cùng batch. Quan hệ này là đối chiếu mã nghiệp vụ, không phải FK fact_key mới.'),
 'L02':('F02 xác định ngày phòng bị chặn', 'Dùng EXISTS hoặc tập DISTINCT (namespace, room_id, date_key). Nhiều công việc cùng chặn một phòng/ngày chỉ làm mất một room-day. room_key chọn phiên bản theo ngày công suất.',
        'maintenance_id truy vết F16. Không SUM chi phí bảo trì sau khi mở rộng qua nhiều ngày; PK dùng room_id bền vững, không dùng room_key phiên bản.'),
 'L03':('F04/F05 liên kết về booking hợp lệ', 'service_type phân biệt TICKET_ORDER và RENTAL. Mỗi dịch vụ có tối đa một booking. Dịch vụ độc lập không có dòng link; ref có giá trị nhưng sai bị cách ly và báo thiếu.',
        'Kiểm chứng ref độc lập với eligibility B03. Cohort tiếp tục lọc booking COMPLETED; tổng hợp dịch vụ về booking trước khi đối chiếu. Đây là view kiểm chứng, không phải fact doanh thu.'),
 'L04':('Hợp nhất mã cụm giữa hai nguồn', 'Namespace trung tâm = entertainment_ops; namespace cụm = hotel_ops. centres.site_code ánh xạ sites.site_id, không đoán theo tên hoặc khoảng cách. Một centre ánh xạ một site; nhiều centre có thể cùng site.',
        'View hiện hành không lưu lịch sử riêng. Khi phân loại giao dịch lịch sử, phải tra thuộc tính site của phiên bản DimCentre đúng thời điểm theo quy tắc R17; không dùng crosswalk current thay lịch sử. Không tạo FK snowflake từ DimCentre sang DimSite.')}
for lid,t in links.items():
    p=Page(lid+' - '+t['name'],lid+' - '+t['name'],t['kind']+' | '+t['grain']+' | Khóa ghép là một nhóm cột, không phải từng cột riêng lẻ.')
    fb=entity_box(p,lid,610,205,690,18,34)
    dd=list(dict.fromkeys(c['dimension'] for c in t['columns'] if c.get('dimension')))
    for i,did in enumerate(dd):
        db=compact_dim(p,did,70,205+i*215)
        for row,c in enumerate(t['columns']):
            if c.get('dimension')==did:
                p.edge(db,0,fb,row,'left',lane=i*20)
                FK_ROLES.append({'entity':lid,'column':c['name'],'dimension':did,'references':c['references'],'nullable':c['nullable'],'missing_policy':c.get('missing_policy')})
    if not dd:
        p.note('nofk',70,205,475,350,'Liên kết kiểm chứng','Không có FK dimension trong hợp đồng này. Các cột định danh dùng để kiểm chứng và ánh xạ nghiệp vụ.\nKhông vẽ thêm quan hệ vật lý chưa được khai báo.',22,PALE)
    title,body,warning=LINK_NOTES[lid]
    p.note('pkuk',70,650,1660,140,'Khóa và tính duy nhất','PK: '+', '.join(t['primary_key'])+'\n'+uks(t),20,PALE)
    p.note('use',70,825,800,300,title,body,22,PALE)
    p.note('guard',930,825,800,300,'Giới hạn đường nối',warning,22,PALE)
    PAGES.append(p)

# 34-35: requirements, unchanged KPI identifiers and relation to conceptual model.
for start in [0,4]:
    p=Page('Coverage '+str(start+1),f'Đối chiếu nhu cầu - B0{start+1} đến B0{start+4}','Truy vết từ mô hình ý niệm đến schema luận lý và hợp đồng KPI; không thêm nhu cầu hay công thức mới.')
    for i,r in enumerate(kpi['requirements'][start:start+4]):
        br=next(x for x in baseline['requirements'] if x['id']==r['id'])
        ff=list(br['fact_usage']);names=', '.join(f+' '+facts[f]['name'] for f in ff)
        body='Facts: '+names+'\nKPI: '+', '.join(m['id'] for m in r['metrics'])
        p.note(r['id'],70,180+i*200,1660,175,r['id']+' - '+r['name'],body,22,PALE)
    p.note('handoff',70,990,1660,160,'Điểm kết thúc của bước luận lý','Đã đối chiếu đủ 37 entity, 631 cột, 102 vai trò FK fact-dimension và 47 KPI. Bước tiếp theo: chọn phiên bản/môi trường Oracle và Spark-Iceberg, ánh xạ kiểu dữ liệu/ràng buộc, rồi viết DDL và ETL.\nBản vẽ chưa tạo bảng, index, partition hay chạy pipeline; nguồn v2, seed và lake giữ nguyên.',20,PALE)
    PAGES.append(p)

def validate_scene():
    expected={(t['id'],c['name']) for t in tables.values() for c in t['columns']}
    assert set(COLUMNS)==expected and len(COLUMNS)==len(expected)==631
    expected_fk={(t['id'],c['name'],c['references']) for t in tables.values() for c in t['columns'] if c.get('references')}
    actual_fk={(f['entity'],f['column'],f['references']) for f in FK_ROLES}
    assert actual_fk==expected_fk and len(FK_ROLES)==len(expected_fk)==106
    assert sum(f['entity'].startswith('F') for f in FK_ROLES)==102
    cf={f['id']:f for f in concept['facts']}
    assert set(cf)==set(facts) and {d['id'] for d in concept['dimensions']}==set(dims)
    for fid,t in facts.items():
        assert {c['dimension'] for c in t['columns'] if c.get('dimension')}=={d['id'] for d in cf[fid]['dimensions']}
    assert concept['metric_mapping']==design['metric_mapping']
    assert len(PAGES)==35
    assert sum(t['history_policy']=='SCD_TYPE2' for t in dims.values())==14
    for p in PAGES:
        ids=[b['id'] for b in p.boxes]+[n['id'] for n in p.notes]
        assert len(ids)==len(set(ids)),p.name
        for b in p.boxes+p.notes:
            assert 50<=b['x'] and b['x']+b['w']<=W-50 and 160<=b['y'] and b['y']+b['h']<=1150,(p.name,b['id'],b['y']+b['h'])
        # Boxes/notes may not overlap, including note margins.
        items=p.boxes+p.notes
        for i,a in enumerate(items):
            for b in items[i+1:]:
                assert not (max(a['x'],b['x'])<min(a['x']+a['w'],b['x']+b['w']) and max(a['y'],b['y'])<min(a['y']+a['h'],b['y']+b['h'])),(p.name,'overlap',a['id'],b['id'])
        byid={b['id']:b for b in p.boxes}
        for e in p.edges:
            for end,row in [('source','sr'),('target','tr')]:assert 0<=e[row]<len(byid[e[end]]['rows'])
    for path,h in HASHES.items():assert digest(path)==h

def render_pdf():
    path=ROOT/'docs/CompanyE_Logical_Model_v1_1.pdf'
    c=canvas.Canvas(str(path),pagesize=(W,H));c.setTitle('CompanyE - Logical Model 1.1');c.setAuthor('CompanyE Project - CO5173')
    for i,p in enumerate(PAGES,1):
        c.bookmarkPage(p.name);c.addOutlineEntry(p.name,p.name,0)
        c.setFillColor(HexColor('#FFFFFF'));c.rect(0,0,W,H,fill=1,stroke=0)
        c.setFillColor(HexColor(BLUE));c.rect(0,0,27,H,fill=1,stroke=0)
        c.setFont('Arial',39);c.drawString(70,H-70,p.title)
        c.setStrokeColor(HexColor(BLUE));c.line(50,H-95,1750,H-95)
        c.setFillColor(HexColor(MUTED));c.setFont('Arial',18)
        for j,line in enumerate(wrap(p.subtitle,1660,18)):c.drawString(70,H-128-j*23,line)
        for e in p.edges:
            c.setStrokeColor(HexColor(TEAL));c.setLineWidth(1.5)
            c.setDash(6,4) if e['dashed'] else c.setDash()
            for a,b in zip(e['points'],e['points'][1:]):c.line(a[0],H-a[1],b[0],H-b[1])
            sx,sy=e['points'][0];tx,ty=e['points'][-1];direction=1 if e['side']=='left' else -1
            for off in [9,14]:c.line(sx+direction*off,H-sy-6,sx+direction*off,H-sy+6)
            for dy in [-7,0,7]:c.line(tx-direction*13,H-ty,tx,H-ty+dy)
            c.circle(tx-direction*22,H-ty,3.5,stroke=1,fill=0);c.setDash()
        for b in p.boxes:
            x,y,w,h=b['x'],b['y'],b['w'],b['h'];fill='#D9E7FA' if b['kind']=='fact' else '#E6F3F1' if b['kind']=='bridge' else '#F1F4F9'
            c.setStrokeColor(HexColor(INK));c.setFillColor(HexColor('#FFFFFF'));c.setLineWidth(1)
            c.rect(x,H-y-h,w,h,fill=1,stroke=1)
            c.setFillColor(HexColor(fill));c.rect(x,H-y-38,w,38,fill=1,stroke=0)
            c.setFillColor(HexColor(INK));c.setFont('Arial-Bold',b['font']+1);c.drawString(x+12,H-y-26,b['title'])
            for j,row in enumerate(b['rows']):
                yy=y+38+j*b['rh'];c.setLineWidth(.35);c.line(x,H-yy,x+w,H-yy)
                c.setFont('Arial',b['font']);c.drawString(x+12,H-yy-b['rh']*.72,row)
        for n in p.notes:
            x,y,w,h=n['x'],n['y'],n['w'],n['h'];size=n['size']
            c.setFillColor(HexColor(n['fill']));c.rect(x,H-y-h,w,h,fill=1,stroke=0)
            c.setFillColor(HexColor(INK));yy=y+16
            for bold,content in [(True,n['title']),(False,n['body'])]:
                if not content:continue
                c.setFont('Arial-Bold' if bold else 'Arial',size)
                for line in wrap(content,w-32,size,bold):c.drawString(x+16,H-yy-size,line);yy+=size*1.3
                if bold:yy+=12
        c.setFillColor(HexColor(MUTED));c.setFont('Arial',13)
        c.drawString(70,65,'CompanyE | Logical 1.1 | PK/FK/BK/UK; ! / ? / N!; [S]: khóa thành viên đặc biệt. Chú giải trang 02. SCD2: trang 03.')
        c.drawString(70,40,'Theo cách trình bày bảng/quan hệ trong CO5173 Chương 2, slide 54-55, 59. Nguồn: design 1.1 và mô hình ý niệm 1.0 | 13/10/2026.')
        c.drawRightString(1730,40,f'{i:02d} / {len(PAGES):02d}');c.showPage()
    c.save();return path

def render_drawio():
    root=ET.Element('mxfile',host='app.diagrams.net',type='device',version='24.7.17',pages=str(len(PAGES)))
    for pi,p in enumerate(PAGES,1):
        diag=ET.SubElement(root,'diagram',id='logical11-'+str(pi),name=p.name)
        g=ET.SubElement(diag,'mxGraphModel',page='1',pageWidth=str(W),pageHeight=str(H),grid='1');cells=ET.SubElement(g,'root')
        ET.SubElement(cells,'mxCell',id='0');ET.SubElement(cells,'mxCell',id='1',parent='0')
        def cell(uid,value,x,y,w,h,style,parent='1'):
            e=ET.SubElement(cells,'mxCell',id=uid,value=value,style=style,vertex='1',parent=parent)
            ET.SubElement(e,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),attrib={'as':'geometry'})
        cell('stripe','',0,0,27,H,f'fillColor={BLUE};strokeColor=none;')
        cell('title',html.escape(p.title),70,20,1660,65,f'text;html=1;fontFamily=Arial;fontSize=39;fontColor={BLUE};align=left;')
        cell('subtitle',html.escape(p.subtitle),70,105,1660,50,'text;html=1;whiteSpace=wrap;fontFamily=Arial;fontSize=18;align=left;')
        for b in p.boxes:
            cell(b['id'],'',b['x'],b['y'],b['w'],b['h'],'group;')
            fill='#D9E7FA' if b['kind']=='fact' else '#E6F3F1' if b['kind']=='bridge' else '#F1F4F9'
            base=f'html=1;rounded=0;strokeColor={INK};fontFamily=Arial;align=left;spacingLeft=12;'
            cell(b['id']+'title',html.escape(b['title']),0,0,b['w'],38,base+f'fontStyle=1;fontSize={b["font"]+1};fillColor={fill};',b['id'])
            for j,row in enumerate(b['rows']):cell(b['id']+'r'+str(j),html.escape(row),0,38+j*b['rh'],b['w'],b['rh'],base+f'fontSize={b["font"]};fillColor=#FFFFFF;',b['id'])
        for i,e in enumerate(p.edges):
            left=e['side']=='left'
            style=f'edgeStyle=segmentEdgeStyle;rounded=0;strokeColor={TEAL};startArrow=ERmandOne;endArrow=ERzeroToMany;startFill=0;endFill=0;exitX={int(left)};exitY=0.5;entryX={int(not left)};entryY=0.5;'
            edge=ET.SubElement(cells,'mxCell',id='edge'+str(i),edge='1',parent='1',source=e['source']+'r'+str(e['sr']),target=e['target']+'r'+str(e['tr']),style=style)
            geo=ET.SubElement(edge,'mxGeometry',relative='1',attrib={'as':'geometry'});arr=ET.SubElement(geo,'Array',attrib={'as':'points'})
            for x,y in e['points'][1:-1]:ET.SubElement(arr,'mxPoint',x=str(x),y=str(y))
        for n in p.notes:
            value=('<b>'+html.escape(n['title'])+'</b><br><br>' if n['title'] else '')+html.escape(n['body']).replace('\n','<br>')
            cell(n['id'],value,n['x'],n['y'],n['w'],n['h'],f'html=1;whiteSpace=wrap;align=left;verticalAlign=top;spacing=16;fontFamily=Arial;fontSize={n["size"]};fillColor={n["fill"]};strokeColor=none;')
        cell('footer',f'CompanyE | Logical 1.1 | Chú giải trang 02; SCD2 trang 03 | {pi:02d}/{len(PAGES):02d}',70,1170,1660,40,'text;html=1;fontFamily=Arial;fontSize=15;align=left;')
    path=ROOT/'docs/CompanyE_Logical_Model_v1_1.drawio';ET.indent(root);ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True);return path

if __name__=='__main__':
    validate_scene();pdf=render_pdf();drawio=render_drawio()
    reader=PdfReader(pdf);assert len(reader.pages)==len(PAGES)
    for tid,t in tables.items():
        page=FACT_PAGE[tid] if tid.startswith('F') else DIM_PAGE[tid] if tid.startswith('D') else 30+list(links).index(tid)
        text=reader.pages[page-1].extract_text()
        assert t['name'] in text
        for c in t['columns']:assert c['name'] in text,(tid,c['name'])
    alltext='\n'.join(p.extract_text() for p in reader.pages)
    for r in kpi['requirements']:
        for m in r['metrics']:assert m['id'] in alltext
    xml=ET.parse(drawio)
    for diag in xml.findall('diagram'):
        cells=diag.findall('.//mxCell');ids=[c.get('id') for c in cells];assert len(ids)==len(set(ids))
        for c in cells:
            for key in ['parent','source','target']:
                if c.get(key):assert c.get(key) in ids
    logical=dict(version='companye-logical-model-1.1',created_on='2026-10-13',status='LOGICAL_DESIGN_NOT_IMPLEMENTED',
      authority=INPUTS[0],conceptual_model=INPUTS[1],input_sha256=HASHES,
      types=DOMAIN,tables=[{k:v for k,v in t.items() if k!='physical_name'} for t in tables.values()],
      foreign_key_roles=FK_ROLES,metric_mapping=design['metric_mapping'],
      diagram_pages=[dict(page=i,name=p.name,title=p.title) for i,p in enumerate(PAGES,1)])
    save('config/logical_model_v1_1.json',logical)
    outputs=['docs/CompanyE_Logical_Model_v1_1.pdf','docs/CompanyE_Logical_Model_v1_1.drawio','config/logical_model_v1_1.json']
    report=dict(status='PASSED_STRUCTURAL_CHECKS',visual_review='PENDING',pages=len(PAGES),entities=37,columns=631,
      dimensions=16,scd2_dimensions=14,static_dimensions=2,facts=17,bridges=2,validation_views=2,
      fact_dimension_pairs=len({(f['entity'],f['dimension']) for f in FK_ROLES if f['entity'].startswith('F')}),
      fact_dimension_foreign_keys=102,bridge_dimension_foreign_keys=4,kpis=47,
      input_sha256=HASHES,output_sha256={p:digest(p) for p in outputs},
      checks=['Exact column coverage against design 1.1','Exact FK coverage and PK targets',
              'Conceptual dimension associations and KPI mapping unchanged','SCD2/static counts',
              'Box bounds and nonoverlap; text widths/heights','PDF page/column/KPI readback',
              'draw.io unique IDs and valid editable endpoints','Input checksums unchanged'],
      limitations=['Native draw.io XML checked; not tested in draw.io UI.','Documentation only; DDL and ETL have not been implemented.'])
    for t in tables.values():
        names={c['name'] for c in t['columns']}
        for u in [t['primary_key']]+t['unique_keys']:assert set(u)<=names
        for c in t['columns']:
            if c.get('references'):
                did,key=c['references'].split('.');assert key in tables[did]['primary_key']
    for path,h in HASHES.items():assert digest(path)==h
    save('reports/logical_model_v1_1_validation.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ['input_sha256','output_sha256']},ensure_ascii=False,indent=2))
