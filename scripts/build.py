#!/usr/bin/env python3
"""Build the subscribable .ics calendars and the landing page into site/."""
import datetime
import hashlib
import html
import sys
from pathlib import Path

import jdatetime
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lunar  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SITE = ROOT / "site"

MONTHS_FA = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
             "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
MONTHS_EN = ["Farvardin", "Ordibehesht", "Khordad", "Tir", "Mordad", "Shahrivar",
             "Mehr", "Aban", "Azar", "Dey", "Bahman", "Esfand"]
FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def fa_num(n):
    return str(n).translate(FA_DIGITS)


def load(name):
    return yaml.safe_load((DATA / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------- iCalendar
def esc(text):
    return (text.replace("\\", "\\\\").replace(";", r"\;")
            .replace(",", r"\,").replace("\n", r"\n"))


def fold(line):
    """Fold to 75 octets per RFC 5545 without splitting UTF-8 characters."""
    out, cur, size = [], "", 0
    for ch in line:
        b = len(ch.encode("utf-8"))
        if size + b > (75 if not out else 74):
            out.append(cur)
            cur, size = "", 0
        cur += ch
        size += b
    out.append(cur)
    return "\r\n ".join(out)


def calendar_ics(name, desc, lang, events, stamp):
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0",
        "PRODID:-//shamsi-calendar//Persian Calendar//EN",
        "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
        f"X-WR-CALNAME:{esc(name)}", f"X-WR-CALDESC:{esc(desc)}",
        "X-WR-TIMEZONE:Asia/Tehran",
        "REFRESH-INTERVAL;VALUE=DURATION:P1D", "X-PUBLISHED-TTL:P1D",
    ]
    for ev in sorted(events, key=lambda e: (e["date"], e["uid"])):
        d = ev["date"]
        lines += [
            "BEGIN:VEVENT",
            f"UID:{ev['uid']}",
            f"DTSTAMP:{stamp}",
            f"DTSTART;VALUE=DATE:{d:%Y%m%d}",
            f"DTEND;VALUE=DATE:{d + datetime.timedelta(days=1):%Y%m%d}",
            f"SUMMARY:{esc(ev['title'])}",
            "TRANSP:TRANSPARENT",
            "CLASS:PUBLIC",
        ]
        if ev.get("desc"):
            lines.append(f"DESCRIPTION:{esc(ev['desc'])}")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(fold(line) for line in lines) + "\r\n"


def uid(kind, date, key):
    h = hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]
    return f"{kind}-{date:%Y%m%d}-{h}@shamsi-calendar"


# ---------------------------------------------------------------- content
def jalali_days(first_year, last_year):
    d = jdatetime.date(first_year, 1, 1)
    end = jdatetime.date(last_year + 1, 1, 1)
    while d < end:
        yield d
        d += datetime.timedelta(days=1)


def date_events(first, last):
    fa, en = [], []
    for j in jalali_days(first, last):
        g = j.togregorian()
        fa.append({"date": g, "uid": uid("date", g, "fa"),
                   "title": f"{fa_num(j.day)} {MONTHS_FA[j.month - 1]} {fa_num(j.year)}"})
        en.append({"date": g, "uid": uid("date", g, "en"),
                   "title": f"{j.day} {MONTHS_EN[j.month - 1]} {j.year}"})
    return fa, en


def holiday_events(first, last, official_last):
    data = load("holidays.yaml")
    g_start = jdatetime.date(first, 1, 1).togregorian()
    g_end = jdatetime.date(last + 1, 1, 1).togregorian()
    by_day = {}  # gregorian date -> list of (fa, en, approx)

    for y in range(first, last + 1):
        for h in data["solar"]:
            g = jdatetime.date(y, h["month"], h["day"]).togregorian()
            by_day.setdefault(g, []).append((h["fa"], h["en"], False))

    first_h = lunar.month_start(1440, 1)[0]
    hy_first = 1440 + int((g_start - first_h).days / 354.37) - 1
    hy_last = 1440 + int((g_end - first_h).days / 354.37) + 1
    for hy in range(hy_first, hy_last + 1):
        for h in data["lunar"]:
            if h["day"] == "end":
                g, from_table = lunar.end_of_month(hy, h["month"])
            else:
                g, from_table = lunar.to_gregorian(hy, h["month"], h["day"])
            if not (g_start <= g < g_end):
                continue
            jy = jdatetime.date.fromgregorian(date=g).year
            approx = (not from_table) or jy > official_last
            by_day.setdefault(g, []).append((h["fa"], h["en"], approx))

    fa, en = [], []
    for g, items in by_day.items():
        if not (g_start <= g < g_end):
            continue
        names_fa, names_en, any_approx = [], [], False
        for f, e, a in items:
            if f not in names_fa:
                names_fa.append(f)
            if e not in names_en:
                names_en.append(e)
            any_approx |= a
        t_fa = "تعطیل: " + " و ".join(names_fa) + (" (تقریبی)" if any_approx else "")
        t_en = "Holiday: " + " & ".join(names_en) + (" (approx.)" if any_approx else "")
        d_fa = "تاریخ قمری تقریبی است و ممکن است یک روز جابه‌جا شود." if any_approx else ""
        d_en = "Lunar date is estimated and may shift by one day." if any_approx else ""
        fa.append({"date": g, "uid": uid("hol", g, "fa"), "title": t_fa, "desc": d_fa})
        en.append({"date": g, "uid": uid("hol", g, "en"), "title": t_en, "desc": d_en})
    return fa, en


def last_wednesday_eve(year):
    d = jdatetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
    while d.togregorian().weekday() != 2:  # Wednesday
        d -= datetime.timedelta(days=1)
    return (d - datetime.timedelta(days=1)).togregorian()


def custom_events(first, last):
    fa, en = [], []
    for y in range(first, last + 1):
        for ev in load("events.yaml") or []:
            if ev.get("rule") == "chaharshanbe-suri":
                g = last_wednesday_eve(y)
            else:
                try:
                    g = jdatetime.date(y, int(ev["month"]), int(ev["day"])).togregorian()
                except ValueError:  # e.g. 30 Esfand in a non-leap year
                    continue
            key = f"{ev.get('month')}-{ev.get('day')}-{ev.get('rule')}-{ev['en']}"
            fa.append({"date": g, "uid": uid("evt", g, "fa" + key), "title": ev["fa"],
                       "desc": ev.get("note", "")})
            en.append({"date": g, "uid": uid("evt", g, "en" + key), "title": ev["en"],
                       "desc": ev.get("note", "")})
    return fa, en


# ---------------------------------------------------------------- page
def landing_page(cfg, files):
    host = cfg["base_url"].split("://", 1)[-1].rstrip("/")
    rows = []
    for key in ("all", "dates", "holidays", "events"):
        names = cfg["calendars"][key]
        links = []
        for lang, label in (("fa", "فارسی"), ("en", "Latin")):
            fn = files[(key, lang)]
            links.append(
                f'<div class="row"><a class="btn" href="webcal://{host}/{fn}" data-goatcounter-click="subscribe-{key}-{lang}">{label}</a>'
                f'<button class="copy" type="button" data-file="{fn}" data-goatcounter-click="copy-{key}-{lang}">'
                f'<span lang="fa">کپی لینک</span> · Copy</button></div>')
        cls = ' class="featured"' if key == "all" else ""
        rows.append(f"""
    <section{cls}>
      <h2>{html.escape(names['fa'])}</h2>
      <p class="names" dir="ltr">{html.escape(names['en'])} · {html.escape(names['de'])}</p>
      <div class="links">{''.join(links)}</div>
    </section>""")
    template = (ROOT / "scripts" / "page.html").read_text(encoding="utf-8")
    code = (cfg.get("goatcounter") or "").strip()
    analytics = privacy = ""
    if code:
        analytics = (f'<script data-goatcounter="https://{code}.goatcounter.com/count" '
                     'async src="//gc.zgo.at/count.js"></script>')
        privacy = ('<p>آمار بازدید به‌صورت ناشناس و بدون کوکی با GoatCounter جمع می‌شود.</p>'
                   '<p dir="ltr">Anonymous, cookie-free visit statistics via GoatCounter.</p>'
                   '<p dir="ltr" lang="de">Anonyme Besuchsstatistik ohne Cookies über GoatCounter.</p>')
    return (template.replace("{{SECTIONS}}", "".join(rows))
            .replace("{{ANALYTICS}}", analytics).replace("{{PRIVACY}}", privacy))


def main():
    cfg = load("config.yaml")
    today_year = jdatetime.date.today().year
    first = today_year - int(cfg["years_back"])
    last = today_year + int(cfg["years_forward"])
    official_last = int(cfg["official_last_year"])
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    SITE.mkdir(exist_ok=True)
    parts = {
        "dates": date_events(first, last),
        "holidays": holiday_events(first, last, official_last),
        "events": custom_events(first, last),
    }
    parts["all"] = tuple(
        parts["dates"][i] + parts["holidays"][i] + parts["events"][i] for i in (0, 1))
    files = {}
    for key, (ev_fa, ev_en) in parts.items():
        for lang, evs in (("fa", ev_fa), ("en", ev_en)):
            fn = f"{key}-{lang}.ics"
            names = cfg["calendars"][key]
            desc = f"{names['fa']} / {names['en']} — {first}–{last}"
            (SITE / fn).write_bytes(calendar_ics(names[lang], desc, lang, evs, stamp).encode("utf-8"))
            files[(key, lang)] = fn
            print(f"{fn}: {len(evs)} events")
    (SITE / "index.html").write_text(landing_page(cfg, files), encoding="utf-8")
    host = cfg["base_url"].split("://", 1)[-1].rstrip("/")
    if "example.com" not in host:
        (SITE / "CNAME").write_text(host + "\n", encoding="utf-8")
    print(f"Range: {first}–{last} (official lunar data through {official_last})")


if __name__ == "__main__":
    main()
