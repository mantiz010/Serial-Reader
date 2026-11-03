# Serial Reader for Home Assistant

Serial Reader **1.2.0** monitors USB serial devices, shows their names and connection state, and sends commands only when you explicitly request them.

## Controls

- **Connect** opens the selected device at the chosen baud rate. Other connected devices stay connected.
- **Disconnect** closes the selected device and releases its serial handle.
- **Pause Display / Resume Display** freezes or resumes the visible log. Reading and connection-status updates continue.
- **Send Command** is enabled only for a connected selected device. Commands end with a newline.

Loading or refreshing the viewer never opens a port or sends a command. The viewer recognises connections already owned by Serial Reader. Lost devices are closed and reported; reconnecting requires another explicit Connect. Home Assistant shutdown closes the owned handles, and startup does not reopen them.

Logs are timestamped and labelled by connection path. The viewer shows the selected device's lines from the backend's last 100 lines. Partial UTF-8 lines are retained until completed; overlong lines are bounded and truncated. This is a live monitor, not permanent log storage.

## Names and stable paths

This installation identifies:

| Current port | Device | Preferred path |
|---|---|---|
| `/dev/ttyUSB3` | ESP-NOW Receiver | `/dev/serial/by-id/espnow-receiver` |
| `/dev/ttyUSB4` | ESP-NOW Wi-Fi Master | `/dev/serial/by-id/espnow-wifi-master` |
| `/dev/ttyACM0` | SMS Text Gateway | `/dev/serial/by-id/sms-text-gateway` |
| `/dev/ttyACM1` | Bresser 6-in-1 Weather Receiver | `/dev/serial/by-id/bresser-weather-receiver` |

Names come from the host udev database. All named by-id links are discovered, and standard USB by-id links are used only when their serial identity is unique among attached ports. Ambiguous generic links are excluded. Changing between an alias and a raw path for the same open device reuses its connection instead of resetting it.

`host_rules/` records this installation's naming rules. They contain device-specific USB IDs and hub paths; adapt them for other hardware. The ESP-NOW boards share a generic USB identity, so keep them in their assigned hub sockets. SMS and Bresser have distinct USB serial numbers, so their labels follow the boards if sockets change. Rules belong in HA OS's persistent `/etc/udev/rules.d`; validate before reloading, and apply metadata-change events only to the affected devices. Existing tty nodes and USB serial IDs are retained.

## Port protection and limits

Before opening a device, Serial Reader checks other open handles visible in the Core process namespace. It also requires POSIX exclusive serial locking. A busy or failed replacement connection leaves existing connections intact. Read, write, open and close operations run outside Home Assistant's main event loop under a shared lock. Reads are nonblocking and limited to 4096 bytes per poll; writes have a bounded timeout.

**Other containers' processes may not be visible, and applications that ignore advisory locks cannot be guaranteed blocked.** The viewer does not label a port definitely free. See the [pySerial exclusive-access documentation](https://pyserial.readthedocs.io/en/latest/pyserial_api.html).

RTS/DTR are configured inactive before opening, but some USB drivers can still glitch these lines. Opening a USB board can reset it. No device reset or serial command is used to test discovery or naming.

## Install or update

Copy these files into `config/custom_components/serial_reader/`:

```text
__init__.py
api.py
connections.py
ports.py
sensor.py
const.py
manifest.json
```

Add the integration to `configuration.yaml` if it is not already present:

```yaml
serial_reader:
```

Copy `serial_ports.html` and `serial_reader_logo.png` into `config/www/`. Validate the Home Assistant configuration, then restart Home Assistant Core once to load Python changes. A VM or host reboot is unnecessary. After restarting, select the device and press Connect to begin reading.

The page is served at `/local/serial_ports.html`. Home Assistant caches `/local` files for a month, so **update the iframe URL whenever the HTML changes**, for example:

```yaml
type: iframe
url: /local/serial_ports.html?v=1.2.0
```

The installed sidebar deployment uses the HTML's SHA256 prefix as `v`. Always verify the actual sidebar iframe, not only a fresh direct link. Frontend-only updates require a new URL version and page refresh, not a Core restart.

## API

`GET /api/serial_reader` returns `version`, `capabilities`, `port_details`, `active_port_details` and the existing `available_ports`, `active_ports`, `serial_data` fields. It never opens ports. Device metadata includes names, preferred paths, aliases, connection status and the last read error.

`POST /api/serial_reader` accepts explicit actions:

```json
{"action":"connect","serial_ports":["/dev/serial/by-id/espnow-receiver"],"baud_rate":115200}
{"action":"disconnect","serial_ports":["/dev/serial/by-id/espnow-receiver"]}
{"action":"command","serial_ports":["/dev/serial/by-id/espnow-receiver"],"command":"status"}
```

Connect/Disconnect/Command target one device. Legacy list-only requests retain their replace-selection behaviour for existing clients. Sending to a disconnected device reports an error without opening it. The API preserves the existing standalone viewer's authentication behaviour.

## Verification

```sh
python3 tests/test_backend.py
node tests/named-paths.cjs
node tests/sidebar-live.cjs
```

Backend tests use fake serial connections and a Linux virtual terminal for exclusive-lock/owner checks. They cover alias reuse, targeted disconnect, missing/busy ports, failed opens, bounded reads, partial lines, read failure and shutdown cleanup. Browser fixtures cover four stable links after port renumbering, independent connections, display pause and busy failures.

The installation-specific live test opens the actual `/serial-reader` dashboard, checks its versioned iframe and all four device names, selects a device and pauses its display. It never presses Connect, Disconnect or Send. It requires the local Playwright installation and a private HA token outside this repository. No SMS, weather or ESP-NOW USB port is opened during automated verification.
