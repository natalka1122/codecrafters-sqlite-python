from app.const import CommandType
from app.database import Database
from app.logging_config import get_logger
from app.statement import Statement

logger = get_logger(__name__)


def sql_exec(command: Statement, db: Database) -> list[str]:
    command_type = command.cmd_type
    if command_type == CommandType.DBINFO:
        return [
            f"database page size: {db.page_size}",
            f"number of tables: {db.table_count}",
        ]
    elif command_type == CommandType.TABLES:
        return [" ".join(db.table_names)]
    elif command_type == CommandType.SELECT:
        return do_select(command=command, db=db)
    raise NotImplementedError(f"Invalid command: '{command}'")


def do_select(command: Statement, db: Database) -> list[str]:
    if command.cmd_type != CommandType.SELECT:
        raise NotImplementedError
    if command.columns == ("COUNT(*)",):
        return [str(db.count(command.from_clause))]
    raise NotImplementedError(f"command.columns = {command.columns}")
