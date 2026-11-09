import pathlib,sys,types,sqlite3,json
sys.path[:0]=['.','tests/gateway_target_adapter'];import test_direct
root=pathlib.Path(sys.argv[1]);allowed=root/'allowed';outside=root/'allowed-sibling';allowed.mkdir();outside.mkdir()
code=next(c for c in test_direct.DirectTests.test_actual_target_no_python_network_and_only_owned_sqlite.__code__.co_consts if isinstance(c,types.CodeType) and c.co_name=='owned_connect')
calls=[];self=types.SimpleNamespace(temp=types.SimpleNamespace(name=str(allowed)));values={'calls':calls,'original':sqlite3.connect,'self':self}
def cell(v):return (lambda:v).__closure__[0]
observer=types.FunctionType(code,test_direct.__dict__,closure=tuple(cell(values[name]) for name in code.co_freevars))
inside=observer(allowed/'positive.sqlite');inside.close()
external=outside/'outside-allowed-root.sqlite';con=observer(external);con.execute('CREATE TABLE a8_negative(x)');con.commit();con.close()
assert external.is_file() and external.parent!=allowed and allowed not in external.parents
print(json.dumps(dict(actual_primary_test_observer=True,positive_inside_detected=True,outside_allowed_root_SQLite_accepted=True,allowed=str(allowed),outside=str(external),recorded_calls=calls,scope='TEST_INSTRUMENTATION_P2_NOT_RUNTIME_EXTERNAL_WRITE_OR_AUTH_BYPASS'),indent=2))
