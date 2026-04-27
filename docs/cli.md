# CLI

Use `pym2v` from your terminal to inspect your account, discover machines, and export time-series data.

## Command overview

### user-info

Shows the authenticated user's profile payload.

```bash
  pym2v user-info
```

### routers

Lists routers available to your account.

```bash
pym2v routers --size 25 --order desc
```

Be aware:
- Use pagination flags (`--page`, `--size`) for large accounts
- `--filter` is passed directly to the backend filter engine

### machines

Lists machines you can access.

```bash
  pym2v machines --sort updatedAt --order desc
```

### machine-uuid

Looks up a machine UUID from its machine name.

```bash
pym2v machine-uuid --name "Boiler Room Controller"
```

Be aware:
- Machine name matching is exact
- If no machine is found, the command exits with an error payload

### measurements

Lists available measurement names for a machine.

```bash
pym2v measurements \
  --machine-uuid 3f89e8b2-0a0d-4a31-9283-7b1a6f8f2b8f \
  --size 100
```

### setpoints

Lists setpoints for a machine.

```bash
pym2v setpoints --machine-uuid 3f89e8b2-0a0d-4a31-9283-7b1a6f8f2b8f --size 100
```

### data

Fetches time-series data for one or more measurement names.

```bash
pym2v data \
  --machine-uuid 3f89e8b2-0a0d-4a31-9283-7b1a6f8f2b8f \
  --names temperature humidity \
  --start 2025-01-01T00:00:00 \
  --end 2025-01-01T06:00:00 \
  --format json
```

Be aware:
- `--start` and `--end` must conform to [ISO-8601][1] format and `start < end`
- Datetimes must both be timezone-aware or both timezone-naive
- `--interval` and `--max-frame-length` are seconds
- `--format parquet` requires `--output`
- Without `--output`, `csv` and `json` are printed to stdout


[1]: https://en.wikipedia.org/wiki/ISO_8601
