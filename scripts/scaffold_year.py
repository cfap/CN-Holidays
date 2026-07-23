#!/usr/bin/env python3
"""Create a yearly JSON skeleton for the next calendar update."""

from __future__ import annotations

import argparse
import calendar
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "data"


def nth_weekday(year: int, month: int, weekday: int, ordinal: int) -> date:
    if ordinal < 1:
        raise ValueError("星期序号必须是正整数")
    matching_days = [
        week[weekday]
        for week in calendar.monthcalendar(year, month)
        if week[weekday] != 0
    ]
    try:
        day = matching_days[ordinal - 1]
    except (IndexError, TypeError) as exc:
        raise ValueError("指定月份不存在对应的星期日期") from exc
    return date(year, month, day)


def build_observances(year: int) -> list[dict[str, Any]]:
    mothers_day = nth_weekday(year, 5, calendar.SUNDAY, 2)
    fathers_day = nth_weekday(year, 6, calendar.SUNDAY, 3)
    return [
        {
            "id": "valentines-day",
            "name": "情人节",
            "date": date(year, 2, 14).isoformat(),
            "basis": "每年2月14日",
        },
        {
            "id": "mothers-day",
            "name": "母亲节",
            "date": mothers_day.isoformat(),
            "basis": "5月第二个星期日",
        },
        {
            "id": "fathers-day",
            "name": "父亲节",
            "date": fathers_day.isoformat(),
            "basis": "6月第三个星期日",
        },
        {
            "id": "qixi-festival",
            "name": "七夕节",
            "date": "TODO",
            "basis": "农历七月初七；TODO：核对对应公历日期",
            "source_url": (
                "https://www.hko.gov.hk/tc/gts/time/calendar/pdf/files/"
                f"{year}.pdf"
            ),
        },
    ]


def build_year(year: int) -> dict[str, Any]:
    modified = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    return {
        "year": year,
        "revision": 0,
        "last_modified": modified,
        "document_title": f"国务院办公厅关于{year}年部分节假日安排的通知",
        "document_number": "TODO",
        "source_url": "TODO",
        "holidays": [],
        "observances": build_observances(year),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("year", type=int, help="要新增的数据年份")
    parser.add_argument(
        "--output",
        type=Path,
        help="输出路径（默认：data/<年份>.json）",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.year < 1949 or args.year > 9999:
        print("错误：年份必须介于 1949 和 9999 之间", file=sys.stderr)
        return 1

    output = args.output or DEFAULT_DATA_DIR / f"{args.year}.json"
    if output.exists():
        print(f"错误：文件已存在，不会覆盖：{output}", file=sys.stderr)
        return 1

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(build_year(args.year), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"已创建年度数据骨架：{output}")
    print("请完成所有 TODO 和法定节假日数据，再运行 make generate check test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
