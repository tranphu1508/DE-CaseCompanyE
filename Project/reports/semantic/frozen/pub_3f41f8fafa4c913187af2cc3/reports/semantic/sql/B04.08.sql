-- KPI B04.08; numerator, denominator, SQL value. Quality policy also required.
WITH ent AS (SELECT COALESCE(SUM(eligible_covers),0) eligible, COALESCE(SUM(redeemed_covers),0) redeemed FROM {F06} f WHERE f.service_date_key>=20240101 AND f.service_date_key<20260101),
dining AS (SELECT COALESCE(SUM(net_vnd),0) net, COALESCE(SUM(covers),0) covers, COALESCE(SUM(rating_sum),0) ratings, COALESCE(SUM(rating_count),0) rated FROM {F07} f WHERE f.service_date_key>=20240101 AND f.service_date_key<20260101),
session_total AS (SELECT COALESCE(SUM(ingredient_cost_vnd),0) cost, COALESCE(SUM(actual_covers),0) actual FROM {F08} f WHERE f.service_date_key>=20240101 AND f.service_date_key<20260101 AND EXISTS (SELECT 1 FROM {D10} m WHERE m.meal_key=f.meal_key AND m.meal_code IN ('BREAKFAST','DINNER')))
SELECT (ratings) b04_08_n,
(rated) b04_08_d,
CAST((ratings) AS DECIMAL(28,12))/NULLIF(CAST((rated) AS DECIMAL(28,12)),0) b04_08_value FROM ent CROSS JOIN dining CROSS JOIN session_total
