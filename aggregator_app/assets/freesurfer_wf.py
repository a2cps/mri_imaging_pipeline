import shutil
from pathlib import Path

import utils

FSOUTPUTS = ("orig.mgz", "orig_nu.mgz", "T1.mgz")


def main(outdir: Path, inroot: Path) -> None:
    if not outdir.exists():
        outdir.mkdir(parents=True)

    for src in inroot.glob("fmriprep/*/anat/freesurfer/sub*"):
        # folders renamed so that sessions do not collide
        shutil.copytree(
            src,
            outdir / f"sub-{utils._get_sub(src)}_ses-{utils._get_ses(src)}",
            copy_function=utils._copy_if_needed,
        )
