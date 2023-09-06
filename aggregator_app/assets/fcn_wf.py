from pathlib import Path

import utils


def copy(outdir: Path, inroot: Path) -> None:
    if not outdir.exists():
        outdir.mkdir(parents=True)

    for src in inroot.glob("fcn/*"):
        for out in [
            "connectivity",
            "connectivity-cleaned",
            "connectivity-confounds",
            "acompcor",
        ]:
            utils.mergetree_overwrite(src / out, outdir / out)
