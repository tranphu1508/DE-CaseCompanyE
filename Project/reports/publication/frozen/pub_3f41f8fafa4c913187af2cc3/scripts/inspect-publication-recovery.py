"""Read-only durable state capture before resuming an interrupted publication."""
from pathlib import Path
from datetime import datetime, timezone
import importlib.util, json, hashlib

spec = importlib.util.spec_from_file_location('publication_launcher', Path(__file__).with_name('publication.py'))
pub = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pub)

sql = """SELECT json_build_object(
 'candidates',(SELECT coalesce(json_agg(x),'[]') FROM (SELECT publication_id,run_id,slot,generation,expected_active,state,manifest_sha256,created_at FROM ce_control.publication_candidate) x),
 'active',(SELECT coalesce(json_agg(x),'[]') FROM ce_control.active_publication x),
 'runs',(SELECT coalesce(json_agg(x),'[]') FROM (SELECT run_id,state,oracle_slot FROM ce_control.pipeline_run) x),
 'events',(SELECT coalesce(json_agg(x ORDER BY event_id),'[]') FROM ce_control.publication_event x),
 'reservations',(SELECT coalesce(json_agg(x),'[]') FROM ce_control.slot_reservation x),
 'live_readers',(SELECT count(*) FROM ce_control.reader_lease WHERE expires_at>clock_timestamp()));"""
metadata = json.loads(pub.call(['docker','exec','-i',pub.svc.container('metadata'),'psql','-U','ce_meta_admin','-d','ce_metadata','-X','-A','-t','-v','ON_ERROR_STOP=1'], sql))
oracle_sql = """set heading off feedback off pagesize 0 linesize 300 trimspool on
whenever sqlerror exit sql.sqlcode rollback
alter session set container=FREEPDB1;
select slot||'|'||state||'|'||publication_id from ce_stage.publication_guard order by slot;
exit
"""
guard_text = pub.call(['docker','exec','-i',pub.svc.container('oracle'),'sqlplus','-S','/ as sysdba'],oracle_sql)
guards = [dict(zip(['slot','state','publication_id'], line.strip().split('|'))) for line in guard_text.splitlines() if '|' in line]
log = pub.OUT/'prepare-interrupted-reboot.log'
result = dict(observed_at=datetime.now(timezone.utc).isoformat(),status='OBSERVED_BEFORE_RESUME',metadata=metadata,oracle_guards=guards,
 interrupted_log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),
 host_restart='Reported by user; cause not established',
 docker_recovery='Preserved stale socket directories and let Docker recreate runtime sockets; no volume reset')
target=pub.OUT/'reboot-recovery.json'
if target.exists():
    raise SystemExit('Evidence already exists; preserve it before another capture.')
target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(result,ensure_ascii=False,indent=2))
