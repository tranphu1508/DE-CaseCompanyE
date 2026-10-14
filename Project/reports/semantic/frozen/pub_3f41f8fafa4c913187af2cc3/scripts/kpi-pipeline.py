"""Run read-only semantic validation in the existing publication runtime."""
from pathlib import Path
import argparse,importlib.util,json,subprocess
spec=importlib.util.spec_from_file_location('publication_launcher',Path(__file__).with_name('publication.py'))
pub=importlib.util.module_from_spec(spec);spec.loader.exec_module(pub)
ap=argparse.ArgumentParser();ap.add_argument('phase',choices=['baseline','fixtures','slices']);args=ap.parse_args()
out=pub.ROOT/'reports/semantic';out.mkdir(exist_ok=True)
jars=json.loads((pub.ROOT/'reports/analytics-runtime/jars.json').read_text())['jars']
cmd=['docker','exec',pub.svc.container('spark'),'/opt/spark/bin/spark-submit','--jars',','.join(j['file'] for j in jars),'/workspace/src/semantic/main.py',args.phase]
with (out/(args.phase+'.log')).open('w',encoding='utf8') as f:
    p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,cwd=pub.ROOT);code=p.wait(timeout=7200)
print((out/(args.phase+'.log')).read_text(encoding='utf8')[-4500:]);raise SystemExit(code)
