from pathlib import Path
import importlib.util,json,subprocess
spec=importlib.util.spec_from_file_location('publication_launcher',Path(__file__).with_name('publication.py'))
pub=importlib.util.module_from_spec(spec);spec.loader.exec_module(pub)
out=pub.ROOT/'reports/powerbi';out.mkdir(exist_ok=True)
jars=json.loads((pub.ROOT/'reports/analytics-runtime/jars.json').read_text())['jars']
cmd=['docker','exec',pub.svc.container('spark'),'/opt/spark/bin/spark-submit','--jars',','.join(j['file'] for j in jars),'/workspace/src/powerbi_export.py']
with (out/'export.log').open('w',encoding='utf8') as f:
    p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,cwd=pub.ROOT);code=p.wait(timeout=3600)
print((out/'export.log').read_text(encoding='utf8')[-3500:]);raise SystemExit(code)
