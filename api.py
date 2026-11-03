import asyncio
import os
from homeassistant.components.http import HomeAssistantView
from .ports import list_ports
from .connections import open_port,visible_users
DOMAIN='serial_reader'
DEFAULT_BAUD_RATE=115200
VERSION='1.2.0'

class SerialAPI(HomeAssistantView):
    url='/api/serial_reader'
    name='api:serial_reader'
    requires_auth=False  # Existing standalone viewer compatibility.
    def __init__(self,hass):
        self.hass=hass
        self.lock=hass.data[DOMAIN].setdefault('_lock',asyncio.Lock())
        for key in ['identities','buffers','errors']:hass.data[DOMAIN].setdefault(key,{})
    def identity(self,path):
        return self.hass.data[DOMAIN]['identities'].get(path,os.path.realpath(path))
    async def get(self,request):
        details=await asyncio.to_thread(list_ports)
        async with self.lock:
            store=self.hass.data[DOMAIN];connections=store['connections']
            busy=await asyncio.to_thread(visible_users,details,connections)
            by_device={os.path.realpath(p['device']):p for p in details}
            active=[]
            for path,conn in connections.items():
                item=by_device.get(self.identity(path),{'device':path,'name':path,'preferred_path':path,'aliases':[]})
                active.append({'path':path,**item,'baud_rate':conn.baudrate})
            owned={self.identity(p) for p in connections}
            for item in details:
                item['status']='connected' if os.path.realpath(item['device']) in owned else 'busy' if item['device'] in busy else 'disconnected'
                item['last_error']=store['errors'].get(os.path.realpath(item['device']), '')
            return self.json({'version':VERSION,'capabilities':['connection_actions','exclusive_open','stable_paths'],'available_ports':[p['device'] for p in details],
                'port_details':details,'active_ports':list(connections),'active_port_details':active,
                'serial_data':list(store.get('serial_data',[])[-100:]),
                'protection':'Visible port owners checked; POSIX exclusive locking is required on Connect. Other applications must honour serial locks.'})
    async def post(self,request):
        try:body=await request.json()
        except Exception:return self.json({'status':'error','message':'Invalid JSON request'})
        # A disconnected browser must not leave a worker opening an untracked port.
        return await asyncio.shield(self.mutate(body))
    async def mutate(self,body):
        async with self.lock:
            opened={}
            try:
                if self.hass.data[DOMAIN].get('_stopping'):raise ValueError('Serial Reader is shutting down')
                if not isinstance(body,dict):raise ValueError('Expected a JSON object')
                paths=body.get('serial_ports',[])
                if not isinstance(paths,list) or any(not isinstance(p,str) for p in paths):raise ValueError('serial_ports must be a list of paths')
                store=self.hass.data[DOMAIN];connections=store['connections'];existing={self.identity(p):p for p in connections}
                action=body.get('action','command' if 'command' in body else 'replace')
                if action not in ['connect','disconnect','command','replace']:raise ValueError('Unknown action')
                if action in ['connect','disconnect','command'] and len(paths)!=1:raise ValueError('Select exactly one device')
                details=await asyncio.to_thread(list_ports)
                allowed={p for item in details for p in [item['device'],*item['aliases']]}|set(connections)
                if any(p not in allowed for p in paths):raise ValueError('Selected device is unavailable')
                requested={}
                for path in paths:requested.setdefault(self.identity(path),path)
                if action=='disconnect':
                    for physical in requested:
                        key=existing.get(physical)
                        if key is not None:
                            await asyncio.to_thread(connections[key].close);del connections[key]
                            store['identities'].pop(key,None);store['buffers'].pop(key,None)
                elif action=='command':
                    key=existing.get(self.identity(paths[0]));command=body.get('command')
                    if key is None:raise ValueError('Device is disconnected; press Connect first')
                    if not isinstance(command,str) or not command or len(command)>4096:raise ValueError('Enter a command up to 4096 characters')
                    await asyncio.to_thread(connections[key].write,(command+'\n').encode('utf-8'))
                else:
                    baud=body.get('baud_rate',store.get('baud_rate',DEFAULT_BAUD_RATE))
                    if not isinstance(baud,int) or isinstance(baud,bool) or not 1<=baud<=4000000:raise ValueError('Invalid baud rate')
                    busy=await asyncio.to_thread(visible_users,details,connections)
                    for physical,path in requested.items():
                        if physical not in existing:
                            if physical in busy:raise ValueError('Port in use by another reader or application')
                            opened[path]=await asyncio.to_thread(open_port,path,baud)
                    for physical,path in existing.items():
                        if action=='replace' and physical not in requested:
                            await asyncio.to_thread(connections[path].close);del connections[path]
                            store['identities'].pop(path,None);store['buffers'].pop(path,None)
                        elif physical in requested and connections[path].baudrate!=baud:
                            await asyncio.to_thread(setattr,connections[path],'baudrate',baud)
                    connections.update(opened)
                    for path in opened:store['identities'][path]=os.path.realpath(path)
                    for physical in requested:store['errors'].pop(physical,None)
                    store['baud_rate']=baud
                store['serial_ports']=list(connections)
                return self.json({'status':'success','active_ports':list(connections)})
            except Exception as error:
                for path,conn in opened.items():
                    if path not in self.hass.data[DOMAIN]['connections']:await asyncio.to_thread(conn.close)
                return self.json({'status':'error','message':str(error)})
