from typing import Optional, Sequence

import sqlparse

from app.const import CommandType


class Statement:
    def __init__(self, command: str) -> None:
        self.str = command
        parsed_tokens: Sequence[sqlparse.sql.Token] = list(
            filter(lambda x: not x.is_whitespace, sqlparse.parse(command)[0])
        )
        parsed = list(map(lambda x: x.value, parsed_tokens))
        if parsed[0] == ".":
            self._cmd_type = CommandType(f".{parsed[1]}")
            return
        if parsed[0].upper() == "SELECT":
            self._cmd_type = CommandType.SELECT
        else:
            raise NotImplementedError
        from_clause: Optional[str] = None
        columns: list[str] = []
        i = 1
        while i < len(parsed):
            if parsed[i].upper() == "FROM":
                from_clause = parsed[i + 1]
                i += 2
                continue
            if parsed[i].upper() == "COUNT(*)":
                parsed[i] = "COUNT(*)"
            columns.append(parsed[i])
            i += 1
        self.columns: tuple[str, ...] = tuple(columns)
        if from_clause is None:
            raise NotImplementedError
        self.from_clause = from_clause

    def __repr__(self) -> str:
        return str(self.__dict__)

    @property
    def cmd_type(self) -> CommandType:
        return self._cmd_type
