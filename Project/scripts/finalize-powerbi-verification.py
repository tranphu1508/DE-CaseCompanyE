"""Package the observed Desktop acceptance session and machine-check evidence.

UI observations below are an explicit record of the 2026-10-14 manual/tool-driven
session, not inferred from successful file generation. Re-running this script
does not perform a new UI test.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'reports/powerbi'
def read(name):
    return json.loads((REPORT / name).read_text(encoding='utf-8-sig'))
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

dax = read('dax-verification.json')
assert dax['status'] == 'PASSED_DAX' and not dax['failures']
assert read('input-verification.json')['status'] == 'PASSED_IMPORT_INPUT_CHECKS'
assert read('ui-reference-verification.json')['status'] == 'PASSED'
presentation = read('presentation-results.json')
reopened = read('reopened-presentation-results.json')
assert len(reopened) == 47
assert {r['KPI[id]']: r for r in reopened} == {r['KPI[id]']: r for r in presentation}

cases = [
    ('01-overview-total', 'Tổng toàn chuỗi: 73.275/174.478; công suất 42,00%; giá trị giữ lại 105.545.873.007 VND.'),
    ('02-site-SP', 'Lọc SP: 18.313/43.621; công suất 41,98%.'),
    ('03-iceberg-SP', 'Chuyển sang Iceberg, giữ SP: kết quả giống Oracle.'),
    ('04-B06-no-item', 'B06.01–06 trống khi chưa chọn item; có cảnh báo chọn một mặt hàng.'),
    ('05-B06-RICE', 'Chọn RICE: đặt 24.728, chấp nhận 24.164, từ chối 564, trễ 3.589; tỷ lệ 97,72%, 2,28%, OTIF 64,30%.'),
    ('06-QA-PARTIAL', 'Dữ liệu mô phỏng: vẫn hiển thị 37,50% (30/80 hợp lệ), kèm cảnh báo thiếu dữ liệu.'),
    ('07-QA-UNAVAILABLE', 'Dữ liệu mô phỏng: (Blank), cảnh báo không khả dụng; không thành 0.'),
    ('08-QA-ZERO-DENOMINATOR', 'Dữ liệu mô phỏng: (Blank), cảnh báo mẫu số 0.'),
    ('09-B04-LUNCH', 'B04.01–03/06–07 ngoài phạm vi, trống và báo rõ; B04.04=4.456.100.000 VND, B04.05=14.934.'),
    ('10-overview-January-2024', 'Tháng 01/2024: 2.682/7.440, 36,05%, 3.495.785.045 VND; khớp SQL.'),
    ('11-overview-hotel-DL3', 'Hotel DL-3: 9.079/17.445, 52,04%, 7.626.417.211 VND; khớp phép tổng hợp CSV độc lập.'),
    ('12-overview-filters-cleared', 'Xóa lọc kỳ và khách sạn: tổng toàn chuỗi khôi phục chính xác.'),
    ('13-reopened-overview', 'Sau Save và đóng/mở lại: dữ liệu và tổng vẫn đúng.'),
    ('14-B01', 'Trang B01 hiển thị 5 KPI, không cộng tổng các KPI khác đơn vị.'),
    ('15-B02', 'Trang B02 có 6 KPI, dùng thanh cuộn cho các dòng cuối.'),
    ('16-B03', 'Trang B03 hiển thị 5 KPI bán chéo.'),
    ('17-B05', 'Trang B05 có 6 KPI giải trí/phương tiện.'),
    ('18-B07-no-item', 'B07.01–04 yêu cầu một item; B07.05–06 vẫn có giá trị tổng được phép.'),
    ('19-B08', 'Trang B08 hiển thị 4 KPI; ngày khả dụng bằng B01.02.'),
    ('20-QA-COMPLETE', 'Dữ liệu mô phỏng: 40,00% và đầy đủ 40/100.'),
]
evidence = []
for name, observation in cases:
    files = []
    for ext in ['png', 'txt']:
        path = REPORT / 'ui-evidence' / (name + '.' + ext)
        assert path.exists() and path.stat().st_size > 0, path
        files.append(dict(path=str(path.relative_to(ROOT)), sha256=digest(path)))
    evidence.append(dict(id=name, status='OBSERVED_PASS', observation=observation, files=files))

old = read('ui-verification.json')
if old.get('status') == 'PREPARED_WAITING_FOR_DESKTOP_INSTALL':
    (REPORT / 'ui-verification-before-install.json').write_text(json.dumps(old, indent=2), encoding='utf8')
project_files = [p for p in (ROOT / 'powerbi').rglob('*') if p.is_file()
                 and (p.suffix in ['.pbip', '.pbir', '.pbism', '.bim'] or '/definition/' in p.as_posix())]
result = dict(
    status='PASSED_DESKTOP_IMPORT_UI_WITH_DOCUMENTED_LIMITS',
    observed_on='2026-10-14', packaged_at=datetime.now(timezone.utc).isoformat(),
    publication_id='pub_3f41f8fafa4c913187af2cc3',
    installation='INSTALLED_AND_RUNNING', desktop_version='2.158.1304.0',
    report_project='powerbi/CompanyE.pbip', connection_mode='Import from immutable, verified per-engine publication CSV exports',
    power_query_refresh='PASSED_36_TABLES', tables=36, relationships=69, measures=196, business_kpis=47,
    dax_verification=dict(status=dax['status'], queries=dax['queries'], metric_checks=dax['metric_checks'], excluded=dax['excluded']),
    reopened_presentation=dict(rows=47, unchanged=True),
    ui_filter_tests='PASSED_IN_LISTED_CASES', ui_total_tests='PASSED_IN_LISTED_CASES',
    ui_warning_tests='PASSED_IN_LISTED_CASES', save_reopen='PASSED',
    structural_validation=dict(status=read('static-validation.json')['status'], report='reports/powerbi/static-validation.json',
                               note='Generated version passed 95 schemas. Desktop saved newer visual schemas; HTTP 404 prevents validating those files, not counted as passed.'),
    limitations=[
        'Frozen Import only; no DirectQuery, scheduled refresh, gateway or cloud publication.',
        'Current production publication is COMPLETE. PARTIAL/UNAVAILABLE QA is isolated simulation, not end-to-end import of a partial publication.',
        'Weather filters and variable B06 assessment date are not implemented; B06 assessment is fixed at 2025-12-31.',
        'UI checks cover the listed scenarios, not every possible slicer combination. Tables with many KPI rows require vertical scrolling.',
        'Web, performance benchmarks/stress tests and decision usefulness evaluation remain separate work.',
    ], evidence=evidence,
    project_sha256=[dict(path=str(p.relative_to(ROOT)), sha256=digest(p)) for p in sorted(project_files)],
)
(REPORT / 'ui-verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
print(result['status'], len(evidence), 'observed UI cases; 47 presentation rows preserved after reopening')
