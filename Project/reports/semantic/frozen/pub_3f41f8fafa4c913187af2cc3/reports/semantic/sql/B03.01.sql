-- KPI B03.01; numerator, denominator, SQL value. Quality policy also required.
WITH cohort AS (SELECT f.source_system,f.booking_id,f.customer_due_vnd FROM {F01} f WHERE f.departure_date_key>=20240101 AND f.departure_date_key<20260101 AND f.status='COMPLETED'),
tickets AS (SELECT l.booking_source_system,l.booking_id,SUM(t.net_ticket_vnd) ticket_value,MAX(CASE WHEN t.net_ticket_vnd>0 THEN 1 ELSE 0 END) bought_ticket FROM {F04} t JOIN {L03} l ON l.service_source_system=t.source_system AND l.service_id=t.ticket_order_id AND l.service_type='TICKET_ORDER' GROUP BY l.booking_source_system,l.booking_id),
rentals AS (SELECT l.booking_source_system,l.booking_id,SUM(r.agreed_vnd) rental_value,MAX(CASE WHEN r.agreed_vnd>0 THEN 1 ELSE 0 END) bought_rental FROM {F05} r JOIN {L03} l ON l.service_source_system=r.source_system AND l.service_id=r.rental_id AND l.service_type='RENTAL' WHERE r.status='COMPLETED' GROUP BY l.booking_source_system,l.booking_id),
cohort_total AS (SELECT COUNT(*) cohort_count,COALESCE(SUM(CASE WHEN COALESCE(t.bought_ticket,0)=1 OR COALESCE(r.bought_rental,0)=1 THEN 1 ELSE 0 END),0) bought,COALESCE(SUM(t.ticket_value),0) ticket_value,COALESCE(SUM(r.rental_value),0) rental_value,COALESCE(SUM(c.customer_due_vnd),0) room_value FROM cohort c LEFT JOIN tickets t ON t.booking_source_system=c.source_system AND t.booking_id=c.booking_id LEFT JOIN rentals r ON r.booking_source_system=c.source_system AND r.booking_id=c.booking_id)
SELECT (bought) b03_01_n,
(1) b03_01_d,
(bought) b03_01_value FROM cohort_total
