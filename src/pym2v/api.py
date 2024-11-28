import asyncio
from json import JSONDecodeError
from typing import Any

import pandas as pd
from loguru import logger
from oauthlib.oauth2 import LegacyApplicationClient
from requests_oauthlib import OAuth2Session
from tenacity import retry, stop_after_attempt, wait_exponential_jitter
from tqdm import tqdm

from .constants import TOKEN_ROUTE
from .settings import SETTINGS, Settings
from .types import IntInput, TsInput
from .utils import batch_interval, log_retry_attempt

_limit = asyncio.Semaphore(5)


class EurogardAPI:
    def __init__(self, settings: Settings = SETTINGS):
        self._settings = settings
        self._token_url = settings.base_url + TOKEN_ROUTE
        self._session = self.create_session()

    def create_session(self) -> OAuth2Session:
        extras: dict[str, Any] = {
            "client_id": self._settings.client_id,
            "client_secret": self._settings.client_secret,
        }

        client = LegacyApplicationClient(client_id=self._settings.client_id)
        oauth = OAuth2Session(
            client=client,
            auto_refresh_url=self._token_url,
            auto_refresh_kwargs=extras,
            token_updater=lambda x: x,
        )

        oauth.fetch_token(
            token_url=self._token_url,
            username=self._settings.username,
            password=self._settings.password,
            **extras,
        )

        return oauth

    def get_user_info(self) -> dict[str, Any]:
        response = self._session.get(
            f"{self._settings.base_url}/backend/user-controller/meGUI",
        )
        return response.json()

    def get_routers(
        self, page: int = 0, size: int = 10, sort: str = "name", order: str = "asc", filter: str = "__archived:false"
    ) -> dict[str, Any]:
        params = {
            "page": page,
            "size": size,
            "sort": sort,
            "order": order,
            "filter": filter,
        }
        response = self._session.get(
            f"{self._settings.base_url}/backend/thing-gui-controller/filter",
            params=params,
        )
        response.raise_for_status()

        return response.json()

    def get_machines(
        self, page: int = 0, size: int = 10, sort: str = "name", order: str = "asc", filter: str = "__archived:false"
    ) -> dict[str, Any]:
        params = {
            "page": page,
            "size": size,
            "sort": sort,
            "order": order,
            "filter": filter,
        }
        response = self._session.get(
            f"{self._settings.base_url}/backend/machine-gui-controller/filter",
            params=params,
        )
        return response.json()

    def get_machine_measurements(
        self,
        machine_uuid: str,
        page: int = 0,
        size: int = 10,
        sort: str = "updatedAt",
        order: str = "desc",
        filter: str = "__archived:false",
    ) -> dict[str, Any]:
        params = {"page": page, "size": size, "sort": sort, "order": order, "filter": filter}

        response = self._session.get(
            f"{self._settings.base_url}/backend/machine-controller/{machine_uuid}/measurements",
            params=params,
        )
        response.raise_for_status()

        return response.json()

    def get_machine_setpoints(
        self,
        machine_uuid: str,
        page: int = 0,
        size: int = 10,
        sort: str = "updatedAt",
        order: str = "desc",
        filter: str = "__archived:false",
    ) -> dict[str, Any]:
        params = {
            "page": page,
            "size": size,
            "sort": sort,
            "order": order,
            "filter": filter,
        }

        response = self._session.get(
            f"{self._settings.base_url}/backend/machine-controller/{machine_uuid}/set-points",
            params=params,
        )
        response.raise_for_status()

        return response.json()

    def send_machine_setpoint(
        self, data_definition_key_item_uuid: str, machine_uuid: str, set_point_value: str, timestamp: int
    ) -> dict[str, Any]:
        data = {
            "dataDefinitionKeyItemUuid": data_definition_key_item_uuid,
            "machineUuid": machine_uuid,
            "setPointValue": set_point_value,
            "timestamp": timestamp,
        }

        response = self._session.post(
            f"{self._settings.base_url}/backend/data-definition-key-item-controller/set-point",
            json=data,
        )
        response.raise_for_status()

        return response.json()

    @retry(stop=stop_after_attempt(5), wait=wait_exponential_jitter(max=10, jitter=3), before=log_retry_attempt)
    def get_historical_data(
        self, machine_uuid: str, data_definition_key_item_names: list[str], start: int, end: int, interval_in_s: int
    ) -> dict[str, Any]:
        data = {
            "condition": "",
            "values": data_definition_key_item_names,
            "start": start,
            "end": end,
            "machineUuid": machine_uuid,
            "intervalInS": interval_in_s,
        }

        logger.debug(f"Calling get_historical_data with {data=}")
        response = self._session.post(
            f"{self._settings.base_url}/backend/machine-controller/postDataByRangeAndInterval",
            json=data,
        )

        response.raise_for_status()
        try:
            result = response.json()
        except JSONDecodeError:
            logger.error(f"Error decoding JSON: {response.text}")
            raise

        return result

    def get_frame_from_names(
        self, machine_uuid: str, names: list[str], start: TsInput, end: TsInput, interval: IntInput
    ) -> pd.DataFrame:
        ts_start = pd.Timestamp(start)
        ts_end = pd.Timestamp(end)
        int_interval = pd.Timedelta(interval)

        result = self.get_historical_data(
            machine_uuid,
            data_definition_key_item_names=names,
            start=int(ts_start.timestamp() * 1000),
            end=int(ts_end.timestamp() * 1000),
            interval_in_s=int(int_interval.total_seconds()),
        )

        dfs = {}
        for res in result["results"]:
            dff = pd.DataFrame.from_records(res["values"])
            dff = dff.set_index(pd.to_datetime(dff["timestamp"], unit="ms"))
            dfs[res["dataDefinitionKeyItemName"]] = dff["value"]

        if all(d.empty for d in dfs.values()):
            logger.warning(f"No data found for {names=} in the interval {start=} -> {end=}")
            df = pd.DataFrame()
        else:
            df = pd.concat(dfs, axis="columns")

        return df

    def get_long_frame_from_names(
        self,
        machine_uuid: str,
        names: list[str],
        start: TsInput,
        end: TsInput,
        interval: IntInput,
        max_frame_length: IntInput,
        show_progress: bool = False,
    ) -> pd.DataFrame:
        batches = list(batch_interval(start, end, max_frame_length))
        if show_progress:
            batches = tqdm(batches)
        dfs = []

        for left, right in tqdm(batches):
            data = self.get_frame_from_names(
                machine_uuid=machine_uuid, names=names, start=left, end=right, interval=interval
            )
            if not data.empty:
                dfs.append(data)

        df = pd.concat(dfs)
        return df

    async def asmart_get_frame_from_names(
        self,
        machine_uuid: str,
        names: list[str],
        start: TsInput,
        end: TsInput,
        interval: IntInput,
        timeout: int = 15,
        max_recursion: int = 10,
    ) -> pd.DataFrame:
        ts_start = pd.Timestamp(start)
        ts_end = pd.Timestamp(end)
        int_interval = pd.Timedelta(interval)
        loop = asyncio.get_event_loop()

        # Try to get the data with self.get_frame_from_names with a timeout of `timeout` seconds
        # if it fails, split time interval in run the function recursively with each half
        try:
            # run the function in run_in_executor
            task = loop.run_in_executor(
                None,
                self.get_frame_from_names,
                machine_uuid,
                names,
                ts_start,
                ts_end,
                int_interval,
            )
            async with _limit:
                df = await asyncio.wait_for(task, timeout=timeout)

        except asyncio.TimeoutError:
            logger.info(f"Request took more than {timeout=}s -> splitting the interval")
            if max_recursion == 0:
                raise RecursionError("Max recursion depth reached")

            mid = ts_start + (ts_end - ts_start) / 2
            # Round mid down to full minutes
            mid = mid.floor("min")

            logger.info(f"New intervals: {ts_start=} -> {mid=} and {mid=} -> {ts_end=}")

            frames = await asyncio.gather(
                self.asmart_get_frame_from_names(
                    machine_uuid, names, ts_start, mid, int_interval, timeout, max_recursion - 1
                ),
                self.asmart_get_frame_from_names(
                    machine_uuid, names, mid, ts_end, int_interval, timeout, max_recursion - 1
                ),
            )

            df = pd.concat(frames, axis="index")

        return df
