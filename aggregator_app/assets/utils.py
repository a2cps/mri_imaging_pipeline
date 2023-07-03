import logging
import re
import shutil
from pathlib import Path

import nibabel as nb
import numpy as np
from nilearn import masking

# TODO: deface fslanat


FSOUTPUTS = ("orig.mgz", "orig_nu.mgz", "T1.mgz")
FSLANATOUTPUTS = (
    "T1.nii.gz",
    "T1_fullfov.nii.gz",
    "T1_orig.niig.z",
    "T1_biascorr.nii.gz",
    "T1_to_MNI_lin.nii.gz",
    "T1_to_MNI_nonlin.nii.gz",
)


def _get_entity(f: Path, pattern: str) -> str:
    possibility = re.findall(pattern, str(f))
    if not len(possibility):
        raise ValueError
    return possibility[0]


def _get_sub(f: Path) -> str:
    return _get_entity(f=f, pattern=r"\d{5}")


def _get_ses(f: Path) -> str:
    return _get_entity(f=f, pattern=r"V[13]")


def _copy_if_needed(src, dst, *args, **kwargs) -> Path:  # noqa: ARG001
    if Path(dst).exists():
        logging.info(
            f"File {src} would overwrite {dst}. Leaving files unchanged."
        )
    elif (src2 := Path(src)).is_symlink():
        Path(dst).symlink_to(Path(src2).resolve())
    else:
        # otherwise, copy the file
        shutil.copy2(src, dst)
    return dst


def _symlink_if_needed(src, dst, *args, **kwargs) -> Path:  # noqa: ARG001
    if Path(dst).exists():
        logging.info(
            f"File {src} would overwrite {dst}. Leaving files unchanged."
        )
    else:
        Path(dst).symlink_to(Path(src).resolve())
    return dst


def _deface(volume: Path, mask: Path, make_mask: bool = False) -> None:  # type: ignore  # noqa: FBT002, FBT001
    if make_mask:
        _mask = nb.load(mask)  # type: ignore
        mask_data = np.asarray(_mask.get_fdata() > 0, dtype=np.uint8)
        mask: nb.Nifti1Image = nb.Nifti1Image(mask_data, affine=_mask.affine)  # type: ignore

    masked_data = masking.apply_mask(volume, mask)
    masked: nb.Nifti1Image = masking.unmask(masked_data, mask)  # type: ignore
    volume.unlink()
    nb.save(masked, volume)  # type: ignore


def _deface_fslanat(subsesdir: Path) -> None:
    for anatdir in subsesdir.glob("*anat"):
        for t1 in FSLANATOUTPUTS:
            _deface(anatdir / t1, subsesdir / "T1_biascorr_brain_mask.nii.gz")
        _deface(
            anatdir / "T1_to_MNI_nonlin.nii.gz",
            anatdir / "MNI152_T1_2mm_brain_mask_dil1.nii.gz",
        )
        _deface(
            anatdir / "T1_to_MNI_lin.nii.gz",
            anatdir / "MNI152_T1_2mm_brain_mask_dil1.nii.gz",
        )


def _deface_qsiprep(subsesdir: Path, sub: str) -> None:
    _deface(
        subsesdir
        / "qsiprep"
        / f"sub-{sub}"
        / "anat"
        / f"sub-{sub}_desc-preproc_T1w.nii.gz",
        subsesdir
        / "qsiprep"
        / f"sub-{sub}"
        / "anat"
        / f"sub-{sub}_desc-brain_mask.nii.gz",
    )
    _deface(
        subsesdir
        / "qsiprep"
        / f"sub-{sub}"
        / "anat"
        / f"sub-{sub}_space-MNI152NLin2009cAsym_desc-preproc_T1w.nii.gz",
        subsesdir
        / "qsiprep"
        / f"sub-{sub}"
        / "anat"
        / f"sub-{sub}_space-MNI152NLin2009cAsym_desc-brain_mask.nii.gz",
    )


def _deface_all(subsesdir: Path, tmp_site: Path) -> None:
    sub = _get_sub(subsesdir)
    ses = _get_ses(subsesdir)
    subses_fmriprep = tmp_site / "fmriprep" / subsesdir
    fmriprep_mask = (
        subses_fmriprep
        / "anat"
        / "fmriprep"
        / f"sub-{sub}"
        / f"ses-{ses}"
        / "anat"
        / f"sub-{sub}_ses-{ses}_desc-brain_mask.nii.gz"
    )
    _deface(
        tmp_site
        / "bids"
        / subsesdir
        / f"sub-{sub}"
        / f"ses-{ses}"
        / "anat"
        / f"sub-{sub}_ses-{ses}_T1w.nii.gz",
        fmriprep_mask,
    )
    for subjob in ["anat", "cuff", "rest"]:
        # output might not exist
        for output in (
            subses_fmriprep / subjob / "fmriprep" / f"sub-{sub}"
        ).glob("ses*"):
            _deface(
                output
                / "anat"
                / f"sub-{sub}_ses-{ses}_desc-preproc_T1w.nii.gz",
                fmriprep_mask,
            )

            _deface(
                output
                / "anat"
                / f"sub-{sub}_ses-{ses}_space-MNI152NLin2009cAsym_desc-preproc_T1w.nii.gz",
                output
                / "anat"
                / f"sub-{sub}_ses-{ses}_space-MNI152NLin2009cAsym_desc-brain_mask.nii.gz",
            )
    # now freesurfer
    _deface(
        subses_fmriprep
        / "anat"
        / "freesurfer"
        / f"sub-{sub}"
        / "mri"
        / "orig"
        / "001.mgz",
        fmriprep_mask,
    )
    _deface(
        subses_fmriprep
        / "anat"
        / "freesurfer"
        / f"sub-{sub}"
        / "mri"
        / "rawavg.mgz",
        fmriprep_mask,
    )
    for mgz in FSOUTPUTS:
        _deface(
            subses_fmriprep
            / "anat"
            / "freesurfer"
            / f"sub-{sub}"
            / "mri"
            / mgz,
            subses_fmriprep
            / "anat"
            / "freesurfer"
            / f"sub-{sub}"
            / "mri"
            / "brainmask.mgz",
            make_mask=True,
        )

    _deface_qsiprep(tmp_site / "qsiprep" / subsesdir, sub=sub)
    _deface_fslanat(tmp_site / "fslanat" / subsesdir)
