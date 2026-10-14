import json
import os
from pathlib import Path

import pytest
from hypothesis import settings, HealthCheck

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path(os.environ.get('COMPANYE_TEST_RUN', '/tmp/companye-test-results'))
OUTPUT.mkdir(parents=True, exist_ok=True)
settings.register_profile('companye', max_examples=12, deadline=None,
                          derandomize=True, database=None,
                          suppress_health_check=[HealthCheck.too_slow])
settings.load_profile('companye')


@pytest.fixture(scope='session')
def root():
    return ROOT


@pytest.fixture(scope='session')
def report_dir():
    return OUTPUT


@pytest.fixture(scope='session')
def config():
    return json.loads((ROOT/'config/generation.json').read_text())


@pytest.fixture(scope='session')
def pg():
    import psycopg
    dsn = os.environ.get('COMPANYE_TEST_DSN', '')
    if '@postgres-test:5432' not in dsn:
        pytest.fail('Tests require the dedicated postgres-test service, never production.')
    def connect(db='hotel_ops'):
        assert db in ('hotel_ops', 'entertainment_ops', 'hotel_ops_v2', 'entertainment_ops_v2', 'postgres')
        return psycopg.connect(dsn+'/'+db, autocommit=True)
    return connect


@pytest.fixture(scope='session')
def spark(tmp_path_factory):
    import lake_job
    from pyspark.sql import SparkSession
    work = tmp_path_factory.mktemp('companye-lake')
    patch = pytest.MonkeyPatch()
    patch.setattr(lake_job, 'ROOT', work)
    patch.setattr(lake_job, 'LAKE', work/'lake')
    patch.setattr(lake_job, 'CATALOG', work/'lake/catalog')
    lake_job.CATALOG.mkdir(parents=True)
    os.environ['PYSPARK_SUBMIT_ARGS']='--master local[2] --driver-memory 1536m --conf spark.ui.enabled=false pyspark-shell'
    session = lake_job.session()
    session.sparkContext.setLogLevel('ERROR')
    yield session
    if session.sparkContext._jsc is not None:
        session.stop()
    patch.undo()


def pytest_runtest_logreport(report):
    if report.when == 'call' or report.failed or report.skipped:
        record = {'test': report.nodeid, 'stage': report.when,
                  'outcome': report.outcome, 'seconds': report.duration}
        if report.failed or report.skipped:
            record['detail'] = str(report.longrepr)
        with (OUTPUT/'cases.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(record, ensure_ascii=False)+'\n')
