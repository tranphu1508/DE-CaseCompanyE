set echo off verify off define off feedback off
whenever sqlerror exit sql.sqlcode
whenever oserror exit failure
alter session set container=FREEPDB1;
DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tablespaces WHERE tablespace_name='CE_DATA'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLESPACE ce_data DATAFILE ''/opt/oracle/oradata/FREE/FREEPDB1/ce_data01.dbf'' SIZE 256M AUTOEXTEND ON NEXT 64M MAXSIZE 8G'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tablespaces WHERE tablespace_name='CE_STAGE_DATA'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLESPACE ce_stage_data DATAFILE ''/opt/oracle/oradata/FREE/FREEPDB1/ce_stage_data01.dbf'' SIZE 256M AUTOEXTEND ON NEXT 64M MAXSIZE 1G'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_users WHERE username='CE_DWH_A'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE USER ce_dwh_a NO AUTHENTICATION DEFAULT TABLESPACE ce_data QUOTA 8G ON ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_users WHERE username='CE_DWH_B'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE USER ce_dwh_b NO AUTHENTICATION DEFAULT TABLESPACE ce_data QUOTA 8G ON ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_users WHERE username='CE_STAGE'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE USER ce_stage NO AUTHENTICATION DEFAULT TABLESPACE ce_stage_data QUOTA 1G ON ce_stage_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_A' AND table_name='DIM_DATE'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_a.dim_date (
  date_key NUMBER(8,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  member_kind VARCHAR2(64 CHAR) NOT NULL,
  calendar_date DATE,
  day NUMBER(10,0),
  day_of_week NUMBER(10,0),
  month NUMBER(10,0),
  quarter NUMBER(10,0),
  year NUMBER(10,0),
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='PK_D01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_date ADD CONSTRAINT pk_d01 PRIMARY KEY (date_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='UK_D01_1'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_date ADD CONSTRAINT uk_d01_1 UNIQUE (calendar_date) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D01_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_date ADD CONSTRAINT ck_d01_01 CHECK (date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D01_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_date ADD CONSTRAINT ck_d01_02 CHECK (calendar_date=TRUNC(calendar_date))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D01_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_date ADD CONSTRAINT ck_d01_03 CHECK (day BETWEEN -2147483648 AND 2147483647)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D01_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_date ADD CONSTRAINT ck_d01_04 CHECK (day_of_week BETWEEN -2147483648 AND 2147483647)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D01_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_date ADD CONSTRAINT ck_d01_05 CHECK (month BETWEEN -2147483648 AND 2147483647)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D01_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_date ADD CONSTRAINT ck_d01_06 CHECK (quarter BETWEEN -2147483648 AND 2147483647)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D01_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_date ADD CONSTRAINT ck_d01_07 CHECK (year BETWEEN -2147483648 AND 2147483647)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D01_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_date ADD CONSTRAINT ck_d01_08 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D01_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_date ADD CONSTRAINT ck_d01_09 CHECK ((member_kind=''NORMAL'' AND date_key>0) OR (member_kind=''UNKNOWN'' AND date_key=0) OR (member_kind=''NOT_APPLICABLE'' AND date_key=-1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D01_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_date ADD CONSTRAINT ck_d01_10 CHECK (member_kind<>''NORMAL'' OR (calendar_date IS NOT NULL AND day IS NOT NULL AND day_of_week IS NOT NULL AND month IS NOT NULL AND quarter IS NOT NULL AND year IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D01_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_date ADD CONSTRAINT ck_d01_11 CHECK (member_kind<>''NORMAL'' OR date_key=TO_NUMBER(TO_CHAR(calendar_date,''YYYYMMDD'')))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D01_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_date ADD CONSTRAINT ck_d01_12 CHECK (member_kind<>''NORMAL'' OR year=EXTRACT(YEAR FROM calendar_date))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D01_13'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_date ADD CONSTRAINT ck_d01_13 CHECK (member_kind<>''NORMAL'' OR month=EXTRACT(MONTH FROM calendar_date))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D01_14'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_date ADD CONSTRAINT ck_d01_14 CHECK (member_kind<>''NORMAL'' OR day=EXTRACT(DAY FROM calendar_date))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D01_15'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_date ADD CONSTRAINT ck_d01_15 CHECK (member_kind<>''NORMAL'' OR quarter=CEIL(month/3.0))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D01_16'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_date ADD CONSTRAINT ck_d01_16 CHECK (member_kind<>''NORMAL'' OR day_of_week=calendar_date-TRUNC(calendar_date,''IW'')+1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_A' AND table_name='DIM_SITE'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_a.dim_site (
  site_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  member_kind VARCHAR2(64 CHAR) NOT NULL,
  site_id VARCHAR2(128 CHAR),
  site_name VARCHAR2(512 CHAR),
  climate_region VARCHAR2(512 CHAR),
  valid_from_utc TIMESTAMP(6) NOT NULL,
  valid_to_utc TIMESTAMP(6),
  is_current NUMBER(1,0) NOT NULL,
  version_no NUMBER(18,0) NOT NULL,
  effective_time_basis VARCHAR2(64 CHAR) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='PK_D02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_site ADD CONSTRAINT pk_d02 PRIMARY KEY (site_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UK_D02_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uk_d02_1 ON ce_dwh_a.dim_site (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN site_id END,CASE WHEN member_kind=''NORMAL'' THEN valid_from_utc END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UK_D02_2'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uk_d02_2 ON ce_dwh_a.dim_site (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN site_id END,CASE WHEN member_kind=''NORMAL'' THEN version_no END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UC_D02_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uc_d02_1 ON ce_dwh_a.dim_site (CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN source_system END,CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN site_id END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D02_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_site ADD CONSTRAINT ck_d02_01 CHECK (site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D02_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_site ADD CONSTRAINT ck_d02_02 CHECK (is_current IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D02_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_site ADD CONSTRAINT ck_d02_03 CHECK (version_no>=0 AND version_no<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D02_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_site ADD CONSTRAINT ck_d02_04 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D02_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_site ADD CONSTRAINT ck_d02_05 CHECK ((member_kind=''NORMAL'' AND site_key>0) OR (member_kind=''UNKNOWN'' AND site_key=0) OR (member_kind=''NOT_APPLICABLE'' AND site_key=-1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D02_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_site ADD CONSTRAINT ck_d02_06 CHECK (member_kind<>''NORMAL'' OR (site_id IS NOT NULL AND site_name IS NOT NULL AND climate_region IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D02_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_site ADD CONSTRAINT ck_d02_07 CHECK (version_no>=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D02_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_site ADD CONSTRAINT ck_d02_08 CHECK ((is_current=1 AND valid_to_utc IS NULL) OR (is_current=0 AND valid_to_utc IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D02_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_site ADD CONSTRAINT ck_d02_09 CHECK (valid_to_utc IS NULL OR valid_from_utc<valid_to_utc)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D02_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_site ADD CONSTRAINT ck_d02_10 CHECK (member_kind=''NORMAL'' OR (version_no=1 AND is_current=1 AND valid_to_utc IS NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_A' AND table_name='DIM_HOTEL'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_a.dim_hotel (
  hotel_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  member_kind VARCHAR2(64 CHAR) NOT NULL,
  hotel_id VARCHAR2(128 CHAR),
  hotel_name VARCHAR2(512 CHAR),
  stars NUMBER(10,0),
  site_id VARCHAR2(128 CHAR),
  website_channel VARCHAR2(512 CHAR),
  valid_from_utc TIMESTAMP(6) NOT NULL,
  valid_to_utc TIMESTAMP(6),
  is_current NUMBER(1,0) NOT NULL,
  version_no NUMBER(18,0) NOT NULL,
  effective_time_basis VARCHAR2(64 CHAR) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='PK_D03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_hotel ADD CONSTRAINT pk_d03 PRIMARY KEY (hotel_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UK_D03_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uk_d03_1 ON ce_dwh_a.dim_hotel (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN hotel_id END,CASE WHEN member_kind=''NORMAL'' THEN valid_from_utc END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UK_D03_2'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uk_d03_2 ON ce_dwh_a.dim_hotel (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN hotel_id END,CASE WHEN member_kind=''NORMAL'' THEN version_no END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UC_D03_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uc_d03_1 ON ce_dwh_a.dim_hotel (CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN source_system END,CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN hotel_id END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D03_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_hotel ADD CONSTRAINT ck_d03_01 CHECK (hotel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D03_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_hotel ADD CONSTRAINT ck_d03_02 CHECK (stars BETWEEN -2147483648 AND 2147483647)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D03_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_hotel ADD CONSTRAINT ck_d03_03 CHECK (is_current IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D03_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_hotel ADD CONSTRAINT ck_d03_04 CHECK (version_no>=0 AND version_no<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D03_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_hotel ADD CONSTRAINT ck_d03_05 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D03_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_hotel ADD CONSTRAINT ck_d03_06 CHECK ((member_kind=''NORMAL'' AND hotel_key>0) OR (member_kind=''UNKNOWN'' AND hotel_key=0) OR (member_kind=''NOT_APPLICABLE'' AND hotel_key=-1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D03_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_hotel ADD CONSTRAINT ck_d03_07 CHECK (member_kind<>''NORMAL'' OR (hotel_id IS NOT NULL AND hotel_name IS NOT NULL AND stars IS NOT NULL AND site_id IS NOT NULL AND website_channel IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D03_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_hotel ADD CONSTRAINT ck_d03_08 CHECK (version_no>=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D03_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_hotel ADD CONSTRAINT ck_d03_09 CHECK ((is_current=1 AND valid_to_utc IS NULL) OR (is_current=0 AND valid_to_utc IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D03_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_hotel ADD CONSTRAINT ck_d03_10 CHECK (valid_to_utc IS NULL OR valid_from_utc<valid_to_utc)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D03_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_hotel ADD CONSTRAINT ck_d03_11 CHECK (member_kind=''NORMAL'' OR (version_no=1 AND is_current=1 AND valid_to_utc IS NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D03_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_hotel ADD CONSTRAINT ck_d03_12 CHECK (member_kind<>''NORMAL'' OR (stars IN (3,5)))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_A' AND table_name='DIM_ROOM'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_a.dim_room (
  room_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  member_kind VARCHAR2(64 CHAR) NOT NULL,
  room_id VARCHAR2(128 CHAR),
  hotel_id VARCHAR2(128 CHAR),
  room_type VARCHAR2(512 CHAR),
  capacity NUMBER(10,0),
  base_rate_vnd NUMBER(19,0),
  valid_from_utc TIMESTAMP(6) NOT NULL,
  valid_to_utc TIMESTAMP(6),
  is_current NUMBER(1,0) NOT NULL,
  version_no NUMBER(18,0) NOT NULL,
  effective_time_basis VARCHAR2(64 CHAR) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='PK_D04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_room ADD CONSTRAINT pk_d04 PRIMARY KEY (room_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UK_D04_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uk_d04_1 ON ce_dwh_a.dim_room (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN room_id END,CASE WHEN member_kind=''NORMAL'' THEN valid_from_utc END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UK_D04_2'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uk_d04_2 ON ce_dwh_a.dim_room (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN room_id END,CASE WHEN member_kind=''NORMAL'' THEN version_no END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UC_D04_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uc_d04_1 ON ce_dwh_a.dim_room (CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN source_system END,CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN room_id END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D04_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_room ADD CONSTRAINT ck_d04_01 CHECK (room_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D04_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_room ADD CONSTRAINT ck_d04_02 CHECK (capacity BETWEEN -2147483648 AND 2147483647)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D04_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_room ADD CONSTRAINT ck_d04_03 CHECK (is_current IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D04_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_room ADD CONSTRAINT ck_d04_04 CHECK (version_no>=0 AND version_no<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D04_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_room ADD CONSTRAINT ck_d04_05 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D04_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_room ADD CONSTRAINT ck_d04_06 CHECK ((member_kind=''NORMAL'' AND room_key>0) OR (member_kind=''UNKNOWN'' AND room_key=0) OR (member_kind=''NOT_APPLICABLE'' AND room_key=-1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D04_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_room ADD CONSTRAINT ck_d04_07 CHECK (member_kind<>''NORMAL'' OR (room_id IS NOT NULL AND hotel_id IS NOT NULL AND room_type IS NOT NULL AND capacity IS NOT NULL AND base_rate_vnd IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D04_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_room ADD CONSTRAINT ck_d04_08 CHECK (version_no>=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D04_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_room ADD CONSTRAINT ck_d04_09 CHECK ((is_current=1 AND valid_to_utc IS NULL) OR (is_current=0 AND valid_to_utc IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D04_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_room ADD CONSTRAINT ck_d04_10 CHECK (valid_to_utc IS NULL OR valid_from_utc<valid_to_utc)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D04_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_room ADD CONSTRAINT ck_d04_11 CHECK (member_kind=''NORMAL'' OR (version_no=1 AND is_current=1 AND valid_to_utc IS NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D04_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_room ADD CONSTRAINT ck_d04_12 CHECK (member_kind<>''NORMAL'' OR (capacity>0))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D04_13'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_room ADD CONSTRAINT ck_d04_13 CHECK (member_kind<>''NORMAL'' OR (base_rate_vnd>0))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_A' AND table_name='DIM_CHANNEL'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_a.dim_channel (
  channel_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  member_kind VARCHAR2(64 CHAR) NOT NULL,
  channel_code VARCHAR2(128 CHAR),
  channel_name VARCHAR2(512 CHAR),
  channel_type VARCHAR2(512 CHAR),
  commission_bps NUMBER(10,0),
  valid_from_utc TIMESTAMP(6) NOT NULL,
  valid_to_utc TIMESTAMP(6),
  is_current NUMBER(1,0) NOT NULL,
  version_no NUMBER(18,0) NOT NULL,
  effective_time_basis VARCHAR2(64 CHAR) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='PK_D05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_channel ADD CONSTRAINT pk_d05 PRIMARY KEY (channel_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UK_D05_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uk_d05_1 ON ce_dwh_a.dim_channel (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN channel_code END,CASE WHEN member_kind=''NORMAL'' THEN valid_from_utc END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UK_D05_2'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uk_d05_2 ON ce_dwh_a.dim_channel (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN channel_code END,CASE WHEN member_kind=''NORMAL'' THEN version_no END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UC_D05_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uc_d05_1 ON ce_dwh_a.dim_channel (CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN source_system END,CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN channel_code END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D05_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_channel ADD CONSTRAINT ck_d05_01 CHECK (channel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D05_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_channel ADD CONSTRAINT ck_d05_02 CHECK (commission_bps BETWEEN -2147483648 AND 2147483647)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D05_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_channel ADD CONSTRAINT ck_d05_03 CHECK (is_current IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D05_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_channel ADD CONSTRAINT ck_d05_04 CHECK (version_no>=0 AND version_no<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D05_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_channel ADD CONSTRAINT ck_d05_05 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D05_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_channel ADD CONSTRAINT ck_d05_06 CHECK ((member_kind=''NORMAL'' AND channel_key>0) OR (member_kind=''UNKNOWN'' AND channel_key=0) OR (member_kind=''NOT_APPLICABLE'' AND channel_key=-1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D05_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_channel ADD CONSTRAINT ck_d05_07 CHECK (member_kind<>''NORMAL'' OR (channel_code IS NOT NULL AND channel_name IS NOT NULL AND channel_type IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D05_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_channel ADD CONSTRAINT ck_d05_08 CHECK (version_no>=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D05_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_channel ADD CONSTRAINT ck_d05_09 CHECK ((is_current=1 AND valid_to_utc IS NULL) OR (is_current=0 AND valid_to_utc IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D05_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_channel ADD CONSTRAINT ck_d05_10 CHECK (valid_to_utc IS NULL OR valid_from_utc<valid_to_utc)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D05_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_channel ADD CONSTRAINT ck_d05_11 CHECK (member_kind=''NORMAL'' OR (version_no=1 AND is_current=1 AND valid_to_utc IS NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D05_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_channel ADD CONSTRAINT ck_d05_12 CHECK (member_kind<>''NORMAL'' OR (commission_bps BETWEEN 0 AND 10000))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_A' AND table_name='DIM_PROMOTION'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_a.dim_promotion (
  promotion_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  member_kind VARCHAR2(64 CHAR) NOT NULL,
  promotion_id VARCHAR2(128 CHAR),
  promotion_name VARCHAR2(512 CHAR),
  channel_id VARCHAR2(128 CHAR),
  site_id VARCHAR2(128 CHAR),
  sale_from DATE,
  sale_to DATE,
  stay_from DATE,
  stay_to DATE,
  discount_bps NUMBER(10,0),
  partner_share_bps NUMBER(10,0),
  cap_vnd NUMBER(19,0),
  valid_from_utc TIMESTAMP(6) NOT NULL,
  valid_to_utc TIMESTAMP(6),
  is_current NUMBER(1,0) NOT NULL,
  version_no NUMBER(18,0) NOT NULL,
  effective_time_basis VARCHAR2(64 CHAR) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='PK_D06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_promotion ADD CONSTRAINT pk_d06 PRIMARY KEY (promotion_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UK_D06_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uk_d06_1 ON ce_dwh_a.dim_promotion (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN promotion_id END,CASE WHEN member_kind=''NORMAL'' THEN valid_from_utc END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UK_D06_2'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uk_d06_2 ON ce_dwh_a.dim_promotion (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN promotion_id END,CASE WHEN member_kind=''NORMAL'' THEN version_no END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UC_D06_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uc_d06_1 ON ce_dwh_a.dim_promotion (CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN source_system END,CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN promotion_id END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D06_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_promotion ADD CONSTRAINT ck_d06_01 CHECK (promotion_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D06_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_promotion ADD CONSTRAINT ck_d06_02 CHECK (sale_from=TRUNC(sale_from))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D06_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_promotion ADD CONSTRAINT ck_d06_03 CHECK (sale_to=TRUNC(sale_to))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D06_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_promotion ADD CONSTRAINT ck_d06_04 CHECK (stay_from=TRUNC(stay_from))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D06_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_promotion ADD CONSTRAINT ck_d06_05 CHECK (stay_to=TRUNC(stay_to))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D06_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_promotion ADD CONSTRAINT ck_d06_06 CHECK (discount_bps BETWEEN -2147483648 AND 2147483647)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D06_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_promotion ADD CONSTRAINT ck_d06_07 CHECK (partner_share_bps BETWEEN -2147483648 AND 2147483647)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D06_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_promotion ADD CONSTRAINT ck_d06_08 CHECK (is_current IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D06_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_promotion ADD CONSTRAINT ck_d06_09 CHECK (version_no>=0 AND version_no<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D06_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_promotion ADD CONSTRAINT ck_d06_10 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D06_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_promotion ADD CONSTRAINT ck_d06_11 CHECK ((member_kind=''NORMAL'' AND promotion_key>0) OR (member_kind=''UNKNOWN'' AND promotion_key=0) OR (member_kind=''NOT_APPLICABLE'' AND promotion_key=-1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D06_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_promotion ADD CONSTRAINT ck_d06_12 CHECK (member_kind<>''NORMAL'' OR (promotion_id IS NOT NULL AND promotion_name IS NOT NULL AND sale_from IS NOT NULL AND sale_to IS NOT NULL AND stay_from IS NOT NULL AND stay_to IS NOT NULL AND discount_bps IS NOT NULL AND partner_share_bps IS NOT NULL AND cap_vnd IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D06_13'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_promotion ADD CONSTRAINT ck_d06_13 CHECK (version_no>=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D06_14'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_promotion ADD CONSTRAINT ck_d06_14 CHECK ((is_current=1 AND valid_to_utc IS NULL) OR (is_current=0 AND valid_to_utc IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D06_15'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_promotion ADD CONSTRAINT ck_d06_15 CHECK (valid_to_utc IS NULL OR valid_from_utc<valid_to_utc)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D06_16'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_promotion ADD CONSTRAINT ck_d06_16 CHECK (member_kind=''NORMAL'' OR (version_no=1 AND is_current=1 AND valid_to_utc IS NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D06_17'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_promotion ADD CONSTRAINT ck_d06_17 CHECK (member_kind<>''NORMAL'' OR (discount_bps BETWEEN 0 AND 10000))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D06_18'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_promotion ADD CONSTRAINT ck_d06_18 CHECK (member_kind<>''NORMAL'' OR (partner_share_bps BETWEEN 0 AND 10000))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D06_19'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_promotion ADD CONSTRAINT ck_d06_19 CHECK (member_kind<>''NORMAL'' OR (cap_vnd>=0))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D06_20'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_promotion ADD CONSTRAINT ck_d06_20 CHECK (member_kind<>''NORMAL'' OR (sale_to>=sale_from))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D06_21'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_promotion ADD CONSTRAINT ck_d06_21 CHECK (member_kind<>''NORMAL'' OR (stay_to>=stay_from))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_A' AND table_name='DIM_CUSTOMER_PROFILE'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_a.dim_customer_profile (
  customer_profile_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  member_kind VARCHAR2(64 CHAR) NOT NULL,
  source_customer_id VARCHAR2(128 CHAR),
  full_name VARCHAR2(512 CHAR),
  phone VARCHAR2(512 CHAR),
  email VARCHAR2(512 CHAR),
  member_card_ref VARCHAR2(128 CHAR),
  valid_from_utc TIMESTAMP(6) NOT NULL,
  valid_to_utc TIMESTAMP(6),
  is_current NUMBER(1,0) NOT NULL,
  version_no NUMBER(18,0) NOT NULL,
  effective_time_basis VARCHAR2(64 CHAR) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='PK_D07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_customer_profile ADD CONSTRAINT pk_d07 PRIMARY KEY (customer_profile_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UK_D07_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uk_d07_1 ON ce_dwh_a.dim_customer_profile (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN source_customer_id END,CASE WHEN member_kind=''NORMAL'' THEN valid_from_utc END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UK_D07_2'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uk_d07_2 ON ce_dwh_a.dim_customer_profile (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN source_customer_id END,CASE WHEN member_kind=''NORMAL'' THEN version_no END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UC_D07_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uc_d07_1 ON ce_dwh_a.dim_customer_profile (CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN source_system END,CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN source_customer_id END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D07_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_customer_profile ADD CONSTRAINT ck_d07_01 CHECK (customer_profile_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D07_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_customer_profile ADD CONSTRAINT ck_d07_02 CHECK (is_current IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D07_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_customer_profile ADD CONSTRAINT ck_d07_03 CHECK (version_no>=0 AND version_no<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D07_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_customer_profile ADD CONSTRAINT ck_d07_04 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D07_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_customer_profile ADD CONSTRAINT ck_d07_05 CHECK ((member_kind=''NORMAL'' AND customer_profile_key>0) OR (member_kind=''UNKNOWN'' AND customer_profile_key=0) OR (member_kind=''NOT_APPLICABLE'' AND customer_profile_key=-1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D07_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_customer_profile ADD CONSTRAINT ck_d07_06 CHECK (member_kind<>''NORMAL'' OR (source_customer_id IS NOT NULL AND full_name IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D07_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_customer_profile ADD CONSTRAINT ck_d07_07 CHECK (version_no>=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D07_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_customer_profile ADD CONSTRAINT ck_d07_08 CHECK ((is_current=1 AND valid_to_utc IS NULL) OR (is_current=0 AND valid_to_utc IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D07_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_customer_profile ADD CONSTRAINT ck_d07_09 CHECK (valid_to_utc IS NULL OR valid_from_utc<valid_to_utc)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D07_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_customer_profile ADD CONSTRAINT ck_d07_10 CHECK (member_kind=''NORMAL'' OR (version_no=1 AND is_current=1 AND valid_to_utc IS NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_A' AND table_name='DIM_RATE_PLAN'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_a.dim_rate_plan (
  rate_plan_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  member_kind VARCHAR2(64 CHAR) NOT NULL,
  rate_plan_id VARCHAR2(128 CHAR),
  hotel_id VARCHAR2(128 CHAR),
  channel_id VARCHAR2(128 CHAR),
  plan_name VARCHAR2(512 CHAR),
  breakfast_included NUMBER(1,0),
  refundable NUMBER(1,0),
  valid_from_utc TIMESTAMP(6) NOT NULL,
  valid_to_utc TIMESTAMP(6),
  is_current NUMBER(1,0) NOT NULL,
  version_no NUMBER(18,0) NOT NULL,
  effective_time_basis VARCHAR2(64 CHAR) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='PK_D08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_rate_plan ADD CONSTRAINT pk_d08 PRIMARY KEY (rate_plan_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UK_D08_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uk_d08_1 ON ce_dwh_a.dim_rate_plan (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN rate_plan_id END,CASE WHEN member_kind=''NORMAL'' THEN valid_from_utc END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UK_D08_2'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uk_d08_2 ON ce_dwh_a.dim_rate_plan (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN rate_plan_id END,CASE WHEN member_kind=''NORMAL'' THEN version_no END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UC_D08_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uc_d08_1 ON ce_dwh_a.dim_rate_plan (CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN source_system END,CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN rate_plan_id END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D08_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_rate_plan ADD CONSTRAINT ck_d08_01 CHECK (rate_plan_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D08_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_rate_plan ADD CONSTRAINT ck_d08_02 CHECK (breakfast_included IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D08_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_rate_plan ADD CONSTRAINT ck_d08_03 CHECK (refundable IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D08_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_rate_plan ADD CONSTRAINT ck_d08_04 CHECK (is_current IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D08_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_rate_plan ADD CONSTRAINT ck_d08_05 CHECK (version_no>=0 AND version_no<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D08_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_rate_plan ADD CONSTRAINT ck_d08_06 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D08_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_rate_plan ADD CONSTRAINT ck_d08_07 CHECK ((member_kind=''NORMAL'' AND rate_plan_key>0) OR (member_kind=''UNKNOWN'' AND rate_plan_key=0) OR (member_kind=''NOT_APPLICABLE'' AND rate_plan_key=-1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D08_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_rate_plan ADD CONSTRAINT ck_d08_08 CHECK (member_kind<>''NORMAL'' OR (rate_plan_id IS NOT NULL AND hotel_id IS NOT NULL AND channel_id IS NOT NULL AND plan_name IS NOT NULL AND breakfast_included IS NOT NULL AND refundable IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D08_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_rate_plan ADD CONSTRAINT ck_d08_09 CHECK (version_no>=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D08_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_rate_plan ADD CONSTRAINT ck_d08_10 CHECK ((is_current=1 AND valid_to_utc IS NULL) OR (is_current=0 AND valid_to_utc IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D08_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_rate_plan ADD CONSTRAINT ck_d08_11 CHECK (valid_to_utc IS NULL OR valid_from_utc<valid_to_utc)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D08_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_rate_plan ADD CONSTRAINT ck_d08_12 CHECK (member_kind=''NORMAL'' OR (version_no=1 AND is_current=1 AND valid_to_utc IS NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_A' AND table_name='DIM_OUTLET'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_a.dim_outlet (
  outlet_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  member_kind VARCHAR2(64 CHAR) NOT NULL,
  outlet_id VARCHAR2(128 CHAR),
  hotel_id VARCHAR2(128 CHAR),
  outlet_type VARCHAR2(512 CHAR),
  capacity NUMBER(10,0),
  quality_profile NUMBER(10,0),
  valid_from_utc TIMESTAMP(6) NOT NULL,
  valid_to_utc TIMESTAMP(6),
  is_current NUMBER(1,0) NOT NULL,
  version_no NUMBER(18,0) NOT NULL,
  effective_time_basis VARCHAR2(64 CHAR) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='PK_D09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_outlet ADD CONSTRAINT pk_d09 PRIMARY KEY (outlet_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UK_D09_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uk_d09_1 ON ce_dwh_a.dim_outlet (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN outlet_id END,CASE WHEN member_kind=''NORMAL'' THEN valid_from_utc END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UK_D09_2'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uk_d09_2 ON ce_dwh_a.dim_outlet (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN outlet_id END,CASE WHEN member_kind=''NORMAL'' THEN version_no END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UC_D09_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uc_d09_1 ON ce_dwh_a.dim_outlet (CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN source_system END,CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN outlet_id END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D09_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_outlet ADD CONSTRAINT ck_d09_01 CHECK (outlet_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D09_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_outlet ADD CONSTRAINT ck_d09_02 CHECK (capacity BETWEEN -2147483648 AND 2147483647)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D09_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_outlet ADD CONSTRAINT ck_d09_03 CHECK (quality_profile BETWEEN -2147483648 AND 2147483647)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D09_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_outlet ADD CONSTRAINT ck_d09_04 CHECK (is_current IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D09_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_outlet ADD CONSTRAINT ck_d09_05 CHECK (version_no>=0 AND version_no<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D09_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_outlet ADD CONSTRAINT ck_d09_06 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D09_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_outlet ADD CONSTRAINT ck_d09_07 CHECK ((member_kind=''NORMAL'' AND outlet_key>0) OR (member_kind=''UNKNOWN'' AND outlet_key=0) OR (member_kind=''NOT_APPLICABLE'' AND outlet_key=-1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D09_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_outlet ADD CONSTRAINT ck_d09_08 CHECK (member_kind<>''NORMAL'' OR (outlet_id IS NOT NULL AND hotel_id IS NOT NULL AND outlet_type IS NOT NULL AND capacity IS NOT NULL AND quality_profile IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D09_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_outlet ADD CONSTRAINT ck_d09_09 CHECK (version_no>=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D09_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_outlet ADD CONSTRAINT ck_d09_10 CHECK ((is_current=1 AND valid_to_utc IS NULL) OR (is_current=0 AND valid_to_utc IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D09_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_outlet ADD CONSTRAINT ck_d09_11 CHECK (valid_to_utc IS NULL OR valid_from_utc<valid_to_utc)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D09_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_outlet ADD CONSTRAINT ck_d09_12 CHECK (member_kind=''NORMAL'' OR (version_no=1 AND is_current=1 AND valid_to_utc IS NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D09_13'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_outlet ADD CONSTRAINT ck_d09_13 CHECK (member_kind<>''NORMAL'' OR (outlet_type IN (''RESTAURANT'',''BAR'')))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D09_14'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_outlet ADD CONSTRAINT ck_d09_14 CHECK (member_kind<>''NORMAL'' OR (capacity>0))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_A' AND table_name='DIM_MEAL'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_a.dim_meal (
  meal_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  member_kind VARCHAR2(64 CHAR) NOT NULL,
  meal_code VARCHAR2(64 CHAR),
  meal_name VARCHAR2(512 CHAR),
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='PK_D10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_meal ADD CONSTRAINT pk_d10 PRIMARY KEY (meal_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='UK_D10_1'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_meal ADD CONSTRAINT uk_d10_1 UNIQUE (meal_code) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D10_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_meal ADD CONSTRAINT ck_d10_01 CHECK (meal_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D10_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_meal ADD CONSTRAINT ck_d10_02 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D10_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_meal ADD CONSTRAINT ck_d10_03 CHECK ((member_kind=''NORMAL'' AND meal_key>0) OR (member_kind=''UNKNOWN'' AND meal_key=0) OR (member_kind=''NOT_APPLICABLE'' AND meal_key=-1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D10_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_meal ADD CONSTRAINT ck_d10_04 CHECK (member_kind<>''NORMAL'' OR (meal_code IS NOT NULL AND meal_name IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D10_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_meal ADD CONSTRAINT ck_d10_05 CHECK (member_kind<>''NORMAL'' OR (meal_key=1 AND meal_code=''BREAKFAST'') OR (meal_key=2 AND meal_code=''LUNCH'') OR (meal_key=3 AND meal_code=''DINNER'') OR (meal_key=4 AND meal_code=''BAR''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_A' AND table_name='DIM_CENTRE'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_a.dim_centre (
  centre_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  member_kind VARCHAR2(64 CHAR) NOT NULL,
  centre_id VARCHAR2(128 CHAR),
  centre_name VARCHAR2(512 CHAR),
  site_code VARCHAR2(128 CHAR),
  valid_from_utc TIMESTAMP(6) NOT NULL,
  valid_to_utc TIMESTAMP(6),
  is_current NUMBER(1,0) NOT NULL,
  version_no NUMBER(18,0) NOT NULL,
  effective_time_basis VARCHAR2(64 CHAR) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='PK_D11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_centre ADD CONSTRAINT pk_d11 PRIMARY KEY (centre_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UK_D11_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uk_d11_1 ON ce_dwh_a.dim_centre (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN centre_id END,CASE WHEN member_kind=''NORMAL'' THEN valid_from_utc END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UK_D11_2'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uk_d11_2 ON ce_dwh_a.dim_centre (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN centre_id END,CASE WHEN member_kind=''NORMAL'' THEN version_no END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UC_D11_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uc_d11_1 ON ce_dwh_a.dim_centre (CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN source_system END,CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN centre_id END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D11_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_centre ADD CONSTRAINT ck_d11_01 CHECK (centre_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D11_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_centre ADD CONSTRAINT ck_d11_02 CHECK (is_current IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D11_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_centre ADD CONSTRAINT ck_d11_03 CHECK (version_no>=0 AND version_no<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D11_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_centre ADD CONSTRAINT ck_d11_04 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D11_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_centre ADD CONSTRAINT ck_d11_05 CHECK ((member_kind=''NORMAL'' AND centre_key>0) OR (member_kind=''UNKNOWN'' AND centre_key=0) OR (member_kind=''NOT_APPLICABLE'' AND centre_key=-1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D11_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_centre ADD CONSTRAINT ck_d11_06 CHECK (member_kind<>''NORMAL'' OR (centre_id IS NOT NULL AND centre_name IS NOT NULL AND site_code IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D11_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_centre ADD CONSTRAINT ck_d11_07 CHECK (version_no>=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D11_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_centre ADD CONSTRAINT ck_d11_08 CHECK ((is_current=1 AND valid_to_utc IS NULL) OR (is_current=0 AND valid_to_utc IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D11_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_centre ADD CONSTRAINT ck_d11_09 CHECK (valid_to_utc IS NULL OR valid_from_utc<valid_to_utc)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D11_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_centre ADD CONSTRAINT ck_d11_10 CHECK (member_kind=''NORMAL'' OR (version_no=1 AND is_current=1 AND valid_to_utc IS NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_A' AND table_name='DIM_ACTIVITY'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_a.dim_activity (
  activity_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  member_kind VARCHAR2(64 CHAR) NOT NULL,
  activity_id VARCHAR2(128 CHAR),
  centre_id VARCHAR2(128 CHAR),
  activity_name VARCHAR2(512 CHAR),
  outdoor NUMBER(1,0),
  capacity_per_day NUMBER(10,0),
  valid_from_utc TIMESTAMP(6) NOT NULL,
  valid_to_utc TIMESTAMP(6),
  is_current NUMBER(1,0) NOT NULL,
  version_no NUMBER(18,0) NOT NULL,
  effective_time_basis VARCHAR2(64 CHAR) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='PK_D12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_activity ADD CONSTRAINT pk_d12 PRIMARY KEY (activity_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UK_D12_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uk_d12_1 ON ce_dwh_a.dim_activity (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN activity_id END,CASE WHEN member_kind=''NORMAL'' THEN valid_from_utc END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UK_D12_2'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uk_d12_2 ON ce_dwh_a.dim_activity (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN activity_id END,CASE WHEN member_kind=''NORMAL'' THEN version_no END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UC_D12_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uc_d12_1 ON ce_dwh_a.dim_activity (CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN source_system END,CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN activity_id END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D12_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_activity ADD CONSTRAINT ck_d12_01 CHECK (activity_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D12_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_activity ADD CONSTRAINT ck_d12_02 CHECK (outdoor IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D12_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_activity ADD CONSTRAINT ck_d12_03 CHECK (capacity_per_day BETWEEN -2147483648 AND 2147483647)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D12_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_activity ADD CONSTRAINT ck_d12_04 CHECK (is_current IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D12_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_activity ADD CONSTRAINT ck_d12_05 CHECK (version_no>=0 AND version_no<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D12_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_activity ADD CONSTRAINT ck_d12_06 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D12_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_activity ADD CONSTRAINT ck_d12_07 CHECK ((member_kind=''NORMAL'' AND activity_key>0) OR (member_kind=''UNKNOWN'' AND activity_key=0) OR (member_kind=''NOT_APPLICABLE'' AND activity_key=-1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D12_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_activity ADD CONSTRAINT ck_d12_08 CHECK (member_kind<>''NORMAL'' OR (activity_id IS NOT NULL AND centre_id IS NOT NULL AND activity_name IS NOT NULL AND outdoor IS NOT NULL AND capacity_per_day IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D12_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_activity ADD CONSTRAINT ck_d12_09 CHECK (version_no>=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D12_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_activity ADD CONSTRAINT ck_d12_10 CHECK ((is_current=1 AND valid_to_utc IS NULL) OR (is_current=0 AND valid_to_utc IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D12_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_activity ADD CONSTRAINT ck_d12_11 CHECK (valid_to_utc IS NULL OR valid_from_utc<valid_to_utc)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D12_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_activity ADD CONSTRAINT ck_d12_12 CHECK (member_kind=''NORMAL'' OR (version_no=1 AND is_current=1 AND valid_to_utc IS NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D12_13'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_activity ADD CONSTRAINT ck_d12_13 CHECK (member_kind<>''NORMAL'' OR (capacity_per_day>0))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_A' AND table_name='DIM_VEHICLE'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_a.dim_vehicle (
  vehicle_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  member_kind VARCHAR2(64 CHAR) NOT NULL,
  vehicle_id VARCHAR2(128 CHAR),
  centre_id VARCHAR2(128 CHAR),
  vehicle_type VARCHAR2(512 CHAR),
  daily_rate_vnd NUMBER(19,0),
  valid_from_utc TIMESTAMP(6) NOT NULL,
  valid_to_utc TIMESTAMP(6),
  is_current NUMBER(1,0) NOT NULL,
  version_no NUMBER(18,0) NOT NULL,
  effective_time_basis VARCHAR2(64 CHAR) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='PK_D13'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_vehicle ADD CONSTRAINT pk_d13 PRIMARY KEY (vehicle_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UK_D13_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uk_d13_1 ON ce_dwh_a.dim_vehicle (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN vehicle_id END,CASE WHEN member_kind=''NORMAL'' THEN valid_from_utc END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UK_D13_2'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uk_d13_2 ON ce_dwh_a.dim_vehicle (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN vehicle_id END,CASE WHEN member_kind=''NORMAL'' THEN version_no END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UC_D13_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uc_d13_1 ON ce_dwh_a.dim_vehicle (CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN source_system END,CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN vehicle_id END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D13_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_vehicle ADD CONSTRAINT ck_d13_01 CHECK (vehicle_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D13_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_vehicle ADD CONSTRAINT ck_d13_02 CHECK (is_current IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D13_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_vehicle ADD CONSTRAINT ck_d13_03 CHECK (version_no>=0 AND version_no<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D13_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_vehicle ADD CONSTRAINT ck_d13_04 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D13_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_vehicle ADD CONSTRAINT ck_d13_05 CHECK ((member_kind=''NORMAL'' AND vehicle_key>0) OR (member_kind=''UNKNOWN'' AND vehicle_key=0) OR (member_kind=''NOT_APPLICABLE'' AND vehicle_key=-1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D13_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_vehicle ADD CONSTRAINT ck_d13_06 CHECK (member_kind<>''NORMAL'' OR (vehicle_id IS NOT NULL AND centre_id IS NOT NULL AND vehicle_type IS NOT NULL AND daily_rate_vnd IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D13_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_vehicle ADD CONSTRAINT ck_d13_07 CHECK (version_no>=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D13_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_vehicle ADD CONSTRAINT ck_d13_08 CHECK ((is_current=1 AND valid_to_utc IS NULL) OR (is_current=0 AND valid_to_utc IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D13_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_vehicle ADD CONSTRAINT ck_d13_09 CHECK (valid_to_utc IS NULL OR valid_from_utc<valid_to_utc)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D13_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_vehicle ADD CONSTRAINT ck_d13_10 CHECK (member_kind=''NORMAL'' OR (version_no=1 AND is_current=1 AND valid_to_utc IS NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D13_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_vehicle ADD CONSTRAINT ck_d13_11 CHECK (member_kind<>''NORMAL'' OR (daily_rate_vnd>0))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_A' AND table_name='DIM_SUPPLIER'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_a.dim_supplier (
  supplier_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  member_kind VARCHAR2(64 CHAR) NOT NULL,
  supplier_id VARCHAR2(128 CHAR),
  supplier_name VARCHAR2(512 CHAR),
  category VARCHAR2(512 CHAR),
  site_id VARCHAR2(128 CHAR),
  delivery_format VARCHAR2(512 CHAR),
  valid_from_utc TIMESTAMP(6) NOT NULL,
  valid_to_utc TIMESTAMP(6),
  is_current NUMBER(1,0) NOT NULL,
  version_no NUMBER(18,0) NOT NULL,
  effective_time_basis VARCHAR2(64 CHAR) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='PK_D14'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_supplier ADD CONSTRAINT pk_d14 PRIMARY KEY (supplier_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UK_D14_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uk_d14_1 ON ce_dwh_a.dim_supplier (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN supplier_id END,CASE WHEN member_kind=''NORMAL'' THEN valid_from_utc END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UK_D14_2'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uk_d14_2 ON ce_dwh_a.dim_supplier (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN supplier_id END,CASE WHEN member_kind=''NORMAL'' THEN version_no END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UC_D14_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uc_d14_1 ON ce_dwh_a.dim_supplier (CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN source_system END,CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN supplier_id END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D14_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_supplier ADD CONSTRAINT ck_d14_01 CHECK (supplier_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D14_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_supplier ADD CONSTRAINT ck_d14_02 CHECK (is_current IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D14_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_supplier ADD CONSTRAINT ck_d14_03 CHECK (version_no>=0 AND version_no<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D14_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_supplier ADD CONSTRAINT ck_d14_04 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D14_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_supplier ADD CONSTRAINT ck_d14_05 CHECK ((member_kind=''NORMAL'' AND supplier_key>0) OR (member_kind=''UNKNOWN'' AND supplier_key=0) OR (member_kind=''NOT_APPLICABLE'' AND supplier_key=-1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D14_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_supplier ADD CONSTRAINT ck_d14_06 CHECK (member_kind<>''NORMAL'' OR (supplier_id IS NOT NULL AND supplier_name IS NOT NULL AND category IS NOT NULL AND delivery_format IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D14_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_supplier ADD CONSTRAINT ck_d14_07 CHECK (version_no>=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D14_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_supplier ADD CONSTRAINT ck_d14_08 CHECK ((is_current=1 AND valid_to_utc IS NULL) OR (is_current=0 AND valid_to_utc IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D14_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_supplier ADD CONSTRAINT ck_d14_09 CHECK (valid_to_utc IS NULL OR valid_from_utc<valid_to_utc)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D14_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_supplier ADD CONSTRAINT ck_d14_10 CHECK (member_kind=''NORMAL'' OR (version_no=1 AND is_current=1 AND valid_to_utc IS NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_A' AND table_name='DIM_ITEM'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_a.dim_item (
  item_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  member_kind VARCHAR2(64 CHAR) NOT NULL,
  item_id VARCHAR2(128 CHAR),
  item_name VARCHAR2(512 CHAR),
  specification VARCHAR2(512 CHAR),
  base_unit VARCHAR2(512 CHAR),
  shelf_life_days NUMBER(10,0),
  valid_from_utc TIMESTAMP(6) NOT NULL,
  valid_to_utc TIMESTAMP(6),
  is_current NUMBER(1,0) NOT NULL,
  version_no NUMBER(18,0) NOT NULL,
  effective_time_basis VARCHAR2(64 CHAR) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='PK_D15'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_item ADD CONSTRAINT pk_d15 PRIMARY KEY (item_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UK_D15_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uk_d15_1 ON ce_dwh_a.dim_item (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN item_id END,CASE WHEN member_kind=''NORMAL'' THEN valid_from_utc END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UK_D15_2'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uk_d15_2 ON ce_dwh_a.dim_item (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN item_id END,CASE WHEN member_kind=''NORMAL'' THEN version_no END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UC_D15_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uc_d15_1 ON ce_dwh_a.dim_item (CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN source_system END,CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN item_id END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D15_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_item ADD CONSTRAINT ck_d15_01 CHECK (item_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D15_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_item ADD CONSTRAINT ck_d15_02 CHECK (shelf_life_days BETWEEN -2147483648 AND 2147483647)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D15_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_item ADD CONSTRAINT ck_d15_03 CHECK (is_current IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D15_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_item ADD CONSTRAINT ck_d15_04 CHECK (version_no>=0 AND version_no<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D15_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_item ADD CONSTRAINT ck_d15_05 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D15_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_item ADD CONSTRAINT ck_d15_06 CHECK ((member_kind=''NORMAL'' AND item_key>0) OR (member_kind=''UNKNOWN'' AND item_key=0) OR (member_kind=''NOT_APPLICABLE'' AND item_key=-1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D15_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_item ADD CONSTRAINT ck_d15_07 CHECK (member_kind<>''NORMAL'' OR (item_id IS NOT NULL AND item_name IS NOT NULL AND specification IS NOT NULL AND base_unit IS NOT NULL AND shelf_life_days IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D15_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_item ADD CONSTRAINT ck_d15_08 CHECK (version_no>=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D15_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_item ADD CONSTRAINT ck_d15_09 CHECK ((is_current=1 AND valid_to_utc IS NULL) OR (is_current=0 AND valid_to_utc IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D15_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_item ADD CONSTRAINT ck_d15_10 CHECK (valid_to_utc IS NULL OR valid_from_utc<valid_to_utc)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D15_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_item ADD CONSTRAINT ck_d15_11 CHECK (member_kind=''NORMAL'' OR (version_no=1 AND is_current=1 AND valid_to_utc IS NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D15_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_item ADD CONSTRAINT ck_d15_12 CHECK (member_kind<>''NORMAL'' OR (shelf_life_days>=0))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_A' AND table_name='DIM_ASSET'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_a.dim_asset (
  asset_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  member_kind VARCHAR2(64 CHAR) NOT NULL,
  asset_id VARCHAR2(128 CHAR),
  hotel_id VARCHAR2(128 CHAR),
  room_id VARCHAR2(128 CHAR),
  asset_type VARCHAR2(512 CHAR),
  supplier_id VARCHAR2(128 CHAR),
  valid_from_utc TIMESTAMP(6) NOT NULL,
  valid_to_utc TIMESTAMP(6),
  is_current NUMBER(1,0) NOT NULL,
  version_no NUMBER(18,0) NOT NULL,
  effective_time_basis VARCHAR2(64 CHAR) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='PK_D16'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_asset ADD CONSTRAINT pk_d16 PRIMARY KEY (asset_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UK_D16_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uk_d16_1 ON ce_dwh_a.dim_asset (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN asset_id END,CASE WHEN member_kind=''NORMAL'' THEN valid_from_utc END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UK_D16_2'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uk_d16_2 ON ce_dwh_a.dim_asset (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN asset_id END,CASE WHEN member_kind=''NORMAL'' THEN version_no END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_A' AND index_name='UC_D16_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_a.uc_d16_1 ON ce_dwh_a.dim_asset (CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN source_system END,CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN asset_id END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D16_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_asset ADD CONSTRAINT ck_d16_01 CHECK (asset_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D16_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_asset ADD CONSTRAINT ck_d16_02 CHECK (is_current IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D16_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_asset ADD CONSTRAINT ck_d16_03 CHECK (version_no>=0 AND version_no<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D16_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_asset ADD CONSTRAINT ck_d16_04 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D16_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_asset ADD CONSTRAINT ck_d16_05 CHECK ((member_kind=''NORMAL'' AND asset_key>0) OR (member_kind=''UNKNOWN'' AND asset_key=0) OR (member_kind=''NOT_APPLICABLE'' AND asset_key=-1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D16_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_asset ADD CONSTRAINT ck_d16_06 CHECK (member_kind<>''NORMAL'' OR (asset_id IS NOT NULL AND hotel_id IS NOT NULL AND asset_type IS NOT NULL AND supplier_id IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D16_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_asset ADD CONSTRAINT ck_d16_07 CHECK (version_no>=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D16_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_asset ADD CONSTRAINT ck_d16_08 CHECK ((is_current=1 AND valid_to_utc IS NULL) OR (is_current=0 AND valid_to_utc IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D16_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_asset ADD CONSTRAINT ck_d16_09 CHECK (valid_to_utc IS NULL OR valid_from_utc<valid_to_utc)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_D16_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.dim_asset ADD CONSTRAINT ck_d16_10 CHECK (member_kind=''NORMAL'' OR (version_no=1 AND is_current=1 AND valid_to_utc IS NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_A' AND table_name='FACT_BOOKING'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_a.fact_booking (
  fact_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  booked_date_key NUMBER(8,0) NOT NULL,
  arrival_date_key NUMBER(8,0) NOT NULL,
  departure_date_key NUMBER(8,0) NOT NULL,
  site_key NUMBER(18,0) NOT NULL,
  hotel_key NUMBER(18,0) NOT NULL,
  channel_key NUMBER(18,0) NOT NULL,
  promotion_key NUMBER(18,0) NOT NULL,
  customer_profile_key NUMBER(18,0) NOT NULL,
  booking_id VARCHAR2(128 CHAR) NOT NULL,
  status VARCHAR2(512 CHAR) NOT NULL,
  source_updated_at_utc TIMESTAMP(6) NOT NULL,
  gross_vnd NUMBER(19,0) NOT NULL,
  discount_vnd NUMBER(19,0) NOT NULL,
  customer_due_vnd NUMBER(19,0) NOT NULL,
  company_share_vnd NUMBER(19,0) NOT NULL,
  partner_share_vnd NUMBER(19,0) NOT NULL,
  commission_vnd NUMBER(19,0) NOT NULL,
  booking_count NUMBER(18,0) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='PK_F01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_booking ADD CONSTRAINT pk_f01 PRIMARY KEY (fact_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='UK_F01_1'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_booking ADD CONSTRAINT uk_f01_1 UNIQUE (source_system,booking_id) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F01_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_booking ADD CONSTRAINT ck_f01_01 CHECK (fact_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F01_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_booking ADD CONSTRAINT ck_f01_02 CHECK (booked_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F01_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_booking ADD CONSTRAINT ck_f01_03 CHECK (arrival_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F01_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_booking ADD CONSTRAINT ck_f01_04 CHECK (departure_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F01_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_booking ADD CONSTRAINT ck_f01_05 CHECK (site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F01_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_booking ADD CONSTRAINT ck_f01_06 CHECK (hotel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F01_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_booking ADD CONSTRAINT ck_f01_07 CHECK (channel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F01_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_booking ADD CONSTRAINT ck_f01_08 CHECK (promotion_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F01_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_booking ADD CONSTRAINT ck_f01_09 CHECK (customer_profile_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F01_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_booking ADD CONSTRAINT ck_f01_10 CHECK (gross_vnd>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F01_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_booking ADD CONSTRAINT ck_f01_11 CHECK (discount_vnd>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F01_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_booking ADD CONSTRAINT ck_f01_12 CHECK (customer_due_vnd>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F01_13'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_booking ADD CONSTRAINT ck_f01_13 CHECK (company_share_vnd>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F01_14'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_booking ADD CONSTRAINT ck_f01_14 CHECK (partner_share_vnd>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F01_15'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_booking ADD CONSTRAINT ck_f01_15 CHECK (commission_vnd>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F01_16'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_booking ADD CONSTRAINT ck_f01_16 CHECK (booking_count>=0 AND booking_count<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F01_17'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_booking ADD CONSTRAINT ck_f01_17 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F01_18'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_booking ADD CONSTRAINT ck_f01_18 CHECK (fact_key>0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F01_19'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_booking ADD CONSTRAINT ck_f01_19 CHECK (status IN (''COMPLETED'',''CANCELLED'',''NO_SHOW''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F01_20'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_booking ADD CONSTRAINT ck_f01_20 CHECK (arrival_date_key<departure_date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F01_21'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_booking ADD CONSTRAINT ck_f01_21 CHECK (booked_date_key<=arrival_date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F01_22'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_booking ADD CONSTRAINT ck_f01_22 CHECK (discount_vnd=company_share_vnd+partner_share_vnd)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F01_23'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_booking ADD CONSTRAINT ck_f01_23 CHECK (customer_due_vnd=gross_vnd-discount_vnd)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F01_24'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_booking ADD CONSTRAINT ck_f01_24 CHECK (booking_count=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_A' AND table_name='FACT_ROOM_DAY'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_a.fact_room_day (
  fact_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  room_id VARCHAR2(128 CHAR) NOT NULL,
  date_key NUMBER(8,0) NOT NULL,
  site_key NUMBER(18,0) NOT NULL,
  hotel_key NUMBER(18,0) NOT NULL,
  room_key NUMBER(18,0) NOT NULL,
  inventory_day NUMBER(1,0) NOT NULL,
  blocked_day NUMBER(1,0) NOT NULL,
  available_day NUMBER(1,0) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='PK_F02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_room_day ADD CONSTRAINT pk_f02 PRIMARY KEY (fact_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='UK_F02_1'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_room_day ADD CONSTRAINT uk_f02_1 UNIQUE (source_system,room_id,date_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F02_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_room_day ADD CONSTRAINT ck_f02_01 CHECK (fact_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F02_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_room_day ADD CONSTRAINT ck_f02_02 CHECK (date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F02_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_room_day ADD CONSTRAINT ck_f02_03 CHECK (site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F02_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_room_day ADD CONSTRAINT ck_f02_04 CHECK (hotel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F02_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_room_day ADD CONSTRAINT ck_f02_05 CHECK (room_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F02_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_room_day ADD CONSTRAINT ck_f02_06 CHECK (inventory_day IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F02_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_room_day ADD CONSTRAINT ck_f02_07 CHECK (blocked_day IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F02_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_room_day ADD CONSTRAINT ck_f02_08 CHECK (available_day IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F02_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_room_day ADD CONSTRAINT ck_f02_09 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F02_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_room_day ADD CONSTRAINT ck_f02_10 CHECK (fact_key>0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F02_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_room_day ADD CONSTRAINT ck_f02_11 CHECK (inventory_day=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F02_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_room_day ADD CONSTRAINT ck_f02_12 CHECK (available_day=inventory_day-blocked_day)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_A' AND table_name='FACT_STAY_NIGHT'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_a.fact_stay_night (
  fact_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  room_id VARCHAR2(128 CHAR) NOT NULL,
  service_date_key NUMBER(8,0) NOT NULL,
  site_key NUMBER(18,0) NOT NULL,
  hotel_key NUMBER(18,0) NOT NULL,
  room_key NUMBER(18,0) NOT NULL,
  channel_key NUMBER(18,0) NOT NULL,
  customer_profile_key NUMBER(18,0) NOT NULL,
  rate_plan_key NUMBER(18,0) NOT NULL,
  stay_id VARCHAR2(128 CHAR) NOT NULL,
  booking_room_id VARCHAR2(128 CHAR) NOT NULL,
  booking_id VARCHAR2(128 CHAR) NOT NULL,
  occupied_night NUMBER(1,0) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='PK_F03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stay_night ADD CONSTRAINT pk_f03 PRIMARY KEY (fact_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='UK_F03_1'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stay_night ADD CONSTRAINT uk_f03_1 UNIQUE (source_system,room_id,service_date_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F03_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stay_night ADD CONSTRAINT ck_f03_01 CHECK (fact_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F03_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stay_night ADD CONSTRAINT ck_f03_02 CHECK (service_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F03_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stay_night ADD CONSTRAINT ck_f03_03 CHECK (site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F03_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stay_night ADD CONSTRAINT ck_f03_04 CHECK (hotel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F03_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stay_night ADD CONSTRAINT ck_f03_05 CHECK (room_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F03_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stay_night ADD CONSTRAINT ck_f03_06 CHECK (channel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F03_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stay_night ADD CONSTRAINT ck_f03_07 CHECK (customer_profile_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F03_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stay_night ADD CONSTRAINT ck_f03_08 CHECK (rate_plan_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F03_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stay_night ADD CONSTRAINT ck_f03_09 CHECK (occupied_night IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F03_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stay_night ADD CONSTRAINT ck_f03_10 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F03_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stay_night ADD CONSTRAINT ck_f03_11 CHECK (fact_key>0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F03_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stay_night ADD CONSTRAINT ck_f03_12 CHECK (occupied_night=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_A' AND table_name='FACT_TICKET_ORDER'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_a.fact_ticket_order (
  fact_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  ordered_date_key NUMBER(8,0) NOT NULL,
  cohort_departure_date_key NUMBER(8,0) NOT NULL,
  service_site_key NUMBER(18,0) NOT NULL,
  booking_site_key NUMBER(18,0) NOT NULL,
  referral_hotel_key NUMBER(18,0) NOT NULL,
  ticket_channel_key NUMBER(18,0) NOT NULL,
  booking_channel_key NUMBER(18,0) NOT NULL,
  customer_profile_key NUMBER(18,0) NOT NULL,
  centre_key NUMBER(18,0) NOT NULL,
  ticket_order_id VARCHAR2(128 CHAR) NOT NULL,
  hotel_booking_ref VARCHAR2(128 CHAR),
  gross_vnd NUMBER(19,0) NOT NULL,
  refunded_vnd NUMBER(19,0) NOT NULL,
  net_ticket_vnd NUMBER(19,0) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='PK_F04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_ticket_order ADD CONSTRAINT pk_f04 PRIMARY KEY (fact_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='UK_F04_1'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_ticket_order ADD CONSTRAINT uk_f04_1 UNIQUE (source_system,ticket_order_id) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F04_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_ticket_order ADD CONSTRAINT ck_f04_01 CHECK (fact_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F04_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_ticket_order ADD CONSTRAINT ck_f04_02 CHECK (ordered_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F04_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_ticket_order ADD CONSTRAINT ck_f04_03 CHECK (cohort_departure_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F04_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_ticket_order ADD CONSTRAINT ck_f04_04 CHECK (service_site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F04_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_ticket_order ADD CONSTRAINT ck_f04_05 CHECK (booking_site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F04_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_ticket_order ADD CONSTRAINT ck_f04_06 CHECK (referral_hotel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F04_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_ticket_order ADD CONSTRAINT ck_f04_07 CHECK (ticket_channel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F04_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_ticket_order ADD CONSTRAINT ck_f04_08 CHECK (booking_channel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F04_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_ticket_order ADD CONSTRAINT ck_f04_09 CHECK (customer_profile_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F04_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_ticket_order ADD CONSTRAINT ck_f04_10 CHECK (centre_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F04_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_ticket_order ADD CONSTRAINT ck_f04_11 CHECK (gross_vnd>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F04_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_ticket_order ADD CONSTRAINT ck_f04_12 CHECK (refunded_vnd>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F04_13'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_ticket_order ADD CONSTRAINT ck_f04_13 CHECK (net_ticket_vnd>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F04_14'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_ticket_order ADD CONSTRAINT ck_f04_14 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F04_15'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_ticket_order ADD CONSTRAINT ck_f04_15 CHECK (fact_key>0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F04_16'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_ticket_order ADD CONSTRAINT ck_f04_16 CHECK (gross_vnd>=refunded_vnd)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F04_17'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_ticket_order ADD CONSTRAINT ck_f04_17 CHECK (net_ticket_vnd=gross_vnd-refunded_vnd)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_A' AND table_name='FACT_RENTAL'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_a.fact_rental (
  fact_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  pickup_date_key NUMBER(8,0) NOT NULL,
  return_date_key NUMBER(8,0) NOT NULL,
  cohort_departure_date_key NUMBER(8,0) NOT NULL,
  service_site_key NUMBER(18,0) NOT NULL,
  booking_site_key NUMBER(18,0) NOT NULL,
  referral_hotel_key NUMBER(18,0) NOT NULL,
  booking_channel_key NUMBER(18,0) NOT NULL,
  customer_profile_key NUMBER(18,0) NOT NULL,
  centre_key NUMBER(18,0) NOT NULL,
  vehicle_key NUMBER(18,0) NOT NULL,
  rental_id VARCHAR2(128 CHAR) NOT NULL,
  hotel_booking_ref VARCHAR2(128 CHAR),
  status VARCHAR2(512 CHAR) NOT NULL,
  agreed_vnd NUMBER(19,0) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='PK_F05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_rental ADD CONSTRAINT pk_f05 PRIMARY KEY (fact_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='UK_F05_1'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_rental ADD CONSTRAINT uk_f05_1 UNIQUE (source_system,rental_id) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F05_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_rental ADD CONSTRAINT ck_f05_01 CHECK (fact_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F05_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_rental ADD CONSTRAINT ck_f05_02 CHECK (pickup_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F05_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_rental ADD CONSTRAINT ck_f05_03 CHECK (return_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F05_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_rental ADD CONSTRAINT ck_f05_04 CHECK (cohort_departure_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F05_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_rental ADD CONSTRAINT ck_f05_05 CHECK (service_site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F05_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_rental ADD CONSTRAINT ck_f05_06 CHECK (booking_site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F05_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_rental ADD CONSTRAINT ck_f05_07 CHECK (referral_hotel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F05_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_rental ADD CONSTRAINT ck_f05_08 CHECK (booking_channel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F05_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_rental ADD CONSTRAINT ck_f05_09 CHECK (customer_profile_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F05_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_rental ADD CONSTRAINT ck_f05_10 CHECK (centre_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F05_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_rental ADD CONSTRAINT ck_f05_11 CHECK (vehicle_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F05_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_rental ADD CONSTRAINT ck_f05_12 CHECK (agreed_vnd>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F05_13'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_rental ADD CONSTRAINT ck_f05_13 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F05_14'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_rental ADD CONSTRAINT ck_f05_14 CHECK (fact_key>0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F05_15'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_rental ADD CONSTRAINT ck_f05_15 CHECK (status IN (''COMPLETED'',''CANCELLED''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F05_16'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_rental ADD CONSTRAINT ck_f05_16 CHECK (pickup_date_key<return_date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_A' AND table_name='FACT_BREAKFAST_ENTITLEMENT'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_a.fact_breakfast_entitlement (
  fact_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  service_date_key NUMBER(8,0) NOT NULL,
  site_key NUMBER(18,0) NOT NULL,
  hotel_key NUMBER(18,0) NOT NULL,
  room_key NUMBER(18,0) NOT NULL,
  customer_profile_key NUMBER(18,0) NOT NULL,
  rate_plan_key NUMBER(18,0) NOT NULL,
  outlet_key NUMBER(18,0) NOT NULL,
  meal_key NUMBER(18,0) NOT NULL,
  entitlement_id VARCHAR2(128 CHAR) NOT NULL,
  booking_room_id VARCHAR2(128 CHAR) NOT NULL,
  eligible_covers NUMBER(18,0) NOT NULL,
  redeemed_covers NUMBER(18,0) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='PK_F06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_breakfast_entitlement ADD CONSTRAINT pk_f06 PRIMARY KEY (fact_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='UK_F06_1'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_breakfast_entitlement ADD CONSTRAINT uk_f06_1 UNIQUE (source_system,entitlement_id) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='UK_F06_2'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_breakfast_entitlement ADD CONSTRAINT uk_f06_2 UNIQUE (source_system,booking_room_id,service_date_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F06_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_breakfast_entitlement ADD CONSTRAINT ck_f06_01 CHECK (fact_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F06_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_breakfast_entitlement ADD CONSTRAINT ck_f06_02 CHECK (service_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F06_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_breakfast_entitlement ADD CONSTRAINT ck_f06_03 CHECK (site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F06_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_breakfast_entitlement ADD CONSTRAINT ck_f06_04 CHECK (hotel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F06_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_breakfast_entitlement ADD CONSTRAINT ck_f06_05 CHECK (room_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F06_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_breakfast_entitlement ADD CONSTRAINT ck_f06_06 CHECK (customer_profile_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F06_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_breakfast_entitlement ADD CONSTRAINT ck_f06_07 CHECK (rate_plan_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F06_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_breakfast_entitlement ADD CONSTRAINT ck_f06_08 CHECK (outlet_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F06_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_breakfast_entitlement ADD CONSTRAINT ck_f06_09 CHECK (meal_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F06_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_breakfast_entitlement ADD CONSTRAINT ck_f06_10 CHECK (eligible_covers>=0 AND eligible_covers<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F06_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_breakfast_entitlement ADD CONSTRAINT ck_f06_11 CHECK (redeemed_covers>=0 AND redeemed_covers<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F06_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_breakfast_entitlement ADD CONSTRAINT ck_f06_12 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F06_13'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_breakfast_entitlement ADD CONSTRAINT ck_f06_13 CHECK (fact_key>0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F06_14'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_breakfast_entitlement ADD CONSTRAINT ck_f06_14 CHECK (eligible_covers>=redeemed_covers)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F06_15'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_breakfast_entitlement ADD CONSTRAINT ck_f06_15 CHECK (meal_key=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_A' AND table_name='FACT_DINING_ORDER'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_a.fact_dining_order (
  fact_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  service_date_key NUMBER(8,0) NOT NULL,
  site_key NUMBER(18,0) NOT NULL,
  service_hotel_key NUMBER(18,0) NOT NULL,
  booking_hotel_key NUMBER(18,0) NOT NULL,
  customer_profile_key NUMBER(18,0) NOT NULL,
  outlet_key NUMBER(18,0) NOT NULL,
  meal_key NUMBER(18,0) NOT NULL,
  dining_order_id VARCHAR2(128 CHAR) NOT NULL,
  booking_id VARCHAR2(128 CHAR),
  net_vnd NUMBER(19,0) NOT NULL,
  covers NUMBER(18,0) NOT NULL,
  rating_sum NUMBER(18,0) NOT NULL,
  rating_count NUMBER(18,0) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='PK_F07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_dining_order ADD CONSTRAINT pk_f07 PRIMARY KEY (fact_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='UK_F07_1'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_dining_order ADD CONSTRAINT uk_f07_1 UNIQUE (source_system,dining_order_id) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F07_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_dining_order ADD CONSTRAINT ck_f07_01 CHECK (fact_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F07_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_dining_order ADD CONSTRAINT ck_f07_02 CHECK (service_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F07_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_dining_order ADD CONSTRAINT ck_f07_03 CHECK (site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F07_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_dining_order ADD CONSTRAINT ck_f07_04 CHECK (service_hotel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F07_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_dining_order ADD CONSTRAINT ck_f07_05 CHECK (booking_hotel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F07_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_dining_order ADD CONSTRAINT ck_f07_06 CHECK (customer_profile_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F07_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_dining_order ADD CONSTRAINT ck_f07_07 CHECK (outlet_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F07_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_dining_order ADD CONSTRAINT ck_f07_08 CHECK (meal_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F07_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_dining_order ADD CONSTRAINT ck_f07_09 CHECK (net_vnd>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F07_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_dining_order ADD CONSTRAINT ck_f07_10 CHECK (covers>=0 AND covers<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F07_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_dining_order ADD CONSTRAINT ck_f07_11 CHECK (rating_sum>=0 AND rating_sum<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F07_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_dining_order ADD CONSTRAINT ck_f07_12 CHECK (rating_count>=0 AND rating_count<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F07_13'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_dining_order ADD CONSTRAINT ck_f07_13 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F07_14'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_dining_order ADD CONSTRAINT ck_f07_14 CHECK (fact_key>0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F07_15'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_dining_order ADD CONSTRAINT ck_f07_15 CHECK (rating_sum BETWEEN 1 AND 5)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F07_16'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_dining_order ADD CONSTRAINT ck_f07_16 CHECK (rating_count=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_A' AND table_name='FACT_MEAL_SESSION'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_a.fact_meal_session (
  fact_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  outlet_id VARCHAR2(128 CHAR) NOT NULL,
  service_date_key NUMBER(8,0) NOT NULL,
  site_key NUMBER(18,0) NOT NULL,
  hotel_key NUMBER(18,0) NOT NULL,
  outlet_key NUMBER(18,0) NOT NULL,
  meal_key NUMBER(18,0) NOT NULL,
  session_id VARCHAR2(128 CHAR) NOT NULL,
  actual_covers NUMBER(18,0) NOT NULL,
  ingredient_cost_vnd NUMBER(19,0) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='PK_F08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_meal_session ADD CONSTRAINT pk_f08 PRIMARY KEY (fact_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='UK_F08_1'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_meal_session ADD CONSTRAINT uk_f08_1 UNIQUE (source_system,outlet_id,service_date_key,meal_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='UK_F08_2'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_meal_session ADD CONSTRAINT uk_f08_2 UNIQUE (source_system,session_id) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F08_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_meal_session ADD CONSTRAINT ck_f08_01 CHECK (fact_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F08_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_meal_session ADD CONSTRAINT ck_f08_02 CHECK (service_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F08_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_meal_session ADD CONSTRAINT ck_f08_03 CHECK (site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F08_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_meal_session ADD CONSTRAINT ck_f08_04 CHECK (hotel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F08_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_meal_session ADD CONSTRAINT ck_f08_05 CHECK (outlet_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F08_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_meal_session ADD CONSTRAINT ck_f08_06 CHECK (meal_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F08_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_meal_session ADD CONSTRAINT ck_f08_07 CHECK (actual_covers>=0 AND actual_covers<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F08_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_meal_session ADD CONSTRAINT ck_f08_08 CHECK (ingredient_cost_vnd>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F08_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_meal_session ADD CONSTRAINT ck_f08_09 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F08_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_meal_session ADD CONSTRAINT ck_f08_10 CHECK (fact_key>0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F08_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_meal_session ADD CONSTRAINT ck_f08_11 CHECK (meal_key IN (1,3))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_A' AND table_name='FACT_ADMISSION'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_a.fact_admission (
  fact_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  admission_date_key NUMBER(8,0) NOT NULL,
  site_key NUMBER(18,0) NOT NULL,
  customer_profile_key NUMBER(18,0) NOT NULL,
  centre_key NUMBER(18,0) NOT NULL,
  activity_key NUMBER(18,0) NOT NULL,
  admission_id VARCHAR2(128 CHAR) NOT NULL,
  ticket_id VARCHAR2(128 CHAR) NOT NULL,
  entered_at_utc TIMESTAMP(6) NOT NULL,
  admission_count NUMBER(18,0) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='PK_F09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_admission ADD CONSTRAINT pk_f09 PRIMARY KEY (fact_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='UK_F09_1'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_admission ADD CONSTRAINT uk_f09_1 UNIQUE (source_system,admission_id) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F09_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_admission ADD CONSTRAINT ck_f09_01 CHECK (fact_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F09_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_admission ADD CONSTRAINT ck_f09_02 CHECK (admission_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F09_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_admission ADD CONSTRAINT ck_f09_03 CHECK (site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F09_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_admission ADD CONSTRAINT ck_f09_04 CHECK (customer_profile_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F09_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_admission ADD CONSTRAINT ck_f09_05 CHECK (centre_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F09_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_admission ADD CONSTRAINT ck_f09_06 CHECK (activity_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F09_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_admission ADD CONSTRAINT ck_f09_07 CHECK (admission_count>=0 AND admission_count<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F09_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_admission ADD CONSTRAINT ck_f09_08 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F09_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_admission ADD CONSTRAINT ck_f09_09 CHECK (fact_key>0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F09_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_admission ADD CONSTRAINT ck_f09_10 CHECK (admission_count=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_A' AND table_name='FACT_ACTIVITY_DAY'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_a.fact_activity_day (
  fact_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  activity_id VARCHAR2(128 CHAR) NOT NULL,
  date_key NUMBER(8,0) NOT NULL,
  site_key NUMBER(18,0) NOT NULL,
  centre_key NUMBER(18,0) NOT NULL,
  activity_key NUMBER(18,0) NOT NULL,
  nominal_capacity NUMBER(18,0) NOT NULL,
  is_closed NUMBER(1,0) NOT NULL,
  available_capacity NUMBER(18,0) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='PK_F10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_activity_day ADD CONSTRAINT pk_f10 PRIMARY KEY (fact_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='UK_F10_1'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_activity_day ADD CONSTRAINT uk_f10_1 UNIQUE (source_system,activity_id,date_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F10_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_activity_day ADD CONSTRAINT ck_f10_01 CHECK (fact_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F10_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_activity_day ADD CONSTRAINT ck_f10_02 CHECK (date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F10_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_activity_day ADD CONSTRAINT ck_f10_03 CHECK (site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F10_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_activity_day ADD CONSTRAINT ck_f10_04 CHECK (centre_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F10_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_activity_day ADD CONSTRAINT ck_f10_05 CHECK (activity_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F10_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_activity_day ADD CONSTRAINT ck_f10_06 CHECK (nominal_capacity>=0 AND nominal_capacity<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F10_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_activity_day ADD CONSTRAINT ck_f10_07 CHECK (is_closed IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F10_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_activity_day ADD CONSTRAINT ck_f10_08 CHECK (available_capacity>=0 AND available_capacity<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F10_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_activity_day ADD CONSTRAINT ck_f10_09 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F10_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_activity_day ADD CONSTRAINT ck_f10_10 CHECK (fact_key>0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F10_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_activity_day ADD CONSTRAINT ck_f10_11 CHECK (nominal_capacity>0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F10_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_activity_day ADD CONSTRAINT ck_f10_12 CHECK (available_capacity=nominal_capacity*(1-is_closed))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_A' AND table_name='FACT_VEHICLE_DAY'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_a.fact_vehicle_day (
  fact_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  vehicle_id VARCHAR2(128 CHAR) NOT NULL,
  date_key NUMBER(8,0) NOT NULL,
  site_key NUMBER(18,0) NOT NULL,
  centre_key NUMBER(18,0) NOT NULL,
  vehicle_key NUMBER(18,0) NOT NULL,
  inventory_day NUMBER(1,0) NOT NULL,
  maintenance_day NUMBER(1,0) NOT NULL,
  available_day NUMBER(1,0) NOT NULL,
  rented_day NUMBER(1,0) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='PK_F11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_vehicle_day ADD CONSTRAINT pk_f11 PRIMARY KEY (fact_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='UK_F11_1'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_vehicle_day ADD CONSTRAINT uk_f11_1 UNIQUE (source_system,vehicle_id,date_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F11_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_vehicle_day ADD CONSTRAINT ck_f11_01 CHECK (fact_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F11_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_vehicle_day ADD CONSTRAINT ck_f11_02 CHECK (date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F11_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_vehicle_day ADD CONSTRAINT ck_f11_03 CHECK (site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F11_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_vehicle_day ADD CONSTRAINT ck_f11_04 CHECK (centre_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F11_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_vehicle_day ADD CONSTRAINT ck_f11_05 CHECK (vehicle_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F11_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_vehicle_day ADD CONSTRAINT ck_f11_06 CHECK (inventory_day IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F11_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_vehicle_day ADD CONSTRAINT ck_f11_07 CHECK (maintenance_day IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F11_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_vehicle_day ADD CONSTRAINT ck_f11_08 CHECK (available_day IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F11_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_vehicle_day ADD CONSTRAINT ck_f11_09 CHECK (rented_day IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F11_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_vehicle_day ADD CONSTRAINT ck_f11_10 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F11_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_vehicle_day ADD CONSTRAINT ck_f11_11 CHECK (fact_key>0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F11_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_vehicle_day ADD CONSTRAINT ck_f11_12 CHECK (inventory_day=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F11_13'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_vehicle_day ADD CONSTRAINT ck_f11_13 CHECK (available_day=1-maintenance_day)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F11_14'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_vehicle_day ADD CONSTRAINT ck_f11_14 CHECK (rented_day<=available_day)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_A' AND table_name='FACT_PURCHASE_LINE'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_a.fact_purchase_line (
  fact_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  ordered_date_key NUMBER(8,0) NOT NULL,
  expected_date_key NUMBER(8,0) NOT NULL,
  site_key NUMBER(18,0) NOT NULL,
  hotel_key NUMBER(18,0) NOT NULL,
  supplier_key NUMBER(18,0) NOT NULL,
  item_key NUMBER(18,0) NOT NULL,
  purchase_line_id VARCHAR2(128 CHAR) NOT NULL,
  purchase_order_id VARCHAR2(128 CHAR) NOT NULL,
  ordered_qty NUMBER(18,3) NOT NULL,
  unit_price_vnd NUMBER(19,0) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='PK_F12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_purchase_line ADD CONSTRAINT pk_f12 PRIMARY KEY (fact_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='UK_F12_1'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_purchase_line ADD CONSTRAINT uk_f12_1 UNIQUE (source_system,purchase_line_id) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F12_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_purchase_line ADD CONSTRAINT ck_f12_01 CHECK (fact_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F12_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_purchase_line ADD CONSTRAINT ck_f12_02 CHECK (ordered_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F12_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_purchase_line ADD CONSTRAINT ck_f12_03 CHECK (expected_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F12_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_purchase_line ADD CONSTRAINT ck_f12_04 CHECK (site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F12_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_purchase_line ADD CONSTRAINT ck_f12_05 CHECK (hotel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F12_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_purchase_line ADD CONSTRAINT ck_f12_06 CHECK (supplier_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F12_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_purchase_line ADD CONSTRAINT ck_f12_07 CHECK (item_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F12_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_purchase_line ADD CONSTRAINT ck_f12_08 CHECK (unit_price_vnd>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F12_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_purchase_line ADD CONSTRAINT ck_f12_09 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F12_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_purchase_line ADD CONSTRAINT ck_f12_10 CHECK (fact_key>0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F12_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_purchase_line ADD CONSTRAINT ck_f12_11 CHECK (ordered_qty>0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F12_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_purchase_line ADD CONSTRAINT ck_f12_12 CHECK (unit_price_vnd>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F12_13'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_purchase_line ADD CONSTRAINT ck_f12_13 CHECK (ordered_date_key<=expected_date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_A' AND table_name='FACT_RECEIPT'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_a.fact_receipt (
  fact_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  received_date_key NUMBER(8,0) NOT NULL,
  expected_date_key NUMBER(8,0) NOT NULL,
  expires_date_key NUMBER(8,0) NOT NULL,
  site_key NUMBER(18,0) NOT NULL,
  hotel_key NUMBER(18,0) NOT NULL,
  supplier_key NUMBER(18,0) NOT NULL,
  item_key NUMBER(18,0) NOT NULL,
  receipt_id VARCHAR2(128 CHAR) NOT NULL,
  purchase_line_id VARCHAR2(128 CHAR) NOT NULL,
  accepted_qty NUMBER(18,3) NOT NULL,
  rejected_qty NUMBER(18,3) NOT NULL,
  late_accepted_qty NUMBER(18,3) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='PK_F13'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_receipt ADD CONSTRAINT pk_f13 PRIMARY KEY (fact_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='UK_F13_1'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_receipt ADD CONSTRAINT uk_f13_1 UNIQUE (source_system,receipt_id) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F13_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_receipt ADD CONSTRAINT ck_f13_01 CHECK (fact_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F13_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_receipt ADD CONSTRAINT ck_f13_02 CHECK (received_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F13_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_receipt ADD CONSTRAINT ck_f13_03 CHECK (expected_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F13_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_receipt ADD CONSTRAINT ck_f13_04 CHECK (expires_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F13_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_receipt ADD CONSTRAINT ck_f13_05 CHECK (site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F13_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_receipt ADD CONSTRAINT ck_f13_06 CHECK (hotel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F13_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_receipt ADD CONSTRAINT ck_f13_07 CHECK (supplier_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F13_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_receipt ADD CONSTRAINT ck_f13_08 CHECK (item_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F13_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_receipt ADD CONSTRAINT ck_f13_09 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F13_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_receipt ADD CONSTRAINT ck_f13_10 CHECK (fact_key>0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F13_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_receipt ADD CONSTRAINT ck_f13_11 CHECK (accepted_qty>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F13_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_receipt ADD CONSTRAINT ck_f13_12 CHECK (rejected_qty>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F13_13'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_receipt ADD CONSTRAINT ck_f13_13 CHECK (late_accepted_qty IN (0,accepted_qty))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_A' AND table_name='FACT_STOCK_MOVEMENT'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_a.fact_stock_movement (
  fact_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  movement_date_key NUMBER(8,0) NOT NULL,
  site_key NUMBER(18,0) NOT NULL,
  hotel_key NUMBER(18,0) NOT NULL,
  supplier_key NUMBER(18,0) NOT NULL,
  item_key NUMBER(18,0) NOT NULL,
  movement_id VARCHAR2(128 CHAR) NOT NULL,
  receipt_id VARCHAR2(128 CHAR) NOT NULL,
  session_id VARCHAR2(128 CHAR),
  movement_type VARCHAR2(512 CHAR) NOT NULL,
  usage_area VARCHAR2(512 CHAR) NOT NULL,
  quantity NUMBER(18,3) NOT NULL,
  signed_qty NUMBER(18,3) NOT NULL,
  in_qty NUMBER(18,3) NOT NULL,
  use_qty NUMBER(18,3) NOT NULL,
  waste_qty NUMBER(18,3) NOT NULL,
  unit_price_vnd NUMBER(19,0) NOT NULL,
  movement_value_vnd NUMBER(38,3) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='PK_F14'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stock_movement ADD CONSTRAINT pk_f14 PRIMARY KEY (fact_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='UK_F14_1'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stock_movement ADD CONSTRAINT uk_f14_1 UNIQUE (source_system,movement_id) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F14_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stock_movement ADD CONSTRAINT ck_f14_01 CHECK (fact_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F14_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stock_movement ADD CONSTRAINT ck_f14_02 CHECK (movement_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F14_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stock_movement ADD CONSTRAINT ck_f14_03 CHECK (site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F14_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stock_movement ADD CONSTRAINT ck_f14_04 CHECK (hotel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F14_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stock_movement ADD CONSTRAINT ck_f14_05 CHECK (supplier_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F14_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stock_movement ADD CONSTRAINT ck_f14_06 CHECK (item_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F14_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stock_movement ADD CONSTRAINT ck_f14_07 CHECK (unit_price_vnd>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F14_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stock_movement ADD CONSTRAINT ck_f14_08 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F14_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stock_movement ADD CONSTRAINT ck_f14_09 CHECK (fact_key>0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F14_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stock_movement ADD CONSTRAINT ck_f14_10 CHECK (movement_type IN (''IN'',''USE'',''WASTE''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F14_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stock_movement ADD CONSTRAINT ck_f14_11 CHECK (quantity>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F14_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stock_movement ADD CONSTRAINT ck_f14_12 CHECK (in_qty>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F14_13'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stock_movement ADD CONSTRAINT ck_f14_13 CHECK (use_qty>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F14_14'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stock_movement ADD CONSTRAINT ck_f14_14 CHECK (waste_qty>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F14_15'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stock_movement ADD CONSTRAINT ck_f14_15 CHECK (signed_qty=in_qty-use_qty-waste_qty)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_A' AND table_name='AGG_INVENTORY_LOT_DAY'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_a.agg_inventory_lot_day (
  fact_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  hotel_id VARCHAR2(128 CHAR) NOT NULL,
  item_id VARCHAR2(128 CHAR) NOT NULL,
  snapshot_date_key NUMBER(8,0) NOT NULL,
  site_key NUMBER(18,0) NOT NULL,
  hotel_key NUMBER(18,0) NOT NULL,
  supplier_key NUMBER(18,0) NOT NULL,
  item_key NUMBER(18,0) NOT NULL,
  receipt_id VARCHAR2(128 CHAR) NOT NULL,
  closing_qty NUMBER(18,3) NOT NULL,
  closing_value_vnd NUMBER(38,3) NOT NULL,
  in_qty NUMBER(18,3) NOT NULL,
  use_qty NUMBER(18,3) NOT NULL,
  waste_qty NUMBER(18,3) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='PK_F15'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.agg_inventory_lot_day ADD CONSTRAINT pk_f15 PRIMARY KEY (fact_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='UK_F15_1'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.agg_inventory_lot_day ADD CONSTRAINT uk_f15_1 UNIQUE (source_system,receipt_id,hotel_id,item_id,snapshot_date_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F15_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.agg_inventory_lot_day ADD CONSTRAINT ck_f15_01 CHECK (fact_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F15_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.agg_inventory_lot_day ADD CONSTRAINT ck_f15_02 CHECK (snapshot_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F15_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.agg_inventory_lot_day ADD CONSTRAINT ck_f15_03 CHECK (site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F15_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.agg_inventory_lot_day ADD CONSTRAINT ck_f15_04 CHECK (hotel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F15_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.agg_inventory_lot_day ADD CONSTRAINT ck_f15_05 CHECK (supplier_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F15_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.agg_inventory_lot_day ADD CONSTRAINT ck_f15_06 CHECK (item_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F15_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.agg_inventory_lot_day ADD CONSTRAINT ck_f15_07 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F15_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.agg_inventory_lot_day ADD CONSTRAINT ck_f15_08 CHECK (fact_key>0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F15_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.agg_inventory_lot_day ADD CONSTRAINT ck_f15_09 CHECK (closing_qty>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F15_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.agg_inventory_lot_day ADD CONSTRAINT ck_f15_10 CHECK (in_qty>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F15_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.agg_inventory_lot_day ADD CONSTRAINT ck_f15_11 CHECK (use_qty>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F15_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.agg_inventory_lot_day ADD CONSTRAINT ck_f15_12 CHECK (waste_qty>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_A' AND table_name='FACT_MAINTENANCE_WORK'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_a.fact_maintenance_work (
  fact_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  start_date_key NUMBER(8,0) NOT NULL,
  end_date_key NUMBER(8,0) NOT NULL,
  site_key NUMBER(18,0) NOT NULL,
  hotel_key NUMBER(18,0) NOT NULL,
  room_key NUMBER(18,0) NOT NULL,
  asset_key NUMBER(18,0) NOT NULL,
  maintenance_id VARCHAR2(128 CHAR) NOT NULL,
  work_type VARCHAR2(512 CHAR) NOT NULL,
  status VARCHAR2(512 CHAR) NOT NULL,
  cost_vnd NUMBER(19,0) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='PK_F16'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_maintenance_work ADD CONSTRAINT pk_f16 PRIMARY KEY (fact_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='UK_F16_1'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_maintenance_work ADD CONSTRAINT uk_f16_1 UNIQUE (source_system,maintenance_id) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F16_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_maintenance_work ADD CONSTRAINT ck_f16_01 CHECK (fact_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F16_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_maintenance_work ADD CONSTRAINT ck_f16_02 CHECK (start_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F16_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_maintenance_work ADD CONSTRAINT ck_f16_03 CHECK (end_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F16_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_maintenance_work ADD CONSTRAINT ck_f16_04 CHECK (site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F16_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_maintenance_work ADD CONSTRAINT ck_f16_05 CHECK (hotel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F16_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_maintenance_work ADD CONSTRAINT ck_f16_06 CHECK (room_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F16_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_maintenance_work ADD CONSTRAINT ck_f16_07 CHECK (asset_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F16_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_maintenance_work ADD CONSTRAINT ck_f16_08 CHECK (cost_vnd>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F16_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_maintenance_work ADD CONSTRAINT ck_f16_09 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F16_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_maintenance_work ADD CONSTRAINT ck_f16_10 CHECK (fact_key>0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F16_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_maintenance_work ADD CONSTRAINT ck_f16_11 CHECK (start_date_key<end_date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F16_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_maintenance_work ADD CONSTRAINT ck_f16_12 CHECK (work_type IN (''BREAKDOWN'',''PLANNED''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F16_13'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_maintenance_work ADD CONSTRAINT ck_f16_13 CHECK (status=''COMPLETED'')'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_A' AND table_name='FACT_WEATHER_DAY'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_a.fact_weather_day (
  fact_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  site_id VARCHAR2(128 CHAR) NOT NULL,
  weather_date_key NUMBER(8,0) NOT NULL,
  site_key NUMBER(18,0) NOT NULL,
  weather_id VARCHAR2(128 CHAR) NOT NULL,
  provenance VARCHAR2(512 CHAR) NOT NULL,
  temperature_c NUMBER(10,0) NOT NULL,
  rain_mm NUMBER(10,0) NOT NULL,
  severe_weather NUMBER(1,0) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='PK_F17'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_weather_day ADD CONSTRAINT pk_f17 PRIMARY KEY (fact_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='UK_F17_1'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_weather_day ADD CONSTRAINT uk_f17_1 UNIQUE (source_system,site_id,weather_date_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='UK_F17_2'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_weather_day ADD CONSTRAINT uk_f17_2 UNIQUE (source_system,weather_id) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F17_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_weather_day ADD CONSTRAINT ck_f17_01 CHECK (fact_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F17_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_weather_day ADD CONSTRAINT ck_f17_02 CHECK (weather_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F17_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_weather_day ADD CONSTRAINT ck_f17_03 CHECK (site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F17_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_weather_day ADD CONSTRAINT ck_f17_04 CHECK (temperature_c BETWEEN -2147483648 AND 2147483647)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F17_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_weather_day ADD CONSTRAINT ck_f17_05 CHECK (rain_mm BETWEEN -2147483648 AND 2147483647)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F17_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_weather_day ADD CONSTRAINT ck_f17_06 CHECK (severe_weather IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F17_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_weather_day ADD CONSTRAINT ck_f17_07 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F17_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_weather_day ADD CONSTRAINT ck_f17_08 CHECK (fact_key>0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_F17_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_weather_day ADD CONSTRAINT ck_f17_09 CHECK (rain_mm>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_A' AND table_name='BRIDGE_BOOKING_ROOM'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_a.bridge_booking_room (
  source_system VARCHAR2(64 CHAR) NOT NULL,
  booking_room_id VARCHAR2(128 CHAR) NOT NULL,
  booking_id VARCHAR2(128 CHAR) NOT NULL,
  room_key NUMBER(18,0) NOT NULL,
  rate_plan_key NUMBER(18,0) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='PK_L01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.bridge_booking_room ADD CONSTRAINT pk_l01 PRIMARY KEY (source_system,booking_room_id) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_L01_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.bridge_booking_room ADD CONSTRAINT ck_l01_01 CHECK (room_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_L01_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.bridge_booking_room ADD CONSTRAINT ck_l01_02 CHECK (rate_plan_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_L01_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.bridge_booking_room ADD CONSTRAINT ck_l01_03 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_A' AND table_name='BRIDGE_ROOM_DAY_MAINTENANCE'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_a.bridge_room_day_maintenance (
  source_system VARCHAR2(64 CHAR) NOT NULL,
  maintenance_id VARCHAR2(128 CHAR) NOT NULL,
  room_id VARCHAR2(128 CHAR) NOT NULL,
  room_key NUMBER(18,0) NOT NULL,
  date_key NUMBER(8,0) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='PK_L02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.bridge_room_day_maintenance ADD CONSTRAINT pk_l02 PRIMARY KEY (source_system,room_id,date_key,maintenance_id) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_L02_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.bridge_room_day_maintenance ADD CONSTRAINT ck_l02_01 CHECK (room_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_L02_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.bridge_room_day_maintenance ADD CONSTRAINT ck_l02_02 CHECK (date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='CK_L02_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.bridge_room_day_maintenance ADD CONSTRAINT ck_l02_03 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_STAGE' AND table_name='VALIDATED_BOOKING_SERVICE_LINK_INPUT_A'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_stage.validated_booking_service_link_input_a (
  service_source_system VARCHAR2(64 CHAR) NOT NULL,
  service_type VARCHAR2(64 CHAR) NOT NULL,
  service_id VARCHAR2(128 CHAR) NOT NULL,
  booking_source_system VARCHAR2(64 CHAR) NOT NULL,
  booking_id VARCHAR2(128 CHAR) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_stage_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_STAGE' AND constraint_name='PK_L03_A'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_stage.validated_booking_service_link_input_a ADD CONSTRAINT pk_l03_a PRIMARY KEY (service_source_system,service_type,service_id) USING INDEX TABLESPACE ce_stage_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_STAGE' AND constraint_name='CK_L03_01_A'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_stage.validated_booking_service_link_input_a ADD CONSTRAINT ck_l03_01_a CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

GRANT SELECT ON ce_stage.validated_booking_service_link_input_a TO ce_dwh_a;

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_views WHERE owner='CE_DWH_A' AND view_name='VALIDATED_BOOKING_SERVICE_LINK'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE VIEW ce_dwh_a.validated_booking_service_link AS SELECT service_source_system,service_type,service_id,booking_source_system,booking_id,source_batch_id,transform_version,row_hash,created_at_utc,updated_at_utc FROM ce_stage.validated_booking_service_link_input_a'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_STAGE' AND table_name='SITE_CROSSWALK_INPUT_A'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_stage.site_crosswalk_input_a (
  centre_source_system VARCHAR2(64 CHAR) NOT NULL,
  centre_id VARCHAR2(128 CHAR) NOT NULL,
  site_source_system VARCHAR2(64 CHAR) NOT NULL,
  site_id VARCHAR2(128 CHAR) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_stage_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_STAGE' AND constraint_name='PK_L04_A'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_stage.site_crosswalk_input_a ADD CONSTRAINT pk_l04_a PRIMARY KEY (centre_source_system,centre_id) USING INDEX TABLESPACE ce_stage_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_STAGE' AND constraint_name='CK_L04_01_A'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_stage.site_crosswalk_input_a ADD CONSTRAINT ck_l04_01_a CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

GRANT SELECT ON ce_stage.site_crosswalk_input_a TO ce_dwh_a;

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_views WHERE owner='CE_DWH_A' AND view_name='SITE_CROSSWALK'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE VIEW ce_dwh_a.site_crosswalk AS SELECT centre_source_system,centre_id,site_source_system,site_id,source_batch_id,transform_version,row_hash,created_at_utc,updated_at_utc FROM ce_stage.site_crosswalk_input_a'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F01_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_booking ADD CONSTRAINT fk_f01_02 FOREIGN KEY (booked_date_key) REFERENCES ce_dwh_a.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F01_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_booking ADD CONSTRAINT fk_f01_03 FOREIGN KEY (arrival_date_key) REFERENCES ce_dwh_a.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F01_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_booking ADD CONSTRAINT fk_f01_04 FOREIGN KEY (departure_date_key) REFERENCES ce_dwh_a.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F01_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_booking ADD CONSTRAINT fk_f01_05 FOREIGN KEY (site_key) REFERENCES ce_dwh_a.dim_site (site_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F01_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_booking ADD CONSTRAINT fk_f01_06 FOREIGN KEY (hotel_key) REFERENCES ce_dwh_a.dim_hotel (hotel_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F01_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_booking ADD CONSTRAINT fk_f01_07 FOREIGN KEY (channel_key) REFERENCES ce_dwh_a.dim_channel (channel_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F01_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_booking ADD CONSTRAINT fk_f01_08 FOREIGN KEY (promotion_key) REFERENCES ce_dwh_a.dim_promotion (promotion_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F01_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_booking ADD CONSTRAINT fk_f01_09 FOREIGN KEY (customer_profile_key) REFERENCES ce_dwh_a.dim_customer_profile (customer_profile_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F02_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_room_day ADD CONSTRAINT fk_f02_03 FOREIGN KEY (date_key) REFERENCES ce_dwh_a.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F02_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_room_day ADD CONSTRAINT fk_f02_04 FOREIGN KEY (site_key) REFERENCES ce_dwh_a.dim_site (site_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F02_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_room_day ADD CONSTRAINT fk_f02_05 FOREIGN KEY (hotel_key) REFERENCES ce_dwh_a.dim_hotel (hotel_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F02_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_room_day ADD CONSTRAINT fk_f02_06 FOREIGN KEY (room_key) REFERENCES ce_dwh_a.dim_room (room_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F03_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stay_night ADD CONSTRAINT fk_f03_03 FOREIGN KEY (service_date_key) REFERENCES ce_dwh_a.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F03_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stay_night ADD CONSTRAINT fk_f03_04 FOREIGN KEY (site_key) REFERENCES ce_dwh_a.dim_site (site_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F03_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stay_night ADD CONSTRAINT fk_f03_05 FOREIGN KEY (hotel_key) REFERENCES ce_dwh_a.dim_hotel (hotel_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F03_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stay_night ADD CONSTRAINT fk_f03_06 FOREIGN KEY (room_key) REFERENCES ce_dwh_a.dim_room (room_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F03_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stay_night ADD CONSTRAINT fk_f03_07 FOREIGN KEY (channel_key) REFERENCES ce_dwh_a.dim_channel (channel_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F03_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stay_night ADD CONSTRAINT fk_f03_08 FOREIGN KEY (customer_profile_key) REFERENCES ce_dwh_a.dim_customer_profile (customer_profile_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F03_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stay_night ADD CONSTRAINT fk_f03_09 FOREIGN KEY (rate_plan_key) REFERENCES ce_dwh_a.dim_rate_plan (rate_plan_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F04_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_ticket_order ADD CONSTRAINT fk_f04_02 FOREIGN KEY (ordered_date_key) REFERENCES ce_dwh_a.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F04_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_ticket_order ADD CONSTRAINT fk_f04_03 FOREIGN KEY (cohort_departure_date_key) REFERENCES ce_dwh_a.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F04_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_ticket_order ADD CONSTRAINT fk_f04_04 FOREIGN KEY (service_site_key) REFERENCES ce_dwh_a.dim_site (site_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F04_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_ticket_order ADD CONSTRAINT fk_f04_05 FOREIGN KEY (booking_site_key) REFERENCES ce_dwh_a.dim_site (site_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F04_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_ticket_order ADD CONSTRAINT fk_f04_06 FOREIGN KEY (referral_hotel_key) REFERENCES ce_dwh_a.dim_hotel (hotel_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F04_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_ticket_order ADD CONSTRAINT fk_f04_07 FOREIGN KEY (ticket_channel_key) REFERENCES ce_dwh_a.dim_channel (channel_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F04_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_ticket_order ADD CONSTRAINT fk_f04_08 FOREIGN KEY (booking_channel_key) REFERENCES ce_dwh_a.dim_channel (channel_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F04_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_ticket_order ADD CONSTRAINT fk_f04_09 FOREIGN KEY (customer_profile_key) REFERENCES ce_dwh_a.dim_customer_profile (customer_profile_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F04_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_ticket_order ADD CONSTRAINT fk_f04_10 FOREIGN KEY (centre_key) REFERENCES ce_dwh_a.dim_centre (centre_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F05_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_rental ADD CONSTRAINT fk_f05_02 FOREIGN KEY (pickup_date_key) REFERENCES ce_dwh_a.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F05_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_rental ADD CONSTRAINT fk_f05_03 FOREIGN KEY (return_date_key) REFERENCES ce_dwh_a.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F05_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_rental ADD CONSTRAINT fk_f05_04 FOREIGN KEY (cohort_departure_date_key) REFERENCES ce_dwh_a.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F05_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_rental ADD CONSTRAINT fk_f05_05 FOREIGN KEY (service_site_key) REFERENCES ce_dwh_a.dim_site (site_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F05_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_rental ADD CONSTRAINT fk_f05_06 FOREIGN KEY (booking_site_key) REFERENCES ce_dwh_a.dim_site (site_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F05_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_rental ADD CONSTRAINT fk_f05_07 FOREIGN KEY (referral_hotel_key) REFERENCES ce_dwh_a.dim_hotel (hotel_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F05_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_rental ADD CONSTRAINT fk_f05_08 FOREIGN KEY (booking_channel_key) REFERENCES ce_dwh_a.dim_channel (channel_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F05_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_rental ADD CONSTRAINT fk_f05_09 FOREIGN KEY (customer_profile_key) REFERENCES ce_dwh_a.dim_customer_profile (customer_profile_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F05_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_rental ADD CONSTRAINT fk_f05_10 FOREIGN KEY (centre_key) REFERENCES ce_dwh_a.dim_centre (centre_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F05_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_rental ADD CONSTRAINT fk_f05_11 FOREIGN KEY (vehicle_key) REFERENCES ce_dwh_a.dim_vehicle (vehicle_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F06_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_breakfast_entitlement ADD CONSTRAINT fk_f06_02 FOREIGN KEY (service_date_key) REFERENCES ce_dwh_a.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F06_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_breakfast_entitlement ADD CONSTRAINT fk_f06_03 FOREIGN KEY (site_key) REFERENCES ce_dwh_a.dim_site (site_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F06_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_breakfast_entitlement ADD CONSTRAINT fk_f06_04 FOREIGN KEY (hotel_key) REFERENCES ce_dwh_a.dim_hotel (hotel_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F06_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_breakfast_entitlement ADD CONSTRAINT fk_f06_05 FOREIGN KEY (room_key) REFERENCES ce_dwh_a.dim_room (room_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F06_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_breakfast_entitlement ADD CONSTRAINT fk_f06_06 FOREIGN KEY (customer_profile_key) REFERENCES ce_dwh_a.dim_customer_profile (customer_profile_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F06_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_breakfast_entitlement ADD CONSTRAINT fk_f06_07 FOREIGN KEY (rate_plan_key) REFERENCES ce_dwh_a.dim_rate_plan (rate_plan_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F06_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_breakfast_entitlement ADD CONSTRAINT fk_f06_08 FOREIGN KEY (outlet_key) REFERENCES ce_dwh_a.dim_outlet (outlet_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F06_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_breakfast_entitlement ADD CONSTRAINT fk_f06_09 FOREIGN KEY (meal_key) REFERENCES ce_dwh_a.dim_meal (meal_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F07_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_dining_order ADD CONSTRAINT fk_f07_02 FOREIGN KEY (service_date_key) REFERENCES ce_dwh_a.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F07_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_dining_order ADD CONSTRAINT fk_f07_03 FOREIGN KEY (site_key) REFERENCES ce_dwh_a.dim_site (site_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F07_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_dining_order ADD CONSTRAINT fk_f07_04 FOREIGN KEY (service_hotel_key) REFERENCES ce_dwh_a.dim_hotel (hotel_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F07_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_dining_order ADD CONSTRAINT fk_f07_05 FOREIGN KEY (booking_hotel_key) REFERENCES ce_dwh_a.dim_hotel (hotel_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F07_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_dining_order ADD CONSTRAINT fk_f07_06 FOREIGN KEY (customer_profile_key) REFERENCES ce_dwh_a.dim_customer_profile (customer_profile_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F07_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_dining_order ADD CONSTRAINT fk_f07_07 FOREIGN KEY (outlet_key) REFERENCES ce_dwh_a.dim_outlet (outlet_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F07_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_dining_order ADD CONSTRAINT fk_f07_08 FOREIGN KEY (meal_key) REFERENCES ce_dwh_a.dim_meal (meal_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F08_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_meal_session ADD CONSTRAINT fk_f08_03 FOREIGN KEY (service_date_key) REFERENCES ce_dwh_a.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F08_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_meal_session ADD CONSTRAINT fk_f08_04 FOREIGN KEY (site_key) REFERENCES ce_dwh_a.dim_site (site_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F08_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_meal_session ADD CONSTRAINT fk_f08_05 FOREIGN KEY (hotel_key) REFERENCES ce_dwh_a.dim_hotel (hotel_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F08_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_meal_session ADD CONSTRAINT fk_f08_06 FOREIGN KEY (outlet_key) REFERENCES ce_dwh_a.dim_outlet (outlet_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F08_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_meal_session ADD CONSTRAINT fk_f08_07 FOREIGN KEY (meal_key) REFERENCES ce_dwh_a.dim_meal (meal_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F09_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_admission ADD CONSTRAINT fk_f09_02 FOREIGN KEY (admission_date_key) REFERENCES ce_dwh_a.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F09_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_admission ADD CONSTRAINT fk_f09_03 FOREIGN KEY (site_key) REFERENCES ce_dwh_a.dim_site (site_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F09_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_admission ADD CONSTRAINT fk_f09_04 FOREIGN KEY (customer_profile_key) REFERENCES ce_dwh_a.dim_customer_profile (customer_profile_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F09_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_admission ADD CONSTRAINT fk_f09_05 FOREIGN KEY (centre_key) REFERENCES ce_dwh_a.dim_centre (centre_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F09_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_admission ADD CONSTRAINT fk_f09_06 FOREIGN KEY (activity_key) REFERENCES ce_dwh_a.dim_activity (activity_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F10_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_activity_day ADD CONSTRAINT fk_f10_03 FOREIGN KEY (date_key) REFERENCES ce_dwh_a.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F10_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_activity_day ADD CONSTRAINT fk_f10_04 FOREIGN KEY (site_key) REFERENCES ce_dwh_a.dim_site (site_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F10_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_activity_day ADD CONSTRAINT fk_f10_05 FOREIGN KEY (centre_key) REFERENCES ce_dwh_a.dim_centre (centre_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F10_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_activity_day ADD CONSTRAINT fk_f10_06 FOREIGN KEY (activity_key) REFERENCES ce_dwh_a.dim_activity (activity_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F11_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_vehicle_day ADD CONSTRAINT fk_f11_03 FOREIGN KEY (date_key) REFERENCES ce_dwh_a.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F11_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_vehicle_day ADD CONSTRAINT fk_f11_04 FOREIGN KEY (site_key) REFERENCES ce_dwh_a.dim_site (site_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F11_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_vehicle_day ADD CONSTRAINT fk_f11_05 FOREIGN KEY (centre_key) REFERENCES ce_dwh_a.dim_centre (centre_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F11_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_vehicle_day ADD CONSTRAINT fk_f11_06 FOREIGN KEY (vehicle_key) REFERENCES ce_dwh_a.dim_vehicle (vehicle_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F12_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_purchase_line ADD CONSTRAINT fk_f12_02 FOREIGN KEY (ordered_date_key) REFERENCES ce_dwh_a.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F12_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_purchase_line ADD CONSTRAINT fk_f12_03 FOREIGN KEY (expected_date_key) REFERENCES ce_dwh_a.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F12_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_purchase_line ADD CONSTRAINT fk_f12_04 FOREIGN KEY (site_key) REFERENCES ce_dwh_a.dim_site (site_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F12_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_purchase_line ADD CONSTRAINT fk_f12_05 FOREIGN KEY (hotel_key) REFERENCES ce_dwh_a.dim_hotel (hotel_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F12_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_purchase_line ADD CONSTRAINT fk_f12_06 FOREIGN KEY (supplier_key) REFERENCES ce_dwh_a.dim_supplier (supplier_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F12_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_purchase_line ADD CONSTRAINT fk_f12_07 FOREIGN KEY (item_key) REFERENCES ce_dwh_a.dim_item (item_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F13_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_receipt ADD CONSTRAINT fk_f13_02 FOREIGN KEY (received_date_key) REFERENCES ce_dwh_a.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F13_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_receipt ADD CONSTRAINT fk_f13_03 FOREIGN KEY (expected_date_key) REFERENCES ce_dwh_a.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F13_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_receipt ADD CONSTRAINT fk_f13_04 FOREIGN KEY (expires_date_key) REFERENCES ce_dwh_a.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F13_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_receipt ADD CONSTRAINT fk_f13_05 FOREIGN KEY (site_key) REFERENCES ce_dwh_a.dim_site (site_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F13_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_receipt ADD CONSTRAINT fk_f13_06 FOREIGN KEY (hotel_key) REFERENCES ce_dwh_a.dim_hotel (hotel_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F13_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_receipt ADD CONSTRAINT fk_f13_07 FOREIGN KEY (supplier_key) REFERENCES ce_dwh_a.dim_supplier (supplier_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F13_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_receipt ADD CONSTRAINT fk_f13_08 FOREIGN KEY (item_key) REFERENCES ce_dwh_a.dim_item (item_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F14_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stock_movement ADD CONSTRAINT fk_f14_02 FOREIGN KEY (movement_date_key) REFERENCES ce_dwh_a.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F14_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stock_movement ADD CONSTRAINT fk_f14_03 FOREIGN KEY (site_key) REFERENCES ce_dwh_a.dim_site (site_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F14_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stock_movement ADD CONSTRAINT fk_f14_04 FOREIGN KEY (hotel_key) REFERENCES ce_dwh_a.dim_hotel (hotel_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F14_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stock_movement ADD CONSTRAINT fk_f14_05 FOREIGN KEY (supplier_key) REFERENCES ce_dwh_a.dim_supplier (supplier_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F14_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_stock_movement ADD CONSTRAINT fk_f14_06 FOREIGN KEY (item_key) REFERENCES ce_dwh_a.dim_item (item_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F15_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.agg_inventory_lot_day ADD CONSTRAINT fk_f15_04 FOREIGN KEY (snapshot_date_key) REFERENCES ce_dwh_a.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F15_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.agg_inventory_lot_day ADD CONSTRAINT fk_f15_05 FOREIGN KEY (site_key) REFERENCES ce_dwh_a.dim_site (site_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F15_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.agg_inventory_lot_day ADD CONSTRAINT fk_f15_06 FOREIGN KEY (hotel_key) REFERENCES ce_dwh_a.dim_hotel (hotel_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F15_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.agg_inventory_lot_day ADD CONSTRAINT fk_f15_07 FOREIGN KEY (supplier_key) REFERENCES ce_dwh_a.dim_supplier (supplier_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F15_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.agg_inventory_lot_day ADD CONSTRAINT fk_f15_08 FOREIGN KEY (item_key) REFERENCES ce_dwh_a.dim_item (item_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F16_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_maintenance_work ADD CONSTRAINT fk_f16_02 FOREIGN KEY (start_date_key) REFERENCES ce_dwh_a.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F16_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_maintenance_work ADD CONSTRAINT fk_f16_03 FOREIGN KEY (end_date_key) REFERENCES ce_dwh_a.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F16_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_maintenance_work ADD CONSTRAINT fk_f16_04 FOREIGN KEY (site_key) REFERENCES ce_dwh_a.dim_site (site_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F16_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_maintenance_work ADD CONSTRAINT fk_f16_05 FOREIGN KEY (hotel_key) REFERENCES ce_dwh_a.dim_hotel (hotel_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F16_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_maintenance_work ADD CONSTRAINT fk_f16_06 FOREIGN KEY (room_key) REFERENCES ce_dwh_a.dim_room (room_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F16_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_maintenance_work ADD CONSTRAINT fk_f16_07 FOREIGN KEY (asset_key) REFERENCES ce_dwh_a.dim_asset (asset_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F17_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_weather_day ADD CONSTRAINT fk_f17_03 FOREIGN KEY (weather_date_key) REFERENCES ce_dwh_a.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_F17_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.fact_weather_day ADD CONSTRAINT fk_f17_04 FOREIGN KEY (site_key) REFERENCES ce_dwh_a.dim_site (site_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_L01_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.bridge_booking_room ADD CONSTRAINT fk_l01_03 FOREIGN KEY (room_key) REFERENCES ce_dwh_a.dim_room (room_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_L01_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.bridge_booking_room ADD CONSTRAINT fk_l01_04 FOREIGN KEY (rate_plan_key) REFERENCES ce_dwh_a.dim_rate_plan (rate_plan_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_L02_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.bridge_room_day_maintenance ADD CONSTRAINT fk_l02_03 FOREIGN KEY (room_key) REFERENCES ce_dwh_a.dim_room (room_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_A' AND constraint_name='FK_L02_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_a.bridge_room_day_maintenance ADD CONSTRAINT fk_l02_04 FOREIGN KEY (date_key) REFERENCES ce_dwh_a.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_B' AND table_name='DIM_DATE'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_b.dim_date (
  date_key NUMBER(8,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  member_kind VARCHAR2(64 CHAR) NOT NULL,
  calendar_date DATE,
  day NUMBER(10,0),
  day_of_week NUMBER(10,0),
  month NUMBER(10,0),
  quarter NUMBER(10,0),
  year NUMBER(10,0),
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='PK_D01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_date ADD CONSTRAINT pk_d01 PRIMARY KEY (date_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='UK_D01_1'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_date ADD CONSTRAINT uk_d01_1 UNIQUE (calendar_date) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D01_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_date ADD CONSTRAINT ck_d01_01 CHECK (date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D01_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_date ADD CONSTRAINT ck_d01_02 CHECK (calendar_date=TRUNC(calendar_date))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D01_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_date ADD CONSTRAINT ck_d01_03 CHECK (day BETWEEN -2147483648 AND 2147483647)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D01_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_date ADD CONSTRAINT ck_d01_04 CHECK (day_of_week BETWEEN -2147483648 AND 2147483647)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D01_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_date ADD CONSTRAINT ck_d01_05 CHECK (month BETWEEN -2147483648 AND 2147483647)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D01_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_date ADD CONSTRAINT ck_d01_06 CHECK (quarter BETWEEN -2147483648 AND 2147483647)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D01_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_date ADD CONSTRAINT ck_d01_07 CHECK (year BETWEEN -2147483648 AND 2147483647)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D01_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_date ADD CONSTRAINT ck_d01_08 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D01_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_date ADD CONSTRAINT ck_d01_09 CHECK ((member_kind=''NORMAL'' AND date_key>0) OR (member_kind=''UNKNOWN'' AND date_key=0) OR (member_kind=''NOT_APPLICABLE'' AND date_key=-1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D01_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_date ADD CONSTRAINT ck_d01_10 CHECK (member_kind<>''NORMAL'' OR (calendar_date IS NOT NULL AND day IS NOT NULL AND day_of_week IS NOT NULL AND month IS NOT NULL AND quarter IS NOT NULL AND year IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D01_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_date ADD CONSTRAINT ck_d01_11 CHECK (member_kind<>''NORMAL'' OR date_key=TO_NUMBER(TO_CHAR(calendar_date,''YYYYMMDD'')))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D01_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_date ADD CONSTRAINT ck_d01_12 CHECK (member_kind<>''NORMAL'' OR year=EXTRACT(YEAR FROM calendar_date))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D01_13'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_date ADD CONSTRAINT ck_d01_13 CHECK (member_kind<>''NORMAL'' OR month=EXTRACT(MONTH FROM calendar_date))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D01_14'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_date ADD CONSTRAINT ck_d01_14 CHECK (member_kind<>''NORMAL'' OR day=EXTRACT(DAY FROM calendar_date))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D01_15'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_date ADD CONSTRAINT ck_d01_15 CHECK (member_kind<>''NORMAL'' OR quarter=CEIL(month/3.0))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D01_16'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_date ADD CONSTRAINT ck_d01_16 CHECK (member_kind<>''NORMAL'' OR day_of_week=calendar_date-TRUNC(calendar_date,''IW'')+1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_B' AND table_name='DIM_SITE'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_b.dim_site (
  site_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  member_kind VARCHAR2(64 CHAR) NOT NULL,
  site_id VARCHAR2(128 CHAR),
  site_name VARCHAR2(512 CHAR),
  climate_region VARCHAR2(512 CHAR),
  valid_from_utc TIMESTAMP(6) NOT NULL,
  valid_to_utc TIMESTAMP(6),
  is_current NUMBER(1,0) NOT NULL,
  version_no NUMBER(18,0) NOT NULL,
  effective_time_basis VARCHAR2(64 CHAR) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='PK_D02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_site ADD CONSTRAINT pk_d02 PRIMARY KEY (site_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UK_D02_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uk_d02_1 ON ce_dwh_b.dim_site (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN site_id END,CASE WHEN member_kind=''NORMAL'' THEN valid_from_utc END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UK_D02_2'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uk_d02_2 ON ce_dwh_b.dim_site (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN site_id END,CASE WHEN member_kind=''NORMAL'' THEN version_no END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UC_D02_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uc_d02_1 ON ce_dwh_b.dim_site (CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN source_system END,CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN site_id END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D02_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_site ADD CONSTRAINT ck_d02_01 CHECK (site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D02_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_site ADD CONSTRAINT ck_d02_02 CHECK (is_current IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D02_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_site ADD CONSTRAINT ck_d02_03 CHECK (version_no>=0 AND version_no<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D02_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_site ADD CONSTRAINT ck_d02_04 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D02_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_site ADD CONSTRAINT ck_d02_05 CHECK ((member_kind=''NORMAL'' AND site_key>0) OR (member_kind=''UNKNOWN'' AND site_key=0) OR (member_kind=''NOT_APPLICABLE'' AND site_key=-1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D02_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_site ADD CONSTRAINT ck_d02_06 CHECK (member_kind<>''NORMAL'' OR (site_id IS NOT NULL AND site_name IS NOT NULL AND climate_region IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D02_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_site ADD CONSTRAINT ck_d02_07 CHECK (version_no>=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D02_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_site ADD CONSTRAINT ck_d02_08 CHECK ((is_current=1 AND valid_to_utc IS NULL) OR (is_current=0 AND valid_to_utc IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D02_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_site ADD CONSTRAINT ck_d02_09 CHECK (valid_to_utc IS NULL OR valid_from_utc<valid_to_utc)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D02_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_site ADD CONSTRAINT ck_d02_10 CHECK (member_kind=''NORMAL'' OR (version_no=1 AND is_current=1 AND valid_to_utc IS NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_B' AND table_name='DIM_HOTEL'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_b.dim_hotel (
  hotel_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  member_kind VARCHAR2(64 CHAR) NOT NULL,
  hotel_id VARCHAR2(128 CHAR),
  hotel_name VARCHAR2(512 CHAR),
  stars NUMBER(10,0),
  site_id VARCHAR2(128 CHAR),
  website_channel VARCHAR2(512 CHAR),
  valid_from_utc TIMESTAMP(6) NOT NULL,
  valid_to_utc TIMESTAMP(6),
  is_current NUMBER(1,0) NOT NULL,
  version_no NUMBER(18,0) NOT NULL,
  effective_time_basis VARCHAR2(64 CHAR) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='PK_D03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_hotel ADD CONSTRAINT pk_d03 PRIMARY KEY (hotel_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UK_D03_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uk_d03_1 ON ce_dwh_b.dim_hotel (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN hotel_id END,CASE WHEN member_kind=''NORMAL'' THEN valid_from_utc END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UK_D03_2'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uk_d03_2 ON ce_dwh_b.dim_hotel (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN hotel_id END,CASE WHEN member_kind=''NORMAL'' THEN version_no END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UC_D03_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uc_d03_1 ON ce_dwh_b.dim_hotel (CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN source_system END,CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN hotel_id END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D03_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_hotel ADD CONSTRAINT ck_d03_01 CHECK (hotel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D03_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_hotel ADD CONSTRAINT ck_d03_02 CHECK (stars BETWEEN -2147483648 AND 2147483647)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D03_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_hotel ADD CONSTRAINT ck_d03_03 CHECK (is_current IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D03_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_hotel ADD CONSTRAINT ck_d03_04 CHECK (version_no>=0 AND version_no<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D03_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_hotel ADD CONSTRAINT ck_d03_05 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D03_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_hotel ADD CONSTRAINT ck_d03_06 CHECK ((member_kind=''NORMAL'' AND hotel_key>0) OR (member_kind=''UNKNOWN'' AND hotel_key=0) OR (member_kind=''NOT_APPLICABLE'' AND hotel_key=-1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D03_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_hotel ADD CONSTRAINT ck_d03_07 CHECK (member_kind<>''NORMAL'' OR (hotel_id IS NOT NULL AND hotel_name IS NOT NULL AND stars IS NOT NULL AND site_id IS NOT NULL AND website_channel IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D03_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_hotel ADD CONSTRAINT ck_d03_08 CHECK (version_no>=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D03_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_hotel ADD CONSTRAINT ck_d03_09 CHECK ((is_current=1 AND valid_to_utc IS NULL) OR (is_current=0 AND valid_to_utc IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D03_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_hotel ADD CONSTRAINT ck_d03_10 CHECK (valid_to_utc IS NULL OR valid_from_utc<valid_to_utc)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D03_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_hotel ADD CONSTRAINT ck_d03_11 CHECK (member_kind=''NORMAL'' OR (version_no=1 AND is_current=1 AND valid_to_utc IS NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D03_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_hotel ADD CONSTRAINT ck_d03_12 CHECK (member_kind<>''NORMAL'' OR (stars IN (3,5)))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_B' AND table_name='DIM_ROOM'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_b.dim_room (
  room_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  member_kind VARCHAR2(64 CHAR) NOT NULL,
  room_id VARCHAR2(128 CHAR),
  hotel_id VARCHAR2(128 CHAR),
  room_type VARCHAR2(512 CHAR),
  capacity NUMBER(10,0),
  base_rate_vnd NUMBER(19,0),
  valid_from_utc TIMESTAMP(6) NOT NULL,
  valid_to_utc TIMESTAMP(6),
  is_current NUMBER(1,0) NOT NULL,
  version_no NUMBER(18,0) NOT NULL,
  effective_time_basis VARCHAR2(64 CHAR) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='PK_D04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_room ADD CONSTRAINT pk_d04 PRIMARY KEY (room_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UK_D04_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uk_d04_1 ON ce_dwh_b.dim_room (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN room_id END,CASE WHEN member_kind=''NORMAL'' THEN valid_from_utc END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UK_D04_2'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uk_d04_2 ON ce_dwh_b.dim_room (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN room_id END,CASE WHEN member_kind=''NORMAL'' THEN version_no END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UC_D04_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uc_d04_1 ON ce_dwh_b.dim_room (CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN source_system END,CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN room_id END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D04_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_room ADD CONSTRAINT ck_d04_01 CHECK (room_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D04_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_room ADD CONSTRAINT ck_d04_02 CHECK (capacity BETWEEN -2147483648 AND 2147483647)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D04_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_room ADD CONSTRAINT ck_d04_03 CHECK (is_current IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D04_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_room ADD CONSTRAINT ck_d04_04 CHECK (version_no>=0 AND version_no<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D04_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_room ADD CONSTRAINT ck_d04_05 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D04_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_room ADD CONSTRAINT ck_d04_06 CHECK ((member_kind=''NORMAL'' AND room_key>0) OR (member_kind=''UNKNOWN'' AND room_key=0) OR (member_kind=''NOT_APPLICABLE'' AND room_key=-1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D04_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_room ADD CONSTRAINT ck_d04_07 CHECK (member_kind<>''NORMAL'' OR (room_id IS NOT NULL AND hotel_id IS NOT NULL AND room_type IS NOT NULL AND capacity IS NOT NULL AND base_rate_vnd IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D04_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_room ADD CONSTRAINT ck_d04_08 CHECK (version_no>=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D04_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_room ADD CONSTRAINT ck_d04_09 CHECK ((is_current=1 AND valid_to_utc IS NULL) OR (is_current=0 AND valid_to_utc IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D04_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_room ADD CONSTRAINT ck_d04_10 CHECK (valid_to_utc IS NULL OR valid_from_utc<valid_to_utc)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D04_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_room ADD CONSTRAINT ck_d04_11 CHECK (member_kind=''NORMAL'' OR (version_no=1 AND is_current=1 AND valid_to_utc IS NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D04_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_room ADD CONSTRAINT ck_d04_12 CHECK (member_kind<>''NORMAL'' OR (capacity>0))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D04_13'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_room ADD CONSTRAINT ck_d04_13 CHECK (member_kind<>''NORMAL'' OR (base_rate_vnd>0))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_B' AND table_name='DIM_CHANNEL'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_b.dim_channel (
  channel_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  member_kind VARCHAR2(64 CHAR) NOT NULL,
  channel_code VARCHAR2(128 CHAR),
  channel_name VARCHAR2(512 CHAR),
  channel_type VARCHAR2(512 CHAR),
  commission_bps NUMBER(10,0),
  valid_from_utc TIMESTAMP(6) NOT NULL,
  valid_to_utc TIMESTAMP(6),
  is_current NUMBER(1,0) NOT NULL,
  version_no NUMBER(18,0) NOT NULL,
  effective_time_basis VARCHAR2(64 CHAR) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='PK_D05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_channel ADD CONSTRAINT pk_d05 PRIMARY KEY (channel_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UK_D05_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uk_d05_1 ON ce_dwh_b.dim_channel (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN channel_code END,CASE WHEN member_kind=''NORMAL'' THEN valid_from_utc END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UK_D05_2'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uk_d05_2 ON ce_dwh_b.dim_channel (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN channel_code END,CASE WHEN member_kind=''NORMAL'' THEN version_no END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UC_D05_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uc_d05_1 ON ce_dwh_b.dim_channel (CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN source_system END,CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN channel_code END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D05_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_channel ADD CONSTRAINT ck_d05_01 CHECK (channel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D05_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_channel ADD CONSTRAINT ck_d05_02 CHECK (commission_bps BETWEEN -2147483648 AND 2147483647)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D05_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_channel ADD CONSTRAINT ck_d05_03 CHECK (is_current IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D05_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_channel ADD CONSTRAINT ck_d05_04 CHECK (version_no>=0 AND version_no<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D05_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_channel ADD CONSTRAINT ck_d05_05 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D05_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_channel ADD CONSTRAINT ck_d05_06 CHECK ((member_kind=''NORMAL'' AND channel_key>0) OR (member_kind=''UNKNOWN'' AND channel_key=0) OR (member_kind=''NOT_APPLICABLE'' AND channel_key=-1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D05_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_channel ADD CONSTRAINT ck_d05_07 CHECK (member_kind<>''NORMAL'' OR (channel_code IS NOT NULL AND channel_name IS NOT NULL AND channel_type IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D05_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_channel ADD CONSTRAINT ck_d05_08 CHECK (version_no>=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D05_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_channel ADD CONSTRAINT ck_d05_09 CHECK ((is_current=1 AND valid_to_utc IS NULL) OR (is_current=0 AND valid_to_utc IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D05_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_channel ADD CONSTRAINT ck_d05_10 CHECK (valid_to_utc IS NULL OR valid_from_utc<valid_to_utc)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D05_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_channel ADD CONSTRAINT ck_d05_11 CHECK (member_kind=''NORMAL'' OR (version_no=1 AND is_current=1 AND valid_to_utc IS NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D05_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_channel ADD CONSTRAINT ck_d05_12 CHECK (member_kind<>''NORMAL'' OR (commission_bps BETWEEN 0 AND 10000))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_B' AND table_name='DIM_PROMOTION'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_b.dim_promotion (
  promotion_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  member_kind VARCHAR2(64 CHAR) NOT NULL,
  promotion_id VARCHAR2(128 CHAR),
  promotion_name VARCHAR2(512 CHAR),
  channel_id VARCHAR2(128 CHAR),
  site_id VARCHAR2(128 CHAR),
  sale_from DATE,
  sale_to DATE,
  stay_from DATE,
  stay_to DATE,
  discount_bps NUMBER(10,0),
  partner_share_bps NUMBER(10,0),
  cap_vnd NUMBER(19,0),
  valid_from_utc TIMESTAMP(6) NOT NULL,
  valid_to_utc TIMESTAMP(6),
  is_current NUMBER(1,0) NOT NULL,
  version_no NUMBER(18,0) NOT NULL,
  effective_time_basis VARCHAR2(64 CHAR) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='PK_D06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_promotion ADD CONSTRAINT pk_d06 PRIMARY KEY (promotion_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UK_D06_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uk_d06_1 ON ce_dwh_b.dim_promotion (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN promotion_id END,CASE WHEN member_kind=''NORMAL'' THEN valid_from_utc END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UK_D06_2'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uk_d06_2 ON ce_dwh_b.dim_promotion (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN promotion_id END,CASE WHEN member_kind=''NORMAL'' THEN version_no END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UC_D06_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uc_d06_1 ON ce_dwh_b.dim_promotion (CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN source_system END,CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN promotion_id END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D06_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_promotion ADD CONSTRAINT ck_d06_01 CHECK (promotion_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D06_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_promotion ADD CONSTRAINT ck_d06_02 CHECK (sale_from=TRUNC(sale_from))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D06_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_promotion ADD CONSTRAINT ck_d06_03 CHECK (sale_to=TRUNC(sale_to))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D06_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_promotion ADD CONSTRAINT ck_d06_04 CHECK (stay_from=TRUNC(stay_from))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D06_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_promotion ADD CONSTRAINT ck_d06_05 CHECK (stay_to=TRUNC(stay_to))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D06_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_promotion ADD CONSTRAINT ck_d06_06 CHECK (discount_bps BETWEEN -2147483648 AND 2147483647)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D06_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_promotion ADD CONSTRAINT ck_d06_07 CHECK (partner_share_bps BETWEEN -2147483648 AND 2147483647)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D06_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_promotion ADD CONSTRAINT ck_d06_08 CHECK (is_current IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D06_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_promotion ADD CONSTRAINT ck_d06_09 CHECK (version_no>=0 AND version_no<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D06_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_promotion ADD CONSTRAINT ck_d06_10 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D06_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_promotion ADD CONSTRAINT ck_d06_11 CHECK ((member_kind=''NORMAL'' AND promotion_key>0) OR (member_kind=''UNKNOWN'' AND promotion_key=0) OR (member_kind=''NOT_APPLICABLE'' AND promotion_key=-1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D06_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_promotion ADD CONSTRAINT ck_d06_12 CHECK (member_kind<>''NORMAL'' OR (promotion_id IS NOT NULL AND promotion_name IS NOT NULL AND sale_from IS NOT NULL AND sale_to IS NOT NULL AND stay_from IS NOT NULL AND stay_to IS NOT NULL AND discount_bps IS NOT NULL AND partner_share_bps IS NOT NULL AND cap_vnd IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D06_13'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_promotion ADD CONSTRAINT ck_d06_13 CHECK (version_no>=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D06_14'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_promotion ADD CONSTRAINT ck_d06_14 CHECK ((is_current=1 AND valid_to_utc IS NULL) OR (is_current=0 AND valid_to_utc IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D06_15'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_promotion ADD CONSTRAINT ck_d06_15 CHECK (valid_to_utc IS NULL OR valid_from_utc<valid_to_utc)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D06_16'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_promotion ADD CONSTRAINT ck_d06_16 CHECK (member_kind=''NORMAL'' OR (version_no=1 AND is_current=1 AND valid_to_utc IS NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D06_17'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_promotion ADD CONSTRAINT ck_d06_17 CHECK (member_kind<>''NORMAL'' OR (discount_bps BETWEEN 0 AND 10000))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D06_18'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_promotion ADD CONSTRAINT ck_d06_18 CHECK (member_kind<>''NORMAL'' OR (partner_share_bps BETWEEN 0 AND 10000))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D06_19'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_promotion ADD CONSTRAINT ck_d06_19 CHECK (member_kind<>''NORMAL'' OR (cap_vnd>=0))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D06_20'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_promotion ADD CONSTRAINT ck_d06_20 CHECK (member_kind<>''NORMAL'' OR (sale_to>=sale_from))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D06_21'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_promotion ADD CONSTRAINT ck_d06_21 CHECK (member_kind<>''NORMAL'' OR (stay_to>=stay_from))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_B' AND table_name='DIM_CUSTOMER_PROFILE'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_b.dim_customer_profile (
  customer_profile_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  member_kind VARCHAR2(64 CHAR) NOT NULL,
  source_customer_id VARCHAR2(128 CHAR),
  full_name VARCHAR2(512 CHAR),
  phone VARCHAR2(512 CHAR),
  email VARCHAR2(512 CHAR),
  member_card_ref VARCHAR2(128 CHAR),
  valid_from_utc TIMESTAMP(6) NOT NULL,
  valid_to_utc TIMESTAMP(6),
  is_current NUMBER(1,0) NOT NULL,
  version_no NUMBER(18,0) NOT NULL,
  effective_time_basis VARCHAR2(64 CHAR) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='PK_D07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_customer_profile ADD CONSTRAINT pk_d07 PRIMARY KEY (customer_profile_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UK_D07_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uk_d07_1 ON ce_dwh_b.dim_customer_profile (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN source_customer_id END,CASE WHEN member_kind=''NORMAL'' THEN valid_from_utc END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UK_D07_2'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uk_d07_2 ON ce_dwh_b.dim_customer_profile (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN source_customer_id END,CASE WHEN member_kind=''NORMAL'' THEN version_no END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UC_D07_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uc_d07_1 ON ce_dwh_b.dim_customer_profile (CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN source_system END,CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN source_customer_id END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D07_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_customer_profile ADD CONSTRAINT ck_d07_01 CHECK (customer_profile_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D07_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_customer_profile ADD CONSTRAINT ck_d07_02 CHECK (is_current IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D07_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_customer_profile ADD CONSTRAINT ck_d07_03 CHECK (version_no>=0 AND version_no<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D07_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_customer_profile ADD CONSTRAINT ck_d07_04 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D07_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_customer_profile ADD CONSTRAINT ck_d07_05 CHECK ((member_kind=''NORMAL'' AND customer_profile_key>0) OR (member_kind=''UNKNOWN'' AND customer_profile_key=0) OR (member_kind=''NOT_APPLICABLE'' AND customer_profile_key=-1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D07_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_customer_profile ADD CONSTRAINT ck_d07_06 CHECK (member_kind<>''NORMAL'' OR (source_customer_id IS NOT NULL AND full_name IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D07_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_customer_profile ADD CONSTRAINT ck_d07_07 CHECK (version_no>=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D07_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_customer_profile ADD CONSTRAINT ck_d07_08 CHECK ((is_current=1 AND valid_to_utc IS NULL) OR (is_current=0 AND valid_to_utc IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D07_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_customer_profile ADD CONSTRAINT ck_d07_09 CHECK (valid_to_utc IS NULL OR valid_from_utc<valid_to_utc)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D07_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_customer_profile ADD CONSTRAINT ck_d07_10 CHECK (member_kind=''NORMAL'' OR (version_no=1 AND is_current=1 AND valid_to_utc IS NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_B' AND table_name='DIM_RATE_PLAN'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_b.dim_rate_plan (
  rate_plan_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  member_kind VARCHAR2(64 CHAR) NOT NULL,
  rate_plan_id VARCHAR2(128 CHAR),
  hotel_id VARCHAR2(128 CHAR),
  channel_id VARCHAR2(128 CHAR),
  plan_name VARCHAR2(512 CHAR),
  breakfast_included NUMBER(1,0),
  refundable NUMBER(1,0),
  valid_from_utc TIMESTAMP(6) NOT NULL,
  valid_to_utc TIMESTAMP(6),
  is_current NUMBER(1,0) NOT NULL,
  version_no NUMBER(18,0) NOT NULL,
  effective_time_basis VARCHAR2(64 CHAR) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='PK_D08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_rate_plan ADD CONSTRAINT pk_d08 PRIMARY KEY (rate_plan_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UK_D08_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uk_d08_1 ON ce_dwh_b.dim_rate_plan (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN rate_plan_id END,CASE WHEN member_kind=''NORMAL'' THEN valid_from_utc END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UK_D08_2'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uk_d08_2 ON ce_dwh_b.dim_rate_plan (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN rate_plan_id END,CASE WHEN member_kind=''NORMAL'' THEN version_no END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UC_D08_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uc_d08_1 ON ce_dwh_b.dim_rate_plan (CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN source_system END,CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN rate_plan_id END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D08_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_rate_plan ADD CONSTRAINT ck_d08_01 CHECK (rate_plan_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D08_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_rate_plan ADD CONSTRAINT ck_d08_02 CHECK (breakfast_included IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D08_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_rate_plan ADD CONSTRAINT ck_d08_03 CHECK (refundable IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D08_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_rate_plan ADD CONSTRAINT ck_d08_04 CHECK (is_current IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D08_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_rate_plan ADD CONSTRAINT ck_d08_05 CHECK (version_no>=0 AND version_no<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D08_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_rate_plan ADD CONSTRAINT ck_d08_06 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D08_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_rate_plan ADD CONSTRAINT ck_d08_07 CHECK ((member_kind=''NORMAL'' AND rate_plan_key>0) OR (member_kind=''UNKNOWN'' AND rate_plan_key=0) OR (member_kind=''NOT_APPLICABLE'' AND rate_plan_key=-1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D08_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_rate_plan ADD CONSTRAINT ck_d08_08 CHECK (member_kind<>''NORMAL'' OR (rate_plan_id IS NOT NULL AND hotel_id IS NOT NULL AND channel_id IS NOT NULL AND plan_name IS NOT NULL AND breakfast_included IS NOT NULL AND refundable IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D08_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_rate_plan ADD CONSTRAINT ck_d08_09 CHECK (version_no>=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D08_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_rate_plan ADD CONSTRAINT ck_d08_10 CHECK ((is_current=1 AND valid_to_utc IS NULL) OR (is_current=0 AND valid_to_utc IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D08_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_rate_plan ADD CONSTRAINT ck_d08_11 CHECK (valid_to_utc IS NULL OR valid_from_utc<valid_to_utc)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D08_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_rate_plan ADD CONSTRAINT ck_d08_12 CHECK (member_kind=''NORMAL'' OR (version_no=1 AND is_current=1 AND valid_to_utc IS NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_B' AND table_name='DIM_OUTLET'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_b.dim_outlet (
  outlet_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  member_kind VARCHAR2(64 CHAR) NOT NULL,
  outlet_id VARCHAR2(128 CHAR),
  hotel_id VARCHAR2(128 CHAR),
  outlet_type VARCHAR2(512 CHAR),
  capacity NUMBER(10,0),
  quality_profile NUMBER(10,0),
  valid_from_utc TIMESTAMP(6) NOT NULL,
  valid_to_utc TIMESTAMP(6),
  is_current NUMBER(1,0) NOT NULL,
  version_no NUMBER(18,0) NOT NULL,
  effective_time_basis VARCHAR2(64 CHAR) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='PK_D09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_outlet ADD CONSTRAINT pk_d09 PRIMARY KEY (outlet_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UK_D09_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uk_d09_1 ON ce_dwh_b.dim_outlet (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN outlet_id END,CASE WHEN member_kind=''NORMAL'' THEN valid_from_utc END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UK_D09_2'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uk_d09_2 ON ce_dwh_b.dim_outlet (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN outlet_id END,CASE WHEN member_kind=''NORMAL'' THEN version_no END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UC_D09_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uc_d09_1 ON ce_dwh_b.dim_outlet (CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN source_system END,CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN outlet_id END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D09_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_outlet ADD CONSTRAINT ck_d09_01 CHECK (outlet_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D09_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_outlet ADD CONSTRAINT ck_d09_02 CHECK (capacity BETWEEN -2147483648 AND 2147483647)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D09_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_outlet ADD CONSTRAINT ck_d09_03 CHECK (quality_profile BETWEEN -2147483648 AND 2147483647)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D09_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_outlet ADD CONSTRAINT ck_d09_04 CHECK (is_current IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D09_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_outlet ADD CONSTRAINT ck_d09_05 CHECK (version_no>=0 AND version_no<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D09_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_outlet ADD CONSTRAINT ck_d09_06 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D09_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_outlet ADD CONSTRAINT ck_d09_07 CHECK ((member_kind=''NORMAL'' AND outlet_key>0) OR (member_kind=''UNKNOWN'' AND outlet_key=0) OR (member_kind=''NOT_APPLICABLE'' AND outlet_key=-1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D09_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_outlet ADD CONSTRAINT ck_d09_08 CHECK (member_kind<>''NORMAL'' OR (outlet_id IS NOT NULL AND hotel_id IS NOT NULL AND outlet_type IS NOT NULL AND capacity IS NOT NULL AND quality_profile IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D09_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_outlet ADD CONSTRAINT ck_d09_09 CHECK (version_no>=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D09_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_outlet ADD CONSTRAINT ck_d09_10 CHECK ((is_current=1 AND valid_to_utc IS NULL) OR (is_current=0 AND valid_to_utc IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D09_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_outlet ADD CONSTRAINT ck_d09_11 CHECK (valid_to_utc IS NULL OR valid_from_utc<valid_to_utc)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D09_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_outlet ADD CONSTRAINT ck_d09_12 CHECK (member_kind=''NORMAL'' OR (version_no=1 AND is_current=1 AND valid_to_utc IS NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D09_13'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_outlet ADD CONSTRAINT ck_d09_13 CHECK (member_kind<>''NORMAL'' OR (outlet_type IN (''RESTAURANT'',''BAR'')))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D09_14'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_outlet ADD CONSTRAINT ck_d09_14 CHECK (member_kind<>''NORMAL'' OR (capacity>0))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_B' AND table_name='DIM_MEAL'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_b.dim_meal (
  meal_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  member_kind VARCHAR2(64 CHAR) NOT NULL,
  meal_code VARCHAR2(64 CHAR),
  meal_name VARCHAR2(512 CHAR),
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='PK_D10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_meal ADD CONSTRAINT pk_d10 PRIMARY KEY (meal_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='UK_D10_1'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_meal ADD CONSTRAINT uk_d10_1 UNIQUE (meal_code) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D10_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_meal ADD CONSTRAINT ck_d10_01 CHECK (meal_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D10_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_meal ADD CONSTRAINT ck_d10_02 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D10_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_meal ADD CONSTRAINT ck_d10_03 CHECK ((member_kind=''NORMAL'' AND meal_key>0) OR (member_kind=''UNKNOWN'' AND meal_key=0) OR (member_kind=''NOT_APPLICABLE'' AND meal_key=-1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D10_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_meal ADD CONSTRAINT ck_d10_04 CHECK (member_kind<>''NORMAL'' OR (meal_code IS NOT NULL AND meal_name IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D10_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_meal ADD CONSTRAINT ck_d10_05 CHECK (member_kind<>''NORMAL'' OR (meal_key=1 AND meal_code=''BREAKFAST'') OR (meal_key=2 AND meal_code=''LUNCH'') OR (meal_key=3 AND meal_code=''DINNER'') OR (meal_key=4 AND meal_code=''BAR''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_B' AND table_name='DIM_CENTRE'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_b.dim_centre (
  centre_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  member_kind VARCHAR2(64 CHAR) NOT NULL,
  centre_id VARCHAR2(128 CHAR),
  centre_name VARCHAR2(512 CHAR),
  site_code VARCHAR2(128 CHAR),
  valid_from_utc TIMESTAMP(6) NOT NULL,
  valid_to_utc TIMESTAMP(6),
  is_current NUMBER(1,0) NOT NULL,
  version_no NUMBER(18,0) NOT NULL,
  effective_time_basis VARCHAR2(64 CHAR) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='PK_D11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_centre ADD CONSTRAINT pk_d11 PRIMARY KEY (centre_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UK_D11_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uk_d11_1 ON ce_dwh_b.dim_centre (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN centre_id END,CASE WHEN member_kind=''NORMAL'' THEN valid_from_utc END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UK_D11_2'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uk_d11_2 ON ce_dwh_b.dim_centre (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN centre_id END,CASE WHEN member_kind=''NORMAL'' THEN version_no END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UC_D11_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uc_d11_1 ON ce_dwh_b.dim_centre (CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN source_system END,CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN centre_id END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D11_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_centre ADD CONSTRAINT ck_d11_01 CHECK (centre_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D11_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_centre ADD CONSTRAINT ck_d11_02 CHECK (is_current IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D11_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_centre ADD CONSTRAINT ck_d11_03 CHECK (version_no>=0 AND version_no<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D11_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_centre ADD CONSTRAINT ck_d11_04 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D11_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_centre ADD CONSTRAINT ck_d11_05 CHECK ((member_kind=''NORMAL'' AND centre_key>0) OR (member_kind=''UNKNOWN'' AND centre_key=0) OR (member_kind=''NOT_APPLICABLE'' AND centre_key=-1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D11_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_centre ADD CONSTRAINT ck_d11_06 CHECK (member_kind<>''NORMAL'' OR (centre_id IS NOT NULL AND centre_name IS NOT NULL AND site_code IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D11_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_centre ADD CONSTRAINT ck_d11_07 CHECK (version_no>=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D11_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_centre ADD CONSTRAINT ck_d11_08 CHECK ((is_current=1 AND valid_to_utc IS NULL) OR (is_current=0 AND valid_to_utc IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D11_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_centre ADD CONSTRAINT ck_d11_09 CHECK (valid_to_utc IS NULL OR valid_from_utc<valid_to_utc)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D11_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_centre ADD CONSTRAINT ck_d11_10 CHECK (member_kind=''NORMAL'' OR (version_no=1 AND is_current=1 AND valid_to_utc IS NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_B' AND table_name='DIM_ACTIVITY'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_b.dim_activity (
  activity_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  member_kind VARCHAR2(64 CHAR) NOT NULL,
  activity_id VARCHAR2(128 CHAR),
  centre_id VARCHAR2(128 CHAR),
  activity_name VARCHAR2(512 CHAR),
  outdoor NUMBER(1,0),
  capacity_per_day NUMBER(10,0),
  valid_from_utc TIMESTAMP(6) NOT NULL,
  valid_to_utc TIMESTAMP(6),
  is_current NUMBER(1,0) NOT NULL,
  version_no NUMBER(18,0) NOT NULL,
  effective_time_basis VARCHAR2(64 CHAR) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='PK_D12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_activity ADD CONSTRAINT pk_d12 PRIMARY KEY (activity_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UK_D12_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uk_d12_1 ON ce_dwh_b.dim_activity (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN activity_id END,CASE WHEN member_kind=''NORMAL'' THEN valid_from_utc END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UK_D12_2'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uk_d12_2 ON ce_dwh_b.dim_activity (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN activity_id END,CASE WHEN member_kind=''NORMAL'' THEN version_no END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UC_D12_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uc_d12_1 ON ce_dwh_b.dim_activity (CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN source_system END,CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN activity_id END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D12_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_activity ADD CONSTRAINT ck_d12_01 CHECK (activity_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D12_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_activity ADD CONSTRAINT ck_d12_02 CHECK (outdoor IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D12_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_activity ADD CONSTRAINT ck_d12_03 CHECK (capacity_per_day BETWEEN -2147483648 AND 2147483647)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D12_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_activity ADD CONSTRAINT ck_d12_04 CHECK (is_current IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D12_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_activity ADD CONSTRAINT ck_d12_05 CHECK (version_no>=0 AND version_no<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D12_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_activity ADD CONSTRAINT ck_d12_06 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D12_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_activity ADD CONSTRAINT ck_d12_07 CHECK ((member_kind=''NORMAL'' AND activity_key>0) OR (member_kind=''UNKNOWN'' AND activity_key=0) OR (member_kind=''NOT_APPLICABLE'' AND activity_key=-1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D12_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_activity ADD CONSTRAINT ck_d12_08 CHECK (member_kind<>''NORMAL'' OR (activity_id IS NOT NULL AND centre_id IS NOT NULL AND activity_name IS NOT NULL AND outdoor IS NOT NULL AND capacity_per_day IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D12_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_activity ADD CONSTRAINT ck_d12_09 CHECK (version_no>=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D12_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_activity ADD CONSTRAINT ck_d12_10 CHECK ((is_current=1 AND valid_to_utc IS NULL) OR (is_current=0 AND valid_to_utc IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D12_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_activity ADD CONSTRAINT ck_d12_11 CHECK (valid_to_utc IS NULL OR valid_from_utc<valid_to_utc)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D12_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_activity ADD CONSTRAINT ck_d12_12 CHECK (member_kind=''NORMAL'' OR (version_no=1 AND is_current=1 AND valid_to_utc IS NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D12_13'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_activity ADD CONSTRAINT ck_d12_13 CHECK (member_kind<>''NORMAL'' OR (capacity_per_day>0))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_B' AND table_name='DIM_VEHICLE'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_b.dim_vehicle (
  vehicle_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  member_kind VARCHAR2(64 CHAR) NOT NULL,
  vehicle_id VARCHAR2(128 CHAR),
  centre_id VARCHAR2(128 CHAR),
  vehicle_type VARCHAR2(512 CHAR),
  daily_rate_vnd NUMBER(19,0),
  valid_from_utc TIMESTAMP(6) NOT NULL,
  valid_to_utc TIMESTAMP(6),
  is_current NUMBER(1,0) NOT NULL,
  version_no NUMBER(18,0) NOT NULL,
  effective_time_basis VARCHAR2(64 CHAR) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='PK_D13'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_vehicle ADD CONSTRAINT pk_d13 PRIMARY KEY (vehicle_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UK_D13_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uk_d13_1 ON ce_dwh_b.dim_vehicle (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN vehicle_id END,CASE WHEN member_kind=''NORMAL'' THEN valid_from_utc END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UK_D13_2'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uk_d13_2 ON ce_dwh_b.dim_vehicle (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN vehicle_id END,CASE WHEN member_kind=''NORMAL'' THEN version_no END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UC_D13_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uc_d13_1 ON ce_dwh_b.dim_vehicle (CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN source_system END,CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN vehicle_id END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D13_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_vehicle ADD CONSTRAINT ck_d13_01 CHECK (vehicle_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D13_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_vehicle ADD CONSTRAINT ck_d13_02 CHECK (is_current IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D13_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_vehicle ADD CONSTRAINT ck_d13_03 CHECK (version_no>=0 AND version_no<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D13_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_vehicle ADD CONSTRAINT ck_d13_04 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D13_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_vehicle ADD CONSTRAINT ck_d13_05 CHECK ((member_kind=''NORMAL'' AND vehicle_key>0) OR (member_kind=''UNKNOWN'' AND vehicle_key=0) OR (member_kind=''NOT_APPLICABLE'' AND vehicle_key=-1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D13_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_vehicle ADD CONSTRAINT ck_d13_06 CHECK (member_kind<>''NORMAL'' OR (vehicle_id IS NOT NULL AND centre_id IS NOT NULL AND vehicle_type IS NOT NULL AND daily_rate_vnd IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D13_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_vehicle ADD CONSTRAINT ck_d13_07 CHECK (version_no>=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D13_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_vehicle ADD CONSTRAINT ck_d13_08 CHECK ((is_current=1 AND valid_to_utc IS NULL) OR (is_current=0 AND valid_to_utc IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D13_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_vehicle ADD CONSTRAINT ck_d13_09 CHECK (valid_to_utc IS NULL OR valid_from_utc<valid_to_utc)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D13_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_vehicle ADD CONSTRAINT ck_d13_10 CHECK (member_kind=''NORMAL'' OR (version_no=1 AND is_current=1 AND valid_to_utc IS NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D13_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_vehicle ADD CONSTRAINT ck_d13_11 CHECK (member_kind<>''NORMAL'' OR (daily_rate_vnd>0))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_B' AND table_name='DIM_SUPPLIER'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_b.dim_supplier (
  supplier_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  member_kind VARCHAR2(64 CHAR) NOT NULL,
  supplier_id VARCHAR2(128 CHAR),
  supplier_name VARCHAR2(512 CHAR),
  category VARCHAR2(512 CHAR),
  site_id VARCHAR2(128 CHAR),
  delivery_format VARCHAR2(512 CHAR),
  valid_from_utc TIMESTAMP(6) NOT NULL,
  valid_to_utc TIMESTAMP(6),
  is_current NUMBER(1,0) NOT NULL,
  version_no NUMBER(18,0) NOT NULL,
  effective_time_basis VARCHAR2(64 CHAR) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='PK_D14'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_supplier ADD CONSTRAINT pk_d14 PRIMARY KEY (supplier_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UK_D14_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uk_d14_1 ON ce_dwh_b.dim_supplier (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN supplier_id END,CASE WHEN member_kind=''NORMAL'' THEN valid_from_utc END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UK_D14_2'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uk_d14_2 ON ce_dwh_b.dim_supplier (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN supplier_id END,CASE WHEN member_kind=''NORMAL'' THEN version_no END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UC_D14_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uc_d14_1 ON ce_dwh_b.dim_supplier (CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN source_system END,CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN supplier_id END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D14_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_supplier ADD CONSTRAINT ck_d14_01 CHECK (supplier_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D14_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_supplier ADD CONSTRAINT ck_d14_02 CHECK (is_current IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D14_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_supplier ADD CONSTRAINT ck_d14_03 CHECK (version_no>=0 AND version_no<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D14_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_supplier ADD CONSTRAINT ck_d14_04 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D14_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_supplier ADD CONSTRAINT ck_d14_05 CHECK ((member_kind=''NORMAL'' AND supplier_key>0) OR (member_kind=''UNKNOWN'' AND supplier_key=0) OR (member_kind=''NOT_APPLICABLE'' AND supplier_key=-1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D14_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_supplier ADD CONSTRAINT ck_d14_06 CHECK (member_kind<>''NORMAL'' OR (supplier_id IS NOT NULL AND supplier_name IS NOT NULL AND category IS NOT NULL AND delivery_format IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D14_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_supplier ADD CONSTRAINT ck_d14_07 CHECK (version_no>=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D14_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_supplier ADD CONSTRAINT ck_d14_08 CHECK ((is_current=1 AND valid_to_utc IS NULL) OR (is_current=0 AND valid_to_utc IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D14_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_supplier ADD CONSTRAINT ck_d14_09 CHECK (valid_to_utc IS NULL OR valid_from_utc<valid_to_utc)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D14_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_supplier ADD CONSTRAINT ck_d14_10 CHECK (member_kind=''NORMAL'' OR (version_no=1 AND is_current=1 AND valid_to_utc IS NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_B' AND table_name='DIM_ITEM'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_b.dim_item (
  item_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  member_kind VARCHAR2(64 CHAR) NOT NULL,
  item_id VARCHAR2(128 CHAR),
  item_name VARCHAR2(512 CHAR),
  specification VARCHAR2(512 CHAR),
  base_unit VARCHAR2(512 CHAR),
  shelf_life_days NUMBER(10,0),
  valid_from_utc TIMESTAMP(6) NOT NULL,
  valid_to_utc TIMESTAMP(6),
  is_current NUMBER(1,0) NOT NULL,
  version_no NUMBER(18,0) NOT NULL,
  effective_time_basis VARCHAR2(64 CHAR) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='PK_D15'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_item ADD CONSTRAINT pk_d15 PRIMARY KEY (item_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UK_D15_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uk_d15_1 ON ce_dwh_b.dim_item (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN item_id END,CASE WHEN member_kind=''NORMAL'' THEN valid_from_utc END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UK_D15_2'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uk_d15_2 ON ce_dwh_b.dim_item (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN item_id END,CASE WHEN member_kind=''NORMAL'' THEN version_no END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UC_D15_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uc_d15_1 ON ce_dwh_b.dim_item (CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN source_system END,CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN item_id END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D15_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_item ADD CONSTRAINT ck_d15_01 CHECK (item_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D15_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_item ADD CONSTRAINT ck_d15_02 CHECK (shelf_life_days BETWEEN -2147483648 AND 2147483647)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D15_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_item ADD CONSTRAINT ck_d15_03 CHECK (is_current IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D15_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_item ADD CONSTRAINT ck_d15_04 CHECK (version_no>=0 AND version_no<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D15_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_item ADD CONSTRAINT ck_d15_05 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D15_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_item ADD CONSTRAINT ck_d15_06 CHECK ((member_kind=''NORMAL'' AND item_key>0) OR (member_kind=''UNKNOWN'' AND item_key=0) OR (member_kind=''NOT_APPLICABLE'' AND item_key=-1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D15_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_item ADD CONSTRAINT ck_d15_07 CHECK (member_kind<>''NORMAL'' OR (item_id IS NOT NULL AND item_name IS NOT NULL AND specification IS NOT NULL AND base_unit IS NOT NULL AND shelf_life_days IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D15_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_item ADD CONSTRAINT ck_d15_08 CHECK (version_no>=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D15_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_item ADD CONSTRAINT ck_d15_09 CHECK ((is_current=1 AND valid_to_utc IS NULL) OR (is_current=0 AND valid_to_utc IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D15_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_item ADD CONSTRAINT ck_d15_10 CHECK (valid_to_utc IS NULL OR valid_from_utc<valid_to_utc)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D15_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_item ADD CONSTRAINT ck_d15_11 CHECK (member_kind=''NORMAL'' OR (version_no=1 AND is_current=1 AND valid_to_utc IS NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D15_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_item ADD CONSTRAINT ck_d15_12 CHECK (member_kind<>''NORMAL'' OR (shelf_life_days>=0))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_B' AND table_name='DIM_ASSET'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_b.dim_asset (
  asset_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  member_kind VARCHAR2(64 CHAR) NOT NULL,
  asset_id VARCHAR2(128 CHAR),
  hotel_id VARCHAR2(128 CHAR),
  room_id VARCHAR2(128 CHAR),
  asset_type VARCHAR2(512 CHAR),
  supplier_id VARCHAR2(128 CHAR),
  valid_from_utc TIMESTAMP(6) NOT NULL,
  valid_to_utc TIMESTAMP(6),
  is_current NUMBER(1,0) NOT NULL,
  version_no NUMBER(18,0) NOT NULL,
  effective_time_basis VARCHAR2(64 CHAR) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='PK_D16'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_asset ADD CONSTRAINT pk_d16 PRIMARY KEY (asset_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UK_D16_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uk_d16_1 ON ce_dwh_b.dim_asset (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN asset_id END,CASE WHEN member_kind=''NORMAL'' THEN valid_from_utc END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UK_D16_2'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uk_d16_2 ON ce_dwh_b.dim_asset (CASE WHEN member_kind=''NORMAL'' THEN source_system END,CASE WHEN member_kind=''NORMAL'' THEN asset_id END,CASE WHEN member_kind=''NORMAL'' THEN version_no END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_indexes WHERE owner='CE_DWH_B' AND index_name='UC_D16_1'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE UNIQUE INDEX ce_dwh_b.uc_d16_1 ON ce_dwh_b.dim_asset (CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN source_system END,CASE WHEN member_kind=''NORMAL'' AND is_current=1 THEN asset_id END) TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D16_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_asset ADD CONSTRAINT ck_d16_01 CHECK (asset_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D16_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_asset ADD CONSTRAINT ck_d16_02 CHECK (is_current IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D16_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_asset ADD CONSTRAINT ck_d16_03 CHECK (version_no>=0 AND version_no<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D16_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_asset ADD CONSTRAINT ck_d16_04 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D16_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_asset ADD CONSTRAINT ck_d16_05 CHECK ((member_kind=''NORMAL'' AND asset_key>0) OR (member_kind=''UNKNOWN'' AND asset_key=0) OR (member_kind=''NOT_APPLICABLE'' AND asset_key=-1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D16_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_asset ADD CONSTRAINT ck_d16_06 CHECK (member_kind<>''NORMAL'' OR (asset_id IS NOT NULL AND hotel_id IS NOT NULL AND asset_type IS NOT NULL AND supplier_id IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D16_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_asset ADD CONSTRAINT ck_d16_07 CHECK (version_no>=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D16_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_asset ADD CONSTRAINT ck_d16_08 CHECK ((is_current=1 AND valid_to_utc IS NULL) OR (is_current=0 AND valid_to_utc IS NOT NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D16_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_asset ADD CONSTRAINT ck_d16_09 CHECK (valid_to_utc IS NULL OR valid_from_utc<valid_to_utc)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_D16_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.dim_asset ADD CONSTRAINT ck_d16_10 CHECK (member_kind=''NORMAL'' OR (version_no=1 AND is_current=1 AND valid_to_utc IS NULL))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_B' AND table_name='FACT_BOOKING'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_b.fact_booking (
  fact_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  booked_date_key NUMBER(8,0) NOT NULL,
  arrival_date_key NUMBER(8,0) NOT NULL,
  departure_date_key NUMBER(8,0) NOT NULL,
  site_key NUMBER(18,0) NOT NULL,
  hotel_key NUMBER(18,0) NOT NULL,
  channel_key NUMBER(18,0) NOT NULL,
  promotion_key NUMBER(18,0) NOT NULL,
  customer_profile_key NUMBER(18,0) NOT NULL,
  booking_id VARCHAR2(128 CHAR) NOT NULL,
  status VARCHAR2(512 CHAR) NOT NULL,
  source_updated_at_utc TIMESTAMP(6) NOT NULL,
  gross_vnd NUMBER(19,0) NOT NULL,
  discount_vnd NUMBER(19,0) NOT NULL,
  customer_due_vnd NUMBER(19,0) NOT NULL,
  company_share_vnd NUMBER(19,0) NOT NULL,
  partner_share_vnd NUMBER(19,0) NOT NULL,
  commission_vnd NUMBER(19,0) NOT NULL,
  booking_count NUMBER(18,0) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='PK_F01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_booking ADD CONSTRAINT pk_f01 PRIMARY KEY (fact_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='UK_F01_1'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_booking ADD CONSTRAINT uk_f01_1 UNIQUE (source_system,booking_id) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F01_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_booking ADD CONSTRAINT ck_f01_01 CHECK (fact_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F01_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_booking ADD CONSTRAINT ck_f01_02 CHECK (booked_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F01_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_booking ADD CONSTRAINT ck_f01_03 CHECK (arrival_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F01_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_booking ADD CONSTRAINT ck_f01_04 CHECK (departure_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F01_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_booking ADD CONSTRAINT ck_f01_05 CHECK (site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F01_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_booking ADD CONSTRAINT ck_f01_06 CHECK (hotel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F01_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_booking ADD CONSTRAINT ck_f01_07 CHECK (channel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F01_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_booking ADD CONSTRAINT ck_f01_08 CHECK (promotion_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F01_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_booking ADD CONSTRAINT ck_f01_09 CHECK (customer_profile_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F01_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_booking ADD CONSTRAINT ck_f01_10 CHECK (gross_vnd>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F01_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_booking ADD CONSTRAINT ck_f01_11 CHECK (discount_vnd>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F01_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_booking ADD CONSTRAINT ck_f01_12 CHECK (customer_due_vnd>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F01_13'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_booking ADD CONSTRAINT ck_f01_13 CHECK (company_share_vnd>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F01_14'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_booking ADD CONSTRAINT ck_f01_14 CHECK (partner_share_vnd>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F01_15'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_booking ADD CONSTRAINT ck_f01_15 CHECK (commission_vnd>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F01_16'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_booking ADD CONSTRAINT ck_f01_16 CHECK (booking_count>=0 AND booking_count<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F01_17'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_booking ADD CONSTRAINT ck_f01_17 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F01_18'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_booking ADD CONSTRAINT ck_f01_18 CHECK (fact_key>0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F01_19'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_booking ADD CONSTRAINT ck_f01_19 CHECK (status IN (''COMPLETED'',''CANCELLED'',''NO_SHOW''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F01_20'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_booking ADD CONSTRAINT ck_f01_20 CHECK (arrival_date_key<departure_date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F01_21'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_booking ADD CONSTRAINT ck_f01_21 CHECK (booked_date_key<=arrival_date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F01_22'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_booking ADD CONSTRAINT ck_f01_22 CHECK (discount_vnd=company_share_vnd+partner_share_vnd)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F01_23'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_booking ADD CONSTRAINT ck_f01_23 CHECK (customer_due_vnd=gross_vnd-discount_vnd)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F01_24'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_booking ADD CONSTRAINT ck_f01_24 CHECK (booking_count=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_B' AND table_name='FACT_ROOM_DAY'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_b.fact_room_day (
  fact_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  room_id VARCHAR2(128 CHAR) NOT NULL,
  date_key NUMBER(8,0) NOT NULL,
  site_key NUMBER(18,0) NOT NULL,
  hotel_key NUMBER(18,0) NOT NULL,
  room_key NUMBER(18,0) NOT NULL,
  inventory_day NUMBER(1,0) NOT NULL,
  blocked_day NUMBER(1,0) NOT NULL,
  available_day NUMBER(1,0) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='PK_F02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_room_day ADD CONSTRAINT pk_f02 PRIMARY KEY (fact_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='UK_F02_1'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_room_day ADD CONSTRAINT uk_f02_1 UNIQUE (source_system,room_id,date_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F02_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_room_day ADD CONSTRAINT ck_f02_01 CHECK (fact_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F02_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_room_day ADD CONSTRAINT ck_f02_02 CHECK (date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F02_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_room_day ADD CONSTRAINT ck_f02_03 CHECK (site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F02_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_room_day ADD CONSTRAINT ck_f02_04 CHECK (hotel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F02_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_room_day ADD CONSTRAINT ck_f02_05 CHECK (room_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F02_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_room_day ADD CONSTRAINT ck_f02_06 CHECK (inventory_day IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F02_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_room_day ADD CONSTRAINT ck_f02_07 CHECK (blocked_day IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F02_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_room_day ADD CONSTRAINT ck_f02_08 CHECK (available_day IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F02_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_room_day ADD CONSTRAINT ck_f02_09 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F02_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_room_day ADD CONSTRAINT ck_f02_10 CHECK (fact_key>0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F02_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_room_day ADD CONSTRAINT ck_f02_11 CHECK (inventory_day=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F02_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_room_day ADD CONSTRAINT ck_f02_12 CHECK (available_day=inventory_day-blocked_day)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_B' AND table_name='FACT_STAY_NIGHT'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_b.fact_stay_night (
  fact_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  room_id VARCHAR2(128 CHAR) NOT NULL,
  service_date_key NUMBER(8,0) NOT NULL,
  site_key NUMBER(18,0) NOT NULL,
  hotel_key NUMBER(18,0) NOT NULL,
  room_key NUMBER(18,0) NOT NULL,
  channel_key NUMBER(18,0) NOT NULL,
  customer_profile_key NUMBER(18,0) NOT NULL,
  rate_plan_key NUMBER(18,0) NOT NULL,
  stay_id VARCHAR2(128 CHAR) NOT NULL,
  booking_room_id VARCHAR2(128 CHAR) NOT NULL,
  booking_id VARCHAR2(128 CHAR) NOT NULL,
  occupied_night NUMBER(1,0) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='PK_F03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stay_night ADD CONSTRAINT pk_f03 PRIMARY KEY (fact_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='UK_F03_1'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stay_night ADD CONSTRAINT uk_f03_1 UNIQUE (source_system,room_id,service_date_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F03_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stay_night ADD CONSTRAINT ck_f03_01 CHECK (fact_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F03_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stay_night ADD CONSTRAINT ck_f03_02 CHECK (service_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F03_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stay_night ADD CONSTRAINT ck_f03_03 CHECK (site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F03_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stay_night ADD CONSTRAINT ck_f03_04 CHECK (hotel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F03_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stay_night ADD CONSTRAINT ck_f03_05 CHECK (room_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F03_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stay_night ADD CONSTRAINT ck_f03_06 CHECK (channel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F03_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stay_night ADD CONSTRAINT ck_f03_07 CHECK (customer_profile_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F03_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stay_night ADD CONSTRAINT ck_f03_08 CHECK (rate_plan_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F03_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stay_night ADD CONSTRAINT ck_f03_09 CHECK (occupied_night IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F03_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stay_night ADD CONSTRAINT ck_f03_10 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F03_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stay_night ADD CONSTRAINT ck_f03_11 CHECK (fact_key>0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F03_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stay_night ADD CONSTRAINT ck_f03_12 CHECK (occupied_night=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_B' AND table_name='FACT_TICKET_ORDER'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_b.fact_ticket_order (
  fact_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  ordered_date_key NUMBER(8,0) NOT NULL,
  cohort_departure_date_key NUMBER(8,0) NOT NULL,
  service_site_key NUMBER(18,0) NOT NULL,
  booking_site_key NUMBER(18,0) NOT NULL,
  referral_hotel_key NUMBER(18,0) NOT NULL,
  ticket_channel_key NUMBER(18,0) NOT NULL,
  booking_channel_key NUMBER(18,0) NOT NULL,
  customer_profile_key NUMBER(18,0) NOT NULL,
  centre_key NUMBER(18,0) NOT NULL,
  ticket_order_id VARCHAR2(128 CHAR) NOT NULL,
  hotel_booking_ref VARCHAR2(128 CHAR),
  gross_vnd NUMBER(19,0) NOT NULL,
  refunded_vnd NUMBER(19,0) NOT NULL,
  net_ticket_vnd NUMBER(19,0) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='PK_F04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_ticket_order ADD CONSTRAINT pk_f04 PRIMARY KEY (fact_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='UK_F04_1'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_ticket_order ADD CONSTRAINT uk_f04_1 UNIQUE (source_system,ticket_order_id) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F04_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_ticket_order ADD CONSTRAINT ck_f04_01 CHECK (fact_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F04_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_ticket_order ADD CONSTRAINT ck_f04_02 CHECK (ordered_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F04_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_ticket_order ADD CONSTRAINT ck_f04_03 CHECK (cohort_departure_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F04_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_ticket_order ADD CONSTRAINT ck_f04_04 CHECK (service_site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F04_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_ticket_order ADD CONSTRAINT ck_f04_05 CHECK (booking_site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F04_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_ticket_order ADD CONSTRAINT ck_f04_06 CHECK (referral_hotel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F04_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_ticket_order ADD CONSTRAINT ck_f04_07 CHECK (ticket_channel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F04_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_ticket_order ADD CONSTRAINT ck_f04_08 CHECK (booking_channel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F04_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_ticket_order ADD CONSTRAINT ck_f04_09 CHECK (customer_profile_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F04_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_ticket_order ADD CONSTRAINT ck_f04_10 CHECK (centre_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F04_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_ticket_order ADD CONSTRAINT ck_f04_11 CHECK (gross_vnd>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F04_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_ticket_order ADD CONSTRAINT ck_f04_12 CHECK (refunded_vnd>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F04_13'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_ticket_order ADD CONSTRAINT ck_f04_13 CHECK (net_ticket_vnd>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F04_14'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_ticket_order ADD CONSTRAINT ck_f04_14 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F04_15'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_ticket_order ADD CONSTRAINT ck_f04_15 CHECK (fact_key>0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F04_16'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_ticket_order ADD CONSTRAINT ck_f04_16 CHECK (gross_vnd>=refunded_vnd)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F04_17'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_ticket_order ADD CONSTRAINT ck_f04_17 CHECK (net_ticket_vnd=gross_vnd-refunded_vnd)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_B' AND table_name='FACT_RENTAL'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_b.fact_rental (
  fact_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  pickup_date_key NUMBER(8,0) NOT NULL,
  return_date_key NUMBER(8,0) NOT NULL,
  cohort_departure_date_key NUMBER(8,0) NOT NULL,
  service_site_key NUMBER(18,0) NOT NULL,
  booking_site_key NUMBER(18,0) NOT NULL,
  referral_hotel_key NUMBER(18,0) NOT NULL,
  booking_channel_key NUMBER(18,0) NOT NULL,
  customer_profile_key NUMBER(18,0) NOT NULL,
  centre_key NUMBER(18,0) NOT NULL,
  vehicle_key NUMBER(18,0) NOT NULL,
  rental_id VARCHAR2(128 CHAR) NOT NULL,
  hotel_booking_ref VARCHAR2(128 CHAR),
  status VARCHAR2(512 CHAR) NOT NULL,
  agreed_vnd NUMBER(19,0) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='PK_F05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_rental ADD CONSTRAINT pk_f05 PRIMARY KEY (fact_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='UK_F05_1'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_rental ADD CONSTRAINT uk_f05_1 UNIQUE (source_system,rental_id) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F05_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_rental ADD CONSTRAINT ck_f05_01 CHECK (fact_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F05_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_rental ADD CONSTRAINT ck_f05_02 CHECK (pickup_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F05_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_rental ADD CONSTRAINT ck_f05_03 CHECK (return_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F05_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_rental ADD CONSTRAINT ck_f05_04 CHECK (cohort_departure_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F05_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_rental ADD CONSTRAINT ck_f05_05 CHECK (service_site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F05_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_rental ADD CONSTRAINT ck_f05_06 CHECK (booking_site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F05_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_rental ADD CONSTRAINT ck_f05_07 CHECK (referral_hotel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F05_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_rental ADD CONSTRAINT ck_f05_08 CHECK (booking_channel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F05_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_rental ADD CONSTRAINT ck_f05_09 CHECK (customer_profile_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F05_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_rental ADD CONSTRAINT ck_f05_10 CHECK (centre_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F05_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_rental ADD CONSTRAINT ck_f05_11 CHECK (vehicle_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F05_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_rental ADD CONSTRAINT ck_f05_12 CHECK (agreed_vnd>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F05_13'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_rental ADD CONSTRAINT ck_f05_13 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F05_14'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_rental ADD CONSTRAINT ck_f05_14 CHECK (fact_key>0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F05_15'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_rental ADD CONSTRAINT ck_f05_15 CHECK (status IN (''COMPLETED'',''CANCELLED''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F05_16'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_rental ADD CONSTRAINT ck_f05_16 CHECK (pickup_date_key<return_date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_B' AND table_name='FACT_BREAKFAST_ENTITLEMENT'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_b.fact_breakfast_entitlement (
  fact_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  service_date_key NUMBER(8,0) NOT NULL,
  site_key NUMBER(18,0) NOT NULL,
  hotel_key NUMBER(18,0) NOT NULL,
  room_key NUMBER(18,0) NOT NULL,
  customer_profile_key NUMBER(18,0) NOT NULL,
  rate_plan_key NUMBER(18,0) NOT NULL,
  outlet_key NUMBER(18,0) NOT NULL,
  meal_key NUMBER(18,0) NOT NULL,
  entitlement_id VARCHAR2(128 CHAR) NOT NULL,
  booking_room_id VARCHAR2(128 CHAR) NOT NULL,
  eligible_covers NUMBER(18,0) NOT NULL,
  redeemed_covers NUMBER(18,0) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='PK_F06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_breakfast_entitlement ADD CONSTRAINT pk_f06 PRIMARY KEY (fact_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='UK_F06_1'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_breakfast_entitlement ADD CONSTRAINT uk_f06_1 UNIQUE (source_system,entitlement_id) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='UK_F06_2'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_breakfast_entitlement ADD CONSTRAINT uk_f06_2 UNIQUE (source_system,booking_room_id,service_date_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F06_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_breakfast_entitlement ADD CONSTRAINT ck_f06_01 CHECK (fact_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F06_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_breakfast_entitlement ADD CONSTRAINT ck_f06_02 CHECK (service_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F06_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_breakfast_entitlement ADD CONSTRAINT ck_f06_03 CHECK (site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F06_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_breakfast_entitlement ADD CONSTRAINT ck_f06_04 CHECK (hotel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F06_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_breakfast_entitlement ADD CONSTRAINT ck_f06_05 CHECK (room_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F06_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_breakfast_entitlement ADD CONSTRAINT ck_f06_06 CHECK (customer_profile_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F06_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_breakfast_entitlement ADD CONSTRAINT ck_f06_07 CHECK (rate_plan_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F06_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_breakfast_entitlement ADD CONSTRAINT ck_f06_08 CHECK (outlet_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F06_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_breakfast_entitlement ADD CONSTRAINT ck_f06_09 CHECK (meal_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F06_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_breakfast_entitlement ADD CONSTRAINT ck_f06_10 CHECK (eligible_covers>=0 AND eligible_covers<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F06_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_breakfast_entitlement ADD CONSTRAINT ck_f06_11 CHECK (redeemed_covers>=0 AND redeemed_covers<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F06_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_breakfast_entitlement ADD CONSTRAINT ck_f06_12 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F06_13'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_breakfast_entitlement ADD CONSTRAINT ck_f06_13 CHECK (fact_key>0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F06_14'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_breakfast_entitlement ADD CONSTRAINT ck_f06_14 CHECK (eligible_covers>=redeemed_covers)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F06_15'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_breakfast_entitlement ADD CONSTRAINT ck_f06_15 CHECK (meal_key=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_B' AND table_name='FACT_DINING_ORDER'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_b.fact_dining_order (
  fact_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  service_date_key NUMBER(8,0) NOT NULL,
  site_key NUMBER(18,0) NOT NULL,
  service_hotel_key NUMBER(18,0) NOT NULL,
  booking_hotel_key NUMBER(18,0) NOT NULL,
  customer_profile_key NUMBER(18,0) NOT NULL,
  outlet_key NUMBER(18,0) NOT NULL,
  meal_key NUMBER(18,0) NOT NULL,
  dining_order_id VARCHAR2(128 CHAR) NOT NULL,
  booking_id VARCHAR2(128 CHAR),
  net_vnd NUMBER(19,0) NOT NULL,
  covers NUMBER(18,0) NOT NULL,
  rating_sum NUMBER(18,0) NOT NULL,
  rating_count NUMBER(18,0) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='PK_F07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_dining_order ADD CONSTRAINT pk_f07 PRIMARY KEY (fact_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='UK_F07_1'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_dining_order ADD CONSTRAINT uk_f07_1 UNIQUE (source_system,dining_order_id) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F07_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_dining_order ADD CONSTRAINT ck_f07_01 CHECK (fact_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F07_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_dining_order ADD CONSTRAINT ck_f07_02 CHECK (service_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F07_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_dining_order ADD CONSTRAINT ck_f07_03 CHECK (site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F07_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_dining_order ADD CONSTRAINT ck_f07_04 CHECK (service_hotel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F07_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_dining_order ADD CONSTRAINT ck_f07_05 CHECK (booking_hotel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F07_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_dining_order ADD CONSTRAINT ck_f07_06 CHECK (customer_profile_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F07_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_dining_order ADD CONSTRAINT ck_f07_07 CHECK (outlet_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F07_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_dining_order ADD CONSTRAINT ck_f07_08 CHECK (meal_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F07_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_dining_order ADD CONSTRAINT ck_f07_09 CHECK (net_vnd>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F07_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_dining_order ADD CONSTRAINT ck_f07_10 CHECK (covers>=0 AND covers<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F07_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_dining_order ADD CONSTRAINT ck_f07_11 CHECK (rating_sum>=0 AND rating_sum<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F07_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_dining_order ADD CONSTRAINT ck_f07_12 CHECK (rating_count>=0 AND rating_count<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F07_13'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_dining_order ADD CONSTRAINT ck_f07_13 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F07_14'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_dining_order ADD CONSTRAINT ck_f07_14 CHECK (fact_key>0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F07_15'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_dining_order ADD CONSTRAINT ck_f07_15 CHECK (rating_sum BETWEEN 1 AND 5)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F07_16'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_dining_order ADD CONSTRAINT ck_f07_16 CHECK (rating_count=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_B' AND table_name='FACT_MEAL_SESSION'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_b.fact_meal_session (
  fact_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  outlet_id VARCHAR2(128 CHAR) NOT NULL,
  service_date_key NUMBER(8,0) NOT NULL,
  site_key NUMBER(18,0) NOT NULL,
  hotel_key NUMBER(18,0) NOT NULL,
  outlet_key NUMBER(18,0) NOT NULL,
  meal_key NUMBER(18,0) NOT NULL,
  session_id VARCHAR2(128 CHAR) NOT NULL,
  actual_covers NUMBER(18,0) NOT NULL,
  ingredient_cost_vnd NUMBER(19,0) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='PK_F08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_meal_session ADD CONSTRAINT pk_f08 PRIMARY KEY (fact_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='UK_F08_1'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_meal_session ADD CONSTRAINT uk_f08_1 UNIQUE (source_system,outlet_id,service_date_key,meal_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='UK_F08_2'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_meal_session ADD CONSTRAINT uk_f08_2 UNIQUE (source_system,session_id) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F08_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_meal_session ADD CONSTRAINT ck_f08_01 CHECK (fact_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F08_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_meal_session ADD CONSTRAINT ck_f08_02 CHECK (service_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F08_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_meal_session ADD CONSTRAINT ck_f08_03 CHECK (site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F08_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_meal_session ADD CONSTRAINT ck_f08_04 CHECK (hotel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F08_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_meal_session ADD CONSTRAINT ck_f08_05 CHECK (outlet_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F08_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_meal_session ADD CONSTRAINT ck_f08_06 CHECK (meal_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F08_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_meal_session ADD CONSTRAINT ck_f08_07 CHECK (actual_covers>=0 AND actual_covers<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F08_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_meal_session ADD CONSTRAINT ck_f08_08 CHECK (ingredient_cost_vnd>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F08_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_meal_session ADD CONSTRAINT ck_f08_09 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F08_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_meal_session ADD CONSTRAINT ck_f08_10 CHECK (fact_key>0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F08_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_meal_session ADD CONSTRAINT ck_f08_11 CHECK (meal_key IN (1,3))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_B' AND table_name='FACT_ADMISSION'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_b.fact_admission (
  fact_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  admission_date_key NUMBER(8,0) NOT NULL,
  site_key NUMBER(18,0) NOT NULL,
  customer_profile_key NUMBER(18,0) NOT NULL,
  centre_key NUMBER(18,0) NOT NULL,
  activity_key NUMBER(18,0) NOT NULL,
  admission_id VARCHAR2(128 CHAR) NOT NULL,
  ticket_id VARCHAR2(128 CHAR) NOT NULL,
  entered_at_utc TIMESTAMP(6) NOT NULL,
  admission_count NUMBER(18,0) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='PK_F09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_admission ADD CONSTRAINT pk_f09 PRIMARY KEY (fact_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='UK_F09_1'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_admission ADD CONSTRAINT uk_f09_1 UNIQUE (source_system,admission_id) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F09_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_admission ADD CONSTRAINT ck_f09_01 CHECK (fact_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F09_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_admission ADD CONSTRAINT ck_f09_02 CHECK (admission_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F09_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_admission ADD CONSTRAINT ck_f09_03 CHECK (site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F09_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_admission ADD CONSTRAINT ck_f09_04 CHECK (customer_profile_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F09_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_admission ADD CONSTRAINT ck_f09_05 CHECK (centre_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F09_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_admission ADD CONSTRAINT ck_f09_06 CHECK (activity_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F09_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_admission ADD CONSTRAINT ck_f09_07 CHECK (admission_count>=0 AND admission_count<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F09_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_admission ADD CONSTRAINT ck_f09_08 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F09_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_admission ADD CONSTRAINT ck_f09_09 CHECK (fact_key>0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F09_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_admission ADD CONSTRAINT ck_f09_10 CHECK (admission_count=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_B' AND table_name='FACT_ACTIVITY_DAY'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_b.fact_activity_day (
  fact_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  activity_id VARCHAR2(128 CHAR) NOT NULL,
  date_key NUMBER(8,0) NOT NULL,
  site_key NUMBER(18,0) NOT NULL,
  centre_key NUMBER(18,0) NOT NULL,
  activity_key NUMBER(18,0) NOT NULL,
  nominal_capacity NUMBER(18,0) NOT NULL,
  is_closed NUMBER(1,0) NOT NULL,
  available_capacity NUMBER(18,0) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='PK_F10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_activity_day ADD CONSTRAINT pk_f10 PRIMARY KEY (fact_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='UK_F10_1'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_activity_day ADD CONSTRAINT uk_f10_1 UNIQUE (source_system,activity_id,date_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F10_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_activity_day ADD CONSTRAINT ck_f10_01 CHECK (fact_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F10_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_activity_day ADD CONSTRAINT ck_f10_02 CHECK (date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F10_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_activity_day ADD CONSTRAINT ck_f10_03 CHECK (site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F10_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_activity_day ADD CONSTRAINT ck_f10_04 CHECK (centre_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F10_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_activity_day ADD CONSTRAINT ck_f10_05 CHECK (activity_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F10_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_activity_day ADD CONSTRAINT ck_f10_06 CHECK (nominal_capacity>=0 AND nominal_capacity<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F10_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_activity_day ADD CONSTRAINT ck_f10_07 CHECK (is_closed IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F10_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_activity_day ADD CONSTRAINT ck_f10_08 CHECK (available_capacity>=0 AND available_capacity<=999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F10_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_activity_day ADD CONSTRAINT ck_f10_09 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F10_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_activity_day ADD CONSTRAINT ck_f10_10 CHECK (fact_key>0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F10_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_activity_day ADD CONSTRAINT ck_f10_11 CHECK (nominal_capacity>0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F10_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_activity_day ADD CONSTRAINT ck_f10_12 CHECK (available_capacity=nominal_capacity*(1-is_closed))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_B' AND table_name='FACT_VEHICLE_DAY'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_b.fact_vehicle_day (
  fact_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  vehicle_id VARCHAR2(128 CHAR) NOT NULL,
  date_key NUMBER(8,0) NOT NULL,
  site_key NUMBER(18,0) NOT NULL,
  centre_key NUMBER(18,0) NOT NULL,
  vehicle_key NUMBER(18,0) NOT NULL,
  inventory_day NUMBER(1,0) NOT NULL,
  maintenance_day NUMBER(1,0) NOT NULL,
  available_day NUMBER(1,0) NOT NULL,
  rented_day NUMBER(1,0) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='PK_F11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_vehicle_day ADD CONSTRAINT pk_f11 PRIMARY KEY (fact_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='UK_F11_1'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_vehicle_day ADD CONSTRAINT uk_f11_1 UNIQUE (source_system,vehicle_id,date_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F11_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_vehicle_day ADD CONSTRAINT ck_f11_01 CHECK (fact_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F11_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_vehicle_day ADD CONSTRAINT ck_f11_02 CHECK (date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F11_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_vehicle_day ADD CONSTRAINT ck_f11_03 CHECK (site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F11_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_vehicle_day ADD CONSTRAINT ck_f11_04 CHECK (centre_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F11_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_vehicle_day ADD CONSTRAINT ck_f11_05 CHECK (vehicle_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F11_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_vehicle_day ADD CONSTRAINT ck_f11_06 CHECK (inventory_day IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F11_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_vehicle_day ADD CONSTRAINT ck_f11_07 CHECK (maintenance_day IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F11_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_vehicle_day ADD CONSTRAINT ck_f11_08 CHECK (available_day IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F11_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_vehicle_day ADD CONSTRAINT ck_f11_09 CHECK (rented_day IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F11_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_vehicle_day ADD CONSTRAINT ck_f11_10 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F11_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_vehicle_day ADD CONSTRAINT ck_f11_11 CHECK (fact_key>0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F11_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_vehicle_day ADD CONSTRAINT ck_f11_12 CHECK (inventory_day=1)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F11_13'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_vehicle_day ADD CONSTRAINT ck_f11_13 CHECK (available_day=1-maintenance_day)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F11_14'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_vehicle_day ADD CONSTRAINT ck_f11_14 CHECK (rented_day<=available_day)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_B' AND table_name='FACT_PURCHASE_LINE'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_b.fact_purchase_line (
  fact_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  ordered_date_key NUMBER(8,0) NOT NULL,
  expected_date_key NUMBER(8,0) NOT NULL,
  site_key NUMBER(18,0) NOT NULL,
  hotel_key NUMBER(18,0) NOT NULL,
  supplier_key NUMBER(18,0) NOT NULL,
  item_key NUMBER(18,0) NOT NULL,
  purchase_line_id VARCHAR2(128 CHAR) NOT NULL,
  purchase_order_id VARCHAR2(128 CHAR) NOT NULL,
  ordered_qty NUMBER(18,3) NOT NULL,
  unit_price_vnd NUMBER(19,0) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='PK_F12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_purchase_line ADD CONSTRAINT pk_f12 PRIMARY KEY (fact_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='UK_F12_1'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_purchase_line ADD CONSTRAINT uk_f12_1 UNIQUE (source_system,purchase_line_id) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F12_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_purchase_line ADD CONSTRAINT ck_f12_01 CHECK (fact_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F12_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_purchase_line ADD CONSTRAINT ck_f12_02 CHECK (ordered_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F12_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_purchase_line ADD CONSTRAINT ck_f12_03 CHECK (expected_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F12_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_purchase_line ADD CONSTRAINT ck_f12_04 CHECK (site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F12_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_purchase_line ADD CONSTRAINT ck_f12_05 CHECK (hotel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F12_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_purchase_line ADD CONSTRAINT ck_f12_06 CHECK (supplier_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F12_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_purchase_line ADD CONSTRAINT ck_f12_07 CHECK (item_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F12_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_purchase_line ADD CONSTRAINT ck_f12_08 CHECK (unit_price_vnd>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F12_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_purchase_line ADD CONSTRAINT ck_f12_09 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F12_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_purchase_line ADD CONSTRAINT ck_f12_10 CHECK (fact_key>0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F12_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_purchase_line ADD CONSTRAINT ck_f12_11 CHECK (ordered_qty>0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F12_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_purchase_line ADD CONSTRAINT ck_f12_12 CHECK (unit_price_vnd>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F12_13'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_purchase_line ADD CONSTRAINT ck_f12_13 CHECK (ordered_date_key<=expected_date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_B' AND table_name='FACT_RECEIPT'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_b.fact_receipt (
  fact_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  received_date_key NUMBER(8,0) NOT NULL,
  expected_date_key NUMBER(8,0) NOT NULL,
  expires_date_key NUMBER(8,0) NOT NULL,
  site_key NUMBER(18,0) NOT NULL,
  hotel_key NUMBER(18,0) NOT NULL,
  supplier_key NUMBER(18,0) NOT NULL,
  item_key NUMBER(18,0) NOT NULL,
  receipt_id VARCHAR2(128 CHAR) NOT NULL,
  purchase_line_id VARCHAR2(128 CHAR) NOT NULL,
  accepted_qty NUMBER(18,3) NOT NULL,
  rejected_qty NUMBER(18,3) NOT NULL,
  late_accepted_qty NUMBER(18,3) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='PK_F13'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_receipt ADD CONSTRAINT pk_f13 PRIMARY KEY (fact_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='UK_F13_1'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_receipt ADD CONSTRAINT uk_f13_1 UNIQUE (source_system,receipt_id) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F13_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_receipt ADD CONSTRAINT ck_f13_01 CHECK (fact_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F13_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_receipt ADD CONSTRAINT ck_f13_02 CHECK (received_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F13_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_receipt ADD CONSTRAINT ck_f13_03 CHECK (expected_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F13_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_receipt ADD CONSTRAINT ck_f13_04 CHECK (expires_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F13_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_receipt ADD CONSTRAINT ck_f13_05 CHECK (site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F13_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_receipt ADD CONSTRAINT ck_f13_06 CHECK (hotel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F13_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_receipt ADD CONSTRAINT ck_f13_07 CHECK (supplier_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F13_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_receipt ADD CONSTRAINT ck_f13_08 CHECK (item_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F13_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_receipt ADD CONSTRAINT ck_f13_09 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F13_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_receipt ADD CONSTRAINT ck_f13_10 CHECK (fact_key>0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F13_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_receipt ADD CONSTRAINT ck_f13_11 CHECK (accepted_qty>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F13_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_receipt ADD CONSTRAINT ck_f13_12 CHECK (rejected_qty>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F13_13'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_receipt ADD CONSTRAINT ck_f13_13 CHECK (late_accepted_qty IN (0,accepted_qty))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_B' AND table_name='FACT_STOCK_MOVEMENT'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_b.fact_stock_movement (
  fact_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  movement_date_key NUMBER(8,0) NOT NULL,
  site_key NUMBER(18,0) NOT NULL,
  hotel_key NUMBER(18,0) NOT NULL,
  supplier_key NUMBER(18,0) NOT NULL,
  item_key NUMBER(18,0) NOT NULL,
  movement_id VARCHAR2(128 CHAR) NOT NULL,
  receipt_id VARCHAR2(128 CHAR) NOT NULL,
  session_id VARCHAR2(128 CHAR),
  movement_type VARCHAR2(512 CHAR) NOT NULL,
  usage_area VARCHAR2(512 CHAR) NOT NULL,
  quantity NUMBER(18,3) NOT NULL,
  signed_qty NUMBER(18,3) NOT NULL,
  in_qty NUMBER(18,3) NOT NULL,
  use_qty NUMBER(18,3) NOT NULL,
  waste_qty NUMBER(18,3) NOT NULL,
  unit_price_vnd NUMBER(19,0) NOT NULL,
  movement_value_vnd NUMBER(38,3) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='PK_F14'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stock_movement ADD CONSTRAINT pk_f14 PRIMARY KEY (fact_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='UK_F14_1'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stock_movement ADD CONSTRAINT uk_f14_1 UNIQUE (source_system,movement_id) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F14_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stock_movement ADD CONSTRAINT ck_f14_01 CHECK (fact_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F14_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stock_movement ADD CONSTRAINT ck_f14_02 CHECK (movement_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F14_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stock_movement ADD CONSTRAINT ck_f14_03 CHECK (site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F14_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stock_movement ADD CONSTRAINT ck_f14_04 CHECK (hotel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F14_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stock_movement ADD CONSTRAINT ck_f14_05 CHECK (supplier_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F14_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stock_movement ADD CONSTRAINT ck_f14_06 CHECK (item_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F14_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stock_movement ADD CONSTRAINT ck_f14_07 CHECK (unit_price_vnd>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F14_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stock_movement ADD CONSTRAINT ck_f14_08 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F14_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stock_movement ADD CONSTRAINT ck_f14_09 CHECK (fact_key>0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F14_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stock_movement ADD CONSTRAINT ck_f14_10 CHECK (movement_type IN (''IN'',''USE'',''WASTE''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F14_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stock_movement ADD CONSTRAINT ck_f14_11 CHECK (quantity>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F14_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stock_movement ADD CONSTRAINT ck_f14_12 CHECK (in_qty>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F14_13'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stock_movement ADD CONSTRAINT ck_f14_13 CHECK (use_qty>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F14_14'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stock_movement ADD CONSTRAINT ck_f14_14 CHECK (waste_qty>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F14_15'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stock_movement ADD CONSTRAINT ck_f14_15 CHECK (signed_qty=in_qty-use_qty-waste_qty)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_B' AND table_name='AGG_INVENTORY_LOT_DAY'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_b.agg_inventory_lot_day (
  fact_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  hotel_id VARCHAR2(128 CHAR) NOT NULL,
  item_id VARCHAR2(128 CHAR) NOT NULL,
  snapshot_date_key NUMBER(8,0) NOT NULL,
  site_key NUMBER(18,0) NOT NULL,
  hotel_key NUMBER(18,0) NOT NULL,
  supplier_key NUMBER(18,0) NOT NULL,
  item_key NUMBER(18,0) NOT NULL,
  receipt_id VARCHAR2(128 CHAR) NOT NULL,
  closing_qty NUMBER(18,3) NOT NULL,
  closing_value_vnd NUMBER(38,3) NOT NULL,
  in_qty NUMBER(18,3) NOT NULL,
  use_qty NUMBER(18,3) NOT NULL,
  waste_qty NUMBER(18,3) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='PK_F15'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.agg_inventory_lot_day ADD CONSTRAINT pk_f15 PRIMARY KEY (fact_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='UK_F15_1'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.agg_inventory_lot_day ADD CONSTRAINT uk_f15_1 UNIQUE (source_system,receipt_id,hotel_id,item_id,snapshot_date_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F15_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.agg_inventory_lot_day ADD CONSTRAINT ck_f15_01 CHECK (fact_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F15_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.agg_inventory_lot_day ADD CONSTRAINT ck_f15_02 CHECK (snapshot_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F15_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.agg_inventory_lot_day ADD CONSTRAINT ck_f15_03 CHECK (site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F15_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.agg_inventory_lot_day ADD CONSTRAINT ck_f15_04 CHECK (hotel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F15_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.agg_inventory_lot_day ADD CONSTRAINT ck_f15_05 CHECK (supplier_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F15_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.agg_inventory_lot_day ADD CONSTRAINT ck_f15_06 CHECK (item_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F15_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.agg_inventory_lot_day ADD CONSTRAINT ck_f15_07 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F15_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.agg_inventory_lot_day ADD CONSTRAINT ck_f15_08 CHECK (fact_key>0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F15_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.agg_inventory_lot_day ADD CONSTRAINT ck_f15_09 CHECK (closing_qty>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F15_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.agg_inventory_lot_day ADD CONSTRAINT ck_f15_10 CHECK (in_qty>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F15_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.agg_inventory_lot_day ADD CONSTRAINT ck_f15_11 CHECK (use_qty>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F15_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.agg_inventory_lot_day ADD CONSTRAINT ck_f15_12 CHECK (waste_qty>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_B' AND table_name='FACT_MAINTENANCE_WORK'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_b.fact_maintenance_work (
  fact_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  start_date_key NUMBER(8,0) NOT NULL,
  end_date_key NUMBER(8,0) NOT NULL,
  site_key NUMBER(18,0) NOT NULL,
  hotel_key NUMBER(18,0) NOT NULL,
  room_key NUMBER(18,0) NOT NULL,
  asset_key NUMBER(18,0) NOT NULL,
  maintenance_id VARCHAR2(128 CHAR) NOT NULL,
  work_type VARCHAR2(512 CHAR) NOT NULL,
  status VARCHAR2(512 CHAR) NOT NULL,
  cost_vnd NUMBER(19,0) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='PK_F16'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_maintenance_work ADD CONSTRAINT pk_f16 PRIMARY KEY (fact_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='UK_F16_1'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_maintenance_work ADD CONSTRAINT uk_f16_1 UNIQUE (source_system,maintenance_id) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F16_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_maintenance_work ADD CONSTRAINT ck_f16_01 CHECK (fact_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F16_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_maintenance_work ADD CONSTRAINT ck_f16_02 CHECK (start_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F16_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_maintenance_work ADD CONSTRAINT ck_f16_03 CHECK (end_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F16_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_maintenance_work ADD CONSTRAINT ck_f16_04 CHECK (site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F16_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_maintenance_work ADD CONSTRAINT ck_f16_05 CHECK (hotel_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F16_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_maintenance_work ADD CONSTRAINT ck_f16_06 CHECK (room_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F16_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_maintenance_work ADD CONSTRAINT ck_f16_07 CHECK (asset_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F16_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_maintenance_work ADD CONSTRAINT ck_f16_08 CHECK (cost_vnd>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F16_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_maintenance_work ADD CONSTRAINT ck_f16_09 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F16_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_maintenance_work ADD CONSTRAINT ck_f16_10 CHECK (fact_key>0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F16_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_maintenance_work ADD CONSTRAINT ck_f16_11 CHECK (start_date_key<end_date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F16_12'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_maintenance_work ADD CONSTRAINT ck_f16_12 CHECK (work_type IN (''BREAKDOWN'',''PLANNED''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F16_13'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_maintenance_work ADD CONSTRAINT ck_f16_13 CHECK (status=''COMPLETED'')'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_B' AND table_name='FACT_WEATHER_DAY'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_b.fact_weather_day (
  fact_key NUMBER(18,0) NOT NULL,
  source_system VARCHAR2(64 CHAR) NOT NULL,
  site_id VARCHAR2(128 CHAR) NOT NULL,
  weather_date_key NUMBER(8,0) NOT NULL,
  site_key NUMBER(18,0) NOT NULL,
  weather_id VARCHAR2(128 CHAR) NOT NULL,
  provenance VARCHAR2(512 CHAR) NOT NULL,
  temperature_c NUMBER(10,0) NOT NULL,
  rain_mm NUMBER(10,0) NOT NULL,
  severe_weather NUMBER(1,0) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='PK_F17'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_weather_day ADD CONSTRAINT pk_f17 PRIMARY KEY (fact_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='UK_F17_1'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_weather_day ADD CONSTRAINT uk_f17_1 UNIQUE (source_system,site_id,weather_date_key) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='UK_F17_2'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_weather_day ADD CONSTRAINT uk_f17_2 UNIQUE (source_system,weather_id) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F17_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_weather_day ADD CONSTRAINT ck_f17_01 CHECK (fact_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F17_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_weather_day ADD CONSTRAINT ck_f17_02 CHECK (weather_date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F17_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_weather_day ADD CONSTRAINT ck_f17_03 CHECK (site_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F17_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_weather_day ADD CONSTRAINT ck_f17_04 CHECK (temperature_c BETWEEN -2147483648 AND 2147483647)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F17_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_weather_day ADD CONSTRAINT ck_f17_05 CHECK (rain_mm BETWEEN -2147483648 AND 2147483647)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F17_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_weather_day ADD CONSTRAINT ck_f17_06 CHECK (severe_weather IN (0,1))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F17_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_weather_day ADD CONSTRAINT ck_f17_07 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F17_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_weather_day ADD CONSTRAINT ck_f17_08 CHECK (fact_key>0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_F17_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_weather_day ADD CONSTRAINT ck_f17_09 CHECK (rain_mm>=0)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_B' AND table_name='BRIDGE_BOOKING_ROOM'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_b.bridge_booking_room (
  source_system VARCHAR2(64 CHAR) NOT NULL,
  booking_room_id VARCHAR2(128 CHAR) NOT NULL,
  booking_id VARCHAR2(128 CHAR) NOT NULL,
  room_key NUMBER(18,0) NOT NULL,
  rate_plan_key NUMBER(18,0) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='PK_L01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.bridge_booking_room ADD CONSTRAINT pk_l01 PRIMARY KEY (source_system,booking_room_id) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_L01_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.bridge_booking_room ADD CONSTRAINT ck_l01_01 CHECK (room_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_L01_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.bridge_booking_room ADD CONSTRAINT ck_l01_02 CHECK (rate_plan_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_L01_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.bridge_booking_room ADD CONSTRAINT ck_l01_03 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_DWH_B' AND table_name='BRIDGE_ROOM_DAY_MAINTENANCE'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_dwh_b.bridge_room_day_maintenance (
  source_system VARCHAR2(64 CHAR) NOT NULL,
  maintenance_id VARCHAR2(128 CHAR) NOT NULL,
  room_id VARCHAR2(128 CHAR) NOT NULL,
  room_key NUMBER(18,0) NOT NULL,
  date_key NUMBER(8,0) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='PK_L02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.bridge_room_day_maintenance ADD CONSTRAINT pk_l02 PRIMARY KEY (source_system,room_id,date_key,maintenance_id) USING INDEX TABLESPACE ce_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_L02_01'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.bridge_room_day_maintenance ADD CONSTRAINT ck_l02_01 CHECK (room_key BETWEEN -1 AND 999999999999999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_L02_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.bridge_room_day_maintenance ADD CONSTRAINT ck_l02_02 CHECK (date_key BETWEEN -1 AND 99999999)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='CK_L02_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.bridge_room_day_maintenance ADD CONSTRAINT ck_l02_03 CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_STAGE' AND table_name='VALIDATED_BOOKING_SERVICE_LINK_INPUT_B'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_stage.validated_booking_service_link_input_b (
  service_source_system VARCHAR2(64 CHAR) NOT NULL,
  service_type VARCHAR2(64 CHAR) NOT NULL,
  service_id VARCHAR2(128 CHAR) NOT NULL,
  booking_source_system VARCHAR2(64 CHAR) NOT NULL,
  booking_id VARCHAR2(128 CHAR) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_stage_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_STAGE' AND constraint_name='PK_L03_B'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_stage.validated_booking_service_link_input_b ADD CONSTRAINT pk_l03_b PRIMARY KEY (service_source_system,service_type,service_id) USING INDEX TABLESPACE ce_stage_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_STAGE' AND constraint_name='CK_L03_01_B'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_stage.validated_booking_service_link_input_b ADD CONSTRAINT ck_l03_01_b CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

GRANT SELECT ON ce_stage.validated_booking_service_link_input_b TO ce_dwh_b;

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_views WHERE owner='CE_DWH_B' AND view_name='VALIDATED_BOOKING_SERVICE_LINK'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE VIEW ce_dwh_b.validated_booking_service_link AS SELECT service_source_system,service_type,service_id,booking_source_system,booking_id,source_batch_id,transform_version,row_hash,created_at_utc,updated_at_utc FROM ce_stage.validated_booking_service_link_input_b'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_tables WHERE owner='CE_STAGE' AND table_name='SITE_CROSSWALK_INPUT_B'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE TABLE ce_stage.site_crosswalk_input_b (
  centre_source_system VARCHAR2(64 CHAR) NOT NULL,
  centre_id VARCHAR2(128 CHAR) NOT NULL,
  site_source_system VARCHAR2(64 CHAR) NOT NULL,
  site_id VARCHAR2(128 CHAR) NOT NULL,
  source_batch_id VARCHAR2(128 CHAR) NOT NULL,
  transform_version VARCHAR2(64 CHAR) NOT NULL,
  row_hash VARCHAR2(64 CHAR) NOT NULL,
  created_at_utc TIMESTAMP(6) NOT NULL,
  updated_at_utc TIMESTAMP(6) NOT NULL
) TABLESPACE ce_stage_data NOCOMPRESS NOPARALLEL'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_STAGE' AND constraint_name='PK_L04_B'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_stage.site_crosswalk_input_b ADD CONSTRAINT pk_l04_b PRIMARY KEY (centre_source_system,centre_id) USING INDEX TABLESPACE ce_stage_data'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_STAGE' AND constraint_name='CK_L04_01_B'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_stage.site_crosswalk_input_b ADD CONSTRAINT ck_l04_01_b CHECK (REGEXP_LIKE(row_hash, ''^[0-9a-f]{64}$'', ''c''))'; END IF; END;
/

GRANT SELECT ON ce_stage.site_crosswalk_input_b TO ce_dwh_b;

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_views WHERE owner='CE_DWH_B' AND view_name='SITE_CROSSWALK'; IF n=0 THEN EXECUTE IMMEDIATE 'CREATE VIEW ce_dwh_b.site_crosswalk AS SELECT centre_source_system,centre_id,site_source_system,site_id,source_batch_id,transform_version,row_hash,created_at_utc,updated_at_utc FROM ce_stage.site_crosswalk_input_b'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F01_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_booking ADD CONSTRAINT fk_f01_02 FOREIGN KEY (booked_date_key) REFERENCES ce_dwh_b.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F01_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_booking ADD CONSTRAINT fk_f01_03 FOREIGN KEY (arrival_date_key) REFERENCES ce_dwh_b.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F01_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_booking ADD CONSTRAINT fk_f01_04 FOREIGN KEY (departure_date_key) REFERENCES ce_dwh_b.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F01_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_booking ADD CONSTRAINT fk_f01_05 FOREIGN KEY (site_key) REFERENCES ce_dwh_b.dim_site (site_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F01_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_booking ADD CONSTRAINT fk_f01_06 FOREIGN KEY (hotel_key) REFERENCES ce_dwh_b.dim_hotel (hotel_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F01_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_booking ADD CONSTRAINT fk_f01_07 FOREIGN KEY (channel_key) REFERENCES ce_dwh_b.dim_channel (channel_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F01_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_booking ADD CONSTRAINT fk_f01_08 FOREIGN KEY (promotion_key) REFERENCES ce_dwh_b.dim_promotion (promotion_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F01_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_booking ADD CONSTRAINT fk_f01_09 FOREIGN KEY (customer_profile_key) REFERENCES ce_dwh_b.dim_customer_profile (customer_profile_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F02_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_room_day ADD CONSTRAINT fk_f02_03 FOREIGN KEY (date_key) REFERENCES ce_dwh_b.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F02_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_room_day ADD CONSTRAINT fk_f02_04 FOREIGN KEY (site_key) REFERENCES ce_dwh_b.dim_site (site_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F02_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_room_day ADD CONSTRAINT fk_f02_05 FOREIGN KEY (hotel_key) REFERENCES ce_dwh_b.dim_hotel (hotel_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F02_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_room_day ADD CONSTRAINT fk_f02_06 FOREIGN KEY (room_key) REFERENCES ce_dwh_b.dim_room (room_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F03_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stay_night ADD CONSTRAINT fk_f03_03 FOREIGN KEY (service_date_key) REFERENCES ce_dwh_b.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F03_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stay_night ADD CONSTRAINT fk_f03_04 FOREIGN KEY (site_key) REFERENCES ce_dwh_b.dim_site (site_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F03_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stay_night ADD CONSTRAINT fk_f03_05 FOREIGN KEY (hotel_key) REFERENCES ce_dwh_b.dim_hotel (hotel_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F03_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stay_night ADD CONSTRAINT fk_f03_06 FOREIGN KEY (room_key) REFERENCES ce_dwh_b.dim_room (room_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F03_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stay_night ADD CONSTRAINT fk_f03_07 FOREIGN KEY (channel_key) REFERENCES ce_dwh_b.dim_channel (channel_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F03_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stay_night ADD CONSTRAINT fk_f03_08 FOREIGN KEY (customer_profile_key) REFERENCES ce_dwh_b.dim_customer_profile (customer_profile_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F03_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stay_night ADD CONSTRAINT fk_f03_09 FOREIGN KEY (rate_plan_key) REFERENCES ce_dwh_b.dim_rate_plan (rate_plan_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F04_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_ticket_order ADD CONSTRAINT fk_f04_02 FOREIGN KEY (ordered_date_key) REFERENCES ce_dwh_b.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F04_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_ticket_order ADD CONSTRAINT fk_f04_03 FOREIGN KEY (cohort_departure_date_key) REFERENCES ce_dwh_b.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F04_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_ticket_order ADD CONSTRAINT fk_f04_04 FOREIGN KEY (service_site_key) REFERENCES ce_dwh_b.dim_site (site_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F04_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_ticket_order ADD CONSTRAINT fk_f04_05 FOREIGN KEY (booking_site_key) REFERENCES ce_dwh_b.dim_site (site_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F04_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_ticket_order ADD CONSTRAINT fk_f04_06 FOREIGN KEY (referral_hotel_key) REFERENCES ce_dwh_b.dim_hotel (hotel_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F04_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_ticket_order ADD CONSTRAINT fk_f04_07 FOREIGN KEY (ticket_channel_key) REFERENCES ce_dwh_b.dim_channel (channel_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F04_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_ticket_order ADD CONSTRAINT fk_f04_08 FOREIGN KEY (booking_channel_key) REFERENCES ce_dwh_b.dim_channel (channel_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F04_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_ticket_order ADD CONSTRAINT fk_f04_09 FOREIGN KEY (customer_profile_key) REFERENCES ce_dwh_b.dim_customer_profile (customer_profile_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F04_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_ticket_order ADD CONSTRAINT fk_f04_10 FOREIGN KEY (centre_key) REFERENCES ce_dwh_b.dim_centre (centre_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F05_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_rental ADD CONSTRAINT fk_f05_02 FOREIGN KEY (pickup_date_key) REFERENCES ce_dwh_b.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F05_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_rental ADD CONSTRAINT fk_f05_03 FOREIGN KEY (return_date_key) REFERENCES ce_dwh_b.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F05_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_rental ADD CONSTRAINT fk_f05_04 FOREIGN KEY (cohort_departure_date_key) REFERENCES ce_dwh_b.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F05_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_rental ADD CONSTRAINT fk_f05_05 FOREIGN KEY (service_site_key) REFERENCES ce_dwh_b.dim_site (site_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F05_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_rental ADD CONSTRAINT fk_f05_06 FOREIGN KEY (booking_site_key) REFERENCES ce_dwh_b.dim_site (site_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F05_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_rental ADD CONSTRAINT fk_f05_07 FOREIGN KEY (referral_hotel_key) REFERENCES ce_dwh_b.dim_hotel (hotel_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F05_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_rental ADD CONSTRAINT fk_f05_08 FOREIGN KEY (booking_channel_key) REFERENCES ce_dwh_b.dim_channel (channel_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F05_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_rental ADD CONSTRAINT fk_f05_09 FOREIGN KEY (customer_profile_key) REFERENCES ce_dwh_b.dim_customer_profile (customer_profile_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F05_10'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_rental ADD CONSTRAINT fk_f05_10 FOREIGN KEY (centre_key) REFERENCES ce_dwh_b.dim_centre (centre_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F05_11'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_rental ADD CONSTRAINT fk_f05_11 FOREIGN KEY (vehicle_key) REFERENCES ce_dwh_b.dim_vehicle (vehicle_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F06_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_breakfast_entitlement ADD CONSTRAINT fk_f06_02 FOREIGN KEY (service_date_key) REFERENCES ce_dwh_b.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F06_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_breakfast_entitlement ADD CONSTRAINT fk_f06_03 FOREIGN KEY (site_key) REFERENCES ce_dwh_b.dim_site (site_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F06_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_breakfast_entitlement ADD CONSTRAINT fk_f06_04 FOREIGN KEY (hotel_key) REFERENCES ce_dwh_b.dim_hotel (hotel_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F06_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_breakfast_entitlement ADD CONSTRAINT fk_f06_05 FOREIGN KEY (room_key) REFERENCES ce_dwh_b.dim_room (room_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F06_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_breakfast_entitlement ADD CONSTRAINT fk_f06_06 FOREIGN KEY (customer_profile_key) REFERENCES ce_dwh_b.dim_customer_profile (customer_profile_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F06_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_breakfast_entitlement ADD CONSTRAINT fk_f06_07 FOREIGN KEY (rate_plan_key) REFERENCES ce_dwh_b.dim_rate_plan (rate_plan_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F06_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_breakfast_entitlement ADD CONSTRAINT fk_f06_08 FOREIGN KEY (outlet_key) REFERENCES ce_dwh_b.dim_outlet (outlet_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F06_09'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_breakfast_entitlement ADD CONSTRAINT fk_f06_09 FOREIGN KEY (meal_key) REFERENCES ce_dwh_b.dim_meal (meal_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F07_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_dining_order ADD CONSTRAINT fk_f07_02 FOREIGN KEY (service_date_key) REFERENCES ce_dwh_b.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F07_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_dining_order ADD CONSTRAINT fk_f07_03 FOREIGN KEY (site_key) REFERENCES ce_dwh_b.dim_site (site_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F07_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_dining_order ADD CONSTRAINT fk_f07_04 FOREIGN KEY (service_hotel_key) REFERENCES ce_dwh_b.dim_hotel (hotel_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F07_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_dining_order ADD CONSTRAINT fk_f07_05 FOREIGN KEY (booking_hotel_key) REFERENCES ce_dwh_b.dim_hotel (hotel_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F07_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_dining_order ADD CONSTRAINT fk_f07_06 FOREIGN KEY (customer_profile_key) REFERENCES ce_dwh_b.dim_customer_profile (customer_profile_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F07_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_dining_order ADD CONSTRAINT fk_f07_07 FOREIGN KEY (outlet_key) REFERENCES ce_dwh_b.dim_outlet (outlet_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F07_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_dining_order ADD CONSTRAINT fk_f07_08 FOREIGN KEY (meal_key) REFERENCES ce_dwh_b.dim_meal (meal_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F08_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_meal_session ADD CONSTRAINT fk_f08_03 FOREIGN KEY (service_date_key) REFERENCES ce_dwh_b.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F08_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_meal_session ADD CONSTRAINT fk_f08_04 FOREIGN KEY (site_key) REFERENCES ce_dwh_b.dim_site (site_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F08_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_meal_session ADD CONSTRAINT fk_f08_05 FOREIGN KEY (hotel_key) REFERENCES ce_dwh_b.dim_hotel (hotel_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F08_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_meal_session ADD CONSTRAINT fk_f08_06 FOREIGN KEY (outlet_key) REFERENCES ce_dwh_b.dim_outlet (outlet_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F08_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_meal_session ADD CONSTRAINT fk_f08_07 FOREIGN KEY (meal_key) REFERENCES ce_dwh_b.dim_meal (meal_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F09_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_admission ADD CONSTRAINT fk_f09_02 FOREIGN KEY (admission_date_key) REFERENCES ce_dwh_b.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F09_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_admission ADD CONSTRAINT fk_f09_03 FOREIGN KEY (site_key) REFERENCES ce_dwh_b.dim_site (site_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F09_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_admission ADD CONSTRAINT fk_f09_04 FOREIGN KEY (customer_profile_key) REFERENCES ce_dwh_b.dim_customer_profile (customer_profile_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F09_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_admission ADD CONSTRAINT fk_f09_05 FOREIGN KEY (centre_key) REFERENCES ce_dwh_b.dim_centre (centre_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F09_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_admission ADD CONSTRAINT fk_f09_06 FOREIGN KEY (activity_key) REFERENCES ce_dwh_b.dim_activity (activity_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F10_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_activity_day ADD CONSTRAINT fk_f10_03 FOREIGN KEY (date_key) REFERENCES ce_dwh_b.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F10_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_activity_day ADD CONSTRAINT fk_f10_04 FOREIGN KEY (site_key) REFERENCES ce_dwh_b.dim_site (site_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F10_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_activity_day ADD CONSTRAINT fk_f10_05 FOREIGN KEY (centre_key) REFERENCES ce_dwh_b.dim_centre (centre_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F10_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_activity_day ADD CONSTRAINT fk_f10_06 FOREIGN KEY (activity_key) REFERENCES ce_dwh_b.dim_activity (activity_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F11_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_vehicle_day ADD CONSTRAINT fk_f11_03 FOREIGN KEY (date_key) REFERENCES ce_dwh_b.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F11_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_vehicle_day ADD CONSTRAINT fk_f11_04 FOREIGN KEY (site_key) REFERENCES ce_dwh_b.dim_site (site_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F11_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_vehicle_day ADD CONSTRAINT fk_f11_05 FOREIGN KEY (centre_key) REFERENCES ce_dwh_b.dim_centre (centre_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F11_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_vehicle_day ADD CONSTRAINT fk_f11_06 FOREIGN KEY (vehicle_key) REFERENCES ce_dwh_b.dim_vehicle (vehicle_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F12_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_purchase_line ADD CONSTRAINT fk_f12_02 FOREIGN KEY (ordered_date_key) REFERENCES ce_dwh_b.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F12_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_purchase_line ADD CONSTRAINT fk_f12_03 FOREIGN KEY (expected_date_key) REFERENCES ce_dwh_b.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F12_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_purchase_line ADD CONSTRAINT fk_f12_04 FOREIGN KEY (site_key) REFERENCES ce_dwh_b.dim_site (site_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F12_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_purchase_line ADD CONSTRAINT fk_f12_05 FOREIGN KEY (hotel_key) REFERENCES ce_dwh_b.dim_hotel (hotel_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F12_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_purchase_line ADD CONSTRAINT fk_f12_06 FOREIGN KEY (supplier_key) REFERENCES ce_dwh_b.dim_supplier (supplier_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F12_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_purchase_line ADD CONSTRAINT fk_f12_07 FOREIGN KEY (item_key) REFERENCES ce_dwh_b.dim_item (item_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F13_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_receipt ADD CONSTRAINT fk_f13_02 FOREIGN KEY (received_date_key) REFERENCES ce_dwh_b.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F13_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_receipt ADD CONSTRAINT fk_f13_03 FOREIGN KEY (expected_date_key) REFERENCES ce_dwh_b.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F13_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_receipt ADD CONSTRAINT fk_f13_04 FOREIGN KEY (expires_date_key) REFERENCES ce_dwh_b.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F13_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_receipt ADD CONSTRAINT fk_f13_05 FOREIGN KEY (site_key) REFERENCES ce_dwh_b.dim_site (site_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F13_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_receipt ADD CONSTRAINT fk_f13_06 FOREIGN KEY (hotel_key) REFERENCES ce_dwh_b.dim_hotel (hotel_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F13_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_receipt ADD CONSTRAINT fk_f13_07 FOREIGN KEY (supplier_key) REFERENCES ce_dwh_b.dim_supplier (supplier_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F13_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_receipt ADD CONSTRAINT fk_f13_08 FOREIGN KEY (item_key) REFERENCES ce_dwh_b.dim_item (item_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F14_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stock_movement ADD CONSTRAINT fk_f14_02 FOREIGN KEY (movement_date_key) REFERENCES ce_dwh_b.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F14_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stock_movement ADD CONSTRAINT fk_f14_03 FOREIGN KEY (site_key) REFERENCES ce_dwh_b.dim_site (site_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F14_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stock_movement ADD CONSTRAINT fk_f14_04 FOREIGN KEY (hotel_key) REFERENCES ce_dwh_b.dim_hotel (hotel_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F14_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stock_movement ADD CONSTRAINT fk_f14_05 FOREIGN KEY (supplier_key) REFERENCES ce_dwh_b.dim_supplier (supplier_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F14_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_stock_movement ADD CONSTRAINT fk_f14_06 FOREIGN KEY (item_key) REFERENCES ce_dwh_b.dim_item (item_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F15_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.agg_inventory_lot_day ADD CONSTRAINT fk_f15_04 FOREIGN KEY (snapshot_date_key) REFERENCES ce_dwh_b.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F15_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.agg_inventory_lot_day ADD CONSTRAINT fk_f15_05 FOREIGN KEY (site_key) REFERENCES ce_dwh_b.dim_site (site_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F15_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.agg_inventory_lot_day ADD CONSTRAINT fk_f15_06 FOREIGN KEY (hotel_key) REFERENCES ce_dwh_b.dim_hotel (hotel_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F15_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.agg_inventory_lot_day ADD CONSTRAINT fk_f15_07 FOREIGN KEY (supplier_key) REFERENCES ce_dwh_b.dim_supplier (supplier_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F15_08'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.agg_inventory_lot_day ADD CONSTRAINT fk_f15_08 FOREIGN KEY (item_key) REFERENCES ce_dwh_b.dim_item (item_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F16_02'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_maintenance_work ADD CONSTRAINT fk_f16_02 FOREIGN KEY (start_date_key) REFERENCES ce_dwh_b.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F16_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_maintenance_work ADD CONSTRAINT fk_f16_03 FOREIGN KEY (end_date_key) REFERENCES ce_dwh_b.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F16_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_maintenance_work ADD CONSTRAINT fk_f16_04 FOREIGN KEY (site_key) REFERENCES ce_dwh_b.dim_site (site_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F16_05'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_maintenance_work ADD CONSTRAINT fk_f16_05 FOREIGN KEY (hotel_key) REFERENCES ce_dwh_b.dim_hotel (hotel_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F16_06'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_maintenance_work ADD CONSTRAINT fk_f16_06 FOREIGN KEY (room_key) REFERENCES ce_dwh_b.dim_room (room_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F16_07'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_maintenance_work ADD CONSTRAINT fk_f16_07 FOREIGN KEY (asset_key) REFERENCES ce_dwh_b.dim_asset (asset_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F17_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_weather_day ADD CONSTRAINT fk_f17_03 FOREIGN KEY (weather_date_key) REFERENCES ce_dwh_b.dim_date (date_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_F17_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.fact_weather_day ADD CONSTRAINT fk_f17_04 FOREIGN KEY (site_key) REFERENCES ce_dwh_b.dim_site (site_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_L01_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.bridge_booking_room ADD CONSTRAINT fk_l01_03 FOREIGN KEY (room_key) REFERENCES ce_dwh_b.dim_room (room_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_L01_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.bridge_booking_room ADD CONSTRAINT fk_l01_04 FOREIGN KEY (rate_plan_key) REFERENCES ce_dwh_b.dim_rate_plan (rate_plan_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_L02_03'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.bridge_room_day_maintenance ADD CONSTRAINT fk_l02_03 FOREIGN KEY (room_key) REFERENCES ce_dwh_b.dim_room (room_key)'; END IF; END;
/

DECLARE n NUMBER; BEGIN SELECT COUNT(*) INTO n FROM dba_constraints WHERE owner='CE_DWH_B' AND constraint_name='FK_L02_04'; IF n=0 THEN EXECUTE IMMEDIATE 'ALTER TABLE ce_dwh_b.bridge_room_day_maintenance ADD CONSTRAINT fk_l02_04 FOREIGN KEY (date_key) REFERENCES ce_dwh_b.dim_date (date_key)'; END IF; END;
/
prompt SCHEMA_DDL_COMPLETE
exit
