'use strict';
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let data, current;
const trends={B01:['B01.03'],B02:['B02.06'],B03:['B03.02'],B04:['B04.04'],B05:['B05.03','B05.06'],B06:['B06.07'],B07:['B07.02'],B08:['B08.04']};
const filterNames={site:'Điểm đến',hotel:'Khách sạn',stars:'Hạng sao',item:'Mặt hàng',channel:'Kênh',meal:'Bữa ăn',supplier:'Nhà cung cấp',severe_weather:'Thời tiết xấu',promotion:'Khuyến mãi',outlet:'Nhà hàng',centre:'Trung tâm',activity:'Hoạt động',vehicle_type:'Loại xe',asset_type:'Loại tài sản',work_type:'Bảo trì',outdoor:'Ngoài trời',usage_area:'Khu vực sử dụng',room_type:'Loại phòng'};
const sites={SP:'Sa Pa',DN:'Đà Nẵng',DL:'Đà Lạt',PQ:'Phú Quốc'};
function contextLabel(c){
 const x=c.context,f=x.filters||{},parts=[];
 if(c.name==='baseline')return 'Toàn chuỗi · 2024–2025';
 if(x.start)parts.push(x.start+' → '+x.end+' (không gồm ngày cuối)');
 for(const [k,v] of Object.entries(f))parts.push((filterNames[k]||k)+': '+(k==='site'?sites[v]||v:v));
 if(x.assessment)parts.push('Đánh giá: '+x.assessment);
 return parts.join(' · ')||c.name;
}
function meta(id){return data.groups.flatMap(g=>g.metrics).find(m=>m.id===id)}
function fmt(v,m,compact=false){
 if(v===null||v===undefined)return '—';
 let n=Number(v);if(m.unit.startsWith('%'))return (n*100).toLocaleString('vi-VN',{minimumFractionDigits:2,maximumFractionDigits:2})+'%';
 if(compact&&m.unit==='VND')return (n/1e9).toLocaleString('vi-VN',{minimumFractionDigits:2,maximumFractionDigits:2});
 return n.toLocaleString('vi-VN',{maximumFractionDigits:2});
}
function quality(v){if(!v)return 'Chưa có kết quả cho phạm vi này';if(v.reasons.includes('SELECT_ONE_ITEM_FOR_COMPATIBLE_QUANTITY'))return 'Chọn một mặt hàng';if(v.reasons.includes('ZERO_DENOMINATOR'))return 'Mẫu số bằng 0';if(v.quality==='NOT_APPLICABLE')return 'Không áp dụng';if(v.quality==='UNAVAILABLE')return 'Không có dữ liệu';return v.quality}
function route(){
 const wanted=location.hash.slice(1),id=['overview','dashboard','generation','architecture','quality','reproduce'].includes(wanted)?wanted:'overview';
 document.querySelectorAll('.page').forEach(p=>p.hidden=p.id!==id);
 document.querySelectorAll('nav a').forEach(a=>{a.classList.toggle('active',a.dataset.page===id);if(a.dataset.page===id)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current')});
 document.title='CompanyE — '+({overview:'Tổng quan',dashboard:'Dashboard',generation:'Sinh dữ liệu',architecture:'Kiến trúc & ETL',quality:'Kiểm chứng',reproduce:'Tái lập'}[id]);
 window.scrollTo(0,0);
}
function setGroup(){
 const group=$('group').value, choices=data.cases.filter(c=>c.group===group);
 $('scenario').innerHTML=choices.map(c=>'<option value="'+c.id+'">'+esc(contextLabel(c))+'</option>').join('');
 if(['B06','B07'].includes(group)){const rice=choices.find(c=>c.context.filters?.item==='RICE');if(rice)$('scenario').value=rice.id}
 $('trend-metric').innerHTML=trends[group].map(id=>'<option value="'+id+'">'+esc(meta(id).name)+'</option>').join('');
 render();
}
function render(){
 current=data.cases.find(c=>c.id===$('scenario').value);
 const group=data.groups.find(g=>g.id===$('group').value);
 $('context').textContent=contextLabel(current)+' · '+($('engine').value==='oracle'?'Oracle':'Iceberg')+' · Kết quả hai nhánh khớp · 12 cảnh báo đối soát nguồn ngoài';
 const available=group.metrics.filter(m=>Object.hasOwn(current.metrics,m.id));
 $('scores').innerHTML=available.slice(0,4).map(m=>{const v=current.metrics[m.id];return '<article class="score"><small>'+esc(m.id)+'</small><h3>'+esc(m.name)+'</h3><strong>'+fmt(v.value,m,true)+'</strong><em>'+esc(m.unit==='VND'?'tỷ đồng':m.unit.split(';')[0])+' · '+esc(quality(v))+'</em></article>'}).join('');
 $('metric-table').innerHTML='<table><thead><tr><th>Chỉ tiêu</th><th>Giá trị</th><th>Đơn vị</th><th>Trạng thái</th></tr></thead><tbody>'+group.metrics.map(m=>{const v=current.metrics[m.id];return '<tr><td><strong>'+esc(m.id)+' · '+esc(m.name)+'</strong><details><summary>Công thức</summary><small>'+esc(m.formula)+'</small></details></td><td>'+fmt(v?.value,m)+'</td><td>'+esc(m.unit)+'</td><td><span class="pill '+(!v||v.quality!=='COMPLETE'?'pending':'')+'">'+esc(quality(v))+'</span></td></tr>'}).join('')+'</tbody></table>';
 renderChart();
}
function renderChart(){
 const id=$('trend-metric').value,m=meta(id),f=current.context.filters||{},ks=Object.keys(f),isRice=id==='B07.02';
 $('chart-title').textContent=m.name;
 // Monthly exports support the all-chain context; stock is specifically RICE.
 const allowed=(!ks.length&&!isRice)||(isRice&&ks.length===1&&f.item==='RICE');
 const sameAssessment=!current.context.assessment||current.context.assessment==='2025-12-31';
 const rows=data.monthly.filter(r=>r.engine===$('engine').value).filter(r=>{
  const s=r.month+'-01',a=r.month.split('-').map(Number),e=a[1]===12?(a[0]+1)+'-01-01':a[0]+'-'+String(a[1]+1).padStart(2,'0')+'-01';
  return s>=(current.context.start||'2024-01-01')&&e<=(current.context.end||'2026-01-01');
 });
 const billion=['B02.06','B04.04'].includes(id),pct=m.unit.startsWith('%'),unit=billion?'tỷ đồng':pct?'%':m.unit.split(';')[0];
 $('trend-scope').textContent=(isRice?'Mặt hàng RICE. ':'Toàn chuỗi. ')+'Chỉ tháng trọn vẹn trong kỳ; đơn vị '+unit+'. Nguồn: Power BI Import đã kiểm chứng, '+$('engine').value+'.';
 if(!allowed||!sameAssessment||!rows.length){
  $('chart').innerHTML='<div class="note">Chưa có chuỗi tháng đã xuất cho phạm vi này. Chọn “Toàn chuỗi”'+(isRice?' hoặc mặt hàng RICE':'')+' để xem xu hướng; bảng KPI vẫn giữ đúng phạm vi đang chọn.</div>';
  $('month-table').innerHTML='';return;
 }
 const val=r=>r.values[id]===null?null:Number(r.values[id])*(pct?100:1);
 const nums=rows.map(val),max=Math.max(...nums.filter(n=>n!==null),0)*1.18||1;
 const width=950,height=270,left=60,right=22,top=18,bottom=46,x=i=>rows.length===1?width/2:left+i*(width-left-right)/(rows.length-1),y=v=>height-bottom-v/max*(height-top-bottom);
 let svg='<svg class="chart-svg" viewBox="0 0 '+width+' '+height+'" role="img" aria-label="'+esc(m.name+' theo tháng; dữ liệu có ở bảng bên dưới')+'">';
 for(let i=0;i<=4;i++){const v=max*i/4,yy=y(v);svg+='<line x1="'+left+'" x2="'+(width-right)+'" y1="'+yy+'" y2="'+yy+'" stroke="#e4ebe1"/><text x="'+(left-12)+'" y="'+(yy+4)+'" text-anchor="end">'+v.toLocaleString('vi-VN',{maximumFractionDigits:1})+'</text>'}
 let segments=[],segment=[];nums.forEach((v,i)=>{if(v===null){if(segment.length)segments.push(segment);segment=[]}else segment.push(x(i)+','+y(v))});if(segment.length)segments.push(segment);
 for(const s of segments)svg+='<polyline points="'+s.join(' ')+'" fill="none" stroke="#237b6c" stroke-width="2.5" stroke-linejoin="round"/>';
 nums.forEach((v,i)=>{if(v!==null)svg+='<circle cx="'+x(i)+'" cy="'+y(v)+'" r="3.5"><title>'+esc(rows[i].month+' · '+v.toLocaleString('vi-VN',{maximumFractionDigits:3})+' '+unit)+'</title></circle>';if(i%Math.max(1,Math.ceil(rows.length/8))===0||i===rows.length-1)svg+='<text x="'+x(i)+'" y="'+(height-15)+'" text-anchor="middle">'+rows[i].month+'</text>'});
 $('chart').innerHTML=svg+'</svg>';
 $('month-table').innerHTML='<table><thead><tr><th>Tháng</th><th>'+esc(m.name)+' · '+esc(unit)+'</th></tr></thead><tbody>'+rows.map((r,i)=>'<tr><td>'+r.month+'</td><td>'+(nums[i]===null?'—':nums[i].toLocaleString('vi-VN',{maximumFractionDigits:6}))+'</td></tr>').join('')+'</tbody></table>';
}
function download(){
 const g=data.groups.find(g=>g.id===$('group').value);
 const rows=[['publication','engine','context','kpi','name','value','unit','quality'],...g.metrics.map(m=>[data.publication,$('engine').value,contextLabel(current),m.id,m.name,current.metrics[m.id]?.value??'',m.unit,quality(current.metrics[m.id])])];
 const csv='\uFEFF'+rows.map(r=>r.map(v=>'"'+String(v).replace(/"/g,'""')+'"').join(',')).join('\r\n');
 const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'})),a=document.createElement('a');a.href=url;a.download='CompanyE-'+g.id+'-'+current.id+'.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
async function start(){
 route();
 try{
  const [dr,cr]=await Promise.all([fetch('data.json'),fetch('config.json')]);if(!dr.ok||!cr.ok)throw Error('Không tải được dữ liệu');
  data=await dr.json();const config=await cr.json();
  if(config.repositoryUrl&&/^https:\/\//.test(config.repositoryUrl)){$('repo').href=config.repositoryUrl;$('repo').hidden=false}
  document.querySelectorAll('.publication').forEach(e=>e.textContent=data.publication);
  $('group').innerHTML=data.groups.map(g=>'<option value="'+g.id+'">'+esc(g.id+' · '+g.name)+'</option>').join('');
  $('seeds').textContent=JSON.stringify(data.seeds,null,2);
  $('provenance').textContent=JSON.stringify({publication:data.publication,checked_at:data.checked_at,source_sha256:data.provenance},null,2);
  $('test-stats').innerHTML=[[47,'KPI nghiệp vụ'],[96,'Phạm vi SQL'],[1148,'Phép đối chiếu DAX'],[457,'Phép đối chiếu biểu đồ']].map(([n,t])=>'<article><strong>'+n.toLocaleString('vi-VN')+'</strong><span>'+t+'</span></article>').join('');
  for(const [id,label] of Object.entries({group:'Nghiệp vụ',scenario:'Phạm vi đã kiểm chứng',engine:'Nguồn kết quả','trend-metric':'Chỉ tiêu'}))$(id).setAttribute('aria-label',label);
  setGroup();
  $('group').addEventListener('change',setGroup);$('scenario').addEventListener('change',render);$('engine').addEventListener('change',render);$('trend-metric').addEventListener('change',renderChart);
  $('reset').addEventListener('click',()=>{$('group').value='B01';$('engine').value='oracle';setGroup()});
  $('download').addEventListener('click',download);
 }catch(e){$('error').textContent='Không tải được bản dữ liệu demo. Vui lòng tải lại trang. '+e.message;$('error').hidden=false}
}
window.addEventListener('hashchange',route);start();

