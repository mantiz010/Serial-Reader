import asyncio
import os
import serial
from homeassistant.components.http import HomeAssistantView
from .ports import list_ports
DOMAIN='serial_reader'
DEFAULT_BAUD_RATE=115200

class SerialAPI(HomeAssistantView):
    """Serial API with discovered device names and identity-aware path handling."""
    url='/api/serial_reader'
    name='api:serial_reader'
    requires_auth=False  # Preserve existing standalone viewer compatibility.
    def __init__(self,hass):
        self.hass=hass
        self.lock=asyncio.Lock()
    async def get(self,request):
        details=await asyncio.to_thread(list_ports)
        connections=self.hass.data[DOMAIN]['connections']
        by_device={os.path.realpath(p['device']):p for p in details}
        active=[{'path':path,**by_device.get(os.path.realpath(path),{'device':path,'name':path,'preferred_path':path,'aliases':[]})} for path in connections]
        return self.json({'version':'1.1.0','available_ports':[p['device'] for p in details],
                          'port_details':details,'active_ports':list(connections),
                          'active_port_details':active,'serial_data':self.hass.data[DOMAIN].get('serial_data',[])[-100:]})
    async def post(self,request):
        async with self.lock:
            try:
                body=await request.json()
                paths=body.get('serial_ports',[])
                if not isinstance(paths,list) or any(not isinstance(p,str) for p in paths):raise ValueError('serial_ports must be a list of device paths')
                details=await asyncio.to_thread(list_ports)
                allowed={path for p in details for path in [p['device'],*p['aliases']]}
                if any(p not in allowed for p in paths):raise ValueError('Selected serial device is not currently available')
                requested={}
                for path in paths:requested.setdefault(os.path.realpath(path),path)
                store=self.hass.data[DOMAIN];connections=store['connections']
                existing={os.path.realpath(path):path for path in connections}
                command=body.get('command')
                if command is not None:
                    if not isinstance(command,str) or not command or not paths:raise ValueError('Choose an open port and a non-empty command')
                    key=existing.get(os.path.realpath(paths[0]))
                    if key is None:raise ValueError('Selected port is not open; press Start first')
                    await asyncio.to_thread(connections[key].write,(command+'\n').encode('utf-8'))
                    return self.json({'status':'success','message':'Command sent to '+paths[0]})
                baud=body.get('baud_rate',store.get('baud_rate',DEFAULT_BAUD_RATE))
                if not isinstance(baud,int) or isinstance(baud,bool) or not 1<=baud<=4000000:raise ValueError('Invalid baud rate')
                opened={}
                try:
                    for physical,path in requested.items():
                        if physical not in existing:opened[path]=await asyncio.to_thread(serial.Serial,path,baud,timeout=1)
                except Exception:
                    for conn in opened.values():await asyncio.to_thread(conn.close)
                    raise
                # Switching between ttyUSB and its alias keeps the same connection.
                for physical,path in existing.items():
                    if physical not in requested:
                        await asyncio.to_thread(connections[path].close);del connections[path]
                    elif connections[path].baudrate!=baud:
                        await asyncio.to_thread(setattr,connections[path],'baudrate',baud)
                connections.update(opened)
                store['serial_ports']=list(connections);store['baud_rate']=baud
                return self.json({'status':'success','active_ports':list(connections)})
            except Exception as error:
                return self.json({'status':'error','message':str(error)})
