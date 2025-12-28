from enum import StrEnum


class CommandType(StrEnum):
    SELECT = "SELECT"
    DBINFO = ".dbinfo"
    TABLES = ".tables"


SQLITE_SCHEMA = (
    "CREATE TABLE sqlite_schema(type text, name text, tbl_name text, rootpage integer, sql text)"
)
