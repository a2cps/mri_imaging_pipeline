from pathlib import Path

import utils


def copy(outdir: Path, inroot: Path) -> None:
    if not outdir.exists():
        outdir.mkdir(parents=True)

    for src in inroot.glob("signatures/*"):
        for out in [
            "cleaned",
            "confounds",
            "signatures-by-part",
            "signatures-by-part-diff",
            "signatures-by-run",
            "signatures-by-run-diff",
            "signatures-by-tr",
            "signatures-by-tr-diff",
        ]:
            utils.mergetree_overwrite(src / out, outdir / out)
