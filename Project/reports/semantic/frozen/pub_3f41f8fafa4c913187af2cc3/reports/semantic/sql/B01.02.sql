-- KPI B01.02; numerator, denominator, SQL value. Quality policy also required.
WITH stay AS (SELECT COALESCE(SUM(occupied_night),0) occupied FROM {F03} f WHERE f.service_date_key>=20240101 AND f.service_date_key<20260101),
roomday AS (SELECT COALESCE(SUM(available_day),0) available FROM {F02} f WHERE f.date_key>=20240101 AND f.date_key<20260101),
booking AS (SELECT COALESCE(SUM(1),0) bookings, COALESCE(SUM(CASE WHEN status='CANCELLED' THEN 1 ELSE 0 END),0) cancelled, COALESCE(SUM(CASE WHEN status='NO_SHOW' THEN 1 ELSE 0 END),0) noshow FROM {F01} f WHERE f.arrival_date_key>=20240101 AND f.arrival_date_key<20260101)
SELECT (available) b01_02_n,
(1) b01_02_d,
(available) b01_02_value FROM stay CROSS JOIN roomday CROSS JOIN booking
