[![Static Badge](https://img.shields.io/badge/DOI-10.1145%2F3641234.3671077-blue)](https://doi.org/10.1145/3641234.3671077) [![Static Badge](https://img.shields.io/badge/Webpage-bambi--eco.github.io%2FRARF%2F-blue)](https://bambi-eco.github.io/RARF)

# Reconstructionless Airborne Radiance Fields

Christoph Praschl, Leopold Böss, David C. Schedl

This repository contains the official authors implementation associated with the paper "Reconstructionless Airborne Radiance Fields", which can be found [here](https://doi.org/10.1145/3641234.3671077) published at [SIGGRAPH 2024](https://s2024.siggraph.org/).

![sync](./images/header.svg)

_Abstract: For a few years now, radiance fields and especially neural radiance fields (NeRF) represent a cutting-edge advancement in computer graphics, enabling the generation of high-quality novel views for scenes captured from various angles through multiple photos or videos. Instead of traditional methods that rely on geometric representations or explicit scene meshes, NeRF leverages neural networks to directly model the volumetric scene function. Like this, the approach has dramatically transformed the landscape of novel-view synthesis, offering unprecedented realism and flexibility in rendering complex scenes. However, the training of NeRF models is typically based on computationally intensive image-based reconstructions of camera positions and visual features of the addressed scenes using Structure from Motion (SfM). In airborne imaging, camera poses are already explicitly available by exact global navigation satellite systems (i.e., GPS) and internal sensors of aerial vehicles. In this work, we introduce a novel processing pipeline designed to effectively harness image and sensor data captured by uncrewed aerial vehicles (UAVs) to train NeRF-like models without needing SfM._

## Overview

The proposed pipeline relies on automated UAV flights utilizing DJI-manufactured devices. These UAVs are equipped to capture (multi-spectral) image/video data while simultaneously logging the camera extrinsics based on global positions and global orientations of both the drone and the camera gimbal. The global position is expressed as WGS84 coordinates consisting of longitude, latitude, and altitude. DJI provides two types of log files:
- Flight log (binary encoded; can be accessed using tools like [Airdata](https://airdata.com/)) at 10 Hz with 13-digit positional precision (~ 2 cm spatial precision)
- Video log (.srt file; has to be activated in DJI Pilot app: Settings > Camera > Advanced Camera Settings > Video Subtitles) at 29.97 Hz with 5-digit positional precision (~ 1 m spatial precision)

When flying with a typical flight speed of 5 m/s the low frequency of the flight log is not sufficient, since it would result in approximately one position every 50 cm. On the other hand the low-precision position in the video log is also not sufficient. Because of that, our pipeline uses a time- and position-based optimization approach to synchronize both log files, allowing to have a high precision at a high frequency. In combination with camera intrinsics from previous calibration, the so created camera extrinsics are the basis for training novel view synthesis models like NeRF or Gaussian Splatting.

![sync](./images/sync.svg)




|                      | SfM                                     | Ours                        |
|----------------------|-----------------------------------------|-----------------------------|
| Runtime Complexity   | Exponential                             | Linear                      |
| Runtime (854 images) | 511 min                                 | 2.54 sec                    |
| Quality              | Ground Truth                            | Comparable / slightly worse |
| Features             | Intrinsics, Extrinsics, Sparse 3D model | Extrinsics                  |


## Results

The evaluation is executed on a Windows 10 system with an AMD Ryzen Threadripper 2990WX CPU, four Nvidia RTX 2080 GPUs, and 128 GB RAM. The SfM-based reconstruction requires 511.273 min for the 10 FPS dataset, with 0.25 min for feature extraction, 7.477 min for the exhaustive matching, and 503.546 min for the actual reconstruction. For the 2 FPS dataset, the process requires 9.916 min, which consists of 0.066 min for feature extraction, 0.294 min for feature matching, and 9.556 min for the reconstruction. In comparison, our pipeline utilizes the log files created by the drone in flight. This conversion process takes 2.54 sec for the 10 FPS dataset and 2.48 sec for the 2 FPS version.

Both techniques result in similar camera poses with slight variations. To quantify the difference, we transformed the SfM-based poses to our extrinsic, using iterative-closest-point matching with a rigid-body transformation (including scaling), and computed the mean difference of corresponding camera positions, leading to average differences of 0.39 and 0.11 m for the 2 and 10 FPS dataset, respectively. 

![positions](./images/positions.png)

The qualitative comparison of the trained NeRFs (Nerfstudio's nerfacto model in the default 6GB size) shows comparable qualities of the synthesized novel views using ours and the SfM-based reconstruction with both e.g., having problems in the roof area or the meadow in front of the building (c.f. Figure \ref{fig:a} and \ref{fig:b}). However, with GS (Nerfstudio's splatfacto model in the default 6GB size), SfM-based reconstruction presents notable advantages (e.g. bottom left corner of the building) owing to the presence of reconstructed sparse 3D points as seed information in the SfM reconstruction only. In contrast, our method relies on randomly initialized geometries

![result](./images/result.svg)

https://github.com/user-attachments/assets/d892233f-c173-4b1b-b873-db0f1285d75d

### Additional scene

In addition to the scene described in the research paper, we have prepared another novel view synthesis scene:

https://github.com/user-attachments/assets/cf025dab-1cf5-4cd0-9068-ecba2301ac53




## Bibtex

```
@inproceedings{rarf,
    author = {Praschl, Christoph and Böss, Leo and Schedl, David C.},
    title = {Reconstructionless Airborne Radiance Fields},
    year = {2024},
    publisher = {Association for Computing Machinery},
    address = {New York, NY, USA},
    url = {https://doi.org/10.1145/3641234.3671077},
    doi = {10.1145/3641234.3671077},
    booktitle = {ACM SIGGRAPH 2024 Posters},
    location = {Denver, CO, USA},
    series = {SIGGRAPH '24}
}
```

## Funding and Acknowledgments

This research is funded by the Austrian Research Promotion Agency FFG (project _BAMBI_; program number: 892231) within the funding program Ai4Green, for which the budget is provided by the Federal Republic of Austria. 

