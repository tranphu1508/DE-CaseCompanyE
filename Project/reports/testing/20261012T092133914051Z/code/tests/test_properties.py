from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
import json

import pytest
from hypothesis import given, strategies as st
from generate import Generator, days

pytestmark = pytest.mark.property


def small_config(seed, month=1):
    start = date(2024,month,1)
    return dict(dataset_version='TEST_ONLY', seed=seed, date_from=str(start),
                date_to=str(start+timedelta(days=29)), customers=60, bookings=70,
                walkin_tickets=20, five_star_rooms=8, three_star_rooms=8,
                currency='VND', timezone='Asia/Ho_Chi_Minh')


@given(seed=st.integers(min_value=0,max_value=2**32-1), month=st.integers(min_value=1,max_value=12))
def test_generated_business_conservation_across_seeds(report_dir,seed, month):
    gen = Generator(small_config(seed, month)); gen.run()
    h = gen.rows['hotel_ops']; e = gen.rows['entertainment_ops']
    with (report_dir/'hypothesis_examples.jsonl').open('a') as log:
        log.write(json.dumps({'seed':seed,'month':month,'configuration':small_config(seed,month),
            'bookings':len(h['bookings']),'completed':sum(b['status']=='COMPLETED' for b in h['bookings']),
            'cancelled':sum(b['status']=='CANCELLED' for b in h['bookings'])})+'\n')
    booking = {r['booking_id']:r for r in h['bookings']}
    amounts = defaultdict(int)
    for line in h['booking_rooms']:
        b = booking[line['booking_id']]
        nights = (date.fromisoformat(b['departure'])-date.fromisoformat(b['arrival'])).days
        amounts[b['booking_id']] += line['nightly_rate_vnd']*nights
    for b in booking.values():
        assert b['gross_vnd'] == amounts[b['booking_id']]
        assert 0 <= b['discount_vnd'] <= b['gross_vnd']
        assert b['discount_vnd'] == b['company_share_vnd']+b['partner_share_vnd']
        assert b['customer_due_vnd']+b['discount_vnd'] == b['gross_vnd']
    rooms = {r['booking_room_id']:r['room_id'] for r in h['booking_rooms']}
    occupied = set()
    for stay in h['stays']:
        start, end = map(date.fromisoformat, (stay['checkin_date'],stay['checkout_date']))
        for offset in range((end-start).days):
            key = (rooms[stay['booking_room_id']], start+timedelta(days=offset))
            assert key not in occupied
            occupied.add(key)
    balances = defaultdict(Decimal)
    for movement in h['stock_movements']:
        balances[movement['receipt_id']] += Decimal(str(movement['quantity']))*(1 if movement['movement_type']=='IN' else -1)
    assert all(v >= 0 for v in balances.values())
    for ent in h['breakfast_entitlements']:
        assert 0 <= ent['redeemed_covers'] <= ent['eligible_covers']
    tickets = defaultdict(int)
    for t in e['tickets']: tickets[t['ticket_order_id']] += t['price_vnd']
    assert all(tickets[o['ticket_order_id']] == o['gross_vnd'] for o in e['ticket_orders'])


@given(st.integers(min_value=1,max_value=1000000))
def test_small_generator_is_deterministic(seed):
    a=Generator(small_config(seed)); a.run()
    b=Generator(small_config(seed)); b.run()
    assert a.rows == b.rows


@given(st.dates(min_value=date(2020,1,1), max_value=date(2030,12,1)),
       st.integers(min_value=0,max_value=30))
def test_half_open_date_intervals(start, length):
    end=start+timedelta(days=length)
    actual=days(start,end)
    assert len(actual)==length and len(set(actual))==length
    assert end not in actual
    assert all(start <= d < end for d in actual)
