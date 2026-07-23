from __future__ import annotations

import unittest

from scripts.generate_calendar import (
    DEFAULT_DATA_DIR,
    DEFAULT_OUTPUT,
    generate_calendar,
    load_years,
)


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

    def test_2026_event_counts(self) -> None:
        self.assertEqual(self.calendar.count(b"BEGIN:VEVENT\r\n"), 39)
        self.assertEqual(len(self.summaries), 39)
        self.assertEqual(sum(title.endswith("（补班）") for title in self.summaries), 6)
        self.assertEqual(
            sum(title.endswith("（最后一天）") for title in self.summaries),
            7,
        )
        self.assertEqual(sum("（第" in title for title in self.summaries), 26)

    def test_holiday_days_are_individual_all_day_events(self) -> None:
        self.assertIn("DTSTART;VALUE=DATE:20260215", self.unfolded)
        self.assertIn("DTEND;VALUE=DATE:20260216", self.unfolded)
        self.assertIn("春节（第1天）", self.summaries)
        self.assertIn("春节（第8天）", self.summaries)
        self.assertIn("春节（最后一天）", self.summaries)
        self.assertNotIn("春节（第9天）", self.summaries)

    def test_workday_titles_use_holiday_name(self) -> None:
        self.assertEqual(self.summaries.count("春节（补班）"), 2)
        self.assertEqual(self.summaries.count("国庆节（补班）"), 2)
        self.assertIn("元旦（补班）", self.summaries)
        self.assertIn("劳动节（补班）", self.summaries)
        self.assertNotIn("调休上班", self.unfolded)
        self.assertEqual(
            self.unfolded.count("CATEGORIES:中国大陆节假日,补班"),
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

    def test_rfc5545_line_endings_and_lengths(self) -> None:
        self.assertNotIn(b"\n", self.calendar.replace(b"\r\n", b""))
        for line in self.calendar.split(b"\r\n")[:-1]:
            self.assertLessEqual(len(line), 75)

    def test_committed_calendar_is_current(self) -> None:
        self.assertTrue(DEFAULT_OUTPUT.exists())
        self.assertEqual(DEFAULT_OUTPUT.read_bytes(), self.calendar)


if __name__ == "__main__":
    unittest.main()
