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
PREVIOUS_DAY_REMINDER_TRIGGER = "-PT10H"
SAME_DAY_REMINDER_TRIGGER = "PT9H"
ANNUAL_UPDATE_REMINDER = (11, 15)
CALENDAR_UPDATE_EVENT_MONTH_DAY = (12, 1)
CALENDAR_UPDATE_EVENT_TEXT = "日历订阅源需要更新到明年"
CHINA_STANDARD_TIME = timezone(timedelta(hours=8))


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
                raise CalendarDataError(f"{item_context} 的补班日期必须位于 {year} 年")
            if workday in workday_dates:
                raise CalendarDataError(f"{context} 中存在重复补班日期：{workday.isoformat()}")
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

    raw_observances = record.get("observances", [])
    if not isinstance(raw_observances, list):
        raise CalendarDataError(f"{context}.observances 必须是数组")

    observances: list[dict[str, Any]] = []
    observance_ids: set[str] = set()
    for index, raw_observance in enumerate(raw_observances):
        item_context = f"{context}.observances[{index}]"
        if not isinstance(raw_observance, dict):
            raise CalendarDataError(f"{item_context} 必须是对象")

        observance_id = require_text(raw_observance, "id", item_context)
        if not ID_PATTERN.fullmatch(observance_id):
            raise CalendarDataError(f"{item_context}.id 只能包含小写字母、数字和连字符")
        if observance_id in observance_ids:
            raise CalendarDataError(f"{context} 中存在重复纪念日 id：{observance_id}")
        observance_ids.add(observance_id)

        name = require_text(raw_observance, "name", item_context)
        basis = require_text(raw_observance, "basis", item_context)
        observance_date = parse_date(
            raw_observance.get("date"),
            f"{item_context}.date",
        )
        if observance_date.year != year:
            raise CalendarDataError(f"{item_context}.date 必须位于 {year} 年")

        observance_source = raw_observance.get("source_url")
        if observance_source is not None:
            if (
                not isinstance(observance_source, str)
                or not observance_source.startswith("https://")
            ):
                raise CalendarDataError(f"{item_context}.source_url 必须使用 HTTPS")
            observance_source = observance_source.strip()

        observances.append(
            {
                "id": observance_id,
                "name": name,
                "date": observance_date,
                "basis": basis,
                "source_url": observance_source,
            }
        )

    return {
        "year": year,
        "revision": revision,
        "last_modified": last_modified,
        "document_title": document_title,
        "document_number": document_number,
        "source_url": source_url,
        "holidays": holidays,
        "observances": observances,
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


def annual_update_warning(
    years: list[dict[str, Any]],
    today: date | None = None,
) -> str | None:
    current_date = today or datetime.now(CHINA_STANDARD_TIME).date()
    required_year = current_date.year
    if (current_date.month, current_date.day) >= ANNUAL_UPDATE_REMINDER:
        required_year += 1

    latest_year = max(item["year"] for item in years)
    if latest_year >= required_year:
        return None
    return (
        f"当前数据只覆盖至 {latest_year} 年，请新增 data/{required_year}.json；"
        "操作步骤见 MAINTENANCE.md"
    )


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
    source_url: str | None,
    timestamp: datetime,
    sequence: int,
    reminders: Iterable[tuple[str, str]] = (),
) -> list[str]:
    stamp = format_timestamp(timestamp)
    lines = [
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
    ]
    if source_url is not None:
        lines.append(f"URL;VALUE=URI:{source_url}")
    for trigger, reminder in reminders:
        lines.extend(
            (
                "BEGIN:VALARM",
                "ACTION:DISPLAY",
                f"TRIGGER:{trigger}",
                f"DESCRIPTION:{escape_text(reminder)}",
                "END:VALARM",
            )
        )
    lines.append("END:VEVENT")
    return lines


def generate_calendar(years: list[dict[str, Any]]) -> bytes:
    year_label = "、".join(str(item["year"]) for item in years)
    logical_lines = [
        "BEGIN:VCALENDAR",
        "PRODID:-//CNCalendar//Mainland China Public Holidays//ZH-CN",
        "VERSION:2.0",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape_text('中国大陆节假日与纪念日')}",
        "X-WR-TIMEZONE:Asia/Shanghai",
        "X-APPLE-CALENDAR-COLOR:#D70015",
        "REFRESH-INTERVAL;VALUE=DURATION:P1D",
        "X-PUBLISHED-TTL:PT24H",
        "X-WR-CALDESC:"
        + escape_text(
            "依据国务院办公厅年度通知整理，包含放假区间与补班日期。"
            "另含情人节、母亲节、父亲节和七夕节等纪念日。"
            "补班日期及每段假期首尾日设有前一天下午2点提醒。"
            "所有放假日、补班日期和纪念日设有当天上午9点提醒。"
            "每年公历12月1日设有日历订阅源年度更新提醒。"
            f"当前数据覆盖 {year_label} 年。"
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
                    summary = f"{holiday['name']}假期（最后一天）"
                    day_description = (
                        f"今天是{holiday['name']}假期最后一天，"
                        f"也是第{day_number}天（共{holiday_days}天）。"
                    )
                else:
                    summary = f"{holiday['name']}假期（第{day_number}天）"
                    day_description = (
                        f"今天是{holiday['name']}假期第{day_number}天，"
                        f"共{holiday_days}天。"
                    )

                if holiday_days == 1:
                    same_day_reminder = f"今天是{holiday['name']}"
                elif day_number == 1:
                    same_day_reminder = f"{holiday['name']}假期第1天"
                elif day_number == holiday_days:
                    same_day_reminder = f"{holiday['name']}假期最后一天"
                else:
                    same_day_reminder = f"{holiday['name']}假期第{day_number}天"

                reminders = [
                    (SAME_DAY_REMINDER_TRIGGER, same_day_reminder),
                ]
                if holiday_days == 1:
                    reminders.insert(
                        0,
                        (
                            PREVIOUS_DAY_REMINDER_TRIGGER,
                            f"明天是{holiday['name']}",
                        ),
                    )
                elif day_index == 0:
                    reminders.insert(
                        0,
                        (
                            PREVIOUS_DAY_REMINDER_TRIGGER,
                            f"明天开始{holiday['name']}放假",
                        ),
                    )
                elif day_number == holiday_days:
                    reminders.insert(
                        0,
                        (
                            PREVIOUS_DAY_REMINDER_TRIGGER,
                            f"明天是{holiday['name']}假期最后一天",
                        ),
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
                            reminders=reminders,
                        ),
                    )
                )

            for workday in holiday["workdays"]:
                readable_date = f"{workday.year}年{workday.month}月{workday.day}日"
                workday_description = (
                    f"按照{document}，{readable_date}为{holiday['name']}补班日期。\n"
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
                            categories=("中国大陆节假日", "补班"),
                            source_url=year["source_url"],
                            timestamp=year["last_modified"],
                            sequence=year["revision"],
                            reminders=(
                                (
                                    PREVIOUS_DAY_REMINDER_TRIGGER,
                                    f"明天是{holiday['name']}补班",
                                ),
                                (
                                    SAME_DAY_REMINDER_TRIGGER,
                                    f"{holiday['name']}补班",
                                ),
                            ),
                        ),
                    )
                )

        for observance in year["observances"]:
            observance_description = (
                f"{observance['basis']}\n"
                "该日为纪念日，不属于法定放假安排。"
            )
            if observance["source_url"] is not None:
                observance_description += f"\n来源：{observance['source_url']}"

            observance_date = observance["date"]
            events.append(
                (
                    observance_date,
                    2,
                    event_lines(
                        uid=(
                            f"observance-{observance_date.strftime('%Y%m%d')}-"
                            f"{observance['id']}@cncalendar"
                        ),
                        start=observance_date,
                        end=observance_date,
                        summary=observance["name"],
                        description=observance_description,
                        categories=("纪念日",),
                        source_url=observance["source_url"],
                        timestamp=year["last_modified"],
                        sequence=year["revision"],
                        reminders=(
                            (
                                SAME_DAY_REMINDER_TRIGGER,
                                f"今天是{observance['name']}",
                            ),
                        ),
                    ),
                )
            )

        calendar_update_date = date(
            year["year"],
            *CALENDAR_UPDATE_EVENT_MONTH_DAY,
        )
        events.append(
            (
                calendar_update_date,
                3,
                event_lines(
                    uid=(
                        "maintenance-"
                        f"{calendar_update_date.strftime('%Y%m%d')}-"
                        "calendar-update@cncalendar"
                    ),
                    start=calendar_update_date,
                    end=calendar_update_date,
                    summary=CALENDAR_UPDATE_EVENT_TEXT,
                    description=CALENDAR_UPDATE_EVENT_TEXT,
                    categories=("日历维护",),
                    source_url=None,
                    timestamp=year["last_modified"],
                    sequence=year["revision"],
                    reminders=(
                        (
                            SAME_DAY_REMINDER_TRIGGER,
                            CALENDAR_UPDATE_EVENT_TEXT,
                        ),
                    ),
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
    if calendar.count(b"BEGIN:VALARM\r\n") != calendar.count(b"END:VALARM\r\n"):
        raise CalendarDataError("VALARM 开始与结束数量不一致")


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
        maintenance_warning = annual_update_warning(years)
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
            if maintenance_warning is not None:
                print(f"年度更新提醒：{maintenance_warning}", file=sys.stderr)
                return 1
            print(
                f"校验通过：{len(years)} 个年度，"
                f"{generated.count(b'BEGIN:VEVENT')} 个日程"
            )
            return 0

        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(generated)
        if maintenance_warning is not None:
            print(f"年度更新提醒：{maintenance_warning}", file=sys.stderr)
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
