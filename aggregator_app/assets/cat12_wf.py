import shutil
from pathlib import Path

import utils


def main(outdir: Path, inroot: Path) -> None:
    if not outdir.exists():
        outdir.mkdir(parents=True)

    for src in inroot.glob("cat12/*"):
        for out in ["label", "mri", "report", "surf"]:
            shutil.copytree(
                src / out,
                outdir / out,
                dirs_exist_ok=True,
                copy_function=utils._copy_if_needed,
            )
