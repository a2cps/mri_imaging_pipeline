from pathlib import Path

import pandas as pd
import numpy as np
import nibabel as nb

import utils

SMALLWOOD = (
    Path("/opt/tapis/neg_mni152_C05_1k_clust.nii.gz")
    if Path("/opt/tapis/neg_mni152_C05_1k_clust.nii.gz").exists()
    else Path("neg_mni152_C05_1k_clust.nii.gz")
)


def get_volume(nii: nb.nifti1.Nifti1Image, value: float | int) -> float:
    if not len(nii.shape) == 3:
        raise AssertionError("Expected 3d image")
    n_voxels = np.isclose(nii.get_fdata(), value).sum()
    return n_voxels * np.prod(nii.header.get_zooms())


def get_smallwood(mridir: Path) -> pd.DataFrame:
    smallwood: list[pd.DataFrame] = []
    # https://neuro-jena.github.io/cat12-help/#naming
    for wmp1 in mridir.glob("mwp1*nii"):
        sub = utils._get_sub(wmp1)
        ses = utils._get_ses(wmp1)
        nii: nb.nifti1.Nifti1Image = nb.nifti1.load(wmp1)  # type: ignore
        volumes: list[pd.DataFrame] = []
        for cluster in range(1, 3):
            cluster_volume = get_volume(nii, cluster)
            volumes.append(
                pd.DataFrame(
                    {
                        "sub": [sub],
                        "ses": [ses],
                        f"smallwood_cluster_mwp1_{cluster}": [cluster_volume],
                    }
                )
            )
        smallwood.append(pd.concat(volumes, ignore_index=True))

    return pd.concat(smallwood, ignore_index=True)


def make_toplevel(outdir: Path) -> None:
    get_smallwood(mridir=outdir / "mri").to_csv(
        outdir / "smallwood.tsv", sep="\t", index=False
    )


def copy(outdir: Path, inroot: Path) -> None:
    if not outdir.exists():
        outdir.mkdir(parents=True)

    for src in inroot.glob("cat12/*"):
        for out in ["label", "mri", "report", "surf"]:
            utils.mergetree_overwrite(src / out, outdir / out)
