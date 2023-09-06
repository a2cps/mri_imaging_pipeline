from pathlib import Path

import utils


def copy(outdir: Path, inroot: Path) -> None:
    if not outdir.exists():
        outdir.mkdir(parents=True)

    for src in inroot.glob("signatures/*"):
        for out in [
            "signature-by-part",
            "signature-by-run",
            "signature-by-tr",
            "signature-labels",
            "signature-cleaned",
            "signature-confounds",
            "signature-rawdata",
        ]:
            utils.mergetree_overwrite(src / out, outdir / out)
