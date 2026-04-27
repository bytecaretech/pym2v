# pym2v

![CI](https://github.com/bytecaretech/pym2v/actions/workflows/ci.yml/badge.svg)
![Docs](https://github.com/bytecaretech/pym2v/actions/workflows/docs.yml/badge.svg)
![PyPI](https://img.shields.io/pypi/v/pym2v)

Python wrapper to interact with [m2v][1] industrial IoT platform from [Eurogard][2].

## Prerequisites

- Python 3.12+
- Programmatic access to the Eurogard API

## Installation

pym2v is available as a Python package and can be installed via pip or [uv][3].

### Via pip

1. Create a virtual environment: `python3 -m venv .venv`
1. Activate the virtual environment: `source .venv/bin/activate`
1. Install pym2v via pip: `pip install pym2v`

### Via uv

1. Install pym2v via uv: `uv add pym2v`

## Configuration

To authenticate with the Eurogard API, you need to provide the following credentials:

- Username
- Password
- Client ID
- Client Secret

You can do this either by setting environment variables directly, or by loading values from an `.env` file explicitly.

### Using an .env file

Rename the `.env.example` at the root of the project to `.env`, and replace the placeholder values with your actual credentials.

```
EUROGARD_BASE_URL=https://eurogard.cloud
EUROGARD_USERNAME=your_username_here
EUROGARD_PASSWORD=your_password_here
EUROGARD_CLIENT_ID=your_client_id_here
EUROGARD_CLIENT_SECRET=your_client_secret_here
```

## Usage

For library usage, create explicit `Settings` and pass them to `EurogardAPI`:

```python
from datetime import datetime, timedelta

from pym2v import EurogardAPI, Settings


settings = Settings(
    base_url="https://eurogard.cloud",
    username="your_username_here",
    password="your_password_here",
    client_id="your_client_id_here",
    client_secret="your_client_secret_here",
)
api = EurogardAPI(settings=settings)
```

If you prefer `.env` loading convenience:

```python
from pym2v import EurogardAPI

api = EurogardAPI.from_env()
```

Retrieve a list of machines

```python
machines = api.get_machines()
```

Get the UUID of the machine you are interested in

```python
MACHINE_NAME = "1337Machine"

machine_uuid = api.get_machine_uuid(MACHINE_NAME, machines)
```

Get the names of measurements for which you like to pull data

```python
result = api.get_machine_measurement_names(machine_uuid)
```

Turn the data returned by the API into a DataFrame for easier handling

```python
import polars as pl

measurement_names_df = pl.DataFrame(result["entities"])
```

Get actual data

```python
START_DATE = datetime(2025, 1, 1)
END_DATE = datetime(2025, 1, 13)
INTERVAL = timedelta(seconds=60)
MAX_FRAME_LENGTH = timedelta(days=30)
NAMES = [col.strip() for col in measurement_names_df.get_column("name").to_list()]

data_df = api.get_long_frame_from_names(
    machine_uuid=machine_uuid,
    names=NAMES,
    start=START_DATE,
    end=END_DATE,
    interval=INTERVAL,
    max_frame_length=MAX_FRAME_LENGTH,
)
```

## CLI

After installing pym2v, you can also use the CLI:

```bash
pym2v user-info
pym2v machines --page 0 --size 25
pym2v machine-uuid --name "1337Machine"
pym2v data \
  --machine-uuid "<machine_uuid>" \
  --names temperature pressure \
  --start 2025-01-01T00:00:00 \
  --end 2025-01-01T01:00:00 \
  --format csv
```

For full command reference, see [docs/cli.md](docs/cli.md).

## Contributing

Check out [CONTRIBUTING.md](CONTRIBUTING.md) for further information.


[1]: https://eurogard.de
[2]: https://eurogard.de/software/m2v/
[3]: https://docs.astral.sh/uv/
