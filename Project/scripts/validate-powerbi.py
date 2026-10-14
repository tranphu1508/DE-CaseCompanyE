"""Validate PBIR against Microsoft's schemas; does NOT certify DAX or UI."""
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urljoin,urldefrag
import json,sys,hashlib
from urllib.error import HTTPError, URLError
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/powerbi-python'))
from jsonschema import Draft7Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT7
CACHE=ROOT/'config/powerbi/schema-cache';CACHE.mkdir(parents=True,exist_ok=True)
store={}
def fetch(url):
    url=urldefrag(url)[0]
    if url in store:return store[url]
    key=CACHE/(hashlib.sha256(url.encode()).hexdigest()+'.json')
    if key.exists():data=json.loads(key.read_text(encoding='utf8'))
    else:
        raw=url.replace('https://developer.microsoft.com/json-schemas/','https://raw.githubusercontent.com/microsoft/json-schemas/main/')
        data=json.loads(urlopen(raw,timeout=30).read());key.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    store[url]=data
    def walk(x):
        if isinstance(x,dict):
            ref=x.get('$ref')
            if ref and not ref.startswith('#'):fetch(urljoin(url,ref))
            for v in x.values():walk(v)
        elif isinstance(x,list):
            for v in x:walk(v)
    walk(data);return data
checks=[];errors=[];unavailable=[];unavailable_schemas={}
for p in (ROOT/'powerbi/CompanyE.Report/definition').rglob('*.json'):
    data=json.loads(p.read_text(encoding='utf8'));url=data['$schema']
    try:
        if url in unavailable_schemas:raise RuntimeError(unavailable_schemas[url])
        schema=fetch(url)
    except (HTTPError, URLError, RuntimeError) as exc:
        unavailable_schemas[url]=str(exc)
        unavailable.append(dict(path=str(p.relative_to(ROOT)),schema=url,reason=str(exc)))
        continue
    registry=Registry().with_resources((key,Resource.from_contents(value,default_specification=DRAFT7)) for key,value in store.items())
    validator=Draft7Validator(schema,registry=registry)
    errs=[str(e) for e in validator.iter_errors(data)]
    checks.append(dict(path=str(p.relative_to(ROOT)),errors=errs));errors+=errs
status='FAILED_STATIC_SCHEMA' if errors else ('INCOMPLETE_SCHEMA_UNAVAILABLE' if unavailable else 'PASSED_STATIC_SCHEMA')
result=dict(status=status,checked_files=len(checks),checks=checks,unavailable=unavailable,limitations='Does not execute Power Query, DAX or Desktop UI. Unavailable schemas are not counted as passed; Desktop may save a newer schema version than Microsoft currently publishes.')
(ROOT/'reports/powerbi/static-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(result['status'],len(checks),'files')
for error in errors:print(error[:1800])
sys.exit(1 if errors else (2 if unavailable else 0))
