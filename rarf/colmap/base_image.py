from dataclasses import dataclass
from typing import Any

from rarf.colmap.point import Vector4, Vector3, Point2D


@dataclass(frozen=True)
class BaseImage:
    """
    Class representing one entry in a Colmap reconstruction images file.
    """
    identifier: int
    r_quat: Vector4
    t_vec: Vector3
    camera_id: int
    name: str
    points2D: list[Point2D]

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, BaseImage) and \
               self.identifier == other.identifier and \
               self.r_quat == other.r_quat and \
               self.t_vec == other.t_vec and \
               self.camera_id == other.camera_id and \
               self.name == other.name and \
               all(pa == pb for pa, pb in zip(self.points2D, other.points2D))
