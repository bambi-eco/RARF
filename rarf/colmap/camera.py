from dataclasses import dataclass
from typing import Any, Sequence


@dataclass(frozen=True)
class CameraModel:
    """
    Class representing a camera model for colmap cameras.
    """
    model_id: int
    model_name: str
    num_params: int


@dataclass(frozen=True)
class Camera:
    """
    Class representing a camera compatible with the Colmap format.
    """
    identifier: int
    model: CameraModel
    width: int
    height: int
    params: Sequence[float]

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Camera) and \
               self.identifier == other.identifier and \
               self.model == other.model and \
               self.width == other.width and \
               self.height == other.height and \
               all(pa == pb for pa, pb in zip(self.params, other.params))
