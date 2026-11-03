"""Bounded serial operations, executed in worker threads only."""
import os
from pathlib import Path
import serial

def visible_users(details, connections):
    """Find other opens visible in this process namespace, without opening a port."""
    devices={}
    for item in details:
        try:devices[os.stat(item['device']).st_rdev]=item['device']
        except OSError:pass
    owned=set()
    for conn in connections.values():
        try:owned.add((str(os.getpid()),str(conn.fileno())))
        except (OSError,ValueError,AttributeError):pass
    busy=set()
    for proc in Path('/proc').glob('[0-9]*'):
        try:fds=list((proc/'fd').iterdir())
        except OSError:continue
        for fd in fds:
            if (proc.name,fd.name) in owned:continue
            try:
                device=devices.get(fd.stat().st_rdev)
                if device:busy.add(device)
            except OSError:pass
    return busy

def open_port(path,baud):
    conn=serial.Serial(port=None,baudrate=baud,timeout=0,write_timeout=1,exclusive=True)
    conn.dtr=False
    conn.rts=False
    conn.port=path
    try:conn.open()
    except BaseException:
        conn.close()
        raise
    return conn

def drain(conn,partial):
    chunk=conn.read(min(conn.in_waiting,4096))
    parts=(partial+chunk).split(b'\n');tail=parts.pop();lines=[]
    for line in parts:lines.append(line[:8192].decode('utf-8',errors='replace').rstrip('\r'))
    if len(tail)>8192:lines.append(tail[:8192].decode('utf-8',errors='replace')+' [line truncated]');tail=b''
    return lines,tail
