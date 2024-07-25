import struct
from typing import Union, Literal, Iterable, Any, BinaryIO

ByteData = Union[bytes, int, float]
ByteEndian = Literal["@", "=", "<", ">", "!"]
ByteFormat = Literal["x", "c", "b", "B", "?", "h", "H", "i", "I", "l", "L", "q", "Q", "n", "N", "e", "f", "d", "s",
                     "p", "P"]


def write_bytes(file: BinaryIO, data: Union[ByteData, Iterable[ByteData]], byte_format: Union[ByteFormat, str],
                byte_endian: ByteEndian = "<") -> None:
    """
    Writes data to file in the specified byte format.
    :param file: The IO to write data to.
    :param data: The data to write.
    :param byte_format: The byte format to use for writing.
    :param byte_endian: The byte endianness to use for writing.
    """
    format_str = f"{byte_endian}{byte_format}"
    if len(byte_format) == 1:
        data = (data,)
    file.write(struct.pack(format_str, *data))


def read_bytes(file: BinaryIO, byte_format: Union[ByteFormat, str],
               byte_endian: ByteEndian = "<") -> Union[Any, tuple[Any, ...]]:
    """
    Reads data from file in the specified byte format.
    :param file: The IO to read data from.
    :param byte_format: The byte format to use for reading.
    :param byte_endian: The byte endianness to use for reading.
    :return: The data read from the file.
    """
    format_str = f"{byte_endian}{byte_format}"
    num_bytes = struct.calcsize(byte_format)
    buffer = file.read(num_bytes)
    data = struct.unpack(format_str, buffer)
    return data[0] if len(byte_format) == 1 else data


def read_string(file: BinaryIO, terminator: bytes = "\0") -> str:
    """
    Reads text from file until the given terminator is encountered or the end of the file is reached.
    :param file: The IO to read from.
    :param terminator: The terminator character.
    :return: The text read from the file.
    """
    characters = []
    char = ""
    while char != terminator:
        characters.append(char)
        char = file.read(1).decode("latin-1")
    return "".join(characters)
