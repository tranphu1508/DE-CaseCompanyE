from pathlib import Path
import os
from pyspark.sql import SparkSession


def secret(name):
    return Path(os.environ[name]).read_text(encoding='utf-8').strip()


def create_session(name):
    return (SparkSession.builder.appName(name)
            .config('spark.sql.catalog.ce.jdbc.user', 'ce_catalog')
            .config('spark.sql.catalog.ce.jdbc.password', secret('CE_CATALOG_PASSWORD_FILE'))
            .getOrCreate())
