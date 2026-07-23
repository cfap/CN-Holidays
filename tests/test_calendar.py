from __future__ import annotations

import unittest
from datetime import date, timedelta

from scripts.generate_calendar import (
    DEFAULT_DATA_DIR,
    DEFAULT_OUTPUT,
    annual_update_warning,
    generate_calendar,
    load_years,
)
from scripts.scaffold_year import build_observances


class CalendarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.years = load_years(DEFAULT_DATA_DIR)
        cls.calendar = generate_calendar(cls.years)
        cls.unfolded = cls.calendar.decode("utf-8").replace("\r\n ", "")
        cls.summaries = [
            line.removeprefix("SUMMARY:")
            for line in cls.unfolded.splitlines()
            if line.startswith("SUMMARY:")
        ]
        cls.event_blocks = cls.unfolded.split("BEGIN:VEVENT\r\n")[1:]
        cls.events_by_uid = {}
        cls.summaries_by_uid = {}
        for block in cls.event_blocks:
            lines = block.splitlines()
            uid = next(
                line.removeprefix("UID:")
                for line in lines
                if line.startswith("UID:")
            )
            summary = next(
                line.removeprefix("SUMMARY:")
                for line in lines
                if line.startswith("SUMMARY:")
            )
            cls.events_by_uid[uid] = block
            cls.summaries_by_uid[uid] = summary
        cls.summaries_2026 = [
            cls.summaries_by_uid[uid]
            for uid, block in cls.events_by_uid.items()
            if "DTSTART;VALUE=DATE:2026" in block
        ]

    def test_2026_event_counts(self) -> None:
        self.assertEqual(len(self.summaries_2026), 44)
        self.assertEqual(
            sum(title.endswith("（补班）") for title in self.summaries_2026),
            6,
        )
        self.assertEqual(
            sum(title.endswith("（最后一天）") for title in self.summaries_2026),
            7,
        )
        self.assertEqual(sum("（第" in title for title in self.summaries_2026), 26)
        self.assertEqual(
            sum(
                title
                in {
                    "情人节",
                    "母亲节",
                    "父亲节",
                    "七夕节",
                }
                for title in self.summaries_2026
            ),
            4,
        )
        self.assertEqual(
            self.summaries_2026.count("日历订阅源需要更新到明年"),
            1,
        )

    def test_calendar_color_and_reminder_prefixes(self) -> None:
        self.assertIn("X-APPLE-CALENDAR-COLOR:#007AFF", self.unfolded)
        self.assertNotIn("X-APPLE-CALENDAR-COLOR:#D70015", self.unfolded)

        observance_prefixes = {
            "observance-20260214-valentines-day@cncalendar": "💕 ",
            "observance-20260510-mothers-day@cncalendar": "👩 ",
            "observance-20260621-fathers-day@cncalendar": "👨 ",
            "observance-20260819-qixi-festival@cncalendar": "💕 ",
        }
        for uid, block in self.events_by_uid.items():
            summary = self.summaries_by_uid[uid]
            self.assertFalse(
                summary.startswith(("🏖️ ", "💔 ", "💕 ", "👩 ", "👨 "))
            )
            alarm_descriptions = [
                next(
                    line.removeprefix("DESCRIPTION:")
                    for line in alarm.splitlines()
                    if line.startswith("DESCRIPTION:")
                )
                for alarm in block.split("BEGIN:VALARM")[1:]
            ]
            if uid.startswith("holiday-"):
                self.assertTrue(
                    all(
                        description.startswith("🏖️ ")
                        for description in alarm_descriptions
                    )
                )
            elif uid.startswith("observance-"):
                expected_prefix = observance_prefixes[uid]
                self.assertTrue(
                    all(
                        description.startswith(expected_prefix)
                        for description in alarm_descriptions
                    )
                )
            elif uid.startswith("workday-"):
                self.assertTrue(
                    all(
                        description.startswith("💔 ")
                        for description in alarm_descriptions
                    )
                )

    def test_holiday_days_are_individual_all_day_events(self) -> None:
        self.assertIn("DTSTART;VALUE=DATE:20260215", self.unfolded)
        self.assertIn("DTEND;VALUE=DATE:20260216", self.unfolded)
        self.assertIn("春节假期（第1天）", self.summaries)
        self.assertIn("春节假期（第8天）", self.summaries)
        self.assertIn("春节假期（最后一天）", self.summaries)
        self.assertNotIn("春节假期（第9天）", self.summaries)
        self.assertIn(
            "DESCRIPTION:今天是春节假期第1天，共9天。",
            self.events_by_uid[
                "holiday-20260215-spring-festival@cncalendar"
            ],
        )
        self.assertIn(
            "DESCRIPTION:今天是春节假期最后一天，"
            "也是第9天（共9天）。",
            self.events_by_uid[
                "holiday-20260223-spring-festival@cncalendar"
            ],
        )

    def test_workday_titles_use_holiday_name(self) -> None:
        self.assertEqual(self.summaries_2026.count("春节（补班）"), 2)
        self.assertEqual(self.summaries_2026.count("国庆节（补班）"), 2)
        self.assertIn("元旦（补班）", self.summaries_2026)
        self.assertIn("劳动节（补班）", self.summaries_2026)
        self.assertNotIn("调休上班", self.unfolded)
        self.assertEqual(
            sum(
                "CATEGORIES:中国大陆节假日,补班" in block
                for block in self.events_by_uid.values()
                if "DTSTART;VALUE=DATE:2026" in block
            ),
            6,
        )

    def test_workday_dates_are_present(self) -> None:
        for value in (
            "20260104",
            "20260214",
            "20260228",
            "20260509",
            "20260920",
            "20261010",
        ):
            self.assertIn(f"DTSTART;VALUE=DATE:{value}", self.unfolded)

    def test_observance_dates_and_categories(self) -> None:
        expected = {
            "observance-20260214-valentines-day@cncalendar": (
                "情人节",
                "20260214",
                "💕 ",
            ),
            "observance-20260510-mothers-day@cncalendar": (
                "母亲节",
                "20260510",
                "👩 ",
            ),
            "observance-20260621-fathers-day@cncalendar": (
                "父亲节",
                "20260621",
                "👨 ",
            ),
            "observance-20260819-qixi-festival@cncalendar": (
                "七夕节",
                "20260819",
                "💕 ",
            ),
        }
        for uid, (summary, calendar_date, prefix) in expected.items():
            block = self.events_by_uid[uid]
            self.assertIn(f"SUMMARY:{summary}", block)
            self.assertIn(f"DTSTART;VALUE=DATE:{calendar_date}", block)
            self.assertIn("CATEGORIES:纪念日", block)
            self.assertEqual(block.count("BEGIN:VALARM"), 1)
            self.assertIn("TRIGGER:PT9H", block)
            self.assertIn(
                f"DESCRIPTION:{prefix}今天是{summary}",
                block,
            )
            self.assertNotIn("TRIGGER:-PT10H", block)

        qixi = self.events_by_uid[
            "observance-20260819-qixi-festival@cncalendar"
        ]
        self.assertIn("农历七月初七", qixi)
        self.assertIn("www.hko.gov.hk", qixi)

    def test_reminders_cover_holidays_observances_and_workdays(self) -> None:
        expected_same_day_uids = set()
        expected_previous_day_uids = set()
        for year in self.years:
            for holiday in year["holidays"]:
                holiday_days = (holiday["end"] - holiday["start"]).days + 1
                for day_index in range(holiday_days):
                    holiday_date = holiday["start"] + timedelta(days=day_index)
                    expected_same_day_uids.add(
                        "holiday-"
                        f"{holiday_date.strftime('%Y%m%d')}-"
                        f"{holiday['id']}@cncalendar"
                    )
                for holiday_date in {holiday["start"], holiday["end"]}:
                    expected_previous_day_uids.add(
                        "holiday-"
                        f"{holiday_date.strftime('%Y%m%d')}-"
                        f"{holiday['id']}@cncalendar"
                    )
                for workday in holiday["workdays"]:
                    workday_uid = (
                        f"workday-{workday.strftime('%Y%m%d')}-"
                        f"{holiday['id']}@cncalendar"
                    )
                    expected_same_day_uids.add(workday_uid)
                    expected_previous_day_uids.add(workday_uid)
            for observance in year["observances"]:
                observance_date = observance["date"]
                expected_same_day_uids.add(
                    "observance-"
                    f"{observance_date.strftime('%Y%m%d')}-"
                    f"{observance['id']}@cncalendar"
                )
            expected_same_day_uids.add(
                f"maintenance-{year['year']}1201-"
                "calendar-update@cncalendar"
            )

        alarm_uids = {
            uid
            for uid, block in self.events_by_uid.items()
            if "BEGIN:VALARM" in block
        }
        expected_alarm_uids = expected_same_day_uids | expected_previous_day_uids
        expected_alarm_count = (
            len(expected_same_day_uids) + len(expected_previous_day_uids)
        )
        self.assertEqual(alarm_uids, expected_alarm_uids)
        self.assertEqual(
            self.unfolded.count("BEGIN:VALARM"),
            expected_alarm_count,
        )
        self.assertEqual(
            self.unfolded.count("END:VALARM"),
            expected_alarm_count,
        )
        self.assertEqual(
            self.unfolded.count("ACTION:DISPLAY"),
            expected_alarm_count,
        )
        self.assertEqual(
            self.unfolded.count("TRIGGER:PT9H"),
            len(expected_same_day_uids),
        )
        self.assertEqual(
            self.unfolded.count("TRIGGER:-PT10H"),
            len(expected_previous_day_uids),
        )

        middle_day = self.events_by_uid[
            "holiday-20260102-new-year@cncalendar"
        ]
        self.assertEqual(middle_day.count("BEGIN:VALARM"), 1)
        self.assertIn("TRIGGER:PT9H", middle_day)
        self.assertIn("DESCRIPTION:🏖️ 元旦假期第2天", middle_day)
        self.assertNotIn("TRIGGER:-PT10H", middle_day)

        first_day = self.events_by_uid[
            "holiday-20260101-new-year@cncalendar"
        ]
        self.assertEqual(first_day.count("BEGIN:VALARM"), 2)
        self.assertIn(
            "DESCRIPTION:🏖️ 明天开始元旦放假",
            first_day,
        )
        self.assertIn(
            "DESCRIPTION:🏖️ 元旦假期第1天",
            first_day,
        )
        self.assertIn(
            "DESCRIPTION:🏖️ 明天是元旦假期最后一天",
            self.events_by_uid["holiday-20260103-new-year@cncalendar"],
        )
        self.assertIn(
            "DESCRIPTION:🏖️ 元旦假期最后一天",
            self.events_by_uid["holiday-20260103-new-year@cncalendar"],
        )
        workday = self.events_by_uid[
            "workday-20260104-new-year@cncalendar"
        ]
        self.assertEqual(workday.count("BEGIN:VALARM"), 2)
        self.assertIn(
            "DESCRIPTION:💔 明天是元旦补班",
            workday,
        )
        self.assertIn("TRIGGER:PT9H", workday)
        self.assertIn("DESCRIPTION:💔 元旦补班", workday)

    def test_calendar_update_event_is_on_december_1(self) -> None:
        block = self.events_by_uid[
            "maintenance-20261201-calendar-update@cncalendar"
        ]
        self.assertIn("DTSTART;VALUE=DATE:20261201", block)
        self.assertIn("DTEND;VALUE=DATE:20261202", block)
        self.assertIn("SUMMARY:日历订阅源需要更新到明年", block)
        self.assertIn("CATEGORIES:日历维护", block)
        self.assertEqual(block.count("BEGIN:VALARM"), 1)
        self.assertIn("TRIGGER:PT9H", block)
        self.assertIn(
            "DESCRIPTION:日历订阅源需要更新到明年",
            block,
        )
        self.assertNotIn("TRIGGER:-PT10H", block)

    def test_single_day_holiday_reminder_copy(self) -> None:
        source_year = self.years[0]
        holiday_date = date(2026, 3, 1)
        single_day_year = {
            **source_year,
            "holidays": [
                {
                    "id": "single-day-test",
                    "name": "测试节日",
                    "start": holiday_date,
                    "end": holiday_date,
                    "workdays": [],
                    "schedule": "3月1日放假。",
                }
            ],
            "observances": [],
        }
        calendar = generate_calendar([single_day_year])
        unfolded = calendar.decode("utf-8").replace("\r\n ", "")
        holiday_block = unfolded.split(
            "UID:holiday-20260301-single-day-test@cncalendar",
            1,
        )[1].split("END:VEVENT", 1)[0]
        self.assertEqual(holiday_block.count("BEGIN:VALARM"), 2)
        self.assertIn("DESCRIPTION:测试节日假期，共1天。", holiday_block)
        self.assertIn("SUMMARY:测试节日", holiday_block)
        self.assertIn("DESCRIPTION:🏖️ 明天是测试节日", holiday_block)
        self.assertIn("DESCRIPTION:🏖️ 今天是测试节日", holiday_block)
        self.assertNotIn(
            "DESCRIPTION:🏖️ 明天是测试节日假期",
            holiday_block,
        )
        self.assertNotIn(
            "DESCRIPTION:🏖️ 今天是测试节日假期",
            holiday_block,
        )

    def test_annual_update_warning_starts_on_november_15(self) -> None:
        self.assertIsNone(
            annual_update_warning(self.years, today=date(2026, 11, 14))
        )
        warning = annual_update_warning(
            self.years,
            today=date(2026, 11, 15),
        )
        self.assertIsNotNone(warning)
        self.assertIn("data/2027.json", warning or "")

        future_years = [*self.years, {"year": 2027}]
        self.assertIsNone(
            annual_update_warning(future_years, today=date(2026, 11, 15))
        )

    def test_scaffold_calculates_sunday_observances(self) -> None:
        observances = {
            item["id"]: item
            for item in build_observances(2026)
        }
        self.assertEqual(observances["valentines-day"]["date"], "2026-02-14")
        self.assertEqual(observances["mothers-day"]["date"], "2026-05-10")
        self.assertEqual(observances["fathers-day"]["date"], "2026-06-21")
        self.assertEqual(observances["qixi-festival"]["date"], "TODO")

    def test_rfc5545_line_endings_and_lengths(self) -> None:
        self.assertNotIn(b"\n", self.calendar.replace(b"\r\n", b""))
        for line in self.calendar.split(b"\r\n")[:-1]:
            self.assertLessEqual(len(line), 75)

    def test_committed_calendar_is_current(self) -> None:
        self.assertTrue(DEFAULT_OUTPUT.exists())
        self.assertEqual(DEFAULT_OUTPUT.read_bytes(), self.calendar)


if __name__ == "__main__":
    unittest.main()
