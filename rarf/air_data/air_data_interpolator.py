# pylint: disable=R0201
import datetime
from io import TextIOBase
from typing import List, Optional, TextIO, Union

import numpy as np
import numpy.typing as npt
from scipy import interpolate

from rarf.air_data.air_data_frame import AirDataFrame
from rarf.air_data.air_data_parser import AirDataParser


def interpolate_property(
    x: npt.ArrayLike,
    xp: npt.ArrayLike,
    ad_frames: Union[List[object], List[AirDataFrame]],
    prop: str,
    period: Optional[float] = None,
):
    """Interpolate a property of a dictionary-like object (e.g. AirDataFrame)

    :param x: The x-coordinates of the interpolated values.
    :param xp: The x-coordinates of the data points.
    :param ad_frames: The data points (as dicts or AirDataFrames) to interpolate from.
    :param prop: The property of the __dict__ to interpolate.
    :param period: A period for the x-coordinates. This parameter allows the proper interpolation of angular x-coordinates (e.g. 360°)

    :return The interpolated values.
    """

    if len(ad_frames) < 1:
        return []

    if len(ad_frames) == 1:
        return [getattr(ad_frames[0], prop)] * len(x)

    # form_np does nothing, but if the property is a datetime, we need to convert it to seconds (see below)
    from_np = lambda x: x

    fp_prop = np.array([getattr(frame, prop) for frame in ad_frames])

    if isinstance(fp_prop[0], datetime.datetime):
        # if the property is a datetime, we need to convert it to seconds
        s = fp_prop[0]

        # convert fp_prop to seconds
        fp_prop = np.array([(t - s).total_seconds() for t in fp_prop], dtype=float)
        # from_np converts seconds back to datetime

        def from_np(delta):
            if np.isnan(delta):
                delta = 0.0
            return s + datetime.timedelta(seconds=delta)

    if period is not None:
        fp_prop = np.unwrap(fp_prop, period=period)

    # using scipy interpolation (supports extrapolation)
    inter_prop = interpolate.interp1d(
        np.asarray(xp, dtype=float), fp_prop, kind="linear", fill_value="extrapolate"
    )(
        np.asarray(x, dtype=float)
    )  # create interpolator and directly apply it

    if period is not None:
        inter_prop = np.mod(inter_prop, period)

    return list(map(from_np, inter_prop))


class AirDataTimeInterpolator:
    """
    Parser that allows to read an AirData file
    """

    def __init__(
        self, frames_or_file: Union[str, TextIO, TextIOBase, List[AirDataFrame]]
    ):

        if isinstance(frames_or_file, list):
            self.frames = frames_or_file
        else:
            parser = AirDataParser()
            self.frames = parser.parse(frames_or_file)

        # make sure all frames have a datetime
        for frame in self.frames:
            if frame.datetime is None or (
                not isinstance(frame.datetime, datetime.datetime)
            ):
                raise ValueError(
                    "All frames must have a datetime of type datetime.datetime"
                )

        # use first frame's datetime as start time
        self.start: datetime.datetime = self.frames[0].datetime

        # precompute (for speed)
        self.seconds = np.array(
            [(ad.datetime - self.start).total_seconds() for ad in self.frames]
        )

    def __call__(
        self, time: Union[datetime.datetime, List[datetime.datetime]]
    ) -> List[AirDataFrame]:
        if not isinstance(time, list):
            time = [time]

        x_seconds = np.array([(t - self.start).total_seconds() for t in time])

        targets = [AirDataFrame() for _ in range(len(time))]
        first_frame = self.frames[0].__dict__
        for key, value in first_frame.items():
            period = None
            if key in [
                "compass_heading",
                "gimbal_pitch",
                "gimbal_yaw",
                "gimbal_roll",
                "gimbal_heading",
            ]:
                period = (
                    360  # we deal with angles (in degrees), so we need to unwrap them
                )

            if (
                isinstance(value, int)
                or isinstance(value, float)
                or isinstance(value, datetime.datetime)
            ):
                value = interpolate_property(
                    x_seconds, self.seconds, self.frames, key, period=period
                )
            else:
                # for strings and other props take the first frame's value
                value = [first_frame[key]] * len(time)

            # for isPhoto and isVideo, convert to binary (0 or 1)
            dont_interpolate = key in ["isPhoto", "isVideo"]
            if dont_interpolate:
                value = np.array(value)
                value[value > 0] = 1

            for iv, target in enumerate(targets):
                setattr(target, key, value[iv])

        return targets