"""Freeze runtime, binaries and checksums without exporting credentials."""
import json
import platform
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
from manage import digest, save


def run(*args):
    return subprocess.run(args,cwd=ROOT,check=True,capture_output=True,encoding='utf-8').stdout.strip()


def main():
    cfg=json.loads((ROOT/'config/generation.json').read_text(encoding='utf-8'))
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    target=ROOT/'reports/runtime'/stamp
    target.mkdir(parents=True)
    images={}
    for image in ['postgres:17','apache/spark:3.5.7-python3']:
        images[image]=json.loads(run('docker','image','inspect',image,'--format','{{json .RepoDigests}}'))
    files={}
    for folder in ['src','config','scripts']:
        for src in sorted((ROOT/folder).glob('*')):
            if not src.is_file(): continue
            relative=src.relative_to(ROOT)
            dst=target/relative; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(src,dst)
            files[relative.as_posix()]=digest(src)
    shutil.copyfile(ROOT/'compose.yaml',target/'compose.yaml')
    files['compose.yaml']=digest(ROOT/'compose.yaml')
    backups={p.name:digest(p) for p in sorted((ROOT/'databases').glob('*.dump'))}
    record={'captured_at':datetime.now(timezone.utc).isoformat(),'dataset_version':cfg['dataset_version'],'python':platform.python_version(),'host_platform':platform.platform(),'images':images,'postgres_runtime':run('docker','compose','exec','-T','postgres','psql','-X','-U','companye','-d','postgres','-At','-c','SELECT version()'),'spark_runtime':json.loads((ROOT/'lake/catalog/catalog.json').read_text(encoding='utf-8'))['spark_version'],'files':files,'database_backups_sha256':backups,'credentials_exported':False,'runtime_archive':str(target)}
    save(target/'runtime.json',record)
    save(ROOT/'reports/runtime_environment.json',record)
    print(json.dumps({'runtime_archive':str(target),'files_frozen':len(files),'backups_hashed':len(backups)},ensure_ascii=False))


if __name__=='__main__': main()
