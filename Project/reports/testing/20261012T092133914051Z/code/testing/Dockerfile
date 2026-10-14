FROM python:3.11.9-slim-bookworm@sha256:8fb099199b9f2d70342674bd9dbccd3ed03a258f26bbd1d556822c6dfc60c317
RUN apt-get update && apt-get install -y --no-install-recommends openjdk-17-jre-headless procps \
    && rm -rf /var/lib/apt/lists/*
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 \
    SPARK_LOCAL_IP=127.0.0.1 PYTHONPATH=/workspace/src PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 PYSPARK_PYTHON=python GX_ANALYTICS_ENABLED=false
COPY requirements.txt requirements.lock /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.lock && pip check
WORKDIR /workspace
CMD ["python", "testing/run_suite.py"]
