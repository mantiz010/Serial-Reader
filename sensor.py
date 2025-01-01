from homeassistant.helpers.entity import Entity

DOMAIN = "serial_reader"

def setup_platform(hass, config, add_entities, discovery_info=None):
    add_entities([SerialSensor(hass)])

class SerialSensor(Entity):
    """A sensor reflecting the last line of serial data."""

    def __init__(self, hass):
        self.hass = hass
        self._state = None

    @property
    def name(self):
        return "Serial Data"

    @property
    def state(self):
        return self._state

    def update(self):
        """Fetch the latest line from the global serial_data list."""
        data_list = self.hass.data[DOMAIN].get("serial_data", [])
        if data_list:
            self._state = data_list[-1]
        else:
            self._state = None
