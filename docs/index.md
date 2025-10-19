# Home

Python wrapper to inteact with [m2v][1] industrial IoT platform from [Eurogard][2].

## Prerequisites

- Python 3.12+
- Programmatic access to the Eurogard API

## Installation

py2mv is available as a Python package and can be installed via pip or [uv][3].

### Via pip

1. Create a virtual environment: `python3 -m venv .venv`
1. Activate the virtual environment: `source .venv/bin/active`
1. Install pym2v via pip: `pip install pym2v`

### Via uv

1. Install pym2v via uv: `uv add pym2v`

## Configuration

To authenticate with the Eurogard API, you need to provide the following credentials:

- Username
- Password
- Client ID
- Client Secret

You can do this either by using an `.env` file (recommended) or by setting environment variables directly.

### Using an .env file

Rename the `.env.example` at the root of the project to `.env`, and replace the placeholder values with your actual credentials.

```
EUROGARD_BASEURL=https://eurogard.cloud
EUROGARD_USERNAME=your_username_here
EUROGARD_PASSWORD=your_password_here
EUROGARD_CLIENT_ID=your_client_id_here
EUROGARD_CLIENT_SECRET=your_client_secret_here
```

## Usage

Import the `EuroGardAPI` object and create an instance of it

```python
from pym2v.api import EurogardAPI


api = EurogardAPI()
```

Retrieve a list of machines

```python
machines = api.get_machines()
```

Get the UUID of the machine your are interested in

```python
MACHINE_NAME = "1337Machine"

machine_uuid = api.get_machine_uuid(MACHINE_NAME, machines)
```

Get the names of measurements for which you like to pull data

```python
result = api.get_machine_measurements(machine_uuid)
```

Turn the data returned by the API into a DataFrame for easier handling

```python
measurements_df = pd.DataFrame.from_dict(result["entities"])
```

Get actual data

```python
START_DATE = "2025-01-01"
END_DATE = "2025-01-13"
INTERVAL = "60s"
MAX_FRAME_LENGTH = "30D"

data_df = api.get_long_frame_from_names(
    machine_uuid=machine_uuid,
    names=measurements_df.name.to_list(),
    start=START_DATE,
    end=END_DATE,
    interval=INTERVAL,
    max_frame_length=MAX_FRAME_LENGTH,
)
```

[1]: https://eurogard.de
[2]: https://eurogard.de/software/m2v/
[3]: https://docs.astral.sh/uv/
