# pym2v
Python wrapper for Eurogard m2v IoT platform

## Prerequisites
Before working on this project, ensure you have the following installed:
- [uv](https://uv.link/installation) for managing virtual environments.

## Installation
To install pym2v, use pip:
```bash
git clone https://github.com/bytecaretech/pym2v.git
cd pym2v
pip install .
```

## Usage
Here is a basic example of how to use pym2v:
```python
import pandas as pd
from loguru import logger

from pym2v.api import EurogardAPI

logger.add("notebook.log")

api = EurogardAPI()

machine_uuid = str(api.get_machines()["entities"][0]["uuid"])
result = api.get_machine_measurements(machine_uuid, page=5)
measures = pd.DataFrame.from_dict(result["entities"])

data = api.get_long_frame_from_names(
    machine_uuid=machine_uuid,
    names=measures["name"].to_list()[:3],
    start="2024-01-01",
    end="2025-01-01",
    interval="60s",
    max_frame_length="30D",
)

data.info()
print(f"Completeness: {len(data.index) / len(pd.date_range(data.index[0], data.index[-1], freq='60s')):.3%}")
print(f"Duplicates: {data.index.duplicated().sum()}")
```

## Authentication
To authenticate with the Eurogard API, you need to provide your credentials. You can do this either by setting environment variables or by configuring the `Settings` object directly.

### Using Environment Variables
Create a `.env` file in the root of your project and add the following lines, replacing the placeholder values with your actual credentials:

```bash
# filepath: ./.env
# Eurogard API configuration
EUROGARD_BASE_URL=https://eurogard.cloud
EUROGARD_USERNAME=your_username_here
EUROGARD_PASSWORD=your_password_here
EUROGARD_CLIENT_ID=your_client_id_here
EUROGARD_CLIENT_SECRET=your_client_secret_here
```

### Using the Settings Object
Alternatively, you can configure the `Settings` object directly in your code:

```python
from pym2v.settings import Settings

settings = Settings(
    base_url="https://eurogard.cloud",
    username="your_username_here",
    password="your_password_here",
    client_id="your_client_id_here",
    client_secret="your_client_secret_here"
)
```

### Default Behavior
If you do not provide settings explicitly, the `EurogardAPI` will attempt to load settings from environment variables or a `.env` file. See `.env.sample` for example env vars.

## Setting Up the Project for Development
To set up the project for development, follow these steps:

1. Clone the repository:
```bash
git clone https://github.com/bytecaretech/pym2v.git
cd pym2v
```

2. Sync the environment (a `.venv` will be created if none exists):
```bash
uv sync
```

3. Install pre-commit hooks:
```bash
pre-commit install
```

Now you are ready to start developing pym2v!
