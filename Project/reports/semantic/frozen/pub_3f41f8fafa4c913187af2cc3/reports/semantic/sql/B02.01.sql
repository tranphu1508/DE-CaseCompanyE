-- KPI B02.01; numerator, denominator, SQL value. Quality policy also required.
WITH booking AS (SELECT COALESCE(SUM(gross_vnd),0) gross_vnd, COALESCE(SUM(customer_due_vnd),0) customer_due_vnd, COALESCE(SUM(company_share_vnd),0) company_share_vnd, COALESCE(SUM(partner_share_vnd),0) partner_share_vnd, COALESCE(SUM(commission_vnd),0) commission_vnd FROM {F01} f WHERE f.departure_date_key>=20240101 AND f.departure_date_key<20260101 AND status='COMPLETED')
SELECT (gross_vnd) b02_01_n,
(1) b02_01_d,
(gross_vnd) b02_01_value FROM booking
