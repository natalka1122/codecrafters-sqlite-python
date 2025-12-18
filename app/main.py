import argparse
import sys

from app.logging_config import get_logger, setup_logging

setup_logging(level="DEBUG", console_logs_target=sys.stderr)

logger = get_logger(__name__)
database_file_path = sys.argv[1]
command = sys.argv[2]


def parse_args() -> argparse.Namespace:  # noqa: WPS213
    parser = argparse.ArgumentParser()
    parser.add_argument("db_file")
    parser.add_argument("command")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sql = args.command
    if sql == ".dbinfo":
        with open(args.db_file, "rb") as database_file:
            database_file.seek(16)
            page_size = int.from_bytes(database_file.read(2), byteorder="big")
            sys.stdout.write(f"database page size: {page_size}\n")
    else:
        sys.stderr.write(f"Invalid command: {sql}")


if __name__ == "__main__":
    main()
