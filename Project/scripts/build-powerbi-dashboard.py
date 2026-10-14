"""Upgrade the certified PBIP presentation; preserve every existing KPI expression.

Close Desktop before running. A first-run backup preserves the previous report,
model and verification records. No published data, seeds, or ETL is modified.
"""
from pathlib import Path
from datetime import datetime, timezone
import copy, csv, hashlib, json, shutil

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'powerbi'
REPORT = ROOT / 'reports/powerbi/dashboard'
REPORT.mkdir(parents=True, exist_ok=True)
BACKUP = REPORT / 'before-dashboard'
MODEL = OUT / 'CompanyE.SemanticModel/model.bim'
DEFINITION = OUT / 'CompanyE.Report/definition'
BASE = 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf8')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
export = read(ROOT/'reports/powerbi/export.json')
assert export['publication_id']=='pub_3f41f8fafa4c913187af2cc3'
assert export['external_warning_count']==12
assert all(q['status']=='COMPLETE' for q in export['quality_metrics'].values())
assert not export.get('quality_scope'), 'Dashboard quality footer must be adapted for a different publication.'
if not BACKUP.exists():
    BACKUP.mkdir()
    shutil.copytree(OUT / 'CompanyE.Report', BACKUP / 'CompanyE.Report')
    shutil.copy2(MODEL, BACKUP / 'model.bim')
    for name in ['ui-verification.json', 'dax-verification.json', 'static-validation.json']:
        shutil.copy2(ROOT / 'reports/powerbi' / name, BACKUP / name)

model = read(MODEL)
original = read(BACKUP / 'model.bim')
kpi = next(t for t in model['model']['tables'] if t['name'] == 'KPI')
old = {m['name']: m for m in next(t for t in original['model']['tables'] if t['name']=='KPI')['measures']}
current = {m['name']: m for m in kpi['measures']}
for name, m in old.items():
    assert current[name]['expression'] == m['expression'], 'Original measure changed: ' + name
new = {}
def measure(name, expr, fmt=None):
    result = dict(name=name, expression=expr, displayFolder='Dashboard')
    if fmt: result['formatString'] = fmt
    new[name] = result
    return name
def textmeasure(name, text): return measure('DB '+name, '"'+text.replace('"','""')+'"')
def money(mid):
    return measure('DB '+mid+' tỷ', 'DIVIDE(CONVERT(['+mid+'],DOUBLE),1000000000.0)', '#,0.00')

# A separate month axis prevents the Period slicer from being mistaken for a
# grouping dimension. Only complete months within the chosen [S,E) are shown.
month_file = OUT / 'data/dashboard-months.csv'
with month_file.open('w', encoding='utf8', newline='') as f:
    writer=csv.DictWriter(f,fieldnames=['month','start_key','end_key']);writer.writeheader()
    for y in (2024,2025):
        for m in range(1,13):
            writer.writerow(dict(month=f'{y}-{m:02}',start_key=y*10000+m*100+1,end_key=y*10000+(m+1)*100+1 if m<12 else (y+1)*10000+101))
month_table=dict(name='ChartMonth',columns=[dict(name=n,dataType=t,sourceColumn=n,summarizeBy='none') for n,t in [('month','string'),('start_key','int64'),('end_key','int64')]],partitions=[dict(name='ChartMonth',mode='import',source=dict(type='m',expression='let Source=Csv.Document(File.Contents("'+str(month_file)+'"),[Delimiter=",",Encoding=65001,QuoteStyle=QuoteStyle.Csv]), Headers=Table.PromoteHeaders(Source,[PromoteAllScalars=true]), Types=Table.TransformColumnTypes(Headers,{{"month",type text},{"start_key",Int64.Type},{"end_key",Int64.Type}}) in Types'))])
model['model']['tables']=[t for t in model['model']['tables'] if t['name']!='ChartMonth']+[month_table]
def trend(mid, scaled=False):
    name='DB '+mid+' tháng'
    base=money(mid) if scaled else mid
    expr='''VAR s=SELECTEDVALUE(Period[start_key],20240101)
VAR e=SELECTEDVALUE(Period[end_key],20260101)
VAR ms=SELECTEDVALUE(ChartMonth[start_key])
VAR me=SELECTEDVALUE(ChartMonth[end_key])
VAR validPeriod=NOT ISFILTERED(Period[period]) || HASONEVALUE(Period[period])
RETURN IF(validPeriod && NOT ISBLANK(ms) && ms>=s && me<=e,
CALCULATE(['''+base+'''],REMOVEFILTERS(Period),TREATAS({ms},Period[start_key]),TREATAS({me},Period[end_key])))'''
    return measure(name,expr,'#,0.00' if scaled else old[mid].get('formatString','#,0'))

NAVY='#142C45'; TEAL='#007F86'; GOLD='#C37D24'; BG='#F2F5F8'; INK='#20364C'; MUTED='#566C80'; WHITE='#FFFFFF'
def lit(v):
    return {'expr':{'Literal':{'Value':"'"+v.replace("'","''")+"'" if isinstance(v,str) else str(v).lower() if isinstance(v,bool) else str(v)+'D'}}}
def color(s): return {'solid':{'color':lit(s)}}
def obj(**props): return [{'properties':props}]
def field(t,c,ism=False): return {('Measure' if ism else 'Column'):{'Expression':{'SourceRef':{'Entity':t}},'Property':c}}
def proj(t,c,ism=False,label=None): return dict(field=field(t,c,ism),queryRef=t+'.'+c,displayName=label or c)
def filt(t,c,values,name='scope'):
    return {'name':name,'field':field(t,c),'type':'Categorical','filter':{'Version':2,'From':[{'Name':'s','Entity':t,'Type':0}],'Where':[{'Condition':{'In':{'Expressions':[{'Column':{'Expression':{'SourceRef':{'Source':'s'}},'Property':c}}],'Values':[[{'Literal':{'Value':"'"+str(v).replace("'","''")+"'"}}] for v in values]}}}]}}

# Construct into a staging directory; replace only this exact report definition.
STAGE = REPORT / 'definition-staging'
if STAGE.exists():
    assert STAGE.resolve() == (ROOT/'reports/powerbi/dashboard/definition-staging').resolve()
    shutil.rmtree(STAGE)
STAGE.mkdir()
pages={}; visuals={}
def visual(page,name,typ,x,y,w,h,roles,title=None,objects=None,bg=WHITE,filters=None):
    container={'background':obj(show=lit(True),color=color(bg),transparency=lit(0)),
               'border':obj(show=lit(False)),
               'title':obj(show=lit(bool(title)),text=lit(title or ''),fontSize=lit(15),fontColor=color(INK),bold=lit(True))}
    v={'visualType':typ,'query':{'queryState':{r:{'projections':p} for r,p in roles.items()}},'visualContainerObjects':container}
    if objects: v['objects']=objects
    data={'$schema':BASE+'visualContainer/2.0.0/schema.json','name':name,'position':dict(x=x,y=y,z=len(visuals[page])+1,width=w,height=h),'visual':v}
    if filters:data['filterConfig']={'filters':filters}
    save(STAGE/'pages'/page/'visuals'/name/'visual.json',data);visuals[page].append(name)
    return data
def card(page,name,mid,title,x,y,w,h=104,dark=False,size=32):
    visual(page,name,'card',x,y,w,h,{'Values':[proj('KPI',mid,True)]},title,
           {'labels':obj(fontSize=lit(size),color=color(WHITE if dark else TEAL),labelDisplayUnits=lit(1)),
            'categoryLabels':obj(show=lit(False))},bg=NAVY if dark else WHITE)
    if dark:
        p=STAGE/'pages'/page/'visuals'/name/'visual.json';v=read(p)
        v['visual']['visualContainerObjects']['title'][0]['properties']['fontColor']=color(WHITE);save(p,v)
def table(page,name,roles,x,y,w,h,title=None,small=False,bg=WHITE):
    visual(page,name,'tableEx',x,y,w,h,{'Values':roles},title,
      {'values':obj(fontSize=lit(12 if small else 14),fontColor=color(INK),wordWrap=lit(True)),
       'columnHeaders':obj(fontSize=lit(12 if small else 13),fontColor=color(MUTED),wordWrap=lit(True)),
       'grid':obj(rowPadding=lit(4)), 'total':obj(totals=lit(not small),fontSize=lit(13))},bg=bg)
def textbox(page,name,text,y,height,bg=BG):
    paragraphs=[{'textRuns':[{'value':text,'textStyle':{'fontFamily':'Segoe UI','fontSize':'12pt','color':INK}}]}]
    data={'$schema':BASE+'visualContainer/2.0.0/schema.json','name':name,
          'position':dict(x=20,y=y,z=len(visuals[page])+1,width=1400,height=height),
          'visual':{'visualType':'textbox','objects':{'general':obj(paragraphs=paragraphs)},
          'visualContainerObjects':{'background':obj(show=lit(True),color=color(bg),transparency=lit(0))}}}
    save(STAGE/'pages'/page/'visuals'/name/'visual.json',data);visuals[page].append(name)
def slicer(page,name,t,c,label,x,w,default=None):
    objects={'data':obj(mode=lit('Dropdown')),'items':obj(textSize=lit(15)),'header':obj(textSize=lit(13)),
             'selection':obj(singleSelect=lit(True))}
    if default: objects['general']=obj(filter={'filter':filt(t,c,[default])['filter']})
    visual(page,name,'slicer',x,85,w,72,{'Values':[proj(t,c,label=label)]},objects=objects)
def chart(page,name,typ,t,c,mids,labels,title,x,w):
    roles={'Category':[proj(t,c,label='Tháng' if t=='ChartMonth' else 'Nhóm so sánh')], 'Y':[proj('KPI',m,True,l) for m,l in zip(mids,labels)]}
    objects={'categoryAxis':obj(show=lit(True),showAxisTitle=lit(False),fontSize=lit(13),labelColor=color(MUTED)),
             'valueAxis':obj(show=lit(True),showAxisTitle=lit(False),fontSize=lit(12),labelColor=color(MUTED)),
             'legend':obj(show=lit(len(mids)>1),position=lit('Top'),fontSize=lit(12)),
             'dataPoint':[{'properties':{'defaultColor':color(TEAL)}}],
             'labels':obj(show=lit(typ!='lineChart'),fontSize=lit(12),labelDisplayUnits=lit(1)),
             'lineStyles':obj(strokeWidth=lit(3),showMarker=lit(True),markerSize=lit(4))}
    if len(mids)>1:
        objects['dataPoint']=[{'selector':{'metadata':'KPI.'+m},'properties':{'fill':color(col)}} for m,col in zip(mids,[TEAL,GOLD])]
    filters=None
    if t=='D02': filters=[filt('D02','site_id',['DL','DN','PQ','SP'])]
    if t=='D03': filters=[filt('D03','hotel_id',[s+'-'+star for s in ['DL','DN','PQ','SP'] for star in ['3','5']])]
    v=visual(page,name,typ,x,282,w,244 if page=='overview' else 276,roles,title,objects,filters=filters)
    v['visual']['query']['sortDefinition']={'sort':[{'field':field(t,c),'direction':'Ascending'}],'isDefaultSort':True}
    save(STAGE/'pages'/page/'visuals'/name/'visual.json',v)

contract=read(ROOT/'config/kpi_contract_v1.json')
groups={g['id']:g for g in contract['requirements']}
titles={'overview':'COMPANY E  /  ĐIỀU HÀNH TOÀN CHUỖI',
        'B01':'01  /  LƯU TRÚ','B02':'02  /  KÊNH BÁN & KHUYẾN MÃI','B03':'03  /  BÁN CHÉO DỊCH VỤ',
        'B04':'04  /  BUFFET & NHÀ HÀNG','B05':'05  /  GIẢI TRÍ & PHƯƠNG TIỆN',
        'B06':'06  /  HIỆU QUẢ NHÀ CUNG CẤP','B07':'07  /  TỒN KHO & HAO HỤT','B08':'08  /  BẢO TRÌ & NGÀY PHÒNG'}
cards={
 'overview':[('B02.06','Giữ lại trước chi phí vận hành · tỷ đồng',True),('B01.03','Công suất phòng',False),('B03.02','Tỷ lệ booking mua chéo',False),('B06.07','Giao hàng OTIF',False)],
 'B01':[('B01.01','Đêm phòng thực ở',False),('B01.02','Đêm phòng khả dụng',False),('B01.03','Công suất phòng',False),('B01.04','Booking hủy',False)],
 'B02':[('B02.06','Giữ lại trước chi phí vận hành · tỷ đồng',True),('B02.03','CompanyE tài trợ giảm giá · tỷ đồng',True),('B02.04','Đối tác tài trợ giảm giá · tỷ đồng',True),('B02.05','Hoa hồng kênh bán · tỷ đồng',True)],
 'B03':[('B03.01','Booking có mua chéo',False),('B03.02','Tỷ lệ mua chéo',False),('B03.03','Giá trị vé gắn booking · tỷ đồng',True),('B03.04','Thuê xe gắn booking · tỷ đồng',True)],
 'B04':[('B04.03','Sử dụng quyền lợi buffet sáng',False),('B04.04','Ăn uống bán riêng · tỷ đồng',True),('B04.07','Nguyên liệu / lượt buffet · đồng',False),('B04.08','Điểm đánh giá / 5',False)],
 'B05':[('B05.01','Lượt sử dụng hoạt động',False),('B05.03','Sử dụng công suất giải trí',False),('B05.04','Ngày xe được thuê',False),('B05.06','Sử dụng đội xe',False)],
 'B06':[('B06.07','Đơn giao đủ và đúng hạn · OTIF',False),('B06.05','Tỷ lệ lượng nhận chấp nhận',False),('B06.06','Tỷ lệ lượng bị từ chối',False),('B06.04','Lượng nhận trễ · chọn một mặt hàng',False)],
 'B07':[('B07.01','Tồn đầu kỳ · chọn một mặt hàng',False),('B07.02','Tồn cuối kỳ · chọn một mặt hàng',False),('B07.05','Giá trị hao hụt · tỷ đồng',True),('B07.06','Tỷ lệ hao hụt theo giá trị',False)],
 'B08':[('B08.01','Chi phí bảo trì hoàn tất · tỷ đồng',True),('B08.02','Ngày phòng ngừng bán',False),('B08.03','Ngày phòng khả dụng',False),('B08.04','Tỷ trọng ngừng bán',False)]}
notes={
 'overview':'4 điểm đến • 8 khách sạn • 2 phân khúc  |  Chọn một kỳ và một nguồn dữ liệu. Số tiền là giá trị giữ lại trước chi phí vận hành, không phải lợi nhuận.',
 'B01':'Công suất = tổng đêm thực ở / tổng đêm khả dụng. Booking hủy và no-show dùng cohort ngày đến; không cộng hai chỉ tiêu vào một trạng thái.',
 'B02':'Ngày phân tích: trả phòng của booking COMPLETED. Phần đối tác tài trợ được tách riêng; giá trị giữ lại chưa trừ chi phí vận hành.',
 'B03':'Cohort theo ngày trả phòng. Dịch vụ vé/xe gắn booking được gom trước khi nối; booking không mua chéo vẫn nằm trong mẫu số.',
 'B04':'Chọn LUNCH/BAR sẽ để trống KPI buffet ngoài phạm vi. Mức giá phòng có bữa sáng không được cộng lần nữa vào doanh thu ăn uống bán riêng.',
 'B05':'Hai tỷ lệ dùng hai mẫu số riêng: công suất hoạt động và ngày xe sẵn sàng. Lượt hoạt động không phải số khách duy nhất.',
 'B06':'Chọn đúng một mặt hàng để xem số lượng và tỷ lệ lượng. OTIF tính theo dòng đặt hàng. Ngày đánh giá cố định: 31/12/2025.',
 'B07':'Chọn đúng một mặt hàng để xem tồn và số lượng. Tồn cuối là số chốt, không cộng qua tháng. Giá trị hao hụt được cộng giữa các mặt hàng.',
 'B08':'Ngày phòng khả dụng dùng cùng định nghĩa B01.02. Lọc loại phòng không áp dụng cho KPI chi phí bảo trì tài sản; bảng chi tiết sẽ báo rõ.'}
for p in titles:
    visuals[p]=[]
    pages[p]={'$schema':BASE+'page/2.0.0/schema.json','name':p,'displayName':'00 | Tổng quan' if p=='overview' else p+' | '+groups[p]['name'],
              'displayOption':'FitToPage','width':1440,'height':900,'objects':{'background':obj(color=color(BG),transparency=lit(0))}}
    if p!='overview':pages[p]['filterConfig']={'filters':[filt('KPI','group',[p],p+'_filter')]}
    card(p,'title',textmeasure(p+' title',titles[p]),None,20,8,1400,40,True,24)
    card(p,'heading','Nguồn và kỳ',None,20,48,1400,28,True,13)
    slicer(p,'engine','Engine','engine','Nguồn dữ liệu',20,170)
    slicer(p,'period','Period','period','Kỳ báo cáo',202,270)
    slicer(p,'site','D02','site_id','Điểm đến',484,180)
    if p!='B05':slicer(p,'hotel','D03','hotel_id','Khách sạn',676,220)
    extra={'B01':('D04','room_type','Loại phòng'),'B02':('D05','channel_code','Kênh đặt phòng'),
           'B03':('D05','channel_code','Kênh đặt phòng'),'B04':('D10','meal_code','Bữa ăn'),
           'B05':('D11','centre_id','Trung tâm giải trí'),'B06':('D15','item_id','Mặt hàng'),
           'B07':('D15','item_id','Mặt hàng'),'B08':('D04','room_type','Loại phòng')}.get(p)
    if extra:slicer(p,'detail',*extra,908,270,default='RICE' if p in ('B06','B07') else None)
    for i,(mid,label,scaled) in enumerate(cards[p]):card(p,'score'+str(i+1),money(mid) if scaled else mid,label,20+i*354,170,338)
    # Two charts per page: a comparable breakdown and monthly evolution.
    if p=='overview':
        chart(p,'comparison','clusteredBarChart','D02','site_id',[money('B02.06')],['Giá trị giữ lại'],'Giá trị giữ lại theo điểm đến · tỷ đồng',20,680)
        chart(p,'trend','lineChart','ChartMonth','month',[trend('B01.03')],['Công suất phòng'],'Công suất phòng theo tháng · %',716,704)
    elif p=='B01':
        chart(p,'comparison','clusteredColumnChart','D03','hotel_id',['B01.01','B01.02'],['Thực ở','Khả dụng'],'Đêm phòng theo khách sạn',20,680)
        chart(p,'trend','lineChart','ChartMonth','month',[trend('B01.03')],['Công suất'],'Công suất phòng theo tháng · %',716,704)
    elif p=='B02':
        chart(p,'comparison','clusteredBarChart','D05','channel_code',[money('B02.06')],['Giữ lại'],'Giá trị giữ lại theo kênh · tỷ đồng',20,680)
        chart(p,'trend','lineChart','ChartMonth','month',[trend('B02.06',True)],['Giữ lại'],'Giá trị giữ lại theo tháng · tỷ đồng',716,704)
    elif p=='B03':
        chart(p,'comparison','clusteredColumnChart','D03','hotel_id',['B03.02'],['Mua chéo'],'Tỷ lệ mua chéo theo khách sạn · %',20,680)
        chart(p,'trend','lineChart','ChartMonth','month',[trend('B03.02')],['Mua chéo'],'Tỷ lệ mua chéo theo tháng · %',716,704)
    elif p=='B04':
        chart(p,'comparison','clusteredBarChart','D03','hotel_id',['B04.07'],['Đồng/lượt'],'Chi phí nguyên liệu mỗi lượt buffet · đồng',20,680)
        chart(p,'trend','lineChart','ChartMonth','month',[trend('B04.04',True)],['Ăn uống bán riêng'],'Ăn uống bán riêng theo tháng · tỷ đồng',716,704)
    elif p=='B05':
        chart(p,'comparison','clusteredColumnChart','D02','site_id',['B05.03','B05.06'],['Giải trí','Đội xe'],'Sử dụng công suất theo điểm đến · %',20,680)
        chart(p,'trend','lineChart','ChartMonth','month',[trend('B05.03'),trend('B05.06')],['Giải trí','Đội xe'],'Sử dụng công suất theo tháng · %',716,704)
    elif p=='B06':
        chart(p,'comparison','clusteredBarChart','D14','supplier_id',['B06.07'],['OTIF'],'Giao đủ và đúng hạn theo nhà cung cấp · %',20,680)
        chart(p,'trend','lineChart','ChartMonth','month',[trend('B06.07')],['OTIF'],'OTIF theo tháng hẹn giao · %',716,704)
    elif p=='B07':
        chart(p,'comparison','clusteredBarChart','D03','hotel_id',['B07.02'],['Tồn cuối'],'Tồn cuối theo khách sạn · chọn một mặt hàng',20,680)
        chart(p,'trend','lineChart','ChartMonth','month',[trend('B07.02')],['Tồn cuối tháng'],'Tồn cuối từng tháng · không cộng qua thời gian',716,704)
    elif p=='B08':
        chart(p,'comparison','clusteredColumnChart','D03','hotel_id',['B08.02'],['Ngày ngừng bán'],'Ngày phòng ngừng bán theo khách sạn',20,680)
        chart(p,'trend','lineChart','ChartMonth','month',[trend('B08.04')],['Ngừng bán'],'Tỷ trọng ngừng bán theo tháng · %',716,704)
    if p=='overview':
        cols=[proj('D02','site_id',label='Điểm đến')]+[proj('KPI',m,True,l) for m,l in [('B01.01','Đêm thực ở'),('B01.02','Đêm khả dụng'),('B01.03','Công suất'),('B02.06','Giữ lại · VND'),('B03.02','Mua chéo'),('B06.07','OTIF')]]
    else:cols=[proj('KPI','label',label='KPI'),proj('KPI','Giá trị hiển thị',True,'Giá trị'),proj('KPI','unit',label='Đơn vị'),proj('KPI','Trạng thái KPI',True,'Trạng thái')]
    table(p,'metrics',cols,20,538 if p=='overview' else 570,1400,234 if p=='overview' else 202,'Chi tiết & đối soát · cuộn bảng để xem đủ KPI')
    if p=='overview':
        target=STAGE/'pages'/p/'visuals/metrics/visual.json';data=read(target)
        data['filterConfig']={'filters':[filt('D02','site_id',['DL','DN','PQ','SP'])]};save(target,data)
    footer=notes[p]+'  |  Xu hướng: chỉ các tháng trọn vẹn trong kỳ chọn. Dùng slicer để lọc; biểu đồ dùng để đối chiếu.'
    textbox(p,'guidance',footer,780,55)
    textbox(p,'warning','CHẤT LƯỢNG: COMPLETE  •  12 cảnh báo đối soát nguồn ngoài. Trống ≠ 0; xem trạng thái từng KPI.\nImport cố định · pub_3f41f8fafa4c913187af2cc3  |  B06 đánh giá đến 31/12/2025.',838,54,bg='#FFF3DC')
    # Avoid chart selections creating partially supported cross-highlights or
    # silently filtering KPI cards via the disconnected monthly axis.
    pages[p]['visualInteractions']=[dict(source=src,target=dst,type='NoFilter') for src in ['comparison','trend','metrics'] for dst in visuals[p] if src!=dst]
    save(STAGE/'pages'/p/'page.json',pages[p])

# Keep the previously verified QA page isolated and unchanged.
shutil.copytree(BACKUP/'CompanyE.Report/definition/pages/qa',STAGE/'pages/qa')
order=list(titles)+['qa']
save(STAGE/'pages/pages.json',{'$schema':BASE+'pagesMetadata/1.0.0/schema.json','pageOrder':order,'activePageName':'overview'})
save(STAGE/'version.json',{'$schema':BASE+'versionMetadata/1.0.0/schema.json','version':'2.0.0'})
report=read(BACKUP/'CompanyE.Report/definition/report.json')
save(STAGE/'report.json',report)
kpi['measures']=[m for m in kpi['measures'] if not m['name'].startswith('DB ')]+list(new.values())
save(MODEL,model)
assert DEFINITION.resolve() == (ROOT/'powerbi/CompanyE.Report/definition').resolve()
assert BACKUP.exists()
shutil.rmtree(DEFINITION)
shutil.copytree(STAGE,DEFINITION)
save(REPORT/'build.json',dict(created_at=datetime.now(timezone.utc).isoformat(),pages=10,charts=18,kpi_cards=36,
    original_measures_unchanged=len(old),added_measures=len(new),tables=len(model['model']['tables']),
    chart_month_rows=24,model_sha256=sha(MODEL),
    monthly_scope='Only full calendar months within selected Period; ratios and stocks re-evaluated per month.',
    interactions='Slicers filter. Charts/detail table do not cross-filter other visuals.',
    source_publication='pub_3f41f8fafa4c913187af2cc3'))
print('BUILT DASHBOARD:',len(new),'presentation measures, 18 charts, 36 cards; original',len(old),'measures unchanged')
