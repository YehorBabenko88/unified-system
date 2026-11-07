"""Owned bounded loopback-only real Consul test fixture; never a service installer."""
import hashlib,json,os,socket,subprocess,time,urllib.request,urllib.error,sys
from pathlib import Path

BINARY_SHA={'win32':'41762ef5b98c8dd9b6852df6cfbceed37e7f0acc5760856be33100f1092475e1','linux':'acb0a1b5b2a22a5fadb5d725f03610335e499e193eeade9df458c6c6017a77f4'}
class ConsulLab:
    def __init__(self,binary,scratch):
        self.binary=Path(binary).resolve();self.scratch=Path(scratch).resolve()
        if hashlib.sha256(self.binary.read_bytes()).hexdigest()!=BINARY_SHA.get(sys.platform):raise ValueError('BINARY_PIN')
        self.processes=[];self.logs=[];self.nodes=[]
    def __enter__(self):
        self.scratch.mkdir(parents=True,exist_ok=False)
        sockets=[]
        try:
            for _ in range(12):
                s=socket.socket();s.bind(('127.0.0.1',0));sockets.append(s)
            ports=[s.getsockname()[1] for s in sockets]
        finally:
            for s in sockets:s.close()
        try:
            for i in range(3):
                rpc,lan,wan,http=ports[i*4:i*4+4]
                folder=self.scratch/str(i);folder.mkdir()
                config=dict(server=True,bootstrap_expect=3,datacenter='a2-mux-lab',node_name='a2-mux-'+str(i),
                    data_dir=str(folder/'data'),bind_addr='127.0.0.1',advertise_addr='127.0.0.1',client_addr='127.0.0.1',
                    ports=dict(server=rpc,serf_lan=lan,serf_wan=wan,http=http,https=-1,dns=-1,grpc=-1,grpc_tls=-1),
                    retry_join=['127.0.0.1:'+str(ports[j*4+1]) for j in range(3) if j!=i],
                    disable_update_check=True,disable_remote_exec=True,enable_script_checks=False,
                    leave_on_terminate=False,skip_leave_on_interrupt=True,log_level='warn',
                    performance=dict(raft_multiplier=1),connect=dict(enabled=False),raft_logstore=dict(backend='boltdb'))
                path=folder/'config.json';path.write_bytes(json.dumps(config).encode())
                log=(folder/'consul.log').open('ab');self.logs.append(log)
                env=os.environ.copy();env['CHECKPOINT_DISABLE']='1'
                proc=subprocess.Popen([str(self.binary),'agent','-config-file',str(path)],stdout=log,stderr=subprocess.STDOUT,
                    env=env,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                self.processes.append(proc);self.nodes.append('http://127.0.0.1:'+str(http))
            deadline=time.monotonic()+45
            while time.monotonic()<deadline:
                if any(p.poll() is not None for p in self.processes):raise RuntimeError('OWNED_CONSUL_EXITED')
                try:
                    for endpoint in self.nodes:
                        _,raw=self.request(endpoint,'GET','/v1/operator/raft/configuration?consistent')
                        voters=json.loads(raw)['Servers']
                        assert len(voters)==3 and all(v['Voter'] for v in voters) and sum(v['Leader'] for v in voters)==1
                    return self
                except (OSError,ValueError,KeyError,AssertionError):time.sleep(.2)
            raise RuntimeError('OWNED_CONSUL_QUORUM_TIMEOUT')
        except BaseException:
            self.__exit__(None,None,None);raise
    @staticmethod
    def request(endpoint,method,path,data=None):
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        request=urllib.request.Request(endpoint+path,data=data,method=method,headers={'Content-Type':'application/json'})
        try:
            with opener.open(request,timeout=2) as r:return r.status,r.read(4*1024*1024)
        except urllib.error.HTTPError as e:return e.code,e.read(4*1024*1024)
    def __exit__(self,*args):
        # Popen owns handles to exact created process objects; never enumerate/kill names or foreign PIDs.
        for p in self.processes:
            if p.poll() is None:p.kill()
        for p in self.processes:p.wait(timeout=10)
        for log in self.logs:log.close()
