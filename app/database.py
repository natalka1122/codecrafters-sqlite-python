import re
from dataclasses import dataclass
from typing import BinaryIO, Iterator, Optional

from app.const import SQLITE_SCHEMA
from app.logging_config import get_logger

logger = get_logger(__name__)


def _read_bytes(count: int, line: bytes) -> tuple[bytes, bytes]:
    return line[count:], line[:count]


def _read_int(count: int, line: bytes) -> tuple[bytes, int]:
    return line[count:], int.from_bytes(line[:count])


def _read_varint(line: bytes) -> tuple[bytes, int]:
    result = 0
    while True:
        if len(line) == 0:
            raise EOFError("Unexpected end of line while reading varint")
        i = line[0]
        line = line[1:]
        result = (result << 7) | (i & 0x7F)

        if not (i & 0x80):
            break
    return line, result


ValueType = bytes | int | None


class Cell:
    def __init__(self, cell_bytes: bytes) -> None:
        self.cell_bytes = cell_bytes
        logger.info(f"cell_bytes = {cell_bytes!r}")
        cell_bytes, size = _read_varint(cell_bytes)
        cell_bytes, row_id = _read_varint(cell_bytes)
        self.row_id = row_id
        if size != len(cell_bytes):
            logger.error(f"size = {size} len(self.cell_bytes) = {len(self.cell_bytes)}")
            raise NotImplementedError
        cell_bytes, size_of_record_header = _read_varint(cell_bytes)
        cell_bytes, record_header = _read_bytes(size_of_record_header - 1, cell_bytes)
        logger.info(f"record_header = {record_header!r}")
        serial_types: list[int] = []
        while len(record_header) > 0:
            record_header, serial_type = _read_varint(record_header)
            logger.info(f"serial_type = {serial_type!r}")
            serial_types.append(serial_type)
        self.record_values: list[ValueType] = []
        value: ValueType
        for serial_type in serial_types:
            if serial_type == 0:
                value = None
            elif serial_type == 1:
                cell_bytes, value = _read_int(1, cell_bytes)
                logger.info(f"value = {value}")
            elif serial_type >= 12 and serial_type % 2 == 1:
                cell_bytes, value = _read_bytes((serial_type - 12) // 2, cell_bytes)
                logger.info(f"value = {value!r}")
            else:
                logger.info(f"serial_type = {serial_type!r}")
                raise NotImplementedError
            self.record_values.append(value)
        if len(cell_bytes) != 0:
            raise NotImplementedError

    def __repr__(self) -> str:
        return f"Cell({self.record_values})"

    def __len__(self) -> int:
        return len(self.record_values)

    def __iter__(self) -> Iterator[ValueType]:
        return iter(self.record_values)


def _read_btree(page: bytes, shift: int = 0) -> list[Cell]:
    page_size = len(page)
    page = page[shift:]
    page, b_tree_type = _read_int(1, page)
    logger.info(f"b_tree_type = {b_tree_type}")
    if b_tree_type != 13:
        raise NotImplementedError
    page, start_of_first_freeblock = _read_int(2, page)
    logger.info(f"start_of_first_freeblock = {start_of_first_freeblock}")
    if start_of_first_freeblock != 0:
        raise NotImplementedError
    page, number_of_cells = _read_int(2, page)
    logger.info(f"number_of_cells = {number_of_cells}")
    if number_of_cells == 0:
        return []
    page, start_of_the_cell_content_area = _read_int(2, page)
    if start_of_the_cell_content_area == 0:
        start_of_the_cell_content_area = 65536
    logger.info(f"start_of_the_cell_content_area = {start_of_the_cell_content_area}")
    page, number_of_fragmented_free_bytes = _read_int(1, page)
    logger.info(f"number_of_fragmented_free_bytes = {number_of_fragmented_free_bytes}")
    if number_of_fragmented_free_bytes != 0:
        raise NotImplementedError
    cell_indexes: list[int] = [page_size]
    for _ in range(number_of_cells):
        page, cell_index = _read_int(2, page)
        cell_indexes.append(cell_index)
    cell_indexes.sort()
    if cell_indexes[0] != start_of_the_cell_content_area:
        raise NotImplementedError
    logger.info(f"cell_indexes = {cell_indexes}")

    result: list[Cell] = []
    eaten = page_size - len(page)
    for index in range(number_of_cells):
        index1 = cell_indexes[index] - eaten
        index2 = cell_indexes[index + 1] - eaten
        cell = Cell(page[index1:index2])
        logger.info(f"cell = {cell}")
        result.append(cell)
    return result


@dataclass
class Column:
    is_integer: bool
    name: str


class Schema:
    def __init__(self, schema_str: str) -> None:  # noqa: WPS210
        match = re.match(r"CREATE\s+TABLE\s+(?P<name>\w+)\s*\((?P<columns>[\w\s,]+)\)", schema_str)
        if match is None:
            logger.error(f"schema_str = {schema_str}")
            raise NotImplementedError
        self.tablename: str = match.groupdict()["name"]
        columns_str: str = match.groupdict()["columns"]
        columns: list[Column] = []
        for column_str in columns_str.split(","):
            c_split = column_str.split()
            is_integer = c_split[-1] == "integer"
            columns.append(Column(is_integer=is_integer, name=c_split[0]))
        self.columns: tuple[Column, ...] = tuple(columns)

    def __len__(self) -> int:
        return len(self.columns)


class BTree:
    def __init__(self, schema: Schema, cells: list[Cell]) -> None:
        self.tablename = schema.tablename
        self.schema = schema
        logger.info(f"schema = {schema}")
        logger.info(f"cells = {cells}")
        self.btree: list[dict[str, ValueType]] = []
        for cell in cells:
            if len(cell) != len(schema):
                raise NotImplementedError
            leaf: dict[str, ValueType] = {}
            for value, column in zip(cell, schema.columns):
                if column.is_integer and not isinstance(value, int):
                    raise NotImplementedError
                if not column.is_integer and not isinstance(value, bytes):
                    raise NotImplementedError
                leaf[column.name] = value
            self.btree.append(leaf)

    def __len__(self) -> int:
        return len(self.btree)


class Database:
    def __init__(self, file: BinaryIO) -> None:
        self._file = file
        # self.tables: list[bytes] = []
        self._file.seek(16)
        # 2 | The database page size in bytes. Must be a power of two between 512 and 32768 inclusive,
        # or the value 1 representing a page size of 65536.
        self.page_size = int.from_bytes(self._file.read(2))
        if self.page_size == 1:
            self.page_size = 65536
        first_page = self.get_page(1)

        # self._jump_to(28)
        # 4 | Size of the database file in pages. The "in-header database size".
        self.num_pages = int.from_bytes(first_page[28:33])

        self.schema = BTree(schema=Schema(SQLITE_SCHEMA), cells=_read_btree(first_page, shift=100))
        
        # self.table_names =
        logger.info(f"self.schema.btree = {self.schema.btree}")

    @property
    def table_count(self) -> int:
        return len(self.schema)

    @property
    def table_names(self) -> list[str]:
        table_names: list[str] = []
        for record in self.schema.btree:
            table_names.append(record["name"].decode())
        return sorted(table_names)

    def count(self, table_name: str) -> int:
        logger.info(f"self.schema.bree = {self.schema.btree}")
        rootpage: Optional[int] = None
        for cell in self.schema.btree:
            if cell["name"].decode() == table_name:
                rootpage = cell["rootpage"]
                break
        if rootpage is None:
            raise NotImplementedError
        logger.info(f"rootpage = {rootpage}")
        rootpage_bytes = self.get_page(rootpage)
        cells = _read_btree(rootpage_bytes)
        logger.info(f"cells = {cells}")
        return len(cells)

    def read(self, count: int) -> bytes:
        self._index += count
        return self._file.read(count)

    def file_read_int(self, count: int) -> int:
        return int.from_bytes(self.read(count))

    def file_read_varint(self) -> int:
        result = 0
        while True:
            byte_data = self._file.read(1)
            if not byte_data:
                raise EOFError("Unexpected end of file while reading varint")
            self._index += 1
            i = byte_data[0]

            result = (result << 7) | (i & 0x7F)

            if not (i & 0x80):
                break
        return result

    def file_read_bytes(self, count: int) -> bytes:
        return self.read(count)

    def read_varint(self, line: bytes) -> tuple[bytes, int]:
        result = 0
        while True:
            if len(line) == 0:
                raise EOFError("Unexpected end of line while reading varint")
            i = line[0]
            line = line[1:]
            result = (result << 7) | (i & 0x7F)

            if not (i & 0x80):
                break
        return line, result

    def read_bytes(self, count: int, line: bytes) -> tuple[bytes, bytes]:
        return line[count:], line[:count]

    def _jump_to(self, pos: int) -> None:
        self._index = pos
        self._file.seek(pos, 0)

    def get_page(self, index: int) -> bytes:
        self._file.seek((index - 1) * self.page_size)
        return self._file.read(self.page_size)
