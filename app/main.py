import argparse
import sys

from app.database import Database
from app.exec import sql_exec
from app.logging_config import get_logger, setup_logging
from app.statement import Statement

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
    command = Statement(args.command)
    with open(args.db_file, "rb") as file:
        db = Database(file)
        for line in sql_exec(command, db):
            sys.stdout.write(f"{line}\n")


if __name__ == "__main__":
    main()
