import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Sequence, Final

import cv2
import numpy as np
from dateutil import tz
from scipy.optimize import minimize
from pyproj import CRS, Transformer
from scipy.spatial.transform import Rotation

from rarf.air_data.air_data_interpolator import AirDataTimeInterpolator
from rarf.air_data.air_data_frame import AirDataFrame
from rarf.air_data.air_data_parser import AirDataParser
from rarf.srt.srt_frame import SrtFrame
from rarf.srt.srt_parser import SrtParser
from rarf.video.video_frame_accessor import VideoFrameAccessor

CORD_TRANSFORMER: Final[Transformer] = Transformer.from_crs(CRS.from_epsg(4326), CRS.from_epsg(32633))
CORD_CONV_MAT: Final[np.ndarray] = np.array([[1, 0, 0], [0, -1, 0], [0, 0, -1]])
CAMERA_ID: Final[int] = 1


def _get_dem_origin(dem_config_path: str) -> tuple[AirDataFrame, list[int]]:
    origin = AirDataFrame()
    try:
        with open(dem_config_path, "r") as jf:
            dem_config = json.load(jf)
        origin.longitude = dem_config["origin_wgs84"]["longitude"]
        origin.latitude = dem_config["origin_wgs84"]["latitude"]
        origin.altitude = dem_config["origin_wgs84"]["altitude"]
        origin.altitude_above_seaLevel = dem_config["origin_wgs84"]["altitude"]
        origin_transformed = CORD_TRANSFORMER.transform(origin.longitude, origin.latitude)
    except (OSError, json.decoder.JSONDecodeError, KeyError, IndexError):
        origin_transformed = [0, 0]
    return origin, origin_transformed


def _get_srt_video_frames(srt_files: list[str]) -> tuple[list[SrtFrame], int, list[int]]:
    parser = SrtParser()

    srt_frames = []
    num_videos = 0
    frame_to_video = []

    for srt_file in srt_files:
        frames = parser.parse(srt_file)

        # apply local time zone
        for frame in frames:
            frame.timestamp = frame.timestamp.replace(tzinfo=tz.tzlocal())

        srt_frames.extend(frames)
        frame_to_video.extend([num_videos] * len(frames))
        num_videos += 1

    return srt_frames, num_videos, frame_to_video


def _get_air_data_video_frames(airdata_file: str, video_timestamp: datetime) -> list[AirDataFrame]:
    ad_parser = AirDataParser()
    ad_frames = ad_parser.parse(airdata_file)
    # AirData files can apparently arbitrarily miss a date time value
    utc = next(ad_frame.datetime.replace(tzinfo=tz.tzutc()) for ad_frame in ad_frames if ad_frame is not None)
    # AirData Frames are in UTC
    start = utc.astimezone(tz.tzlocal())  # convert to local time

    for frame in ad_frames:
        frame.datetime = (
            start
            + timedelta(milliseconds=frame.time)
            - timedelta(milliseconds=ad_frames[0].time)
        )

    ms_offset = ad_parser.get_video_offset(airdata_file, video_timestamp)
    is_videos = [
        frame.isVideo
        if timedelta(milliseconds=frame.time) >= timedelta(milliseconds=ms_offset)
        else False
        for frame in ad_frames
    ]
    videos_max_index = len(is_videos) - 1
    first_idx = is_videos.index(True)
    try:
        last_idx = is_videos.index(False, first_idx) - 1
    except ValueError:
        last_idx = videos_max_index
    assert first_idx < last_idx, f"Frames {first_idx} and {last_idx} do not form a valid video"
    assert (
        ad_frames[first_idx].isVideo
        and ((first_idx == 0) or (not ad_frames[first_idx - 1].isVideo))
        and ad_frames[first_idx + 1].isVideo
    ), f"The found first video frame {first_idx} is not the first local video frame"
    assert (
        ad_frames[last_idx].isVideo
        and ad_frames[last_idx - 1].isVideo
        and ((last_idx == videos_max_index) or (not ad_frames[last_idx + 1].isVideo))
    ), f"The found last video frame {last_idx} is not the last local video frame"

    return ad_frames[first_idx: last_idx + 1]


def _optimize_srt_to_air_data_offset(srt_frames: list[SrtFrame], ad_frames: list[AirDataFrame]) -> float:
    # use minimization to find the best offset

    st = ad_frames[0].datetime  # start time
    srt_seconds = np.array([(srt.timestamp - st).total_seconds() for srt in srt_frames])
    ad_seconds = np.array([(ad.datetime - st).total_seconds() for ad in ad_frames])
    ad_lons = np.array([frame.longitude for frame in ad_frames])
    ad_lats = np.array([frame.latitude for frame in ad_frames])

    def mse(s: float) -> float:
        inter_lon = np.interp(srt_seconds + s, ad_seconds, ad_lons)
        inter_lat = np.interp(srt_seconds + s, ad_seconds, ad_lats)

        mse = np.mean(
            (inter_lon - [frame.longitude for frame in srt_frames]) ** 2
            + (inter_lat - [frame.latitude for frame in srt_frames]) ** 2
        )
        return mse

    res = minimize(mse, 0, method="Nelder-Mead", options={"disp": False})

    return res.x[0]


def _extract_frames(video_files: Sequence[str], srt_frames: Sequence[SrtFrame], frame_to_video: list[int],
                    sampling_rate: int, frame_target: str, img_extension: str) -> tuple[list[str], list[datetime]]:
    frame_accessor = VideoFrameAccessor()
    image_files = []
    image_timestamps = []

    for v_idx, video_file in enumerate(video_files):
        cur_srt_frames = np.array(srt_frames)[np.array(frame_to_video) == v_idx]

        def accessor_callback(frame_idx: int, img: np.ndarray) -> bool:
            if len(cur_srt_frames) <= frame_idx:
                return False

            cur_srt_frame = srt_frames[frame_idx]
            srt_frame_id = cur_srt_frame.id
            timestamp = cur_srt_frame.timestamp
            filename = f"{len(image_files)}_{frame_idx}_{srt_frame_id}.{img_extension}"
            cv2.imwrite(os.path.join(frame_target, filename), img)

            image_files.append(filename)
            image_timestamps.append(timestamp)

            return True

        frame_accessor.access(video_file, accessor_callback, sampling_rate=sampling_rate)

    return image_files, image_timestamps


def _write_image_file(path: str, image_data: Sequence[tuple[int, list, list, int, str]]):
    with open(path, "w+") as f:
        for identifier, r_quat, t_vec, camera_id, image_file in image_data:
            r_quat_str = ' '.join([str(x) for x in r_quat])
            t_vec_str = ' '.join([str(x) for x in t_vec])
            f.write(f"{identifier} {r_quat_str} {t_vec_str} {camera_id} {image_file}\n\n")


def create_colmap_data(video_files: Sequence[str], dem_config_file: str, airdata_file: str, sampling_rate: int,
                       output_dir: str, img_extension: str = "png") -> int:
    """
    Creates Colmap reconstruction formed data from video, SRT, DEM, and AirData data.
    :param video_files: Paths to video files. The respective SRT files are assumed to share the same name.
    :param dem_config_file: Path to the DEM config JSON file.
    :param airdata_file: Path to the AirData CSV file.
    :param sampling_rate: The step size when extracting frames from the videos (default=3).
    A value of 0 or lower causes all frames to be extracted.
    :param output_dir: Path to the directory to save all data to.
    :param img_extension: The extension used for persisting the extracted video frames.
    :return: The number of frames extracted.
    """
    frame_target = os.path.join(output_dir, "images")
    image_file_target = os.path.join(output_dir, "images.txt")
    Path(frame_target).mkdir(exist_ok=True, parents=True)

    video_files = list(video_files)

    # process SRT data
    srt_files = [os.path.splitext(video_file)[0] + '.srt' for video_file in video_files]
    srt_frames, num_videos, frame_to_video = _get_srt_video_frames(srt_files)
    ad_frames = _get_air_data_video_frames(airdata_file, srt_frames[0].timestamp)
    srt_offset = _optimize_srt_to_air_data_offset(srt_frames, ad_frames)
    srt_offset_td = timedelta(seconds=srt_offset)
    for srt in srt_frames:
        srt.timestamp = srt.timestamp + srt_offset_td

    image_files, image_timestamps = _extract_frames(video_files, srt_frames, frame_to_video, sampling_rate, frame_target,
                                                    img_extension)

    interpolated_frames = AirDataTimeInterpolator(ad_frames)(image_timestamps)

    origin, origin_transformed = _get_dem_origin(dem_config_file)
    origin_altitude = origin.altitude or 0

    image_data = []
    for i, image_file in enumerate(image_files):
        frame = interpolated_frames[i]
        frame_altitude = frame.altitude or 0
        height_diff = frame_altitude - origin_altitude

        frame_coord = CORD_TRANSFORMER.transform(frame.latitude,  frame.longitude)
        t_vec = [
            frame_coord[0] - origin_transformed[0],
            frame_coord[1] - origin_transformed[1],
            height_diff,
        ]
        col_t_vec: list = (CORD_CONV_MAT @ t_vec).tolist()

        r_vec = [
            float(frame.gimbal_pitch) + 90 if frame.gimbal_pitch is not None else 0.0,
            # pitch is rotation around X axis (+90° because per default it faces forward)
            0,  # roll (Y-axis) is always zero!
            frame.compass_heading if frame.compass_heading is not None else 0.0,
        ]
        r_vec = [r % 360 for r in r_vec]
        r_mat = Rotation.from_euler("xyz", r_vec, degrees=True).as_matrix()
        col_r_quat = Rotation.from_matrix(CORD_CONV_MAT @ r_mat).as_quat(False)
        col_r_quat = [col_r_quat[3], col_r_quat[0], col_r_quat[1], col_r_quat[2]]  # colmap uses W, X, Y, Z order

        image_data.append((i, col_r_quat, col_t_vec, CAMERA_ID, image_file))

    _write_image_file(image_file_target, image_data)

    return len(image_data)
