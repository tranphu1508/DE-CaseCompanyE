"""Additive source schema. The frozen v1 model remains unchanged."""
from copy import deepcopy
from model import MODELS as V1, Table, key, fk, integer, money, moment, text

MODELS=deepcopy(V1)
MODELS['hotel_ops'] += [
    Table('booking_revisions','Các phiên bản giá của booking được điều chỉnh; không phải doanh thu bổ sung.',
          'Một booking và một phiên bản.',[
        key('revision_id'),fk('booking_id','bookings'),integer('revision_no','Số phiên bản tăng theo nguồn.'),
        moment('occurred_at','Thời điểm chốt phiên bản giá.'),text('reason','ORIGINAL hoặc RATE_CORRECTION.'),
        money('gross_vnd','Giá gói tại phiên bản.'),money('discount_vnd','Tổng giảm.'),
        money('company_share_vnd','Phần CompanyE tài trợ.'),money('partner_share_vnd','Phần đối tác tài trợ.'),
        money('customer_due_vnd','Khách phải trả.'),money('commission_vnd','Hoa hồng.')],
        ['revision_no > 0','discount_vnd=company_share_vnd+partner_share_vnd','customer_due_vnd=gross_vnd-discount_vnd'],owner='Distribution Finance'),
    Table('booking_room_revisions','Giá từng phòng ở mỗi phiên bản booking được điều chỉnh.',
          'Một phiên bản booking và một phòng.',[
        key('room_revision_id'),fk('revision_id','booking_revisions'),fk('booking_room_id','booking_rooms'),
        money('nightly_rate_vnd','Giá phòng mỗi đêm của phiên bản.')],owner='Hotel Operations')
]
# Composite uniqueness constraints are emitted by the v2 exporter.

def contracts():
    return {db:[t.contract() for t in tables] for db,tables in MODELS.items()}
