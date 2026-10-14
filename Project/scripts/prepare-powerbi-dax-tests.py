"""Build Desktop DAX test vectors from the previously certified SQL results."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from semantic.queries import DOMAINS
read=lambda p:json.loads(p.read_text(encoding='utf8'))
cases=[];excluded=[]
for phase in ['baseline','slices']:
    for case in read(ROOT/f'reports/semantic/{phase}.json')['checks']:
        ctx=case['context'];filters=ctx.get('filters',{})
        if 'severe_weather' in filters or ctx.get('assessment','2025-12-31')!='2025-12-31':
            excluded.append(dict(phase=phase,case=case['case'],group=case['group'],context=ctx,reason='Weather filtering / variable assessment not implemented in first Desktop model.'));continue
        for engine in ['oracle','iceberg']:
            args=['TREATAS({"'+engine+'"},Engine[engine])']
            for k,col,default in [('start','start_key','2024-01-01'),('end','end_key','2026-01-01')]:
                args.append('TREATAS({'+ctx.get(k,default).replace('-','')+'},Period['+col+'])')
            for k,v in filters.items():
                dim,col=DOMAINS[k] if k in DOMAINS else ('F14','usage_area') if k=='usage_area' else ('F16','work_type')
                val=str(v) if isinstance(v,int) else '"'+v+'"'
                args.append('TREATAS({'+val+'},'+dim+'['+col+'])')
            columns=[]
            for mid in case['selected']:
                for suffix in ['', ' n', ' d',' state']:columns += ['"'+mid+suffix+'"','['+mid+suffix+']']
            query='EVALUATE CALCULATETABLE(ROW('+','.join(columns)+'),'+','.join(args)+')'
            cases.append(dict(id=f'{phase}/{case["case"]}/{case["group"]}/{engine}',context=ctx,engine=engine,query=query,expected=case['oracle']))
out=dict(cases=cases,excluded=excluded)
(ROOT/'reports/powerbi/dax-test-vectors.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
print(len(cases),'DAX queries prepared;',len(excluded),'unsupported contexts explicitly excluded')
