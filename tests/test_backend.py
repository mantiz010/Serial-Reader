"""Exercise the actual API with fake serial connections; never touch hardware."""
import asyncio,importlib.util,sys,types,unittest
from pathlib import Path
from unittest.mock import patch,Mock
ROOT=Path(__file__).resolve().parents[1]
http=types.ModuleType('homeassistant.components.http')
class View:
    @staticmethod
    def json(data):return data
http.HomeAssistantView=View
for name in ['homeassistant','homeassistant.components']:
    sys.modules.setdefault(name,types.ModuleType(name))
sys.modules['homeassistant.components.http']=http
package=types.ModuleType('serial_reader');package.__path__=[str(ROOT)];sys.modules['serial_reader']=package
from serial_reader import api
DETAILS=[{'device':'/dev/ttyUSB4','name':'ESP-NOW Wi-Fi Master','preferred_path':'/dev/serial/by-id/espnow-wifi-master','aliases':['/dev/serial/by-id/espnow-wifi-master']},
 {'device':'/dev/ttyUSB3','name':'ESP-NOW Receiver','preferred_path':'/dev/serial/by-id/espnow-receiver','aliases':['/dev/serial/by-id/espnow-receiver']}]
def physical(path):return {'/dev/serial/by-id/espnow-wifi-master':'/dev/ttyUSB4','/dev/serial/by-id/espnow-receiver':'/dev/ttyUSB3'}.get(path,path)
class Request:
    def __init__(self,data):self.data=data
    async def json(self):return self.data
class Tests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.conn=Mock();self.conn.baudrate=115200
        self.store={'connections':{'/dev/ttyUSB4':self.conn},'serial_data':[],'baud_rate':115200}
        self.view=api.SerialAPI(types.SimpleNamespace(data={'serial_reader':self.store}))
        self.paths=patch.object(api.os.path,'realpath',physical);self.paths.start()
        self.listing=patch.object(api,'list_ports',return_value=DETAILS);self.listing.start()
        self.open=patch.object(api.serial,'Serial');self.factory=self.open.start()
        self.addCleanup(self.paths.stop);self.addCleanup(self.listing.stop);self.addCleanup(self.open.stop)
    async def test_get_names_without_opening(self):
        d=await self.view.get(None);self.assertEqual(d['version'],'1.1.0');self.assertEqual(d['port_details'],DETAILS)
        self.assertEqual(d['active_port_details'][0]['name'],'ESP-NOW Wi-Fi Master');self.factory.assert_not_called();self.conn.close.assert_not_called()
    async def test_alias_keeps_existing_connection(self):
        d=await self.view.post(Request({'serial_ports':['/dev/serial/by-id/espnow-wifi-master'],'baud_rate':115200}))
        self.assertEqual(d['status'],'success');self.factory.assert_not_called();self.conn.close.assert_not_called()
    async def test_duplicate_alias_not_opened_twice(self):
        d=await self.view.post(Request({'serial_ports':['/dev/ttyUSB4','/dev/serial/by-id/espnow-wifi-master']}))
        self.assertEqual(len(d['active_ports']),1);self.factory.assert_not_called()
    async def test_command_uses_existing_alias_identity(self):
        d=await self.view.post(Request({'serial_ports':['/dev/serial/by-id/espnow-wifi-master'],'command':'status'}))
        self.assertEqual(d['status'],'success');self.conn.write.assert_called_once_with(b'status\n');self.factory.assert_not_called()
    async def test_command_to_closed_port_never_opens_it(self):
        d=await self.view.post(Request({'serial_ports':['/dev/ttyUSB3'],'command':'status'}))
        self.assertEqual(d['status'],'error');self.factory.assert_not_called();self.conn.close.assert_not_called()
    async def test_missing_alias_preserves_connection(self):
        d=await self.view.post(Request({'serial_ports':['/dev/serial/by-id/missing']}))
        self.assertEqual(d['status'],'error');self.factory.assert_not_called();self.conn.close.assert_not_called()
    async def test_failed_open_keeps_existing_port(self):
        self.factory.side_effect=OSError('Unavailable')
        d=await self.view.post(Request({'serial_ports':['/dev/ttyUSB3']}))
        self.assertEqual(d['status'],'error');self.conn.close.assert_not_called();self.assertIn('/dev/ttyUSB4',self.store['connections'])
    async def test_new_alias_is_actual_open_path(self):
        d=await self.view.post(Request({'serial_ports':['/dev/serial/by-id/espnow-receiver'],'baud_rate':9600}))
        self.assertEqual(d['status'],'success');self.factory.assert_called_once_with('/dev/serial/by-id/espnow-receiver',9600,timeout=1);self.conn.close.assert_called_once()
    async def test_baud_change_does_not_reopen(self):
        d=await self.view.post(Request({'serial_ports':['/dev/ttyUSB4'],'baud_rate':9600}))
        self.assertEqual(d['status'],'success');self.assertEqual(self.conn.baudrate,9600);self.factory.assert_not_called()
if __name__=='__main__':unittest.main()
