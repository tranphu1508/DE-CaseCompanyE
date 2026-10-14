"""Launch the integration probe with pinned verified JARs; capture redacted logs."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path

spec=importlib.util.spec_from_file_location('services',Path(__file__).with_name('analytics-services.py'))
services=importlib.util.module_from_spec(spec)
spec.loader.exec_module(services)
parser=argparse.ArgumentParser()
parser.add_argument('phase',choices=['write','verify'])
args=parser.parse_args()
manifest=services.REPORTS/'active-probe.json'
if args.phase=='write':
    run='runtime_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    services.record('active-probe.json',dict(run_id=run))
else:
    run=json.loads(manifest.read_text())['run_id']
jars=json.loads((services.REPORTS/'jars.json').read_text())['jars']
output=services.command(['docker','exec',services.container('spark'),'/opt/spark/bin/spark-submit',
                         '--jars',','.join(p['file'] for p in jars),
                         '/workspace/src/analytics_runtime/probe.py',args.phase,run])
(services.REPORTS/f'{run}-{args.phase}.log').write_text(services.redact(output),encoding='utf-8')
report=json.loads((services.REPORTS/f'{run}-{args.phase}.json').read_text(encoding='utf-8'))
print(json.dumps(report,ensure_ascii=False,indent=2))
