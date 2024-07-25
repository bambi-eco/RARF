from os import PathLike
from typing import Union

StrPathable = Union[str, PathLike[str]]
BytePathable = Union[bytes, PathLike[bytes]]
Pathable = Union[int, StrPathable, BytePathable]
