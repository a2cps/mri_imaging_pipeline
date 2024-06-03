import logging
import shutil
from pathlib import Path

import nibabel as nb
import numpy as np
from nilearn import masking

from biomarkers import utils as bu


FSOUTPUTS = ("orig.mgz", "orig_nu.mgz", "T1.mgz")


def _copy_overwrite(src: str | Path, dst: str | Path) -> str:
    if (_dst := Path(dst)).exists():
        logging.warning(f"Overwritting old outputs at {_dst}")
        _dst.unlink()

    out = shutil.copy2(src, dst, follow_symlinks=False)
    return out


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
        logging.info(
            f"File {src} would overwrite {dst}. Leaving files unchanged."
        )
    else:
        Path(dst).symlink_to(Path(src).resolve())
    return dst


def _deface(volume: Path, mask: Path, make_mask: bool = False) -> bool:  # type: ignore  # noqa: FBT002, FBT001
    ok = True
    try:
        if make_mask:
            _mask = nb.load(mask)  # type: ignore
            mask_data = np.asarray(_mask.get_fdata() > 0, dtype=np.uint8)
            mask: nb.Nifti1Image = nb.Nifti1Image(mask_data, affine=_mask.affine)  # type: ignore

        masked_data = masking.apply_mask(volume, mask)
        masked: nb.Nifti1Image = masking.unmask(masked_data, mask)  # type: ignore
        volume.unlink()
        nb.save(masked, volume)  # type: ignore
    except Exception as e:
        logging.error(
            f"""
            Exception while defacing {volume} with {mask} but attempting to continue.
            {e}"""
        )
        ok = False
    return ok


def _deface_fslanat(subsesdir: Path, fmriprep_mask: Path) -> bool:
    ok = True
    for anatdir in subsesdir.glob("*anat"):
        for t1 in ("T1.nii.gz", "T1_biascorr.nii.gz"):
            if (f := anatdir / t1).exists():
                ok &= _deface(f, anatdir / "T1_biascorr_brain_mask.nii.gz")
        for mni in ("T1_to_MNI_nonlin.nii.gz", "T1_to_MNI_lin.nii.gz"):
            if (f := anatdir / mni).exists():
                ok &= _deface(
                    f, anatdir / "MNI152_T1_2mm_brain_mask_dil1.nii.gz"
                )
        for orig in ("T1_fullfov.nii.gz", "T1_orig.nii.gz"):
            if (f := anatdir / orig).exists():
                ok &= _deface(f, fmriprep_mask)
    return ok


def _deface_qsiprep(subsesdir: Path, sub: str) -> bool:
    ok = True
    for t1w in (subsesdir / f"sub-{sub}" / "anat").glob("*T1w.nii.gz"):
        ok &= _deface(
            t1w,
            t1w.with_name(
                t1w.name.replace("desc-preproc_T1w", "desc-brain_mask")
            ),
        )
    return ok


def _deface_freesurfer(subdir: Path, fmriprep_mask: Path) -> bool:
    ok = True
    for orig in (subdir / "mri" / "orig").glob("*mgz"):
        ok &= _deface(orig, fmriprep_mask)

    if (rawavg := subdir / "mri" / "rawavg.mgz").exists():
        ok &= _deface(rawavg, fmriprep_mask)

    for mgz in FSOUTPUTS:
        if (f := subdir / "mri" / mgz).exists():
            ok &= _deface(f, subdir / "mri" / "brainmask.mgz", make_mask=True)
    return ok


def _deface_fmriprep(
    subsesdir: Path, fmriprep_mask: Path, sub: str, ses: str
) -> bool:
    ok = True
    for subjob in ["anat", "cuff", "rest"]:
        for output in (subsesdir / subjob / "fmriprep" / f"sub-{sub}").glob(
            "ses*"
        ):
            ok &= _deface(
                output
                / "anat"
                / f"sub-{sub}_ses-{ses}_desc-preproc_T1w.nii.gz",
                fmriprep_mask,
            )
            for space in ["MNI152NLin2009cAsym"]:
                ok &= _deface(
                    output
                    / "anat"
                    / f"sub-{sub}_ses-{ses}_space-{space}_desc-preproc_T1w.nii.gz",
                    output
                    / "anat"
                    / f"sub-{sub}_ses-{ses}_space-{space}_desc-brain_mask.nii.gz",
                )
    return ok


def _deface_all_derivatives(subsesdir: Path, tmp_site: Path) -> bool:
    ok = True

    # NOTE: cannot assume that all standard files exist for all participants
    sub = bu.get_sub_from_sublong(subsesdir)
    ses = bu.get_ses_from_sublong(subsesdir)
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
    ok &= _deface_fmriprep(
        subsesdir=subses_fmriprep,
        fmriprep_mask=fmriprep_mask,
        sub=sub,
        ses=ses,
    )
    ok &= _deface_qsiprep(
        subsesdir=tmp_site / "qsiprep" / subsesdir / "qsiprep", sub=sub
    )

    ok &= _deface_freesurfer(
        subdir=subses_fmriprep / "anat" / "freesurfer" / f"sub-{sub}",
        fmriprep_mask=fmriprep_mask,
    )

    ok &= _deface_fslanat(
        tmp_site / "fslanat" / subsesdir, fmriprep_mask=fmriprep_mask
    )

    return ok
