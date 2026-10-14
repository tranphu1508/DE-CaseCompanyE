"""Small control/driver JDBC operations and explicit typed dimension frames."""
from datetime import datetime,date
from decimal import Decimal
import json
from analytics_runtime.session import secret
from analytics_runtime.scd2 import canonical
from pyspark.sql.types import StructType,StructField,_parse_datatype_string

class Jdbc:
    def __init__(self,spark,engine):
        self.spark=spark;self.j=spark._jvm;self.engine=engine
        if engine=='postgres':
            url='jdbc:postgresql://metadata:5432/ce_metadata';user='ce_control_writer';pw=secret('CE_CONTROL_PASSWORD_FILE')
        else:
            url='jdbc:oracle:thin:@//oracle:1521/FREEPDB1';user='CE_LOADER';pw=secret('CE_ORACLE_LOADER_PASSWORD_FILE')
        props=self.j.java.util.Properties();props.setProperty('user',user);props.setProperty('password',pw)
        driver=self.j.org.postgresql.Driver() if engine=='postgres' else self.j.oracle.jdbc.OracleDriver()
        self.conn=driver.connect(url,props)
    def statement(self,sql,params):
        stmt=self.conn.prepareStatement(sql)
        for i,v in enumerate(params,1):
            if v is None:stmt.setNull(i,self.j.java.sql.Types.NULL)
            elif isinstance(v,datetime):stmt.setTimestamp(i,self.j.java.sql.Timestamp.valueOf(v.isoformat(' ',timespec='microseconds')))
            elif isinstance(v,date):stmt.setDate(i,self.j.java.sql.Date.valueOf(v.isoformat()))
            elif isinstance(v,(Decimal,int)):stmt.setBigDecimal(i,self.j.java.math.BigDecimal(str(v)))
            else:stmt.setString(i,str(v))
        return stmt
    def execute(self,sql,params=()):
        stmt=self.statement(sql,params)
        try:return stmt.executeUpdate()
        finally:stmt.close()
    def query(self,sql,params=()):
        stmt=self.statement(sql,params)
        try:
            rs=stmt.executeQuery();n=rs.getMetaData().getColumnCount();out=[]
            while rs.next():out.append([rs.getString(i) for i in range(1,n+1)])
            rs.close();return out
        finally:stmt.close()
    def registry(self,keys):
        result={}
        for start in range(0,len(keys),1000):
            rows=json.loads(self.query('SELECT ce_control.allocate_keys(?::jsonb)',[canonical(keys[start:start+1000])])[0][0])
            result.update({canonical(k):v for k,v in rows})
        return result
    def write(self,table,rows,columns):
        # One transaction per complete dimension. No Spark partition partial commit.
        sql='INSERT INTO '+table+' ('+','.join(columns)+') VALUES ('+','.join('?' for _ in columns)+')'
        self.conn.setAutoCommit(False)
        stmt=self.conn.prepareStatement(sql)
        try:
            for ri,row in enumerate(rows):
                for i,c in enumerate(columns,1):
                    v=row[c]
                    if v is None:stmt.setNull(i,self.j.java.sql.Types.NULL)
                    elif isinstance(v,datetime):stmt.setTimestamp(i,self.j.java.sql.Timestamp.valueOf(v.isoformat(' ',timespec='microseconds')))
                    elif isinstance(v,date):stmt.setDate(i,self.j.java.sql.Date.valueOf(v.isoformat()))
                    elif isinstance(v,(Decimal,int)):stmt.setBigDecimal(i,self.j.java.math.BigDecimal(str(v)))
                    else:stmt.setString(i,v)
                stmt.addBatch()
                if (ri+1)%1000==0:stmt.executeBatch();stmt.clearBatch()
            stmt.executeBatch();self.conn.commit()
        except Exception:self.conn.rollback();raise
        finally:stmt.close();self.conn.setAutoCommit(True)
    def close(self):self.conn.close()

def frame(spark,entity,rows):
    fields=[StructField(c['name'],_parse_datatype_string(c['spark_sql_type']),c['nullable']) for c in entity['columns']]
    return spark.createDataFrame([tuple(r[c['name']] for c in entity['columns']) for r in rows],StructType(fields))

def oracle_rows(spark,entity,owner='CE_DWH_A'):
    cols=','.join(c['name'] for c in entity['columns'])
    df=(spark.read.format('jdbc').option('url','jdbc:oracle:thin:@//oracle:1521/FREEPDB1')
        .option('user','CE_LOADER').option('password',secret('CE_ORACLE_LOADER_PASSWORD_FILE'))
        .option('driver','oracle.jdbc.OracleDriver').option('dbtable','(SELECT '+cols+' FROM '+owner+'.'+entity['physical_name']+')')
        .option('sessionInitStatement',"ALTER SESSION SET TIME_ZONE='+00:00'").load())
    result=[]
    for record in df.collect():
        raw={k.lower():v for k,v in record.asDict().items()};row={}
        for c in entity['columns']:
            v=raw[c['name']];typ=c['spark_sql_type']
            if v is not None:
                if typ=='DATE' and isinstance(v,datetime):v=v.date()
                if typ in ('INT','BIGINT'):v=int(v)
            row[c['name']]=v
        result.append(row)
    return result

def fingerprint(rows,entity):
    import hashlib
    ordered=sorted(rows,key=lambda r:r[entity['primary_key'][0]])
    return hashlib.sha256('\n'.join(canonical([r[c['name']] for c in entity['columns']]) for r in ordered).encode()).hexdigest()
