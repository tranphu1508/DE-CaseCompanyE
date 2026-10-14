"""Versioned, deterministic CompanyE extensions; never writes v1 artifacts."""
import argparse
import csv
import hashlib
import io
import json
import platform
import random
import re
import shutil
import unicodedata
from collections import defaultdict, Counter
from datetime import date, datetime, timedelta
from pathlib import Path

from generate import Generator, ROOT, days, timestamp, sha, write_json
from model_v2 import MODELS, contracts


def fingerprints():
    return {n:sha(ROOT/'src'/n) for n in ['generate.py','model.py','generate_v2.py','model_v2.py']}


def ascii_name(value):
    return ''.join(c for c in unicodedata.normalize('NFD',value) if unicodedata.category(c)!='Mn').replace('Đ','D')


class GeneratorV2(Generator):
    def __init__(self,cfg):
        super().__init__(cfg)
        self.rows={db:{t.name:[] for t in tables} for db,tables in MODELS.items()}
        self.models={db:{t.name:t for t in tables} for db,tables in MODELS.items()}
        self.pr=random.Random(cfg['procurement_seed'])
        self.po_groups={}
        self.identity_cases=[]

    def purchase(self,hotel,d,supplier,item,amount):
        # Different items for the same supplier/hotel/day share a purchase order.
        group=(hotel['hotel_id'],supplier,d)
        if group not in self.po_groups:
            self.po_groups[group]=self.h('purchase_orders',hotel_id=hotel['hotel_id'],supplier_id=supplier,
                ordered_on=d-timedelta(days=2),expected_on=d)
        po=self.po_groups[group]
        line=self.h('purchase_lines',purchase_order_id=po['purchase_order_id'],item_id=item['item_id'],
            ordered_qty=amount,unit_price_vnd=int(item['reference_cost_vnd']*self.pr.uniform(.9,1.15)//100)*100)
        parts=[amount]
        if amount>=3 and self.pr.random()<self.cfg['split_receipt_probability']:
            first=max(1,amount*2//3); parts=[first,amount-first]
        for part,qty in enumerate(parts):
            received=d+timedelta(days=(1 if self.pr.random()<.05 else 0)+part*2)
            rejected=1 if qty>1 and self.pr.random()<.08 else 0
            accepted=qty-rejected
            receipt=self.h('receipts',purchase_line_id=line['purchase_line_id'],received_on=received,
                accepted_qty=accepted,rejected_qty=rejected,
                expires_on=received+timedelta(days=item['shelf_life_days']) if item['shelf_life_days'] else None)
            values=dict(hotel_id=hotel['hotel_id'],item_id=item['item_id'],receipt_id=receipt['receipt_id'],movement_date=received)
            self.h('stock_movements',**values,movement_type='IN',quantity=accepted,usage_area='WAREHOUSE')
            waste=1 if accepted>2 and self.pr.random()<.08 and item['shelf_life_days'] else 0
            used=max(0,accepted-waste-1)
            bf=self.session_map.get((hotel['hotel_id'],received,'BREAKFAST'))
            dn=self.session_map.get((hotel['hotel_id'],received,'DINNER'))
            total=(bf['actual_covers'] if bf else 0)+(dn['actual_covers'] if dn else 0)
            if item['shelf_life_days'] and total:
                bf_used=round(used*(bf['actual_covers'] if bf else 0)/total)
                for session,n in [(bf,bf_used),(dn,used-bf_used)]:
                    if session and n:
                        self.h('stock_movements',**values,session_id=session['session_id'],movement_type='USE',quantity=n,usage_area='BUFFET')
                        session['ingredient_cost_vnd']+=n*line['unit_price_vnd']
            else:
                self.h('stock_movements',**values,movement_type='USE',quantity=used,
                    usage_area='KITCHEN_OTHER' if item['shelf_life_days'] else 'HOUSEKEEPING')
            if waste: self.h('stock_movements',**values,movement_type='WASTE',quantity=waste,usage_area='WAREHOUSE')
            if receipt['expires_on'] and receipt['expires_on']<=self.end.isoformat():
                self.h('stock_movements',hotel_id=hotel['hotel_id'],item_id=item['item_id'],receipt_id=receipt['receipt_id'],
                    movement_date=receipt['expires_on'],movement_type='WASTE',quantity=1,usage_area='WAREHOUSE')

    def identities(self):
        rng=random.Random(self.cfg['identity_seed'])
        guests=self.rows['hotel_ops']['guests']; customers=self.rows['entertainment_ops']['customers']
        hmap={g['guest_id']:'H-'+format(rng.getrandbits(96),'024x') for g in guests}
        emap={c['customer_id']:'E-'+format(rng.getrandbits(96),'024x') for c in customers}
        for table in self.rows['hotel_ops'].values():
            for row in table:
                if row.get('guest_id') in hmap: row['guest_id']=hmap[row['guest_id']]
        for table in self.rows['entertainment_ops'].values():
            for row in table:
                if row.get('customer_id') in emap: row['customer_id']=emap[row['customer_id']]
        for pair in self.truth:
            pair['hotel_guest_id']=hmap[pair['hotel_guest_id']]
            pair['entertainment_customer_id']=emap[pair['entertainment_customer_id']]
        by_customer={c['customer_id']:c for c in customers}
        for i,(guest,pair) in enumerate(zip(guests,self.truth)):
            guest['full_name']=re.sub(r'\s+\d+$','',guest['full_name'])
            customer=by_customer[pair['entertainment_customer_id']]
            customer['full_name']=ascii_name(guest['full_name']) if i%3==0 else guest['full_name']
            # Small controlled cohorts overlap; classifications stay audit-only.
            labels=[]
            if i%20 in (0,1):
                household=i//20
                phone=f'088{household:07d}'
                guest['phone']=phone; customer['phone']='+84 '+phone[1:]
                labels.append('SHARED_HOUSEHOLD_PHONE')
            if i%10==2:
                customer['phone']=None; customer['email']=None; customer['member_card_ref']=None
                labels.append('MISSING_CONTACTS')
            if i%10==3:
                customer['phone']=f'087{i:07d}'; customer['email']=None
                labels.append('CHANGED_PHONE')
            if i%10==4:
                customer['full_name']=customer['full_name'][:-1]+'h'
                labels.append('NAME_TYPO')
            if i%10==5:
                customer['email']='  '+guest['email'].upper()+'  '
                labels.append('EMAIL_FORMAT')
            if labels: self.identity_cases.append({**pair,'cases':labels})
        for guest in rng.sample(list(guests),min(self.cfg['duplicate_guest_profiles'],len(guests))):
            duplicate={**guest,'guest_id':'H-'+format(rng.getrandbits(96),'024x'),'full_name':ascii_name(guest['full_name'])}
            self.h('guests',**duplicate)
            counterpart=next(p['entertainment_customer_id'] for p in self.truth if p['hotel_guest_id']==guest['guest_id'])
            pair={'hotel_guest_id':duplicate['guest_id'],'entertainment_customer_id':counterpart}
            self.truth.append(pair); self.identity_cases.append({**pair,'cases':['DUPLICATE_LOCAL_PROFILE']})
        # Remove insertion-order linkage and sequential profile suffixes from exported rows.
        rng.shuffle(guests); rng.shuffle(customers)

    def adjustments(self):
        rng=random.Random(self.cfg['adjustment_seed'])
        h=self.rows['hotel_ops']; by_booking=defaultdict(list)
        for line in h['booking_rooms']: by_booking[line['booking_id']].append(line)
        promos={p['promotion_id']:p for p in h['promotions']}
        channels={c['channel_id']:c for c in h['channels']}
        settlements={s['booking_id']:s for s in h['settlements']}
        candidates=[b for b in h['bookings'] if b['status']=='COMPLETED']
        money_cols=['gross_vnd','discount_vnd','company_share_vnd','partner_share_vnd','customer_due_vnd','commission_vnd']
        for b in rng.sample(candidates,min(self.cfg['price_adjustments'],len(candidates))):
            correction_day=min(date.fromisoformat(b['booked_on'])+timedelta(days=1),date.fromisoformat(b['arrival']))
            def revision(number,reason,when):
                rev=self.h('booking_revisions',booking_id=b['booking_id'],revision_no=number,occurred_at=when,
                           reason=reason,**{c:b[c] for c in money_cols})
                for line in by_booking[b['booking_id']]:
                    self.h('booking_room_revisions',revision_id=rev['revision_id'],booking_room_id=line['booking_room_id'],nightly_rate_vnd=line['nightly_rate_vnd'])
            revision(1,'ORIGINAL',timestamp(date.fromisoformat(b['booked_on']),10))
            previous_due=b['customer_due_vnd']
            by_booking[b['booking_id']][0]['nightly_rate_vnd']+=50000
            nights=(date.fromisoformat(b['departure'])-date.fromisoformat(b['arrival'])).days
            b['gross_vnd']=sum(l['nightly_rate_vnd']*nights for l in by_booking[b['booking_id']])
            p=promos.get(b['promotion_id'])
            b['discount_vnd']=min(b['gross_vnd']*p['discount_bps']//10000,p['cap_vnd']) if p else 0
            b['partner_share_vnd']=b['discount_vnd']*p['partner_share_bps']//10000 if p else 0
            b['company_share_vnd']=b['discount_vnd']-b['partner_share_vnd']
            b['customer_due_vnd']=b['gross_vnd']-b['discount_vnd']
            b['commission_vnd']=(b['gross_vnd']-b['company_share_vnd'])*channels[b['channel_id']]['commission_bps']//10000
            self.h('payments',booking_id=b['booking_id'],event_time=timestamp(correction_day,11),event_type='CHARGE',amount_vnd=b['customer_due_vnd']-previous_due)
            if b['booking_id'] in settlements:
                s=settlements[b['booking_id']]; s['sponsor_due_vnd']=b['partner_share_vnd']; s['commission_vnd']=b['commission_vnd']
                s['sponsor_received_vnd']=s['sponsor_due_vnd'] if s['status']=='MATCHED' else 0
            revision(2,'RATE_CORRECTION',timestamp(correction_day,11))

    def run(self):
        super().run(); self.identities(); self.adjustments()


def table_bytes(rows,table):
    output=io.StringIO(newline=''); writer=csv.writer(output)
    names=[c[0] for c in table.columns]; writer.writerow(names)
    writer.writerows(['\\N' if row[n] is None else row[n] for n in names] for row in rows)
    return output.getvalue().encode('utf-8')


def external_files(gen):
    """Files are source representations, not additional economic receipts."""
    rng=random.Random(gen.cfg['delivery_seed']); h=gen.rows['hotel_ops']
    lines={x['purchase_line_id']:x for x in h['purchase_lines']}
    orders={x['purchase_order_id']:x for x in h['purchase_orders']}
    eligible=[r for r in h['receipts'] if lines[r['purchase_line_id']]['item_id'] in ('RICE','TOMATO','FISH')]
    selected=rng.sample(eligible,min(gen.cfg['external_receipts'],len(eligible)))
    fields=['event_id','receipt_ref','revision','occurred_at','source_recorded_at','supplier_id','hotel_id','purchase_line_ref','accepted_qty','unit','unit_price_vnd']
    batches=defaultdict(list); truth=[]
    for i,r in enumerate(selected):
        line=lines[r['purchase_line_id']]; po=orders[line['purchase_order_id']]
        occurred=datetime.fromisoformat(timestamp(date.fromisoformat(r['received_on']),10))
        corrected=i<gen.cfg['external_corrections']
        for revision in ([1,2] if corrected else [1]):
            recorded=occurred+timedelta(hours=revision-1)
            qty=int(r['accepted_qty'])+(1 if corrected and revision==1 else 0)
            unit='sọt' if gen.cfg['external_corrections']<=i<gen.cfg['external_corrections']+gen.cfg['external_unknown_units'] else 'g' if i%3==0 else 'kg'
            row=dict(zip(fields,[f"EV-{i:04d}-R{revision}",r['receipt_id'],revision,occurred.isoformat(),recorded.isoformat(),
                po['supplier_id'],po['hotel_id'],r['purchase_line_id'],qty*1000 if unit=='g' else qty,unit,line['unit_price_vnd']]))
            # Revision 1 of corrected records arrives after revision 2.
            delay=10 if corrected and revision==1 else 4 if i%5==0 else 1
            arrived=recorded+timedelta(days=delay)
            batches[arrived.date().isoformat()].append(row)
        truth.append({'receipt_ref':r['receipt_id'],'accepted_qty_kg':int(r['accepted_qty']),
                      'expected_revision':2 if corrected else 1,'normalizable':unit!='sọt'})
    files={}; deliveries=[]
    for i,(day,rows) in enumerate(sorted(batches.items())):
        name=f'receipts_{i:03d}.csv'; buf=io.StringIO(newline=''); w=csv.DictWriter(buf,fieldnames=fields); w.writeheader(); w.writerows(rows)
        files[name]=buf.getvalue().encode('utf-8')
        deliveries.append({'file':name,'delivery_id':f'DEL-{i:03d}','received_at':day+'T23:00:00+07:00','rows':len(rows)})
    for i,delivery in enumerate(deliveries[:3]):
        replay=f'replay_{i:03d}.csv'; files[replay]=files[delivery['file']]
        deliveries.append({'file':replay,'delivery_id':f'REPLAY-{i:03d}',
            'received_at':(datetime.fromisoformat(delivery['received_at'])+timedelta(days=14)).isoformat(),'rows':delivery['rows']})
    files['delivery_schedule.json']=json.dumps({'quantity_policy':'g -> kg; prices always VND per kg; unknown baskets require review',
        'deliveries':deliveries},ensure_ascii=False,indent=2).encode('utf-8')
    return files,truth


def create(cfg,out):
    gen=GeneratorV2(cfg); gen.run()
    init=['\\set ON_ERROR_STOP on']; counts={}
    for db,tables in MODELS.items():
        folder=out/db; folder.mkdir(parents=True,exist_ok=True)
        ddl='\n\n'.join(t.ddl() for t in tables)
        if db=='hotel_ops': ddl+='\nALTER TABLE booking_revisions ADD UNIQUE(booking_id,revision_no);\nALTER TABLE booking_room_revisions ADD UNIQUE(revision_id,booking_room_id);'
        (folder/'schema.sql').write_text(ddl,encoding='utf-8')
        init += [f'CREATE DATABASE {db}_v2;',f'\\connect {db}_v2','BEGIN;',ddl]; counts[db]={}
        for table in tables:
            (folder/(table.name+'.csv')).write_bytes(table_bytes(gen.rows[db][table.name],table))
            counts[db][table.name]=len(gen.rows[db][table.name])
            init.append(f"COPY {table.name} FROM '/seed/v2/{db}/{table.name}.csv' WITH (FORMAT CSV,HEADER true,NULL '\\N');")
            for n,t,r,d in table.columns:
                if 'REFERENCES' in r: init.append(f'CREATE INDEX ON {table.name} ({n});')
        init+=['COMMIT;','ANALYZE;']
    (out/'load.sql').write_text('\n'.join(init),encoding='utf-8')
    write_json(out/'contracts.json',contracts())
    files,truth=external_files(gen); (out/'external').mkdir()
    for name,data in files.items(): (out/'external'/name).write_bytes(data)
    write_json(out/'audit_only/identity_truth_DO_NOT_INGEST.json',gen.truth)
    write_json(out/'audit_only/identity_cases_DO_NOT_INGEST.json',gen.identity_cases)
    write_json(out/'audit_only/receipt_truth_DO_NOT_INGEST.json',truth)
    audit={'base_rules':'Inherited v1 assumptions except overridden procurement/identity/adjustments; all synthetic.',
        'configuration':cfg,'generator_sha256':fingerprints(),
        'changes':['PO grouped by hotel/supplier/date; multi-item orders','Split deliveries preserve ordered=accepted+rejected and lot-specific stock',
                   'Opaque independent customer IDs, contact changes/missingness/shared phones, duplicate profiles',
                   'Selected completed bookings have two price revisions and an additional charge',
                   'Receipt file replays, late arrivals, out-of-order revisions and unknown units'],
        'limitations':['No causal business inference from artificial distributions','No full CDC or partial booking cancellation',
                       'Receipt exports are representations of source receipts, never extra purchases',
                       'Identity resolution is not implemented; ambiguous profiles must remain unresolved',
                       'Meal costs still use allocation by covers; family loyalty/combo ERP remain out of scope'],
        'identity_case_counts':dict(Counter(c for row in gen.identity_cases for c in row['cases']))}
    write_json(out/'audit_only/generation_audit.json',audit)
    manifest={'dataset_version':'v2','config':cfg,'seed':cfg['seed'],'python_version':platform.python_version(),
        'generator_sha256':fingerprints(),'rows':counts,'total_rows':sum(sum(t.values()) for t in counts.values()),
        'files':{p.relative_to(out).as_posix():sha(p) for p in sorted(out.rglob('*')) if p.is_file()},'synthetic':True}
    write_json(out/'manifest.json',manifest)
    return manifest


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--config',default=str(ROOT/'config/generation_v2.json')); args=parser.parse_args()
    cfg=json.loads(Path(args.config).read_text(encoding='utf-8')); assert cfg['dataset_version']=='v2'
    out=ROOT/'generated/v2'
    if out.exists():
        manifest=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
        assert manifest['config']==cfg and manifest['generator_sha256']==fingerprints(),'Frozen v2 differs; create a new explicit version'
        assert all(sha(out/p)==h for p,h in manifest['files'].items())
        print('Existing v2 verified'); return
    out.mkdir(parents=True); manifest=create(cfg,out)
    evidence=ROOT/'reports/reproducibility/v2'; evidence.mkdir(parents=True,exist_ok=True)
    for name in fingerprints(): shutil.copyfile(ROOT/'src'/name,evidence/name)
    for path in [ROOT/'config/generation_v2.json',out/'manifest.json',out/'audit_only/generation_audit.json']:
        shutil.copyfile(path,evidence/path.name)
    print(json.dumps({'tables':sum(len(t) for t in MODELS.values()),'rows':manifest['total_rows'],'version':'v2'}))


if __name__=='__main__': main()
