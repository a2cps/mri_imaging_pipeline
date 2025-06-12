import logging
import shutil
from pathlib import Path

import nibabel as nb
import numpy as np
from nilearn import maskers


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


def symlink_if_needed(src, dst, *args, **kwargs) -> Path:  # noqa: ARG001
    if Path(dst).exists():
        logging.info(f"File {src} would overwrite {dst}. Leaving files unchanged.")
    else:
        Path(dst).symlink_to(Path(src).resolve())
    return dst


def get_volume(nif: Path, masker: maskers.NiftiLabelsMasker) -> np.ndarray:
    nii: nb.nifti1.Nifti1Image = nb.nifti1.Nifti1Image.load(nif)
    if not len(nii.shape) == 3:
        raise AssertionError("Expected 3d image")
    n_voxels = masker.fit_transform(nii).squeeze()
    return np.astype(n_voxels * np.prod(nii.header.get_zooms()), np.float64)
