set echo off verify off define off feedback off
whenever sqlerror exit sql.sqlcode rollback
alter session set container=FREEPDB1;
begin execute immediate 'create table ce_stage.etl_F01 as select * from ce_dwh_a.fact_booking where 1=0'; exception when others then if sqlcode != -955 then raise; end if; end;
/
grant select,insert,delete on ce_stage.etl_F01 to ce_loader;
grant select,insert on ce_dwh_a.fact_booking to ce_loader;
begin execute immediate 'create table ce_stage.etl_F02 as select * from ce_dwh_a.fact_room_day where 1=0'; exception when others then if sqlcode != -955 then raise; end if; end;
/
grant select,insert,delete on ce_stage.etl_F02 to ce_loader;
grant select,insert on ce_dwh_a.fact_room_day to ce_loader;
begin execute immediate 'create table ce_stage.etl_F03 as select * from ce_dwh_a.fact_stay_night where 1=0'; exception when others then if sqlcode != -955 then raise; end if; end;
/
grant select,insert,delete on ce_stage.etl_F03 to ce_loader;
grant select,insert on ce_dwh_a.fact_stay_night to ce_loader;
begin execute immediate 'create table ce_stage.etl_F04 as select * from ce_dwh_a.fact_ticket_order where 1=0'; exception when others then if sqlcode != -955 then raise; end if; end;
/
grant select,insert,delete on ce_stage.etl_F04 to ce_loader;
grant select,insert on ce_dwh_a.fact_ticket_order to ce_loader;
begin execute immediate 'create table ce_stage.etl_F05 as select * from ce_dwh_a.fact_rental where 1=0'; exception when others then if sqlcode != -955 then raise; end if; end;
/
grant select,insert,delete on ce_stage.etl_F05 to ce_loader;
grant select,insert on ce_dwh_a.fact_rental to ce_loader;
begin execute immediate 'create table ce_stage.etl_F06 as select * from ce_dwh_a.fact_breakfast_entitlement where 1=0'; exception when others then if sqlcode != -955 then raise; end if; end;
/
grant select,insert,delete on ce_stage.etl_F06 to ce_loader;
grant select,insert on ce_dwh_a.fact_breakfast_entitlement to ce_loader;
begin execute immediate 'create table ce_stage.etl_F07 as select * from ce_dwh_a.fact_dining_order where 1=0'; exception when others then if sqlcode != -955 then raise; end if; end;
/
grant select,insert,delete on ce_stage.etl_F07 to ce_loader;
grant select,insert on ce_dwh_a.fact_dining_order to ce_loader;
begin execute immediate 'create table ce_stage.etl_F08 as select * from ce_dwh_a.fact_meal_session where 1=0'; exception when others then if sqlcode != -955 then raise; end if; end;
/
grant select,insert,delete on ce_stage.etl_F08 to ce_loader;
grant select,insert on ce_dwh_a.fact_meal_session to ce_loader;
begin execute immediate 'create table ce_stage.etl_F09 as select * from ce_dwh_a.fact_admission where 1=0'; exception when others then if sqlcode != -955 then raise; end if; end;
/
grant select,insert,delete on ce_stage.etl_F09 to ce_loader;
grant select,insert on ce_dwh_a.fact_admission to ce_loader;
begin execute immediate 'create table ce_stage.etl_F10 as select * from ce_dwh_a.fact_activity_day where 1=0'; exception when others then if sqlcode != -955 then raise; end if; end;
/
grant select,insert,delete on ce_stage.etl_F10 to ce_loader;
grant select,insert on ce_dwh_a.fact_activity_day to ce_loader;
begin execute immediate 'create table ce_stage.etl_F11 as select * from ce_dwh_a.fact_vehicle_day where 1=0'; exception when others then if sqlcode != -955 then raise; end if; end;
/
grant select,insert,delete on ce_stage.etl_F11 to ce_loader;
grant select,insert on ce_dwh_a.fact_vehicle_day to ce_loader;
begin execute immediate 'create table ce_stage.etl_F12 as select * from ce_dwh_a.fact_purchase_line where 1=0'; exception when others then if sqlcode != -955 then raise; end if; end;
/
grant select,insert,delete on ce_stage.etl_F12 to ce_loader;
grant select,insert on ce_dwh_a.fact_purchase_line to ce_loader;
begin execute immediate 'create table ce_stage.etl_F13 as select * from ce_dwh_a.fact_receipt where 1=0'; exception when others then if sqlcode != -955 then raise; end if; end;
/
grant select,insert,delete on ce_stage.etl_F13 to ce_loader;
grant select,insert on ce_dwh_a.fact_receipt to ce_loader;
begin execute immediate 'create table ce_stage.etl_F14 as select * from ce_dwh_a.fact_stock_movement where 1=0'; exception when others then if sqlcode != -955 then raise; end if; end;
/
grant select,insert,delete on ce_stage.etl_F14 to ce_loader;
grant select,insert on ce_dwh_a.fact_stock_movement to ce_loader;
begin execute immediate 'create table ce_stage.etl_F16 as select * from ce_dwh_a.fact_maintenance_work where 1=0'; exception when others then if sqlcode != -955 then raise; end if; end;
/
grant select,insert,delete on ce_stage.etl_F16 to ce_loader;
grant select,insert on ce_dwh_a.fact_maintenance_work to ce_loader;
begin execute immediate 'create table ce_stage.etl_F17 as select * from ce_dwh_a.fact_weather_day where 1=0'; exception when others then if sqlcode != -955 then raise; end if; end;
/
grant select,insert,delete on ce_stage.etl_F17 to ce_loader;
grant select,insert on ce_dwh_a.fact_weather_day to ce_loader;
begin execute immediate 'create table ce_stage.etl_L01 as select * from ce_dwh_a.bridge_booking_room where 1=0'; exception when others then if sqlcode != -955 then raise; end if; end;
/
grant select,insert,delete on ce_stage.etl_L01 to ce_loader;
grant select,insert on ce_dwh_a.bridge_booking_room to ce_loader;
begin execute immediate 'create table ce_stage.etl_L02 as select * from ce_dwh_a.bridge_room_day_maintenance where 1=0'; exception when others then if sqlcode != -955 then raise; end if; end;
/
grant select,insert,delete on ce_stage.etl_L02 to ce_loader;
grant select,insert on ce_dwh_a.bridge_room_day_maintenance to ce_loader;
begin execute immediate 'create table ce_stage.etl_L03 as select * from ce_stage.validated_booking_service_link_input_a where 1=0'; exception when others then if sqlcode != -955 then raise; end if; end;
/
grant select,insert,delete on ce_stage.etl_L03 to ce_loader;
grant select,insert on ce_stage.validated_booking_service_link_input_a to ce_loader;
grant select,read on ce_stage.validated_booking_service_link_input_a to ce_dwh_a with grant option;
begin execute immediate 'create table ce_stage.etl_L04 as select * from ce_stage.site_crosswalk_input_a where 1=0'; exception when others then if sqlcode != -955 then raise; end if; end;
/
grant select,insert,delete on ce_stage.etl_L04 to ce_loader;
grant select,insert on ce_stage.site_crosswalk_input_a to ce_loader;
grant select,read on ce_stage.site_crosswalk_input_a to ce_dwh_a with grant option;
exit
