import logging
import re
import shutil
from pathlib import Path

import nibabel as nb
import numpy as np
from nilearn import masking

# TODO: deface fslanat


FSOUTPUTS = ("orig.mgz", "orig_nu.mgz", "T1.mgz")


def _get_entity(f: Path, pattern: str) -> str:
    possibility = re.findall(pattern, str(f))
    if not len(possibility):
        raise ValueError
    return possibility[0]


def _get_sub(f: Path) -> str:
    return _get_entity(f=f, pattern=r"\d{5}")


def _get_ses(f: Path) -> str:
    return _get_entity(f=f, pattern=r"V[13]")


def _copy_overwrite(src: str | Path, dst: str | Path) -> str:
    if (_dst := Path(dst)).exists():
        logging.warning(f"Overwritting old outputs at {_dst}")
        _dst.unlink()

    out = shutil.copy2(src, dst, follow_symlinks=False)
    return out


def mergetree_overwrite(src: Path, dst: Path) -> None:
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
        src=src, dst=dst, dirs_exist_ok=True, copy_function=_copy_overwrite
    )


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


def _deface_fslanat(subsesdir: Path, fmriprep_mask: Path) -> None:
    for anatdir in subsesdir.glob("*anat"):
        for t1 in ("T1.nii.gz", "T1_biascorr.nii.gz"):
            _deface(anatdir / t1, anatdir / "T1_biascorr_brain_mask.nii.gz")
        for mni in ("T1_to_MNI_nonlin.nii.gz", "T1_to_MNI_lin.nii.gz"):
            _deface(
                anatdir / mni,
                anatdir / "MNI152_T1_2mm_brain_mask_dil1.nii.gz",
            )
        for orig in ("T1_fullfov.nii.gz", "T1_orig.nii.gz"):
            _deface(
                anatdir / orig,
                fmriprep_mask,
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


def _deface_all_derivatives(subsesdir: Path, tmp_site: Path) -> bool:
    sub = _get_sub(subsesdir)
    ses = _get_ses(subsesdir)
    subses_fmriprep = tmp_site / "fmriprep" / subsesdir
    ok = True
    try:
        fmriprep_mask = (
            subses_fmriprep
            / "anat"
            / "fmriprep"
            / f"sub-{sub}"
            / f"ses-{ses}"
            / "anat"
            / f"sub-{sub}_ses-{ses}_desc-brain_mask.nii.gz"
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

        _deface_fslanat(
            tmp_site / "fslanat" / subsesdir, fmriprep_mask=fmriprep_mask
        )
    except Exception as e:
        logging.error(
            f"Encountered {e} while defacing {subsesdir} but attempting to continue."
        )
        ok = False

    return ok
