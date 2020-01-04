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

from datetime import time, timedelta

from voluptuous import Datetime, Required, Schema

from homeassistant.const import ATTR_NAME, ATTR_TIME
from homeassistant.core import callback
from homeassistant.helpers.config_validation import PLATFORM_SCHEMA
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.util import dt as dt_util

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        Required(ATTR_NAME): str,
        Required("schedule"): [
            Schema(
                {
                    Required(ATTR_NAME): str,
                    Required(ATTR_TIME): Datetime(format="%M:%S"),
                }
            )
        ],
    }
)


def _get_next_interval():
    """Determine the next time this sensor should be updated."""
    interval = 60
    now = dt_util.utcnow()
    timestamp = int(dt_util.as_timestamp(now))
    delta = interval - (timestamp % interval)
    print(f"Now: {now} delta: {delta}\n")
    return now + timedelta(seconds=delta)


def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the sensor platform."""
    device = ScheduleSensor(hass, config[ATTR_NAME], config["schedule"])
    async_track_point_in_utc_time(
        hass, device.point_in_time_listener, _get_next_interval()
    )
    async_add_entities([device])


class _SchedSlot:
    def __init__(self, name, hhmm):
        self.name = name
        parts = hhmm.split(":")
        self._time = time(int(parts[0]), int(parts[1]))

    @property
    def start(self):
        """Get the start time of this slot."""
        return self._time

    def after(self, date_time):
        """Determine if this slot comes after the given time."""
        return date_time.time() < self._time

    def active_at(self, date_time):
        """Determine if this slot is active (start time is prior to given time)."""
        return self._time <= date_time.time()


class ScheduleSensor(Entity):
    """Sensor that presents the current slot for a configured schedule."""

    def __init__(self, hass, name, schedule):
        """Initialize the sensor."""
        self.hass = hass
        self._name = name
        self._state = None
        self._schedule = []
        for slot in schedule:
            self._add_slot(slot[ATTR_NAME], slot[ATTR_TIME])

        self._update_internal_state(dt_util.utcnow())

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    def _update_internal_state(self, date_time):
        """Fetch new state data for the sensor."""
        date_time = dt_util.as_local(date_time)
        if self._schedule[-1].after(date_time):
            self._state = self._schedule[0].name
            return self

        for slot in self._schedule:
            if slot.active_at(date_time):
                self._state = slot.name
                return self

        self._state = "unknown"
        return self

    def _add_slot(self, name, hhmm):
        self._schedule.append(_SchedSlot(name, hhmm))
        self._schedule.sort(key=lambda slot: slot.start, reverse=True)

    @callback
    def point_in_time_listener(self, date_time):
        """Get the active schedule slot and update the state."""
        self._update_internal_state(date_time)
        self.async_schedule_update_ha_state()
        async_track_point_in_utc_time(
            self.hass, self.point_in_time_listener, _get_next_interval()
        )
