from typing import Sequence, Final

import numpy as np

from rarf.colmap.base_image import BaseImage
from rarf.colmap.camera import CameraModel, Camera
from rarf.colmap.point import Point2D, Vector4, Vector3, Point3D, IntVector3
from rarf.util.io import write_bytes, read_bytes, read_string
from rarf.util.types import Pathable

CAMERA_MODELS: Final[set[CameraModel]] = {
    CameraModel(model_id=0, model_name="SIMPLE_PINHOLE", num_params=3),
    CameraModel(model_id=1, model_name="PINHOLE", num_params=4),
    CameraModel(model_id=2, model_name="SIMPLE_RADIAL", num_params=4),
    CameraModel(model_id=3, model_name="RADIAL", num_params=5),
    CameraModel(model_id=4, model_name="OPENCV", num_params=8),
    CameraModel(model_id=5, model_name="OPENCV_FISHEYE", num_params=8),
    CameraModel(model_id=6, model_name="FULL_OPENCV", num_params=12),
    CameraModel(model_id=7, model_name="FOV", num_params=5),
    CameraModel(model_id=8, model_name="SIMPLE_RADIAL_FISHEYE", num_params=4),
    CameraModel(model_id=9, model_name="RADIAL_FISHEYE", num_params=5),
    CameraModel(model_id=10, model_name="THIN_PRISM_FISHEYE", num_params=12)
}
CAMERA_MODEL_BY_ID: Final[dict[int, CameraModel]] = {camera_model.model_id: camera_model for camera_model in CAMERA_MODELS}
CAMERA_MODEL_BY_NAME: Final[dict[str, CameraModel]] = {camera_model.model_name: camera_model for camera_model in CAMERA_MODELS}


def write_cameras_binary(cameras: Sequence[Camera], path: Pathable) -> None:
    """
    Write a sequence for cameras to a file in the binary Colmap camera format.
    :param cameras: The sequence of cameras to write.
    :param path: The path of the file to write.
    """
    with open(path, "wb+") as file:
        write_bytes(file, len(cameras), "Q")

        for camera in cameras:
            data = (camera.identifier, camera.model.model_id, camera.width, camera.height)
            write_bytes(file, data, "IiQQ")
            for param in camera.params:
                write_bytes(file, param, "d")


def read_cameras_binary(path: Pathable) -> list[Camera]:
    """
    Read a sequence of cameras from a file in the binary Colmap camera format.
    :param path: The path of the file to read.
    :return: A sequence of cameras read from the file.
    """
    cameras = []
    with open(path, "rb") as file:
        num_cameras = read_bytes(file, "Q")
        for _ in range(num_cameras):
            camera_id, model_id, width, height = read_bytes(file, byte_format="IiQQ")
            model = CAMERA_MODEL_BY_ID[model_id]
            num_params = model.num_params
            params = read_bytes(file, byte_format=f"{'d' * num_params}")
            cameras.append(Camera(identifier=camera_id, model=model, width=width, height=height,
                                  params=np.array(params)))
        assert len(cameras) == num_cameras
    return cameras


def write_cameras_text(cameras: Sequence[Camera], path: Pathable) -> None:
    """
    Write a sequence for cameras to a file in the text Colmap camera format.
    :param cameras: The sequence of cameras to write.
    :param path: The path of the file to write.
    """
    with open(path, "w+") as file:
        for camera in cameras:
            params_str = " ".join([str(x) for x in camera.params])
            file.write(f"{camera.identifier} {camera.model.model_name} {camera.width} {camera.height} {params_str} \n")


def read_cameras_text(path: Pathable) -> list[Camera]:
    """
    Read a sequence of cameras from a file in the text Colmap camera format.
    :param path: The path of the file to read.
    :return: A sequence of cameras read from the file.
    """
    cameras = []
    with open(path, "r") as file:
        while True:
            line = file.readline()
            if not line:
                break
            line_strip = line.lstrip()
            if line_strip.startswith("#") or line_strip == "":
                continue
            line = line.strip()
            splits = line.split(" ")
            camera_id = int(splits[0])
            model = CAMERA_MODEL_BY_NAME[splits[1]]
            width = int(splits[2])
            height = int(splits[3])
            params = [float(x) for x in splits[4:]]
            cameras.append(Camera(identifier=camera_id, model=model, width=width, height=height, params=params))

    return cameras


def write_images_binary(images: list[BaseImage], path: Pathable) -> None:
    """
    Write a sequence of images to a file in the binary Colmap image format.
    :param images: The sequence of images to write.
    :param path: The path of the file to write.
    """
    with open(path, "wb+") as file:
        write_bytes(file, len(images), "Q")

        for image in images:
            write_bytes(file, image.identifier, "I")
            write_bytes(file, image.r_quat, "dddd")
            write_bytes(file, image.t_vec, "ddd")
            write_bytes(file, image.camera_id, "I")

            name = image.name + "\0"
            file.write(name.encode("latin-1"))

            write_bytes(file, len(image.points2D), "Q")
            for point2D in image.points2D:
                write_bytes(file, (point2D.x, point2D.y, point2D.point3D_id), "ddQ")


def read_images_binary(path: Pathable) -> list[BaseImage]:
    """
    Read a sequence of images from a file in the binary Colmap image format.
    :param path: The path of the file to read.
    :return: A sequence of images read from the file.
    """
    images = []
    with open(path, "rb") as file:
        num_images = read_bytes(file, "Q")
        for _ in range(num_images):
            image_id = read_bytes(file, "I")
            qvec = read_bytes(file, "dddd")
            tvec = read_bytes(file, "ddd")
            camera_id = read_bytes(file, "I")
            name = read_string(file)

            num_points2D = read_bytes(file, "Q")
            points2D = []
            for _ in range(num_points2D):
                x, y, point3D_id = read_bytes(file, "ddQ")
                points2D.append(Point2D(x, y, point3D_id))

            image = BaseImage(identifier=image_id, r_quat=qvec, t_vec=tvec, camera_id=camera_id, name=name,
                              points2D=points2D)
            images.append(image)

    return images


def write_images_text(images: list[BaseImage], path: Pathable) -> None:
    """
    Write a sequence of images to a file in the text Colmap image format.
    :param images: The sequence of images to write.
    :param path: The path of the file to write.
    """
    with open(path, "w+") as file:
        for image in images:
            file.write(
                f"{image.identifier} {' '.join([str(x) for x in image.r_quat])} {' '.join([str(x) for x in image.t_vec])} {image.camera_id} {image.name}\n\n")


def read_images_text(path: Pathable) -> list[BaseImage]:
    """
    Read a sequence of images from a file in the text Colmap image format.
    :param path: The path of the file to read.
    :return: A sequence of images read from the file.
    """
    images = []
    with open(path, "r") as file:
        cnt = 0
        identifier = None
        qvec = None
        tvec = None
        camera_id = None
        name = None
        while True:
            line = file.readline()
            cnt += 1
            if not line:
                break
            line = line.strip()
            splits = line.split(" ")
            if cnt % 2 != 0:
                image_id = int(splits[0])
                qvec = Vector4((float(splits[1]), float(splits[2]), float(splits[3]), float(splits[4])))
                tvec = Vector3((float(splits[5]), float(splits[6]), float(splits[7])))
                camera_id = int(splits[8])
                name = splits[9]
                identifier = image_id
                qvec = qvec
                tvec = tvec
                camera_id = camera_id
                name = name
            else:
                points = []
                if len(splits) >= 3:
                    x = None
                    y = None
                    for idx, split in enumerate(splits):
                        if idx % 3 == 0:
                            points.append(Point2D(x, y, int(split)))
                        elif idx % 2 == 0:
                            y = float(split)
                        else:
                            x = float(split)
                images.append(BaseImage(identifier=image_id, r_quat=qvec, t_vec=tvec, camera_id=camera_id, name=name,
                                        points2D=points))
    return images


# noinspection PyPep8Naming
def write_points3D_binary(points3D: Sequence[Point3D], path: Pathable) -> None:
    """
    Write a sequence of points3D to a file in the binary Colmap point3D format.
    :param points3D: The sequence of points3D to write.
    :param path: The path of the file to write.
    """
    with open(path, "wb+") as file:
        write_bytes(file, len(points3D), "Q")

        for point3D in points3D:
            write_bytes(file, point3D.identifier, "Q")
            write_bytes(file, point3D.xyz, "ddd")
            write_bytes(file, point3D.rgb, "BBB")
            write_bytes(file, point3D.error, "d")

            write_bytes(file, len(point3D.image_ids), "Q")
            for image_id, point2D_idx in zip(point3D.image_ids, point3D.point2D_idxs):
                write_bytes(file, image_id, "I")
                write_bytes(file, point2D_idx, "I")


# noinspection PyPep8Naming
def read_points3D_binary(path: Pathable) -> list[Point3D]:
    """
    Read a sequence of points3D from a file in the binary Colmap point3D format.
    :param path: The path of the file to read.
    :return: A sequence of points3D read from the file.
    """
    points3D = []
    with open(path, "rb") as file:
        num_points3D = read_bytes(file, "Q")
        for _ in range(num_points3D):
            point3D_id = read_bytes(file, "Q")
            xyz = read_bytes(file, "ddd")
            rgb = read_bytes(file, "BBB")
            error = read_bytes(file, "d")

            image_ids = []
            point2D_idxs = []
            num_img_point2D = read_bytes(file, "Q")
            for _ in range(num_img_point2D):
                image_ids.append(read_bytes(file, "I"))
                point2D_idxs.append(read_bytes(file, "I"))

            point3D = Point3D(identifier=point3D_id, xyz=xyz, rgb=rgb, error=error, image_ids=image_ids, point2D_idxs=point2D_idxs)
            points3D.append(point3D)

    return points3D


# noinspection PyPep8Naming
def write_points3D_text(points3D: Sequence[Point3D], path: Pathable) -> None:
    """
    Write a sequence of points3D to a file in the text Colmap point3D format.
    :param points3D: The sequence of points3D to write.
    :param path: The path of the file to write.
    """
    with open(path, "w+") as file:
        for point in points3D:
            track = []
            for idx, image_id in point.image_ids:
                track.append((image_id, point.point2D_idxs[idx]))

            file.write(f"{point.identifier} {' '.join([str(x) for x in point.xyz])} {' '.join([str(x) for x in point.rgb])} {point.error} {' '.join([str(j) for sub in track for j in sub])}\n")


# noinspection PyPep8Naming
def read_points3D_text(path: Pathable) -> list[Point3D]:
    """
    Read a sequence of points3D from a file in the text Colmap point3D format.
    :param path: The path of the file to read.
    :return: A sequence of points3D read from the file.
    """
    points3D = []
    with open(path, "r") as file:
        while True:
            line = file.readline()
            if not line:
                break
            line = line.strip()
            splits = line.split(" ")
            point3D_id = int(splits[0])
            xyz = Vector3((float(splits[1]), float(splits[2]), float(splits[3])))
            rgb = IntVector3((int(splits[4]), int(splits[5]), int(splits[6])))
            error = float(splits[7])

            image_ids = []
            point2D_idxs = []
            for idx, split in enumerate(splits[8:]):
                if idx % 2 == 0:
                    point2D_idxs.append(int(split))
                else:
                    image_ids.append(int(split))
            point3D = Point3D(identifier=point3D_id, xyz=xyz, rgb=rgb, error=error, image_ids=image_ids, point2D_idxs=point2D_idxs)
            points3D.append(point3D)
    return points3D
