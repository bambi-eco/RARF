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

When flying with a typical flight speed of 5 m/s the low frequency of the flight log is not sufficient, since it would result in approximately one position every 50 cm. On the other hand the low-precision position in the video log is also not sufficient. Because of that, our pipeline uses a time- and position-based optimization approach to synchronize both log files, allowing to have a high precision at a high frequency, required for the camera extrinsics in novel view synthesis.

![sync](./images/sync.svg)


## Results



https://github.com/user-attachments/assets/d892233f-c173-4b1b-b873-db0f1285d75d



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

