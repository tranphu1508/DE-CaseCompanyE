-- KPI B08.03; numerator, denominator, SQL value. Quality policy also required.
WITH work AS (SELECT COALESCE(SUM(cost_vnd),0) cost FROM {F16} f WHERE f.end_date_key>=20240101 AND f.end_date_key<20260101 AND status='COMPLETED'),
roomday AS (SELECT COALESCE(SUM(blocked_day),0) blocked, COALESCE(SUM(available_day),0) available, COALESCE(SUM(inventory_day),0) inventory FROM {F02} f WHERE f.date_key>=20240101 AND f.date_key<20260101)
SELECT (available) b08_03_n,
(1) b08_03_d,
(available) b08_03_value FROM work CROSS JOIN roomday
