import pytest
from pydantic import SecretStr

from pym2v.api import EurogardAPI
from pym2v.settings import Settings


@pytest.fixture
def api(mocker):
    settings = Settings(
        base_url="https://example.com",
        client_id="client_id",
        client_secret=SecretStr("test"),  # noqa: S106
        username="username",
        password=SecretStr("test"),  # noqa: S106
    )

    mocker.patch("httpx_auth.OAuth2ResourceOwnerPasswordCredentials.__call__", return_value=None)
    api = EurogardAPI(settings)

    return api
