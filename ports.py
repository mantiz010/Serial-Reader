"""Discover serial names from the host's udev metadata and actual named links."""
import os
from pathlib import Path
import serial.tools.list_ports

def port_name(device, fallback):
    try:
        stat=os.stat(device)
        text=Path(f'/run/udev/data/c{os.major(stat.st_rdev)}:{os.minor(stat.st_rdev)}').read_text()
        props=dict(line[2:].split('=',1) for line in text.splitlines() if line.startswith('E:') and '=' in line)
        model=props.get('ID_MODEL_FROM_DATABASE') or props.get('ID_MODEL')
        if model:return model.replace('_',' ')
    except (OSError,ValueError):pass
    return fallback or device

def list_ports():
    links=[]
    root=Path('/dev/serial/by-id')
    if root.exists():
        for p in sorted(root.glob('espnow-*')):
            if p.is_symlink() and p.exists():links.append(str(p))
    details=[]
    for port in serial.tools.list_ports.comports():
        aliases=[p for p in links if os.path.realpath(p)==os.path.realpath(port.device)]
        details.append({'device':port.device,'name':port_name(port.device,port.description),
                        'preferred_path':aliases[0] if aliases else port.device,'aliases':aliases})
    return sorted(details,key=lambda p:p['device'])
