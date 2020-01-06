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

from datetime import date, datetime, time
from unittest import TestCase
from unittest.mock import MagicMock

import voluptuous as vol

from homeassistant.util import dt as dt_util

from . import parse_date, parse_time
from .sensor import _DATE_SCHEMA, _SCHEDULE_SCHEMA, _TIME_SCHEMA, ScheduleSensor
from .schedule import Schedule, DateSlot


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
                _SCHEDULE_SCHEMA(test["input"])

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
                _SCHEDULE_SCHEMA(test["input"])
            except vol.MultipleInvalid as err:
                name = test["name"]
                self.fail(f"{name} failed to validate data: {err}")

    def test_date_time_invalid(self):
        tests = [
            {"schema": _DATE_SCHEMA, "input": {"name": "test 1"}},
            {"schema": _TIME_SCHEMA, "input": {"name": "test 1"}},
            {
                "schema": _TIME_SCHEMA,
                "input": {"name": "test 1", "time_template": "{{foo}"},
            },
        ]

        for test in tests:
            with self.assertRaises(vol.MultipleInvalid):
                test["schema"](test["input"])

    def test_date_time_valid(self):
        tests = [
            {"schema": _DATE_SCHEMA, "input": {"name": "test 1", "date": "01/21"}},
            {"schema": _TIME_SCHEMA, "input": {"name": "test 1", "time": "01:21"}},
            {
                "schema": _DATE_SCHEMA,
                "input": {"name": "test 1", "date_template": "{{ '01/21' }}"},
            },
            {
                "schema": _TIME_SCHEMA,
                "input": {"name": "test 1", "time_template": "{{ '01:21' }}"},
            },
        ]
        for test in tests:
            try:
                test["schema"](test["input"])
            except vol.MultipleInvalid:
                self.fail("Failed to validate data")


class TestSensor(TestCase):
    def setUp(self):
        self.utcnow = dt_util.utcnow
        dt_util.utcnow = MagicMock(return_value=datetime(2010, 1, 1, 0, 0, 30))

    def tearDown(self):
        dt_util.utcnow = self.utcnow

    def test_get_next_interval(self):
        sensor = ScheduleSensor(
            None,
            None,
            [
                Schedule(
                    None,
                    None,
                    None,
                    [DateSlot("", datetime(2010, 1, 1, 0, 0, 0).date())],
                )
            ],
        )
        self.assertEqual(
            sensor.next_interval, datetime(2010, 1, 2, 0, 0, 0), "Incorrect interval",
        )
        dt_util.utcnow = MagicMock(return_value=datetime(2010, 1, 1, 0, 0, 59))
        self.assertEqual(
            sensor.next_interval, datetime(2010, 1, 2, 0, 0, 0), "Incorrect interval",
        )
