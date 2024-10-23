import shutil
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
            to_ignore = utils.get_duplicated_parquet(src / out)
            utils.mergetree_overwrite(
                src / out,
                outdir / out,
                ignore=shutil.ignore_patterns(*to_ignore),
            )
