from datetime import datetime, timedelta
import logging

from homeassistant.core import HomeAssistant  # No deprecated alias
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.event import async_track_time_interval

DOMAIN = "serial_reader"
_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: ConfigType):
    """Set up the Serial Reader integration (single list approach, with timestamps)."""
    # Store integration data in hass.data
    hass.data[DOMAIN] = {
        "serial_ports": [],        # Ports selected by the user
        "baud_rate": 115200,       # Default baud rate
        "connections": {},         # Dict of opened serial connections by port
        "serial_data": [],         # Single list for all incoming lines
    }

    async def read_serial_data(_):
        """Periodically read data from any open serial ports."""
        for port, conn in list(hass.data[DOMAIN]["connections"].items()):
            # Read all available lines from this port
            while conn.in_waiting > 0:
                try:
                    line = conn.readline().decode("utf-8", errors="replace").strip()
                    if line:  # Only add non-empty lines
                        # Add a timestamp and port label
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        hass.data[DOMAIN]["serial_data"].append(f"[{timestamp}][{port}] {line}")
                        # Keep only the last 100 lines
                        hass.data[DOMAIN]["serial_data"] = hass.data[DOMAIN]["serial_data"][-100:]
                except Exception as e:
                    _LOGGER.error(f"Error reading from port {port}: {e}")
                    conn.close()
                    del hass.data[DOMAIN]["connections"][port]
                    break

    # Poll every 200ms for faster data capture (instead of once per second)
    async_track_time_interval(hass, read_serial_data, timedelta(milliseconds=200))

    # Register the API (handles listing ports, opening/closing, sending commands)
    from .api import SerialAPI
    hass.http.register_view(SerialAPI(hass))

    return True
