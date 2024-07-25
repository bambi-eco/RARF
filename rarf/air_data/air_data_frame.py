# pylint: skip-file
import datetime
from typing import Optional


class AirDataFrame:
    """
    Domain class representing one row of an AirData file
    Class fields represent the parsed names of a AirData frame using the AirDataParser class
    """

    def __init__(self):
        self.id: int = 0
        self.time: int = 0
        self.datetime: Optional[datetime.datetime] = None
        self.latitude: Optional[float] = None
        self.longitude: Optional[float] = None
        self.height_above_takeoff: Optional[float] = None
        self.height_above_ground_at_drone_location: Optional[str] = None
        self.ground_elevation_at_drone_location: Optional[str] = None
        self.altitude_above_seaLevel: Optional[float] = None
        self.height_sonar: Optional[float] = None
        self.speed: Optional[int] = None
        self.distance: Optional[float] = None
        self.mileage: Optional[float] = None
        self.satellites: Optional[int] = None
        self.gpslevel: Optional[int] = None
        self.voltage: Optional[int] = None
        self.max_altitude: Optional[float] = None
        self.max_ascent: Optional[float] = None
        self.max_speed: Optional[int] = None
        self.max_distance: Optional[float] = None
        self.xSpeed: Optional[int] = None
        self.ySpeed: Optional[int] = None
        self.zSpeed: Optional[int] = None
        self.compass_heading: Optional[float] = None
        self.pitch: Optional[float] = None
        self.roll: Optional[float] = None
        self.isPhoto: Optional[int] = None
        self.isVideo: Optional[int] = None
        self.rc_elevator: Optional[int] = None
        self.rc_aileron: Optional[int] = None
        self.rc_throttle: Optional[int] = None
        self.rc_rudder: Optional[int] = None
        self.gimbal_heading: Optional[float] = None
        self.gimbal_pitch: Optional[int] = None
        self.gimbal_roll: Optional[int] = None
        self.battery_percent: Optional[int] = None
        self.voltageCell1: Optional[float] = None
        self.voltageCell2: Optional[float] = None
        self.voltageCell3: Optional[float] = None
        self.voltageCell4: Optional[float] = None
        self.voltageCell5: Optional[int] = None
        self.voltageCell6: Optional[int] = None
        self.current: Optional[int] = None
        self.battery_temperature: Optional[int] = None
        self.altitude: Optional[float] = None
        self.ascent: Optional[float] = None
        self.flycStateRaw: Optional[int] = None
        self.flycState: Optional[str] = None
        self.message: Optional[str] = None


def interpolate_frames(
    frame1: AirDataFrame, frame2: AirDataFrame, weight_frame1: float
) -> AirDataFrame:
    """
    Method to interpolate two frames
    :param frame1: first frame
    :param frame2: second frame
    :param weight_frame1: value between 0 and 1.0 defining the distance of the interpolated frame from frame 1 (if weight == 0 interpolation == frame1, if weight == 1 interpolation == frame2)
    :return: interpolated frame
    """
    result = AirDataFrame()
    target = dict()
    values = frame1.__dict__
    others = frame2.__dict__
    for key, value in values.items():
        other_value = others[key]
        if weight_frame1 == 0:
            target[key] = value
            continue
        elif weight_frame1 == 1:
            target[key] = other_value
            continue
        if isinstance(value, int) or isinstance(value, float):
            if key in [
                "compass_heading",
                "pitch",
                "roll",
                "gimbal_heading",
                "gimbal_pitch",
                "gimbal_roll",
            ]:
                if value > 270 and other_value < 90:
                    to_limit = 360 - value
                    distance = (to_limit + other_value) * weight_frame1
                    if distance > to_limit:
                        value = distance - to_limit
                    else:
                        value += distance
                elif other_value > 270 and value < 90:
                    distance = (360 - other_value + value) * weight_frame1
                    if distance > value:
                        value = 360 - (distance - value)
                    else:
                        value -= distance
                else:
                    value = value + (other_value - value) * weight_frame1
            elif key == "latitude":
                if value < -45 and other_value > 45:
                    to_limit = 90 + value
                    distance = (to_limit + 90 - other_value) * weight_frame1
                    if value - distance < -90:
                        value = value - distance + 90
                    else:
                        value = value - distance
                elif other_value < -45 and value > 45:
                    distance = (90 - value + 90 + other_value) * weight_frame1
                    if value + distance > 90:
                        value = -90 + (value + distance - 90)
                    else:
                        value += distance
                else:
                    value = value + (other_value - value) * weight_frame1
            elif key == "longitude":
                if value < -90 and other_value > 90:
                    to_limit = 180 + value
                    distance = (to_limit + 180 - other_value) * weight_frame1
                    if value - distance < -180:
                        value = abs(value - distance + 180)
                    else:
                        value = value - distance
                elif other_value < -90 and value > 90:
                    to_limit = 180 + other_value
                    distance = (to_limit + 180 - value) * weight_frame1
                    if value + distance > 180:
                        value = -180 + (value + distance - 180)
                    else:
                        value += distance
                else:
                    value = value + (other_value - value) * weight_frame1
            else:
                value = value + (other_value - value) * weight_frame1
        elif isinstance(value, datetime.datetime):
            value = value + (other_value - value) * weight_frame1

        # for strings take the previous frame's value (except weight == 1)
        dont_interpolate = isinstance(value, str) or key in ["isPhoto", "isVideo"]
        if weight_frame1 < 1 and dont_interpolate:
            value = values[key]
        elif dont_interpolate:
            value = other_value
        target[key] = value

    result.__dict__ = target
    return result
