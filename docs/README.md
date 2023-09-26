# Documents

## Folder Path

The structure of folders is as follows:

```
/root/
├── workspace/  # repository管理
└── datadrive/  # docker mount/S3管理
    ├── {algo task}  # e.g. ObjectDetection, PoseEstimation, ...
    │   ├── dataset/
    │   │   └── {dataset hash}/
    │   │       ├── cfg/
    │   │       └── data.zip
    │   ├── models/
    │   │   └── {model hash}/
    │   │       ├── checkpoints/
    │   │       └── {model name}.yml
    │   └── samples/
    │       └── data/
    └── {project name}  # project data which should not be included in any dataset
        └── {dataset name}/
            ├── dataset/
            │   ├── cfg/
            │   └── data.zip
            ├── demo_videos/
            ├── drawn_videos/
            ├── interim/
            ├── result_figs/
            └── results/
```

## S3

We use S3 to share DataSet.

The S3 bucket correspond to this repository, whose name is `project-template`, has a DataSet path as follows:
```
s3://aces-project-{template}/
├── raw/  # raw data
└── root/
    └── datadrive/
        ├── {algo task}  # e.g. ObjectDetection, PoseEstimation, ...
        │   ├── dataset/
        │   │   └── {dataset hash}/
        │   │       ├── cfg/
        │   │       └── data.zip
        │   ├── models/
        │   │   └── {model hash}/
        │   │       ├── checkpoints/
        │   │       └── {model name}.yml
        │   └── samples/
        │       └── data/
        └── {project name}  # project data which should not be included in any dataset
            └── {dataset name}/ 
                ├── dataset/
                │   ├── cfg/
                │   └── data.zip
                ├── demo_videos/  # videos to show customers 
                │   └── {experiment_version_name}  # e.g. v1, v2, ...
                ├── drawn_videos/  # video visualization of features (option) 
                │   └── {experiment_version_name}  # e.g. v1, v2, ...
                ├── interim/  # intermediate files of calculation
                │   └── {experiment_version_name}  # e.g. v1, v2, ...
                ├── result_figs/  # timeseries graph which show inference and label
                │   └── {experiment_version_name}  # e.g. v1, v2, ...
                └── results/  # inference results to make demo_videos
                     └── {experiment_version_name}  # e.g. v1, v2, ...
```
