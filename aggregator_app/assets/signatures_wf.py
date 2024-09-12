from pathlib import Path
import shutil

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
            "signature-bold",
        ]:
            to_ignore = utils.get_duplicated_parquet(src / out)
            utils.mergetree_overwrite(
                src / out,
                outdir / out,
                ignore=shutil.ignore_patterns(*to_ignore),
            )
