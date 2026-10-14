"""Capture read-only runtime evidence without credentials or host mount paths."""
import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / '.work/lakehouse-b'
COMPOSE = ['docker', 'compose', '-p', 'ce-lakehouse-b', '-f', str(WORK / 'compose.yaml')]


def output(args):
    return subprocess.check_output(args, text=True, encoding='utf8').strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('label', choices=['before-publish', 'publish-interrupted', 'published', 'restarted'])
    args = parser.parse_args()
    services = {}
    for name in ['spark', 'metadata']:
        container = output(COMPOSE + ['ps', '-q', name])
        info = json.loads(output(['docker', 'inspect', container]))[0]
        services[name] = {
            'image': info['Config']['Image'],
            'image_id': info['Image'],
            'running': info['State']['Running'],
            'restart_count': info['RestartCount'],
            'memory_limit_bytes': info['HostConfig']['Memory'],
            'nano_cpus': info['HostConfig']['NanoCpus'],
            'networks': list(info['NetworkSettings']['Networks']),
            'published_ports': info['HostConfig']['PortBindings'],
            'mounts': [{'type': m['Type'], 'destination': m['Destination'], 'read_write': m['RW'],
                        'volume': m.get('Name')} for m in info['Mounts']],
        }
    query = """SELECT json_build_object(
      'active', (SELECT id FROM ce_b.active WHERE name='gold'),
      'publications', (SELECT coalesce(json_agg(json_build_object('id',id,'state',state,'sha256',sha256)),'[]'::json) FROM ce_b.publication),
      'registered_keys', (SELECT count(*) FROM ce_b.key_registry),
      'active_reader_leases', (SELECT count(*) FROM ce_b.lease WHERE expires_at>clock_timestamp()))::text;"""
    state = json.loads(output(COMPOSE + ['exec', '-T', 'metadata', 'psql', '-U', 'ce_catalog', '-d', 'ce_metadata', '-Atc', query]))
    report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'label': args.label,
              'services': services, 'control': state}
    path = WORK / 'reports' / ('state-' + args.label + '.json')
    path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    print(json.dumps({'report': path.name, 'control': state}, indent=2))


if __name__ == '__main__':
    main()
