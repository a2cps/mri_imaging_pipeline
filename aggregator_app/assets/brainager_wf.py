from pathlib import Path
import shutil

import utils


def copy(outdir: Path, inroot: Path) -> None:
    if not outdir.exists():
        outdir.mkdir(parents=True)

    for src in inroot.glob("brainager/*"):
        sub = utils._get_sub(src)
        ses = utils._get_ses(src)

        out_subses = outdir / f"sub-{sub}" / f"ses-{ses}"
        if not out_subses.exists():
            out_subses.mkdir(parents=True)

        utils.mergetree_overwrite(
            src,
            out_subses,
            ignore=shutil.ignore_patterns("*remove.nii.gz", "sub*nii"),
        )
