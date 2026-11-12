"""Copy explicit owner inputs and reuse lab_release; never execute a capsule."""
import argparse
import hashlib
import json
import os
from pathlib import Path

from unified_system import lab_release as release

SCHEMA='unified.collector.source-recipe.v1'
RECIPE_LIMIT=32*1024*1024
MAX_TOTAL=512*1024*1024
RECEIPT_LIMIT=32768
ROLES=frozenset(('APPLICATION_SOURCE','PYTHON_RUNTIME','DEPENDENCY','LOCK',
                 'GIT_TOOL','GIT_SUPPORT','COLLECTOR_PROFILE','SOURCE_MANIFEST'))


def need(value):
    if not value:raise ValueError('COLLECTOR_PACKAGE_REJECTED')


def exact(value,fields):need(type(value) is dict and set(value)==set(fields))


def absolute(value):
    need(isinstance(value,(str,Path)) and Path(value).is_absolute())
    return release._safe_path(value)


def disjoint(paths):
    for index,left in enumerate(paths):
        for right in paths[index+1:]:need(left!=right and left not in right.parents and right not in left.parents)


def document(path,expected_sha):
    path=release.regular(absolute(path));release.digest(expected_sha)
    need(path.stat().st_size<=RECIPE_LIMIT)
    facts=release.hash_file(path);need(facts['sha256']==expected_sha and facts['bytes']<=RECIPE_LIMIT)
    with path.open('rb') as stream:raw=stream.read(RECIPE_LIMIT+1)
    need(len(raw)==facts['bytes'] and len(raw)<=RECIPE_LIMIT and hashlib.sha256(raw).hexdigest()==expected_sha)
    def unique(pairs):
        out={}
        for key,value in pairs:need(key not in out);out[key]=value
        return out
    value=json.loads(raw.decode('utf-8'),object_pairs_hook=unique,
                     parse_constant=lambda _:need(False))
    return value,raw


def inventory(root,files,directories):
    need(root.is_dir() and type(files) is dict and 1<=len(files)<=100000)
    need(type(directories) is list and len(directories)<=100000 and directories==sorted(set(directories)))
    expected_dirs=set(directories)
    seen=set();actual_dirs=set();actual_files=set();total=0
    for name,pin in files.items():
        release.relative(name);need(name.casefold() not in seen);seen.add(name.casefold())
        exact(pin,('sha256','bytes'));release.digest(pin['sha256'])
        need(type(pin['bytes']) is int and 0<=pin['bytes']<=MAX_TOTAL);total+=pin['bytes']
    need(total<=MAX_TOTAL)
    for name in directories:
        release.relative(name);need(name.casefold() not in seen);seen.add(name.casefold())
    def walk_error(error):raise ValueError('COLLECTOR_INPUT_INVENTORY_UNREADABLE') from error
    for directory,dirs,names in os.walk(root,followlinks=False,onerror=walk_error):
        release._safe_path(directory)
        for name in dirs:
            path=release._safe_path(Path(directory)/name)
            relative=path.relative_to(root).as_posix()
            need(relative in expected_dirs and path.is_dir());actual_dirs.add(relative)
        for name in names:
            path=release.regular(Path(directory)/name);relative=path.relative_to(root).as_posix()
            need(relative in files and release.hash_file(path)==files[relative]);actual_files.add(relative)
    need(actual_files==set(files) and actual_dirs==set(directories))
    return total


def role_valid(role,name,manifest):
    locks={dep['lock_path'] for dep in manifest['dependencies']}|{manifest['runtime']['lock']['path']}
    designated={manifest['collector_profile']:'COLLECTOR_PROFILE',
                manifest['source_manifest']:'SOURCE_MANIFEST',manifest['git']:'GIT_TOOL'}
    if name in designated:return role==designated[name]
    if name in locks:return role=='LOCK'
    if role=='APPLICATION_SOURCE':return name.startswith(('sources/unified-system/','sources/grid/'))
    if role=='PYTHON_RUNTIME':return name.startswith('runtime/python/')
    if role=='DEPENDENCY':return name.startswith('dependencies/') and name not in locks
    if role=='LOCK':return name in locks
    if role=='GIT_TOOL':return name==manifest['git']
    if role=='GIT_SUPPORT':return name.startswith('tools/') and name!=manifest['git']
    if role=='COLLECTOR_PROFILE':return name==manifest['collector_profile']
    if role=='SOURCE_MANIFEST':return name==manifest['source_manifest']
    return False


def write_new(path,raw):
    with path.open('xb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())


def build_package(recipe_path,*,recipe_sha256,work_root,output_root):
    """Return hashes/non-admission receipt; preserve any incomplete new roots."""
    recipe_path=absolute(recipe_path);work=absolute(work_root);output=absolute(output_root)
    recipe,recipe_raw=document(recipe_path,recipe_sha256)
    need(release.canonical(recipe)==recipe_raw)
    exact(recipe,('schema','manifest','input_roots','members','runtime_byte_ledger','native_source_root_data','limits'))
    need(recipe['schema']==SCHEMA)
    manifest=recipe['manifest'];manifest_raw=release.canonical(manifest)
    manifest_sha=hashlib.sha256(manifest_raw).hexdigest()
    need(release.parse_manifest(manifest_raw,manifest_sha)['schema']==release.COLLECTOR_SCHEMA)
    limits=recipe['limits'];exact(limits,('unified_source_bytes','grid_source_bytes','total_bytes','max_files'))
    for key,ceiling in (('unified_source_bytes',56*1024*1024),('grid_source_bytes',3670016),
                        ('total_bytes',MAX_TOTAL),('max_files',100000)):
        need(type(limits[key]) is int and 1<=limits[key]<=ceiling)
    files=manifest['files'];need(len(files)<=limits['max_files'])
    need(len({manifest['collector_profile'],manifest['source_manifest'],manifest['git']})==3)
    lock_paths={dep['lock_path'] for dep in manifest['dependencies']}|{manifest['runtime']['lock']['path']}
    need(not {manifest['collector_profile'],manifest['source_manifest'],manifest['git']}&lock_paths)
    need(sum(pin['bytes'] for pin in files.values())<=limits['total_bytes'])
    for source,key in (('unified-system','unified_source_bytes'),('grid','grid_source_bytes')):
        need(sum(pin['bytes'] for name,pin in files.items() if name.startswith('sources/'+source+'/'))<=limits[key])
    roots=recipe['input_roots'];need(type(roots) is dict and 1<=len(roots)<=64)
    paths={};identities={}
    for key,value in roots.items():
        release.relative(key);exact(value,('path','files','directories'))
        path=absolute(value['path']);need(path.is_dir());paths[key]=path
        stat=path.stat();identities[key]=(stat.st_dev,stat.st_ino)
    disjoint([work,output,*paths.values()]);need(not work.exists() and not output.exists())
    need(work.parent.is_dir() and output.parent.is_dir())
    controls=[recipe_path]
    for field in ('runtime_byte_ledger','native_source_root_data'):
        exact(recipe[field],('path','sha256'));controls.append(absolute(recipe[field]['path']))
    for control in controls:
        need(control!=work and work not in control.parents and control!=output and output not in control.parents)
    need(all(type(value['files']) is dict and type(value['directories']) is list for value in roots.values()))
    need(sum(len(value['files']) for value in roots.values())<=limits['max_files'])
    need(sum(len(value['directories']) for value in roots.values())<=100000)
    ledger,ledger_raw=document(recipe['runtime_byte_ledger']['path'],recipe['runtime_byte_ledger']['sha256'])
    supplier,supplier_raw=document(recipe['native_source_root_data']['path'],recipe['native_source_root_data']['sha256'])
    need(type(ledger) is dict and type(ledger.get('files')) is dict and 1<=len(ledger['files'])<=100000)
    need(type(supplier) is dict)
    total_input=0
    for key,value in roots.items():
        total_input+=inventory(paths[key],value['files'],value['directories'])
    need(total_input<=limits['total_bytes'])
    members=recipe['members'];need(type(members) is dict and set(members)==set(files))
    python_member=members[manifest['runtime']['python']['path']]
    need(type(python_member) is dict and python_member.get('role')=='PYTHON_RUNTIME')
    source_members={};ledger_members=set()
    for name,member in members.items():
        role=member.get('role') if type(member) is dict else None
        exact(member,('root','relative','role','ledger_path') if role=='PYTHON_RUNTIME' else ('root','relative','role'))
        need(type(role) is str and role in ROLES and role_valid(role,name,manifest));release.relative(member['relative'])
        need(type(member['root']) is str and member['root'] in roots)
        pin=roots[member['root']]['files'].get(member['relative'])
        need(pin==files[name]);source_members[name]=paths[member['root']]/member['relative']
        if role=='PYTHON_RUNTIME':
            ledger_path=member['ledger_path'];need(type(ledger_path) is str and ledger_path not in ledger_members)
            need(ledger['files'].get(ledger_path)==pin);ledger_members.add(ledger_path)
    need(ledger_members==set(ledger['files']))
    inventory_raw=release.canonical(dict(schema='unified.collector.package-inventory.v1',files=files,
        directories=manifest['directories'],manifest_sha256=manifest_sha))
    control_bytes={path:raw for path,raw in zip(controls,(recipe_raw,ledger_raw,supplier_raw))}
    external_control_bytes=sum(len(raw) for path,raw in control_bytes.items()
        if not any(root in path.parents for root in paths.values()))
    capsule_bytes=sum(pin['bytes'] for pin in files.values())
    retained_reserved=(total_input+external_control_bytes+2*capsule_bytes+2*len(manifest_raw)
                       +len(recipe_raw)+len(inventory_raw)+RECEIPT_LIMIT)
    need(retained_reserved<=limits['total_bytes'])
    # All owner input and role/budget checks precede new output effects.
    work.mkdir(exist_ok=False);assembly=work/'capsule';assembly.mkdir()
    for directory in manifest['directories']:(assembly/directory).mkdir(parents=True,exist_ok=True)
    for name,pin in files.items():need(release.hash_file(source_members[name],copy_to=assembly/name)==pin)
    write_new(assembly/'lab-release.json',manifest_raw)
    release.verify_capsule(assembly,manifest_sha)
    for key,value in roots.items():
        stat=paths[key].stat();need((stat.st_dev,stat.st_ino)==identities[key])
        inventory(paths[key],value['files'],value['directories'])
    # Re-pin control bytes after assembly, without inventing supplier provenance.
    need(document(recipe_path,recipe_sha256)[1]==recipe_raw)
    need(document(recipe['runtime_byte_ledger']['path'],recipe['runtime_byte_ledger']['sha256'])[1]==ledger_raw)
    need(document(recipe['native_source_root_data']['path'],recipe['native_source_root_data']['sha256'])[1]==supplier_raw)
    output.mkdir(exist_ok=False)
    capsule=output/'capsule'
    verified=release.stage_capsule(assembly,capsule,manifest_sha)
    write_new(output/'source-recipe.json',recipe_raw)
    write_new(output/'file-inventory.json',inventory_raw)
    receipt=dict(schema='unified.collector.package-build-receipt.v1',capsule_root=str(capsule),
        manifest_sha256=manifest_sha,recipe_sha256=recipe_sha256,
        inventory_sha256=hashlib.sha256(inventory_raw).hexdigest(),
        runtime_byte_ledger_sha256=recipe['runtime_byte_ledger']['sha256'],
        native_source_root_data_sha256=recipe['native_source_root_data']['sha256'],
        native_supplier_provenance='EXTERNAL_NOT_ATTESTED',files_verified=verified['files_verified'],
        declared_input_bytes=total_input,
        declared_capsule_bytes=sum(pin['bytes'] for pin in files.values()),
        declared_python_runtime_bytes=sum(ledger['files'][key]['bytes'] for key in ledger_members),
        retained_logical_bytes_reserved=retained_reserved,receipt_headroom_bytes=RECEIPT_LIMIT,
        execution_authority=False,service_admission=False,physical_acceptance='NOT_RUN',
        source_provenance=verified['source_provenance'])
    receipt_raw=release.canonical(receipt);need(len(receipt_raw)<=RECEIPT_LIMIT)
    write_new(output/'build-receipt.json',receipt_raw)
    return receipt


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recipe',required=True);parser.add_argument('--recipe-sha256',required=True)
    parser.add_argument('--work-root',required=True);parser.add_argument('--output-root',required=True)
    args=parser.parse_args(argv)
    result=build_package(args.recipe,recipe_sha256=args.recipe_sha256,
                         work_root=args.work_root,output_root=args.output_root)
    print(json.dumps(result,sort_keys=True));return 0


if __name__=='__main__':raise SystemExit(main())
