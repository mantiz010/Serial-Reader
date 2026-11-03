# Serial Reader for Home Assistant

A custom integration that allows you to monitor one or more serial ports in near real-time, timestamp all incoming data, and send commands back to the connected devices. Includes a web-based UI (`serial_ports.html`) for convenient setup and usage.

---

## Features

- **Open / Close Serial Ports Dynamically**: No need to hardcode your ports in `configuration.yaml`.
- **Timestamped Data**: Automatically prefixes each incoming line with `[YYYY-MM-DD HH:MM:SS][PORT_NAME]`.
- **Fast Polling**: The default polling interval reads data every 200ms (5 times per second).
- **HTTP Endpoints**: A REST API for listing available ports, activating them, and sending commands.
- **Web UI (`serial_ports.html`)**:
  - Lists available ports, allows you to pick a baud rate, and start/stop reading.
  - Displays incoming data with timestamps.
  - Lets you send commands to the current port (appends a newline automatically).

---

## Folder Structure

```plaintext
.
├── README.md                     # This file
├── custom_components/
│   └── serial_reader/
│       ├── __init__.py
│       ├── api.py
│       ├── const.py
│       ├── manifest.json
│       └── sensor.py            # Optional (for a HA sensor)
└── www/
    ├── serial_ports.html
    └── serial_reader_logo.png    # Logo referenced by the HTML
```

> **Note**: In Home Assistant, the `www/` folder is served at `/local/`. So placing `serial_reader_logo.png` in `www/` means the HTML can reference it as `/local/serial_reader_logo.png`.

---

## Installation

1. **Create the required directories** (if not already present):

   - `custom_components/serial_reader/`
   - `www/`

2. **Place the files** into these directories, following the structure shown above.

3. **(Optional) Install `pyserial` manually if needed**:

   ```bash
   pip install pyserial
   ```

   However, Home Assistant should automatically install it via `manifest.json`.

4. **Restart Home Assistant**.

After restart, the integration will be available in Home Assistant. The default polling interval is set in `__init__.py` to 200ms.

---

## Optional YAML Configuration



http:
  use_x_forwarded_for: true
  trusted_proxies:
    - 127.0.0.1
    - ::1
  cors_allowed_origins:
    - "http://yourip:8123"  # Replace with your HA URL
```

- **`serial_reader:`** is not strictly required if you rely on the integration’s defaults.
- **`http:`** settings are only necessary if you have a reverse proxy or need special CORS headers.

---

## Using the Web UI

1. Place `serial_ports.html` and `serial_reader_logo.png` in the `www/` folder.
2. Navigate to `http://<YOUR_HOME_ASSISTANT>:8123/local/serial_ports.html`.
3. You’ll see a dropdown of available ports, a baud rate selector, and controls to start or pause reading:
   - **USB Port**: Select the one your device is plugged into (e.g., `/dev/ttyUSB0`, `/dev/ttyACM0`, `COM3`, etc.).
   - **Baud Rate**: Default 115200; can change as needed.
   - **Start / Pause**: Click to begin reading data or to pause reading.
   - **Command**: Send a newline-terminated command to the currently open port.
   - **Data Window**: Shows the last 100 lines of timestamped data from the open port(s).

---

## Adding to the Dashboard

To embed the `serial_ports.html` interface directly into your Home Assistant dashboard, use an **iframe card**:

1. Go to your Home Assistant dashboard.
2. Click the three dots in the top-right corner and select **Edit Dashboard**.
3. Add a new card and choose **Custom: Iframe**.
4. Configure the card with the following URL:
   ```
   /local/serial_ports.html
   ```
5. Save the dashboard changes.

You can now view and interact with the Serial Reader directly from your dashboard.

---

## API Endpoints

This integration exposes a REST API at `http://<HOME_ASSISTANT>:8123/api/serial_reader`.

### **GET** `/api/serial_reader`

- **Response**:
  ```json
  {
    "available_ports": ["/dev/ttyUSB0", "..."],
    "active_ports": ["/dev/ttyUSB0"],
    "serial_data": [
      "[2025-01-02 12:00:00][/dev/ttyUSB0] Some line of data...",
      ...
    ]
  }
  ```

### **POST** `/api/serial_reader`

- **Body (JSON)**:

  ```json
  {
    "serial_ports": ["/dev/ttyUSB0"],
    "baud_rate": 115200,
    "command": "example_command"
  }
  ```

  - **`serial_ports`**: Array of ports you want active (opens them if not already opened, closes any not in this list).
  - **`baud_rate`**: The desired baud rate for newly opened ports.
  - **`command`** (optional): If present, sends it (with a trailing newline) to the first listed port.

- **Response**:

  ```json
  {"status": "success", "message": "..."}
  ```

---

## Troubleshooting

### No ports found

Ensure your Home Assistant instance can see the device at the OS level (e.g., `ls /dev/ttyUSB*`). If using Docker, you must map the device (e.g., `--device=/dev/ttyUSB0:/dev/ttyUSB0`).

### Permission denied

On Linux, add Home Assistant’s user to the `dialout` group:

```bash
sudo usermod -a -G dialout homeassistant
```

Then restart.

### Integration not appearing

Double-check folder structure (`custom_components/serial_reader/`) and file spelling.

### Data slow to appear

The backend polls every 200ms, but the **frontend** fetches data every 1 second by default. You can reduce that value in `serial_ports.html` if you want more frequent UI updates.

### Send command not working

Check logs for errors or ensure you’re entering a command and the port is active.

---

## Contributing

Feel free to open issues or pull requests in this GitHub repository if you have suggestions or find bugs. You can also customize:

- **Buffer size**: In `__init__.py` (currently `[-100:]`).
- **Timestamp format**: Change `strftime("%Y-%m-%d %H:%M:%S")`.
- **Polling interval**: Adjust `timedelta(milliseconds=200)` in `__init__.py`.
- **Frontend**: Tweak `pollingInterval` in `serial_ports.html`.

---

## License

This code is released under the [MIT License](LICENSE).


### Earlier page-only naming update (superseded by 1.1.0)

The viewer loads optional `/local/serial_device_names.json`. This installation includes ESP-NOW Receiver and ESP-NOW Wi-Fi Master using `/dev/serial/by-id/espnow-receiver` and `/dev/serial/by-id/espnow-wifi-master`. Copy the JSON alongside the HTML into HA's `www` folder. No integration restart is needed for this frontend update.

Named devices are saved choices, not proof of online status: the viewer checks opening on an explicit Start and reports backend failures. Detected raw paths remain available separately. Opening uses the named link rather than a remembered ttyUSB number, so renumbering cannot select the other board. Keep the boards in the hub sockets used by the host's naming rules. Page loading and naming do not open, close or send to a serial port. An existing connection is identified but not changed automatically.

### Serial Reader 1.1.0 backend naming

The component itself now discovers names from the host udev database and resolves the actual ESP-NOW named links. GET retains `available_ports`, `active_ports` and `serial_data`, adding `version`, `port_details` and `active_port_details`. The viewer uses these live backend details; the earlier `serial_device_names.json` is no longer required by this version.

Named links and raw tty paths are matched by physical device. Selecting another name for an already-open board keeps the existing connection. Duplicate aliases do not open twice; commands resolve to the open connection; a command to a closed port reports an error without opening it. Selecting an unavailable port or failing to open a replacement preserves the existing connection. Serial open/write/close operations run outside the HA event loop. The repository's incorrectly named `__init__.p` has been corrected to `__init__.py`.

Install `api.py`, `ports.py`, `manifest.json` and the existing `__init__.py`, `sensor.py`, `const.py` under `custom_components/serial_reader`, and copy `serial_ports.html` into `www`. Loading the changed Python backend requires one Home Assistant Core restart. A VM/host reboot is unnecessary. After that restart, press Start to reopen the wanted serial connection; no automatic connection or command replay is added. GET `/api/serial_reader` must return `version: 1.1.0` after loading.

Checks: `python3 tests/test_backend.py` (nine API tests with fake serial connections) and `node tests/named-paths.cjs` (browser fixtures, including changed ttyUSB numbering and failed opens). Real discovery was also checked inside the installed HA container without opening a port. Backups: `/home/mantiz010/backups/serial-reader-backend-20261103T043103Z`.

### Cached sidebar dashboard correction

The user's actual `serial-reader` Lovelace dashboard embedded `/local/serial_ports.html?v=39`, which kept the old viewer cached even after the integration and HTML were updated. HA serves `/local` files with a month-long cache lifetime. Deployment must update the iframe URL to `/local/serial_ports.html?v=<HTML SHA256 prefix>` when the HTML changes; a direct-link test alone does not verify the sidebar dashboard.

The viewer lists each ESP-NOW board once using its named stable link; it no longer also offers an ambiguous duplicate ttyUSB entry. Other detected ports show their backend device descriptions. The footer shows the backend version. Read-only browser validation opens `/serial-reader`, checks its real iframe URL and both labels/values, and confirms that page loading sends no serial POST requests. This correction requires no additional Home Assistant restart.

Regression command for the installed sidebar: `node tests/sidebar-live.cjs`. It verifies the actual `/serial-reader` dashboard iframe against the HTML content hash, both live backend names/stable paths, removal of duplicate raw entries, and zero serial mutations while loading/selecting. Read-only selection never presses Start or Send. Synthetic browser tests remain `node tests/named-paths.cjs`; API tests remain `python3 tests/test_backend.py`.

### SMS and weather USB names

This installation also identifies `/dev/ttyACM0` as **SMS Text Gateway** and `/dev/ttyACM1` as **Bresser 6-in-1 Weather Receiver**. `host_rules/99-sms-weather-names.rules` matches their distinct USB serial numbers, so these labels follow the boards if they move sockets or ttyACM numbering changes. Install it in HA OS's persistent `/etc/udev/rules.d`; validate with `udevadm verify`, reload rules and trigger metadata change events only for those two USB/tty devices. No firmware change or device reset is required.

Serial Reader 1.1.0 reads their udev labels dynamically, so refreshing the actual sidebar viewer displays the names immediately using its existing detected ACM paths. This backend version's preferred custom-link discovery is still limited to `espnow-*`; the new host links `/dev/sms-text-gateway` and `/dev/bresser-weather-receiver` (and matching `serial/by-id` links) are available on the host, but are not substituted as API open targets by this version. Existing SMS/weather app paths and all USB serial IDs are retained. Do not test by opening a live SMS/weather port or sending a message. The read-only sidebar regression now checks all four labels.
