"""Package verified B reports separately from historical Oracle/BI evidence."""
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / '.work/lakehouse-b'
SOURCE = WORK / 'reports'
DEST = ROOT / 'Project/reports/lakehouse-b'


def read(name):
    return json.loads((SOURCE / name).read_text(encoding='utf8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    verified = read('verification.json')
    fixtures = read('fixtures.json')
    published = read('publication.json')
    gold = read('gold.json')
    silver = read('silver.json')
    assert verified['status'] == fixtures['status'] == 'PASSED'
    assert published['status'] == 'PUBLISHED'
    assert verified['publication_id'] == published['publication_id'] == gold['publication_id']
    assert verified['baseline_metrics'] == 47 and verified['slice_metrics'] == 546
    assert verified['contexts'] == 104 and verified['oracle_connections'] == 0
    assert verified['raw_reference_equal'] and verified['historical_oracle_equal']
    assert fixtures['metric_checks'] == 117 and len(fixtures['policy_checks']) == 15
    before = read('state-before-publish.json')['control']
    interrupted = read('state-publish-interrupted.json')['control']
    after = read('state-published.json')['control']
    assert before['active'] is None and interrupted['active'] is None
    assert interrupted['publications'][0]['state'] == 'PREPARED'
    assert after['active'] == gold['publication_id']
    assert read('silver-before-gold.json')['active_gold_publication'] is None
    assert silver['transform_version'] == gold['transform_version'], 'Final run must pin the same source revision'
    catalog = subprocess.check_output(['docker', 'compose', '-p', 'ce-lakehouse-b', '-f', str(WORK / 'compose.yaml'),
                                      'exec', '-T', 'spark', 'cat', '/companye-lakehouse/catalog/catalog.json'])
    assert hashlib.sha256(catalog).hexdigest() == silver['source_catalog_sha256']
    (SOURCE / 'raw-catalog.json').write_bytes(catalog)
    names = ['silver.json', 'gold.json', 'publication.json', 'verification.json', 'fixtures.json',
             'baseline.json', 'slices.json', 'silver-before-gold.json', 'silver-exploration.json',
             'state-before-publish.json', 'state-publish-interrupted.json', 'state-published.json', 'raw-catalog.json']
    if (SOURCE / 'silver-initial-before-gold.json').exists():
        initial = read('silver-initial-before-gold.json')
        assert initial['active_gold_publication'] is None and not initial['gold_report_exists']
        names.append('silver-initial-before-gold.json')
    if (SOURCE / 'state-restarted.json').exists():
        assert read('state-restarted.json')['control']['active'] == gold['publication_id']
        restart = read('restart-verification.json')
        assert restart['status'] == 'PASSED_RESTART_AND_GOLD_REPLAY'
        assert restart['publication_id'] == gold['publication_id']
        names.extend(['state-restarted.json', 'restart-verification.json'])
    DEST.mkdir(parents=True, exist_ok=True)
    for name in names:
        shutil.copyfile(SOURCE / name, DEST / name)
    faults = []
    for name, marker in [('silver-injected-failure.log', 'INJECTED_FAILURE_AFTER_SILVER_TABLE'),
                         ('gold-injected-failure.log', 'INJECTED_FAILURE_AFTER_GOLD_TABLE'),
                         ('publish-injected-failure.log', 'INJECTED_FAILURE_BEFORE_POINTER_COMMIT')]:
        path = SOURCE / name
        text = path.read_text(encoding='utf8')
        assert marker in text
        faults.append({'file': name, 'sha256': sha(path), 'expected_error': marker, 'tail': text.splitlines()[-12:]})
    code = {p.relative_to(ROOT).as_posix(): sha(p) for folder in ['lakehouse_b', 'analytics_runtime', 'fact_etl', 'semantic']
            for p in sorted((ROOT / 'Project/src' / folder).glob('*.py'))}
    for rel in ['Project/src/lake_v2.py', 'Project/src/lake_job.py', 'scripts/lakehouse.py',
                'scripts/lakehouse-state.py', 'scripts/finalize-lakehouse.py']:
        code[rel] = sha(ROOT / rel)
    config_names = ['source_target_mapping_v1.json', 'warehouse_design_v1.json', 'kpi_contract_v1.json',
                    'analytics/ddl/manifest.json', 'analytics_runtime_lock_v1.json']
    config = {'Project/config/' + rel: sha(ROOT / 'Project/config' / rel) for rel in config_names}
    transform_inputs = {p.removeprefix('Project/'): h for p, h in {**code, **config}.items() if p.startswith('Project/')}
    encoded = json.dumps(transform_inputs, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    assert hashlib.sha256(encoded).hexdigest() == gold['transform_version'], 'Code changed after acceptance'
    development_failures = []
    for name in ['gold-key-bound-failure.log', 'publication-code-drift-rejected.log']:
        path = SOURCE / name
        if path.exists():
            development_failures.append({'file': name, 'sha256': sha(path), 'tail': path.read_text(encoding='utf8').splitlines()[-10:]})
    summary = {'status': 'PASSED_INDEPENDENT_B', 'packaged_at': datetime.now(timezone.utc).isoformat(),
               'publication_id': gold['publication_id'], 'source_batch_id': gold['source_batch_id'],
               'verification': verified, 'fault_injection': faults, 'development_failures': development_failures,
               'code_sha256': code, 'config_sha256': config,
               'reports_sha256': {name: sha(DEST / name) for name in names},
               'notes': ['Initial Silver failure was followed by full content verification and final Silver manifest under the accepted code.',
                         'Gold failure and recovery use the same final transform revision.',
                         'Early key-range bug and worker interruption produced unpublished candidates, retained locally.',
                         'Oracle was isolated from B by network/configuration; original Oracle runtime was not stopped.',
                         'Historical Power BI and web KPI payloads retain their original publication identity.']}
    (DEST / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    overview = f'''# Nghiệm thu lakehouse B độc lập

Publication: `{gold['publication_id']}`. Batch nguồn: `{gold['source_batch_id']}`.

| Kiểm tra | Kết quả |
|---|---|
| Silver | {verified['silver_tables']} bảng; 41 bảng nghiệp vụ và 4 bảng chứng từ |
| Gold | {verified['gold_tables']} bảng, {verified['gold_rows']:,} dòng logic |
| KPI baseline | {verified['baseline_metrics']} phép so sánh đạt |
| Bộ lọc | 96 ngữ cảnh, {verified['slice_metrics']} phép so sánh đạt |
| SQL fixture tính tay | {fixtures['sql_fixture_cases']} ca, {fixtures['metric_checks']} phép kiểm tra đạt |
| Chính sách | {len(fixtures['policy_checks'])} ca đạt |
| Publication/SCD | {len(fixtures['publication_and_scd_checks'])} ca đạt |
| Lỗi trước công bố | PREPARED, active pointer vẫn rỗng; chạy lại công bố thành công |
| Oracle | Không kết nối; đối chiếu báo cáo Oracle lịch sử và raw độc lập |

Đọc [summary.json](summary.json) để xem hash code/config/report và log lỗi chủ động. [silver.json](silver.json) và [gold.json](gold.json) ghi schema, count, content hash và snapshot ID của từng bảng. [fixtures.json](fixtures.json) ghi rõ từng ca; [verification.json](verification.json) ghi phạm vi kiểm chứng.

Các báo cáo ở đây không thay thế bằng chứng Power BI/web lịch sử hoặc benchmark. Runtime dùng initial batch và retry; chưa chứng nhận CDC hay vận hành ở quy mô phân tán. Xem [runbook](../../../docs/06-independent-lakehouse.md).
'''
    (DEST / 'README.md').write_text(overview, encoding='utf8')
    print(json.dumps({'status': summary['status'], 'publication': gold['publication_id'], 'reports': len(names)}))


if __name__ == '__main__':
    main()
