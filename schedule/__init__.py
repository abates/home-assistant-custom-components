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

"""An integration that creates schedule sensors."""

from homeassistant.const import ATTR_DATE, ATTR_TIME
from datetime import datetime

ATTR_SCHEDULE = "schedule"
ATTR_SCHEDULES = "schedules"
ATTR_DATE_TEMPLATE = f"{ATTR_DATE}_template"
ATTR_TIME_TEMPLATE = f"{ATTR_TIME}_template"

DATE_FORMATS = [
    "%m/%d",
    "%Y/%m/%d",
    "%Y-%m-%d",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
]

TIME_FORMATS = ["%H:%M", "%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"]


def _parse(value: str, formats):
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass

    raise ValueError(f"{input} is not a recognized date/time")


def parse_date(value: str):
    """Parse a string into a date object."""
    return _parse(value, DATE_FORMATS).date()


def parse_time(value: str):
    """Parse a string into a time object."""
    return _parse(value, TIME_FORMATS).time()
