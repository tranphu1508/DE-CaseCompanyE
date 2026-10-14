"""Build editable draw.io and vector PDF diagrams from the frozen logical model.

The same scene graph drives both outputs. No database or generator is modified.
"""
import hashlib
import html
import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / 'config/dimensional_model_v1.json'
model_bytes = MODEL.read_bytes()
model = json.loads(model_bytes)
facts = {f['id']: f for f in model['facts']}
dims = {d['id']: d for d in model['dimensions']}
OUT = ROOT / 'docs'
W, H = 1600, 1100
for name, filename in [('Arial','arial.ttf'), ('Arial-Bold','arialbd.ttf')]:
    pdfmetrics.registerFont(TTFont(name, str(Path('C:/Windows/Fonts') / filename)))

# These are logical column names, not a physical DDL contract.
# Every foreign-key role is checked against the existing dimension_roles below.
dim_fields = {
 'D01': ['date_key', 'calendar_date', 'day, day_of_week', 'month, quarter, year'],
 'D02': ['site_key', 'site_id (BK)', 'site_name', 'climate_region'],
 'D03': ['hotel_key', 'hotel_id (BK), hotel_name', 'stars, site_id (thuộc tính)', 'website_channel'],
 'D04': ['room_key', 'room_id (BK), hotel_id', 'room_type, capacity', 'base_rate_vnd'],
 'D05': ['channel_key', 'source_namespace, channel_code (BK)', 'channel_name, channel_type', 'commission_bps (nếu có)'],
 'D06': ['promotion_key', 'promotion_id (BK), promotion_name', 'sale_from/to, stay_from/to', 'discount_bps, partner_share_bps', 'cap_vnd, channel_id, site_id'],
 'D07': ['customer_profile_key', 'source_system + source_customer_id (BK)', 'full_name, phone, email', 'member_card_ref (nếu có)'],
 'D08': ['rate_plan_key', 'rate_plan_id (BK), plan_name', 'breakfast_included, refundable', 'hotel_id, channel_id (thuộc tính)'],
 'D09': ['outlet_key', 'outlet_id (BK), hotel_id', 'outlet_type, capacity', 'quality_profile'],
 'D10': ['meal_key', 'meal_code (BK)', 'BREAKFAST / LUNCH', 'DINNER / BAR'],
 'D11': ['centre_key', 'centre_id (BK), centre_name', 'site_code (thuộc tính)'],
 'D12': ['activity_key', 'activity_id (BK), activity_name', 'outdoor, capacity_per_day', 'centre_id (thuộc tính)'],
 'D13': ['vehicle_key', 'vehicle_id (BK), vehicle_type', 'daily_rate_vnd', 'centre_id (thuộc tính)'],
 'D14': ['supplier_key', 'supplier_id (BK), supplier_name', 'category, delivery_format', 'site_id (thuộc tính)'],
 'D15': ['item_key', 'item_id (BK), item_name', 'specification, base_unit', 'shelf_life_days'],
 'D16': ['asset_key', 'asset_id (BK), asset_type', 'hotel_id, room_id (có thể thiếu)', 'supplier_id (bên bán tài sản)'],
}
default_fk = {k: v[0] for k, v in dim_fields.items()}
role_overrides = {
 'F01': {'D01': ['booked_date_key', 'arrival_date_key', 'departure_date_key'], 'D06': ['promotion_key*']},
 'F03': {'D01': ['service_date_key']},
 'F04': {'D01': ['ordered_date_key', 'cohort_departure_date_key*'], 'D02': ['service_site_key','booking_site_key*'], 'D03': ['referral_hotel_key*'], 'D05': ['ticket_channel_key','booking_channel_key*']},
 'F05': {'D01': ['pickup_date_key','return_date_key','cohort_departure_date_key*'], 'D02': ['service_site_key','booking_site_key*'], 'D03': ['referral_hotel_key*'], 'D05': ['booking_channel_key*']},
 'F06': {'D01': ['service_date_key']},
 'F07': {'D01': ['service_date_key'], 'D03': ['service_hotel_key','booking_hotel_key*'], 'D07': ['customer_profile_key*']},
 'F08': {'D01': ['service_date_key']},
 'F09': {'D01': ['admission_date_key']},
 'F12': {'D01': ['ordered_date_key','expected_date_key']},
 'F13': {'D01': ['received_date_key','expected_date_key','expires_date_key*']},
 'F14': {'D01': ['movement_date_key']},
 'F15': {'D01': ['snapshot_date_key']},
 'F16': {'D01': ['start_date_key','end_date_key'], 'D04': ['room_key*']},
 'F17': {'D01': ['weather_date_key']},
}
measures = {
 'F01': ['booking_count = 1', 'gross_vnd, discount_vnd', 'customer_due_vnd, commission_vnd', 'company_share_vnd, partner_share_vnd'],
 'F02': ['inventory_day = 1', 'blocked_day (0/1)', 'available_day = 1 - blocked_day'],
 'F03': ['occupied_night = 1'],
 'F04': ['gross_vnd, refunded_vnd', 'net_ticket_vnd = gross - refunded'],
 'F05': ['agreed_vnd'],
 'F06': ['eligible_covers', 'redeemed_covers'],
 'F07': ['net_vnd, covers', 'rating_sum, rating_count'],
 'F08': ['actual_covers', 'ingredient_cost_vnd'],
 'F09': ['admission_count = 1'],
 'F10': ['nominal_capacity', 'is_closed, available_capacity'],
 'F11': ['inventory_day, maintenance_day', 'available_day, rented_day'],
 'F12': ['ordered_qty', 'unit_price_vnd'],
 'F13': ['accepted_qty, rejected_qty', 'late_accepted_qty'],
 'F14': ['quantity, signed_qty', 'in_qty, use_qty, waste_qty', 'movement_value_vnd = quantity × giá lô'],
 'F15': ['closing_qty, closing_value_vnd', 'in_qty, use_qty, waste_qty trong ngày'],
 'F16': ['cost_vnd'],
 'F17': ['temperature_c, rain_mm', 'severe_weather'],
}
traces = {
 'F01': ['booking_id (DD), status'], 'F02': [],
 'F03': ['booking_id, booking_room_id, stay_id (DD)'],
 'F04': ['ticket_order_id, hotel_booking_ref* (DD)'],
 'F05': ['rental_id, hotel_booking_ref* (DD), status'],
 'F06': ['entitlement_id, booking_room_id (DD)'],
 'F07': ['dining_order_id, booking_id* (DD)'],
 'F08': ['session_id (DD)'], 'F09': ['admission_id, ticket_id (DD)'],
 'F10': [], 'F11': [], 'F12': ['purchase_line_id, purchase_order_id (DD)'],
 'F13': ['receipt_id, purchase_line_id (DD)'],
 'F14': ['movement_id, receipt_id, session_id* (DD)', 'movement_type, usage_area'],
 'F15': ['receipt_id (DD)'], 'F16': ['maintenance_id (DD), work_type, status'],
 'F17': ['provenance'],
}

def wrapped(text, width, size=15, font='Arial'):
    lines=[]
    for paragraph in str(text).split('\n'):
        line=''
        for word in paragraph.split():
            trial = (line+' '+word).strip()
            if pdfmetrics.stringWidth(trial,font,size) > width and line:
                lines.append(line); line=word
            else: line=trial
        lines.append(line)
    return lines

class Page:
    def __init__(self, name, title, subtitle):
        self.name=name; self.title=title; self.subtitle=subtitle
        self.boxes=[]; self.edges=[]; self.texts=[]
    def text(self, x,y,w,text,size=16,bold=False,color='#222222'):
        lines=wrapped(text,w,size,'Arial-Bold' if bold else 'Arial')
        self.texts.append(dict(x=x,y=y,w=w,h=len(lines)*size*1.28,text='\n'.join(lines),size=size,bold=bold,color=color))
        return len(lines)*size*1.28
    def box(self,id,x,y,w,title,rows,kind='dim',font=14,row_h=27):
        b=dict(id=id,x=x,y=y,w=w,h=34+len(rows)*row_h,title=title,rows=rows,kind=kind,font=font,row_h=row_h)
        assert all(pdfmetrics.stringWidth(r,'Arial',font)<w-20 for r in rows), (title,rows,w)
        self.boxes.append(b); return b
    def edge(self, source, sr, target, tr, side='left', lane=0, dashed=False, label=None):
        # Side indicates the dimension's side relative to the fact.
        sx=source['x']+source['w'] if side=='left' else source['x']
        tx=target['x'] if side=='left' else target['x']+target['w']
        sy=source['y']+34+(sr+0.5)*source['row_h']
        ty=target['y']+34+(tr+0.5)*target['row_h']
        mid=(sx+tx)/2 + lane
        self.edges.append(dict(source=source['id'],sr=sr,target=target['id'],tr=tr,
            points=[(sx,sy),(mid,sy),(mid,ty),(tx,ty)],dashed=dashed,label=label,
            optional=target['rows'][tr].endswith('*')))

pages=[]
overview=Page('00 - Tong the','CompanyE - Fact Constellation','Bản đồ tổng thể | Các trang sau trình bày PK, FK và quan hệ chi tiết của từng star.')
groups=[
 ('Lưu trú | B01-B03',['F01','F02','F03']),
 ('Ăn uống | B04',['F06','F07','F08']),
 ('Vé và hoạt động | B03, B05',['F04','F09','F10']),
 ('Phương tiện | B03, B05',['F05','F11']),
 ('Mua và nhận hàng | B06',['F12','F13']),
 ('Tồn kho | B07',['F14','F15']),
 ('Bảo trì | B08',['F16']),
 ('Ngữ cảnh thời tiết | B05',['F17']),
]
for i,(title,ids) in enumerate(groups):
    x=75+(i%3)*500; y=165+(i//3)*230
    ds=sorted({d for fid in ids for d in facts[fid]['dimension_roles']})
    rows=[fid+' '+facts[fid]['name'] for fid in ids]
    rows+=['Dimension: '+', '.join(ds[:6])]
    if len(ds)>6: rows.append('                    '+', '.join(ds[6:]))
    overview.box('group'+str(i),x,y,450,title,rows,'group',14,29)
overview.text(1075,630,450,'Cùng mã D = cùng dimension logic. Một dimension xuất hiện ở nhiều trang chỉ là bản vẽ lặp, không phải bảng mới.',17,True)
overview.text(1075,727,450,'D01 DimDate và D02 DimSite được dùng ở cả 17 fact/bảng tổng hợp. F15 tùy chọn; F17 là ngữ cảnh.',16)
overview.text(75,874,1450,'Chọn Fact Constellation cho toàn hệ thống; mỗi fact giữ grain riêng. Các trang 03-19 là từng Star Schema. Trang 02 minh họa hai fact thực sự dùng chung dimension; trang 20 mô tả bridge và liên kết có kiểm soát.',17)
pages.append(overview)

def fk_rows(fid):
    return [(d,key) for d in facts[fid]['dimension_roles'] for key in role_overrides.get(fid,{}).get(d,[default_fk[d]])]

def fact_box(page,fid,x,y,w=490,font=15,row_h=26):
    rows=['PK  fact_key (khóa kỹ thuật đề xuất)']
    rows += ['FK  '+k for d,k in fk_rows(fid)]
    rows += ['M   '+m for m in measures[fid]]
    rows += traces[fid]
    return page.box(fid,x,y,w,fid+'  '+facts[fid]['name'],rows,'fact',font,row_h)

def dim_box(page,did,x,y,w=330,font=14,row_h=27,compact=False):
    fields=dim_fields[did]
    if compact: fields=fields[:2]
    return page.box(did,x,y,w,did+'  '+dims[did]['name'],['PK  '+fields[0]]+fields[1:],'dim',font,row_h)

const=Page('01 - Hai fact dung chung','CompanyE - Multiple Fact Tables','B06 | FactPurchaseLine và FactReceipt dùng chung năm dimension; không nối trực tiếp để SUM số đo.')
left=fact_box(const,'F12',75,235,465,14,28)
right=fact_box(const,'F13',1060,235,465,14,28)
for i,did in enumerate(['D01','D02','D03','D14','D15']):
    db=dim_box(const,did,635,160+i*140,330,14,25,True)
    for fb,fid,side in [(left,'F12','right'),(right,'F13','left')]:
        for row,(d,key) in enumerate(fk_rows(fid),1):
            if d==did: const.edge(db,0,fb,row,side,lane=(i-2)*8)
const.text(75,790,455,'Grain F12: một dòng đặt mua.\nGrain F13: một lần nhận của một dòng đặt mua.\nMột dòng mua có thể nhận hàng nhiều lần.',16)
const.text(1060,790,455,'purchase_line_id là định danh đối chiếu. Tổng receipt về dòng mua trước khi ghép để tính KPI; giữ cả dòng đến hạn chưa nhận.',16)
const.text(75,905,1450,'Khóa chiều dùng chung giúp so sánh cùng kỳ, khách sạn, nhà cung cấp và mặt hàng. Các vai trò ordered / expected / received / expires đều tham chiếu cùng DimDate.',16)
pages.append(const)

edge_coverage=[]
for fid,f in facts.items():
    reqs=[r['id'] for r in model['requirements'] if fid in r['fact_usage']]
    scope={'CORE':'CORE','OPTIONAL_AGGREGATE':'TỔNG HỢP TÙY CHỌN','CONTEXT':'DỮ LIỆU NGỮ CẢNH'}[f['scope']]
    p=Page(fid+' - '+f['name'],fid+' - '+f['name'],', '.join(reqs)+' | '+scope+' | Grain: '+f['grain'])
    fb=fact_box(p,fid,555,230)
    ds=list(f['dimension_roles'])
    nleft=math.ceil(len(ds)/2)
    for i,did in enumerate(ds):
        isleft=i<nleft; idx=i if isleft else i-nleft
        db=dim_box(p,did,75 if isleft else 1195,165+idx*180)
        for row,(d,key) in enumerate(fk_rows(fid),1):
            if d==did:
                p.edge(db,0,fb,row,'left' if isleft else 'right',lane=(idx-1.5)*16)
                edge_coverage.append(dict(fact=fid,dimension=d,fk=key.rstrip('*'),conditional=key.endswith('*')))
    unique_key=f['unique_key']
    if fid=='F15': unique_key=unique_key.replace('date_key','snapshot_date_key')
    if fid=='F17': unique_key=unique_key.replace('date_key','weather_date_key')
    p.text(555,fb['y']+fb['h']+15,490,'UQ trong batch:\n'+unique_key,14,True)
    p.text(75,915,1450,'Quy tắc: '+f['rules'],15)
    p.text(75,965,1450,'Vai trò ngày: '+f['date_roles'],14,color='#444444')
    pages.append(p)

# Separate page: controlled links are not ordinary analytical fact-to-fact joins.
links=Page('19 - Bridge va lien ket','CompanyE - Bridge và liên kết','Bridge phục vụ lọc và truy vết có kiểm soát; không phải đường JOIN mặc định để cộng số đo.')
b1=links.box('bridge_booking',560,180,490,'BridgeBookingRoom',[
 'UQ  source_system + booking_room_id','DD  booking_id (có namespace)',
 'FK  room_key','FK  rate_plan_key'],'bridge',15,30)
d4=dim_box(links,'D04',75,175)
d8=dim_box(links,'D08',1195,175)
links.edge(d4,0,b1,2,'left');links.edge(d8,0,b1,3,'right')
links.text(555,355,550,'F01 lọc theo phòng/gói giá bằng EXISTS trên booking_id. Không sao chép tiền booking lên từng phòng và không ngầm phân bổ doanh thu.',16)
b2=links.box('bridge_maintenance',560,470,490,'BridgeRoomDayMaintenance',[
 'UQ  room_key + date_key + maintenance_id', 'FK  room_key','FK  date_key',
 'DD  maintenance_id (có namespace)'],'bridge',15,30)
d1=dim_box(links,'D01',75,470)
# Duplicate graphical room reference has a different diagram identifier only.
d4b=links.box('D04_repeat',1195,470,330,'D04  DimRoom (cùng bảng)', ['PK  room_key','room_id (BK), hotel_id','room_type, capacity'],'dim',14,27)
links.edge(d1,0,b2,2,'left');links.edge(d4b,0,b2,1,'right')
links.text(555,645,555,'F02 lấy DISTINCT room/date để tính ngày ngừng bán. maintenance_id truy vết F16; không SUM cost sau khi nối nhiều ngày.',16)
links.box('validated',75,775,705,'ValidatedBookingServiceLink (view hoặc mapping)',[
 'UQ  service_type + service_id; booking_id có namespace',
 'F04/F05 -> booking hợp lệ: n:1; độc lập: không có ref',
 'Ref sai -> quarantine; tổng dịch vụ về booking trước B03'], 'bridge',14,29)
links.box('crosswalk',820,775,705,'SiteCrosswalk (mapping ở ETL)',[
 'UQ  source centre_id; target site_id',
 'entertainment_ops.centres.site_code = hotel_ops.sites.site_id',
 'Tra cứu cùng DimSite; không phải dimension snowflake'], 'bridge',14,29)
pages.append(links)

# Common notation is part of every page, and therefore travels with screenshots.
legend='PK: khóa chính | FK: khóa ngoại | BK: khóa nghiệp vụ | UQ: khóa duy nhất | M: số đo | DD: định danh giao dịch | *: có thể thiếu'
for i,p in enumerate(pages,1):
    p.text(75,1014,1450,legend,13,color='#333333')
    p.text(75,1039,1450,'Dimension 1 (0..1 nếu FK*) - 0..N fact. BK/DD nguồn có namespace; Type 1 ở v2; D07 chưa hợp nhất khách. Chưa phải DDL, chưa vẽ đủ cột batch/lineage.',12,color='#555555')
    p.text(75,1061,1430,'Mẫu: CO5173 Chương 2, slide 54-55, 59; CO4031 Chương 3, slide 17. CompanyE logical model v1.0 | 13/10/2026.',11,color='#555555')

# Give role-playing references separate attachment ports on the same PK row.
# In particular, optional and required roles must not share a cardinality marker.
for p in pages:
    groups={}
    by_id={b['id']:b for b in p.boxes}
    for e in p.edges:
        groups.setdefault((e['source'],e['sr'],e['points'][0][0]),[]).append(e)
    for (source,sr,sx),edges in groups.items():
        b=by_id[source]
        for i,e in enumerate(edges):
            offset=0 if len(edges)==1 else (i/(len(edges)-1)-0.5)*18
            e['exit_y']=0.5+offset/b['row_h']
            sy=b['y']+34+(sr+0.5)*b['row_h']+offset
            e['points'][0]=(sx,sy)
            e['points'][1]=(e['points'][1][0],sy)

def draw_pdf():
    path=OUT/'CompanyE_Dimensional_Model.pdf'
    c=canvas.Canvas(str(path),pagesize=(W,H),pageCompression=1)
    c.setTitle('CompanyE - Dimensional Model / Fact Constellation')
    c.setAuthor('CompanyE Project - CO5173')
    for number,p in enumerate(pages,1):
        c.bookmarkPage('page'+str(number)); c.addOutlineEntry(p.name,'page'+str(number),0)
        c.setFillColor(HexColor('#FFFFFF'));c.rect(0,0,W,H,fill=1,stroke=0)
        for top,height,color in [(0,365,'#090477'),(365,365,'#073478'),(730,370,'#0F53DD')]:
            c.setFillColor(HexColor(color));c.rect(0,H-top-height,25,height,fill=1,stroke=0)
        c.setFillColor(HexColor('#0800C7'));c.setFont('Arial',36);c.drawString(75,H-68,p.title)
        c.setStrokeColor(HexColor('#0800C7'));c.setLineWidth(1);c.line(45,H-88,1570,H-88)
        c.setFillColor(HexColor('#333333'));c.setFont('Arial',16);c.drawString(75,H-121,p.subtitle)
        c.setFillColor(HexColor('#DFEEFC'));c.rect(55,H-997,1500,852,fill=1,stroke=0)
        # Edges first, tables second, so connectors cannot obscure text.
        for edge in p.edges:
            pts=edge['points'];c.setStrokeColor(HexColor('#239ECC'));c.setLineWidth(1.4)
            c.setDash(5,3) if edge['dashed'] else c.setDash()
            for a,b in zip(pts,pts[1:]):c.line(a[0],H-a[1],b[0],H-b[1])
            sx,sy=pts[0];tx,ty=pts[-1];toward=1 if pts[1][0]>sx else -1
            for off in ([8] if edge['optional'] else [8,12]):c.line(sx+toward*off,H-sy-5,sx+toward*off,H-sy+5)
            if edge['optional']:c.circle(sx+toward*18,H-sy,3,stroke=1,fill=0)
            direction=1 if pts[-2][0]>tx else -1
            for dy in [-6,0,6]:c.line(tx+direction*11,H-ty,tx,H-(ty+dy))
            c.circle(tx+direction*19,H-ty,3,stroke=1,fill=0)
            c.setDash()
        for b in p.boxes:
            x,y,w,h=b['x'],b['y'],b['w'],b['h']
            c.setFillColor(HexColor('#FFFFFF'));c.setStrokeColor(HexColor('#333333'))
            c.setLineWidth(1.5 if b['kind']=='fact' else 0.8)
            c.rect(x,H-y-h,w,h,stroke=1,fill=1)
            fill='#C8DCF0' if b['kind']=='fact' else '#F5F7FA' if b['kind']=='dim' else '#E8E4D9'
            c.setFillColor(HexColor(fill));c.rect(x,H-y-34,w,34,stroke=0,fill=1)
            c.setFillColor(HexColor('#111111'));c.setFont('Arial-Bold',min(16,b['font']+1))
            c.drawString(x+10,H-y-23,b['title'])
            for ri,row in enumerate(b['rows']):
                yy=y+34+ri*b['row_h'];c.setLineWidth(.55);c.line(x,H-yy,x+w,H-yy)
                c.setFont('Arial',b['font']);c.drawString(x+10,H-yy-b['row_h']*.69,row)
        for t in p.texts:
            c.setFillColor(HexColor(t['color']));c.setFont('Arial-Bold' if t['bold'] else 'Arial',t['size'])
            for j,line in enumerate(t['text'].splitlines()):c.drawString(t['x'],H-t['y']-t['size']-j*t['size']*1.28,line)
        c.setFillColor(HexColor('#333333'));c.setFont('Arial',12);c.drawRightString(1560,18,f'{number:02d} / {len(pages):02d}')
        c.showPage()
    c.save();return path

def draw_drawio():
    mxfile=ET.Element('mxfile',{'host':'app.diagrams.net','type':'device','version':'24.7.17','pages':str(len(pages))})
    for pi,p in enumerate(pages):
        diagram=ET.SubElement(mxfile,'diagram',{'id':f'companye-{pi}','name':p.name})
        graph=ET.SubElement(diagram,'mxGraphModel',{'dx':str(W),'dy':str(H),'grid':'1','gridSize':'10','guides':'1','tooltips':'1','connect':'1','arrows':'1','fold':'1','page':'1','pageScale':'1','pageWidth':str(W),'pageHeight':str(H),'math':'0','shadow':'0'})
        root=ET.SubElement(graph,'root');ET.SubElement(root,'mxCell',{'id':'0'});ET.SubElement(root,'mxCell',{'id':'1','parent':'0'})
        def cell(id,value,x,y,w,h,style,parent='1'):
            c=ET.SubElement(root,'mxCell',{'id':id,'value':value,'style':style,'vertex':'1','parent':parent})
            ET.SubElement(c,'mxGeometry',{'x':str(x),'y':str(y),'width':str(w),'height':str(h),'as':'geometry'})
            return c
        for n,(y,h,color) in enumerate([(0,365,'#090477'),(365,365,'#073478'),(730,370,'#0F53DD')]):
            cell('strip'+str(n),'',0,y,25,h,f'fillColor={color};strokeColor=none;')
        cell('bg','',55,145,1500,852,'fillColor=#DFEEFC;strokeColor=none;')
        cell('title',html.escape(p.title),75,22,1470,54,'text;html=1;fontFamily=Arial;fontSize=36;fontColor=#0800C7;align=left;verticalAlign=middle;')
        cell('rule','',45,87,1525,1,'fillColor=#0800C7;strokeColor=none;')
        cell('subtitle',html.escape(p.subtitle),75,97,1450,35,'text;html=1;fontFamily=Arial;fontSize=16;align=left;verticalAlign=middle;')
        for b in p.boxes:
            cell(b['id'],'',b['x'],b['y'],b['w'],b['h'],'group;')
            fill='#C8DCF0' if b['kind']=='fact' else '#F5F7FA' if b['kind']=='dim' else '#E8E4D9'
            cell(b['id']+'_title',html.escape(b['title']),0,0,b['w'],34,f'rounded=0;html=1;fillColor={fill};strokeColor=#333333;fontFamily=Arial;fontSize={min(16,b["font"]+1)};fontStyle=1;align=left;spacingLeft=10;',b['id'])
            for ri,row in enumerate(b['rows']):
                cell(b['id']+'_r'+str(ri),html.escape(row),0,34+ri*b['row_h'],b['w'],b['row_h'],f'rounded=0;html=1;fillColor=#FFFFFF;strokeColor=#333333;fontFamily=Arial;fontSize={b["font"]};align=left;spacingLeft=10;',b['id'])
        for ei,e in enumerate(p.edges):
            pts=e['points'];start_right=pts[1][0]>pts[0][0];end_left=pts[-2][0]<pts[-1][0]
            start_arrow='ERzeroToOne' if e['optional'] else 'ERmandOne'
            style=f'edgeStyle=segmentEdgeStyle;rounded=0;html=1;strokeColor=#239ECC;strokeWidth=1.4;startArrow={start_arrow};startFill=0;endArrow=ERzeroToMany;endFill=0;exitX={1 if start_right else 0};exitY={e["exit_y"]};entryX={0 if end_left else 1};entryY=0.5;'
            if e['dashed']:style+='dashed=1;'
            c=ET.SubElement(root,'mxCell',{'id':'edge'+str(ei),'value':e['label'] or '', 'style':style,'edge':'1','parent':'1','source':e['source']+'_r'+str(e['sr']),'target':e['target']+'_r'+str(e['tr'])})
            g=ET.SubElement(c,'mxGeometry',{'relative':'1','as':'geometry'});a=ET.SubElement(g,'Array',{'as':'points'})
            for x,y in pts[1:-1]:ET.SubElement(a,'mxPoint',{'x':str(x),'y':str(y)})
        for ti,t in enumerate(p.texts):
            cell('text'+str(ti),'<br>'.join(html.escape(line) for line in t['text'].splitlines()),t['x'],t['y'],t['w'],t['h']+5,f'text;html=1;fontFamily=Arial;fontSize={t["size"]};fontColor={t["color"]};fontStyle={1 if t["bold"] else 0};align=left;verticalAlign=top;whiteSpace=wrap;spacing=0;')
        cell('page_number',f'{pi+1:02d} / {len(pages):02d}',1470,1068,90,20,'text;html=1;fontFamily=Arial;fontSize=12;align=right;')
    path=OUT/'CompanyE_Dimensional_Model.drawio'
    ET.indent(mxfile);ET.ElementTree(mxfile).write(path,encoding='utf-8',xml_declaration=True)
    return path

pdf=draw_pdf();drawio=draw_drawio()

# Structural verification: exact fact/dimension coverage, valid editable endpoints,
# page bounds, readable text widths and preservation of the input specification.
actual={(e['fact'],e['dimension']) for e in edge_coverage}
expected={(f['id'],d) for f in facts.values() for d in f['dimension_roles']}
assert actual==expected
for p in pages:
    for b in p.boxes:
        assert 0<=b['x'] and b['x']+b['w']<=W and b['y']+b['h']<1000,(p.name,b['id'])
        assert pdfmetrics.stringWidth(b['title'],'Arial-Bold',min(16,b['font']+1))<b['w']-20,b['title']
    for t in p.texts:assert t['y']+t['h']<=H,(p.name,t)
tree=ET.parse(drawio)
for diagram in tree.getroot():
    cells=diagram.findall('.//mxCell');ids={c.get('id') for c in cells}
    assert len(ids)==len(cells)
    for c in cells:
        for key in ['parent','source','target']:
            if c.get(key):assert c.get(key) in ids
reader=PdfReader(pdf)
assert len(reader.pages)==len(pages)==20
for i,fid in enumerate(facts,2):
    text=reader.pages[i].extract_text()
    assert facts[fid]['name'] in text
    for d in facts[fid]['dimension_roles']:assert dims[d]['name'] in text
assert MODEL.read_bytes()==model_bytes
report={'status':'PASSED','pages':len(pages),'facts':len(facts),'dimensions':len(dims),
        'fact_dimension_pairs':len(expected),'role_specific_foreign_keys':len(edge_coverage),
        'editable_edge_endpoints_valid':True,'model_unchanged':True,
        'model_sha256':hashlib.sha256(model_bytes).hexdigest(),
        'scope':'Logical diagrams only; technical fact_key is proposed, not implemented DDL.',
        'visual_review':'PENDING','foreign_key_roles':edge_coverage}
(ROOT/'reports/dimensional_diagrams_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(ROOT/'config/dimensional_diagram_roles_v1.json').write_text(json.dumps({'dimension_columns':dim_fields,'foreign_key_roles':edge_coverage,'fact_measures':measures,'fact_trace_attributes':traces},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='foreign_key_roles'}))
