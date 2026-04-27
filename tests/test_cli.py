import json
from datetime import timedelta

import polars as pl
import pytest

import pym2v.cli as cli


def test_parse_timedelta_seconds_returns_timedelta():
    value = "60"
    result = cli.parse_timedelta_seconds(value)
    assert result == timedelta(seconds=60)


def test_parse_cli_args_returns_typed_data_args():
    args = cli.parse_cli_args(
        [
            "data",
            "--machine-uuid",
            "machine-id",
            "--names",
            "temp",
            "--start",
            "2025-01-01T00:00:00",
            "--end",
            "2025-01-01T01:00:00",
        ]
    )

    assert isinstance(args, cli.DataCommandArgs)
    assert args.machine_uuid == "machine-id"
    assert args.names == ["temp"]
    assert args.interval == timedelta(seconds=60)
    assert args.max_frame_length == timedelta(days=30)


def test_parse_cli_args_returns_typed_routers_args():
    args = cli.parse_cli_args(["routers"])

    assert isinstance(args, cli.RoutersCommandArgs)
    assert args.page == 0
    assert args.size == 10
    assert args.sort == "name"


def test_main_user_info_happy_path(mocker, capsys):
    mock_api = mocker.Mock()
    mock_api.get_user_info.return_value = {"username": "alice"}
    mocker.patch("pym2v.cli.EurogardAPI", return_value=mock_api)
    result = cli.main(["user-info"])
    captured = capsys.readouterr()
    assert result == 0
    assert json.loads(captured.out) == {"username": "alice"}
    mock_api.get_user_info.assert_called_once_with()


def test_main_routers_dispatches_args(mocker, capsys):
    mock_api = mocker.Mock()
    mock_api.get_routers.return_value = {"entities": []}
    mocker.patch("pym2v.cli.EurogardAPI", return_value=mock_api)
    result = cli.main(
        ["routers", "--page", "2", "--size", "5", "--sort", "online", "--order", "desc", "--filter", "active"]
    )
    capsys.readouterr()
    assert result == 0
    mock_api.get_routers.assert_called_once_with(page=2, size=5, sort="online", order="desc", filter="active")


def test_main_machine_uuid_not_found_returns_structured_error(mocker, capsys):
    mock_api = mocker.Mock()
    mock_api.get_machines.return_value = {"entities": []}
    mock_api.get_machine_uuid.return_value = None
    mocker.patch("pym2v.cli.EurogardAPI", return_value=mock_api)
    result = cli.main(["machine-uuid", "--name", "missing-machine"])
    captured = capsys.readouterr()
    assert result == 1
    payload = json.loads(captured.err)
    assert payload["error"]["type"] == "CliError"
    assert "missing-machine" in payload["error"]["message"]


def test_main_data_stdout_csv_happy_path(mocker, capsys):
    mock_api = mocker.Mock()
    mock_api.get_long_frame_from_names.return_value = pl.DataFrame(
        {"timestamp": ["2025-01-01T00:00:00"], "temp": [1.2]}
    )
    mocker.patch("pym2v.cli.EurogardAPI", return_value=mock_api)
    result = cli.main(
        [
            "data",
            "--machine-uuid",
            "machine-id",
            "--names",
            "temp",
            "--start",
            "2025-01-01T00:00:00",
            "--end",
            "2025-01-01T01:00:00",
            "--format",
            "csv",
        ]
    )
    captured = capsys.readouterr()
    assert result == 0
    assert "timestamp,temp" in captured.out
    mock_api.get_long_frame_from_names.assert_called_once_with(
        machine_uuid="machine-id",
        names=["temp"],
        start=mocker.ANY,
        end=mocker.ANY,
        interval=timedelta(seconds=60),
        max_frame_length=timedelta(days=30),
    )


def test_main_data_parquet_requires_output(mocker, capsys):
    mock_api = mocker.Mock()
    mocker.patch("pym2v.cli.EurogardAPI", return_value=mock_api)
    result = cli.main(
        [
            "data",
            "--machine-uuid",
            "machine-id",
            "--names",
            "temp",
            "--start",
            "2025-01-01T00:00:00",
            "--end",
            "2025-01-01T01:00:00",
            "--format",
            "parquet",
        ]
    )
    captured = capsys.readouterr()
    assert result == 1
    payload = json.loads(captured.err)
    assert payload["error"]["type"] == "CliError"
    assert "--output" in payload["error"]["message"]
    mock_api.get_long_frame_from_names.assert_not_called()


def test_main_data_writes_to_output_file(mocker, capsys, tmp_path):
    output_path = tmp_path / "out.json"
    mock_api = mocker.Mock()
    mock_api.get_long_frame_from_names.return_value = pl.DataFrame(
        {"timestamp": ["2025-01-01T00:00:00"], "temp": [1.2]}
    )
    mocker.patch("pym2v.cli.EurogardAPI", return_value=mock_api)
    result = cli.main(
        [
            "data",
            "--machine-uuid",
            "machine-id",
            "--names",
            "temp",
            "--start",
            "2025-01-01T00:00:00",
            "--end",
            "2025-01-01T01:00:00",
            "--format",
            "json",
            "--output",
            str(output_path),
        ]
    )
    captured = capsys.readouterr()
    assert result == 0
    assert output_path.exists()
    assert json.loads(captured.out) == {"output": str(output_path), "format": "json"}


def test_main_data_rejects_start_greater_or_equal_end(mocker, capsys):
    mock_api = mocker.Mock()
    mocker.patch("pym2v.cli.EurogardAPI", return_value=mock_api)
    result = cli.main(
        [
            "data",
            "--machine-uuid",
            "machine-id",
            "--names",
            "temp",
            "--start",
            "2025-01-01T01:00:00",
            "--end",
            "2025-01-01T01:00:00",
        ]
    )
    captured = capsys.readouterr()
    assert result == 1
    payload = json.loads(captured.err)
    assert payload["error"]["type"] == "CliError"
    assert "--start" in payload["error"]["message"]
    assert "--end" in payload["error"]["message"]
    mock_api.get_long_frame_from_names.assert_not_called()


def test_main_data_rejects_mixed_naive_and_aware_datetimes(mocker, capsys):
    mock_api = mocker.Mock()
    mocker.patch("pym2v.cli.EurogardAPI", return_value=mock_api)
    result = cli.main(
        [
            "data",
            "--machine-uuid",
            "machine-id",
            "--names",
            "temp",
            "--start",
            "2025-01-01T00:00:00+00:00",
            "--end",
            "2025-01-01T01:00:00",
        ]
    )
    captured = capsys.readouterr()
    assert result == 1
    payload = json.loads(captured.err)
    assert payload["error"]["type"] == "CliError"
    assert "timezone" in payload["error"]["message"].lower()
    mock_api.get_long_frame_from_names.assert_not_called()


@pytest.mark.parametrize(
    ("argv", "expected_message"),
    [
        (["routers", "--size", "abc"], "--size"),
        (["routers", "--page", "abc"], "--page"),
        (["routers", "--size", "0"], "--size"),
        (["routers", "--page", "-1"], "--page"),
        (["machine-uuid", "--name", "foo", "--size", "0"], "--size"),
        (["machine-uuid", "--name", "foo", "--size", "abc"], "--size"),
        (
            [
                "data",
                "--machine-uuid",
                "machine-id",
                "--names",
                "temp",
                "--start",
                "2025-01-01T00:00:00",
                "--end",
                "2025-01-01T01:00:00",
                "--interval",
                "0",
            ],
            "--interval",
        ),
        (
            [
                "data",
                "--machine-uuid",
                "machine-id",
                "--names",
                "temp",
                "--start",
                "2025-01-01T00:00:00",
                "--end",
                "2025-01-01T01:00:00",
                "--interval",
                "abc",
            ],
            "--interval",
        ),
        (
            [
                "data",
                "--machine-uuid",
                "machine-id",
                "--names",
                "temp",
                "--start",
                "2025-01-01T00:00:00",
                "--end",
                "2025-01-01T01:00:00",
                "--max-frame-length",
                "0",
            ],
            "--max-frame-length",
        ),
        (
            [
                "data",
                "--machine-uuid",
                "machine-id",
                "--names",
                "temp",
                "--start",
                "2025-01-01T00:00:00",
                "--end",
                "2025-01-01T01:00:00",
                "--max-frame-length",
                "abc",
            ],
            "--max-frame-length",
        ),
        (
            [
                "data",
                "--machine-uuid",
                "machine-id",
                "--names",
                "temp",
                "--start",
                "not-a-date",
                "--end",
                "2025-01-01T01:00:00",
            ],
            "--start",
        ),
        (
            [
                "data",
                "--machine-uuid",
                "machine-id",
                "--names",
                "temp",
                "--start",
                "2025-01-01T00:00:00",
                "--end",
                "not-a-date",
            ],
            "--end",
        ),
    ],
)
def test_main_invalid_cli_usage_returns_exit_code_2(argv, expected_message, capsys):
    result = cli.main(argv)
    captured = capsys.readouterr()
    assert result == 2
    assert "usage:" in captured.err
    assert expected_message in captured.err


def test_parser_top_level_help_includes_command_descriptions():
    parser = cli.build_parser()

    help_output = parser.format_help()

    assert "show user profile details" in help_output.lower()
    assert "list machines available to your account" in help_output.lower()


def test_parser_data_help_includes_safe_metavars_and_guidance(capsys):
    parser = cli.build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["data", "--help"])
    help_output = capsys.readouterr().out

    assert "--start DATETIME" in help_output
    assert "--end DATETIME" in help_output
    assert "--interval SECONDS" in help_output
    assert "--max-frame-length SECONDS" in help_output
    assert "--output PATH" in help_output
    assert "iso-8601" in help_output.lower()
