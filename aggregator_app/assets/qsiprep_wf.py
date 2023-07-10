import shutil
from pathlib import Path

import utils


def main(outdir: Path, inroot: Path) -> None:
    if not outdir.exists():
        outdir.mkdir(parents=True)

    for src in inroot.glob("qsiprep/*/qsiprep/sub*"):
        if src.is_file():
            sub = utils._get_sub(src)
            ses = utils._get_ses(src)
            # assumes that the src is a file like sub-#####.html
            # and that there's only one
            utils._copy_if_needed(
                src,
                outdir / f"sub-{sub}_ses-{ses}.html",
            )
            utils._copy_if_needed(
                src.with_name("dwiqc.json"),
                outdir / f"sub-{sub}_ses-{ses}.json",
            )
        else:
            shutil.copytree(
                src,
                outdir / src.name,
                dirs_exist_ok=True,
                copy_function=utils._copy_if_needed,
            )
