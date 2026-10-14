import argparse
import sys
from pathlib import Path
# spark-submit puts this file's directory first. Avoid shadowing the legacy
# top-level publication package with lakehouse_b/publication.py.
sys.path=[p for p in sys.path if Path(p or '.').resolve()!=Path(__file__).resolve().parent]
from lakehouse_b.common import create_session,Database

def main():
    ap=argparse.ArgumentParser();ap.add_argument('phase');ap.add_argument('--fail-after',type=int,default=0);a=ap.parse_args()
    spark=create_session('CompanyE-independent-B-'+a.phase);spark.sparkContext.setLogLevel('WARN');db=Database(spark)
    try:
        db.lock()
        if a.phase=='silver':
            from lakehouse_b.silver import build
            build(spark,a.fail_after)
        elif a.phase=='gold':
            from lakehouse_b.gold import build
            build(spark,db,a.fail_after)
        elif a.phase=='explore':
            from lakehouse_b.verification import explore
            explore(spark,db)
        elif a.phase=='publish':
            from lakehouse_b.publication import publish
            publish(spark,db,a.fail_after)
        elif a.phase=='verify':
            from lakehouse_b.verification import verify
            verify(spark,db)
        elif a.phase=='fixtures':
            from lakehouse_b.verification import fixtures
            fixtures(spark,db)
        else:raise ValueError(a.phase)
    finally:db.close();spark.stop()
if __name__=='__main__':main()
