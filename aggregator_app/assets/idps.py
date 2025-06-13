from pathlib import Path

import nibabel as nb
import numpy as np
import polars as pl
from biomarkers import utils as bu


def get_nii_volume(f: Path) -> float:
    nii = nb.nifti1.Nifti1Image.load(f)
    return (nii.get_fdata() > 0).sum() * np.prod(nii.header.get_zooms())


def update_vols(f: Path, vols: dict[str, list], root: Path) -> None:
    vols["sub"].append(np.uint16(bu.get_sub(f)))
    vols["source"].append(str(f.relative_to(root)))
    vols["volume"].append(get_nii_volume(f))


def get_mask_volumes(root: Path) -> pl.DataFrame:
    vols = {"sub": [], "ses": [], "source": [], "volume": []}
    for f in (root / "synthstrip").rglob("*brain_mask.nii.gz"):
        update_vols(f, vols, root)
        vols["ses"].append(bu.get_ses(f))

    for f in (root / "cat12").rglob("*wmsub*.nii.gz"):
        update_vols(f, vols, root)
        vols["ses"].append(bu.get_ses(f))

    for f in (root / "fslanat").rglob("*T1_biascorr_brain_mask.nii.gz"):
        update_vols(f, vols, root)
        vols["ses"].append(bu.get_ses(f))

    for ses in ["V1", "V3"]:
        for f in (root / f"qsiprep-{ses}").rglob("*brain_mask.nii.gz"):
            update_vols(f, vols, root)
            vols["ses"].append(ses)

    return pl.DataFrame(vols)


def get_fslanat(root: Path) -> pl.DataFrame:
    return pl.read_csv(root / "fslanat.tsv", separator="\t")


def get_freesurfer(root: Path) -> pl.DataFrame:
    return pl.read_csv(root / "headers.tsv", separator="\t")


def get_gift(root: Path) -> pl.DataFrame:
    amplitude = (
        pl.scan_parquet(root / "amplitude")
        .filter(pl.col("model") == 2.1)
        .drop("model")
        .with_columns(
            component=("component_" + pl.col("component").cast(pl.Utf8) + "_falff")
        )
        .rename({"fALFF": "value", "component": "variable"})
    )
    connectivity = (
        pl.scan_parquet(root / "connectivity")
        .filter(pl.col("model") == 2.1)
        .with_columns(
            variable="source_"
            + pl.col("source").cast(pl.Utf8)
            + "_target_"
            + pl.col("target").cast(pl.Utf8)
            + "_connectivity",
        )
        .drop(["source", "target", "model"])
        .rename({"connectivity": "value"})
    )

    return (
        pl.concat([amplitude, connectivity], how="diagonal")
        .with_columns(
            pl.col("sub").cast(pl.UInt16),
            variable="task_"
            + pl.col("task")
            + "_run_"
            + pl.col("run").cast(pl.Utf8)
            + "_"
            + pl.col("variable"),
        )
        .drop("task", "run")
        .collect()
        .pivot(index=["sub", "ses"], on="variable")
    )


def make_toplevel(root: Path):
    fslanat = get_fslanat(root / "fslanat")
    freesurfer = get_freesurfer(root / "freesurfer")
    gift = get_gift(root / "postgift")

    dst_dir = root / "idp"
    bu.mkdir_recursive(dst_dir)
    fslanat.join(
        freesurfer, on=["sub", "ses"], how="full", validate="1:1", coalesce=True
    ).join(
        gift, on=["sub", "ses"], how="full", validate="1:1", coalesce=True
    ).write_csv(dst_dir / "mri.tsv", separator="\t")
    get_mask_volumes(root).write_csv(dst_dir / "mask_volumes.tsv", separator="\t")
