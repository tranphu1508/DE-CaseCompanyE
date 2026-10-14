"""Independent regeneration check; never used as an input to lake transformations."""
import csv
import hashlib
import io
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone

from generate import Generator, ROOT, code_fingerprint, write_json, sha
from model import MODELS


def main():
    cfg=json.loads((ROOT/'config/generation.json').read_text(encoding='utf-8'))
    out=ROOT/'generated'/cfg['dataset_version']
    manifest=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
    if code_fingerprint()!=manifest['generator_sha256']:
        raise RuntimeError('Generator code no longer matches the frozen seed manifest')
    gen=Generator(cfg); gen.run()
    comparisons=[]
    for db,tables in MODELS.items():
        for table in tables:
            data=io.StringIO(newline=''); writer=csv.writer(data)
            names=[c[0] for c in table.columns]; writer.writerow(names)
            writer.writerows(['\\N' if row[n] is None else row[n] for n in names] for row in gen.rows[db][table.name])
            regenerated=hashlib.sha256(data.getvalue().encode('utf-8')).hexdigest()
            original=sha(out/db/(table.name+'.csv'))
            comparisons.append({'table':db+'.'+table.name,'rows':len(gen.rows[db][table.name]),'sha256':original,'regenerated_sha256':regenerated,'identical':original==regenerated})
    if not all(c['identical'] for c in comparisons): raise RuntimeError('Deterministic regeneration failed')
    bookings=gen.rows['hotel_ops']['bookings']
    segments=defaultdict(Counter)
    for b in bookings:
        key=b['hotel_id']+'|'+b['arrival'][:7]
        segments[key]['bookings']+=1; segments[key][b['status']]+=1
        segments[key]['gross_vnd']+=b['gross_vnd']; segments[key]['company_discount_vnd']+=b['company_share_vnd']
    external=out/'external/supplier_mixed.csv'
    with external.open(encoding='utf-8-sig',newline='') as f: raw=list(csv.DictReader(f,delimiter=';'))
    docs=Counter((r['Supplier'],r['Document']) for r in raw)
    observed_quality={'rows':len(raw),'invalid_dates':sum(r['Date']=='khong ro' for r in raw),'unknown_unit_rows':sum(r['Unit']!='kg' for r in raw),'duplicate_document_rows':sum(n-1 for n in docs.values())}
    # A second seed is a small sensitivity fixture, never loaded into source or lake.
    alt={**cfg,'seed':cfg['seed']+1,'date_from':'2024-01-01','date_to':'2024-01-31','bookings':80,'customers':100,'walkin_tickets':15}
    alt_same={**alt,'seed':cfg['seed']}
    a=Generator(alt_same); a.run(); b=Generator(alt); b.run()
    changed=a.rows['hotel_ops']['bookings']!=b.rows['hotel_ops']['bookings']
    if not changed: raise RuntimeError('Changing random seed had no effect')
    report={'status':'PASSED','verified_at':datetime.now(timezone.utc).isoformat(),'seed':cfg['seed'],'generator_sha256':code_fingerprint(),'same_seed_same_code_byte_identical_tables':comparisons,'different_seed_changes_bookings':changed,'observed_external_quality':observed_quality,'segments_by_hotel_month':dict(segments),'warning':'Distribution checks describe generator assumptions; they are not evidence of real tourism demand or causality.'}
    write_json(ROOT/'reports/reproducibility'/cfg['dataset_version']/'regeneration_check.json',report)
    print(json.dumps({'status':'PASSED','byte_identical_tables':len(comparisons),'seed_sensitivity':changed,'external_quality':observed_quality},ensure_ascii=False))


if __name__=='__main__': main()
