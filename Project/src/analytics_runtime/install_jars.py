"""Download pinned runtime JARs and verify the published Maven checksum.

Checksums come from HTTPS Maven Central; local SHA-256/SHA-512 are recorded.
Once installed, subsequent runs require the recorded SHA-256 as well.
"""
from pathlib import Path
import hashlib
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone

root = Path('/analytics/jars')
root.mkdir(parents=True, exist_ok=True)
lock = json.loads(Path('/workspace/config/analytics_runtime_lock_v1.json').read_text())
manifest_path = root / 'manifest.json'
previous = json.loads(manifest_path.read_text()) if manifest_path.exists() else []
known = {p['coordinate']: p for p in previous}
entries = []
for package in lock['packages']:
    group, artifact, version = package['coordinate'].split(':')
    name = f'{artifact}-{version}.jar'
    url = 'https://repo.maven.apache.org/maven2/' + group.replace('.', '/') + f'/{artifact}/{version}/{name}'
    path = root / name
    if not path.exists():
        partial = path.with_suffix('.jar.part')
        with urllib.request.urlopen(url, timeout=120) as response, partial.open('wb') as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
        partial.replace(path)
    data = path.read_bytes()
    sha256, sha512 = hashlib.sha256(data).hexdigest(), hashlib.sha512(data).hexdigest()
    # Some Maven publishers provide SHA-1 only. Record the actual verification
    # algorithm; local SHA-256/SHA-512 still pin the exact downloaded bytes.
    algorithm = None
    for candidate in ('sha512', 'sha256', 'sha1'):
        try:
            with urllib.request.urlopen(url + '.' + candidate, timeout=60) as response:
                expected = response.read().decode().split()[0].lower()
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
            continue
        algorithm = candidate
        if hashlib.new(candidate, data).hexdigest() != expected:
            raise RuntimeError(f'Maven {candidate} mismatch: {name}')
        break
    if algorithm is None:
        raise RuntimeError(f'No supported Maven checksum published: {name}')
    if package['coordinate'] in known and sha256 != known[package['coordinate']]['sha256']:
        raise RuntimeError(f'Previously recorded JAR hash differs: {name}')
    if package.get('jar_sha256') and sha256 != package['jar_sha256']:
        raise RuntimeError(f'Pinned runtime-lock JAR hash differs: {name}')
    entries.append(dict(coordinate=package['coordinate'], file=str(path), url=url,
                        bytes=len(data), sha256=sha256, sha512=sha512,
                        published_checksum_algorithm=algorithm, published_checksum=expected,
                        checksum_source=url + '.' + algorithm, verified_at=datetime.now(timezone.utc).isoformat()))
manifest_path.write_text(json.dumps(entries, indent=2) + '\n')
print(json.dumps({'status': 'VERIFIED', 'jars': entries}))
