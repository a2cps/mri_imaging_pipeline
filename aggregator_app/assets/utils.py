import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import nibabel as nb
import numpy as np
from biomarkers import utils as bu
from nilearn import masking

FSOUTPUTS = ("orig.mgz", "orig_nu.mgz", "T1.mgz")
SYNTHSTRIP_MODEL = Path("/opt/synthstrip.1.pt")


def synthstrip(src: Path, n_threads: int = 1) -> Path:
    with tempfile.NamedTemporaryFile(suffix=".nii.gz") as brain:
        proc = subprocess.run(
            [
                "synthstrip",
                "-i",
                src,
                "-o",
                brain.name,
                "-n",
                str(n_threads),
                "--model",
                SYNTHSTRIP_MODEL,
            ]
        )
        if proc.returncode > 0:
            msg = f"Failed to synthstrip {src}"
            raise RuntimeError(msg)
        src.unlink()
        shutil.copy2(brain.name, src)
        os.chmod(src, 0o640)
    return src


def _copy_overwrite(src: str | Path, dst: str | Path) -> str:
    out = Path(dst)
    if not out.exists():
        shutil.copy2(src, dst, follow_symlinks=False)
    elif not out.samefile(src):
        logging.warning(f"Overwritting {dst}")
        out.unlink()
        shutil.copy2(src, dst, follow_symlinks=False)
    return str(out)


def mergetree_overwrite(src: Path, dst: Path, ignore=None) -> None:
    """Merge src directory tree with dst directory tree, overwritting files in dst

    Args:
        src: Source from which files will be copied
        dst: Location files will be copied to

    Details:
        copytree will fail if destination contains files that are symlinks;
        the copy_function is only used to copy regular files, and for symlinks
        os.symlink(src, dst) is used, which fails when dst exists.
        This is not configurable with copytree, and so here copytree
        is called only after dst is removed
        this is done within the copy function (rather than removing the
        entire dst tree) because we may be merging src with files in dst
        that should be kept
    """

    shutil.copytree(
        src=src,
        dst=dst,
        dirs_exist_ok=True,
        copy_function=_copy_overwrite,
        ignore=ignore,
    )


def _symlink_if_needed(src, dst, *args, **kwargs) -> Path:  # noqa: ARG001
    if Path(dst).exists():
        logging.info(f"File {src} would overwrite {dst}. Leaving files unchanged.")
    else:
        Path(dst).symlink_to(Path(src).resolve())
    return dst


def _deface(volume: Path, mask: Path, make_mask: bool = False):  # noqa: FBT002, FBT001
    if make_mask:
        _mask = nb.nifti1.load(mask)
        mask_data = np.asarray(_mask.get_fdata() > 0, dtype=np.uint8)
        mask_to_use = nb.nifti1.Nifti1Image(mask_data, affine=_mask.affine)
    else:
        mask_to_use = mask

    masked_data = masking.apply_mask(volume, mask_to_use)
    masked: nb.Nifti1Image = masking.unmask(masked_data, mask_to_use)  # type: ignore
    volume.unlink()
    nb.loadsave.save(masked, volume)


def _deface_fslanat(subsesdir: Path, n_threads: int = 1):
    for anatdir in subsesdir.glob("*anat"):
        for t1 in ("T1.nii.gz", "T1_biascorr.nii.gz"):
            if (f := anatdir / t1).exists():
                _deface(f, anatdir / "T1_biascorr_brain_mask.nii.gz")
        for mni in ("T1_to_MNI_nonlin.nii.gz", "T1_to_MNI_lin.nii.gz"):
            if (f := anatdir / mni).exists():
                _deface(f, anatdir / "MNI152_T1_2mm_brain_mask_dil1.nii.gz")
        for orig in ("T1_fullfov.nii.gz", "T1_orig.nii.gz"):
            if (f := anatdir / orig).exists():
                synthstrip(f, n_threads=n_threads)


def _deface_qsiprep(subsesdir: Path, sub: str):
    for t1w in (subsesdir / f"sub-{sub}" / "anat").glob("*T1w.nii.gz"):
        _deface(
            t1w,
            t1w.with_name(t1w.name.replace("preproc_T1w", "brain_mask")),
        )


def _deface_freesurfer(subdir: Path, fmriprep_mask: Path):
    for orig in (subdir / "mri" / "orig").glob("*mgz"):
        _deface(orig, fmriprep_mask)

    if (rawavg := subdir / "mri" / "rawavg.mgz").exists():
        _deface(rawavg, fmriprep_mask)

    for mgz in FSOUTPUTS:
        if (f := subdir / "mri" / mgz).exists():
            _deface(f, subdir / "mri" / "brainmask.mgz", make_mask=True)


def _deface_fmriprep(
    subsesdir: Path,
    synthstrip_mask: Path,
    sub: str,
    ses: str,
):
    for output in (subsesdir / "fmriprep" / f"sub-{sub}").glob("ses*"):
        _deface(
            output / "anat" / f"sub-{sub}_ses-{ses}_desc-preproc_T1w.nii.gz",
            synthstrip_mask,
        )
        for t1 in (output / "anat").glob("*space*desc-preproc_T1w.nii.gz"):
            _deface(t1, t1.parent / t1.name.replace("preproc_T1w", "brain_mask"))


def deface_all_derivatives(subsesdir: Path, tmp_site: Path, n_threads: int = 1):
    # NOTE: cannot assume that all standard files exist for all participants
    sub = bu.get_sub_from_sublong(subsesdir)
    ses = bu.get_ses_from_sublong(subsesdir)
    subses_fmriprep = tmp_site / "fmriprep" / subsesdir
    fmriprep_mask = (
        subses_fmriprep
        / "synthstrip"
        / f"sub-{sub}"
        / f"ses-{ses}"
        / "anat"
        / f"sub-{sub}_ses-{ses}_desc-brain_mask.nii.gz"
    )
    _deface_fmriprep(
        subsesdir=subses_fmriprep, synthstrip_mask=fmriprep_mask, sub=sub, ses=ses
    )
    _deface_qsiprep(subsesdir=tmp_site / "qsiprep" / subsesdir / "qsiprep", sub=sub)

    _deface_freesurfer(
        subdir=subses_fmriprep / "sourcedata" / "freesurfer" / f"sub-{sub}",
        fmriprep_mask=fmriprep_mask,
    )

    _deface_fslanat(tmp_site / "fslanat" / subsesdir, n_threads=n_threads)
