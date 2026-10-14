"""Reproduce sources + cataloged lake in a separate local workspace.

Python standard library only. Original generators are copied byte-for-byte.
The platform command never starts or modifies the original companye project.
"""
from pathlib import Path
import argparse, hashlib, json, os, shutil, subprocess, sys

REPO=Path(__file__).resolve().parents[1]
SOURCE=REPO/'Project'
WORK=REPO/'.work/platform/Project'

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def run(*args, env=None):
    subprocess.run(list(args),cwd=WORK,env=env,check=True)

def prepare(port):
    WORK.mkdir(parents=True,exist_ok=True)
    lock=WORK.parent/'inputs.json'
    paths=[]
    for folder in ['src','scripts','config','tests','testing']:
        paths.extend(p for p in (SOURCE/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
    paths += [SOURCE/name for name in ['compose.yaml','compose.test.yaml','compose.analytics.yaml','compose.publication.yaml','pytest.ini']]
    expected={p.relative_to(SOURCE).as_posix():sha(p) for p in paths}
    spec={'source_sha256':expected,'port':port,'compose_project':'ce-repro-'+hashlib.sha256(str(WORK).encode()).hexdigest()[:10]}
    if lock.exists():
        if json.loads(lock.read_text())!=spec:
            raise SystemExit('Reproduction input changed. Preserve this run and use a fresh clone/worktree; no files overwritten.')
    for p in paths:
        q=WORK/p.relative_to(SOURCE);data=p.read_bytes()
        if p.name=='compose.yaml':
            data=data.replace(b'127.0.0.1:55432:5432',f'127.0.0.1:{port}:5432'.encode())
        if q.exists():
            if q.read_bytes()!=data: raise SystemExit('Working input differs: '+q.relative_to(WORK).as_posix())
        else:q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(data)
    (WORK/'reports').mkdir(exist_ok=True)
    lock.write_text(json.dumps(spec,indent=2),encoding='utf-8')
    return spec

def verify_seeds():
    result={'status':'PASSED','versions':{}}
    for version in ['v1','v2']:
        baseline=json.loads((SOURCE/f'reports/reproducibility/{version}/manifest.json').read_text(encoding='utf-8'))
        actual=json.loads((WORK/f'generated/{version}/manifest.json').read_text(encoding='utf-8'))
        # v1 persisted Windows separators; normalize path keys for portable comparisons.
        old={k.replace('\\','/'):v for k,v in baseline['files'].items()}
        new={k.replace('\\','/'):v for k,v in actual['files'].items()}
        metadata_differences=[]
        compared=dict(new)
        audit='audit_only/generation_audit.json'
        if version=='v1' and old.get(audit)!=new.get(audit):
            original=json.loads((SOURCE/f'reports/reproducibility/{version}/generation_audit.json').read_text(encoding='utf-8'))
            regenerated=json.loads((WORK/f'generated/{version}'/audit).read_text(encoding='utf-8'))
            differing=[k for k in set(original)|set(regenerated) if original.get(k)!=regenerated.get(k)]
            if differing==['python_version']:
                metadata_differences.append({'file':audit,'field':'python_version','baseline':original['python_version'],'current':regenerated['python_version']})
                compared[audit]=old[audit]
        if old!=compared or baseline['rows']!=actual['rows'] or baseline['generator_sha256']!=actual['generator_sha256'] or baseline['config']!=actual['config']:
            raise SystemExit('Baseline mismatch for '+version+'; original evidence was not modified.')
        for rel,digest in new.items():
            if sha(WORK/'generated'/version/rel)!=digest:raise SystemExit('Generated file checksum mismatch: '+rel)
        result['versions'][version]={'files':len(new),'tables':sum(len(x) for x in actual['rows'].values()),'rows':actual['total_rows'],'all_business_payload_sha256_equal':True,'all_file_sha256_equal':old==new,'metadata_differences':metadata_differences,'baseline_python':baseline['python_version'],'current_python':actual['python_version']}
    (WORK/'reports/repository-seed-check.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase',choices=['prepare','generate','verify-seed','up','load','ingest','lake','verify','test','status','stop','all'])
    p.add_argument('--port',type=int,default=55433,help='Loopback PostgreSQL port; default avoids the original 55432 service')
    a=p.parse_args()
    if not 1024<=a.port<=65535: p.error('Choose a non-privileged port in 1024..65535')
    spec=prepare(a.port)
    env={**os.environ,'COMPOSE_PROJECT_NAME':spec['compose_project']}
    def py(file,*args):run(sys.executable,'-X','utf8',file,*args,env=env)
    if a.phase=='prepare':print('Prepared isolated workspace: '+str(WORK));return
    if a.phase in ['generate','all']:
        py('src/generate.py');py('src/audit_generation.py');py('src/generate_v2.py');verify_seeds()
    if a.phase=='verify-seed':verify_seeds()
    if a.phase in ['up','all']:py('src/manage.py','up')
    if a.phase=='all':
        for phase in ['load','ingest','lake','verify']:py('src/manage_v2.py',phase)
    elif a.phase in ['load','ingest','lake','verify']:py('src/manage_v2.py',a.phase)
    elif a.phase=='status':run('docker','compose','ps',env=env)
    elif a.phase=='stop':run('docker','compose','stop',env=env)
    elif a.phase=='test':
        verify_seeds()
        # Historical lake/GX acceptance reads the v1 Parquet snapshot and golden
        # aggregates. Rebuild that prerequisite locally, never copy old lake state.
        if not (WORK/'lake/catalog/latest_ingestion.json').exists():py('src/manage.py','all')
        else:
            py('src/manage.py','up');py('src/manage.py','verify')
        testenv={**env,'COMPOSE_PROJECT_NAME':spec['compose_project']+'-tests'}
        run('docker','compose','-f','compose.test.yaml','build','tester',env=testenv)
        try:
            run('docker','compose','-f','compose.test.yaml','up','-d','--wait','postgres-test',env=testenv)
            run('docker','compose','-f','compose.test.yaml','run','--rm','tester','python','testing/run_suite.py',env=testenv)
        finally:run('docker','compose','-f','compose.test.yaml','down',env=testenv)

if __name__=='__main__':main()

