"""Read-only schema audit; create CompanyE's three-part ERD as draw.io and PDF."""
import collections, hashlib, heapq, html, json, math, re
import xml.etree.ElementTree as ET
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs'
W,H=2200,1400
for name,file in [('Arial','arial.ttf'),('Arial-Bold','arialbd.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(Path('C:/Windows/Fonts')/file)))
inputs=[ROOT/'generated/v2'/db/'schema.sql' for db in ['hotel_ops','entertainment_ops']]
inputs += [ROOT/'generated/v2/contracts.json',ROOT/'lake/v2/catalog/catalog.json',ROOT/'src/lake_v2.py',ROOT/'config/dimensional_model_v1.json']
hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
contract=json.loads((ROOT/'generated/v2/contracts.json').read_text(encoding='utf-8'))
tables={}; fks=[]
for db in ['hotel_ops','entertainment_ops']:
    sql=(ROOT/'generated/v2'/db/'schema.sql').read_text(encoding='utf-8')
    for t in contract[db]:
        name=t['name']; key=db+'.'+name
        block=re.search(r'CREATE TABLE "'+name+r'" \((.*?)\n\);',sql,re.S).group(1)
        sqlcols=re.findall(r'^\s+"([^"]+)"',block,re.M)
        assert sqlcols==[c['name'] for c in t['columns']],key
        t={**t,'db':db,'key':key,'unique':re.findall(r'ALTER TABLE '+name+r' ADD UNIQUE\(([^)]+)\)',sql)}
        tables[key]=t
        for ci,c in enumerate(t['columns']):
            sql_line=next(line.strip().rstrip(',') for line in block.splitlines() if line.strip().startswith('"'+c['name']+'"'))
            assert c['sql_type'] in sql_line and c['constraints'] in sql_line,(key,c['name'])
            assert c['nullable']==('NOT NULL' not in sql_line and 'PRIMARY KEY' not in sql_line),(key,c['name'])
            ref=re.search(r'REFERENCES (\w+)\((\w+)\)',c['constraints'])
            if ref:fks.append(dict(parent=db+'.'+ref[1],pk=ref[2],child=key,fk=c['name'],nullable=c['nullable']))
assert len(tables)==41

def wrap(s,width,size=16,bold=False):
    font='Arial-Bold' if bold else 'Arial'; result=[]
    for para in str(s).split('\n'):
        line=''
        for word in para.split():
            trial=(line+' '+word).strip()
            if line and pdfmetrics.stringWidth(trial,font,size)>width:result.append(line);line=word
            else:line=trial
        result.append(line)
    return result

class Page:
    def __init__(self,name,title,subtitle,notes=''):
        self.name=name;self.title=title;self.subtitle=subtitle;self.notes=notes
        self.nodes=[];self.edges=[];self.texts=[]
    def text(self,x,y,w,s,size=18,bold=False,color='#222222'):
        lines=wrap(s,w,size,bold)
        self.texts.append(dict(x=x,y=y,w=w,h=len(lines)*size*1.25,text='\n'.join(lines),size=size,bold=bold,color=color))
    def box(self,id,x,y,w,title,rows,kind='table',size=15):
        cooked=[]
        for r in rows:
            lines=wrap(r,w-24,size);cooked.append(dict(text='\n'.join(lines),h=max(29,len(lines)*size*1.22+9)))
        title_lines=wrap(title,w-20,17,True);th=max(42,len(title_lines)*22+10)
        n=dict(id=id,x=x,y=y,w=w,h=th+sum(r['h'] for r in cooked),title='\n'.join(title_lines),rows=cooked,kind=kind,size=size,th=th)
        self.nodes.append(n);return n
    def entity(self,id,x,y,w,name):
        n=dict(id=id,x=x,y=y,w=w,h=76,title=name,rows=[],kind='entity',size=21,th=76)
        self.nodes.append(n);return n
    def edge(self,a,ar,b,br,kind='fk',optional=False,label=''):
        self.edges.append(dict(a=a['id'],ar=ar,b=b['id'],br=br,kind=kind,optional=optional,label=label,points=[]))

pages=[]

# I. Chen-style conceptual views: entities and relationship diamonds.
def conceptual(name,title,entities,relations,notes):
    p=Page(name,title,'PHẦN I | Mô hình nghiệp vụ khái niệm; hình chữ nhật = thực thể, hình thoi = quan hệ. Thuộc tính xem phần II.',notes)
    ns={k:p.entity(k,x,y,w,label) for k,x,y,w,label in entities}
    for index,(a,b,label,card_a,card_b) in enumerate(relations):
        na,nb=ns[a],ns[b]; sx=na['x']+na['w'];sy=na['y']+38;tx=nb['x'];ty=nb['y']+38
        # A relationship has its own editable node and two incidence lines.
        dx=(sx+tx)/2;dy=ty
        diamond_w=min(170,max(110,tx-sx-80))
        d=dict(id='rel'+str(index),x=dx-diamond_w/2,y=dy-38,w=diamond_w,h=76,title=label,rows=[],kind='diamond',size=17,th=76)
        p.nodes.append(d)
        lane=sx+45+(35 if a=='guest' and b=='member' else 0)
        p.edges.append(dict(a=a,ar=-1,b=d['id'],br=-1,kind='concept',optional=False,label='',points=[(sx,sy),(lane,sy),(lane,dy),(dx-diamond_w/2,dy)],cards=[(sx+15,sy-15,card_a)]))
        if a=='guest' and b=='member':
            p.edges[-1].update(points=[(na['x'],sy),(55,sy),(55,dy),(dx-diamond_w/2,dy)],cards=[(60,sy-15,card_a)],source_left=True)
        p.edges.append(dict(a=d['id'],ar=-1,b=b,br=-1,kind='concept',optional=False,label='',points=[(dx+diamond_w/2,dy),(tx,ty)],cards=[(tx-38,ty-15,card_b)]))
    pages.append(p)

conceptual('I.1 Co so va dich vu','CompanyE - Cơ sở và danh mục dịch vụ',[
 ('e',100,550,260,'CompanyE'),('site',610,550,300,'Cụm du lịch'),
 ('hotel',1160,300,300,'Khách sạn'),('centre',1160,830,300,'Trung tâm giải trí'),
 ('room',1780,190,300,'Phòng'),('outlet',1780,450,300,'Điểm ăn uống'),
 ('activity',1780,740,300,'Hoạt động giải trí'),('vehicle',1780,1000,300,'Phương tiện')],
 [('e','site','quản lý','1','4'),('site','hotel','có','1','2'),('site','centre','có','1','1'),
  ('hotel','room','gồm','1','N'),('hotel','outlet','vận hành','1','N'),('centre','activity','tổ chức','1','N'),('centre','vehicle','quản lý','1','N')],
 'Giả định case: Sa Pa, Đà Nẵng, Đà Lạt, Phú Quốc; mỗi cụm có một trung tâm và hai khách sạn (3 sao, 5 sao). Số lượng 4/2/1 là quy mô case, không phải ràng buộc UNIQUE/FK trong DDL. Điểm ăn uống bao gồm nhà hàng và bar; không giả định mỗi khách sạn chỉ có một outlet.')

conceptual('I.2 Khach va giao dich','CompanyE - Khách và giao dịch dịch vụ',[
 ('guest',90,210,310,'Hồ sơ khách khách sạn'),('booking',730,210,310,'Booking'),('br',1400,210,310,'Phòng trong booking'),
 ('stay',1900,210,230,'Lưu trú'),
 ('cust',90,520,310,'Hồ sơ khách giải trí'),('order',730,520,310,'Đơn vé'),('ticket',1400,520,310,'Vé'),('admission',1900,520,230,'Lượt vào'),
 ('rent',730,820,310,'Hợp đồng thuê xe'),('vehicle',1400,820,310,'Phương tiện'),
 ('member',730,1060,310,'Đăng ký hội viên'),('card',1400,1060,310,'Thẻ hội viên')],
 [('guest','booking','đặt','1','N'),('booking','br','gồm','1','N'),('br','stay','phát sinh','1','N'),
  ('cust','order','mua','1','N'),('order','ticket','gồm','1','N'),('ticket','admission','ghi nhận','1','N'),
  ('cust','rent','thuê','1','N'),('rent','vehicle','dùng xe','N','1'),
  ('guest','member','đăng ký','1','N'),('member','card','cấp thẻ','1','N')],
 'Hồ sơ khách khách sạn và hồ sơ khách giải trí chưa được hợp nhất thành một người. N biểu thị khả năng nhiều; minimum participation và NULL xem DDL phần II. Không giả định stays hoặc admissions là 1:1: hiện không có UNIQUE trên khóa tham chiếu tương ứng. Quan hệ hội viên/phòng/ăn sáng được chi tiết hóa ở phần II.')

conceptual('I.3 Cung ung va van hanh','CompanyE - Cung ứng, ăn uống và bảo trì',[
 ('supplier',90,210,300,'Nhà cung cấp'),('po',680,210,300,'Đơn mua hàng'),('line',1260,210,300,'Dòng mua hàng'),('receipt',1850,210,300,'Lần nhận / lô hàng'),
 ('hotel',90,590,300,'Khách sạn'),('outlet',680,590,300,'Điểm ăn uống'),('dining',1260,590,300,'Hóa đơn ăn uống'),
 ('session',1260,850,300,'Phiên buffet'),('movement',1850,850,300,'Biến động kho'),
 ('asset',680,1080,300,'Tài sản khách sạn'),('work',1260,1080,300,'Công việc bảo trì')],
 [('supplier','po','nhận đơn','1','N'),('po','line','gồm','1','N'),('line','receipt','nhận hàng','1','N'),
  ('hotel','outlet','vận hành','1','N'),('outlet','dining','phục vụ','1','N'),('outlet','session','tổ chức','1','N'),
  ('session','movement','dùng hàng','0..1','N'),('hotel','asset','sở hữu','1','N'),('asset','work','bảo trì','1','N')],
 'Một dòng mua có thể nhận nhiều đợt; mỗi movement tham chiếu một lô receipt (quan hệ chi tiết ở II.8). session chỉ liên quan khi movement phục vụ một phiên buffet. Nhà cung cấp bán tài sản không mặc định là đơn vị thực hiện bảo trì. Hóa đơn ăn uống không có grain dòng món trong nguồn hiện tại.')

# II. Split only for readability; every table has one full definition, with small
# PK-only copies for out-of-page parents. Every declared FK is drawn exactly once.
groups=[
 ('hotel_ops','II.1 Co so','Cơ sở, phòng và thời tiết',['sites','hotels','rooms','weather_daily']),
 ('hotel_ops','II.2 Dat phong','Kênh bán, khách, khuyến mãi và booking',['channels','guests','promotions','rate_plans','bookings']),
 ('hotel_ops','II.3 Luu tru','Phòng đặt, lưu trú và quyền lợi sáng',['booking_rooms','stays','breakfast_entitlements']),
 ('hotel_ops','II.4 An uong','Nhà hàng, bar và phiên buffet',['outlets','dining_orders','meal_sessions']),
 ('hotel_ops','II.5 Hoi vien','Gói hội viên, đăng ký và thẻ',['membership_plans','memberships','member_cards']),
 ('hotel_ops','II.6 Tien va revision','Thanh toán, đối soát và lịch sử sửa booking',['payments','settlements','booking_revisions','booking_room_revisions']),
 ('hotel_ops','II.7 Mua hang','Nhà cung cấp, đặt mua và nhận hàng',['suppliers','items','purchase_orders','purchase_lines','receipts']),
 ('hotel_ops','II.8 Kho','Biến động kho và tham chiếu lô',['stock_movements']),
 ('hotel_ops','II.9 Bao tri','Tài sản và bảo trì khách sạn',['assets','maintenance']),
 ('entertainment_ops','II.10 Danh muc','Trung tâm, hoạt động, xe và lịch ngừng phục vụ',['centres','activities','closures','vehicles','vehicle_maintenance']),
 ('entertainment_ops','II.11 Ve','Hồ sơ khách, đơn vé, vé và lượt vào',['customers','ticket_orders','tickets','admissions']),
 ('entertainment_ops','II.12 Thue xe','Thuê xe và thu/hoàn tiền',['rentals','cash_events']),
]
notes={
 'II.1 Co so':'website_channel là TEXT, không có REFERENCES trong DDL. Thời tiết gắn với cụm; PK weather_id chưa bảo đảm UNIQUE(site_id, weather_date). Tính duy nhất theo grain cần kiểm tra chất lượng.',
 'II.2 Dat phong':'promotion_id của booking có thể NULL. Khuyến mãi có thể không giới hạn channel/site. Các FK độc lập không tự bảo đảm phòng, gói giá và booking cùng khách sạn: cần kiểm tra chéo khi ETL.',
 'II.3 Luu tru':'Không có UNIQUE(booking_room_id) trên stays hoặc UNIQUE(booking_room_id, service_date) trên breakfast_entitlements. Grain mong muốn và chống overlap là quy tắc kiểm thử, không phải ràng buộc được DDL bảo đảm.',
 'II.4 An uong':'guest_id và booking_id của dining_orders có thể NULL. Không có FK từ breakfast_entitlements tới outlet: ánh xạ nhà hàng phải được kiểm tra trong ETL. Không có bảng món ăn hoặc dòng hóa đơn.',
 'II.5 Hoi vien':'member_cards có FK riêng tới membership và guest; DDL không tự bảo đảm guest trên thẻ trùng guest của membership. Một khách có thể có nhiều đăng ký/thẻ. Hiệu lực valid_from/valid_to cần kiểm tra theo thời điểm.',
 'II.6 Tien va revision':'UQ đã khai báo: booking_revisions(booking_id, revision_no); booking_room_revisions(revision_id, booking_room_id). settlements.booking_id không UNIQUE: không mặc định một booking chỉ có một settlement.',
 'II.7 Mua hang':'receipts là từng lần nhận của một dòng mua. accepted_qty và rejected_qty >= 0; expires_on có thể NULL. Lượng đặt mua không được nhân lên theo số lần nhận; chỉ accepted_qty được nhập kho.',
 'II.8 Kho':'movement_type thuộc IN/USE/WASTE, quantity >= 0; session_id có thể NULL. FK độc lập không bảo đảm hotel/item/session khớp lô nhận: phải đối chiếu chuỗi receipt -> purchase_line -> purchase_order. Chưa có warehouse_id riêng.',
 'II.9 Bao tri':'assets.room_id có thể NULL với tài sản chung. assets.supplier_id chỉ là bên bán tài sản. DDL kiểm tra ends_on > starts_on; overlap và tác động ngày phòng cần logic riêng.',
 'II.10 Danh muc':'centres.site_code là TEXT NOT NULL, không có FK tới database khách sạn. Lịch closure/bảo trì có thể nhiều dòng trùng ngày; hợp ngày trước khi tính công suất. Không có bảng nhà thầu bảo trì xe.',
 'II.11 Ve':'member_card_ref và hotel_booking_ref là tham chiếu liên hệ thống, không có REFERENCES. tickets.ticket_order_id và admissions.ticket_id không UNIQUE; không suy lượt vào từ status hoặc ngày hiệu lực vé.',
 'II.12 Thue xe':'CHECK XOR trên cash_events: đúng một trong ticket_order_id và rental_id có giá trị. FK không bảo đảm thuê xe không chồng lấn hoặc không trùng bảo trì; cần kiểm tra riêng.',
}
full_seen=[];edges_seen=[]
for db,name,title,local in groups:
    full={db+'.'+t for t in local}; local_edges=[e for e in fks if e['child'] in full]
    ids=full | {e['parent'] for e in local_edges}
    # Rank by declared FK dependency (no schema cycles in this source snapshot).
    rank={key:0 for key in ids}
    for _ in range(len(ids)):
        changed=False
        for e in local_edges:
            if rank[e['child']]<=rank[e['parent']]:rank[e['child']]=rank[e['parent']]+1;changed=True
        if not changed:break
    assert max(rank.values())<len(ids)
    ncol=max(rank.values())+1
    if ncol==1:ncol=2
    width=min(540,(2040-120*(ncol-1))/ncol)
    spacing=(2040-width*ncol)/max(1,ncol-1)
    p=Page(name,'CompanyE - '+title,'PHẦN II | '+db+' | DDL v2: đủ cột, kiểu dữ liệu, PK, FK và NULL. REF = bảng lặp rút gọn ở trang khác.',notes[name])
    nd={};colnames={}
    for lev in range(ncol):
        keys=sorted([k for k in ids if rank[k]==lev],key=lambda k:(k not in full,local.index(k.split('.')[1]) if k in full else k))
        for key in keys:
            t=tables[key];cols=t['columns'] if key in full else [c for c in t['columns'] if 'PRIMARY KEY' in c['constraints']]
            rows=[];rowmap={}
            for c in cols:
                flag='PK' if 'PRIMARY KEY' in c['constraints'] else 'FK' if 'REFERENCES' in c['constraints'] else '  '
                rows.append(f"{flag}  {c['name']} : {c['sql_type']} [{'NULL' if c['nullable'] else 'NN'}]")
                rowmap[c['name']]=len(rows)-1
            if key in full:
                rows+=['UQ  '+u for u in t['unique']];full_seen.append(key)
            n=p.box(key,80+lev*(width+spacing),0,width,t['name']+(' [REF]' if key not in full else ''),rows,'table' if key in full else 'ref',15)
            nd[key]=n;colnames[key]=rowmap
        boxes=[nd[k] for k in keys]
        total=sum(n['h'] for n in boxes);gap=55
        assert total+gap*max(0,len(boxes)-1)<1000,(name,total,len(boxes))
        y=200+(980-total-gap*max(0,len(boxes)-1))/2
        for n in boxes:n['y']=y;y+=n['h']+gap
    for e in local_edges:
        p.edge(nd[e['parent']],colnames[e['parent']][e['pk']],nd[e['child']],colnames[e['child']][e['fk']],optional=e['nullable'])
        edges_seen.append((e['child'],e['fk'],e['parent'],e['pk']))
    pages.append(p)

# III. Operational references across DB boundaries are intentionally dashed.
cross=Page('III.1 Lien DB','CompanyE - Liên kết giữa hai database','PHẦN III | Nét đứt: tham chiếu do ETL kiểm tra, không phải FK do PostgreSQL bảo đảm.',
 'booking_ref NULL = bán độc lập; ref có giá trị nhưng sai = lỗi cần quarantine, không đổi thành bán độc lập. guest_id và customer_id luôn có namespace. member_card_ref chỉ là bằng chứng liên kết khi đã xác minh, chưa tạo Golden Customer; không dùng audit_only/identity truth để nối dữ liệu khai thác.')
s=cross.box('sites',100,210,600,'hotel_ops.sites',['PK site_id','SP / DN / DL / PQ'],'table',19)
c=cross.box('centres',1440,210,650,'entertainment_ops.centres',['PK centre_id','site_code [NN] - mã cụm cần đối chiếu'],'table',19)
b=cross.box('booking',100,530,600,'hotel_ops.bookings',['PK booking_id','hotel_id, guest_id, channel_id'],'table',19)
t=cross.box('ticket',1440,460,650,'entertainment_ops.ticket_orders',['PK ticket_order_id','hotel_booking_ref [NULL]'],'table',19)
r=cross.box('rental',1440,650,650,'entertainment_ops.rentals',['PK rental_id','hotel_booking_ref [NULL]'],'table',19)
ca=cross.box('cards',100,930,600,'hotel_ops.member_cards',['PK card_id','guest_id, membership_id'],'table',19)
cu=cross.box('customers',1440,930,650,'entertainment_ops.customers',['PK customer_id','member_card_ref [NULL]'],'table',19)
for a,ar,z,zr,nullable in [(s,0,c,1,False),(b,0,t,1,True),(b,0,r,1,True),(ca,0,cu,1,True)]:cross.edge(a,ar,z,zr,'external',nullable)
cross.text(765,200,580,'Cụm: site_code = site_id. Mỗi centre phải tìm thấy đúng một site; không suy theo tên.',19)
cross.text(765,465,580,'Bán chéo: kiểm tra tồn tại booking; giữ cơ sở phục vụ và cơ sở đặt phòng riêng. Tổng dịch vụ về booking trước khi ghép KPI.',19)
cross.text(765,890,580,'Hội viên: kiểm tra card, guest và membership nhất quán; khi phân tích quyền lợi phải xét valid_from/valid_to và chính sách thẻ.',19)
pages.append(cross)

lake=Page('III.2 Feed va lake','CompanyE - Nhà cung cấp và data lake','PHẦN III | Đây là luồng tích hợp/đối chiếu. Mũi tên chỉ luồng dữ liệu; không biểu thị cardinality ER.',
 'Nguồn v2 đang xét là feed receipt có version/replay; CSV còn g/kg, thời gian nguồn và thời gian nhận khác nhau. File supplier_mixed, TEXT/SVG chưa chuẩn hóa của v1 thuộc batch/cấu trúc v1 riêng, không gán nhầm vào catalog v2. Phiếu nhận trong DB là nguồn nghiệp vụ cho B06-B07; feed ngoài không tạo thêm lượng nhận.')
raw=lake.box('raw',80,210,600,'RAW - giữ nguyên file và nguồn gốc',[
 'receipts_*.csv, replay_*.csv', 'delivery_schedule.json: delivery_id, received_at',
 'event_id, receipt_ref, revision', 'purchase_line_ref, supplier_id, hotel_id',
 'accepted_qty + unit (kg/g), unit_price_vnd', 'occurred_at, source_recorded_at, _source_path'], 'table',18)
proc=lake.box('normalize',800,210,600,'Chuẩn hóa và phân loại - lake_v2.py',[
 'Kiểm tra event_id + payload hash', 'Trùng event, cùng payload -> receipt_replays',
 'Cast kiểu, g -> kg, kiểm tra thời gian/giá/lượng', 'Không hợp lệ -> receipt_quarantine',
 'Hợp lệ -> receipt_versions', 'receipt_latest: revision lớn nhất mỗi receipt_ref'], 'process',18)
outputs=lake.box('output',1530,210,590,'Catalog: companye_v2_external',[
 'receipt_versions: các phiên bản hợp lệ', 'receipt_latest: một dòng / receipt_ref',
 'receipt_replays: lần giao lặp', 'receipt_quarantine: lỗi + lý do'], 'table',18)
db=lake.box('receipt_db',1530,810,590,'Đối chiếu hotel_ops',[
 'receipt_ref = receipts.receipt_id', 'purchase_line_ref = purchase_lines.purchase_line_id',
 'supplier_id, hotel_id = purchase_orders', 'accepted_qty_kg = receipts.accepted_qty',
 'unit_price_vnd = purchase_lines.unit_price_vnd'], 'table',17)
meta=lake.box('metadata',80,810,600,'Catalog và metadata theo batch',[
 'catalog.json: dataset, owner, grain, schema', 'raw/standardized path, row_count, sha256',
 'derived_datasets + upstream_datasets', 'Parquet: _ingestion_batch, _source_system',
 'Metadata tables: datasets / columns / artifacts'], 'process',18)
warn=lake.box('rules',800,810,600,'Quy tắc bảo toàn nghiệp vụ',[
 'Không UNION ALL feed với receipts để tính KPI', 'Không chọn latest theo thứ tự file đến',
 'Cùng event_id, khác payload: dừng vì xung đột', 'Nhiều identity cùng receipt/revision: báo lỗi'], 'process',18)
lake.edge(raw,2,proc,0,'flow');lake.edge(proc,4,outputs,0,'flow')
lake.edge(outputs,1,db,0,'reconcile');lake.edge(meta,0,raw,0,'metadata')
lake.text(800,590,600,'Tách ba mốc thời gian: nghiệp vụ xảy ra, nguồn ghi nhận và hệ thống nhận file. Giữ phiên bản và replay để tái lập, kiểm thử ETL.',19)
pages.append(lake)

assert len(full_seen)==len(set(full_seen))==len(tables)
assert set(edges_seen)=={(e['child'],e['fk'],e['parent'],e['pk']) for e in fks}

# Route FK edges on an orthogonal grid, avoiding every table's bounding box.
def row_y(n,r):
    return n['y']+n['th']+sum(x['h'] for x in n['rows'][:r])+n['rows'][r]['h']/2 if r>=0 else n['y']+n['h']/2
def route(page):
    nodes={n['id']:n for n in page.nodes};step=10
    blocked=set();used=collections.Counter()
    for n in page.nodes:
        for gx in range(math.floor((n['x']-18)/step),math.ceil((n['x']+n['w']+18)/step)+1):
            for gy in range(math.floor((n['y']-15)/step),math.ceil((n['y']+n['h']+15)/step)+1):blocked.add((gx,gy))
    for e in page.edges:
        if e['points']:continue
        a,b=nodes[e['a']],nodes[e['b']];sy=row_y(a,e['ar']);ty=row_y(b,e['br'])
        # Edges normally leave right and enter left. Same-column flows use right.
        same=abs(a['x']-b['x'])<10
        sx=a['x']+a['w'];tx=b['x']+b['w'] if same else b['x']
        start=(math.ceil((sx+20)/step),round(sy/step));end=(math.ceil((tx+20)/step) if same else math.floor((tx-20)/step),round(ty/step))
        while start in blocked:start=(start[0]+1,start[1])
        while end in blocked:end=(end[0]+(1 if same else -1),end[1])
        assert start not in blocked and end not in blocked,(page.name,e)
        heap=[(0,0,start[0],start[1],-1)];best={(start[0],start[1],-1):0};prev={};found=None
        while heap:
            _,cost,x,y,d=heapq.heappop(heap);state=(x,y,d)
            if cost!=best.get(state):continue
            if (x,y)==end:found=state;break
            for nd,(dx,dy) in enumerate([(1,0),(0,1),(-1,0),(0,-1)]):
                nx,ny=x+dx,y+dy
                if not (4<=nx<=218 and 16<=ny<=120) or (nx,ny) in blocked:continue
                nc=cost+1+(0.6 if nd!=d and d!=-1 else 0)+used[(nx,ny)]*5
                ns=(nx,ny,nd)
                if nc<best.get(ns,1e12):
                    best[ns]=nc;prev[ns]=state
                    heapq.heappush(heap,(nc+abs(nx-end[0])+abs(ny-end[1]),nc,nx,ny,nd))
        assert found is not None,('route failed',page.name,e)
        path=[]
        while found in prev:path.append((found[0]*step,found[1]*step));found=prev[found]
        path.append((start[0]*step,start[1]*step));path.reverse()
        for x,y in path:used[(x/step,y/step)]+=1
        pts=[(sx,sy),(start[0]*step,sy)]+path+[(end[0]*step,ty),(tx,ty)]
        simple=[]
        for pt in pts:
            if simple and pt==simple[-1]:continue
            if len(simple)>1 and ((simple[-2][0]==simple[-1][0]==pt[0]) or (simple[-2][1]==simple[-1][1]==pt[1])):simple[-1]=pt
            else:simple.append(pt)
        e['points']=simple;e['same_column']=same
for p in pages:route(p)

def decorate(p,num):
    p.text(80,1240,2040,p.notes,18)
    if p.name.startswith('II.'):
        p.text(80,1330,2040,'PK = khóa chính; FK = khóa ngoại khai báo; NN = NOT NULL; NULL = cho phép thiếu; UQ = UNIQUE. Một cha có 0..N con; FK NULL cho phép con có 0..1 cha, ngược lại đúng 1 cha.',15)
    elif p.name.startswith('I.'):
        p.text(80,1330,2040,'Các thực thể lặp giữa các trang là cùng khái niệm. Quan hệ khái niệm không thay thế ràng buộc SQL; phần II là tài liệu tham chiếu chính xác của nguồn v2.',15)
    else:p.text(80,1330,2040,'Nét đứt màu cam = đối chiếu/liên hệ thống; xanh = luồng dữ liệu; tím = metadata. Không suy quan hệ nhận diện khách từ tên, email hoặc thứ tự ID.',15)
    p.text(80,1360,1950,'CompanyE | 13/10/2026 | Nguồn: DDL/contracts v2, catalog v2, lake_v2.py. Mẫu: CO5173 Chương 1 slide 63-65; bảng quan hệ theo ký hiệu PK/FK.',13,color='#555555')
for i,p in enumerate(pages,1):decorate(p,i)

colors={'fk':'#2085B0','external':'#BD6B18','concept':'#303030','flow':'#2085B0','reconcile':'#BD6B18','metadata':'#7953A5'}
def render_pdf():
    path=OUT/'CompanyE_Enterprise_Source_ERD.pdf';c=canvas.Canvas(str(path),pagesize=(W,H),pageCompression=1)
    c.setTitle('CompanyE - Enterprise, Source and Cross-System ERD');c.setAuthor('CompanyE - CO5173')
    for idx,p in enumerate(pages,1):
        c.bookmarkPage('p'+str(idx));c.addOutlineEntry(p.name,'p'+str(idx),0)
        c.setFillColor(HexColor('#FFFFFF'));c.rect(0,0,W,H,fill=1,stroke=0)
        for y,h,color in [(0,467,'#080477'),(467,466,'#073478'),(933,467,'#0F53DD')]:
            c.setFillColor(HexColor(color));c.rect(0,H-y-h,28,h,fill=1,stroke=0)
        c.setFillColor(HexColor('#0800C7'));c.setFont('Arial',42);c.drawString(80,H-72,p.title)
        c.setStrokeColor(HexColor('#0800C7'));c.line(45,H-100,2160,H-100)
        c.setFillColor(HexColor('#333333'));c.setFont('Arial',19);c.drawString(80,H-136,p.subtitle)
        c.setFillColor(HexColor('#E8F2FC'));c.rect(55,H-1220,2110,1060,fill=1,stroke=0)
        for e in p.edges:
            col=colors[e['kind']];c.setStrokeColor(HexColor(col));c.setLineWidth(1.6)
            c.setDash(7,4) if e['kind'] in ['external','reconcile','metadata'] else c.setDash()
            pts=e['points']
            for a,b in zip(pts,pts[1:]):c.line(a[0],H-a[1],b[0],H-b[1])
            c.setDash()
            if e['kind'] in ['fk','external']:
                sx,sy=pts[0];tx,ty=pts[-1];enddir=1 if pts[-2][0]>tx else -1
                for off in ([8] if e['optional'] else [8,13]):c.line(sx+off,H-sy-6,sx+off,H-sy+6)
                if e['optional']:c.circle(sx+22,H-sy,4,stroke=1,fill=0)
                for dy in [-7,0,7]:c.line(tx+enddir*14,H-ty,tx,H-(ty+dy))
                c.circle(tx+enddir*24,H-ty,4,stroke=1,fill=0)
            elif e['kind']!='concept':
                tx,ty=pts[-1];dx=tx-pts[-2][0];dy=ty-pts[-2][1];norm=math.hypot(dx,dy);ux,uy=dx/norm,dy/norm
                for s in [-1,1]:c.line(tx,H-ty,tx-ux*14+s*uy*6,H-(ty-uy*14-s*ux*6))
            for x,y,label in e.get('cards',[]):
                c.setFillColor(HexColor('#202020'));c.setFont('Arial-Bold',18);c.drawString(x,H-y,label)
        for n in p.nodes:
            x,y,w,h=n['x'],n['y'],n['w'],n['h'];c.setStrokeColor(HexColor('#333333'));c.setLineWidth(1)
            fill='#FFF4E0' if n['kind']=='diamond' else '#FFFFFF';c.setFillColor(HexColor(fill))
            if n['kind']=='diamond':
                diamond_path=c.beginPath();diamond_path.moveTo(x+w/2,H-y);diamond_path.lineTo(x+w,H-y-h/2);diamond_path.lineTo(x+w/2,H-y-h);diamond_path.lineTo(x,H-y-h/2);diamond_path.close();c.drawPath(diamond_path,fill=1,stroke=1)
            else:c.rect(x,H-y-h,w,h,fill=1,stroke=1)
            if n['kind'] in ['entity','diamond']:
                c.setFillColor(HexColor('#111111'));c.setFont('Arial-Bold' if n['kind']=='entity' else 'Arial',n['size'])
                for j,line in enumerate(wrap(n['title'],w-24,n['size'],n['kind']=='entity')):c.drawCentredString(x+w/2,H-y-h/2+4-j*n['size']*1.2,line)
            else:
                c.setFillColor(HexColor('#E5E7EB' if n['kind']=='ref' else '#D5E5F5' if n['kind']=='table' else '#E4DDF1'));c.rect(x,H-y-n['th'],w,n['th'],stroke=0,fill=1)
                c.setFillColor(HexColor('#111111'));c.setFont('Arial-Bold',17)
                for j,line in enumerate(n['title'].splitlines()):c.drawString(x+10,H-y-24-j*22,line)
                yy=y+n['th']
                for row in n['rows']:
                    c.setLineWidth(.5);c.line(x,H-yy,x+w,H-yy);c.setFont('Arial',n['size'])
                    for j,line in enumerate(row['text'].splitlines()):c.drawString(x+12,H-yy-21-j*n['size']*1.22,line)
                    yy+=row['h']
        for t in p.texts:
            c.setFillColor(HexColor(t['color']));c.setFont('Arial-Bold' if t['bold'] else 'Arial',t['size'])
            for j,line in enumerate(t['text'].splitlines()):c.drawString(t['x'],H-t['y']-t['size']-j*t['size']*1.25,line)
        c.setFont('Arial',14);c.drawRightString(2160,18,f'{idx:02d} / {len(pages):02d}');c.showPage()
    c.save();return path

def render_drawio():
    file=ET.Element('mxfile',{'host':'app.diagrams.net','type':'device','pages':str(len(pages))})
    for pi,p in enumerate(pages):
        dia=ET.SubElement(file,'diagram',{'id':'companye-erd-'+str(pi),'name':p.name})
        graph=ET.SubElement(dia,'mxGraphModel',{'grid':'1','gridSize':'10','page':'1','pageScale':'1','pageWidth':str(W),'pageHeight':str(H),'guides':'1','connect':'1','arrows':'1'})
        root=ET.SubElement(graph,'root');ET.SubElement(root,'mxCell',{'id':'0'});ET.SubElement(root,'mxCell',{'id':'1','parent':'0'})
        def cell(id,text,x,y,w,h,style,parent='1'):
            el=ET.SubElement(root,'mxCell',{'id':id,'value':'<br>'.join(html.escape(line) for line in text.split('\n')),'style':style,'vertex':'1','parent':parent})
            ET.SubElement(el,'mxGeometry',{'x':str(x),'y':str(y),'width':str(w),'height':str(h),'as':'geometry'})
        base='html=1;fontFamily=Arial;whiteSpace=wrap;'
        cell('strip','',0,0,28,H,'fillColor=#080477;strokeColor=none;')
        cell('bg','',55,160,2110,1060,'fillColor=#E8F2FC;strokeColor=none;')
        cell('heading',p.title,80,22,2060,60,base+'text;fontSize=42;fontColor=#0800C7;align=left;')
        cell('subtitle',p.subtitle,80,108,2060,40,base+'text;fontSize=19;align=left;')
        for n in p.nodes:
            if n['kind'] in ['entity','diamond']:
                cell(n['id'],n['title'],n['x'],n['y'],n['w'],n['h'],base+f'shape={"rhombus" if n["kind"]=="diamond" else "rectangle"};fillColor={"#FFF4E0" if n["kind"]=="diamond" else "#FFFFFF"};fontSize={n["size"]};fontStyle={1 if n["kind"]=="entity" else 0};strokeColor=#333333;')
                continue
            cell(n['id'],'',n['x'],n['y'],n['w'],n['h'],'group;')
            color='#E5E7EB' if n['kind']=='ref' else '#D5E5F5' if n['kind']=='table' else '#E4DDF1'
            cell(n['id']+'_h',n['title'],0,0,n['w'],n['th'],base+f'fillColor={color};strokeColor=#333333;fontSize=17;fontStyle=1;align=left;spacingLeft=10;',n['id'])
            yy=n['th']
            for ri,row in enumerate(n['rows']):
                cell(n['id']+'_r'+str(ri),row['text'],0,yy,n['w'],row['h'],base+f'fillColor=#FFFFFF;strokeColor=#333333;fontSize={n["size"]};align=left;spacingLeft=12;',n['id']);yy+=row['h']
        for i,e in enumerate(p.edges):
            iser=e['kind'] in ['fk','external'];pts=e['points']
            style=base+f'edgeStyle=segmentEdgeStyle;rounded=0;strokeColor={colors[e["kind"]]};strokeWidth=1.6;'
            style+=f'startArrow={"ERzeroToOne" if e["optional"] else "ERmandOne"};endArrow=ERzeroToMany;startFill=0;endFill=0;' if iser else 'startArrow=none;endArrow='+('none' if e['kind']=='concept' else 'open')+';'
            if e['kind'] in ['external','reconcile','metadata']:style+='dashed=1;'
            source=e['a']+('_r'+str(e['ar']) if e['ar']>=0 else '');target=e['b']+('_r'+str(e['br']) if e['br']>=0 else '')
            style+='exitX='+('0' if e.get('source_left') else '1')+';exitY=0.5;entryX='+('1' if e.get('same_column') else '0')+';entryY=0.5;'
            el=ET.SubElement(root,'mxCell',{'id':'edge'+str(i),'edge':'1','parent':'1','source':source,'target':target,'style':style,'value':''})
            geo=ET.SubElement(el,'mxGeometry',{'relative':'1','as':'geometry'});arr=ET.SubElement(geo,'Array',{'as':'points'})
            for x,y in pts[1:-1]:ET.SubElement(arr,'mxPoint',{'x':str(x),'y':str(y)})
            for j,(x,y,text) in enumerate(e.get('cards',[])):cell(f'card{i}-{j}',text,x,y-20,65,26,base+'text;fontSize=18;fontStyle=1;')
        for i,t in enumerate(p.texts):cell('text'+str(i),t['text'],t['x'],t['y'],t['w'],t['h']+6,base+f'text;align=left;verticalAlign=top;fontSize={t["size"]};fontColor={t["color"]};spacing=0;')
    path=OUT/'CompanyE_Enterprise_Source_ERD.drawio';ET.indent(file);ET.ElementTree(file).write(path,encoding='utf-8',xml_declaration=True);return path

pdf=render_pdf();drawio=render_drawio()
reader=PdfReader(pdf);assert len(reader.pages)==len(pages)
for page_index,(db,name,title,local) in enumerate(groups,3):
    page_text=reader.pages[page_index].extract_text()
    for table in local:
        assert table in page_text,(name,table)
        for col in tables[db+'.'+table]['columns']:
            assert col['name'] in page_text,(name,table,col['name'])
for p in pages:
    for n in p.nodes:assert n['x']>=0 and n['y']>=160 and n['x']+n['w']<W and n['y']+n['h']<1220,(p.name,n['id'])
    for t in p.texts:assert t['y']+t['h']<H,(p.name,t)
for dia in ET.parse(drawio).getroot():
    cells=dia.findall('.//mxCell');ids={c.get('id') for c in cells};assert len(ids)==len(cells)
    for c in cells:
        for key in ['parent','source','target']:
            if c.get(key):assert c.get(key) in ids
assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in hashes.items())
report={'status':'PASSED','pages':len(pages),'conceptual_pages':3,'source_pages':len(groups),'integration_pages':2,
 'source_tables':len(tables),'source_columns':sum(len(t['columns']) for t in tables.values()),'declared_foreign_keys':len(fks),
 'all_tables_shown_in_full_once':True,'all_declared_foreign_keys_drawn':True,'source_files_unchanged':True,
 'all_source_columns_present_in_pdf':True,
 'inputs_sha256':hashes,'visual_review':'PENDING','page_index':[p.name for p in pages],
 'scope':'Static DDL/contracts/catalog review; not a live database constraint audit.'}
(ROOT/'reports/companye_erd_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(ROOT/'config/source_erd_relationships_v2.json').write_text(json.dumps({'tables':[{k:t[k] for k in ['key','columns','checks','unique']} for t in tables.values()],'foreign_keys':fks,'cross_database_refs':['centres.site_code -> sites.site_id','ticket_orders.hotel_booking_ref -> bookings.booking_id','rentals.hotel_booking_ref -> bookings.booking_id','customers.member_card_ref -> member_cards.card_id']},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ['inputs_sha256','page_index']}))

