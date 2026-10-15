"""Migrate the BI presentation to independently certified lakehouse B."""
import argparse,csv,hashlib,json,shutil,subprocess,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];P=ROOT/'Project';WORK=ROOT/'.work/lakehouse-b'
BUILD=ROOT/'.work/bi-b/Project';REPORT=P/'reports/bi-migration';BI=P/'powerbi-b'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(script,*args):subprocess.run([sys.executable,'-X','utf8',str(script),*args],check=True,cwd=ROOT)

def export():
    cmd=['docker','compose','-p','ce-lakehouse-b','-f',str(WORK/'compose.yaml'),'exec','-T','spark','/opt/spark/bin/spark-submit',
         '--jars',','.join(read(WORK/'jars.json')),'/workspace/src/bi_migration/export_b.py']
    log=WORK/'reports/bi-export.log'
    with log.open('w',encoding='utf8') as stream:
        result=subprocess.run(cmd,stdout=stream,stderr=subprocess.STDOUT)
    print(log.read_text(encoding='utf8')[-2500:]);assert result.returncode==0
    m=read(WORK/'reports/bi-export.json');pid=m['publication_id'];dest=BUILD/'reports/powerbi/imports'/pid
    dest.mkdir(parents=True,exist_ok=True)
    container=subprocess.check_output(cmd[:6]+['ps','-q','spark'],text=True).strip()
    assert container, 'Spark service is not running'
    subprocess.run(['docker','cp',container+':/workspace/reports/bi-imports/'+pid+'/.',str(dest)],check=True)
    save(BUILD/'reports/powerbi/export.json',m);save(REPORT/'export.json',m)

def build():
    m=read(BUILD/'reports/powerbi/export.json');pid=m['publication_id']
    verified=read(P/'reports/lakehouse-b/verification.json');assert verified['publication_id']==pid and verified['status']=='PASSED'
    assert m['engines']==['iceberg'] and all(q['status']=='COMPLETE' for q in m['quality_metrics'].values())
    assert m['external_warning_count']==12 and not m['quality_scope'],'Adapt quality UI for a different batch'
    for table in m['tables']:
        source=BUILD/'reports/powerbi/imports'/pid/table['filename']
        assert sha(source)==table['sha256'], 'Input checksum changed: '+table['entity']
    (BUILD/'scripts').mkdir(parents=True,exist_ok=True)
    shutil.copytree(P/'config',BUILD/'config',dirs_exist_ok=True)
    shutil.copytree(P/'src/semantic',BUILD/'src/semantic',dirs_exist_ok=True)
    save(BUILD/'reports/publication/manifest.json',read(P/'reports/lakehouse-b/gold.json'))
    adapters=[]
    for name in ['build-powerbi.py','build-powerbi-dashboard.py']:
        text=(P/'scripts'/name).read_text(encoding='utf8');changes=[]
        if name=='build-powerbi-dashboard.py':
            old="assert export['publication_id']=='pub_3f41f8fafa4c913187af2cc3'"
            assert text.count(old)==1
            text=text.replace(old,"assert export['publication_id']==read(ROOT/'reports/publication/manifest.json')['publication_id']")
            changes.append('Replace historical fixed publication guard with candidate manifest identity; retain quality guards.')
        (BUILD/'scripts'/name).write_text(text,encoding='utf8')
        adapters.append({'script':name,'source_sha256':sha(P/'scripts'/name),'changes':changes})
    for n in ['ui-verification.json','dax-verification.json','static-validation.json']:
        save(BUILD/'reports/powerbi'/n,{'status':'NOT_RUN_FOR_B'})
    run(BUILD/'scripts/build-powerbi.py');run(BUILD/'scripts/build-powerbi-dashboard.py')
    # Retain exact certified formulas; only the engine default and attribution change.
    model=read(BUILD/'powerbi/CompanyE.SemanticModel/model.bim');changed=[]
    for t in model['model']['tables']:
        for part in t.get('partitions',[]):
            exp=part['source']['expression']
            if isinstance(exp,list):exp='\n'.join(exp)
            import re
            match=re.search(r'File.Contents\("([^\"]+)"\)',exp);assert match,t['name']
            src=Path(match[1]);dest=BI/'data'/pid/src.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
            part['source']['expression']=exp.replace(match[1],str(dest))
        for measure in t.get('measures',[]):
            old=measure['expression'];new=old.replace('"oracle"','"iceberg"').replace('oracle (mặc định)','iceberg (mặc định)')
            if new!=old:changed.append(measure['name']);measure['expression']=new
    with (BI/'data'/pid/'Engine.csv').open('w',encoding='utf8',newline='') as f:
        w=csv.writer(f);w.writerow(['engine']);w.writerow(['iceberg'])
    shutil.copytree(BUILD/'powerbi/CompanyE.Report',BI/'CompanyE.Report',dirs_exist_ok=True)
    for file in (BI/'CompanyE.Report').rglob('*.json'):
        value=read(file)
        def change(x):
            if isinstance(x,dict):return {k:change(v) for k,v in x.items()}
            if isinstance(x,list):return [change(v) for v in x]
            if isinstance(x,str):
                return "'iceberg'" if x=="'oracle'" else x.replace('pub_3f41f8fafa4c913187af2cc3',pid)
            return x
        save(file,change(value))
    shutil.copyfile(BUILD/'powerbi/CompanyE.pbip',BI/'CompanyE-B.pbip')
    save(BI/'CompanyE.SemanticModel/model.bim',model)
    shutil.copyfile(BUILD/'powerbi/CompanyE.SemanticModel/definition.pbism',BI/'CompanyE.SemanticModel/definition.pbism')
    save(REPORT/'build.json',{'status':'BUILT_NOT_YET_DESKTOP_VERIFIED','publication_id':pid,'engines':['iceberg'],
                            'template_adapters':adapters,'engine_default_changes':changed,'model_sha256':sha(BI/'CompanyE.SemanticModel/model.bim'),
                            'note':'B uses its own dimensions/keys. Historical A report is preserved. Numerical KPI expressions only change engine fallback.'})
    print('B PBIP:',BI/'CompanyE-B.pbip')

def prepare_tests():
    """Reuse certified test generators with explicit B-only adapters, preserving A."""
    pid=read(REPORT/'export.json')['publication_id']
    for phase in ['baseline','slices']:
        save(BUILD/f'reports/semantic/{phase}.json',read(P/f'reports/lakehouse-b/{phase}.json'))
    adaptations=[]
    for name in ['prepare-powerbi-dax-tests.py','verify-powerbi-dax.py','verify-powerbi-dashboard.py','validate-powerbi.py']:
        source=(P/'scripts'/name).read_text(encoding='utf8');text=source
        if name=='prepare-powerbi-dax-tests.py':
            text=text.replace("['oracle','iceberg']","['iceberg']").replace("case['oracle']","case['iceberg']")
        if name=='verify-powerbi-dashboard.py':
            text=text.replace('pub_3f41f8fafa4c913187af2cc3',pid).replace("['oracle','iceberg']","['iceberg']").replace("'oracle'","'iceberg'")
        (BUILD/'scripts'/name).write_text(text,encoding='utf8')
        adaptations.append({'script':name,'source_sha256':sha(P/'scripts'/name),'adapted_sha256':sha(BUILD/'scripts'/name),
                            'changes':'Use B evidence, B publication and one Iceberg engine; comparison logic/tolerances unchanged.' if text!=source else 'Unchanged validator.'})
    # Test the final retargeted model, including B default engine (not the scratch template).
    shutil.copyfile(BI/'CompanyE.SemanticModel/model.bim',BUILD/'powerbi/CompanyE.SemanticModel/model.bim')
    run(BUILD/'scripts/prepare-powerbi-dax-tests.py')
    run(BUILD/'scripts/verify-powerbi-dashboard.py','prepare')
    save(REPORT/'test-adapters.json',adaptations)
    for source,target in [('dax-test-vectors.json','dax-test-vectors.json'),('dashboard/vectors.json','chart-vectors.json')]:
        shutil.copyfile(BUILD/'reports/powerbi'/source,REPORT/target)
    acceptance=[dict(id='identity',query='EVALUATE ROW("publication",[Publication],"engines",COUNTROWS(Engine),"rows",COUNTROWS(F01))',
                     expected={'publication':pid+' | Import cố định; không phải dữ liệu trực tiếp','engines':1,
                               'rows':next(t['rows_per_engine'] for t in read(REPORT/'export.json')['tables'] if t['entity']=='F01')}),
                dict(id='mixed_kpi_total',query='EVALUATE ROW("value",[Giá trị KPI],"display",[Giá trị hiển thị],"state",[Trạng thái KPI])',
                     expected={'value':None,'display':None,'state':'Không cộng KPI khác đơn vị'})]
    for state,value in [('COMPLETE',0.4),('PARTIAL',0.375),('UNAVAILABLE',None),('ZERO_DENOMINATOR',None)]:
        acceptance.append(dict(id='qa/'+state,query='EVALUATE CALCULATETABLE(ROW("value",[QA giá trị],"warning",[QA cảnh báo]),TREATAS({"'+state+'"},QA[scenario]))',
                               expected={'value':value},warning_prefix='KIỂM THỬ:'))
    save(REPORT/'acceptance-vectors.json',{'cases':acceptance})

def verify():
    for source,target in [('dax-results.json','dax-results.json'),('chart-results.json','dashboard/results.json')]:
        shutil.copyfile(REPORT/source,BUILD/'reports/powerbi'/target)
    run(BUILD/'scripts/verify-powerbi-dax.py');run(BUILD/'scripts/verify-powerbi-dashboard.py','verify')
    for source,target in [('dax-verification.json','dax-verification.json'),('dashboard/verification.json','chart-verification.json')]:
        value=read(BUILD/'reports/powerbi'/source);assert value['status'].startswith('PASSED'),value['status']
        value['publication_id']=read(REPORT/'export.json')['publication_id'];value['engine']='iceberg'
        save(REPORT/target,value)
    cases=read(REPORT/'acceptance-vectors.json')['cases'];results={r['id']:r for r in read(REPORT/'acceptance-results.json')};checks=[]
    for case in cases:
        actual=results.get(case['id'],{});rows=actual.get('rows',[])
        ok='error' not in actual and len(rows)==1
        if ok:
            ok=all(rows[0].get('['+k+']')==v for k,v in case['expected'].items())
            if case.get('warning_prefix'):ok=ok and rows[0].get('[warning]','').startswith(case['warning_prefix'])
        checks.append({'case':case['id'],'passed':ok,'actual':actual})
    save(REPORT/'acceptance-verification.json',{'status':'PASSED' if all(c['passed'] for c in checks) else 'FAILED','checks':checks})
    assert all(c['passed'] for c in checks),'Acceptance guard failed'
    model=read(BI/'CompanyE.SemanticModel/model.bim');old=read(P/'powerbi/CompanyE.SemanticModel/model.bim')
    norm=lambda s:'\n'.join(s) if isinstance(s,list) else s
    measures=lambda m:{x['name']:norm(x['expression']) for t in m['model']['tables'] for x in t.get('measures',[])}
    oldm=measures(old);newm=measures(model)
    assert set(oldm)==set(newm),'Measure inventory changed'
    assert read(REPORT/'export.json')['publication_id'] in newm['Publication']
    for name,expression in newm.items():
        if name!='Publication':
            assert expression==oldm[name].replace('"oracle"','"iceberg"').replace('oracle (mặc định)','iceberg (mặc định)'),name
    for file in (BI/'CompanyE.Report/definition').rglob('*.json'):
        assert 'pub_3f41f8fafa4c913187af2cc3' not in file.read_text(encoding='utf8'),str(file)
    save(REPORT/'model-contract-verification.json',{'status':'PASSED','unchanged_measures_except_engine_default':len(newm)-1,
         'publication_measure_updated':True,'no_historical_publication_in_B_report':True,
         'model_sha256':sha(BI/'CompanyE.SemanticModel/model.bim'),'tables':len(model['model']['tables']),
         'relationships':len(model['model']['relationships'])})

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('phase',choices=['export','build','prepare-tests','verify']);a=ap.parse_args()
    REPORT.mkdir(parents=True,exist_ok=True)
    {'export':export,'build':build,'prepare-tests':prepare_tests,'verify':verify}[a.phase]()
