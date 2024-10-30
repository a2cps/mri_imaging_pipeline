from pathlib import Path

import nibabel as nb
import numpy as np
import pandas as pd
import utils
from biomarkers import utils as bu
from nilearn import maskers

SMALLWOOD = (
    Path("/opt/tapis/tpl-MNI152NLin2009cAsym_atlas-smallwood_dseg.nii.gz")
    if Path("/opt/tapis/tpl-MNI152NLin2009cAsym_atlas-smallwood_dseg.nii.gz").exists()
    else Path("tpl-MNI152NLin2009cAsym_atlas-smallwood_dseg.nii.gz")
)

HENN = (
    Path(
        "/opt/tapis/tpl-MNI152NLin2009cAsym_atlas-henn_desc-controlspatientgmtfce05_dseg.nii.gz"
    )
    if Path(
        "/opt/tapis/tpl-MNI152NLin2009cAsym_atlas-henn_desc-controlspatientgmtfce05_dseg.nii.gz"
    ).exists()
    else Path(
        "tpl-MNI152NLin2009cAsym_atlas-henn_desc-controlspatientgmtfce05_dseg.nii.gz"
    )
)


def get_volume(nif: Path, masker: maskers.NiftiLabelsMasker) -> np.ndarray:
    nii: nb.nifti1.Nifti1Image = nb.nifti1.load(nif)  # type: ignore
    if not len(nii.shape) == 3:
        raise AssertionError("Expected 3d image")
    n_voxels = masker.fit_transform(nii).squeeze()
    return n_voxels * np.prod(nii.header.get_zooms())  # type: ignore


def get_atlas_volumes(mridir: Path, atlas: Path) -> pd.DataFrame | None:
    out = []
    masker = maskers.NiftiLabelsMasker(labels_img=atlas, strategy="sum")
    # https://neuro-jena.github.io/cat12-help/#naming
    for p1 in mridir.glob("*wp1*nii"):
        sub = bu.get_sub_from_sublong(p1)
        ses = bu.get_ses_from_sublong(p1)
        cluster_volume = get_volume(p1, masker)
        volumes = {
            "sub": sub,
            "ses": ses,
            "mri": bu.img_stem(p1),
            "atlas": bu.img_stem(atlas),
            "cluster": list(range(len(cluster_volume))),
            "volume": cluster_volume,
        }
        out.append(pd.DataFrame(volumes).set_index(["sub", "ses", "mri", "atlas"]))

    return pd.concat(out, axis=0) if len(out) else None


def make_toplevel(outdir: Path) -> None:
    bu.mkdir_recursive(outdir)
    smallwood_volumes = get_atlas_volumes(mridir=outdir / "mri", atlas=SMALLWOOD)
    henn_volumes = get_atlas_volumes(mridir=outdir / "mri", atlas=HENN)
    if smallwood_volumes is not None and henn_volumes is not None:
        pd.concat([smallwood_volumes, henn_volumes]).to_csv(
            outdir / "cluster_volumes.tsv", sep="\t"
        )


def copy(outdir: Path, inroot: Path) -> None:
    bu.mkdir_recursive(outdir)

    for src in inroot.glob("cat12/*"):
        for out in ["label", "mri", "report", "surf"]:
            utils.mergetree_overwrite(src / out, outdir / out)
