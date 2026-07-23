#!/usr/bin/env python3
"""Generate a deterministic RFC 5545 calendar from yearly JSON data."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "data"
DEFAULT_OUTPUT = ROOT / "docs" / "cn-holidays.ics"
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class CalendarDataError(ValueError):
    """Raised when a yearly data file is not safe to publish."""


def parse_date(value: Any, context: str) -> date:
    if not isinstance(value, str):
        raise CalendarDataError(f"{context} 必须是 YYYY-MM-DD 字符串")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise CalendarDataError(f"{context} 不是有效日期：{value}") from exc


def parse_timestamp(value: Any, context: str) -> datetime:
    if not isinstance(value, str):
        raise CalendarDataError(f"{context} 必须是 ISO 8601 时间字符串")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CalendarDataError(f"{context} 不是有效时间：{value}") from exc
    if parsed.tzinfo is None:
        raise CalendarDataError(f"{context} 必须包含时区：{value}")
    return parsed.astimezone(timezone.utc)


def require_text(record: dict[str, Any], key: str, context: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CalendarDataError(f"{context}.{key} 必须是非空字符串")
    return value.strip()


def validate_year(record: dict[str, Any], source: Path) -> dict[str, Any]:
    context = source.name
    year = record.get("year")
    if not isinstance(year, int) or year < 1949 or year > 9999:
        raise CalendarDataError(f"{context}.year 不是有效年份")

    revision = record.get("revision")
    if not isinstance(revision, int) or revision < 0:
        raise CalendarDataError(f"{context}.revision 必须是非负整数")

    last_modified = parse_timestamp(record.get("last_modified"), f"{context}.last_modified")
    document_title = require_text(record, "document_title", context)
    document_number = require_text(record, "document_number", context)
    source_url = require_text(record, "source_url", context)
    if not source_url.startswith("https://"):
        raise CalendarDataError(f"{context}.source_url 必须使用 HTTPS")

    raw_holidays = record.get("holidays")
    if not isinstance(raw_holidays, list) or not raw_holidays:
        raise CalendarDataError(f"{context}.holidays 必须是非空数组")

    holidays: list[dict[str, Any]] = []
    holiday_dates: set[date] = set()
    workday_dates: set[date] = set()
    holiday_ids: set[str] = set()

    for index, raw_holiday in enumerate(raw_holidays):
        item_context = f"{context}.holidays[{index}]"
        if not isinstance(raw_holiday, dict):
            raise CalendarDataError(f"{item_context} 必须是对象")

        holiday_id = require_text(raw_holiday, "id", item_context)
        if not ID_PATTERN.fullmatch(holiday_id):
            raise CalendarDataError(f"{item_context}.id 只能包含小写字母、数字和连字符")
        if holiday_id in holiday_ids:
            raise CalendarDataError(f"{context} 中存在重复节日 id：{holiday_id}")
        holiday_ids.add(holiday_id)

        name = require_text(raw_holiday, "name", item_context)
        schedule = require_text(raw_holiday, "schedule", item_context)
        start = parse_date(raw_holiday.get("start"), f"{item_context}.start")
        end = parse_date(raw_holiday.get("end"), f"{item_context}.end")
        if start.year != year or end.year != year:
            raise CalendarDataError(f"{item_context} 的放假日期必须位于 {year} 年")
        if end < start:
            raise CalendarDataError(f"{item_context}.end 不能早于 start")

        period_dates = {
            start + timedelta(days=offset)
            for offset in range((end - start).days + 1)
        }
        overlap = holiday_dates.intersection(period_dates)
        if overlap:
            repeated = min(overlap).isoformat()
            raise CalendarDataError(f"{context} 中的放假区间在 {repeated} 重叠")
        holiday_dates.update(period_dates)

        raw_workdays = raw_holiday.get("workdays")
        if not isinstance(raw_workdays, list):
            raise CalendarDataError(f"{item_context}.workdays 必须是数组")
        workdays: list[date] = []
        for workday_index, raw_workday in enumerate(raw_workdays):
            workday = parse_date(
                raw_workday,
                f"{item_context}.workdays[{workday_index}]",
            )
            if workday.year != year:
                raise CalendarDataError(f"{item_context} 的调休日必须位于 {year} 年")
            if workday in workday_dates:
                raise CalendarDataError(f"{context} 中存在重复调休日：{workday.isoformat()}")
            workday_dates.add(workday)
            workdays.append(workday)

        holidays.append(
            {
                "id": holiday_id,
                "name": name,
                "start": start,
                "end": end,
                "workdays": workdays,
                "schedule": schedule,
            }
        )

    invalid_workdays = holiday_dates.intersection(workday_dates)
    if invalid_workdays:
        invalid = min(invalid_workdays).isoformat()
        raise CalendarDataError(f"{context} 中的 {invalid} 同时被标记为放假和上班")

    return {
        "year": year,
        "revision": revision,
        "last_modified": last_modified,
        "document_title": document_title,
        "document_number": document_number,
        "source_url": source_url,
        "holidays": holidays,
    }


def load_years(data_dir: Path) -> list[dict[str, Any]]:
    files = sorted(data_dir.glob("*.json"))
    if not files:
        raise CalendarDataError(f"没有在 {data_dir} 中找到年度 JSON 数据")

    years: list[dict[str, Any]] = []
    seen_years: set[int] = set()
    for source in files:
        try:
            raw = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CalendarDataError(f"无法读取 {source}：{exc}") from exc
        if not isinstance(raw, dict):
            raise CalendarDataError(f"{source.name} 的根节点必须是对象")
        year = validate_year(raw, source)
        if year["year"] in seen_years:
            raise CalendarDataError(f"存在重复年度数据：{year['year']}")
        seen_years.add(year["year"])
        years.append(year)
    return sorted(years, key=lambda item: item["year"])


def escape_text(value: str) -> str:
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    return (
        normalized.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace(";", "\\;")
        .replace(",", "\\,")
    )


def fold_content_line(line: str) -> list[str]:
    """Fold one content line at 75 UTF-8 octets, including continuation space."""
    if len(line.encode("utf-8")) <= 75:
        return [line]

    chunks: list[str] = []
    current = ""
    limit = 75
    for character in line:
        candidate = current + character
        if len(candidate.encode("utf-8")) > limit:
            if not current:
                raise ValueError("单个字符超过 iCalendar 行长度限制")
            chunks.append(current)
            current = character
            limit = 74
        else:
            current = candidate
    if current:
        chunks.append(current)

    return [chunks[0], *(f" {chunk}" for chunk in chunks[1:])]


def format_date(value: date) -> str:
    return value.strftime("%Y%m%d")


def format_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def event_lines(
    *,
    uid: str,
    start: date,
    end: date,
    summary: str,
    description: str,
    categories: Iterable[str],
    source_url: str,
    timestamp: datetime,
    sequence: int,
) -> list[str]:
    stamp = format_timestamp(timestamp)
    return [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{stamp}",
        f"CREATED:{stamp}",
        f"LAST-MODIFIED:{stamp}",
        f"SEQUENCE:{sequence}",
        f"DTSTART;VALUE=DATE:{format_date(start)}",
        f"DTEND;VALUE=DATE:{format_date(end + timedelta(days=1))}",
        f"SUMMARY:{escape_text(summary)}",
        f"DESCRIPTION:{escape_text(description)}",
        "CATEGORIES:" + ",".join(escape_text(category) for category in categories),
        "CLASS:PUBLIC",
        "STATUS:CONFIRMED",
        "TRANSP:TRANSPARENT",
        "X-MICROSOFT-CDO-BUSYSTATUS:FREE",
        f"URL;VALUE=URI:{source_url}",
        "END:VEVENT",
    ]


def generate_calendar(years: list[dict[str, Any]]) -> bytes:
    year_label = "、".join(str(item["year"]) for item in years)
    logical_lines = [
        "BEGIN:VCALENDAR",
        "PRODID:-//CNCalendar//Mainland China Public Holidays//ZH-CN",
        "VERSION:2.0",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape_text('中国大陆法定节假日与调休')}",
        "X-WR-TIMEZONE:Asia/Shanghai",
        "X-APPLE-CALENDAR-COLOR:#D70015",
        "REFRESH-INTERVAL;VALUE=DURATION:P1D",
        "X-PUBLISHED-TTL:PT24H",
        "X-WR-CALDESC:"
        + escape_text(
            f"依据国务院办公厅年度通知整理，包含放假区间与调休上班日。当前数据覆盖 {year_label} 年。"
        ),
    ]

    events: list[tuple[date, int, list[str]]] = []
    for year in years:
        document = f"{year['document_title']}（{year['document_number']}）"
        for holiday in year["holidays"]:
            holiday_days = (holiday["end"] - holiday["start"]).days + 1
            for day_index in range(holiday_days):
                holiday_date = holiday["start"] + timedelta(days=day_index)
                day_number = day_index + 1
                if holiday_days == 1:
                    summary = holiday["name"]
                    day_description = f"{holiday['name']}假期，共1天。"
                elif day_number == holiday_days:
                    summary = f"{holiday['name']}（最后一天）"
                    day_description = (
                        f"今天是{holiday['name']}假期最后一天，"
                        f"也是第{day_number}天（共{holiday_days}天）。"
                    )
                else:
                    summary = f"{holiday['name']}（第{day_number}天）"
                    day_description = (
                        f"今天是{holiday['name']}假期第{day_number}天，"
                        f"共{holiday_days}天。"
                    )

                description = (
                    f"{day_description}\n"
                    f"{holiday['schedule']}\n"
                    f"官方文件：{document}\n"
                    f"来源：{year['source_url']}"
                )
                events.append(
                    (
                        holiday_date,
                        0,
                        event_lines(
                            uid=(
                                f"holiday-{holiday_date.strftime('%Y%m%d')}-"
                                f"{holiday['id']}@cncalendar"
                            ),
                            start=holiday_date,
                            end=holiday_date,
                            summary=summary,
                            description=description,
                            categories=("中国大陆节假日", "放假"),
                            source_url=year["source_url"],
                            timestamp=year["last_modified"],
                            sequence=year["revision"],
                        ),
                    )
                )

            for workday in holiday["workdays"]:
                readable_date = f"{workday.year}年{workday.month}月{workday.day}日"
                workday_description = (
                    f"按照{document}，{readable_date}为{holiday['name']}调休上班日。\n"
                    f"来源：{year['source_url']}"
                )
                events.append(
                    (
                        workday,
                        1,
                        event_lines(
                            uid=(
                                f"workday-{workday.strftime('%Y%m%d')}-"
                                f"{holiday['id']}@cncalendar"
                            ),
                            start=workday,
                            end=workday,
                            summary=f"{holiday['name']}（补班）",
                            description=workday_description,
                            categories=("中国大陆节假日", "调休上班"),
                            source_url=year["source_url"],
                            timestamp=year["last_modified"],
                            sequence=year["revision"],
                        ),
                    )
                )

    for _, _, lines in sorted(events, key=lambda event: (event[0], event[1])):
        logical_lines.extend(lines)
    logical_lines.append("END:VCALENDAR")

    physical_lines = [
        physical
        for logical in logical_lines
        for physical in fold_content_line(logical)
    ]
    calendar = ("\r\n".join(physical_lines) + "\r\n").encode("utf-8")
    validate_ics_bytes(calendar)
    return calendar


def validate_ics_bytes(calendar: bytes) -> None:
    if not calendar.startswith(b"BEGIN:VCALENDAR\r\n"):
        raise CalendarDataError("生成结果缺少 VCALENDAR 开始标记")
    if not calendar.endswith(b"END:VCALENDAR\r\n"):
        raise CalendarDataError("生成结果缺少 VCALENDAR 结束标记")
    without_crlf = calendar.replace(b"\r\n", b"")
    if b"\r" in without_crlf or b"\n" in without_crlf:
        raise CalendarDataError("生成结果包含非 CRLF 换行")
    for line_number, line in enumerate(calendar.split(b"\r\n")[:-1], start=1):
        if len(line) > 75:
            raise CalendarDataError(
                f"生成结果第 {line_number} 行超过 75 字节：{len(line)}"
            )
    if calendar.count(b"BEGIN:VEVENT\r\n") != calendar.count(b"END:VEVENT\r\n"):
        raise CalendarDataError("VEVENT 开始与结束数量不一致")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"年度 JSON 目录（默认：{DEFAULT_DATA_DIR}）",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"输出文件（默认：{DEFAULT_OUTPUT}）",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="只校验数据及现有输出是否为最新，不写文件",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        years = load_years(args.data_dir)
        generated = generate_calendar(years)
        if args.check:
            if not args.output.exists():
                print(f"错误：输出文件不存在：{args.output}", file=sys.stderr)
                return 1
            if args.output.read_bytes() != generated:
                print(
                    "错误：日历文件不是最新版本，请运行 "
                    "python3 scripts/generate_calendar.py",
                    file=sys.stderr,
                )
                return 1
            print(
                f"校验通过：{len(years)} 个年度，"
                f"{generated.count(b'BEGIN:VEVENT')} 个日程"
            )
            return 0

        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(generated)
        print(
            f"已生成 {args.output}：{len(years)} 个年度，"
            f"{generated.count(b'BEGIN:VEVENT')} 个日程"
        )
        return 0
    except (CalendarDataError, OSError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
