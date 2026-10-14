-- KPI B06.02; numerator, denominator, SQL value. Quality policy also required.
WITH due AS (SELECT f.source_system,f.purchase_line_id,f.ordered_qty FROM {F12} f WHERE f.expected_date_key>=20240101 AND f.expected_date_key<20260101 AND f.expected_date_key<=20251231),
received AS (SELECT source_system,purchase_line_id,SUM(accepted_qty) accepted,SUM(rejected_qty) rejected,SUM(late_accepted_qty) late,SUM(CASE WHEN received_date_key<=expected_date_key THEN accepted_qty ELSE 0 END) ontime FROM {F13} WHERE received_date_key<=20251231 GROUP BY source_system,purchase_line_id),
purchase_total AS (SELECT COALESCE(SUM(d.ordered_qty),0) ordered,COALESCE(SUM(r.accepted),0) accepted,COALESCE(SUM(r.rejected),0) rejected,COALESCE(SUM(r.late),0) late,COALESCE(SUM(CASE WHEN COALESCE(r.ontime,0)>=d.ordered_qty THEN 1 ELSE 0 END),0) otif,COUNT(*) lines FROM due d LEFT JOIN received r ON r.source_system=d.source_system AND r.purchase_line_id=d.purchase_line_id)
SELECT (accepted) b06_02_n,
(1) b06_02_d,
(accepted) b06_02_value FROM purchase_total
