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
from .schedule import (
    DateSlot,
    TimeSlot,
    Schedule,
)
from datetime import datetime


class TestScheduleSlot(TestCase):
    def time(self, hour, minute):
        return datetime(2010, 1, 1, hour, minute, 0)

    def date(self, month, day):
        return datetime(2010, month, day, 0, 0, 0)

    def setUp(self):
        self.as_local = dt_util.as_local
        dt_util.as_local = MagicMock(return_value=datetime(2010, 1, 1, 0, 0, 0))

    def tearDown(self):
        dt_util.as_local = self.as_local

    def test_after(self):
        self.assertTrue(TimeSlot("", self.time(1, 0).time()).after(self.time(0, 0)))
        self.assertFalse(TimeSlot("", self.time(1, 0).time()).after(self.time(1, 0)))
        self.assertTrue(DateSlot("", self.date(12, 1).date()).after(self.date(11, 1)))
        self.assertFalse(DateSlot("", self.date(11, 1).date()).after(self.date(12, 1)))

    def test_active_at(self):
        self.assertTrue(TimeSlot("", self.time(0, 0).time()).active_at(self.time(0, 0)))
        self.assertTrue(TimeSlot("", self.time(1, 0).time()).active_at(self.time(2, 0)))
        self.assertTrue(
            DateSlot("", self.date(11, 1).date()).active_at(self.date(11, 1))
        )


class TestSchedule(TestCase):
    def time(self, hour, minute):
        return datetime(2010, 1, 1, hour, minute, 0)

    def setUp(self):
        self.utcnow = dt_util.utcnow
        dt_util.utcnow = MagicMock(return_value=datetime(2010, 1, 1, 0, 0, 30))

    def tearDown(self):
        dt_util.utcnow = self.utcnow

    def test_update_state(self):
        schedule = Schedule(
            None,
            None,
            None,
            [
                TimeSlot("t1", self.time(1, 0).time()),
                TimeSlot("t2", self.time(2, 0).time()),
                TimeSlot("t3", self.time(3, 0).time()),
            ],
        )
        # pylint: disable=protected-access
        self.assertEqual(schedule.update(self.time(2, 0)).state, "t2")
        self.assertEqual(schedule.update(self.time(3, 0)).state, "t3")
        self.assertEqual(schedule.update(self.time(1, 0)).state, "t1")
        self.assertEqual(schedule.update(self.time(0, 0)).state, "t3")

