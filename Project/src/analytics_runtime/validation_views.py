"""Register the two session-scoped helper views from explicitly pinned Parquet.

Missing files or mismatched checksums are errors. A missing publication must not
be represented by an empty business report. The DDL probe uses its own explicitly
labelled empty fixture publication, never the active business publication.
"""
import hashlib
from pathlib import Path
from pyspark.sql.types import StructType


def register_validation_views(spark, manifest, contract):
    if not manifest.get('publication_id'):
        raise ValueError('Explicit publication_id required')
    views=[e for e in contract['entities'] if e['kind']=='VALIDATION_VIEW']
    if set(manifest['helpers'])!={v['physical_name'] for v in views}:
        raise ValueError('Helper view inventory differs from contract')
    for entity in views:
        name=entity['physical_name']; helper=manifest['helpers'][name]
        path=Path(helper['path'])
        actual={str(p.relative_to(path)):hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(path.rglob('*')) if p.is_file()}
        if not actual or actual!=helper['sha256']:
            raise ValueError('Missing or changed helper files: '+name)
        schema=StructType.fromJson(helper['schema'])
        expected=[(c['name'],c['spark_sql_type'].lower()) for c in entity['columns']]
        # Verify contract field names and types before exposing the view.
        declared=[(f.name,f.dataType.simpleString()) for f in schema]
        aliases={'bigint':'bigint','int':'int','string':'string','timestamp_ntz':'timestamp_ntz','date':'date'}
        if declared!=[(n,aliases.get(t,t)) for n,t in expected]:
            raise ValueError('Helper schema differs: '+name)
        spark.read.schema(schema).parquet(str(path)).createOrReplaceTempView(name)
