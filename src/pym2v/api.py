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

    def get_user_info(self):
        response = self._session.get(
            f"{self._settings.base_url}/backend/user-controller/meGUI",
        )
        return response.json()
