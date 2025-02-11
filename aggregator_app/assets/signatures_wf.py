from pathlib import Path

import utils


def copy(outdir: Path, inroot: Path) -> None:
    if not outdir.exists():
        outdir.mkdir(parents=True)

    for src in inroot.glob("signatures/*"):
        for subfolder in [
            "cleaned",
            "confounds",
            "signatures-by-part",
            "signatures-by-part-diff",
            "signatures-by-run",
            "signatures-by-run-diff",
            "signatures-by-tr",
            "signatures-by-tr-diff",
        ]:
            if (out := src / subfolder).exists():
                utils.mergetree_overwrite(out, outdir / subfolder)
