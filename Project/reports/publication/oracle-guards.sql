set echo off verify off define off feedback off
whenever sqlerror exit sql.sqlcode rollback
alter session set container=FREEPDB1;
declare n number; begin select count(*) into n from dba_users where username='CE_PUBLISHER'; if n=0 then execute immediate 'create user CE_PUBLISHER identified by "[PRIVATE_SECRET]"'; end if; end;
/
grant create session to CE_PUBLISHER;
declare n number; begin select count(*) into n from dba_users where username='CE_READER'; if n=0 then execute immediate 'create user CE_READER identified by "[PRIVATE_SECRET]"'; end if; end;
/
grant create session to CE_READER;
begin execute immediate 'create table ce_stage.publication_guard(slot varchar2(20) primary key, state varchar2(10) not null, publication_id varchar2(128))'; exception when others then if sqlcode<>-955 then raise; end if; end;
/
merge into ce_stage.publication_guard g using (select 'CE_DWH_A' slot from dual) s on(g.slot=s.slot) when not matched then insert(slot,state) values(s.slot,'OPEN');
merge into ce_stage.publication_guard g using (select 'CE_DWH_B' slot from dual) s on(g.slot=s.slot) when not matched then insert(slot,state) values(s.slot,'OPEN');
merge into ce_stage.publication_guard g using (select 'TEST_A' slot from dual) s on(g.slot=s.slot) when not matched then insert(slot,state) values(s.slot,'OPEN');
merge into ce_stage.publication_guard g using (select 'TEST_B' slot from dual) s on(g.slot=s.slot) when not matched then insert(slot,state) values(s.slot,'OPEN');
commit;
create or replace procedure ce_stage.assert_publication_writable(p_slot varchar2) authid definer as s varchar2(10);
begin
 select state into s from ce_stage.publication_guard where slot=p_slot for update;
 if s<>'OPEN' then raise_application_error(-20072,'PUBLICATION_SLOT_SEALED'); end if;
end;
/
create or replace procedure ce_stage.seal_publication_slot(p_slot varchar2,p_id varchar2) authid definer as s varchar2(10); old_id varchar2(128);
begin
 select state,publication_id into s,old_id from ce_stage.publication_guard where slot=p_slot for update;
 if s='SEALED' and old_id<>p_id then raise_application_error(-20073,'SLOT_SEALED_FOR_OTHER_PUBLICATION'); end if;
 update ce_stage.publication_guard set state='SEALED',publication_id=p_id where slot=p_slot;
end;
/
grant execute on ce_stage.seal_publication_slot to ce_publisher;
grant select on ce_stage.publication_guard to ce_publisher;
grant execute on ce_stage.assert_publication_writable to ce_dwh_a,ce_dwh_b;
grant read on ce_dwh_a.dim_date to ce_reader;
grant read on ce_dwh_a.dim_site to ce_reader;
grant read on ce_dwh_a.dim_hotel to ce_reader;
grant read on ce_dwh_a.dim_room to ce_reader;
grant read on ce_dwh_a.dim_channel to ce_reader;
grant read on ce_dwh_a.dim_promotion to ce_reader;
grant read on ce_dwh_a.dim_customer_profile to ce_reader;
grant read on ce_dwh_a.dim_rate_plan to ce_reader;
grant read on ce_dwh_a.dim_outlet to ce_reader;
grant read on ce_dwh_a.dim_meal to ce_reader;
grant read on ce_dwh_a.dim_centre to ce_reader;
grant read on ce_dwh_a.dim_activity to ce_reader;
grant read on ce_dwh_a.dim_vehicle to ce_reader;
grant read on ce_dwh_a.dim_supplier to ce_reader;
grant read on ce_dwh_a.dim_item to ce_reader;
grant read on ce_dwh_a.dim_asset to ce_reader;
grant read on ce_dwh_a.fact_booking to ce_reader;
grant read on ce_dwh_a.fact_room_day to ce_reader;
grant read on ce_dwh_a.fact_stay_night to ce_reader;
grant read on ce_dwh_a.fact_ticket_order to ce_reader;
grant read on ce_dwh_a.fact_rental to ce_reader;
grant read on ce_dwh_a.fact_breakfast_entitlement to ce_reader;
grant read on ce_dwh_a.fact_dining_order to ce_reader;
grant read on ce_dwh_a.fact_meal_session to ce_reader;
grant read on ce_dwh_a.fact_admission to ce_reader;
grant read on ce_dwh_a.fact_activity_day to ce_reader;
grant read on ce_dwh_a.fact_vehicle_day to ce_reader;
grant read on ce_dwh_a.fact_purchase_line to ce_reader;
grant read on ce_dwh_a.fact_receipt to ce_reader;
grant read on ce_dwh_a.fact_stock_movement to ce_reader;
grant read on ce_dwh_a.agg_inventory_lot_day to ce_reader;
grant read on ce_dwh_a.fact_maintenance_work to ce_reader;
grant read on ce_dwh_a.fact_weather_day to ce_reader;
grant read on ce_dwh_a.bridge_booking_room to ce_reader;
grant read on ce_dwh_a.bridge_room_day_maintenance to ce_reader;
grant select,read on ce_stage.validated_booking_service_link_input_a to ce_dwh_a with grant option;
grant read on ce_dwh_a.validated_booking_service_link to ce_reader;
grant select,read on ce_stage.site_crosswalk_input_a to ce_dwh_a with grant option;
grant read on ce_dwh_a.site_crosswalk to ce_reader;
begin execute immediate 'create table ce_stage.pub_probe_a_dim(id number(18,0) primary key,v number(18,0) not null)'; exception when others then if sqlcode<>-955 then raise; end if; end;
/
grant select,insert,delete on ce_stage.pub_probe_a_dim to ce_loader;
grant read on ce_stage.pub_probe_a_dim to ce_reader;
grant select on ce_stage.pub_probe_a_dim to ce_publisher;
begin execute immediate 'create table ce_stage.pub_probe_a_fact(id number(18,0) primary key,v number(18,0) not null)'; exception when others then if sqlcode<>-955 then raise; end if; end;
/
grant select,insert,delete on ce_stage.pub_probe_a_fact to ce_loader;
grant read on ce_stage.pub_probe_a_fact to ce_reader;
grant select on ce_stage.pub_probe_a_fact to ce_publisher;
grant read on ce_dwh_b.dim_date to ce_reader;
grant read on ce_dwh_b.dim_site to ce_reader;
grant read on ce_dwh_b.dim_hotel to ce_reader;
grant read on ce_dwh_b.dim_room to ce_reader;
grant read on ce_dwh_b.dim_channel to ce_reader;
grant read on ce_dwh_b.dim_promotion to ce_reader;
grant read on ce_dwh_b.dim_customer_profile to ce_reader;
grant read on ce_dwh_b.dim_rate_plan to ce_reader;
grant read on ce_dwh_b.dim_outlet to ce_reader;
grant read on ce_dwh_b.dim_meal to ce_reader;
grant read on ce_dwh_b.dim_centre to ce_reader;
grant read on ce_dwh_b.dim_activity to ce_reader;
grant read on ce_dwh_b.dim_vehicle to ce_reader;
grant read on ce_dwh_b.dim_supplier to ce_reader;
grant read on ce_dwh_b.dim_item to ce_reader;
grant read on ce_dwh_b.dim_asset to ce_reader;
grant read on ce_dwh_b.fact_booking to ce_reader;
grant read on ce_dwh_b.fact_room_day to ce_reader;
grant read on ce_dwh_b.fact_stay_night to ce_reader;
grant read on ce_dwh_b.fact_ticket_order to ce_reader;
grant read on ce_dwh_b.fact_rental to ce_reader;
grant read on ce_dwh_b.fact_breakfast_entitlement to ce_reader;
grant read on ce_dwh_b.fact_dining_order to ce_reader;
grant read on ce_dwh_b.fact_meal_session to ce_reader;
grant read on ce_dwh_b.fact_admission to ce_reader;
grant read on ce_dwh_b.fact_activity_day to ce_reader;
grant read on ce_dwh_b.fact_vehicle_day to ce_reader;
grant read on ce_dwh_b.fact_purchase_line to ce_reader;
grant read on ce_dwh_b.fact_receipt to ce_reader;
grant read on ce_dwh_b.fact_stock_movement to ce_reader;
grant read on ce_dwh_b.agg_inventory_lot_day to ce_reader;
grant read on ce_dwh_b.fact_maintenance_work to ce_reader;
grant read on ce_dwh_b.fact_weather_day to ce_reader;
grant read on ce_dwh_b.bridge_booking_room to ce_reader;
grant read on ce_dwh_b.bridge_room_day_maintenance to ce_reader;
grant select,read on ce_stage.validated_booking_service_link_input_b to ce_dwh_b with grant option;
grant read on ce_dwh_b.validated_booking_service_link to ce_reader;
grant select,read on ce_stage.site_crosswalk_input_b to ce_dwh_b with grant option;
grant read on ce_dwh_b.site_crosswalk to ce_reader;
begin execute immediate 'create table ce_stage.pub_probe_b_dim(id number(18,0) primary key,v number(18,0) not null)'; exception when others then if sqlcode<>-955 then raise; end if; end;
/
grant select,insert,delete on ce_stage.pub_probe_b_dim to ce_loader;
grant read on ce_stage.pub_probe_b_dim to ce_reader;
grant select on ce_stage.pub_probe_b_dim to ce_publisher;
begin execute immediate 'create table ce_stage.pub_probe_b_fact(id number(18,0) primary key,v number(18,0) not null)'; exception when others then if sqlcode<>-955 then raise; end if; end;
/
grant select,insert,delete on ce_stage.pub_probe_b_fact to ce_loader;
grant read on ce_stage.pub_probe_b_fact to ce_reader;
grant select on ce_stage.pub_probe_b_fact to ce_publisher;
create or replace trigger ce_dwh_a.pub_guard_d01_a before insert or update or delete on ce_dwh_a.dim_date begin ce_stage.assert_publication_writable('CE_DWH_A'); end;
/
create or replace trigger ce_dwh_a.pub_guard_d02_a before insert or update or delete on ce_dwh_a.dim_site begin ce_stage.assert_publication_writable('CE_DWH_A'); end;
/
create or replace trigger ce_dwh_a.pub_guard_d03_a before insert or update or delete on ce_dwh_a.dim_hotel begin ce_stage.assert_publication_writable('CE_DWH_A'); end;
/
create or replace trigger ce_dwh_a.pub_guard_d04_a before insert or update or delete on ce_dwh_a.dim_room begin ce_stage.assert_publication_writable('CE_DWH_A'); end;
/
create or replace trigger ce_dwh_a.pub_guard_d05_a before insert or update or delete on ce_dwh_a.dim_channel begin ce_stage.assert_publication_writable('CE_DWH_A'); end;
/
create or replace trigger ce_dwh_a.pub_guard_d06_a before insert or update or delete on ce_dwh_a.dim_promotion begin ce_stage.assert_publication_writable('CE_DWH_A'); end;
/
create or replace trigger ce_dwh_a.pub_guard_d07_a before insert or update or delete on ce_dwh_a.dim_customer_profile begin ce_stage.assert_publication_writable('CE_DWH_A'); end;
/
create or replace trigger ce_dwh_a.pub_guard_d08_a before insert or update or delete on ce_dwh_a.dim_rate_plan begin ce_stage.assert_publication_writable('CE_DWH_A'); end;
/
create or replace trigger ce_dwh_a.pub_guard_d09_a before insert or update or delete on ce_dwh_a.dim_outlet begin ce_stage.assert_publication_writable('CE_DWH_A'); end;
/
create or replace trigger ce_dwh_a.pub_guard_d10_a before insert or update or delete on ce_dwh_a.dim_meal begin ce_stage.assert_publication_writable('CE_DWH_A'); end;
/
create or replace trigger ce_dwh_a.pub_guard_d11_a before insert or update or delete on ce_dwh_a.dim_centre begin ce_stage.assert_publication_writable('CE_DWH_A'); end;
/
create or replace trigger ce_dwh_a.pub_guard_d12_a before insert or update or delete on ce_dwh_a.dim_activity begin ce_stage.assert_publication_writable('CE_DWH_A'); end;
/
create or replace trigger ce_dwh_a.pub_guard_d13_a before insert or update or delete on ce_dwh_a.dim_vehicle begin ce_stage.assert_publication_writable('CE_DWH_A'); end;
/
create or replace trigger ce_dwh_a.pub_guard_d14_a before insert or update or delete on ce_dwh_a.dim_supplier begin ce_stage.assert_publication_writable('CE_DWH_A'); end;
/
create or replace trigger ce_dwh_a.pub_guard_d15_a before insert or update or delete on ce_dwh_a.dim_item begin ce_stage.assert_publication_writable('CE_DWH_A'); end;
/
create or replace trigger ce_dwh_a.pub_guard_d16_a before insert or update or delete on ce_dwh_a.dim_asset begin ce_stage.assert_publication_writable('CE_DWH_A'); end;
/
create or replace trigger ce_dwh_a.pub_guard_f01_a before insert or update or delete on ce_dwh_a.fact_booking begin ce_stage.assert_publication_writable('CE_DWH_A'); end;
/
create or replace trigger ce_dwh_a.pub_guard_f02_a before insert or update or delete on ce_dwh_a.fact_room_day begin ce_stage.assert_publication_writable('CE_DWH_A'); end;
/
create or replace trigger ce_dwh_a.pub_guard_f03_a before insert or update or delete on ce_dwh_a.fact_stay_night begin ce_stage.assert_publication_writable('CE_DWH_A'); end;
/
create or replace trigger ce_dwh_a.pub_guard_f04_a before insert or update or delete on ce_dwh_a.fact_ticket_order begin ce_stage.assert_publication_writable('CE_DWH_A'); end;
/
create or replace trigger ce_dwh_a.pub_guard_f05_a before insert or update or delete on ce_dwh_a.fact_rental begin ce_stage.assert_publication_writable('CE_DWH_A'); end;
/
create or replace trigger ce_dwh_a.pub_guard_f06_a before insert or update or delete on ce_dwh_a.fact_breakfast_entitlement begin ce_stage.assert_publication_writable('CE_DWH_A'); end;
/
create or replace trigger ce_dwh_a.pub_guard_f07_a before insert or update or delete on ce_dwh_a.fact_dining_order begin ce_stage.assert_publication_writable('CE_DWH_A'); end;
/
create or replace trigger ce_dwh_a.pub_guard_f08_a before insert or update or delete on ce_dwh_a.fact_meal_session begin ce_stage.assert_publication_writable('CE_DWH_A'); end;
/
create or replace trigger ce_dwh_a.pub_guard_f09_a before insert or update or delete on ce_dwh_a.fact_admission begin ce_stage.assert_publication_writable('CE_DWH_A'); end;
/
create or replace trigger ce_dwh_a.pub_guard_f10_a before insert or update or delete on ce_dwh_a.fact_activity_day begin ce_stage.assert_publication_writable('CE_DWH_A'); end;
/
create or replace trigger ce_dwh_a.pub_guard_f11_a before insert or update or delete on ce_dwh_a.fact_vehicle_day begin ce_stage.assert_publication_writable('CE_DWH_A'); end;
/
create or replace trigger ce_dwh_a.pub_guard_f12_a before insert or update or delete on ce_dwh_a.fact_purchase_line begin ce_stage.assert_publication_writable('CE_DWH_A'); end;
/
create or replace trigger ce_dwh_a.pub_guard_f13_a before insert or update or delete on ce_dwh_a.fact_receipt begin ce_stage.assert_publication_writable('CE_DWH_A'); end;
/
create or replace trigger ce_dwh_a.pub_guard_f14_a before insert or update or delete on ce_dwh_a.fact_stock_movement begin ce_stage.assert_publication_writable('CE_DWH_A'); end;
/
create or replace trigger ce_dwh_a.pub_guard_f15_a before insert or update or delete on ce_dwh_a.agg_inventory_lot_day begin ce_stage.assert_publication_writable('CE_DWH_A'); end;
/
create or replace trigger ce_dwh_a.pub_guard_f16_a before insert or update or delete on ce_dwh_a.fact_maintenance_work begin ce_stage.assert_publication_writable('CE_DWH_A'); end;
/
create or replace trigger ce_dwh_a.pub_guard_f17_a before insert or update or delete on ce_dwh_a.fact_weather_day begin ce_stage.assert_publication_writable('CE_DWH_A'); end;
/
create or replace trigger ce_dwh_a.pub_guard_l01_a before insert or update or delete on ce_dwh_a.bridge_booking_room begin ce_stage.assert_publication_writable('CE_DWH_A'); end;
/
create or replace trigger ce_dwh_a.pub_guard_l02_a before insert or update or delete on ce_dwh_a.bridge_room_day_maintenance begin ce_stage.assert_publication_writable('CE_DWH_A'); end;
/
create or replace trigger ce_stage.pub_guard_l03_a before insert or update or delete on ce_stage.validated_booking_service_link_input_a begin ce_stage.assert_publication_writable('CE_DWH_A'); end;
/
create or replace trigger ce_stage.pub_guard_l04_a before insert or update or delete on ce_stage.site_crosswalk_input_a begin ce_stage.assert_publication_writable('CE_DWH_A'); end;
/
create or replace trigger ce_stage.pub_guard_test_a_dim before insert or update or delete on ce_stage.pub_probe_a_dim begin ce_stage.assert_publication_writable('TEST_A'); end;
/
create or replace trigger ce_stage.pub_guard_test_a_fact before insert or update or delete on ce_stage.pub_probe_a_fact begin ce_stage.assert_publication_writable('TEST_A'); end;
/
create or replace trigger ce_dwh_b.pub_guard_d01_b before insert or update or delete on ce_dwh_b.dim_date begin ce_stage.assert_publication_writable('CE_DWH_B'); end;
/
create or replace trigger ce_dwh_b.pub_guard_d02_b before insert or update or delete on ce_dwh_b.dim_site begin ce_stage.assert_publication_writable('CE_DWH_B'); end;
/
create or replace trigger ce_dwh_b.pub_guard_d03_b before insert or update or delete on ce_dwh_b.dim_hotel begin ce_stage.assert_publication_writable('CE_DWH_B'); end;
/
create or replace trigger ce_dwh_b.pub_guard_d04_b before insert or update or delete on ce_dwh_b.dim_room begin ce_stage.assert_publication_writable('CE_DWH_B'); end;
/
create or replace trigger ce_dwh_b.pub_guard_d05_b before insert or update or delete on ce_dwh_b.dim_channel begin ce_stage.assert_publication_writable('CE_DWH_B'); end;
/
create or replace trigger ce_dwh_b.pub_guard_d06_b before insert or update or delete on ce_dwh_b.dim_promotion begin ce_stage.assert_publication_writable('CE_DWH_B'); end;
/
create or replace trigger ce_dwh_b.pub_guard_d07_b before insert or update or delete on ce_dwh_b.dim_customer_profile begin ce_stage.assert_publication_writable('CE_DWH_B'); end;
/
create or replace trigger ce_dwh_b.pub_guard_d08_b before insert or update or delete on ce_dwh_b.dim_rate_plan begin ce_stage.assert_publication_writable('CE_DWH_B'); end;
/
create or replace trigger ce_dwh_b.pub_guard_d09_b before insert or update or delete on ce_dwh_b.dim_outlet begin ce_stage.assert_publication_writable('CE_DWH_B'); end;
/
create or replace trigger ce_dwh_b.pub_guard_d10_b before insert or update or delete on ce_dwh_b.dim_meal begin ce_stage.assert_publication_writable('CE_DWH_B'); end;
/
create or replace trigger ce_dwh_b.pub_guard_d11_b before insert or update or delete on ce_dwh_b.dim_centre begin ce_stage.assert_publication_writable('CE_DWH_B'); end;
/
create or replace trigger ce_dwh_b.pub_guard_d12_b before insert or update or delete on ce_dwh_b.dim_activity begin ce_stage.assert_publication_writable('CE_DWH_B'); end;
/
create or replace trigger ce_dwh_b.pub_guard_d13_b before insert or update or delete on ce_dwh_b.dim_vehicle begin ce_stage.assert_publication_writable('CE_DWH_B'); end;
/
create or replace trigger ce_dwh_b.pub_guard_d14_b before insert or update or delete on ce_dwh_b.dim_supplier begin ce_stage.assert_publication_writable('CE_DWH_B'); end;
/
create or replace trigger ce_dwh_b.pub_guard_d15_b before insert or update or delete on ce_dwh_b.dim_item begin ce_stage.assert_publication_writable('CE_DWH_B'); end;
/
create or replace trigger ce_dwh_b.pub_guard_d16_b before insert or update or delete on ce_dwh_b.dim_asset begin ce_stage.assert_publication_writable('CE_DWH_B'); end;
/
create or replace trigger ce_dwh_b.pub_guard_f01_b before insert or update or delete on ce_dwh_b.fact_booking begin ce_stage.assert_publication_writable('CE_DWH_B'); end;
/
create or replace trigger ce_dwh_b.pub_guard_f02_b before insert or update or delete on ce_dwh_b.fact_room_day begin ce_stage.assert_publication_writable('CE_DWH_B'); end;
/
create or replace trigger ce_dwh_b.pub_guard_f03_b before insert or update or delete on ce_dwh_b.fact_stay_night begin ce_stage.assert_publication_writable('CE_DWH_B'); end;
/
create or replace trigger ce_dwh_b.pub_guard_f04_b before insert or update or delete on ce_dwh_b.fact_ticket_order begin ce_stage.assert_publication_writable('CE_DWH_B'); end;
/
create or replace trigger ce_dwh_b.pub_guard_f05_b before insert or update or delete on ce_dwh_b.fact_rental begin ce_stage.assert_publication_writable('CE_DWH_B'); end;
/
create or replace trigger ce_dwh_b.pub_guard_f06_b before insert or update or delete on ce_dwh_b.fact_breakfast_entitlement begin ce_stage.assert_publication_writable('CE_DWH_B'); end;
/
create or replace trigger ce_dwh_b.pub_guard_f07_b before insert or update or delete on ce_dwh_b.fact_dining_order begin ce_stage.assert_publication_writable('CE_DWH_B'); end;
/
create or replace trigger ce_dwh_b.pub_guard_f08_b before insert or update or delete on ce_dwh_b.fact_meal_session begin ce_stage.assert_publication_writable('CE_DWH_B'); end;
/
create or replace trigger ce_dwh_b.pub_guard_f09_b before insert or update or delete on ce_dwh_b.fact_admission begin ce_stage.assert_publication_writable('CE_DWH_B'); end;
/
create or replace trigger ce_dwh_b.pub_guard_f10_b before insert or update or delete on ce_dwh_b.fact_activity_day begin ce_stage.assert_publication_writable('CE_DWH_B'); end;
/
create or replace trigger ce_dwh_b.pub_guard_f11_b before insert or update or delete on ce_dwh_b.fact_vehicle_day begin ce_stage.assert_publication_writable('CE_DWH_B'); end;
/
create or replace trigger ce_dwh_b.pub_guard_f12_b before insert or update or delete on ce_dwh_b.fact_purchase_line begin ce_stage.assert_publication_writable('CE_DWH_B'); end;
/
create or replace trigger ce_dwh_b.pub_guard_f13_b before insert or update or delete on ce_dwh_b.fact_receipt begin ce_stage.assert_publication_writable('CE_DWH_B'); end;
/
create or replace trigger ce_dwh_b.pub_guard_f14_b before insert or update or delete on ce_dwh_b.fact_stock_movement begin ce_stage.assert_publication_writable('CE_DWH_B'); end;
/
create or replace trigger ce_dwh_b.pub_guard_f15_b before insert or update or delete on ce_dwh_b.agg_inventory_lot_day begin ce_stage.assert_publication_writable('CE_DWH_B'); end;
/
create or replace trigger ce_dwh_b.pub_guard_f16_b before insert or update or delete on ce_dwh_b.fact_maintenance_work begin ce_stage.assert_publication_writable('CE_DWH_B'); end;
/
create or replace trigger ce_dwh_b.pub_guard_f17_b before insert or update or delete on ce_dwh_b.fact_weather_day begin ce_stage.assert_publication_writable('CE_DWH_B'); end;
/
create or replace trigger ce_dwh_b.pub_guard_l01_b before insert or update or delete on ce_dwh_b.bridge_booking_room begin ce_stage.assert_publication_writable('CE_DWH_B'); end;
/
create or replace trigger ce_dwh_b.pub_guard_l02_b before insert or update or delete on ce_dwh_b.bridge_room_day_maintenance begin ce_stage.assert_publication_writable('CE_DWH_B'); end;
/
create or replace trigger ce_stage.pub_guard_l03_b before insert or update or delete on ce_stage.validated_booking_service_link_input_b begin ce_stage.assert_publication_writable('CE_DWH_B'); end;
/
create or replace trigger ce_stage.pub_guard_l04_b before insert or update or delete on ce_stage.site_crosswalk_input_b begin ce_stage.assert_publication_writable('CE_DWH_B'); end;
/
create or replace trigger ce_stage.pub_guard_test_b_dim before insert or update or delete on ce_stage.pub_probe_b_dim begin ce_stage.assert_publication_writable('TEST_B'); end;
/
create or replace trigger ce_stage.pub_guard_test_b_fact before insert or update or delete on ce_stage.pub_probe_b_fact begin ce_stage.assert_publication_writable('TEST_B'); end;
/
exit
