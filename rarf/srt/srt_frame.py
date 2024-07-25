# pylint: skip-file
import datetime
from typing import Optional


class SrtFrame:
    """
    Domain class representing one frame of a Srt file
    """

    def __init__(self) -> None:
        self.id: Optional[int] = None
        self.start: Optional[datetime.time] = None
        self.end: Optional[datetime.time] = None
        self.FrameCnt: Optional[int] = None
        self.DiffTime: Optional[str] = None
        self.timestamp: Optional[datetime.datetime] = None
        self.iso: Optional[int] = None
        self.shutter: Optional[str] = None
        self.fnum: Optional[float] = None
        self.ev: Optional[int] = None
        self.focal_len: Optional[float] = None
        self.dzoom: Optional[float] = None
        self.latitude: Optional[float] = None
        self.longitude: Optional[float] = None
        self.rel_alt: Optional[float] = None
        self.abs_alt: Optional[float] = None
        self.drone_speedx: Optional[float] = None
        self.drone_speedy: Optional[float] = None
        self.drone_speedz: Optional[float] = None
        self.drone_yaw: Optional[float] = None
        self.drone_pitch: Optional[float] = None
        self.drone_roll: Optional[float] = None
        self.gb_yaw: Optional[float] = None
        self.gb_pitch: Optional[float] = None
        self.gb_roll: Optional[float] = None
        self.ae_meter_md: Optional[int] = None
        self.dzoom_ratio: Optional[int] = None
        self.delta: Optional[int] = None
        self.color_md: Optional[str] = None
        self.ct: Optional[int] = None
