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
from .sensor import (
    _get_next_interval,
    _SchedSlot,
    ScheduleSensor,
    SCHEDULE_SCHEMA,
    DATE_SCHEMA,
    TIME_SCHEMA,
    parse_date,
    parse_time,
)
from datetime import datetime, date, time
import voluptuous as vol


class TestDateTimeParsing(TestCase):
    def test_parse_date(self):
        tests = [
            {"parser": parse_date, "input": "10/21", "want": date(1900, 10, 21)},
            {"parser": parse_date, "input": "2011/10/21", "want": date(2011, 10, 21)},
            {"parser": parse_date, "input": "2012-10-21", "want": date(2012, 10, 21)},
            {
                "parser": parse_date,
                "input": "2013-10-21 10:04:59.934104",
                "want": date(2013, 10, 21),
            },
            {"parser": parse_date, "input": "10-21", "wantException": ValueError},
            {"parser": parse_time, "input": "11:30", "want": time(11, 30)},
            {"parser": parse_time, "input": "12:30:40", "want": time(12, 30, 40)},
            {
                "parser": parse_time,
                "input": "2013-10-21 10:04:59",
                "want": time(10, 4, 59),
            },
        ]

        for test in tests:
            if "wantException" in test:
                with self.assertRaises(test["wantException"]):
                    test["parser"](test["input"])
            else:
                try:
                    got = test["parser"](test["input"])
                    self.assertEqual(test["want"], got)
                except ValueError:
                    self.fail(f"Failed to parse {test['input']}")


class TestSensorConfig(TestCase):
    def test_invalid_schedule(self):
        tests = [
            {
                "name": "test 1",
                "input": [
                    {"name": "d1", "date": "01/01"},
                    {"name": "t2", "time": "02/01"},
                ],
            },
        ]

        for test in tests:
            with self.assertRaises(vol.MultipleInvalid):
                SCHEDULE_SCHEMA(test["input"])

    def test_valid_schedule(self):
        tests = [
            {
                "name": "test 1",
                "input": [
                    {"name": "t1", "time": "01:00"},
                    {"name": "t2", "time": "02:00"},
                ],
            },
            {
                "name": "test 2",
                "input": [
                    {"name": "d1", "date": "01/01"},
                    {"name": "d2", "date": "02/01"},
                ],
            },
            {
                "name": "test 3",
                "input": [
                    {"name": "d1", "date": "01/01"},
                    {"name": "d2", "date_template": "{{ '02/01' }}"},
                ],
            },
        ]

        for test in tests:
            try:
                SCHEDULE_SCHEMA(test["input"])
            except vol.MultipleInvalid as err:
                name = test["name"]
                self.fail(f"{name} failed to validate data: {err}")

    def test_date_time_invalid(self):
        tests = [
            {"schema": DATE_SCHEMA, "input": {"name": "test 1"}},
            {"schema": TIME_SCHEMA, "input": {"name": "test 1"}},
            {
                "schema": TIME_SCHEMA,
                "input": {"name": "test 1", "time_template": "{{foo}"},
            },
        ]

        for test in tests:
            with self.assertRaises(vol.MultipleInvalid):
                test["schema"](test["input"])

    def test_date_time_valid(self):
        tests = [
            {"schema": DATE_SCHEMA, "input": {"name": "test 1", "date": "01/21"}},
            {"schema": TIME_SCHEMA, "input": {"name": "test 1", "time": "01:21"}},
            {
                "schema": DATE_SCHEMA,
                "input": {"name": "test 1", "date_template": "{{ '01/21' }}"},
            },
            {
                "schema": TIME_SCHEMA,
                "input": {"name": "test 1", "time_template": "{{ '01:21' }}"},
            },
        ]
        for test in tests:
            try:
                test["schema"](test["input"])
            except vol.MultipleInvalid:
                self.fail("Failed to validate data")


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
        self.assertTrue(
            _SchedSlot(None, {"name": "", "time": "01:00"}).after(self.time(0, 0))
        )
        self.assertFalse(
            _SchedSlot(None, {"name": "", "time": "01:00"}).after(self.time(1, 0))
        )
        self.assertTrue(
            _SchedSlot(None, {"name": "", "date": "12/1"}).after(self.date(11, 1))
        )
        self.assertFalse(
            _SchedSlot(None, {"name": "", "date": "11/1"}).after(self.date(12, 1))
        )

    def test_active_at(self):
        self.assertTrue(
            _SchedSlot(None, {"name": "", "time": "00:00"}).active_at(self.time(0, 0))
        )
        self.assertTrue(
            _SchedSlot(None, {"name": "", "time": "01:00"}).active_at(self.time(2, 0))
        )
        self.assertTrue(
            _SchedSlot(None, {"name": "", "date": "11/1"}).active_at(self.date(11, 1))
        )


class TestScheduleSensor(TestCase):
    def time(self, hour, minute):
        return datetime(2010, 1, 1, hour, minute, 0)

    def setUp(self):
        self.utcnow = dt_util.utcnow
        dt_util.utcnow = MagicMock(return_value=datetime(2010, 1, 1, 0, 0, 30))

    def tearDown(self):
        dt_util.utcnow = self.utcnow

    def test_get_next_interval(self):
        self.assertEqual(
            _get_next_interval(), datetime(2010, 1, 1, 0, 1, 0), "Incorrect interval",
        )
        dt_util.utcnow = MagicMock(return_value=datetime(2010, 1, 1, 0, 0, 59))
        self.assertEqual(
            _get_next_interval(), datetime(2010, 1, 1, 0, 1, 0), "Incorrect interval",
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

        self.assertEqual(schedule._update_internal_state(self.time(2, 0)).state, "t2")
        self.assertEqual(schedule._update_internal_state(self.time(3, 0)).state, "t3")
        self.assertEqual(schedule._update_internal_state(self.time(1, 0)).state, "t1")
        self.assertEqual(schedule._update_internal_state(self.time(0, 0)).state, "t3")

