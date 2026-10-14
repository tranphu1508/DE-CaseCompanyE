"""Reproducible local Power BI Import project; never modifies published facts.

F01 presentation enrichment aggregates each child at its source-aware booking
identity before joining. F12 receipt enrichment has the explicit fixed assessment
date 2025-12-31. Original immutable CSV exports and their hashes are retained.
"""
from pathlib import Path
from collections import defaultdict
from decimal import Decimal
import csv, json, hashlib, uuid, sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from semantic.queries import ALLOWED, DOMAINS
def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
manifest=read(ROOT/'reports/powerbi/export.json');pid=manifest['publication_id']
publication=read(ROOT/'reports/publication/manifest.json')
assert publication['publication_id']==pid
# This initial report uses a fully verified publication. Do not silently reuse
# its COMPLETE banner for a future degraded publication.
assert all(q['status']=='COMPLETE' for q in publication['quality_entities'].values())
assert all(q['status']=='COMPLETE' for q in manifest['quality_metrics'].values())
assert manifest['external_warning_count']==12
bundle=ROOT/'reports/powerbi/imports'/pid
OUT=ROOT/'powerbi';OUT.mkdir(exist_ok=True)
DATA=OUT/'data'/pid;DATA.mkdir(parents=True,exist_ok=True)
def rows(e):
    p=bundle/(e+'.csv');spec=next(t for t in manifest['tables'] if t['entity']==e)
    assert hashlib.sha256(p.read_bytes()).hexdigest()==spec['sha256']
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def writecsv(name,rs,cols=None):
    p=DATA/(name+'.csv')
    with p.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=cols or list(rs[0]));w.writeheader();w.writerows(rs)
    return p

# Grain-safe presentation enrichments; identities include engine and source.
links={(r['engine'],r['service_source_system'],r['service_type'],r['service_id']):(r['engine'],r['booking_source_system'],r['booking_id']) for r in rows('L03')}
cross=defaultdict(lambda: [Decimal(0),Decimal(0),0])
for e,typ,idcol,valcol,ix in [('F04','TICKET_ORDER','ticket_order_id','net_ticket_vnd',0),('F05','RENTAL','rental_id','agreed_vnd',1)]:
    for r in rows(e):
        if e=='F05' and r['status']!='COMPLETED':continue
        key=links.get((r['engine'],r['source_system'],typ,r[idcol]))
        if key:
            v=Decimal(r[valcol]);cross[key][ix]+=v;cross[key][2]=max(cross[key][2],int(v>0))
f01=rows('F01')
for r in f01:
    t,v,b=cross[(r['engine'],r['source_system'],r['booking_id'])]
    r.update(cross_ticket=str(t),cross_rental=str(v),cross_bought=b)
writecsv('F01',f01)
receipts=defaultdict(lambda:[Decimal(0)]*4)
for r in rows('F13'):
    if int(r['received_date_key'])>20251231:continue
    v=receipts[(r['engine'],r['source_system'],r['purchase_line_id'])]
    for i,c in enumerate(['accepted_qty','rejected_qty','late_accepted_qty']):v[i]+=Decimal(r[c])
    if int(r['received_date_key'])<=int(r['expected_date_key']):v[3]+=Decimal(r['accepted_qty'])
f12=rows('F12')
for r in f12:
    a,b,c,d=receipts[(r['engine'],r['source_system'],r['purchase_line_id'])]
    r.update(received_accepted=str(a),received_rejected=str(b),received_late=str(c),otif=int(d>=Decimal(r['ordered_qty'])))
writecsv('F12',f12)

contract=read(ROOT/'config/kpi_contract_v1.json')
metrics={m['id']:m for g in contract['requirements'] for m in g['metrics']}
writecsv('KPI',[{'id':k,'group':k[:3],'label':k+' | '+v['name'],'unit':v['unit']} for k,v in metrics.items()])
writecsv('Engine',[{'engine':'oracle'},{'engine':'iceberg'}])
periods=[{'period':'01 | Toàn kỳ 2024–2025','start_key':20240101,'end_key':20260101}]
for y in [2024,2025]:
    periods.append({'period':f'{y} | Cả năm','start_key':y*10000+101,'end_key':(y+1)*10000+101})
    for m in range(1,13):periods.append({'period':f'{y}-{m:02}','start_key':y*10000+m*100+1,'end_key':y*10000+(m+1)*100+1 if m<12 else (y+1)*10000+101})
periods.append({'period':'2024-02-01 | Một ngày, kiểm tra tồn chuyển kỳ','start_key':20240201,'end_key':20240202})
writecsv('Period',periods)
writecsv('QA',[{'scenario':x} for x in ['COMPLETE','PARTIAL','UNAVAILABLE','ZERO_DENOMINATOR']])

tables=[];relationships=[]
def table(name,cols,path,hidden=False):
    # Blank CSV fields are converted to null before numeric/date conversion.
    casts=[];columns=[]
    for c,t in cols:
        typ='int64' if t in ('INT','BIGINT') else 'decimal' if t.startswith('DECIMAL') else 'dateTime' if t=='DATE' else 'string'
        mt={'int64':'Int64.Type','decimal':'Currency.Type','dateTime':'type date','string':'type text'}[typ]
        casts.append('{"'+c+'", '+mt+'}')
        columns.append(dict(name=c,dataType=typ,sourceColumn=c,summarizeBy='none'))
    expr='let\n Source = Csv.Document(File.Contents("'+str(path).replace('"','""')+'"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),\n Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),\n Nulls = Table.ReplaceValue(Headers,"",null,Replacer.ReplaceValue,Table.ColumnNames(Headers)),\n Types = Table.TransformColumnTypes(Nulls, {'+', '.join(casts)+'}, "en-US")\nin Types'
    tables.append(dict(name=name,isHidden=hidden,columns=columns,partitions=[dict(name=name,mode='import',source=dict(type='m',expression=expr))]))
for spec in manifest['tables']:
    e=spec['entity'];cols=[(c['name'],c['spark_sql_type']) for c in spec['columns']]
    if not e.startswith('D'):cols=[('engine','STRING')]+cols
    if e=='F01':cols += [('cross_ticket','DECIMAL'),('cross_rental','DECIMAL'),('cross_bought','INT')]
    if e=='F12':cols += [(x,'DECIMAL') for x in ['received_accepted','received_rejected','received_late']]+[('otif','INT')]
    table(e,cols,DATA/(e+'.csv') if e in ('F01','F12') else bundle/spec['filename'],e.startswith(('F','L')) or e=='D01')
    if not e.startswith('D'):
        relationships.append(dict(name=e+'_Engine',fromTable=e,fromColumn='engine',toTable='Engine',toColumn='engine'))
        for c in spec['columns']:
            ref=c.get('references')
            if not ref:continue
            d,pk=ref.split('.')
            if d in ('D01','D07','D08') or e in ('F04','F05'):continue
            if e=='F07' and c['name']=='booking_hotel_key':continue
            relationships.append(dict(name=e+'_'+c['name'],fromTable=e,fromColumn=c['name'],toTable=d,toColumn=pk))
for name,cols in [('Engine',[('engine','STRING')]),('Period',[('period','STRING'),('start_key','INT'),('end_key','INT')]),('KPI',[(x,'STRING') for x in ['id','group','label','unit']]),('QA',[('scenario','STRING')])]:table(name,cols,DATA/(name+'.csv'))
measures=[]
def measure(name,expr,fmt=None,hidden=False):
    # KPI is a DAX keyword; all references to the catalogue table must be quoted.
    expr=expr.replace('KPI[',"'KPI'[").replace('VAR id=','VAR metricId=').replace('SWITCH(id,','SWITCH(metricId,')
    v=dict(name=name,expression=expr,isHidden=hidden)
    if fmt:v['formatString']=fmt
    measures.append(v)
def calc(e,col,day,extra='',lo='s',hi='e'):
    return 'VAR s = SELECTEDVALUE(Period[start_key],20240101) VAR e = SELECTEDVALUE(Period[end_key],20260101) VAR eng = SELECTEDVALUE(Engine[engine],"oracle") RETURN COALESCE(CALCULATE('+col+', Engine[engine]=eng, '+e+'['+day+'] >= '+lo+', '+e+'['+day+'] < '+hi+extra+'),0)'
def summed(e,c,day,extra='',**kw):return calc(e,'SUM('+e+'['+c+'])',day,extra,**kw)
raw={}
def rawmetric(mid,n,d='1'):raw[mid]=(n,d)
stay=summed('F03','occupied_night','service_date_key');available=summed('F02','available_day','date_key')
bookingextra=', KEEPFILTERS(TREATAS(SELECTCOLUMNS(L01,"source",L01[source_system],"id",L01[booking_id]),F01[source_system],F01[booking_id]))'
# Only apply the room bridge when room type is explicitly filtered; otherwise
# bookings with no booking-room rows must remain in the arrival cohort.
def booking(count,extra=''):
    base=calc('F01',count,'arrival_date_key',extra)
    filtered=calc('F01',count,'arrival_date_key',extra+bookingextra)
    return 'IF(ISFILTERED(D04[room_type]),('+filtered+'),('+base+'))'
rawmetric('B01.01',stay);rawmetric('B01.02',available);rawmetric('B01.03',stay,available)
for mid,status in [('B01.04','CANCELLED'),('B01.05','NO_SHOW')]:rawmetric(mid,booking('COUNTROWS(F01)',', F01[status]="'+status+'"'),booking('COUNTROWS(F01)'))
def completed(c):return summed('F01',c,'departure_date_key',', F01[status]="COMPLETED"')
for i,c in enumerate(['gross_vnd','customer_due_vnd','company_share_vnd','partner_share_vnd','commission_vnd'],1):rawmetric(f'B02.{i:02}',completed(c))
rawmetric('B02.06','('+completed('gross_vnd')+')-('+completed('company_share_vnd')+')-('+completed('commission_vnd')+')')
rawmetric('B03.01',completed('cross_bought'));rawmetric('B03.02',completed('cross_bought'),calc('F01','COUNTROWS(F01)','departure_date_key',', F01[status]="COMPLETED"'))
rawmetric('B03.03',completed('cross_ticket'));rawmetric('B03.04',completed('cross_rental'));rawmetric('B03.05','('+completed('customer_due_vnd')+')+('+completed('cross_ticket')+')+('+completed('cross_rental')+')')
eligible=summed('F06','eligible_covers','service_date_key');redeemed=summed('F06','redeemed_covers','service_date_key')
cost=summed('F08','ingredient_cost_vnd','service_date_key',', KEEPFILTERS(D10[meal_code] IN {"BREAKFAST","DINNER"})')
actual=summed('F08','actual_covers','service_date_key',', KEEPFILTERS(D10[meal_code] IN {"BREAKFAST","DINNER"})')
for mid,n,d in [('B04.01',eligible,'1'),('B04.02',redeemed,'1'),('B04.03',redeemed,eligible),('B04.04',summed('F07','net_vnd','service_date_key'),'1'),('B04.05','('+summed('F07','covers','service_date_key')+')+('+redeemed+')','1'),('B04.06',cost,'1'),('B04.07',cost,actual),('B04.08',summed('F07','rating_sum','service_date_key'),summed('F07','rating_count','service_date_key'))]:rawmetric(mid,n,d)
adm=summed('F09','admission_count','admission_date_key');cap=summed('F10','available_capacity','date_key');rented=summed('F11','rented_day','date_key');ready=summed('F11','available_day','date_key')
for i,n,d in [(1,adm,'1'),(2,cap,'1'),(3,adm,cap),(4,rented,'1'),(5,ready,'1'),(6,rented,ready)]:rawmetric(f'B05.{i:02}',n,d)
def due(c):return summed('F12',c,'expected_date_key',', F12[expected_date_key]<=20251231')
ordered=due('ordered_qty');accepted=due('received_accepted');rejected=due('received_rejected')
for i,n,d in [(1,ordered,'1'),(2,accepted,'1'),(3,rejected,'1'),(4,due('received_late'),'1'),(5,accepted,ordered),(6,rejected,'('+accepted+')+('+rejected+')'),(7,due('otif'),calc('F12','COUNTROWS(F12)','expected_date_key',', F12[expected_date_key]<=20251231'))]:rawmetric(f'B06.{i:02}',n,d)
opening=summed('F14','signed_qty','movement_date_key',lo='1',hi='s');closing=summed('F14','signed_qty','movement_date_key',lo='1')
wasteval=calc('F14','SUMX(F14,F14[waste_qty]*F14[unit_price_vnd])','movement_date_key')
availval='('+calc('F14','SUMX(F14,F14[signed_qty]*F14[unit_price_vnd])','movement_date_key',lo='1',hi='s')+')+('+calc('F14','SUMX(F14,F14[in_qty]*F14[unit_price_vnd])','movement_date_key')+')'
for i,n,d in [(1,opening,'1'),(2,closing,'1'),(3,summed('F14','use_qty','movement_date_key'),'1'),(4,summed('F14','waste_qty','movement_date_key'),'1'),(5,wasteval,'1'),(6,wasteval,availval)]:rawmetric(f'B07.{i:02}',n,d)
blocked=summed('F02','blocked_day','date_key')
for i,n,d in [(1,summed('F16','cost_vnd','end_date_key',', F16[status]="COMPLETED"'),'1'),(2,blocked,'1'),(3,available,'1'),(4,blocked,summed('F02','inventory_day','date_key'))]:rawmetric(f'B08.{i:02}',n,d)

for mid,(n,d) in raw.items():
    measure(mid+' n',n,hidden=True);measure(mid+' d',d,hidden=True)
    bad=[]
    for key,(dim,col) in DOMAINS.items():
        if key not in ALLOWED[mid]:bad.append(f'ISFILTERED({dim}[{col}])')
    bad += ['ISFILTERED(F14[usage_area])'] if 'usage_area' not in ALLOWED[mid] else []
    bad += ['ISFILTERED(F16[work_type])'] if 'work_type' not in ALLOWED[mid] else []
    invalid=' || '.join(bad) or 'FALSE()'
    item=(mid[:3]=='B06' and int(mid[-2:])<=6) or (mid[:3]=='B07' and int(mid[-2:])<=4)
    meal='FALSE()'
    if mid[:3]=='B04':
        if int(mid[-2:])<=3:meal='ISFILTERED(D10[meal_code]) && NOT(SELECTEDVALUE(D10[meal_code]) IN {"BREAKFAST"})'
        if int(mid[-2:]) in (6,7):meal='ISFILTERED(D10[meal_code]) && NOT(SELECTEDVALUE(D10[meal_code]) IN {"BREAKFAST","DINNER"})'
    quality=manifest['quality_metrics'][mid]['status']
    # Export currently has no scoped stock-history issues. Fail build if this
    # assumption changes instead of silently treating a degraded batch as full.
    assert not manifest.get('quality_scope'), 'Implement scoped quality propagation before rebuilding'
    warn='SWITCH(TRUE(), ISFILTERED(Engine[engine]) && NOT HASONEVALUE(Engine[engine]),"CHỌN MỘT ENGINE", ISFILTERED(Period[period]) && NOT HASONEVALUE(Period[period]),"CHỌN MỘT KỲ", '+invalid+',"BỘ LỌC KHÔNG ÁP DỤNG", '+('NOT HASONEVALUE(D15[item_id])' if item else 'FALSE()')+',"CHỌN MỘT MẶT HÀNG", '+meal+',"BỮA ĂN NGOÀI PHẠM VI", "'+quality+'")'
    measure(mid+' state',warn,hidden=True)
    expr='VAR state = ['+mid+' state] RETURN IF(state IN {"COMPLETE","PARTIAL"}, '+('['+mid+' n]' if d=='1' else 'DIVIDE(CONVERT(['+mid+' n],DOUBLE),CONVERT(['+mid+' d],DOUBLE))')+')'
    fmt='0.00%' if metrics[mid]['unit'].startswith('%') else '#,0.00' if mid=='B04.08' or mid.startswith(('B06','B07')) else '#,0'
    measure(mid,expr,fmt)

def switch(suffix):return 'SWITCH(SELECTEDVALUE(KPI[id]),'+','.join('"'+m+'",['+m+suffix+']' for m in metrics)+')'
measure('Giá trị KPI',switch(''))
measure('Giá trị hiển thị','VAR v=[Giá trị KPI] VAR id=SELECTEDVALUE(KPI[id]) RETURN IF(NOT HASONEVALUE(KPI[id]),BLANK(),IF(ISBLANK(v),"—",SWITCH(id,'+','.join('"'+m+'",FORMAT(v,"'+('0.00%' if metrics[m]['unit'].startswith('%') else '#,0.00' if m=='B04.08' or m.startswith(('B06','B07')) else '#,0')+'")' for m in metrics)+')))')
measure('Trạng thái KPI','VAR q='+switch(' state')+' VAR d='+switch(' d')+' RETURN IF(HASONEVALUE(KPI[id]),IF(q IN {"COMPLETE","PARTIAL"} && d=0,"KHÔNG CÓ MẪU SỐ",q),"Không cộng KPI khác đơn vị")')
measure('Nguồn và kỳ','"CompanyE | " & SELECTEDVALUE(Engine[engine],"oracle (mặc định)") & " | " & SELECTEDVALUE(Period[period],"Toàn kỳ 2024–2025")')
measure('Cảnh báo báo cáo','"12 cảnh báo đối soát nguồn bên ngoài • Dữ liệu tổng hợp đang COMPLETE. B06: ngày đánh giá cố định 31/12/2025. Dấu —: xem cột trạng thái; không thay bằng 0."')
measure('Publication','"'+pid+' | Import cố định; không phải dữ liệu trực tiếp"')
measure('QA giá trị','SWITCH(SELECTEDVALUE(QA[scenario],"COMPLETE"),"COMPLETE",DIVIDE(40,100),"PARTIAL",DIVIDE(30,80),"UNAVAILABLE",BLANK(),"ZERO_DENOMINATOR",DIVIDE(0,0))','0.00%')
measure('QA cảnh báo','SWITCH(SELECTEDVALUE(QA[scenario],"COMPLETE"),"COMPLETE","KIỂM THỬ: đầy đủ 40/100", "PARTIAL","KIỂM THỬ: THIẾU DỮ LIỆU — vẫn báo cáo 30/80 phần hợp lệ", "UNAVAILABLE","KIỂM THỬ: KHÔNG KHẢ DỤNG — không hiển thị số 0", "ZERO_DENOMINATOR","KIỂM THỬ: MẪU SỐ 0 — kết quả trống")')
next(t for t in tables if t['name']=='KPI')['measures']=measures
model=dict(name='CompanyE',compatibilityLevel=1600,model=dict(culture='en-US',defaultPowerBIDataSourceVersion='powerBI_V3',tables=tables,relationships=relationships,annotations=[dict(name='PBI_QueryOrder',value=json.dumps([t['name'] for t in tables]))]))
if '--report-only' not in sys.argv:
    save(OUT/'CompanyE.SemanticModel/model.bim',model)
    save(OUT/'CompanyE.SemanticModel/definition.pbism',{'version':'1.0','settings':{}})
save(OUT/'CompanyE.pbip',{'version':'1.0','artifacts':[{'report':{'path':'CompanyE.Report'}}],'settings':{'enableAutoRecovery':True}})
save(OUT/'CompanyE.Report/definition.pbir',{'version':'4.0','datasetReference':{'byPath':{'path':'../CompanyE.SemanticModel'}}})

BASE='https://developer.microsoft.com/json-schemas/fabric/item/report/definition/'
R=OUT/'CompanyE.Report/definition'
save(R/'version.json',{'$schema':BASE+'versionMetadata/1.0.0/schema.json','version':'2.0.0'})
save(R/'report.json',{'$schema':BASE+'report/3.0.0/schema.json','themeCollection':{'baseTheme':{'name':'CY24SU06','reportVersionAtImport':{'visual':'2.0.0','page':'2.0.0','report':'3.0.0'},'type':'SharedResources'}}})
def lit(v):return {'expr':{'Literal':{'Value':"'"+v.replace("'","''")+"'" if isinstance(v,str) else str(v).lower() if isinstance(v,bool) else str(v)+'D'}}}
def field(t,c,ism=False):return {('Measure' if ism else 'Column'):{'Expression':{'SourceRef':{'Entity':t}},'Property':c}}
def proj(t,c,ism=False,label=None):return dict(field=field(t,c,ism),queryRef=t+'.'+c,displayName=label or c)
def visual(page,name,typ,x,y,w,h,roles,title=None,objects=None):
    if name=='publication':h=85
    if name in ('warning','publication'):
        typ='tableEx'
        objects={'values':[{'properties':{'fontSize':lit(14 if name=='warning' else 11),'wordWrap':lit(True)}}], 'columnHeaders':[{'properties':{'fontSize':lit(11)}}], 'total':[{'properties':{'totals':lit(False)}}]}
    elif typ=='tableEx':
        objects={'values':[{'properties':{'fontSize':lit(14),'wordWrap':lit(True)}}], 'columnHeaders':[{'properties':{'fontSize':lit(13),'wordWrap':lit(True)}}], 'grid':[{'properties':{'rowPadding':lit(8)}}], 'total':[{'properties':{'fontSize':lit(14)}}]}
    elif typ=='card':
        objects=objects or {'labels':[{'properties':{'fontSize':lit(24 if name=='heading' else 38)}}], 'categoryLabels':[{'properties':{'show':lit(False)}}]}
    v={'visualType':typ,'query':{'queryState':{r:{'projections':p} for r,p in roles.items()}}}
    if title:v['visualContainerObjects']={'title':[{'properties':{'show':lit(True),'text':lit(title),'fontSize':lit(12)}}]}
    if objects:v['objects']=objects
    save(R/'pages'/page/'visuals'/name/'visual.json',{'$schema':BASE+'visualContainer/2.0.0/schema.json','name':name,'position':dict(x=x,y=y,z=1,width=w,height=h),'visual':v})
def slicer(page,name,t,c,x,y,w=200,h=105):
    label={'engine':'Nguồn dữ liệu','period':'Kỳ báo cáo','site_id':'Địa điểm','hotel_id':'Khách sạn','item_id':'Mặt hàng','meal_code':'Bữa ăn','channel_code':'Kênh đặt phòng','room_type':'Loại phòng','centre_id':'Trung tâm giải trí','scenario':'Tình huống kiểm thử'}.get(c,c)
    visual(page,name,'slicer',x,y,w,h,{'Values':[proj(t,c,label=label)]},None,{'data':[{'properties':{'mode':lit('Dropdown')}}], 'items':[{'properties':{'textSize':lit(13)}}], 'header':[{'properties':{'textSize':lit(12)}}]})
def page(name,label):save(R/'pages'/name/'page.json',{'$schema':BASE+'page/2.0.0/schema.json','name':name,'displayName':label,'displayOption':'FitToPage','width':1280,'height':800})
order=[]
page('overview','00 | Tổng quan');order.append('overview')
visual('overview','heading','card',20,5,1240,65,{'Values':[proj('KPI','Nguồn và kỳ',True)]})
slicer('overview','engine','Engine','engine',20,75)
slicer('overview','period','Period','period',235,75,260)
slicer('overview','site','D02','site_id',515,75)
slicer('overview','hotel','D03','hotel_id',735,75)
visual('overview','occupancy','tableEx',20,195,1240,345,{'Values':[proj('D02','site_id',label='Địa điểm'),proj('KPI','B01.01',True,'Đêm thực ở'),proj('KPI','B01.02',True,'Đêm khả dụng'),proj('KPI','B01.03',True,'Công suất'),proj('KPI','B02.06',True,'Giá trị giữ lại (VND)')]},'Công suất và giá trị theo địa điểm — tổng tỷ lệ được tính lại')
visual('overview','warning','card',20,560,1240,100,{'Values':[proj('KPI','Cảnh báo báo cáo',True)]},None,{'labels':[{'properties':{'fontSize':lit(14)}}]})
visual('overview','publication','card',20,680,1240,55,{'Values':[proj('KPI','Publication',True)]},None,{'labels':[{'properties':{'fontSize':lit(12)}}]})
for g in contract['requirements']:
    name=g['id'];order.append(name);page(name,name+' | '+g['name'])
    visual(name,'heading','card',20,5,1240,55,{'Values':[proj('KPI','Nguồn và kỳ',True)]})
    slicer(name,'engine','Engine','engine',20,65,170)
    slicer(name,'period','Period','period',205,65,250)
    slicer(name,'site','D02','site_id',470,65,150)
    if name!='B05':slicer(name,'hotel','D03','hotel_id',635,65,180)
    extra={'B01':('D04','room_type'),'B02':('D05','channel_code'),'B03':('D05','channel_code'),'B04':('D10','meal_code'),'B05':('D11','centre_id'),'B06':('D15','item_id'),'B07':('D15','item_id'),'B08':('D04','room_type')}[name]
    slicer(name,'detail',*extra,835,65,220)
    # Each group has its own disconnected KPI catalogue, restricted by a page filter.
    pg=read(R/'pages'/name/'page.json')
    pg['filterConfig']={'filters':[{'name':name+'_filter','field':field('KPI','group'),'type':'Categorical','filter':{'Version':2,'From':[{'Name':'k','Entity':'KPI','Type':0}],'Where':[{'Condition':{'In':{'Expressions':[{'Column':{'Expression':{'SourceRef':{'Source':'k'}},'Property':'group'}}],'Values':[[{'Literal':{'Value':"'"+name+"'"}}]]}}}]}}]}
    save(R/'pages'/name/'page.json',pg)
    visual(name,'metrics','tableEx',20,195,1240,345,{'Values':[proj('KPI','label',label='KPI'),proj('KPI','Giá trị hiển thị',True,'Giá trị'),proj('KPI','unit',label='Đơn vị'),proj('KPI','Trạng thái KPI',True,'Trạng thái')]},g['name'])
    visual(name,'warning','card',20,570,1240,100,{'Values':[proj('KPI','Cảnh báo báo cáo',True)]},None,{'labels':[{'properties':{'fontSize':lit(14)}}]})
    visual(name,'publication','card',20,695,1240,50,{'Values':[proj('KPI','Publication',True)]},None,{'labels':[{'properties':{'fontSize':lit(12)}}]})
page('qa','QA | Kiểm thử cảnh báo');order.append('qa')
slicer('qa','scenario','QA','scenario',30,40,460,200)
visual('qa','value','card',520,40,700,200,{'Values':[proj('KPI','QA giá trị',True)]},'DỮ LIỆU GIẢ LẬP KIỂM THỬ — không phải số liệu CompanyE')
visual('qa','warning','card',30,290,1190,160,{'Values':[proj('KPI','QA cảnh báo',True)]},None,{'labels':[{'properties':{'fontSize':lit(18)}}]})
save(R/'pages/pages.json',{'$schema':BASE+'pagesMetadata/1.0.0/schema.json','pageOrder':order,'activePageName':'overview'})
save(ROOT/'reports/powerbi/build.json',dict(publication_id=pid,measures=len(measures),kpis=len(raw),tables=len(tables),relationships=len(relationships),assessment='2025-12-31',project=str(OUT/'CompanyE.pbip'),files=[dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in DATA.glob('*.csv')]))
print('BUILT',len(tables),'tables',len(raw),'KPI',OUT/'CompanyE.pbip')
