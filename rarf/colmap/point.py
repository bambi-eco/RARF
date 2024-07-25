from dataclasses import dataclass
from typing import Any, Sequence, Union

import numpy as np

Numeric = Union[int, float, np.integer, np.floating]
Vector3 = tuple[Numeric, Numeric, Numeric]
IntVector3 = tuple[int, int, int]
Vector4 = tuple[Numeric, Numeric, Numeric, Numeric]
IntVector4 = tuple[int, int, int, int]


@dataclass(frozen=True)
class Point2D:
    """
    Class representing a 2D coordinate compatible with the Colmap format.
    """
    x: float
    y: float
    point3D_id: int


@dataclass(frozen=True)
class Point3D:
    """
    Class representing a 3D coordinate compatible with the Colmap format.
    """
    identifier: int
    xyz: Vector3
    rgb: IntVector3
    error: float
    image_ids: Sequence[int]
    point2D_idxs: Sequence[int]

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Point3D) and \
               self.identifier == other.identifier and \
               self.xyz == other.xyz and \
               self.rgb == other.rgb and \
               self.error == other.error and \
               all(ia == ib for ia, ib in zip(self.image_ids, other.image_ids)) and \
               all(pa == pb for pa, pb in zip(self.point2D_idxs, other.point2D_idxs))
