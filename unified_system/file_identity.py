"""Stable read-only file identity, shared by offline artifact validators.

Windows path stat exposes legacy creation-time ctime while descriptor fstat can
expose change-time ctime. Never compare those unlike representations. Query the
same authoritative Win32 structures for both descriptor and fresh pathname
handles instead. This does not authenticate publishers or admit any artifact.
"""
import os
import stat
from pathlib import Path
from .owned_python import reject_external_namespace
from .runtime_process import _safe_path


class FileIdentityError(ValueError):pass


def _need(ok):
    if not ok:raise FileIdentityError('FILE_IDENTITY_UNVERIFIED')


def _posix_identity(value):
    _need(stat.S_ISREG(value.st_mode) and value.st_nlink==1 and value.st_size>=0)
    return (value.st_dev,value.st_ino,value.st_nlink,value.st_size,value.st_mtime_ns,value.st_ctime_ns)


class _WindowsAPI:
    def __init__(self):
        import ctypes
        import msvcrt
        self.ctypes=ctypes;self.msvcrt=msvcrt
        class Basic(ctypes.Structure):
            _fields_=[('creation',ctypes.c_int64),('access',ctypes.c_int64),('write',ctypes.c_int64),('change',ctypes.c_int64),('attributes',ctypes.c_uint32)]
        class Standard(ctypes.Structure):
            _fields_=[('allocation',ctypes.c_int64),('size',ctypes.c_int64),('links',ctypes.c_uint32),('delete_pending',ctypes.c_ubyte),('directory',ctypes.c_ubyte)]
        class FileId(ctypes.Structure):
            _fields_=[('volume',ctypes.c_uint64),('identifier',ctypes.c_ubyte*16)]
        self.Basic=Basic;self.Standard=Standard;self.FileId=FileId
        kernel=ctypes.WinDLL('kernel32',use_last_error=True);self.kernel=kernel
        kernel.CreateFileW.argtypes=[ctypes.c_wchar_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p]
        kernel.CreateFileW.restype=ctypes.c_void_p
        kernel.GetFileInformationByHandleEx.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_uint32]
        kernel.GetFileInformationByHandleEx.restype=ctypes.c_int
        kernel.GetFileType.argtypes=[ctypes.c_void_p];kernel.GetFileType.restype=ctypes.c_uint32
        kernel.CloseHandle.argtypes=[ctypes.c_void_p];kernel.CloseHandle.restype=ctypes.c_int
    def handle_from_fd(self,fd):
        handle=self.msvcrt.get_osfhandle(fd);_need(handle!=-1);return handle
    def open_path(self,path,access,sharing,flags):
        handle=self.kernel.CreateFileW(path,access,sharing,None,3,flags,None)  # OPEN_EXISTING
        if handle is None or handle==self.ctypes.c_void_p(-1).value:
            # Preserve the existing missing-artifact classification without
            # treating access, sharing, or other native failures as absence.
            error=self.ctypes.get_last_error()
            if error in (2,3):raise FileNotFoundError('FILE_IDENTITY_MISSING')
            raise FileIdentityError('FILE_IDENTITY_UNVERIFIED')
        return handle
    def query(self,handle):
        basic=self.Basic();standard=self.Standard();identifier=self.FileId()
        for kind,record in ((0,basic),(1,standard),(18,identifier)):
            _need(self.kernel.GetFileInformationByHandleEx(handle,kind,self.ctypes.byref(record),self.ctypes.sizeof(record)))
        return dict(file_type=int(self.kernel.GetFileType(handle)),volume=int(identifier.volume),file_id=bytes(identifier.identifier),
                    links=int(standard.links),size=int(standard.size),creation=int(basic.creation),write=int(basic.write),
                    change=int(basic.change),attributes=int(basic.attributes),directory=bool(standard.directory),delete_pending=bool(standard.delete_pending))
    def close(self,handle):
        _need(self.kernel.CloseHandle(handle))


def _windows_stamp(api,handle):
    value=api.query(handle)
    _need(value['file_type']==1 and value['links']==1 and not value['directory'] and not value['delete_pending'])
    _need(value['volume']>0 and type(value['file_id']) is bytes and len(value['file_id'])==16 and any(value['file_id']))
    _need(value['size']>=0 and not value['attributes']&0x410)  # no reparse point or directory
    _need(all(value[name]>=0 for name in ('creation','write','change')))
    return (value['volume'],value['file_id'],value['links'],value['size'],value['creation'],value['write'],value['change'],value['attributes'])


def _windows_descriptor_identity(fd,*,api=None):
    api=_WindowsAPI() if api is None else api
    # Borrow the CRT descriptor's underlying handle; its stream owns closure.
    return _windows_stamp(api,api.handle_from_fd(fd))


def _windows_path_identity(path,*,api=None):
    reject_external_namespace(str(path));_need(Path(path).is_absolute())
    path=_safe_path(path)
    api=_WindowsAPI() if api is None else api
    # No application file data or descendant namespace is followed by this open.
    handle=api.open_path(str(path),access=0x80,sharing=7,flags=0x00200000|0x02000000)
    try:return _windows_stamp(api,handle)
    finally:api.close(handle)


def descriptor_identity(fd):
    return _windows_descriptor_identity(fd) if os.name=='nt' else _posix_identity(os.fstat(fd))


def path_identity(path):
    if os.name=='nt':return _windows_path_identity(path)
    return _posix_identity(Path(path).lstat())
