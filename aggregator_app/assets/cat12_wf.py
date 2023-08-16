from pathlib import Path

import utils


def main(outdir: Path, inroot: Path) -> None:
    if not outdir.exists():
        outdir.mkdir(parents=True)

    for src in inroot.glob("cat12/*"):
        for out in ["label", "mri", "report", "surf"]:
            utils.mergetree_overwrite(src / out, outdir / out)
