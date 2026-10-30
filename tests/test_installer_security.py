import copy
import hashlib
import unittest
from unified_system.installer_security import build_security_plan, validate_package_lock, REQUIRED


def fixture():
    artifacts, payload = [], {}
    for name in sorted(REQUIRED):
        data = name.encode(); path = name + ".bin"; payload[path] = data
        artifacts.append(dict(path=path, dependency=name, version="18.1" if name == "postgresql" else "1.0",
                              publisher_sha256="a"*64, sha256=hashlib.sha256(data).hexdigest(), bytes=len(data)))
    lock = dict(schema="unified.windows-package-lock.v1", identity_sid="S-1-5-21-100",
                sources={k: dict(commit="a"*40, tree="b"*40) for k in ("grid","strattester","unified","terminan","math")},
                requirements=dict(powershell="5.1,7", postgresql_major=18), artifacts=artifacts)
    return lock, payload


def node(n):
    return dict(id="node"+str(n), identity_sid="S-1-5-21-"+str(100+n), installed={},
                **{k: True for k in ("identity_verified","publisher_pin_verified","path_verified","no_reparse","acl_protected","operator_approved")})


class SecurityPlanTests(unittest.TestCase):
    def test_fleet_boundaries_immutability_and_no_authority(self):
        lock, payload = fixture()
        for count in (0,1,5,6,7,64):
            nodes = [node(n) for n in range(count)]; before = copy.deepcopy((lock,payload,nodes))
            plan = build_security_plan(lock,payload,nodes)
            self.assertEqual(len(plan["nodes"]), count)
            self.assertEqual(plan["admission"], "NOT_GRANTED")
            self.assertEqual(plan["source_provenance"], "NOT_EVALUATED")
            self.assertEqual(plan["production"], "NO_GO")
            self.assertFalse(plan["mutations_performed"])
            self.assertEqual(before, (lock,payload,nodes))
        with self.assertRaises(ValueError): build_security_plan(lock,payload,[node(n) for n in range(65)])

    def test_each_security_observation_missing_false_string_is_blocked(self):
        lock,payload=fixture()
        for field in ("identity_verified","publisher_pin_verified","path_verified","no_reparse","acl_protected","operator_approved"):
            for value in (False,None,"true",1):
                n=node(1); n[field]=value
                self.assertIn(field,build_security_plan(lock,payload,[n])["nodes"][0]["blockers"])

    def test_deltas_and_rollback(self):
        lock,payload=fixture(); n=node(1)
        n["installed"]={a["dependency"]:a["sha256"] for a in lock["artifacts"]}
        self.assertEqual(build_security_plan(lock,payload,[n])["nodes"][0]["deltas"],[])
        n["installed"]["tailscale"]="f"*64
        delta=build_security_plan(lock,payload,[n])["nodes"][0]["deltas"]
        self.assertEqual(len(delta),1); self.assertIn("OPERATOR_APPROVAL",delta[0]["rollback"])

    def test_untrusted_paths_digests_versions_inventory_and_sizes(self):
        for field,bad in [("path","../x"),("path","C:/x"),("path","CON.txt"),("path","x:ads"),("path","x."),
                          ("sha256","a"*63),("publisher_sha256","x"*64),("bytes",True),("bytes",0),("bytes",2**30),
                          ("version","")]:
            lock,payload=fixture(); lock["artifacts"][0][field]=bad
            with self.subTest(field=field,bad=bad), self.assertRaises(ValueError): validate_package_lock(lock,payload)
        lock,payload=fixture(); payload[next(iter(payload))]=b"tampered"
        with self.assertRaises(ValueError): validate_package_lock(lock,payload)
        lock,payload=fixture(); lock["artifacts"].pop()
        with self.assertRaises(ValueError): validate_package_lock(lock,payload)
        lock,payload=fixture(); lock["requirements"]["postgresql_major"]=17
        with self.assertRaises(ValueError): validate_package_lock(lock,payload)
        lock,payload=fixture(); lock["sources"]["grid"]["commit"]="latest"
        with self.assertRaises(ValueError): validate_package_lock(lock,payload)
        lock,payload=fixture(); next(a for a in lock["artifacts"] if a["dependency"]=="postgresql")["version"]="17.9"
        with self.assertRaises(ValueError): validate_package_lock(lock,payload)

    def test_identity_collision_invalid_input_and_no_secret_output(self):
        lock,payload=fixture()
        for nodes in ([node(1),node(1)],[dict(node(1),identity_sid="admin")],[dict(node(1),installed={"secret":"token"})]):
            with self.assertRaises(ValueError): build_security_plan(lock,payload,nodes)
        self.assertFalse(build_security_plan(lock,payload,[node(1)])["secrets_collected"])

    def test_all_five_sources_required_and_pg_major_is_integer(self):
        for name in ("grid", "strattester", "unified", "terminan", "math"):
            lock, payload = fixture()
            del lock["sources"][name]
            with self.subTest(missing=name), self.assertRaises(ValueError):
                validate_package_lock(lock, payload)
        for value in (18.0, True, "18"):
            lock, payload = fixture()
            lock["requirements"]["postgresql_major"] = value
            with self.subTest(pg=value), self.assertRaises(ValueError):
                validate_package_lock(lock, payload)
