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

from datetime import datetime, date, time, timedelta

import voluptuous as vol

from homeassistant.const import ATTR_NAME, ATTR_DATE, ATTR_TIME
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.util import dt as dt_util

ATTR_DATE_TEMPLATE = f"{ATTR_DATE}_template"
ATTR_TIME_TEMPLATE = f"{ATTR_TIME}_template"

TIME_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Required(ATTR_NAME): str,
            vol.Exclusive(ATTR_TIME, "time"): vol.Datetime(format="%M:%S"),
            vol.Exclusive(ATTR_TIME_TEMPLATE, "time"): cv.template,
        }
    ),
    cv.has_at_least_one_key(ATTR_TIME, ATTR_TIME_TEMPLATE),
)

DATE_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Required(ATTR_NAME): str,
            vol.Exclusive(ATTR_DATE, "date"): vol.Datetime(format="%m/%d"),
            vol.Exclusive(ATTR_DATE_TEMPLATE, "date"): cv.template,
        }
    ),
    cv.has_at_least_one_key(ATTR_DATE, ATTR_DATE_TEMPLATE),
)

SCHEDULE_SCHEMA = vol.Any([TIME_SCHEMA], [DATE_SCHEMA])

PLATFORM_SCHEMA = cv.PLATFORM_SCHEMA.extend(
    {vol.Required(ATTR_NAME): str, vol.Required("schedule"): SCHEDULE_SCHEMA}
)

# TODO: update this so that the interval reflects day or time
def _get_next_interval():
    """Determine the next time this sensor should be updated."""
    interval = 60
    now = dt_util.utcnow()
    timestamp = int(dt_util.as_timestamp(now))
    delta = interval - (timestamp % interval)
    return now + timedelta(seconds=delta)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the sensor platform."""
    device = ScheduleSensor(hass, config[ATTR_NAME], config["schedule"])
    async_track_point_in_utc_time(
        hass, device.point_in_time_listener, _get_next_interval()
    )
    async_add_entities([device])


DATE_FORMATS = [
    "%m/%d",
    "%Y/%m/%d",
    "%Y-%m-%d",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
]
TIME_FORMATS = ["%H:%M", "%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"]


def parse(input, formats):
    for fmt in formats:
        try:
            return datetime.strptime(input, fmt)
        except ValueError:
            pass

    raise ValueError(f"{input} is not a recognized date/time")


def parse_date(input):
    "Parse a string into a date object."
    return parse(input, DATE_FORMATS).date()


def parse_time(input):
    return parse(input, TIME_FORMATS).time()


class _SchedSlot:
    def __init__(self, hass, config):
        self.name = config[ATTR_NAME]
        self._date = None
        self._date_template = None
        self._time = None
        self._time_template = None

        if ATTR_DATE in config:
            self._date = parse_date(config[ATTR_DATE])

        if ATTR_DATE_TEMPLATE in config:
            self._date_template = config[ATTR_DATE_TEMPLATE]
            self._date_template.hass = hass

        if ATTR_TIME in config:
            self._time = parse_time(config[ATTR_TIME])

        if ATTR_TIME_TEMPLATE in config:
            self._time_template = config[ATTR_TIME_TEMPLATE]
            self._time_template.hass = hass

    @property
    def date(self):
        if self._date is None and self._date_template is None:
            return None

        if self._date_template is None:
            _date = self._date
            _date = date(
                dt_util.as_local(dt_util.now()).year, self._date.month, self._date.day
            )

            return _date

        return parse_date(self._date_template.async_render())

    @property
    def time(self):
        if self._time_template is None:
            return self._time

        return self._time_template.async_render().time()

    @property
    def start(self):
        """Get the start time of this slot."""
        return self.date or self.time

    def after(self, date_time):
        """Determine if this slot comes after the given time."""
        if self.date is None:
            return date_time.time() < self.time

        return date_time.date() < self.date

    def active_at(self, date_time):
        """Determine if this slot is active (start time is prior to given time)."""
        if self.date is None:
            return self.time <= date_time.time()

        return self.date <= date_time.date()


class ScheduleSensor(Entity):
    """Sensor that presents the current slot for a configured schedule."""

    def __init__(self, hass, name, schedule):
        """Initialize the sensor."""
        self.hass = hass
        self._name = name
        self._state = None
        self._schedule = []
        for slot in schedule:
            self._add_slot(slot)

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

    def _add_slot(self, config):
        self._schedule.append(_SchedSlot(self.hass, config))
        self._schedule.sort(key=lambda slot: slot.start, reverse=True)

    @callback
    def point_in_time_listener(self, date_time):
        """Get the active schedule slot and update the state."""
        self._update_internal_state(date_time)
        self.async_schedule_update_ha_state()
        async_track_point_in_utc_time(
            self.hass, self.point_in_time_listener, _get_next_interval()
        )
