"""Script to download the data from aixponic."""

import pandas as pd
from pym2v.api import EurogardAPI

# constants
DATE_FORMAT: str = "YYYY-mm-dd"
START_DATE: str = "2022-01-01"
END_DATE: str = "2025-03-14"
INTERVAL: str = "60s"
MAX_FRAME_LENGTH: str = "30D"
MACHINE_NAME: str = "Aquakultur"
DATA_PATH_LOCAL: str = "/Users/Vanilleeis/aixponic/aixponic/data_extracts"
NUM_SIGNALS: int = 100


# functions
def get_data_from_server(
    api: EurogardAPI,
    start_date: str = START_DATE,
    end_date: str = END_DATE,
    date_format: str = DATE_FORMAT,
    interval: str = INTERVAL,
    max_frame_length: str = MAX_FRAME_LENGTH,
    mach_name: str = MACHINE_NAME,
    num_features: int = NUM_SIGNALS,
) -> pd.DataFrame:
    """
    Get time series data from source using aixponic specific API paramater.

    Args:
        api (EurogardAPI): ...
        start_date (str): ...
        end_date (str): ...
        date_format (str): ...
        interval (str): ...
        max_frame_length (str): ...
        mach_name (str): ...
        num_features (int): ...

    Returns:
        Pandas dataframe with sensor data.
    """

    machines = api.get_machines()
    machine_uuid = [
        m["uuid"] for m in machines.get("entities") if m.get("name") == mach_name
    ][0]

    result = api.get_machine_measurements(machine_uuid, page=3, size=num_features)

    sensor_df = pd.DataFrame.from_dict(result["entities"])

    # get time series for the data and save on disk
    SENSOR_NAMES = sensor_df.name.to_list()

    data_df = api.get_long_frame_from_names(
        machine_uuid=machine_uuid,
        names=SENSOR_NAMES,
        start=start_date,
        end=end_date,
        interval=interval,
        max_frame_length=max_frame_length,
    )

    return data_df


if __name__ == "__main__":

    data_df = get_data_from_server(
        api=EurogardAPI(),
        start_date="2025-03-12",
    )

    data_df.to_parquet(f"{DATA_PATH_LOCAL}/data_df.parquet")
