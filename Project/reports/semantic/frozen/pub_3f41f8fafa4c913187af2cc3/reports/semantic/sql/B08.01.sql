-- KPI B08.01; numerator, denominator, SQL value. Quality policy also required.
WITH work AS (SELECT COALESCE(SUM(cost_vnd),0) cost FROM {F16} f WHERE f.end_date_key>=20240101 AND f.end_date_key<20260101 AND status='COMPLETED'),
roomday AS (SELECT COALESCE(SUM(blocked_day),0) blocked, COALESCE(SUM(available_day),0) available, COALESCE(SUM(inventory_day),0) inventory FROM {F02} f WHERE f.date_key>=20240101 AND f.date_key<20260101)
SELECT (cost) b08_01_n,
(1) b08_01_d,
(cost) b08_01_value FROM work CROSS JOIN roomday
