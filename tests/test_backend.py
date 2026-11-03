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
        self.busy=patch.object(api,'visible_users',return_value=set());self.busy.start();self.addCleanup(self.busy.stop)
        self.open=patch.object(api,'open_port');self.factory=self.open.start()
        self.addCleanup(self.paths.stop);self.addCleanup(self.listing.stop);self.addCleanup(self.open.stop)
    async def test_get_names_without_opening(self):
        d=await self.view.get(None);self.assertEqual(d['version'],'1.2.0');self.assertEqual(d['port_details'],DETAILS)
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
        self.assertEqual(d['status'],'success');self.factory.assert_called_once_with('/dev/serial/by-id/espnow-receiver',9600);self.conn.close.assert_called_once()
    async def test_baud_change_does_not_reopen(self):
        d=await self.view.post(Request({'serial_ports':['/dev/ttyUSB4'],'baud_rate':9600}))
        self.assertEqual(d['status'],'success');self.assertEqual(self.conn.baudrate,9600);self.factory.assert_not_called()
    async def test_connect_adds_without_closing_other_port(self):
        d=await self.view.post(Request({'action':'connect','serial_ports':['/dev/serial/by-id/espnow-receiver']}))
        self.assertEqual(d['status'],'success');self.assertEqual(len(d['active_ports']),2);self.conn.close.assert_not_called()
    async def test_explicit_disconnect_closes_selected_only(self):
        other=Mock();other.baudrate=115200;self.store['connections']['/dev/ttyUSB3']=other
        d=await self.view.post(Request({'action':'disconnect','serial_ports':['/dev/serial/by-id/espnow-wifi-master']}))
        self.assertEqual(d['active_ports'],['/dev/ttyUSB3']);self.conn.close.assert_called_once();other.close.assert_not_called()
    async def test_busy_port_rejected_before_open(self):
        with patch.object(api,'visible_users',return_value={'/dev/ttyUSB3'}):
            d=await self.view.post(Request({'action':'connect','serial_ports':['/dev/ttyUSB3']}))
        self.assertEqual(d['status'],'error');self.assertIn('in use',d['message']);self.factory.assert_not_called();self.conn.close.assert_not_called()
    async def test_disconnected_device_can_still_be_closed(self):
        with patch.object(api,'list_ports',return_value=[]):
            d=await self.view.post(Request({'action':'disconnect','serial_ports':['/dev/ttyUSB4']}))
        self.assertEqual(d['status'],'success');self.assertEqual(d['active_ports'],[])
    async def test_unknown_action_never_opens(self):
        d=await self.view.post(Request({'action':'restart','serial_ports':['/dev/ttyUSB3']}))
        self.assertEqual(d['status'],'error');self.factory.assert_not_called()

class SerialOperations(unittest.TestCase):
    def test_partial_lines_and_utf8_are_preserved(self):
        from serial_reader.connections import drain
        c=Mock();c.in_waiting=6;c.read.return_value=b'hi \xe2\x82'
        lines,tail=drain(c,b'');self.assertEqual(lines,[])
        c.read.return_value=b'\xac\n';lines,tail=drain(c,tail);self.assertEqual(lines,['hi \u20ac']);self.assertEqual(tail,b'')
    def test_long_line_is_bounded(self):
        from serial_reader.connections import drain
        c=Mock();c.in_waiting=100000;c.read.return_value=b'x'*4096
        lines,tail=drain(c,b'x'*8000);c.read.assert_called_once_with(4096);self.assertEqual(tail,b'');self.assertIn('[line truncated]',lines[0])
    def test_visible_open_is_detected_without_opening_again(self):
        import os,pty
        from serial_reader.connections import visible_users
        master,slave=pty.openpty();path=os.ttyname(slave)
        try:
            self.assertIn(path,visible_users([{'device':path}],{}))
            own=Mock();own.fileno.return_value=slave
            self.assertNotIn(path,visible_users([{'device':path}],{path:own}))
        finally:os.close(master);os.close(slave)
    def test_kernel_exclusive_lock_using_virtual_terminal(self):
        import os,pty,serial
        from serial_reader.connections import open_port
        master,slave=pty.openpty();path=os.ttyname(slave);first=serial.Serial(path,exclusive=True)
        try:
            with self.assertRaises(serial.SerialException):open_port(path,115200)
        finally:first.close();os.close(master);os.close(slave)

class ReaderLifecycle(unittest.IsolatedAsyncioTestCase):
    async def test_read_failure_drops_connection_without_reconnect(self):
        import serial_reader.connections as ops
        core=types.ModuleType('homeassistant.core');core.HomeAssistant=object
        const=types.ModuleType('homeassistant.const');const.EVENT_HOMEASSISTANT_STOP='stop'
        helpers=types.ModuleType('homeassistant.helpers');typing=types.ModuleType('homeassistant.helpers.typing');typing.ConfigType=dict
        event=types.ModuleType('homeassistant.helpers.event');callbacks={};unsubscribe=Mock()
        event.async_track_time_interval=lambda h,cb,interval:(callbacks.update(read=cb) or unsubscribe)
        modules={'homeassistant.core':core,'homeassistant.const':const,'homeassistant.helpers':helpers,'homeassistant.helpers.typing':typing,'homeassistant.helpers.event':event}
        runtime=types.ModuleType('serial_reader.runtime');runtime.__package__='serial_reader'
        with patch.dict(sys.modules,modules):
            exec(compile((ROOT/'__init__.py').read_text(),'__init__.py','exec'),runtime.__dict__)
            hass=types.SimpleNamespace(data={},http=Mock(),bus=Mock())
            await runtime.async_setup(hass,{})
            store=hass.data['serial_reader'];bad=Mock();bad.in_waiting=1;bad.read.side_effect=OSError('USB removed');store['connections']['/dev/mock']=bad
            with patch.object(api,'open_port') as opening:
                await callbacks['read'](None);await callbacks['read'](None);opening.assert_not_called()
            self.assertEqual(store['connections'],{});self.assertIn('USB removed',store['errors']['/dev/mock']);bad.close.assert_called_once()
            good=Mock();store['connections']['/dev/other']=good
            await hass.bus.async_listen_once.call_args.args[1](None)
            good.close.assert_called_once();unsubscribe.assert_called_once();self.assertTrue(store['_stopping'])

if __name__=='__main__':unittest.main()
