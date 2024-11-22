from oauthlib.oauth2 import LegacyApplicationClient
from requests_oauthlib import OAuth2Session

from .settings import SETTINGS, Settings

TOKEN_ROUTE = "/auth/realms/iiot-platform/protocol/openid-connect/token"


class EurogardAPI:
    def __init__(self, settings: Settings = SETTINGS):
        self._settings = settings
        self._session = self.create_session()

    def create_session(self):
        client = LegacyApplicationClient(client_id=self._settings.client_id)
        oauth = OAuth2Session(client=client)
        oauth.fetch_token(
            token_url=self._settings.base_url + TOKEN_ROUTE,
            username=self._settings.username,
            password=self._settings.password,
            client_id=self._settings.client_id,
            client_secret=self._settings.client_secret,
        )
        return oauth

    def get_user_info(self):
        response = self._session.get(
            f"{self._settings.base_url}/backend/user-controller/meGUI",
        )
        return response.json()
