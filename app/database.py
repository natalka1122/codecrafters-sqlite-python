from typing import Any, BinaryIO

from app.logging_config import get_logger

logger = get_logger(__name__)


class Database:
    def __init__(self, file: BinaryIO) -> None:
        self._file = file
        self._index = 0
        self.table_count = 0
        self.tables: list[bytes] = []
        self._jump_to(16)
        # 2 | The database page size in bytes. Must be a power of two between 512 and 32768 inclusive,
        # or the value 1 representing a page size of 65536.
        self.page_size = self.file_read_int(2)
        if self.page_size == 1:
            self.page_size = 65536
        self._jump_to(28)
        # 4 | Size of the database file in pages. The "in-header database size".
        self.num_pages = self.file_read_int(4)
        self._jump_to(100)
        b_tree_type = self.file_read_int(1)
        logger.info(f"b_tree_type = {b_tree_type}")
        if b_tree_type != 13:
            raise NotImplementedError
        self.start_of_first_freeblock = self.file_read_int(2)
        self.number_of_cells = self.file_read_int(2)
        self.start_of_the_cell_content_area = self.file_read_int(2)
        if self.start_of_the_cell_content_area == 0:
            self.start_of_the_cell_content_area = 65536
        self.number_of_fragmented_free_bytes = self.file_read_int(1)
        self._jump_to(self.start_of_the_cell_content_area)

        while self._index < self.page_size:
            size = self.file_read_varint()
            logger.info(f"size = {size}")
            rowid = self.file_read_varint()
            logger.info(f"rowid = {rowid}")
            payload = self.file_read_bytes(size)
            logger.info(f"payload = {payload!r}")
            payload, size_of_record_header = self.read_varint(payload)
            logger.info(f"size_of_record_header = {size_of_record_header!r}")
            payload, record_header = self.read_bytes(size_of_record_header - 1, payload)
            logger.info(f"record_header = {record_header!r}")
            serial_types: list[int] = []
            while len(record_header) > 0:
                record_header, serial_type = self.read_varint(record_header)
                logger.info(f"serial_type = {serial_type!r}")
                serial_types.append(serial_type)
            record_values: list[Any] = []
            value: Any
            for serial_type in serial_types:
                if serial_type == 1:
                    payload, value = self.read_int(1, payload)
                elif serial_type >= 12 and serial_type % 2 == 1:
                    payload, value = self.read_bytes((serial_type - 12) // 2, payload)
                    logger.info(f"value = {value!r}")
                else:
                    logger.info(f"serial_type = {serial_type!r}")
                    raise NotImplementedError
                record_values.append(value)
            self.tables.append(record_values[2])
            self.table_count += 1
        logger.info(self.__dict__)
        self.tables.sort()
        if self._index != self.page_size:
            raise NotImplementedError

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

    def read_int(self, count: int, line: bytes) -> tuple[bytes, int]:
        return line[count:], int.from_bytes(line[:count])

    def read_bytes(self, count: int, line: bytes) -> tuple[bytes, bytes]:
        return line[count:], line[:count]

    def _jump_to(self, pos: int) -> None:
        self._index = pos
        self._file.seek(pos, 0)
