from datetime import date, datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
from oauthlib.oauth2 import LegacyApplicationClient
from requests_oauthlib import OAuth2Session

from .constants import TOKEN_ROUTE
from .settings import SETTINGS, Settings

type TsInput = np.integer | pd.Timestamp | float | str | date | datetime | np.datetime64
type IntInput = str | int | pd.Timedelta | timedelta | np.timedelta64


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
        return response.json()

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
        response = self._session.post(
            f"{self._settings.base_url}/machine-controller/postDataByRangeAndInterval",
            json=data,
        )
        response.raise_for_status()

        return response.json()

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

        df = pd.concat(dfs, axis="columns")

        return df
