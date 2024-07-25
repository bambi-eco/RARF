import json
from pathlib import Path
from typing import Final

import numpy as np
from scipy.spatial.transform import Rotation

from rarf.colmap.camera import Camera
from rarf.colmap.data import CAMERA_MODEL_BY_NAME, read_cameras_binary, read_cameras_text, read_images_binary, \
    read_images_text
from rarf.geo.coordinate_system import CoordinateSystem
from rarf.geo.direction import Direction

MATCHED_POSES_SYSTEM: Final[CoordinateSystem] = CoordinateSystem(Direction.RIGHT, Direction.DOWN, Direction.BACKWARD)


def opencv_to_camera(data: dict, identifier: int = 0) -> Camera:
    """
    Converts a OpenCV camera description to a camera instance. As camera instances represent the Colmap format, only the
    first four distortion coefficients are used by the created instance.
    :param data: The dictionary containing all the OpenCV camera information. This dictionary must contain the camera
    matrix ``"mtx"``, the distortion coefficients ``"dist"``, the width ``"width"``, and the height ``"height"``.
    :param identifier: The identifier to be assigned to the camera (defaults to ``0``).
    :return: The created camera instance.
    """
    mtx = data["mtx"]
    fx = mtx[0][0]
    fy = mtx[1][1]
    cx = mtx[0][2]
    cy = mtx[1][2]

    dist = data["dist"]
    dist_count = len(dist)
    if dist_count < 4:
        dist = np.pad(dist, (0, 4 - dist_count), "constant", constant_values=(0.0, 0.0))
    dist = dist[:4]

    params = [fx, fy, cx, cy, *dist]
    width = data["width"]
    height = data["height"]
    model = CAMERA_MODEL_BY_NAME["OPENCV"]
    return Camera(identifier=identifier, model=model, width=width, height=height, params=params)


def colmap_to_nerfstudio(camera_file: str, image_file: str, output_dir: str, images_root: str = "./images") -> None:
    """
    Converts Colmap results to the transform-format used by Nerfstudio.
    Heavily inspired and based on the implementation included with Nerfstudio:
    https://github.com/nerfstudio-project/nerfstudio/blob/c572eb7f19da8e744b97a997d36e425c870a5647/nerfstudio/process_data/colmap_utils.py#L390
    :param camera_file: The Colmap camera file. Supports both binary and text format.
    :param image_file: The Colmap image file. Supports both binary and text format.
    :param output_dir: The directory the transform JSON file should be put into.
    :param images_root: The root directory in which all images are stored (defaults to ``"./images"``).
    """
    camera_path = Path(camera_file)
    if camera_path.suffix == ".bin":
        cameras = read_cameras_binary(camera_path)
    else:
        cameras = read_cameras_text(camera_path)
    if len(cameras) > 1:
        raise RuntimeError("Only single camera shared for all images is supported.")
    camera = cameras[0]
    if camera.model.model_name != "OPENCV":
        raise RuntimeError("Only 'OPENCV' camera models are supported.")

    out_dict = {
        "w": camera.width,
        "h": camera.height,
        "fl_x": camera.params[0],
        "fl_y": camera.params[1],
        "cx": camera.params[2],
        "cy": camera.params[3],
        "k1": camera.params[4],
        "k2": camera.params[5],
        "p1": camera.params[6],
        "p2": camera.params[7],
        "camera_model": "OPENCV",
    }

    image_path = Path(image_file)
    if image_path.suffix == ".bin":
        images = read_images_binary(image_path)
    else:
        images = read_images_text(image_path)
    images_root_path = Path(images_root)

    conv_function = CoordinateSystem.colmap().convert_func(CoordinateSystem.nerfstudio_world())

    frames = []
    for image in images:
        r_quat = image.r_quat
        r_quat = [r_quat[1], r_quat[2], r_quat[3], r_quat[0]]  # convert back to X, Y, Z, W order
        r_mat = Rotation.from_quat(r_quat).as_matrix()

        t_vec = np.array(image.t_vec)

        r_mat = conv_function(r_mat)
        t_vec = conv_function(t_vec)

        c2w = np.identity(4)
        c2w[:3, :3] = r_mat
        c2w[:3, 3] = t_vec

        name = images_root_path / image.name

        frame = {
            "file_path": name.as_posix(),
            "transform_matrix": c2w.tolist()
        }

        frames.append(frame)

    out_dict["frames"] = frames

    output_dir = Path(output_dir)
    with open(output_dir / "transforms.json", "w", encoding="utf-8") as jf:
        json.dump(out_dict, jf, indent=4)
