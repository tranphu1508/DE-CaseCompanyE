import json
from pathlib import Path
import pytest

pytestmark=pytest.mark.acceptance
CONTRACT=json.loads((Path(__file__).parent/'fixtures/business_acceptance.json').read_text())


@pytest.mark.parametrize('case',CONTRACT['cases'],ids=[c['id'] for c in CONTRACT['cases']])
def test_reference_business_answers(spark,case,report_dir):
    try:
        for name,table in case['tables'].items():
            spark.createDataFrame(table['rows'],table['schema']).createOrReplaceTempView(name)
        actual=[r.asDict() for r in spark.sql(case['sql']).collect()]
        (report_dir/(case['id']+'_reference.json')).write_text(json.dumps({
            'id':case['id'],'name':case['name'],'scope':'REFERENCE_ONLY_NOT_WAREHOUSE',
            'definition':case['definition'],'expected':case['expected'],'actual':actual,
            'passed':actual==case['expected']},ensure_ascii=False,indent=2),encoding='utf-8')
        assert actual==case['expected']
    finally:
        for name in case['tables']: spark.catalog.dropTempView(name)


def test_cross_sell_fixture_detects_fanout_bug(spark):
    case=next(c for c in CONTRACT['cases'] if c['id']=='B03')
    try:
        for name,t in case['tables'].items():
            spark.createDataFrame(t['rows'],t['schema']).createOrReplaceTempView(name)
        wrong=spark.sql('SELECT sum(b.room_amount) amount FROM a_bookings b LEFT JOIN a_tickets t USING(booking_id) LEFT JOIN a_rentals r USING(booking_id)').first()['amount']
        assert wrong != case['expected'][0]['hotel_amount']
    finally:
        for name in case['tables']: spark.catalog.dropTempView(name)
