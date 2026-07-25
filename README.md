# cron-explain

Plain-English explanation of a cron expression, plus a preview of its next
run times. Single self-contained Python script, stdlib only, no install step.

## Install / run

```
curl -O https://raw.githubusercontent.com/marwej/cron-explain/main/cron_explain.py
python3 cron_explain.py "*/15 9-17 * * 1-5"
```

## Usage

```
cron_explain.py "<cron-expression>" [--next N] [--from ISO8601]
```

See [SPEC.md](./SPEC.md) for the full CLI contract and non-goals.

## Pricing

- **Personal / open-source use:** free (MIT licensed).
- **Team license:** $9 one-time per seat — get in touch to arrange a team
  license, priority bugfixes, and update notifications.

See [PRICING.md](./PRICING.md) for the full plan and reasoning.

## Support / contact

Open an issue on this repo, or reach out directly if you want a team license.
