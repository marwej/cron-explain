# SPEC: cron-explain

## What it does
Takes a standard 5-field cron expression and prints a plain-English explanation
of when it runs, plus the next N upcoming run times (UTC). Built for
developers who need to sanity-check a cron line before deploying it.

## CLI contract

```
cron-explain "<cron-expression>" [--next N] [--from ISO8601]
```

- `<cron-expression>` (required, positional): a standard 5-field cron string
  (`minute hour day-of-month month day-of-week`). Supports `*`, numbers,
  ranges (`1-5`), steps (`*/15`), and lists (`1,15,30`).
- `--next N` (optional, default 5): number of upcoming run times to print.
- `--from ISO8601` (optional, default now): reference timestamp to compute
  "next runs" from, e.g. `2026-07-25T00:00:00Z`.

### Exit codes
- `0`: valid expression, explanation printed.
- `1`: malformed expression (wrong field count, out-of-range value, bad
  syntax) — prints an error to stderr naming the bad field.

### Example

```
$ cron-explain "*/15 9-17 * * 1-5"
Runs every 15 minutes, between 09:00 and 17:59, Monday through Friday.

Next 5 runs (UTC):
  2026-07-25 09:00
  2026-07-25 09:15
  2026-07-25 09:30
  2026-07-25 09:45
  2026-07-25 10:00
```

## Non-goals
- No support for non-standard 6/7-field cron (seconds, years) or
  `@hourly`/`@daily` shorthand aliases.
- No timezone handling beyond UTC — input/output is always UTC.
- No cron *editing*, validation-fixing, or interactive prompts.
- Not a scheduler — it never runs anything, only explains and previews.
- No natural-language-to-cron (reverse direction) support.
