from typing import BinaryIO

from app.logging_config import get_logger

logger = get_logger(__name__)


class Database:
    def __init__(self, file: BinaryIO) -> None:
        self._file = file
        self._index = 0
        self.table_count = 0
        self._jump_to(16)
        # 2 | The database page size in bytes. Must be a power of two between 512 and 32768 inclusive,
        # or the value 1 representing a page size of 65536.
        self.page_size = int.from_bytes(self.read(2))
        if self.page_size == 1:
            self.page_size = 65536
        self._jump_to(28)
        # 4 | Size of the database file in pages. The "in-header database size".
        self.num_pages = int.from_bytes(self.read(4))
        self._jump_to(100)
        b_tree_type = self.read(1)[0]
        logger.info(f"b_tree_type = {b_tree_type}")
        if b_tree_type != 13:
            raise NotImplementedError
        self.start_of_first_freeblock = int.from_bytes(self.read(2))
        self.number_of_cells = int.from_bytes(self.read(2))
        self.start_of_the_cell_content_area = int.from_bytes(self.read(2))
        if self.start_of_the_cell_content_area == 0:
            self.start_of_the_cell_content_area = 65536
        self.number_of_fragmented_free_bytes = int.from_bytes(self.read(1))
        self._jump_to(self.start_of_the_cell_content_area)

        while self._index < self.page_size:
            size = self.read(1)[0]
            logger.info(f"size = {size}")
            rowid = self.read(1)[0]
            logger.info(f"rowid = {rowid}")
            content = self.read(size)
            logger.info(f"content = {content!r}")
            self.table_count += 1
        logger.info(self.__dict__)
        if self._index != self.page_size:
            raise NotImplementedError

    def read(self, count: int) -> bytes:
        self._index += count
        return self._file.read(count)

    def _jump_to(self, pos: int) -> None:
        self._index = pos
        self._file.seek(pos, 0)
