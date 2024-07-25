# pylint: disable=R0201
import os.path
from typing import Any, Callable, Generator, List, Optional, Tuple

import cv2
import numpy.typing as npt

from rarf.video.video_domain import VideoInput


class VideoFrameAccessor:
    """
    Class that allows to access video frames
    """

    def access_yield(
        self,
        video_path: str,
        skip: int = 0,
        sampling_rate: int = 0,
        limit: Optional[int] = None,
        check_duplicate_function: Optional[
            Callable[[npt.NDArray[Any], npt.NDArray[Any]], bool]
        ] = None,
        read_grayscale: bool = False,
    ) -> Generator[Tuple[int, npt.NDArray[Any]], None, None]:
        """
        Method that allows to access video frames, yielding the individual frames
        :param video_path: path to the video file
        :param skip: Number of frames that should be skipped (no callback called)
        :param sampling_rate: Number of every x-th frame that should be taken (if 0, every frame is used)
        :param limit: Number of frames that should be accessed
        :param check_duplicate_function: Method allowing to check if two frames are duplicated (still frames). Duplicated frames are ignored if parameter is not None
        :param read_grayscale: Flag if video should be read grayscale or bgr
        :return: Generator of the frames
        """
        capture = None
        if not os.path.isfile(video_path):
            raise ValueError(f"There is no file on the given path: {video_path}")

        previous = None
        try:
            capture = cv2.VideoCapture(video_path)
            success, image = capture.read()
            if success and read_grayscale:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            count = 0
            frames_after_skip = 0
            used_frames = 0
            while success:
                if (
                    check_duplicate_function is None
                    or previous is None
                    or not check_duplicate_function(image, previous)
                ):
                    if count >= skip:
                        if sampling_rate <= 0 or frames_after_skip % sampling_rate == 0:
                            yield (count, image)
                            used_frames += 1
                        frames_after_skip += 1
                previous = image
                success, image = capture.read()
                if success and read_grayscale:
                    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                count += 1
                if limit is not None and used_frames >= limit:
                    break
        finally:
            if capture is not None:
                capture.release()

    def access(
        self,
        video_path: str,
        callback: Callable[[int, npt.NDArray[Any]], bool],
        skip: int = 0,
        sampling_rate: int = 0,
        limit: Optional[int] = None,
        check_duplicate_function: Optional[
            Callable[[npt.NDArray[Any], npt.NDArray[Any]], bool]
        ] = None,
        read_grayscale: bool = False,
    ) -> None:
        """
        Method that allows to access video frames, calling a given callback function for every frame
        :param video_path: path to the video file
        :param callback: callback that is executed for every individual frame (should return bool if access should be continued)
        :param skip: Number of frames that should be skipped (no callback called)
        :param sampling_rate: Number of every x-th frame that should be taken (if 0, every frame is used)
        :param limit: Number of frames that should be accessed
        :param check_duplicate_function: Method allowing to check if two frames are duplicated (still frames). Duplicated frames are ignored if parameter is not None
        :param read_grayscale: Flag if video should be read grayscale or bgr
        :return: None
        """
        for (idx, frame) in self.access_yield(
            video_path,
            skip,
            sampling_rate,
            limit,
            check_duplicate_function,
            read_grayscale,
        ):
            if not callback(idx, frame):
                break

    def access_frame(
        self,
        video_path: str,
        callback: Callable[[int, npt.NDArray[Any]], bool],
        frame_idx: int,
        read_grayscale: bool = False,
    ) -> None:
        """
        Method for accessing a single frame per idx of the video
        :param video_path: path to the video file
        :param callback: callback that is executed for every individual frame
        :param frame_idx: Frame that should be accessed (idx starting with 0)
        :param read_grayscale: Flag if video should be read grayscale or bgr
        :return: None
        """
        self.access(
            video_path, callback, frame_idx, 0, 1, read_grayscale=read_grayscale
        )


class MultiVideoFrameAccessor:
    """
    Class that allows to access multiple video frames in parallel
    """

    def _get_generators(self, videos: List[VideoInput]):
        """
        Method for defining the iterators used to access the individual video frames
        :param videos: to be accessed
        :return: List of generator
        """
        generators = []
        accessor = VideoFrameAccessor()
        for video in videos:
            path = video.video_path
            limit = video.limit
            skip = video.skip
            sampling_rate = video.sampling_rate
            read_grayscale = video.read_grayscale
            generators.append(
                accessor.access_yield(
                    path, skip, sampling_rate, limit, read_grayscale=read_grayscale
                )
            )
        return generators

    def access_yield(
        self,
        videos: List[VideoInput],
        check_duplicate_function: Optional[
            Callable[[List[npt.NDArray[Any]], List[npt.NDArray[Any]]], bool]
        ] = None,
    ) -> Generator[Tuple[int, List[int], List[npt.NDArray[Any]]], None, None]:
        """
        Method for accessing multiple videos in parallel
        :param videos: videos to be accessed
        :param check_duplicate_function: Method allowing to check if two frame pairs are duplicated (still frames). Duplicated frames are ignored if parameter is not None
        :return: Generator accessing the frames
        """
        generators = self._get_generators(videos)

        total_index = 0
        previous = None
        while True:
            images = []
            indices = []
            success = False
            for generator in generators:
                res = next(generator, None)
                if res is None:
                    images.append(None)
                    continue
                (idx, image) = res
                indices.append(idx)
                images.append(image)
                success = success or True
            if not success:
                break
            if (
                check_duplicate_function is None
                or previous is None
                or not check_duplicate_function(previous, images)
            ):
                yield total_index, indices, images
            previous = images
            total_index += 1

    def access(
        self,
        videos: List[VideoInput],
        callback: Callable[[int, List[int], List[npt.NDArray[Any]]], bool],
        check_duplicate_function: Optional[
            Callable[[npt.NDArray[Any], npt.NDArray[Any]], bool]
        ] = None,
    ) -> None:
        """
        Method that allows to access frames of multiple videos, calling a given callback function for every frame
        :param videos: videos to be accessed
        :param callback: callback that is executed for every individual frame pair
        :param check_duplicate_function: Method allowing to check if two frame-pairs are duplicated (still frames). Duplicated frames are ignored if parameter is not None
        :return: None
        """
        for (idx, indices, images) in self.access_yield(
            videos, check_duplicate_function
        ):
            callback(idx, indices, images)

    def access_frame(
        self,
        video_paths: List[str],
        callback: Callable[[int, List[int], List[npt.NDArray[Any]]], bool],
        frame_idx: int,
    ) -> None:
        """
        Method for accessing a single frame per idx of the video
        :param video_paths: paths to the videos to be accessed
        :param callback: callback that is executed for every individual frame
        :param frame_idx: Frame that should be accessed (idx starting with 0)
        :return: None
        """
        input_videos = []
        for video in video_paths:
            input_videos.append(VideoInput(video, frame_idx, 0, 1))

        self.access(input_videos, callback)
