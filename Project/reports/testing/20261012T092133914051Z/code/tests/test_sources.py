import json
import subprocess
import pytest
import psycopg
import manage

pytestmark = pytest.mark.source
CHECKS = [(db, name, sql) for db, checks in manage.source_checks().items() for name, sql in checks.items()]


@pytest.mark.parametrize('db,name,sql', CHECKS, ids=[x[1] for x in CHECKS])
def test_source_invariants(pg, db, name, sql):
    with pg(db) as conn:
        assert conn.execute(sql).fetchone()[0] == 0, name


def test_existing_validation_command(pg, monkeypatch, report_dir):
    def sql(db, query):
        with pg(db) as conn:
            return '\n'.join('|'.join(str(v) for v in row) for row in conn.execute(query))
    monkeypatch.setattr(manage, 'psql', sql)
    monkeypatch.setattr(manage, 'save', lambda path, value: (report_dir/path.name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8'))
    manage.validate_sources()


@pytest.mark.parametrize('query,error', [
    ("INSERT INTO sites VALUES ('SP','duplicate','test')", psycopg.errors.UniqueViolation),
    ("UPDATE rooms SET hotel_id='missing' WHERE room_id=(SELECT room_id FROM rooms LIMIT 1)", psycopg.errors.ForeignKeyViolation),
    ("UPDATE hotels SET hotel_name=NULL WHERE hotel_id='SP-5'", psycopg.errors.NotNullViolation),
    ("UPDATE bookings SET departure=arrival WHERE booking_id=(SELECT booking_id FROM bookings LIMIT 1)", psycopg.errors.CheckViolation),
    ("UPDATE bookings SET company_share_vnd=company_share_vnd+1 WHERE booking_id=(SELECT booking_id FROM bookings LIMIT 1)", psycopg.errors.CheckViolation),
])
def test_database_rejects_invalid_mutations(pg, query, error):
    with pg() as conn:
        with pytest.raises(error):
            with conn.transaction():
                conn.execute(query)


def test_temporal_overlap_checker_detects_deliberate_error(pg):
    with pg() as conn:
        conn.execute('BEGIN')
        try:
            conn.execute("INSERT INTO stays SELECT 'TEST-OVERLAP',booking_room_id,checkin_date,checkout_date FROM stays LIMIT 1")
            assert conn.execute(manage.source_checks()['hotel_ops']['room_overlaps']).fetchone()[0] > 0
        finally:
            conn.execute('ROLLBACK')


def test_source_outage_is_an_error():
    with pytest.raises(psycopg.OperationalError):
        psycopg.connect('host=127.0.0.1 port=1 dbname=missing connect_timeout=2')


def test_ingestion_source_failure_does_not_publish_batch(tmp_path,monkeypatch):
    seed=tmp_path/'generated/v1'; seed.mkdir(parents=True)
    (seed/'manifest.json').write_text(json.dumps({'files':{},'rows':{}}))
    pointer=tmp_path/'lake/catalog/latest_ingestion.json'
    pointer.parent.mkdir(parents=True)
    pointer.write_text('{"batch_id":"previous_good_batch"}')
    monkeypatch.setattr(manage,'ROOT',tmp_path)
    monkeypatch.setattr(manage,'version_folder',lambda:seed)
    def unavailable(*args,**kwargs):
        raise subprocess.CalledProcessError(1,['psql'],stderr='injected source outage')
    monkeypatch.setattr(manage,'dc',unavailable)
    with pytest.raises(subprocess.CalledProcessError): manage.ingest()
    assert json.loads(pointer.read_text())['batch_id']=='previous_good_batch'
    assert not list((tmp_path/'lake/raw').glob('*/ingestion_manifest.json'))
