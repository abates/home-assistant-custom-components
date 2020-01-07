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

from datetime import timedelta

import voluptuous as vol

from homeassistant.const import ATTR_DATE, ATTR_NAME, ATTR_TIME, CONF_CONDITION
from homeassistant.core import callback
from homeassistant.helpers import condition
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.util import dt as dt_util

from . import (
    ATTR_INTERVAL,
    ATTR_NEXT_UPDATE,
    ATTR_DATE_TEMPLATE,
    ATTR_SCHEDULE,
    ATTR_SCHEDULES,
    ATTR_TIME_TEMPLATE,
    parse_date,
    parse_time,
)
from .schedule import DateSlot, Schedule, TimeSlot

_TIME_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Required(ATTR_NAME): str,
            vol.Exclusive(ATTR_TIME, "time"): vol.All(
                vol.Datetime(format="%M:%S"), parse_time
            ),
            vol.Exclusive(ATTR_TIME_TEMPLATE, "time"): cv.template,
        }
    ),
    cv.has_at_least_one_key(ATTR_TIME, ATTR_TIME_TEMPLATE),
    TimeSlot.from_config,
)


_DATE_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Required(ATTR_NAME): str,
            vol.Exclusive(ATTR_DATE, "date"): parse_date,
            vol.Exclusive(ATTR_DATE_TEMPLATE, "date"): cv.template,
        }
    ),
    cv.has_at_least_one_key(ATTR_DATE, ATTR_DATE_TEMPLATE),
    DateSlot.from_config,
)

_SCHEDULE_SCHEMA = vol.Or(
    vol.Schema(
        {
            vol.Optional(ATTR_NAME): str,
            vol.Optional(CONF_CONDITION): cv.CONDITION_SCHEMA,
            vol.Required(ATTR_SCHEDULE): vol.Any([_TIME_SCHEMA], [_DATE_SCHEMA]),
        }
    ),
    vol.Any([_TIME_SCHEMA], [_DATE_SCHEMA]),
)

PLATFORM_SCHEMA = cv.PLATFORM_SCHEMA.extend(
    {
        vol.Required(ATTR_NAME): str,
        vol.Exclusive(ATTR_SCHEDULES, "schedule"): [_SCHEDULE_SCHEMA],
        vol.Exclusive(ATTR_SCHEDULE, "schedule"): _SCHEDULE_SCHEMA,
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the sensor platform."""
    scheds_config = config.get(ATTR_SCHEDULES)
    schedules = []
    if scheds_config is None:
        schedules = [Schedule(hass, None, None, config.get(ATTR_SCHEDULE))]
    else:
        for sched_config in scheds_config:
            if_cond = None
            if sched_config.get(CONF_CONDITION) is not None:
                if_cond = await condition.async_from_config(
                    hass, sched_config.get(CONF_CONDITION), False
                )

            schedules.append(
                Schedule(
                    hass,
                    sched_config.get(ATTR_NAME),
                    if_cond,
                    sched_config.get(ATTR_SCHEDULE),
                )
            )

    sensor = ScheduleSensor(hass, config[ATTR_NAME], schedules)
    async_track_point_in_utc_time(
        hass, sensor.point_in_time_listener, sensor.next_interval
    )
    async_add_entities([sensor])


class ScheduleSensor(Entity):
    """Sensor that presents the current slot for a configured schedule."""

    def __init__(self, hass, name, schedules):
        """Initialize the sensor."""
        self.hass = hass
        self._name = name
        self._state = None
        self.schedules = schedules
        self._update_internal_state(dt_util.utcnow())

    @property
    def next_interval(self):
        """Determine the next time the sensor should be updated"""
        interval = self._schedule.interval
        now = dt_util.utcnow()
        timestamp = int(dt_util.as_timestamp(now))
        delta = interval - (timestamp % interval)
        self.next_update = now + timedelta(seconds=delta)
        return self.next_update

    @property
    def next_update(self):
        """The next time this sensor should be updated"""
        return self.next_update

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {
            ATTR_SCHEDULE: self._schedule.name,
            ATTR_INTERVAL: self._schedule.interval,
            ATTR_NEXT_UPDATE: self.next_update,
        }

    def _update_internal_state(self, date_time):
        """Fetch new state data for the sensor."""

        for schedule in self.schedules:
            # Get the currently active schedule
            if schedule.active:
                self._schedule = schedule
                break

        self._schedule.update(date_time)
        self._state = self._schedule.state

    @callback
    def point_in_time_listener(self, date_time):
        """Get the active schedule slot and update the state."""
        self._update_internal_state(date_time)
        self.async_schedule_update_ha_state()
        async_track_point_in_utc_time(
            self.hass, self.point_in_time_listener, self.next_interval
        )
