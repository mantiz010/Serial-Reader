import asyncio
import serial
import serial.tools.list_ports

from homeassistant.components.http import HomeAssistantView

DOMAIN = "serial_reader"
DEFAULT_BAUD_RATE = 115200

class SerialAPI(HomeAssistantView):
    """API to manage serial ports and retrieve data."""

    url = "/api/serial_reader"
    name = "api:serial_reader"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def get(self, request):
        """
        GET:
          - Lists all available USB ports.
          - Lists currently active ports (opened by this integration).
          - Returns serial_data (last 100 lines, timestamped).
        """
        ports = await asyncio.to_thread(serial.tools.list_ports.comports)
        available_ports = [port.device for port in ports]
        active_ports = list(self.hass.data[DOMAIN]["connections"].keys())
        serial_data = self.hass.data[DOMAIN].get("serial_data", [])
        return self.json({
            "available_ports": available_ports,
            "active_ports": active_ports,
            "serial_data": serial_data[-100:],  # Just in case, limit to last 100 lines
        })

    async def post(self, request):
        """
        POST:
          - Activate/deactivate ports (via "serial_ports" array).
          - Set baud rate (via "baud_rate").
          - Send a command if "command" is provided (append "\n").
        """
        try:
            body = await request.json()
            serial_ports = body.get("serial_ports", [])
            baud_rate = body.get("baud_rate", DEFAULT_BAUD_RATE)
            command = body.get("command", None)

            # If a command is specified, send it to the first listed port
            if command and serial_ports:
                target_port = serial_ports[0]
                if target_port in self.hass.data[DOMAIN]["connections"]:
                    conn = self.hass.data[DOMAIN]["connections"][target_port]
                    conn.write((command + "\n").encode("utf-8"))
                    return self.json({
                        "status": "success",
                        "message": f"Command '{command}' sent to {target_port}"
                    })

            # Store new port list & baud rate
            self.hass.data[DOMAIN]["serial_ports"] = serial_ports
            self.hass.data[DOMAIN]["baud_rate"] = baud_rate

            # Close & remove any connections not in the new list
            for port, conn in list(self.hass.data[DOMAIN]["connections"].items()):
                if port not in serial_ports:
                    conn.close()
                    del self.hass.data[DOMAIN]["connections"][port]

            # Open connections for newly selected ports
            for port in serial_ports:
                if port not in self.hass.data[DOMAIN]["connections"]:
                    self.hass.data[DOMAIN]["connections"][port] = serial.Serial(
                        port, baud_rate, timeout=1
                    )

            return self.json({"status": "success", "active_ports": serial_ports})

        except Exception as e:
            return self.json({"status": "error", "message": str(e)})
