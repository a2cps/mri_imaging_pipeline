from pathlib import Path

import pandas as pd
import numpy as np
import nibabel as nb
from biomarkers import utils as bu

import utils

SMALLWOOD = (
    Path("/opt/tapis/tpl-MNI152NLin2009cAsym_atlas-smallwood_dseg.nii")
    if Path(
        "/opt/tapis/tpl-MNI152NLin2009cAsym_atlas-smallwood_dseg.nii"
    ).exists()
    else Path("tpl-MNI152NLin2009cAsym_atlas-smallwood_dseg.nii")
)


def get_volume(nii: nb.nifti1.Nifti1Image, value: float | int) -> float:
    if not len(nii.shape) == 3:
        raise AssertionError("Expected 3d image")
    n_voxels = np.isclose(nii.get_fdata(), value).sum()
    return n_voxels * np.prod(nii.header.get_zooms())  # type: ignore


def get_smallwood(mridir: Path) -> pd.DataFrame:
    smallwood: list[pd.DataFrame] = []
    # https://neuro-jena.github.io/cat12-help/#naming
    for p1 in mridir.glob("*wp1*nii"):
        sub = bu.get_sub_from_sublong(p1)
        ses = bu.get_ses_from_sublong(p1)
        nii: nb.nifti1.Nifti1Image = nb.nifti1.load(p1)  # type: ignore
        volumes: list[pd.DataFrame] = []
        for cluster in range(1, 3):
            cluster_volume = get_volume(nii, cluster)
            volumes.append(
                pd.DataFrame(
                    {
                        "sub": [sub],
                        "ses": [ses],
                        "modulated": [p1.name.startswith("m")],
                        f"smallwood_cluster_{cluster}": [cluster_volume],
                    }
                ).set_index(["sub", "ses", "modulated"])
            )
        smallwood.append(pd.concat(volumes, axis=1))

    return pd.concat(smallwood, axis=0)


def make_toplevel(outdir: Path) -> None:
    get_smallwood(mridir=outdir / "mri").to_csv(
        outdir / "smallwood.tsv", sep="\t"
    )


def copy(outdir: Path, inroot: Path) -> None:
    bu.mkdir_recursive(outdir)

    for src in inroot.glob("cat12/*"):
        for out in ["label", "mri", "report", "surf"]:
            utils.mergetree_overwrite(src / out, outdir / out)
