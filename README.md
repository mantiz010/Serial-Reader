Serial Reader for Home Assistant

A custom integration that allows you to monitor one or more serial ports in near real-time, timestamp all incoming data, and send commands back to the connected devices. Includes a web-based UI (serial_ports.html) for convenient setup and usage.

Features

Open / Close Serial Ports Dynamically: No need to hardcode your ports in configuration.yaml.

Timestamped Data: Automatically prefixes each incoming line with [YYYY-MM-DD HH:MM:SS][PORT_NAME].

Fast Polling: The default polling interval reads data every 200ms (5 times per second).

HTTP Endpoints: A REST API for listing available ports, activating them, and sending commands.

Web UI (serial_ports.html):

Lists available ports, allows you to pick a baud rate, and start/stop reading.

Displays incoming data with timestamps.

Lets you send commands to the current port (appends a newline automatically).

Folder Structure

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

Note: In Home Assistant, the www/ folder is served at /local/. So placing serial_reader_logo.png in www/ means the HTML can reference it as /local/serial_reader_logo.png.

Installation

Create the required directories (if not already present):

custom_components/serial_reader/

www/

Place the files into these directories, following the structure shown above.

(Optional) Install pyserial manually if needed:

pip install pyserial

However, Home Assistant should automatically install it via manifest.json.

Restart Home Assistant.

After restart, the integration will be available in Home Assistant. The default polling interval is set in __init__.py to 200ms.

Optional YAML Configuration

If you’d like to specify some settings (though this integration primarily works without additional YAML), you could add to configuration.yaml:

serial_reader:
  default_baud_rate: 115200
  scan_interval: 5  # If you want to override how often data is read, in seconds

http:
  use_x_forwarded_for: true
  trusted_proxies:
    - 127.0.0.1
    - ::1
  cors_allowed_origins:
    - "http://yourip:8123"  # Replace with your HA URL

serial_reader: is not strictly required if you rely on the integration’s defaults.

http: settings are only necessary if you have a reverse proxy or need special CORS headers.

Using the Web UI

Place serial_ports.html and serial_reader_logo.png in the www/ folder.

Navigate to http://<YOUR_HOME_ASSISTANT>:8123/local/serial_ports.html.

You’ll see a dropdown of available ports, a baud rate selector, and controls to start or pause reading:

USB Port: Select the one your device is plugged into (e.g., /dev/ttyUSB0, /dev/ttyACM0, COM3, etc.).

Baud Rate: Default 115200; can change as needed.

Start / Pause: Click to begin reading data or to pause reading.

Command: Send a newline-terminated command to the currently open port.

Data Window: Shows the last 100 lines of timestamped data from the open port(s).

API Endpoints

This integration exposes a REST API at http://<HOME_ASSISTANT>:8123/api/serial_reader.

GET /api/serial_reader

Response:

{
  "available_ports": ["/dev/ttyUSB0", "..."],
  "active_ports": ["/dev/ttyUSB0"],
  "serial_data": [
    "[2025-01-02 12:00:00][/dev/ttyUSB0] Some line of data...",
    ...
  ]
}

POST /api/serial_reader

Body (JSON):

{
  "serial_ports": ["/dev/ttyUSB0"],
  "baud_rate": 115200,
  "command": "example_command"
}

serial_ports: Array of ports you want active (opens them if not already opened, closes any not in this list).

baud_rate: The desired baud rate for newly opened ports.

command (optional): If present, sends it (with a trailing newline) to the first listed port.

Response:

{"status": "success", "message": "..."}

Optional Sensor

The file sensor.py (in custom_components/serial_reader/) can create a sensor in Home Assistant that always shows the latest line of data. To enable:

In configuration.yaml:

sensor:
  - platform: serial_reader

After restart, you get a sensor named Serial Data (one per platform instance).

sensor.py only tracks the last line in serial_data; it’s a simple utility if you prefer an entity-based view inside HA.

Troubleshooting

No ports found

Ensure your Home Assistant instance can see the device at the OS level (e.g., ls /dev/ttyUSB*). If using Docker, you must map the device (e.g., --device=/dev/ttyUSB0:/dev/ttyUSB0).

Permission denied

On Linux, add Home Assistant’s user to the dialout group:

sudo usermod -a -G dialout homeassistant

Then restart.

Integration not appearing

Double-check folder structure (custom_components/serial_reader/) and file spelling.

Data slow to appear

The backend polls every 200ms, but the frontend fetches data every 1 second by default. You can reduce that value in serial_ports.html if you want more frequent UI updates.

Send command not working

Check logs for errors or ensure you’re entering a command and the port is active.

Contributing

Feel free to open issues or pull requests in this GitHub repository if you have suggestions or find bugs. You can also customize:

Buffer size: In __init__.py (currently [-100:]).

Timestamp format: Change strftime("%Y-%m-%d %H:%M:%S").

Polling interval: Adjust timedelta(milliseconds=200) in __init__.py.

Frontend: Tweak pollingInterval in serial_ports.html.

License

This code is released under the MIT License.
