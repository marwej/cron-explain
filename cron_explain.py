#!/usr/bin/env python3
"""
cron-explain: plain-English explanation + next N run times for a standard
5-field cron expression. Self-contained, stdlib only.

Usage:
    cron-explain "<cron-expression>" [--next N] [--from ISO8601]

See SPEC.md for full contract and non-goals.
"""

import sys
import argparse
from datetime import datetime, timedelta, timezone

FIELD_NAMES = ["minute", "hour", "day-of-month", "month", "day-of-week"]
FIELD_RANGES = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 6)]

MONTH_NAMES = ["", "January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"]
DOW_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


class CronError(Exception):
    def __init__(self, field_name, msg):
        super().__init__(f"{field_name}: {msg}")
        self.field_name = field_name


def parse_field(raw, lo, hi, field_name):
    """Parse one cron field into a sorted set of allowed integer values."""
    values = set()
    for part in raw.split(","):
        if part == "":
            raise CronError(field_name, f"empty entry in '{raw}'")
        step = 1
        if "/" in part:
            base, step_s = part.split("/", 1)
            if not step_s.isdigit() or int(step_s) <= 0:
                raise CronError(field_name, f"bad step '{step_s}' in '{part}'")
            step = int(step_s)
        else:
            base = part

        if base == "*":
            start, end = lo, hi
        elif "-" in base:
            lo_s, hi_s = base.split("-", 1)
            if not (lo_s.lstrip("-").isdigit() and hi_s.lstrip("-").isdigit()):
                raise CronError(field_name, f"bad range '{base}'")
            start, end = int(lo_s), int(hi_s)
            if start > end:
                raise CronError(field_name, f"range start > end in '{base}'")
        elif base.isdigit() or (base.startswith("-") and base[1:].isdigit()):
            start = end = int(base)
        else:
            raise CronError(field_name, f"invalid token '{base}'")

        if start < lo or end > hi:
            raise CronError(field_name, f"value out of range {lo}-{hi} in '{part}'")

        for v in range(start, end + 1, step):
            values.add(v)

    if not values:
        raise CronError(field_name, f"no valid values parsed from '{raw}'")
    return values


def parse_cron(expr):
    fields = expr.strip().split()
    if len(fields) != 5:
        raise CronError("field-count", f"expected 5 fields, got {len(fields)}")
    parsed = []
    for raw, name, (lo, hi) in zip(fields, FIELD_NAMES, FIELD_RANGES):
        parsed.append(parse_field(raw, lo, hi, name))
    minute, hour, dom, month, dow = parsed
    return {
        "minute": minute, "hour": hour, "dom": dom,
        "month": month, "dow": dow,
        "raw": fields,
    }


def _describe_set(values, lo, hi, name_fn=None, pad=False):
    values = sorted(values)
    full = set(range(lo, hi + 1))
    if set(values) == full:
        return None  # means "every"
    if name_fn:
        items = [name_fn(v) for v in values]
    elif pad:
        items = [f"{v:02d}" for v in values]
    else:
        items = [str(v) for v in values]
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return " and ".join(items)
    return ", ".join(items[:-1]) + ", and " + items[-1]


def explain(cron):
    minute, hour, dom, month, dow = (
        cron["minute"], cron["hour"], cron["dom"], cron["month"], cron["dow"]
    )
    parts = []

    # time-of-day / minute cadence
    all_minutes = set(range(0, 60))
    all_hours = set(range(0, 24))
    if minute == all_minutes and hour == all_hours:
        parts.append("Runs every minute")
    else:
        min_sorted = sorted(minute)
        step = None
        if len(min_sorted) > 1:
            diffs = {min_sorted[i + 1] - min_sorted[i] for i in range(len(min_sorted) - 1)}
            if len(diffs) == 1 and min_sorted[0] == 0 and (60 % list(diffs)[0] == 0) and \
               min_sorted[-1] == 60 - list(diffs)[0]:
                step = list(diffs)[0]
        if step:
            time_desc = f"every {step} minutes"
        elif len(min_sorted) == 1:
            time_desc = f"at minute {min_sorted[0]:02d}"
        else:
            time_desc = "at minutes " + _describe_set(minute, 0, 59, pad=True)

        if hour == all_hours:
            parts.append(f"Runs {time_desc}, every hour")
        else:
            hour_sorted = sorted(hour)
            if len(hour_sorted) > 1 and hour_sorted == list(range(hour_sorted[0], hour_sorted[-1] + 1)):
                hr_desc = f"between {hour_sorted[0]:02d}:00 and {hour_sorted[-1]:02d}:59"
            else:
                hr_desc = "during hour(s) " + _describe_set(hour, 0, 23, pad=True)
            parts.append(f"Runs {time_desc}, {hr_desc}")

    # day-of-month / month
    all_dom = set(range(1, 32))
    all_month = set(range(1, 13))
    if dom != all_dom:
        parts.append("on day(s) " + _describe_set(dom, 1, 31))
    if month != all_month:
        parts.append("in " + _describe_set(month, 1, 12, name_fn=lambda v: MONTH_NAMES[v]))

    # day-of-week
    all_dow = set(range(0, 7))
    if dow != all_dow:
        dow_sorted = sorted(dow)
        if dow_sorted == list(range(dow_sorted[0], dow_sorted[-1] + 1)) and len(dow_sorted) > 1:
            parts.append(f"{DOW_NAMES[dow_sorted[0]]} through {DOW_NAMES[dow_sorted[-1]]}")
        else:
            parts.append(_describe_set(dow, 0, 6, name_fn=lambda v: DOW_NAMES[v]))

    return ", ".join(parts) + "."


def next_runs(cron, start, count):
    """Compute the next `count` run times strictly after `start` (minute resolution)."""
    minute, hour, dom, month, dow = (
        cron["minute"], cron["hour"], cron["dom"], cron["month"], cron["dow"]
    )
    results = []
    t = start.replace(second=0, microsecond=0) + timedelta(minutes=1)
    # Safety cap: ~4 years of minutes to avoid infinite loop on impossible dates (e.g. Feb 30)
    max_iters = 4 * 366 * 24 * 60
    iters = 0
    while len(results) < count and iters < max_iters:
        iters += 1
        if t.month not in month:
            # jump to next month start
            t = (t.replace(day=1) + timedelta(days=32)).replace(
                day=1, hour=0, minute=0)
            continue
        if t.day not in dom or t.weekday_cron() not in dow:
            t = t.replace(hour=0, minute=0) + timedelta(days=1)
            continue
        if t.hour not in hour:
            t = t.replace(minute=0) + timedelta(hours=1)
            continue
        if t.minute not in minute:
            t = t + timedelta(minutes=1)
            continue
        results.append(t)
        t = t + timedelta(minutes=1)
    return results


class CronDT(datetime):
    """datetime subclass adding cron-style weekday (0=Sunday..6=Saturday)."""
    def weekday_cron(self):
        # Python weekday(): Monday=0..Sunday=6 -> convert to cron Sunday=0..Saturday=6
        return (self.weekday() + 1) % 7


def to_cron_dt(dt):
    return CronDT(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second,
                  dt.microsecond, tzinfo=dt.tzinfo)


def parse_iso(s):
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def main(argv):
    parser = argparse.ArgumentParser(prog="cron-explain", add_help=True)
    parser.add_argument("expression")
    parser.add_argument("--next", type=int, default=5)
    parser.add_argument("--from", dest="from_ts", default=None)
    args = parser.parse_args(argv)

    try:
        cron = parse_cron(args.expression)
    except CronError as e:
        print(f"Error in {e.field_name}: {e}", file=sys.stderr)
        return 1

    try:
        start = parse_iso(args.from_ts) if args.from_ts else datetime.now(timezone.utc)
    except ValueError:
        print(f"Error: bad --from timestamp '{args.from_ts}'", file=sys.stderr)
        return 1

    start_cron = to_cron_dt(start)

    print(explain(cron))
    print()
    print(f"Next {args.next} runs (UTC):")
    for t in next_runs(cron, start_cron, args.next):
        print(f"  {t.strftime('%Y-%m-%d %H:%M')}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
