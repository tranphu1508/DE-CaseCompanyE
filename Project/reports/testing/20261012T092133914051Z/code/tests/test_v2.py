import hashlib
import json
from collections import Counter
from decimal import Decimal

import pytest
from generate_v2 import GeneratorV2, table_bytes, external_files, fingerprints
from model_v2 import MODELS
from manage_v2 import V2_CHECKS,COVERAGE
from manage import source_checks
from lake_v2 import receipt_events,EVENT_FIELDS

pytestmark=pytest.mark.v2


def test_v2_frozen_full_regeneration_and_external_bytes(root,report_dir):
    cfg=json.loads((root/'config/generation_v2.json').read_text())
    manifest=json.loads((root/'generated/v2/manifest.json').read_text())
    assert fingerprints()==manifest['generator_sha256']
    assert cfg==manifest['config']
    for name,h in manifest['files'].items():
        assert hashlib.sha256((root/'generated/v2'/name).read_bytes()).hexdigest()==h,name
    gen=GeneratorV2(cfg); gen.run()
    for db,tables in MODELS.items():
        for t in tables:
            assert table_bytes(gen.rows[db][t.name],t)==(root/'generated/v2'/db/(t.name+'.csv')).read_bytes(),t.name
    files,truth=external_files(gen)
    for name,data in files.items(): assert data==(root/'generated/v2/external'/name).read_bytes(),name
    assert gen.truth==json.loads((root/'generated/v2/audit_only/identity_truth_DO_NOT_INGEST.json').read_text())
    (report_dir/'v2_reproduction.json').write_text(json.dumps({'status':'PASSED','tables':41,'external_files':len(files),
        'config':cfg,'generator_sha256':fingerprints(),'total_rows':manifest['total_rows']},indent=2))


@pytest.mark.parametrize('name,query',list(V2_CHECKS.items()),ids=list(V2_CHECKS))
def test_v2_new_invariants(pg,name,query):
    with pg('hotel_ops_v2') as conn: assert conn.execute(query).fetchone()[0]==0,name


def test_v2_inherits_old_invariants_and_has_required_coverage(pg,root,report_dir):
    for db,rules in source_checks().items():
        with pg(db+'_v2') as conn:
            for name,sql in rules.items(): assert conn.execute(sql).fetchone()[0]==0,(db,name)
    observed={}
    with pg('hotel_ops_v2') as conn:
        for name,sql in COVERAGE.items():
            if sql: observed[name]=conn.execute(sql).fetchone()[0]
    assert all(observed.values())
    assert observed['revised_bookings']==160
    pairs=json.loads((root/'generated/v2/audit_only/identity_truth_DO_NOT_INGEST.json').read_text())
    assert len(pairs)==12120 and len({p['entertainment_customer_id'] for p in pairs})==12000
    cases=json.loads((root/'generated/v2/audit_only/identity_cases_DO_NOT_INGEST.json').read_text())
    counts=Counter(label for row in cases for label in row['cases'])
    assert counts['DUPLICATE_LOCAL_PROFILE']==120
    assert all(counts[k]>0 for k in ['MISSING_CONTACTS','SHARED_HOUSEHOLD_PHONE','NAME_TYPO','CHANGED_PHONE'])
    (report_dir/'v2_coverage.json').write_text(json.dumps({'source':observed,'identity':dict(counts)},indent=2))


def fixture_rows(spark,conflict=False):
    schema=', '.join(c+' string' for c in EVENT_FIELDS+['received_at','delivery_id','_source_path'])
    rows=[
        ['e1','r1','1','2024-01-01T10:00:00+07:00','2024-01-01T10:00:00+07:00','s1','h1','p1','6000','g','18000','2024-01-10T23:00:00+07:00','d1','old.csv'],
        ['e2','r1','2','2024-01-01T10:00:00+07:00','2024-01-01T11:00:00+07:00','s1','h1','p1','5000','g','18000','2024-01-02T23:00:00+07:00','d2','new.csv'],
        ['e3','r2','1','2024-01-01T10:00:00+07:00','2024-01-01T10:00:00+07:00','s1','h1','p2','2','sọt','18000','2024-01-02T23:00:00+07:00','d3','bad.csv']]
    replay=list(rows[1]); replay[-3:]=['2024-01-20T23:00:00+07:00','d4','replay.csv']
    if conflict: replay[8]='9000'
    rows.append(replay)
    return spark.createDataFrame(rows,schema)


def test_v2_out_of_order_and_replay_independent_fixture(spark):
    valid,bad,replay,latest=receipt_events(fixture_rows(spark))
    assert valid.count()==2 and bad.count()==1 and replay.count()==1
    row=latest.select('receipt_ref','revision','accepted_qty_kg','unit_price_vnd').first()
    assert tuple(row)==('r1',2,Decimal('5.000'),18000)
    # Version 1 arrived later but must not overwrite the corrected source version.
    assert latest.count()==1


def test_v2_conflicting_replay_is_rejected(spark):
    with pytest.raises(ValueError,match='Conflicting payload'):
        receipt_events(fixture_rows(spark,conflict=True))
