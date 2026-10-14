import csv
import hashlib
import json

import pytest
import audit_generation
import generate
from model import MODELS, all_contracts

pytestmark = pytest.mark.baseline


def test_frozen_seed_files_and_code(root):
    folder = root/'generated/v1'
    manifest = json.loads((folder/'manifest.json').read_text())
    assert generate.code_fingerprint() == manifest['generator_sha256']
    for relative, expected in manifest['files'].items():
        # The immutable v1 manifest was authored on Windows; keep its bytes intact.
        assert hashlib.sha256((folder/relative.replace('\\','/')).read_bytes()).hexdigest() == expected, relative
    assert all_contracts() == json.loads((root/'config/source_contracts.json').read_text())


def test_full_regeneration_without_overwriting_baseline(monkeypatch, report_dir):
    monkeypatch.setattr(audit_generation, 'write_json',
                        lambda path, value: (report_dir/'regeneration.json').write_text(
                            json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8'))
    audit_generation.main()
    report = json.loads((report_dir/'regeneration.json').read_text())
    assert len(report['same_seed_same_code_byte_identical_tables']) == 39


@pytest.mark.parametrize('db,table', [(db,t.name) for db, tables in MODELS.items() for t in tables])
def test_frozen_csv_row_counts(root, db, table):
    manifest = json.loads((root/'generated/v1/manifest.json').read_text())
    with (root/'generated/v1'/db/(table+'.csv')).open(newline='', encoding='utf-8') as stream:
        assert sum(1 for _ in csv.reader(stream))-1 == manifest['rows'][db][table]
