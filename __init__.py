from datetime import datetime,timedelta
import asyncio
import logging
from homeassistant.core import HomeAssistant
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.event import async_track_time_interval
from .connections import drain
DOMAIN='serial_reader'
_LOGGER=logging.getLogger(__name__)

async def async_setup(hass:HomeAssistant,config:ConfigType):
    store=hass.data[DOMAIN]={'serial_ports':[],'baud_rate':115200,'connections':{},'serial_data':[],
                             'identities':{},'buffers':{},'errors':{},'_lock':asyncio.Lock()}
    stopping=False
    async def read_serial_data(_):
        if stopping or store['_lock'].locked():return
        async with store['_lock']:
            for path,conn in list(store['connections'].items()):
                try:
                    lines,partial=await asyncio.to_thread(drain,conn,store['buffers'].get(path,b''))
                    store['buffers'][path]=partial
                    for line in lines:
                        if line:store['serial_data'].append(f"[{datetime.now():%Y-%m-%d %H:%M:%S}][{path}] {line}")
                    store['serial_data']=store['serial_data'][-100:]
                except Exception as error:
                    physical=store['identities'].pop(path,path);store['errors'][physical]='Disconnected: '+str(error)
                    store['buffers'].pop(path,None);store['connections'].pop(path,None)
                    try:await asyncio.to_thread(conn.close)
                    except Exception:pass
                    store['serial_ports']=list(store['connections'])
                    _LOGGER.warning('Serial device disconnected: %s',path)
    unsubscribe=async_track_time_interval(hass,read_serial_data,timedelta(milliseconds=200))
    async def shutdown(_):
        nonlocal stopping
        stopping=True;store['_stopping']=True;unsubscribe()
        async with store['_lock']:
            for conn in store['connections'].values():
                try:await asyncio.to_thread(conn.close)
                except Exception:pass
            store['connections'].clear();store['serial_ports']=[]
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP,shutdown)
    from .api import SerialAPI
    hass.http.register_view(SerialAPI(hass))
    return True
