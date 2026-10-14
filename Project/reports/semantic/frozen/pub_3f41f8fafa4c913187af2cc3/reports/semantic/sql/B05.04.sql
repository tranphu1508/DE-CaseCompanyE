-- KPI B05.04; numerator, denominator, SQL value. Quality policy also required.
WITH adm AS (SELECT COALESCE(SUM(admission_count),0) admissions FROM {F09} f WHERE f.admission_date_key>=20240101 AND f.admission_date_key<20260101),
act AS (SELECT COALESCE(SUM(available_capacity),0) capacity FROM {F10} f WHERE f.date_key>=20240101 AND f.date_key<20260101),
vehicle AS (SELECT COALESCE(SUM(rented_day),0) rented, COALESCE(SUM(available_day),0) ready FROM {F11} f WHERE f.date_key>=20240101 AND f.date_key<20260101)
SELECT (rented) b05_04_n,
(1) b05_04_d,
(rented) b05_04_value FROM adm CROSS JOIN act CROSS JOIN vehicle
