from typing import Any, Dict, Optional, Tuple

import cv2
import numpy.typing as npt


class UndistortionParameters:
    """
    Domain object holding the parameters to undistort video frames based on calibration results
    """

    def __init__(
        self,
        _new_camera_matrix: Optional[npt.NDArray[Any]] = None,
        _new_size: Optional[Tuple[int, int]] = None,
    ):
        self.is_initialized = False
        self.new_camera_matrix = _new_camera_matrix
        self.new_size = _new_size
        self.mapx: Optional[int] = None
        self.mapy: Optional[int] = None

    @property
    def fovx(self) -> float:
        """
        The field of view in x after undistortion
        """
        if self.is_initialized:
            fovx, _, _, _, _ = cv2.calibrationMatrixValues(
                self.new_camera_matrix, self.new_size, 1, 1
            )
            return float(fovx)
        return -1.0

    @property
    def fovy(self) -> float:
        """
        The field of view in y after undistortion
        """
        if self.is_initialized:
            _, fovy, _, _, _ = cv2.calibrationMatrixValues(
                self.new_camera_matrix, self.new_size, 1, 1
            )
            return float(fovy)
        return -1.0


class VideoInput:
    """
    Domain class describing a video input, used for multi-video inputs
    """

    def __init__(
        self,
        video_path: str,
        skip: int = 0,
        sampling_rate: int = 0,
        limit: Optional[int] = None,
        calibration_res: Optional[Dict[str, Any]] = None,
        undistortion_parameters: Optional[UndistortionParameters] = None,
        read_grayscale: bool = False,
    ):
        """
        :param video_path: path to the video file
        :param sampling_rate: Number of every x-th frame that should be taken (if 0, every frame is used)
        :param skip: Number of frames that should be skipped (no callback called)
        :param limit: Number of frames that should be accessed
        :param calibration_res: Calibration results associated with this video
        :param undistortion_parameters: Parameters used to undistort video frames
        :param read_grayscale: Flag if video should be read grayscale or bgr
        """
        self.video_path = video_path
        self.skip = skip
        self.sampling_rate = sampling_rate
        self.limit = limit
        self.calibration_res = calibration_res
        self.undistortion_parameters = undistortion_parameters
        self.read_grayscale = read_grayscale
