import argparse
from dataclasses import dataclass

from rarf import create_colmap_data


@dataclass
class RarfArgs:
    video_files: list[str]
    dem_config_file: str
    airdata_file: str
    output_dir: str
    sampling_rate: int = 3


def _parse_arguments() -> RarfArgs:
    parser = argparse.ArgumentParser(
        description="Extracts a Colmap reconstruction from video, SRT, DEM, and AirData data."
    )

    parser.add_argument("video_files", type=str, nargs="+",
                        help="Paths to video files. The respective SRT files are assumed to share the same name.")
    parser.add_argument("dem_config_file", type=str, help="Path to the DEM config JSON file.")
    parser.add_argument("airdata_file", type=str, help="Path to the AirData CSV file.")
    parser.add_argument("output_dir", type=str, help="Output destination (default=./output)")
    parser.add_argument("-s", "--sampling_rate", type=int, default=3,
                        help="The step size when extracting frames from the videos (default=3). "
                             "A value of 0 or lower causes all frames to be extracted.")
    args = parser.parse_args()
    args_dict = vars(args)
    return RarfArgs(**args_dict)


def main() -> None:
    args = _parse_arguments()
    frame_count = create_colmap_data(args.video_files, args.dem_config_file, args.airdata_file, args.sampling_rate,
                                     args.output_dir)
    print(f"Extracted {frame_count} frames")


if __name__ == '__main__':
    main()
