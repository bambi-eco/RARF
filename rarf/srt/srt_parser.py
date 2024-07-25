import datetime
import re
from io import TextIOBase
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    Iterable,
    List,
    Optional,
    TextIO,
    Tuple,
    Union,
)

from rarf.srt.srt_frame import SrtFrame


class SrtParser:
    """
    Parser implementation for srt files
    """

    def parse(
        self,
        file: Union[str, TextIO, TextIOBase],
        skip: int = 0,
        limit: Optional[int] = None,
    ) -> List[SrtFrame]:
        """
        Method used to parse an SRT file, which will call the callback
        :param file: path or file pointer of the SRT file
        :param skip: Skip the first n frames and don't call the callback
        :param limit: Break reading frames after m frames
        :return:
        """
        res = []

        def callback(frame: SrtFrame) -> None:
            res.append(frame)

        self.parse_with_callback(file, callback, skip, limit)

        return res

    def parse_with_callback(
        self,
        file: Union[str, TextIO, TextIOBase],
        callback: Callable[[SrtFrame], None],
        skip: int = 0,
        limit: Optional[int] = None,
    ) -> None:
        for frame in self.parse_yield(file, skip, limit):
            callback(frame)

    def parse_yield(
        self,
        file: Union[str, TextIO, TextIOBase],
        skip: int = 0,
        limit: Optional[int] = None,
    ) -> Generator[SrtFrame, None, None]:
        """
        Method used to parse an SRT file, which will call the callback
        :param file: path or file pointer of the SRT file
        :param skip: Skip the first n frames and don't call the callback
        :param limit: Break reading frames after m frames
        :return:
        """
        # get a file_pointer if necessary
        t = type(file)
        if t == str:
            file_pointer = open(file, encoding="UTF8")
        elif t == TextIO or issubclass(t, TextIOBase):
            file_pointer = file
        else:
            raise Exception(
                f"File must be either a string or a file pointer not from Type: {type(file)}"
            )

        # state of current iteration
        current_frame = None
        found_id = False
        found_timestamp = False
        found_meta_start = False
        found_meta_timestamp = False
        additional_meta_information = ""
        num_of_frames = 0
        accepted_frames = 0

        while True:
            if accepted_frames == limit:
                break

            # Get next line from file
            line = file_pointer.readline()

            # if line is empty end of file is reached
            if not line:
                break

            # remove whitespaces
            line = line.strip()

            if len(line) == 0:
                continue

            if not found_id:
                num_of_frames += 1
                current_frame = SrtFrame()
                current_frame.id = int(line) - 1
                found_id = True
            elif not found_timestamp:
                splits = line.split("-->")
                current_frame.start = datetime.datetime.strptime(
                    splits[0].strip(), "%H:%M:%S,%f"
                ).time()
                current_frame.end = datetime.datetime.strptime(
                    splits[1].strip(), "%H:%M:%S,%f"
                ).time()
                found_timestamp = True
            elif not found_meta_start and "<font size=" in line:
                idx = line.index(">")
                line = line[idx:]
                infostart = line.index("FrameCnt")
                line = line[infostart:]
                splits = line.split(",")
                for split in splits:
                    (key, value) = split.split(":")
                    current_frame.__dict__[key.strip()] = self.__parse_value(value)
                found_meta_start = True
            elif not found_meta_timestamp:
                # frame line contains timestamp removing , in millis
                line = line[:23]
                try:
                    current_frame.timestamp = datetime.datetime.strptime(
                        line, "%Y-%m-%d %H:%M:%S,%f"
                    )
                except ValueError:
                    current_frame.timestamp = datetime.datetime.strptime(
                        line, "%Y-%m-%d %H:%M:%S.%f"
                    )
                found_meta_timestamp = True
            else:
                additional_meta_information += line.replace("\n", " ")

                if "</font>" in line:
                    current_meta = dict()
                    additional_meta_information = additional_meta_information.replace(
                        "</font>", ""
                    )
                    # M30 fix, replace bracket with comma
                    additional_meta_information = additional_meta_information.replace(
                        "],", "]"
                    )
                    self._parse_meta_information(
                        additional_meta_information, current_meta
                    )

                    for k, v in current_meta.items():
                        current_frame.__dict__[k] = v

                    found_id = False
                    found_timestamp = False
                    found_meta_start = False
                    found_meta_timestamp = False
                    additional_meta_information = ""
                    if current_frame is not None and num_of_frames > skip:
                        yield current_frame
                        accepted_frames += 1

        if isinstance(file, str):
            file_pointer.close()

    def _parse_meta_information(
        self, additional_meta_information: str, current_meta_information: Dict[str, Any]
    ) -> None:
        """
        Internation method used to parse additional meta information from the srt file
        :param additional_meta_information: string containing the additional meta information
        :param current_meta_information: Current state of the meta information
        :return: dictionary of the meta information
        """

        meta_information: List[str] = re.findall(
            r"\[[^\]]*\]", additional_meta_information
        )
        for mi in meta_information:
            # remove brackets
            mi = mi.replace("[", "").replace("]", "")
            # replace multiple whitespaces by one
            mi = re.sub(r"\s+", " ", mi)
            splits = mi.split(":")
            if len(splits) == 2:
                # if split has two elements its just a key/value pair
                key = splits[0].strip().lower()
                if key == "longtitude":  # srt of DJI M2EA has a typo
                    key = "longitude"
                current_meta_information[key] = self.__parse_value(splits[1])
            elif len(splits) > 2:
                # if split has more than two elements it either contains multiple key/value pairs or a sublist
                if "," in mi:
                    # colon identifies a sublist element
                    mid_splits = mi.split(",")
                    base = None

                    if len(mid_splits) > 0 and mid_splits[0].count(":") > 1:
                        val = mid_splits[0]
                        first_colon = mid_splits[0].index(":")
                        del mid_splits[0]
                        base = val[:first_colon]
                        key_val = val[first_colon + 1 :].lower()
                        mid_splits = [key_val] + mid_splits

                    for split in mid_splits:
                        # extract sub elements
                        inner_split = split.split(":")
                        if base is None:
                            key = inner_split[0].strip()
                        else:
                            key = f"{base}_{inner_split[0].strip()}"
                        key = key.lower()
                        current_meta_information[key.lower()] = self.__parse_value(
                            inner_split[1]
                        )
                else:
                    # no colon identifies multiple key/value pairs separated by a whitespace
                    for x, y in self.pairwise(mi.replace(": ", " ").split(" ")):
                        current_meta_information[x.lower()] = self.__parse_value(y)

    def __parse_value(self, value: str) -> Any:
        """
        Method for parsing a string value to a numeric if possible
        :param value: to be parsed
        :return: int/float or string representation of the given value
        """
        if value is None:
            return None

        value = value.strip()
        if value.replace(".", "").replace("-", "").replace("+", "").isdigit():
            if "." in value:
                return float(value)
            else:
                return int(value)
        return value

    @staticmethod
    def pairwise(iterable: Iterable[Any]) -> Tuple[Any, Any]:
        """
        Help method for access two elements of an iterable
        :param iterable: source of data
        :return: zipped tuple of two elements
        """
        a = iter(iterable)
        return zip(a, a)
