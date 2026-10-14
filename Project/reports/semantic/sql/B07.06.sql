-- KPI B07.06; numerator, denominator, SQL value. Quality policy also required.
WITH stock AS (SELECT COALESCE(SUM(CASE WHEN movement_date_key<20240101 THEN signed_qty ELSE 0 END),0) opening, COALESCE(SUM(signed_qty),0) closing, COALESCE(SUM(CASE WHEN movement_date_key>=20240101 THEN use_qty ELSE 0 END),0) used, COALESCE(SUM(CASE WHEN movement_date_key>=20240101 THEN waste_qty ELSE 0 END),0) wasted, COALESCE(SUM(CASE WHEN movement_date_key>=20240101 THEN waste_qty*unit_price_vnd ELSE 0 END),0) waste_value, COALESCE(SUM(CASE WHEN movement_date_key<20240101 THEN signed_qty*unit_price_vnd ELSE in_qty*unit_price_vnd END),0) available_value FROM {F14} f WHERE f.movement_date_key>=1 AND f.movement_date_key<20260101)
SELECT (waste_value) b07_06_n,
(available_value) b07_06_d,
CAST((waste_value) AS DECIMAL(28,12))/NULLIF(CAST((available_value) AS DECIMAL(28,12)),0) b07_06_value FROM stock
