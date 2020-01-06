"""Defines Schedule and Schedule Slot"""

from homeassistant.util import dt as dt_util
from typing import Dict
from datetime import date as new_date
from homeassistant.const import (
    ATTR_NAME,
    ATTR_DATE,
    ATTR_TIME,
)

from . import (
    ATTR_DATE_TEMPLATE,
    ATTR_TIME_TEMPLATE,
    parse_date,
    parse_time,
)


class ScheduleSlot:
    """One slot in a schedule"""

    def __init__(self, name, converter):
        self.name = name
        self._converter = converter

    @property
    def start(self):
        """Determine when this ScheduleSlot begins"""
        pass

    def after(self, date_time):
        """Determine if this ScheduleSlot comes after the given time"""
        return self._converter(date_time) < self.start

    def active_at(self, date_time):
        """Determine if this ScheduleSlot is active for the given time"""
        return self.start <= self._converter(date_time)


class TimeSlot(ScheduleSlot):
    """TimeSlot is a ScheduleSlot for a whole time (hh:mm:ss)"""

    @classmethod
    def from_config(cls, config: Dict) -> "TimeSlot":
        """Create a time slot from the supplied config/dict"""
        return cls(
            config[ATTR_NAME],
            time=config.get(ATTR_TIME),
            time_template=config.get(ATTR_TIME_TEMPLATE),
        )

    def __init__(self, name, time, time_template=None):
        super().__init__(name, lambda dt: dt.time())
        self.time = time
        self.time_template = time_template

    @property
    def start(self):
        """Determine when this time slot starts"""
        if self.time_template is None:
            return self.time

        return parse_time(self.time_template.async_render())


class DateSlot(ScheduleSlot):
    """DateSlot is a ScheduleSlot for whole dates"""

    @classmethod
    def from_config(cls, config: Dict) -> "DateSlot":
        """Create a date slot from the supplied config/dict"""
        return cls(
            config[ATTR_NAME],
            date=config.get(ATTR_DATE),
            date_template=config.get(ATTR_DATE_TEMPLATE),
        )

    def __init__(self, name, date, date_template=None):
        super().__init__(name, lambda dt: dt.date())
        self.date = date
        self.date_template = date_template

    @property
    def start(self):
        """Determine when this date slot starts"""
        if self.date_template is None:
            _date = self.date
            _date = new_date(
                dt_util.as_local(dt_util.now()).year, self.date.month, self.date.day
            )

            return _date

        return parse_date(self.date_template.async_render())


class Schedule:
    """A complete list of timeslots for a given schedule"""

    def __init__(self, hass, name, condition, slots):
        self.hass = hass
        self.name = name
        self._state = "unknown"
        self._condition = condition

        self.slots = []
        for slot in slots:
            if hasattr(slot, "date_template") and slot.date_template is not None:
                slot.date_template.hass = hass
            if hasattr(slot, "time_template") and slot.time_template is not None:
                slot.time_template.hass = hass
            self.slots.append(slot)
        self.slots.sort(key=lambda slot: slot.start, reverse=True)

    def update(self, date_time):
        """Update the schedules internal state for the given datetime"""

        date_time = dt_util.as_local(date_time)
        if self.slots[-1].after(date_time):
            self._state = self.slots[0].name
            return self

        for slot in self.slots:
            if slot.active_at(date_time):
                self._state = slot.name
                return self

        self._state = "unknown"
        return self

    @property
    def interval(self):
        """Determine the update interval for this schedule.

        Schedules made up of date slots will return an interval of 86400 (number of
        seconds in a day).  Schedules made up of time slots will return an interval of
        60 (number of seconds in a minute).
        """
        if isinstance(self.slots[0], DateSlot):
            return 86400
        return 60

    @property
    def state(self):
        """Get the name of the active schedule slot"""
        return self._state

    @property
    def active(self):
        """Determine if this schedule is active"""
        if self._condition is None:
            return True

        return self._condition(self.hass)
