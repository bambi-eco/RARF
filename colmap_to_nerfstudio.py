import os
from argparse import ArgumentParser
from dataclasses import dataclass

from rarf.colmap.convert import colmap_to_nerfstudio


@dataclass
class ConvArgs:
    camera_file: str
    image_file: str
    output_dir: str
    image_file_dir: str = "./images"


def _parse_arguments() -> ConvArgs:
    parser = ArgumentParser(description="Converts a Colmap reconstruction to the transform-format used by Nerfstudio.")

    parser.add_argument("camera_file", type=str, help="Path to the Colmap camera.(txt,bin) file.")
    parser.add_argument("image_file", type=str, help="Path to the Colmap images.(txt,bin) file.")
    parser.add_argument("output_dir", type=str, help="Output destination (default=./output).")
    parser.add_argument("image_file_dir", type=str, help="Directory containing the images.", default="./images")

    args = parser.parse_args()
    args_dict = vars(args)
    return ConvArgs(**args_dict)


def main() -> None:
    args = _parse_arguments()
    colmap_to_nerfstudio(args.camera_file, args.image_file, args.output_dir, args.image_file_dir)
    print(f"Result written to {os.path.join(args.output_dir, 'transform.json')}")


if __name__ == '__main__':
    main()
