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
"""Test that the ScheduleSensor works."""

from unittest import TestCase
from unittest.mock import MagicMock
from homeassistant.util import dt as dt_util
from .sensor import _get_next_interval, _SchedSlot, ScheduleSensor
from datetime import datetime

# schedule = importlib.import_module("custom_components.schedule")


def dt(h, m):
    return datetime(2010, 1, 1, h, m, 0)


class TestScheduleSlot(TestCase):
    def test_after(self):
        self.assertTrue(_SchedSlot("", "01:00").after(dt(0, 0)))
        self.assertFalse(_SchedSlot("", "01:00").after(dt(1, 0)))

    def test_active_at(self):
        self.assertTrue(_SchedSlot("", "00:00").active_at(dt(0, 0)))
        self.assertTrue(_SchedSlot("", "01:00").active_at(dt(2, 0)))


class TestScheduleSensor(TestCase):
    def test_get_next_interval(self):
        dt_util.utcnow = MagicMock(return_value=datetime(2010, 1, 1, 0, 0, 30))
        self.assertEqual(
            _get_next_interval(), datetime(2010, 1, 1, 0, 1, 0), "Incorrect interval"
        )
        dt_util.utcnow = MagicMock(return_value=datetime(2010, 1, 1, 0, 0, 59))
        self.assertEqual(
            _get_next_interval(), datetime(2010, 1, 1, 0, 1, 0), "Incorrect interval"
        )

    def test_update_state(self):
        schedule = ScheduleSensor(
            None,
            "",
            [
                {"name": "t1", "time": "01:00"},
                {"name": "t2", "time": "02:00"},
                {"name": "t3", "time": "03:00"},
            ],
        )

        self.assertEqual(schedule._update_internal_state(dt(2, 0)).state, "t2")
        self.assertEqual(schedule._update_internal_state(dt(3, 0)).state, "t3")
        self.assertEqual(schedule._update_internal_state(dt(1, 0)).state, "t1")
        self.assertEqual(schedule._update_internal_state(dt(0, 0)).state, "t3")

