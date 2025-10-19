from datetime import datetime, timedelta

import pandas as pd
from requests.models import Response

TEST_URL = "https://example.com/"


def test_get_user_info(api, mocker):
    mock_get = mocker.patch.object(api._session, "get")
    mock_response = mocker.Mock(spec=Response)
    mock_response.json.return_value = {"username": "test_user"}
    mock_get.return_value = mock_response

    user_info = api.get_user_info()
    assert user_info == {"username": "test_user"}
    mock_get.assert_called_once_with(f"{TEST_URL}/backend/user-controller/meGUI")


def test_get_routers(api, mocker):
    mock_get = mocker.patch.object(api._session, "get")
    mock_response = mocker.Mock(spec=Response)
    mock_response.json.return_value = {"routers": []}
    mock_get.return_value = mock_response

    routers = api.get_routers()
    assert routers == {"routers": []}
    mock_get.assert_called_once_with(
        f"{TEST_URL}/backend/thing-gui-controller/filter",
        params={"page": 0, "size": 10, "sort": "name", "order": "asc", "filter": "__archived:false"},
    )


def test_get_machines(api, mocker):
    mock_get = mocker.patch.object(api._session, "get")
    mock_response = mocker.Mock(spec=Response)
    mock_response.json.return_value = {"machines": []}
    mock_get.return_value = mock_response

    machines = api.get_machines()
    assert machines == {"machines": []}
    mock_get.assert_called_once()


def test_get_machine_measurements(api, mocker):
    mock_get = mocker.patch.object(api._session, "get")
    mock_response = mocker.Mock(spec=Response)
    mock_response.json.return_value = {"measurements": []}
    mock_get.return_value = mock_response

    machine_uuid = "1234"
    measurements = api.get_machine_measurements(machine_uuid=machine_uuid)
    assert measurements == {"measurements": []}
    mock_get.assert_called_once_with(
        f"{TEST_URL}/backend/machine-controller/{machine_uuid}/measurements",
        params={"page": 0, "size": 10, "sort": "updatedAt", "order": "desc", "filter": "__archived:false"},
    )


def test_get_machine_setpoints(api, mocker):
    mock_get = mocker.patch.object(api._session, "get")
    mock_response = mocker.Mock(spec=Response)
    mock_response.json.return_value = {"setpoints": []}
    mock_get.return_value = mock_response

    machine_uuid = "1234"
    setpoints = api.get_machine_setpoints(machine_uuid=machine_uuid)
    assert setpoints == {"setpoints": []}
    mock_get.assert_called_once_with(
        f"{TEST_URL}/backend/machine-controller/1234/set-points",
        params={"page": 0, "size": 10, "sort": "updatedAt", "order": "desc", "filter": "__archived:false"},
    )


def test_get_historical_data(api, mocker):
    mock_post = mocker.patch.object(api._session, "post")
    mock_response = mocker.Mock(spec=Response)
    mock_response.json.return_value = {"results": []}
    mock_post.return_value = mock_response

    machine_uuid = "1234"
    historical_data = api.get_historical_data(
        machine_uuid=machine_uuid,
        data_definition_key_item_names=["name1", "name2"],
        start=1234567890,
        end=1234567891,
        interval_in_s=60,
    )
    assert historical_data == {"results": []}
    mock_post.assert_called_once_with(
        f"{TEST_URL}/backend/machine-controller/postDataByRangeAndInterval",
        json={
            "condition": "",
            "values": ["name1", "name2"],
            "start": 1234567890,
            "end": 1234567891,
            "machineUuid": "1234",
            "intervalInS": 60,
        },
    )


def test_get_frame_from_names(api, mocker):
    mock_get_historical_data = mocker.patch.object(api, "get_historical_data")
    mock_get_historical_data.return_value = {
        "results": [
            {"dataDefinitionKeyItemName": "name1", "values": [{"timestamp": 1234567890, "value": 1}]},
            {"dataDefinitionKeyItemName": "name2", "values": [{"timestamp": 1234567890, "value": 2}]},
        ]
    }

    start = datetime.now() - timedelta(days=1)
    end = datetime.now()
    interval = "1h"

    names = api.get_frame_from_names(
        machine_uuid="1234", names=["name1", "name2"], start=start, end=end, interval=interval
    )

    assert isinstance(names, pd.DataFrame)
    assert "name1" in names.columns
    assert "name2" in names.columns
    mock_get_historical_data.assert_called_once()
