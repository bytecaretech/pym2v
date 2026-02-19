from datetime import datetime, timedelta

import polars as pl
import pytest
from httpx import Response

from pym2v.utils import batch_interval


def test_get_user_info(api, mocker):
    mock_get = mocker.patch.object(api._client, "get")
    mock_response = mocker.Mock(spec=Response)
    mock_response.json.return_value = {"username": "test_user"}
    mock_get.return_value = mock_response

    user_info = api.get_user_info()
    assert user_info == {"username": "test_user"}
    mock_get.assert_called_once_with("/backend/user-controller/meGUI")


def test_get_routers(api, mocker):
    mock_get = mocker.patch.object(api._client, "get")
    mock_response = mocker.Mock(spec=Response)
    mock_response.json.return_value = {"routers": []}
    mock_get.return_value = mock_response

    routers = api.get_routers()
    assert routers == {"routers": []}
    mock_get.assert_called_once_with(
        "/backend/thing-gui-controller/filter",
        params={"page": 0, "size": 10, "sort": "name", "order": "asc", "filter": "__archived:false"},
    )


def test_get_machines(api, mocker):
    mock_get = mocker.patch.object(api._client, "get")
    mock_response = mocker.Mock(spec=Response)
    mock_response.json.return_value = {"machines": []}
    mock_get.return_value = mock_response

    machines = api.get_machines()
    assert machines == {"machines": []}
    mock_get.assert_called_once()


@pytest.mark.parametrize(("name", "expected"), [("test", "123"), ("non_existing_machine", None)])
def test_get_machine_uuid(api, name, expected):
    data = {"entities": [{"name": "test", "uuid": "123"}, {"name": "test2", "uuid": "456"}]}

    actual = api.get_machine_uuid(machine_name=name, machines=data)

    assert actual == expected


def test_get_machine_measurement_names(api, mocker):
    mock_get = mocker.patch.object(api._client, "get")
    mock_response = mocker.Mock(spec=Response)
    mock_response.json.return_value = {"measurements": []}
    mock_get.return_value = mock_response

    machine_uuid = "1234"
    measurements = api.get_machine_measurement_names(machine_uuid=machine_uuid)
    assert measurements == {"measurements": []}
    mock_get.assert_called_once_with(
        f"/backend/machine-controller/{machine_uuid}/measurements",
        params={"page": 0, "size": 10, "sort": "updatedAt", "order": "desc", "filter": "__archived:false"},
    )


def test_get_machine_setpoints(api, mocker):
    mock_get = mocker.patch.object(api._client, "get")
    mock_response = mocker.Mock(spec=Response)
    mock_response.json.return_value = {"setpoints": []}
    mock_get.return_value = mock_response

    machine_uuid = "1234"
    setpoints = api.get_machine_setpoints(machine_uuid=machine_uuid)
    assert setpoints == {"setpoints": []}
    mock_get.assert_called_once_with(
        "/backend/machine-controller/1234/set-points",
        params={"page": 0, "size": 10, "sort": "updatedAt", "order": "desc", "filter": "__archived:false"},
    )


def test_get_historical_data(api, mocker):
    mock_post = mocker.patch.object(api._client, "post")
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
        "/backend/machine-controller/postDataByRangeAndInterval",
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
            {"dataDefinitionKeyItemName": "name1", "values": [{"timestamp": 1234567890000, "value": 1}]},
            {"dataDefinitionKeyItemName": "name2", "values": [{"timestamp": 1234567890000, "value": 2}]},
        ]
    }

    start = datetime.now() - timedelta(days=1)
    end = datetime.now()
    interval = timedelta(hours=1)

    result = api.get_frame_from_names(
        machine_uuid="1234", names=["name1", "name2"], start=start, end=end, interval=interval
    )

    assert isinstance(result, pl.DataFrame)
    assert "name1" in result.columns
    assert "name2" in result.columns
    assert "timestamp" in result.columns
    mock_get_historical_data.assert_called_once()


def test_get_long_frame_from_names(api, mocker):
    mock_get_frame = mocker.patch.object(api, "get_frame_from_names")
    mock_get_frame.return_value = pl.DataFrame({"timestamp": [datetime(2021, 6, 1, 12, 0)], "value": [1.0]})

    result = api.get_long_frame_from_names(
        machine_uuid="1234",
        names=["name1"],
        start=datetime(2021, 6, 1),
        end=datetime(2021, 6, 3),
        interval=timedelta(hours=1),
        max_frame_length=timedelta(days=1),
    )

    assert isinstance(result, pl.DataFrame)
    assert mock_get_frame.call_count == 2  # 2 days = 2 batches


def test_batch_interval():
    batches = list(batch_interval(datetime(2021, 6, 1), datetime(2021, 6, 3), timedelta(days=1)))

    assert len(batches) == 2
    assert batches[0][0] == datetime(2021, 6, 1)
    assert batches[0][1] == datetime(2021, 6, 2)
    assert batches[1][0] == datetime(2021, 6, 2)
    assert batches[1][1] == datetime(2021, 6, 3)
