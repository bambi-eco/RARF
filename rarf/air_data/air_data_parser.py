# pylint: disable=R0201
import csv
import datetime
import sys
from abc import ABC, abstractmethod
from io import TextIOBase
from typing import Any, Dict, Generator, List, Optional, TextIO, Union, Iterable

from dateutil import tz

from rarf.air_data.air_data_frame import AirDataFrame

maxInt = None

if maxInt is None:
    # Fix csv problem with large fields (source https://stackoverflow.com/a/15063941)
    maxInt = sys.maxsize
    while True:
        # decrease the maxInt value by factor 10
        # as long as the OverflowError occurs.

        try:
            csv.field_size_limit(maxInt)
            break
        except OverflowError:
            maxInt = int(maxInt / 10)


class AirDataParserInterface(ABC):
    """
    Interface for an AirDataParser
    """

    @abstractmethod
    def parse_yield(
        self,
        file: Union[str, TextIO, TextIOBase],
        skip: int = 0,
        limit: Optional[int] = None,
    ) -> Generator[AirDataFrame, None, None]:
        """
        Method used to parse an AirData file, which will call the callback
        :param file: path or file pointer of the airdata file
        :param skip: Skip the first n frames and don't call the callback
        :param limit: Break reading frames after m frames
        :return:
        """
        pass

    def parse(
        self,
        file: Union[str, TextIO, TextIOBase],
        skip: int = 0,
        limit: Optional[int] = None,
    ) -> List[AirDataFrame]:
        """
        Method for parsing an AirData file
        :param file: path or file pointer of the airdata file
        :param skip: Skip the first n frames and don't call the callback
        :param limit: Break reading frames after m frames
        :return:
        """
        res = []
        for frame in self.parse_yield(file, skip, limit):
            res.append(frame)

        return res


class AirDataParser(AirDataParserInterface):
    """
    Parser that allows to read an AirData file
    """

    def __init__(self, delimiter: str = ",", quotechar='"'):
        """
        :param delimiter: Delimiter symbol used to separate columns in the CSV (AirData normally uses ,)
        :param quotechar: Symbol used to quote strings
        """
        self.delimiter = delimiter
        self.quotechar = quotechar

    @staticmethod
    def _ensure_file_pointer(file: Union[str, TextIO, TextIOBase]) -> Iterable[str]:
        t = type(file)
        if t == str:
            return open(file, encoding="UTF-8")
        elif t == TextIO or issubclass(t, TextIOBase):
            return file
        else:
            raise Exception(
                f"File must be either a string or a file pointer not from Type: {type(file)}"
            )

    def parse_yield(
        self,
        file: Union[str, TextIO, TextIOBase],
        skip: int = 0,
        limit: Optional[int] = None,
    ) -> Generator[AirDataFrame, None, None]:
        """
        Method used to parse an AirData file, which will call the callback
        :param file: path or file pointer of the airdata file
        :param skip: Skip the first n frames and don't call the callback
        :param limit: Break reading frames after m frames
        :return:
        """
        # get a file_pointer if necessary
        file_pointer = self._ensure_file_pointer(file)

        reader = csv.reader(
            file_pointer, delimiter=self.delimiter, quotechar=self.quotechar
        )
        headers: List[str] = []
        units: Dict[str, str] = {}
        frame_id = -1
        for idx, row in enumerate(reader):
            # first row not found yet -> get the column description
            if idx == 0:
                for column in row:
                    # remove parenthesis and their content, to get a python valid field name
                    if "(" in column:
                        meta_start = column.index("(")
                        val = column[:meta_start].strip()
                        headers.append(val)
                        unit = column[(meta_start + 1) : -1]
                        units[val] = unit
                    else:
                        headers.append(column.strip())
                continue
            frame_id += 1
            if frame_id < skip:
                continue

            # first row already found -> process the data
            converted: List[Any] = []
            for i, column2 in enumerate(row):
                # clean up value
                column2 = column2.strip()
                if i >= len(headers):
                    continue
                header = headers[i]
                unit2 = units.get(header)

                # try to find out which data type should be used
                # if column is empty use None
                if len(column2) == 0:
                    converted.append(None)
                # if column is a valid digit convert it to a float or an integer, depending on a contained dot
                elif (
                    column2.lower()
                    .replace(".", "")
                    .replace("-", "")
                    .replace("e", "")
                    .isdigit()
                ):
                    if "." in column2:
                        value = float(column2)
                    else:
                        value = int(column2)
                    if unit2 is not None and unit2.lower() == "feet":
                        value /= 3.28  # conversion from feet to meter
                    elif unit2 is not None and unit2.lower() == "mph":
                        value *= 1.6093  # conversion from mph to kmh
                    converted.append(value)
                # otherwise check if it can be parsed to a datetime object and if not just use it as a string
                else:
                    try:
                        dt = datetime.datetime.strptime(
                            column2, "%Y-%m-%d %H:%M:%S"
                        ).replace(
                            tzinfo=tz.tzutc()
                        )  # AirData Files are always in UTC
                        converted.append(dt)
                    except Exception:
                        converted.append(column2)

            # create AirDataFrame object using __dict__ based reflection
            current_object = AirDataFrame()
            current_object.__dict__ = dict(zip(headers, converted))
            current_object.id = frame_id
            yield current_object
            if limit is not None and frame_id == skip + limit - 1:
                break

        if isinstance(file, str):
            file_pointer.close()

    def get_video_offset(
        self, file: Union[str, TextIO, TextIOBase], video_time: datetime.datetime
    ) -> int:
        """
        Returns the video offset for the video starting at the given time
        :param file: path or file pointer of the airdata file
        :param video_time: the timestamp of the video (if no timezone given assume UTC time)
        :return: offset in milliseconds
        """

        # check if timezone is given, if not assume UTC
        if video_time.tzinfo is None:
            video_time = video_time.replace(tzinfo=tz.tzutc())

        best_frame = None
        min_diff = None

        for frame in self.parse_yield(file):
            if frame.isVideo or frame.isPhoto:
                if best_frame is None:
                    best_frame = frame
                    min_diff = abs(frame.datetime - video_time)
                else:
                    diff = abs(frame.datetime - video_time)
                    if diff < min_diff:
                        best_frame = frame
                        min_diff = diff
                    if diff > min_diff:
                        break

        ms_offset = best_frame.time
        utc_time = best_frame.datetime

        # final sanity check
        if abs(utc_time - video_time) > datetime.timedelta(seconds=60):
            raise ValueError(
                f"Time difference between video and airdata log is larger than 60 seconds ({utc_time} vs. {video_time})"
            )

        return ms_offset

    def get_start_and_end(self, file: Union[str, TextIO, TextIOBase]) -> Optional[tuple[datetime, datetime]]:
        """
        Extracts the first and last UTC date time from the given AirData file.
        :param file: The file from which to read the data.
        :return: If no date-time information could be retrieved ``None``; otherwise the date-time data of the first and
        last frame in UTC.
        """
        file_pointer = self._ensure_file_pointer(file)

        start_date_utc = None
        last_date_str = None
        with file_pointer:
            reader = csv.reader(file_pointer, delimiter=self.delimiter, quotechar=self.quotechar)
            next(reader)  # skip header
            for row in reader:
                if start_date_utc is None:
                    date_str = row[1]
                    start_date_utc = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                    start_date_utc = start_date_utc.replace(tzinfo=tz.tzutc())
                    continue
                last_date_str = row[1]
        if last_date_str is None:
            return None
        else:
            end_date_utc = datetime.datetime.strptime(last_date_str, "%Y-%m-%d %H:%M:%S")
            end_date_utc = end_date_utc.replace(tzinfo=tz.tzutc())
            return start_date_utc, end_date_utc
