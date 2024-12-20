import pytest

from pym2v.api import EurogardAPI
from pym2v.settings import Settings

TEST_URL = "https://example.com/"


@pytest.fixture
def api(mocker):
    settings = Settings(
        base_url=TEST_URL,
        client_id="client_id",
        client_secret="client_secret",  # noqa: S106
        username="username",
        password="password",  # noqa: S106
    )

    mocker.patch("requests_oauthlib.oauth2_session.OAuth2Session.fetch_token")
    api = EurogardAPI(settings)

    return api
