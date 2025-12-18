import argparse
import sys

from app.database import Database
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
    command = args.command

    with open(args.db_file, "rb") as file:
        db = Database(file)
        if command == ".dbinfo":
            sys.stdout.write(f"database page size: {db.page_size}\n")
            sys.stdout.write(f"number of tables: {db.table_count}\n")
        elif command == ".tables":
            result = " ".join(map(lambda x: x.decode(), db.tables))
            sys.stdout.write(f"{result}\n")
        else:
            sys.stderr.write(f"Invalid command: {command}\n")


if __name__ == "__main__":
    main()
