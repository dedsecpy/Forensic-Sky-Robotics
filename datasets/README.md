# Datasets (not included in this GitHub repository)

Raw videos are large and are **excluded from git**. Place them locally under this folder before full reproduction.

| Folder | Source | Role |
|---|---|---|
| `cas_fd/` | [CAS-FD foul-vs-dive](https://huggingface.co/datasets/jahid114593/foul-vs-dive-dataset) | Primary labeled evaluation (final ~64% metrics) |
| `sportsd_2022_men/` | [SportsD](https://huggingface.co/datasets/addisonwu05/sportsd) | World Cup clips / ordinary-play negatives |
| `broadcast_halves/` | Local FIFA WC 2022 second-half broadcasts + StatsBomb events | Continuous foul forecasting |
| `kth_pose/` | [KTH Multiview Football II](https://www.csc.kth.se/cvap/cvg/?page=footballdataset2) | External pose benchmark |

After downloading, run the `data_prep/` and `training/` scripts listed in the root README. Trained weights and locked metrics are already in `models/` and `research_results/`.
