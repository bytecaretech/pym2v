"""API client for interacting with the Eurogard backend services."""

import asyncio
from datetime import datetime, timedelta
from json import JSONDecodeError
from typing import Any

import httpx
import polars as pl
from httpx_auth import OAuth2ResourceOwnerPasswordCredentials
from tenacity import retry, stop_after_attempt, wait_exponential_jitter
from tqdm.auto import tqdm

from .constants import TOKEN_ROUTE
from .logger import get_logger
from .settings import Settings
from .utils import _log_retry_attempt, batch_interval

logger = get_logger(__name__)


class EurogardAPI:
    """Pythonic interface to interact with the Eurogard backend services."""

    def __init__(self, settings: Settings | None = None, max_concurrent_requests: int = 5):
        """
        EurogardAPI is the main class for interacting with the Eurogard m2v IoT platform.

        If settings are not provided, they will be loaded from environment variables or a .env file.

        Args:
            settings (Settings, optional): An instance of the Settings class containing API configuration.
                Defaults to None.
            max_concurrent_requests (int, optional): Maximum number of concurrent async requests.
                Defaults to 5.
        """
        if settings is None:
            settings = Settings()  # type: ignore
        self._settings = settings
        self._token_url = f"{settings.base_url}{TOKEN_ROUTE}"
        self._auth = self._create_auth()
        self._client = httpx.Client(auth=self._auth, base_url=settings.base_url)
        self._semaphore = asyncio.Semaphore(max_concurrent_requests)

    def _create_auth(self) -> OAuth2ResourceOwnerPasswordCredentials:
        """Create OAuth2 authentication handler.

        Returns:
            OAuth2ResourceOwnerPasswordCredentials: Configured auth handler.
        """
        return OAuth2ResourceOwnerPasswordCredentials(
            token_url=self._token_url,
            username=self._settings.username,
            password=self._settings.password.get_secret_value(),
            client_id=self._settings.client_id,
            client_secret=self._settings.client_secret.get_secret_value(),
        )

    def get_user_info(self) -> dict[str, Any]:
        """
        Retrieve user information.

        Returns:
            dict[str, Any]: User information.

        """
        response = self._client.get("/backend/user-controller/meGUI")
        response.raise_for_status()

        return response.json()

    def get_routers(
        self,
        page: int = 0,
        size: int = 10,
        sort: str = "name",
        order: str = "asc",
        filter: str = "__archived:false",
    ) -> dict[str, Any]:
        """
        Retrieve a list of routers.

        Args:
            page (int, optional): Page number, starting from 0. Defaults to 0.
            size (int, optional): Number of items per page. Defaults to 10.
            sort (str, optional): Sort field (e.g., name, companyName, online, locationName). Defaults to "name".
            order (str, optional): Sort order (asc or desc). Defaults to "asc".
            filter (str, optional): Filter criteria (e.g., __archived:false). Defaults to "__archived:false".

        Returns:
            dict[str, Any]: List of routers.
        """
        response = self._client.get(
            "/backend/thing-gui-controller/filter",
            params={
                "page": page,
                "size": size,
                "sort": sort,
                "order": order,
                "filter": filter,
            },
        )
        response.raise_for_status()

        return response.json()

    def get_machines(
        self,
        page: int = 0,
        size: int = 10,
        sort: str = "name",
        order: str = "asc",
        filter: str = "__archived:false",
    ) -> dict[str, Any]:
        """
        Retrieve a list of machines.

        Args:
            page (int, optional): Page number, starting from 0. Defaults to 0.
            size (int, optional): Number of items per page. Defaults to 10.
            sort (str, optional): Sort field (e.g., name, companyName, thingName, machineTypeDefinitionName,
                lastConnection). Defaults to "name".
            order (str, optional): Sort order (asc or desc). Defaults to "asc".
            filter (str, optional): Filter criteria (e.g., __archived:false). Defaults to "__archived:false".

        Returns:
            dict[str, Any]: List of machines.
        """
        response = self._client.get(
            "/backend/machine-gui-controller/filter",
            params={
                "page": page,
                "size": size,
                "sort": sort,
                "order": order,
                "filter": filter,
            },
        )
        response.raise_for_status()

        return response.json()

    @staticmethod
    def get_machine_uuid(machine_name: str, machines: dict[str, Any]) -> str | None:
        """
        Get the machine UUID matching the specified name from a list of machines.

        Args:
            machine_name (str): The name of the machine to search for.
            machines: A dictionary containing machine data with an 'entities' key
                     that holds a list of machine objects. Each machine object
                     should have 'name' and 'uuid' fields.

        Returns:
            str | None: UUID for machine that match the given name.
                    Returns None if no matches are found.
        """
        matches = [m["uuid"] for m in machines["entities"] if m["name"] == machine_name]

        if len(matches) == 0:
            return None

        return matches[0]

    def get_machine_measurements(
        self,
        machine_uuid: str,
        page: int = 0,
        size: int = 10,
        sort: str = "updatedAt",
        order: str = "desc",
        filter: str = "__archived:false",
    ) -> dict[str, Any]:
        """
        Retrieve measurements for a specific machine.

        Args:
            machine_uuid (str): Machine UUID.
            page (int, optional): Page number, starting from 0. Defaults to 0.
            size (int, optional): Number of items per page. Defaults to 10.
            sort (str, optional): Sort field (e.g., updatedAt). Defaults to "updatedAt".
            order (str, optional): Sort order (asc or desc). Defaults to "desc".
            filter (str, optional): Filter criteria (e.g., __archived:false). Defaults to "__archived:false".

        Returns:
            dict[str, Any]: Machine measurements.
        """
        response = self._client.get(
            f"/backend/machine-controller/{machine_uuid}/measurements",
            params={
                "page": page,
                "size": size,
                "sort": sort,
                "order": order,
                "filter": filter,
            },
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
        """
        Retrieve setpoints for a specific machine.

        Args:
            machine_uuid (str): Machine UUID.
            page (int, optional): Page number, starting from 0. Defaults to 0.
            size (int, optional): Number of items per page. Defaults to 10.
            sort (str, optional): Sort field (e.g., updatedAt). Defaults to "updatedAt".
            order (str, optional): Sort order (asc or desc). Defaults to "desc".
            filter (str, optional): Filter criteria (e.g., __archived:false). Defaults to "__archived:false".

        Returns:
            dict[str, Any]: Machine setpoints.
        """
        response = self._client.get(
            f"/backend/machine-controller/{machine_uuid}/set-points",
            params={
                "page": page,
                "size": size,
                "sort": sort,
                "order": order,
                "filter": filter,
            },
        )
        response.raise_for_status()

        return response.json()

    @retry(stop=stop_after_attempt(5), wait=wait_exponential_jitter(max=10, jitter=3), before=_log_retry_attempt)
    def get_historical_data(
        self,
        machine_uuid: str,
        data_definition_key_item_names: list[str],
        start: int,
        end: int,
        interval_in_s: int,
    ) -> dict[str, Any]:
        """
        Retrieve historical data for a specific machine.

        Args:
            machine_uuid (str): Machine UUID.
            data_definition_key_item_names (list[str]): List of data definition key item names.
            start (int): Start timestamp in milliseconds.
            end (int): End timestamp in milliseconds.
            interval_in_s (int): Interval in seconds.

        Returns:
            dict[str, Any]: Historical data.
        """
        data = {
            "condition": "",
            "values": data_definition_key_item_names,
            "start": start,
            "end": end,
            "machineUuid": machine_uuid,
            "intervalInS": interval_in_s,
        }

        logger.debug("Calling get_historical_data with data=%s", data)
        response = self._client.post(
            "/backend/machine-controller/postDataByRangeAndInterval",
            json=data,
        )

        response.raise_for_status()

        try:
            result = response.json()
            return result
        except JSONDecodeError:
            logger.error("Error decoding JSON: %s", response.text)
            raise

    def get_frame_from_names(
        self,
        machine_uuid: str,
        names: list[str],
        start: datetime,
        end: datetime,
        interval: timedelta,
    ) -> pl.DataFrame:
        """
        Retrieve a DataFrame of historical data for a specific machine.

        Args:
            machine_uuid (str): Machine UUID.
            names (list[str]): List of data definition key item names.
            start (datetime): Start timestamp.
            end (datetime): End timestamp.
            interval (timedelta): Interval between data points.

        Returns:
            pl.DataFrame: DataFrame of historical data with timestamp column.
        """
        result = self.get_historical_data(
            machine_uuid,
            data_definition_key_item_names=names,
            start=int(start.timestamp() * 1000),
            end=int(end.timestamp() * 1000),
            interval_in_s=int(interval.total_seconds()),
        )

        dataframes = []
        for res in result["results"]:
            if not res["values"]:
                continue
            df = pl.DataFrame(res["values"])
            df = df.with_columns(pl.from_epoch("timestamp", time_unit="ms").alias("timestamp")).select(
                ["timestamp", pl.col("value").alias(res["dataDefinitionKeyItemName"])]
            )
            dataframes.append(df)

        if not dataframes:
            logger.warning("No data found for names=%s in the interval start=%s -> end=%s", names, start, end)
            return pl.DataFrame()

        df_result = dataframes[0]
        for df in dataframes[1:]:
            df_result = df_result.join(df, on="timestamp", how="full", coalesce=True)

        return df_result.sort("timestamp")

    def get_long_frame_from_names(
        self,
        machine_uuid: str,
        names: list[str],
        start: datetime,
        end: datetime,
        interval: timedelta,
        max_frame_length: timedelta,
        show_progress: bool = False,
    ) -> pl.DataFrame:
        """
        Retrieve a long DataFrame of historical data for a specific machine.

        Args:
            machine_uuid (str): Machine UUID.
            names (list[str]): List of data definition key item names.
            start (datetime): Start timestamp.
            end (datetime): End timestamp.
            interval (timedelta): Time interval between data points.
            max_frame_length (timedelta): Maximum interval length for a single API request.
            show_progress (bool, optional): Whether to show progress. Defaults to False.

        Returns:
            pl.DataFrame: Long DataFrame of historical data.
        """
        batches = list(batch_interval(start, end, max_frame_length))
        if show_progress:
            batches = tqdm(batches)

        dataframes = []

        for left, right in batches:
            data = self.get_frame_from_names(
                machine_uuid=machine_uuid,
                names=names,
                start=left,
                end=right,
                interval=interval,
            )
            if not data.is_empty():
                dataframes.append(data)

        if not dataframes:
            return pl.DataFrame()

        return pl.concat(dataframes).sort("timestamp")

    async def aget_frame_from_names(
        self,
        machine_uuid: str,
        names: list[str],
        start: datetime,
        end: datetime,
        interval: timedelta,
        max_frame_length: timedelta,
        timeout: float = 30.0,
    ) -> pl.DataFrame:
        """
        Asynchronously retrieve a DataFrame of historical data for a specific machine.

        Fetches data in batches concurrently for speedup.

        Args:
            machine_uuid (str): Machine UUID.
            names (list[str]): List of data definition key item names.
            start (datetime): Start timestamp.
            end (datetime): End timestamp.
            interval (timedelta): Interval between data points.
            max_frame_length (timedelta): Maximum length of each batch.
            timeout (float, optional): Timeout in seconds. Defaults to 30.0.

        Returns:
            pl.DataFrame: DataFrame of historical data.
        """
        batches = list(batch_interval(start, end, max_frame_length))

        async def fetch_batch(batch_start: datetime, batch_end: datetime) -> pl.DataFrame:
            async with self._semaphore:
                async with httpx.AsyncClient(
                    auth=self._auth, base_url=self._settings.base_url, timeout=timeout
                ) as client:
                    data = {
                        "condition": "",
                        "values": names,
                        "start": int(batch_start.timestamp() * 1000),
                        "end": int(batch_end.timestamp() * 1000),
                        "machineUuid": machine_uuid,
                        "intervalInS": int(interval.total_seconds()),
                    }
                    response = await client.post(
                        "/backend/machine-controller/postDataByRangeAndInterval",
                        json=data,
                    )
                    response.raise_for_status()
                    result = response.json()

                dataframes = []
                for res in result["results"]:
                    if not res["values"]:
                        continue
                    df = pl.DataFrame(res["values"])
                    df = df.with_columns(pl.from_epoch("timestamp", time_unit="ms").alias("timestamp")).select(
                        ["timestamp", pl.col("value").alias(res["dataDefinitionKeyItemName"])]
                    )
                    dataframes.append(df)

                if not dataframes:
                    return pl.DataFrame()

                df_result = dataframes[0]
                for df in dataframes[1:]:
                    df_result = df_result.join(df, on="timestamp", how="full", coalesce=True)

                return df_result

        results = await asyncio.gather(*[fetch_batch(left, right) for left, right in batches])
        dataframes = [df for df in results if not df.is_empty()]

        if not dataframes:
            return pl.DataFrame()

        return pl.concat(dataframes).sort("timestamp")
