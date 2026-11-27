"""Unchanged full discovery plus bounded public case IDs for Actions failures.

Added annotations never contain exception values, traceback bodies, subtest
parameters or object-supplied IDs. Ordinary verbose unittest output is retained.
"""
import os
import re
import sys
import unittest


def static_id(test):
    kind=type(test)
    method=getattr(test,'_testMethodName','')
    value=kind.__module__+'.'+kind.__qualname__+'.'+method if type(method) is str else ''
    return value if len(value)<=500 and re.fullmatch('[A-Za-z_][A-Za-z0-9_.]*',value) else None


def inventory(suite):
    result=set()
    for test in suite:
        if isinstance(test,unittest.TestSuite):result.update(inventory(test))
        else:
            value=static_id(test)
            if value is not None:result.add(value)
    return result


class PublicResult(unittest.TextTestResult):
    def __init__(self,*args,public_ids,**kwargs):
        super().__init__(*args,**kwargs);self.public_ids=public_ids;self.annotations=0
    def annotate(self,test,kind):
        if os.environ.get('GITHUB_ACTIONS')!='true':return
        if self.annotations>=50:
            if self.annotations==50:self.stream.write('\n::error::UNITTEST_ADDITIONAL_FAILURES_SUPPRESSED\n');self.annotations+=1
            return
        value=static_id(test)
        public=value if value in self.public_ids else 'DISCOVERY_OR_UNKNOWN_PUBLIC_CASE'
        self.stream.write('\n::error::UNITTEST_'+kind+' '+public+'\n');self.stream.flush();self.annotations+=1
    def addError(self,test,error):
        self.annotate(test,'ERROR');super().addError(test,error)
    def addFailure(self,test,error):
        self.annotate(test,'FAILURE');super().addFailure(test,error)
    def addSubTest(self,test,subtest,error):
        if error is not None:self.annotate(test,'SUBTEST_FAILURE')
        super().addSubTest(test,subtest,error)


def main():
    sys.path.insert(0,os.getcwd())
    suite=unittest.defaultTestLoader.discover('tests')
    public_ids=inventory(suite)
    def result(*args,**kwargs):return PublicResult(*args,public_ids=public_ids,**kwargs)
    outcome=unittest.TextTestRunner(verbosity=2,resultclass=result).run(suite)
    return 0 if outcome.wasSuccessful() else 1


if __name__=='__main__':raise SystemExit(main())
