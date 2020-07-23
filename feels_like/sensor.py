# Copyright 2020 Andrew Bates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Platform for sensor integration."""

import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant.const import ATTR_NAME, TEMP_FAHRENHEIT
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_state_change
from homeassistant.util.temperature import convert as convert_temperature

import logging

_LOGGER = logging.getLogger(__name__)

DEFAULT_DECIMALS = 2

CONF_TEMP = "temp_sensor"
CONF_HUMIDITY = "humidity_sensor"
CONF_DECIMALS = "decimals"

PLATFORM_SCHEMA = cv.PLATFORM_SCHEMA.extend(
    {
        vol.Required(ATTR_NAME): str,
        vol.Required(CONF_TEMP): str,
        vol.Required(CONF_HUMIDITY): str,
        vol.Optional(CONF_DECIMALS, default=DEFAULT_DECIMALS): cv.positive_int,
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the sensor platform."""
    sensor = FeelsLikeSensor(
        hass,
        config[ATTR_NAME],
        config[CONF_TEMP],
        config[CONF_HUMIDITY],
        config[CONF_DECIMALS],
    )
    async_add_entities([sensor])


def convert(state):
    val = 0.0
    try:
        val = float(state.state)
    except ValueError:
        return None

    if state.attributes["unit_of_measurement"] == "%":
        return val

    return convert_temperature(val, state.attributes["unit_of_measurement"], TEMP_FAHRENHEIT)

class FeelsLikeSensor(Entity):
    """Sensor that presents the current slot for a configured schedule."""

    def __init__(self, hass, name, temp_sensor, humidity_sensor, decimals):
        """Initialize the sensor."""
        self.hass = hass
        self._name = name
        self._temp_sensor = temp_sensor
        self._humidity_sensor = humidity_sensor
        self._decimals = decimals

        self._temp = None
        self._humidity = None
        self._state = None
    
    async def async_added_to_hass(self):
        async_track_state_change(self.hass, [self._temp_sensor], self.async_update_temp)
        async_track_state_change(self.hass, [self._humidity_sensor], self.async_update_humidity)

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    async def async_update_temp(self, entity, old_state, new_state):
        """Update the sensors internal temperature state"""
        self._temp = convert(new_state)
        self._update_internal_state()

    async def async_update_humidity(self, entity, old_state, new_state):
        """Update the sensors internal humidity state"""
        self._humidity = convert(new_state)
        self._update_internal_state()

    def _update_internal_state(self):
        """Fetch new state data for the sensor."""
        if self._temp is None or self._humidity is None:
            return

        if self._temp < 80.0:
            self._state = self._temp
        else:
            self._state = round(
                (-42.379
                + 2.04901523 * self._temp
                + 10.14333127 * self._humidity
                - 0.22475541 * self._temp * self._humidity
                - 0.00683783 * self._temp * self._temp
                - 0.05481717 * self._humidity * self._humidity
                + 0.00122874 * self._temp * self._temp * self._humidity
                + 0.00085282 * self._temp * self._humidity * self._humidity
                - 0.00000199 * self._temp * self._temp * self._humidity * self._humidity),
                self._decimals,
            )

        self.async_schedule_update_ha_state()
