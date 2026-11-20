"""Root provisioning policy for the Data-owned capture schema, never runtime DDL."""
import hashlib
CAPTURE_SCHEMA_SOURCE='sources/market_data/market_data/capture_schema.sql'
CAPTURE_SCHEMA_SHA256='81ed2eee67f5287f6760eca6e45930901395fa1a6685f993287dac413dfe1a7f'
def prepared_capture_sql(raw,pin):
    """Bind the supported Data asset; make every existing-table collision fail."""
    if (type(raw) is not bytes or not 0<len(raw)<=65536 or type(pin) is not dict
            or set(pin)!={'sha256','bytes'} or type(pin['bytes']) is not int
            or pin['bytes']!=len(raw) or pin['sha256']!=CAPTURE_SCHEMA_SHA256
            or hashlib.sha256(raw).hexdigest()!=CAPTURE_SCHEMA_SHA256):
        raise ValueError('CAPTURE_SCHEMA_SOURCE_REJECTED')
    sql=raw.decode('ascii').replace('CREATE TABLE IF NOT EXISTS ','CREATE TABLE public.')
    if sql.count('CREATE TABLE public.')!=3:raise ValueError('CAPTURE_SCHEMA_SOURCE_REJECTED')
    return 'BEGIN;\nSET LOCAL search_path=pg_catalog;\n'+sql+'\nCOMMIT;\n'
