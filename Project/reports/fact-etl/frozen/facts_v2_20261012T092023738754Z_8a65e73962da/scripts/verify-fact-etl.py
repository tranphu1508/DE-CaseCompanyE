from pathlib import Path
import importlib.util,json,subprocess
spec=importlib.util.spec_from_file_location('services',Path(__file__).with_name('analytics-services.py'))
svc=importlib.util.module_from_spec(spec);spec.loader.exec_module(svc)
out=svc.ROOT/'reports/fact-etl';jars=json.loads((svc.ROOT/'reports/analytics-runtime/jars.json').read_text())['jars']
cmd=['docker','exec',svc.container('spark'),'/opt/spark/bin/spark-submit','--jars',','.join(j['file'] for j in jars),'/workspace/src/verify_fact_etl.py']
with (out/'independent-validation.log').open('w',encoding='utf8') as f:
    p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,cwd=svc.ROOT);code=p.wait(timeout=1800)
print((out/'independent-validation.log').read_text(encoding='utf8')[-3500:])
raise SystemExit(code)
