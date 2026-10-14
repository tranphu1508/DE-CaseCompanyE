"""Run six ordered stages; immutable inputs, isolated DB/lake, retained evidence."""
import hashlib
import html
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=Path(os.environ.get('COMPANYE_TEST_OUTPUT','/test-output'))
run=BASE/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
run.mkdir(parents=True)
env={**os.environ,'COMPANYE_TEST_RUN':str(run),'PYTHONPATH':str(ROOT/'src'),
     'HYPOTHESIS_STORAGE_DIRECTORY':'/tmp/companye-hypothesis',
     'SPARK_LOCAL_IP':'127.0.0.1','GX_ANALYTICS_ENABLED':'false'}
hashes={}
for folder in ['src','tests','testing','config']:
    for path in sorted((ROOT/folder).rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
            relative=path.relative_to(ROOT)
            hashes[str(relative)]=hashlib.sha256(path.read_bytes()).hexdigest()
            target=run/'code'/relative
            target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(path,target)
for name in ['compose.test.yaml','pytest.ini','scripts/test.ps1']:
    path=ROOT/name; target=run/'code'/name
    target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(path,target)
    hashes[name]=hashlib.sha256(path.read_bytes()).hexdigest()
manifest=ROOT/'generated/v1/manifest.json'
runtime={'python':platform.python_version(),'platform':platform.platform(),
         'java':subprocess.check_output(['java','-version'],stderr=subprocess.STDOUT,text=True),
         'image_id':os.environ.get('COMPANYE_TEST_IMAGE_ID','not supplied; see Docker environment evidence'),
         'generator_manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),
         'code_sha256':hashes,
         'test_environment':'isolated companye-tests Docker project; source mounts read-only',
         'pip_freeze':subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True).splitlines()}
(run/'runtime.json').write_text(json.dumps(runtime,indent=2),encoding='utf-8')
phases=[('01_baseline_sources','baseline or source'),('02_scenario_coverage','coverage'),
        ('03_properties','property'),('04a_spark','spark'),('04b_lake','lake'),
        ('05_great_expectations','gx'),('06_acceptance_reference','acceptance'),('07_v2_extensions','v2')]
if len(sys.argv)>1:
    phases=[('selected', ' '.join(sys.argv[2:]))] if sys.argv[1]=='-m' else phases
results=[]
for name, expression in phases:
    print('\nSTART '+name,flush=True)
    started=time.monotonic()
    command=[sys.executable,'-m','pytest','-m',expression,'-v','--tb=short',
             '--junitxml='+str(run/(name+'.xml'))]
    with (run/(name+'.log')).open('w',encoding='utf-8') as log:
        proc=subprocess.Popen(command,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        for line in proc.stdout:
            log.write(line); log.flush(); print(line,end='',flush=True)
        code=proc.wait()
    results.append({'stage':name,'selector':expression,'exit_code':code,
                    'status':'PASSED' if code==0 else 'FAILED','seconds':round(time.monotonic()-started,3)})
    (run/'summary.json').write_text(json.dumps({'stages':results,
        'status':'PASSED' if all(r['exit_code']==0 for r in results) else 'FAILED',
        'warehouse_acceptance':'NOT_EXECUTED: no warehouse deployed; stage 06 tests independent reference queries only'},indent=2))
(BASE/'latest.json').write_text(json.dumps({'run':run.name,'summary':str(run/'summary.json')},indent=2))
print('Evidence: '+str(run),flush=True)
records=[json.loads(line) for line in (run/'cases.jsonl').read_text().splitlines()] if (run/'cases.jsonl').exists() else []
passed=sum(r['outcome']=='passed' for r in records)
failed=sum(r['outcome']=='failed' for r in records)
rows=''.join('<tr><td>'+html.escape(r['stage'])+'</td><td>'+r['status']+'</td><td>'+str(r['seconds'])+'</td><td><a href="'+r['stage']+'.log">Log</a> · <a href="'+r['stage']+'.xml">JUnit</a></td></tr>' for r in results)
gx_docs=list((run/'gx').rglob('index.html')) if (run/'gx').exists() else []
gx_link=('<p><a href="'+gx_docs[0].relative_to(run).as_posix()+'">Great Expectations Data Docs</a> (có ca sai có chủ đích)</p>') if gx_docs else ''
page='''<!doctype html><html lang="vi"><meta charset="utf-8"><title>CompanyE — Kiểm thử</title>
<style>body{font:16px system-ui;max-width:1000px;margin:40px auto;padding:0 20px;color:#172b42}table{border-collapse:collapse;width:100%}td,th{padding:12px;text-align:left;border-bottom:1px solid #ccc}a{color:#1763ad}.note{background:#fff4da;padding:16px}</style>
<h1>CompanyE — Báo cáo kiểm thử</h1>'''+f'<p>Lần chạy: {run.name} · {passed} đạt · {failed} lỗi</p>'+'''<p class="note">Bước 6 kiểm tra SQL tham chiếu trên fixture độc lập. Warehouse thực tế chưa được triển khai và chưa được nghiệm thu.</p><table><tr><th>Bước</th><th>Kết quả</th><th>Giây</th><th>Bằng chứng</th></tr>'''+rows+'</table>'+gx_link+'''<p><a href="summary.json">Tổng hợp</a> · <a href="runtime.json">Môi trường và hash mã nguồn</a> · <a href="scenario_coverage.json">Tình huống đã có và còn thiếu</a> · <a href="cases.jsonl">Từng test case</a></p><p>Thời gian trên dùng chẩn đoán một lần chạy; chưa phải benchmark nhiều quy mô.</p></html>'''
(run/'index.html').write_text(page,encoding='utf-8')
sys.exit(0 if all(r['exit_code']==0 for r in results) else 1)
