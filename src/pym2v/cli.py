"""Command line interface for pym2v."""

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal, Sequence, TypeAlias

from pym2v.api import EurogardAPI

DEFAULT_INTERVAL = timedelta(seconds=60)
DEFAULT_MAX_FRAME_LENGTH = timedelta(days=30)


Order: TypeAlias = Literal["asc", "desc"]
DataFormat: TypeAlias = Literal["csv", "json", "parquet"]


@dataclass(frozen=True)
class UserInfoCommandArgs:
    """Typed args for the `user-info` command."""

    command: Literal["user-info"] = "user-info"


@dataclass(frozen=True)
class RoutersCommandArgs:
    """Typed args for the `routers` command."""

    page: int
    size: int
    sort: str
    order: Order
    filter: str
    command: Literal["routers"] = "routers"


@dataclass(frozen=True)
class MachinesCommandArgs:
    """Typed args for the `machines` command."""

    page: int
    size: int
    sort: str
    order: Order
    filter: str
    command: Literal["machines"] = "machines"


@dataclass(frozen=True)
class MachineUUIDCommandArgs:
    """Typed args for the `machine-uuid` command."""

    name: str
    size: int
    command: Literal["machine-uuid"] = "machine-uuid"


@dataclass(frozen=True)
class MeasurementsCommandArgs:
    """Typed args for the `measurements` command."""

    machine_uuid: str
    page: int
    size: int
    sort: str
    order: Order
    filter: str
    command: Literal["measurements"] = "measurements"


@dataclass(frozen=True)
class SetpointsCommandArgs:
    """Typed args for the `setpoints` command."""

    machine_uuid: str
    page: int
    size: int
    sort: str
    order: Order
    filter: str
    command: Literal["setpoints"] = "setpoints"


@dataclass(frozen=True)
class DataCommandArgs:
    """Typed args for the `data` command."""

    machine_uuid: str
    names: list[str]
    start: datetime
    end: datetime
    interval: timedelta
    max_frame_length: timedelta
    format: DataFormat
    output: str | None
    command: Literal["data"] = "data"


CommandArgs: TypeAlias = (
    UserInfoCommandArgs
    | RoutersCommandArgs
    | MachinesCommandArgs
    | MachineUUIDCommandArgs
    | MeasurementsCommandArgs
    | SetpointsCommandArgs
    | DataCommandArgs
)


class CliError(Exception):
    """CLI level error with user-facing message."""


def parse_datetime(value: str) -> datetime:
    """Parse an ISO-8601 datetime string."""
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid datetime '{value}'. Use ISO format, e.g. 2025-01-01T00:00:00"
        ) from exc


def parse_timedelta_seconds(value: str) -> timedelta:
    """Parse seconds into a positive ``timedelta`` value."""
    try:
        seconds = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid seconds value '{value}'") from exc
    if seconds <= 0:
        raise argparse.ArgumentTypeError("Seconds must be greater than 0")
    return timedelta(seconds=seconds)


def parse_positive_int(value: str) -> int:
    """Parse a positive integer value."""
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid integer value '{value}'") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("Value must be greater than 0")
    return parsed


def parse_non_negative_int(value: str) -> int:
    """Parse a non-negative integer value."""
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid integer value '{value}'") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("Value must be greater than or equal to 0")
    return parsed


def _is_timezone_aware(value: datetime) -> bool:
    """Check if a datetime has timezone information."""
    return value.tzinfo is not None and value.utcoffset() is not None


def _add_page_sort_arguments(parser: argparse.ArgumentParser, *, default_sort: str) -> None:
    """Attach common pagination and sorting arguments."""
    parser.add_argument(
        "--page",
        type=parse_non_negative_int,
        default=0,
        metavar="INDEX",
        help="Page index (0-based).",
    )
    parser.add_argument(
        "--size",
        type=parse_positive_int,
        default=10,
        metavar="COUNT",
        help="Number of items per page (>0).",
    )
    parser.add_argument(
        "--sort",
        default=default_sort,
        metavar="FIELD",
        help=f"Field name used for sorting (default: {default_sort}).",
    )
    parser.add_argument(
        "--order",
        choices=["asc", "desc"],
        default="asc" if default_sort == "name" else "desc",
        metavar="DIRECTION",
        help="Sort direction.",
    )
    parser.add_argument(
        "--filter",
        default="__archived:false",
        metavar="EXPRESSION",
        help="Server-side filter expression.",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build and return the CLI parser."""
    parser = argparse.ArgumentParser(
        prog="pym2v",
        description="Query account, machine, and telemetry data from Eurogard.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True, title="commands")

    subparsers.add_parser(
        "user-info",
        help="Show user profile details.",
        description="Show user profile details for the authenticated account.",
    )

    routers = subparsers.add_parser(
        "routers",
        help="List routers visible to your account.",
        description="List routers visible to your account.",
    )
    _add_page_sort_arguments(routers, default_sort="name")

    machines = subparsers.add_parser(
        "machines",
        help="List machines available to your account.",
        description="List machines available to your account.",
    )
    _add_page_sort_arguments(machines, default_sort="name")

    machine_uuid = subparsers.add_parser(
        "machine-uuid",
        help="Resolve a machine UUID by machine name.",
        description="Resolve a machine UUID by machine name.",
    )
    machine_uuid.add_argument("--name", required=True, metavar="MACHINE_NAME", help="Exact machine display name.")
    machine_uuid.add_argument(
        "--size",
        type=parse_positive_int,
        default=1000,
        metavar="COUNT",
        help="Number of machines to inspect while searching.",
    )

    measurements = subparsers.add_parser(
        "measurements",
        help="List measurement names for a machine.",
        description="List measurement names for a machine.",
    )
    measurements.add_argument("--machine-uuid", required=True, metavar="MACHINE_UUID", help="Target machine UUID.")
    _add_page_sort_arguments(measurements, default_sort="updatedAt")

    setpoints = subparsers.add_parser(
        "setpoints",
        help="List setpoints for a machine.",
        description="List setpoints for a machine.",
    )
    setpoints.add_argument("--machine-uuid", required=True, metavar="MACHINE_UUID", help="Target machine UUID.")
    _add_page_sort_arguments(setpoints, default_sort="updatedAt")

    data = subparsers.add_parser(
        "data",
        help="Fetch time-series data for one or more measurement names.",
        description="Fetch time-series data for one or more measurement names.",
    )
    data.add_argument("--machine-uuid", required=True, metavar="MACHINE_UUID", help="Target machine UUID.")
    data.add_argument(
        "--names",
        nargs="+",
        required=True,
        metavar="NAME",
        help="One or more measurement names to fetch.",
    )
    data.add_argument(
        "--start",
        type=parse_datetime,
        required=True,
        metavar="DATETIME",
        help="Start time in ISO-8601 format.",
    )
    data.add_argument(
        "--end",
        type=parse_datetime,
        required=True,
        metavar="DATETIME",
        help="End time in ISO-8601 format.",
    )
    data.add_argument(
        "--interval",
        type=parse_timedelta_seconds,
        default=DEFAULT_INTERVAL,
        metavar="SECONDS",
        help="Resampling interval in seconds (>0).",
    )
    data.add_argument(
        "--max-frame-length",
        type=parse_timedelta_seconds,
        default=DEFAULT_MAX_FRAME_LENGTH,
        metavar="SECONDS",
        help="Maximum time window fetched per API request in seconds (>0).",
    )
    data.add_argument(
        "--format",
        choices=["csv", "json", "parquet"],
        default="csv",
        metavar="FORMAT",
        help="Output format.",
    )
    data.add_argument("--output", metavar="PATH", help="Write output to a file path.")

    return parser


def _serialize_output(payload: Any) -> None:
    """Write JSON output to stdout."""
    print(json.dumps(payload, default=str))


def _namespace_to_command_args(args: argparse.Namespace) -> CommandArgs:
    """Convert raw argparse namespace into typed command args."""
    match args.command:
        case "user-info":
            return UserInfoCommandArgs()
        case "routers":
            return RoutersCommandArgs(
                page=args.page, size=args.size, sort=args.sort, order=args.order, filter=args.filter
            )
        case "machines":
            return MachinesCommandArgs(
                page=args.page, size=args.size, sort=args.sort, order=args.order, filter=args.filter
            )
        case "machine-uuid":
            return MachineUUIDCommandArgs(name=args.name, size=args.size)
        case "measurements":
            return MeasurementsCommandArgs(
                machine_uuid=args.machine_uuid,
                page=args.page,
                size=args.size,
                sort=args.sort,
                order=args.order,
                filter=args.filter,
            )
        case "setpoints":
            return SetpointsCommandArgs(
                machine_uuid=args.machine_uuid,
                page=args.page,
                size=args.size,
                sort=args.sort,
                order=args.order,
                filter=args.filter,
            )
        case "data":
            return DataCommandArgs(
                machine_uuid=args.machine_uuid,
                names=list(args.names),
                start=args.start,
                end=args.end,
                interval=args.interval,
                max_frame_length=args.max_frame_length,
                format=args.format,
                output=args.output,
            )
        case _:
            raise CliError(f"Unsupported command: {args.command}")


def parse_cli_args(argv: Sequence[str] | None = None) -> CommandArgs:
    """Parse CLI arguments and return a typed command argument object."""
    namespace = build_parser().parse_args(argv)
    return _namespace_to_command_args(namespace)


def _handle_data_command(api: EurogardAPI, args: DataCommandArgs) -> dict[str, Any] | None:
    """Handle the `data` command."""
    if args.format == "parquet" and args.output is None:
        raise CliError("Format 'parquet' requires --output")
    if _is_timezone_aware(args.start) != _is_timezone_aware(args.end):
        raise CliError(
            "Invalid datetime timezone: --start and --end must both be timezone-aware or both timezone-naive"
        )
    if args.start >= args.end:
        raise CliError("Invalid datetime range: --start must be earlier than --end")

    frame = api.get_long_frame_from_names(
        machine_uuid=args.machine_uuid,
        names=args.names,
        start=args.start,
        end=args.end,
        interval=args.interval,
        max_frame_length=args.max_frame_length,
    )

    if args.output:
        output_path = Path(args.output)
        if args.format == "csv":
            frame.write_csv(output_path)
        elif args.format == "json":
            frame.write_json(output_path)
        else:
            frame.write_parquet(output_path)
        return {"output": str(output_path), "format": args.format}

    if args.format == "csv":
        print(frame.write_csv())
    elif args.format == "json":
        print(frame.write_json())
    return None


def run(args: CommandArgs, api: EurogardAPI) -> dict[str, Any] | None:
    """Dispatch parsed arguments to API methods."""
    match args:
        case UserInfoCommandArgs():
            return api.get_user_info()
        case RoutersCommandArgs():
            return api.get_routers(page=args.page, size=args.size, sort=args.sort, order=args.order, filter=args.filter)
        case MachinesCommandArgs():
            return api.get_machines(
                page=args.page, size=args.size, sort=args.sort, order=args.order, filter=args.filter
            )
        case MachineUUIDCommandArgs():
            machines = api.get_machines(size=args.size)
            machine_uuid = api.get_machine_uuid(machine_name=args.name, machines=machines)
            if machine_uuid is None:
                raise CliError(f"Machine '{args.name}' not found")
            return {"name": args.name, "machine_uuid": machine_uuid}
        case MeasurementsCommandArgs():
            return api.get_machine_measurement_names(
                machine_uuid=args.machine_uuid,
                page=args.page,
                size=args.size,
                sort=args.sort,
                order=args.order,
                filter=args.filter,
            )
        case SetpointsCommandArgs():
            return api.get_machine_setpoints(
                machine_uuid=args.machine_uuid,
                page=args.page,
                size=args.size,
                sort=args.sort,
                order=args.order,
                filter=args.filter,
            )
        case DataCommandArgs():
            return _handle_data_command(api, args)
        case _:
            raise CliError(f"Unsupported command: {args.command}")


def _print_error(error: Exception) -> None:
    """Write structured error payload to stderr."""
    payload = {"error": {"type": type(error).__name__, "message": str(error)}}
    print(json.dumps(payload), file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI."""
    try:
        args = parse_cli_args(argv)
    except SystemExit as exc:
        return int(exc.code)  # type: ignore error[invalid-argument-type]

    try:
        api = EurogardAPI()
        output = run(args, api)
        if output is not None:
            _serialize_output(output)
        return 0
    except Exception as exc:  # noqa: BLE001
        _print_error(exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
