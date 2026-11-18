"""Iranian lunar (Hijri) month starts.

Official month starts come from data/lunar_months.json (Iranian calendar
center data). Months beyond that table are estimated astronomically
(new moon + simple visibility rule) and must be treated as approximate.
"""
import datetime
import json
import math
from pathlib import Path

DATA = json.loads((Path(__file__).resolve().parent.parent / "data" / "lunar_months.json").read_text(encoding="utf-8"))
_TABLE = {k: datetime.date.fromisoformat(v) for k, v in DATA["month_starts"].items()}
TABLE_END = datetime.date.fromisoformat(DATA["table_end"])

_NMONTHS = 1405 * 12 + 1


def _sind(x):
    return math.sin(math.radians(x))


def _new_moon(n):
    k = n
    T = k / 1236.85
    t2, t3 = T * T, T * T * T
    jd = (2415020.75933 + 29.53058868 * k - .0001178 * t2 - .000000155 * t3
          + .00033 * _sind(166.56 + 132.87 * T - .009173 * t2))
    sa = math.radians(359.2242 + 29.10535608 * k - .0000333 * t2 - .00000347 * t3)
    ma = math.radians(306.0253 + 385.81691806 * k + .0107306 * t2 + .00001236 * t3)
    tf = math.radians(2 * (21.2964 + 390.67050646 * k - .0016528 * t2 - .00000239 * t3))
    xtra = (((.1734 - .000393 * T) * math.sin(sa)) + (.0021 * math.sin(sa * 2))
            - (.4068 * math.sin(ma)) + (.0161 * math.sin(2 * ma)) - (.0004 * math.sin(3 * ma))
            + (.0104 * math.sin(tf)) - (.0051 * math.sin(sa + ma)) - (.0074 * math.sin(sa - ma))
            + (.0004 * math.sin(tf + sa)) - (.0004 * math.sin(tf - sa)) - (.0006 * math.sin(tf + ma))
            + (.001 * math.sin(tf - ma)) + (.0005 * math.sin(sa + 2 * ma)))
    return jd + xtra - (.41 + (1.2053 * T) + (.4992 * t2)) / 1440


def _visibility(n):
    # Simple rule tuned against official Iranian data (1380-1449 AH):
    # the month starts on the second civil day after the conjunction.
    # Matches the official start in ~81% of months, otherwise off by one day.
    return _new_moon(n) + 1


def _estimated_start(year, month):
    k = month + year * 12 - _NMONTHS
    jdn = math.floor(_visibility(k + 1048) + 1 + .5)
    return datetime.date.fromordinal(jdn - 1721425)


def _last_table_month():
    y, m = max((int(k.split("/")[0]), int(k.split("/")[1])) for k in _TABLE)
    return y, m


_CACHE = {}


def month_start(year, month):
    """Return (gregorian date of day 1, is_from_official_table)."""
    key = f"{year}/{month}"
    if key in _TABLE:
        return _TABLE[key], True
    ly, lm = _last_table_month()
    if (year, month) < (ly, lm):
        return _estimated_start(year, month), False
    # Walk forward from the end of the table so month lengths stay 29 or 30 days.
    if (year, month) not in _CACHE:
        y, m, prev = ly, lm, _TABLE[f"{ly}/{lm}"]
        while (y, m) != (year, month):
            y, m = (y, m + 1) if m < 12 else (y + 1, 1)
            if (y, m) not in _CACHE:
                if prev == _TABLE.get(f"{ly}/{lm}") and (y, m) == ((ly, lm + 1) if lm < 12 else (ly + 1, 1)):
                    start = TABLE_END
                else:
                    est = _estimated_start(y, m)
                    lo, hi = prev + datetime.timedelta(days=29), prev + datetime.timedelta(days=30)
                    start = min(max(est, lo), hi)
                _CACHE[(y, m)] = start
            prev = _CACHE[(y, m)]
    return _CACHE[(year, month)], False


def to_gregorian(year, month, day):
    start, official = month_start(year, month)
    return start + datetime.timedelta(days=day - 1), official


def end_of_month(year, month):
    ny, nm = (year, month + 1) if month < 12 else (year + 1, 1)
    start, official = month_start(ny, nm)
    return start - datetime.timedelta(days=1), official
