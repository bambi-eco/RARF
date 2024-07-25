import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import uuid
from abc import ABC, abstractmethod
from enum import IntEnum
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

import numpy.typing as npt
from cv2 import cv2


def get_mp4v() -> Tuple[str, str, str, str]:
    """
    :return: Four-C-Code for MP4
    """
    return "m", "p", "4", "v"


def get_mjpeg() -> Tuple[str, str, str, str]:
    """
    :return: Four-C-Code for MJPEG
    """
    return "M", "J", "P", "G"


def get_mpeg1() -> Tuple[str, str, str, str]:
    """
    :return: Four-C-Code for MPEG1
    """
    return "P", "I", "M", "1"


class AbstractVideoWriter(ABC):
    @abstractmethod
    def write(
        self,
        target_path: str,
        frames: Generator[Tuple[int, npt.NDArray[Any]], None, None],
        target_fps: float = 29.97,
        callback: Optional[Callable[[int, npt.NDArray[Any]], npt.NDArray[Any]]] = None,
    ) -> None:
        """
        Method for writing a video
        :param target_path: where to write the video
        :param frames: to be written
        :param target_fps: frames per seconds used to create the video
        :param fourcc: 	4-character code of codec used to compress the frames. (More information: https://docs.opencv.org/4.5.2/dd/d9e/classcv_1_1VideoWriter.html#ad59c61d8881ba2b2da22cff5487465b5 and https://softron.zendesk.com/hc/en-us/articles/207695697-List-of-FourCC-codes-for-video-codecs)
        :param callback: callback method for post-processing the frames before adding to video
        :return: None
        """
        return


class OpenCvVideoWriter(AbstractVideoWriter):
    """
    Class allowing to create video from frames
    """

    def write(
        self,
        target_path: str,
        frames: Generator[Tuple[int, npt.NDArray[Any]], None, None],
        target_fps: float = 29.97,
        callback: Optional[Callable[[int, npt.NDArray[Any]], npt.NDArray[Any]]] = None,
    ) -> None:
        self.write_with_fourcc(target_path, frames, target_fps, callback=callback)

    def write_with_fourcc(
        self,
        target_path: str,
        frames: Generator[Tuple[int, npt.NDArray[Any]], None, None],
        target_fps: float = 29.97,
        fourcc: Tuple[str, str, str, str] = get_mp4v(),
        callback: Optional[Callable[[int, npt.NDArray[Any]], npt.NDArray[Any]]] = None,
    ) -> None:
        """
        Method for writing a video
        :param target_path: where to write the video
        :param frames: to be written
        :param target_fps: frames per seconds used to create the video
        :param fourcc: 	4-character code of codec used to compress the frames. (More information: https://docs.opencv.org/4.5.2/dd/d9e/classcv_1_1VideoWriter.html#ad59c61d8881ba2b2da22cff5487465b5 and https://softron.zendesk.com/hc/en-us/articles/207695697-List-of-FourCC-codes-for-video-codecs)
        :param callback: callback method for post-processing the frames before adding to video
        :return: None
        """
        writer = None
        try:
            for (idx, frame) in frames:
                if callback is not None:
                    frame = callback(idx, frame)

                if writer is None:
                    shape = frame.shape
                    height, width = shape[:2]
                    writer = cv2.VideoWriter(
                        target_path,
                        cv2.VideoWriter_fourcc(
                            fourcc[0], fourcc[1], fourcc[2], fourcc[3]
                        ),
                        target_fps,
                        (width, height),
                        len(shape) > 2 and shape[2] > 1,
                    )
                writer.write(frame)
        finally:
            if writer is not None:
                writer.release()


class AbstractFFMPEGVideoWriter(AbstractVideoWriter, ABC):
    """
    Abstract video writer based on FFMPEG
    """

    @abstractmethod
    def _get_process_command(
        self,
        target_fps: float,
        outputformat: str,
        pwd: str,
        parameters: Optional[List[Tuple[str, str]]] = None,
    ) -> str:
        """
        :return: The process that should be run
        """
        return ""

    @staticmethod
    def _params_to_string(parameters: Optional[Dict[str, str]] = None) -> str:
        """
        Method for combining the given parameters to a parameter string
        :param parameters: to be combined
        :return: parameter string
        """
        if parameters is None:
            return ""
        else:
            return " ".join([f"{k} {v}" for k, v in parameters.items()])

    def write_with_parameters(
        self,
        target_path: str,
        frames: Generator[Tuple[int, npt.NDArray[Any]], None, None],
        target_fps: float = 29.97,
        parameters: Optional[Dict[str, str]] = None,
        callback: Optional[Callable[[int, npt.NDArray[Any]], npt.NDArray[Any]]] = None,
    ) -> None:
        """
        Method for creating a video using ffmpeg
        :param target_path: where to write the video
        :param frames: to be written
        :param target_fps: frames per seconds used to create the video
        :param parameters: FFMPEG parameters that should be used e.g. ("-pix_fmt", "yuva420p") for defining the pixel format
        :param callback: callback method for post-processing the frames before adding to video
        :return: None
        """
        temp_folder = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}")
        os.makedirs(temp_folder, exist_ok=True)
        try:
            for idx, img in frames:
                if callback is not None:
                    _, img = callback(idx, img)
                cv2.imwrite(os.path.join(temp_folder, f"{idx}.png"), img)

            outputformat = pathlib.Path(target_path).suffix
            p = self._get_process_command(
                target_fps, outputformat, temp_folder, parameters
            )
            subprocess.run(p, cwd=temp_folder)

            shutil.copyfile(
                os.path.join(temp_folder, f"output{outputformat}"), target_path
            )
        finally:
            shutil.rmtree(temp_folder)

    def write(
        self,
        target_path: str,
        frames: Generator[Tuple[int, npt.NDArray[Any]], None, None],
        target_fps: float = 29.97,
        callback: Optional[Callable[[int, npt.NDArray[Any]], npt.NDArray[Any]]] = None,
    ) -> None:
        self.write_with_parameters(
            target_path,
            frames,
            target_fps,
            {"-c:v": "libx264", "-pix_fmt": "yuv420p"},
            callback,
        )


class FFMPEGWriter(AbstractFFMPEGVideoWriter):
    """
    Video writer based on FFMPEG
    """

    def __init__(self, path_to_ffmpeg: Optional[str] = None):
        """
        :param path_to_ffmpeg: Absolute path to ffmpeg; If none ffmpeg must be available on path
        """
        if path_to_ffmpeg is not None:
            self.__path_to_ffmpeg = path_to_ffmpeg
        else:
            self.__path_to_ffmpeg = "ffmpeg"

        p = subprocess.run(f"{self.__path_to_ffmpeg} -version")
        if p.returncode != 0:
            raise Exception("Could not access FFMPEG via given path")

    def _get_process_command(
        self,
        target_fps: float,
        outputformat: str,
        pwd: str,
        parameters: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        :return: The process that should be run
        """
        params = self._params_to_string(parameters)

        return f"{self.__path_to_ffmpeg} -framerate {target_fps} -f image2 -i %d.png {params} output{outputformat}"


class DockerFFMPEGWriter(AbstractFFMPEGVideoWriter):
    """
    Video writer based on FFMPEG using Docker
    """

    class HardwareAcceleration(IntEnum):
        No = 0
        Docker = 1
        Nvidia = 2

    def __init__(
        self,
        path_to_docker: Optional[str] = None,
        use_hardware_acceleration: HardwareAcceleration = HardwareAcceleration.No,
    ):
        """
        :param path_to_docker: Absolute path to Docker; If none ffmpeg must be available on path
        :param use_hardware_acceleration: Flag if hardware acceleration should be used (Option Nvidia requires nvidia-docker)
        """
        self.__path_to_docker = path_to_docker
        self.__use_hardware_acceleration = use_hardware_acceleration

        if path_to_docker is not None:
            self.__path_to_docker = path_to_docker
        else:
            self.__path_to_docker = "docker"

        p = subprocess.run(f"{self.__path_to_docker} --version")
        if p.returncode != 0:
            raise Exception("Could not access Docker via given path")

    def _get_process_command(
        self,
        target_fps: float,
        outputformat: str,
        pwd: str,
        parameters: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        :return: The process that should be run
        """
        runtime = ""
        parameters_copy = parameters.copy()

        if (
            self.__use_hardware_acceleration
            == DockerFFMPEGWriter.HardwareAcceleration.No
        ):
            docker_image = "jrottenberg/ffmpeg:5.0.2-alpine313"
        elif (
            self.__use_hardware_acceleration
            == DockerFFMPEGWriter.HardwareAcceleration.Docker
        ):
            docker_image = "jrottenberg/ffmpeg:5.0.2-vaapi2004"
        else:
            docker_image = "jrottenberg/ffmpeg:5.0.2-nvidia2004"
            runtime = "--runtime=nvidia"
            parameters_copy["-hwaccel"] = "cuvid"

        params = self._params_to_string(parameters_copy)

        return f"{self.__path_to_docker} run {runtime} -v {pwd}:/images/ {docker_image} -framerate {target_fps} -f image2 -i /images/%d.png {params} /images/output{outputformat}"


class WebmFFMPEGWriter(AbstractVideoWriter):
    """
    Wrapper for a FFMPEG Writer intended to create WEBM videos
    """

    def __init__(self, base_writer: AbstractFFMPEGVideoWriter):
        self._base_writer = base_writer

    def write_with_parameters(
        self,
        target_path: str,
        frames: Generator[Tuple[int, npt.NDArray[Any]], None, None],
        target_fps: float = 29.97,
        parameters: Optional[Dict[str, str]] = None,
        callback: Optional[Callable[[int, npt.NDArray[Any]], npt.NDArray[Any]]] = None,
    ) -> None:
        if not target_path.endswith(".webm"):
            raise Exception("Target Path does not end with file subfix .webm")

        if parameters is not None:
            param_copy = parameters.copy()
        else:
            param_copy = {}
        if param_copy.get("-c:v") is None:
            param_copy["-c:v"] = "libvpx-vp9"
        if param_copy.get("-pix_fmt") is None:
            param_copy["-pix_fmt"] = "yuva420p"
        self._base_writer.write_with_parameters(
            target_path, frames, target_fps, param_copy, callback
        )

    def write(
        self,
        target_path: str,
        frames: Generator[Tuple[int, npt.NDArray[Any]], None, None],
        target_fps: float = 29.97,
        callback: Optional[Callable[[int, npt.NDArray[Any]], npt.NDArray[Any]]] = None,
    ) -> None:
        self.write_with_parameters(target_path, frames, target_fps, callback)


class PipeFFMPEGWriter(AbstractVideoWriter):
    """
    Video writer based on FFMPEG using pipe input. Represents a less hard-drive heavy and usually faster
    ``FFMPEGWriter`` counterpart by piping image bytes to FFMPEG after generation. Thus, the video is encoded parallel
    to the image creation and no temporary image files are necessary.
    """

    def __init__(self, path_to_ffmpeg: Optional[str] = None, silent: bool = False):
        """
        :param path_to_ffmpeg: Absolute path to ffmpeg including program name; If none ffmpeg must be available on path.
        :param silent: Whether the FFMPEG output should be hidden (defaults to ``False``).
        """
        if path_to_ffmpeg is not None:
            self.__path_to_ffmpeg = path_to_ffmpeg
        else:
            self.__path_to_ffmpeg = "ffmpeg"

        if silent:
            self.out = self.err = subprocess.DEVNULL
        else:
            self.out = sys.stdout
            self.err = sys.stderr

        p = subprocess.run(f"{self.__path_to_ffmpeg} -version", stdout=self.out, stderr=self.err)
        if p.returncode != 0:
            raise Exception("Could not access FFMPEG via given path")

    def _get_command_list(self, target_fps: float, outputformat: str, parameters: dict[str, str]):

        param_list = [self.__path_to_ffmpeg, "-framerate", str(target_fps), "-f", "image2pipe", "-i", "-"]

        for k, v in parameters.items():
            param_list.append(k)
            param_list.append(str(v))

        param_list.append(f"output{outputformat}")
        return param_list

    def write_with_parameters(
            self,
            target_path: str,
            frames: Generator[Tuple[int, npt.NDArray[Any]], None, None],
            target_fps: float = 29.97,
            parameters: Optional[dict[str, str]] = None,
            callback: Optional[Callable[[int, npt.NDArray[Any]], npt.NDArray[Any]]] = None,
    ) -> None:
        """
        Creates a video from frames using FFMPEG and the 'image2pipe' input. FFMPEG encodes the video parallel to the
        image generation.
        :param target_path: where to write the video
        :param frames: a generator producing index-image pairs representing the frames to be written. The images are
        assumed to be produced in frame order, no additional ordering based on the index is performed.
        :param target_fps: frames per seconds used to create the video
        :param parameters: FFMPEG parameters that should be used e.g. ("-pix_fmt", "yuva420p") for defining the pixel format
        :param callback: callback method for post-processing the frames before adding to video
        :return: None
        """
        temp_folder = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}")
        os.makedirs(temp_folder, exist_ok=True)
        p = None
        try:
            outputformat = pathlib.Path(target_path).suffix
            p_cmd = self._get_command_list(target_fps, outputformat, parameters)
            p = subprocess.Popen(p_cmd, cwd=temp_folder, stdin=subprocess.PIPE, stdout=self.out, stderr=self.err)

            for idx, img in frames:
                if callback is not None:
                    _, img = callback(idx, img)
                img_bytes = cv2.imencode('.bmp', img)[1].tostring()
                p.stdin.write(img_bytes)
                p.stdin.flush()
                del img
                del img_bytes
            p.stdin.close()
            p.wait()

            shutil.copyfile(
                os.path.join(temp_folder, f"output{outputformat}"), target_path
            )
        finally:
            if p is not None and not p.poll():
                p.stdin.close()
                p.wait()
            shutil.rmtree(temp_folder)

    def write(
            self,
            target_path: str,
            frames: Generator[Tuple[int, npt.NDArray[Any]], None, None],
            target_fps: float = 29.97,
            callback: Optional[Callable[[int, npt.NDArray[Any]], npt.NDArray[Any]]] = None,
    ) -> None:
        self.write_with_parameters(
            target_path,
            frames,
            target_fps,
            {"-c:v": "libx264", "-pix_fmt": "yuv420p"},
            callback,
        )


if __name__ == '__main__':
    mypath = r"C:\Users\P41743\Desktop\res"

    onlyfiles = [f for f in os.listdir(mypath) if f.endswith(".png")]
    def sort_function(string: str):
        return int(Path(string).stem)

    onlyfiles.sort(key=sort_function)

    writer = FFMPEGWriter()
    video_path = os.path.join(mypath, "video.mp4")
    gen = ((idx, cv2.imread(x)) for (idx, x) in enumerate(onlyfiles))
    writer.write(video_path, gen)