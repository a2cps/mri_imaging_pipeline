from pathlib import Path

import utils
from biomarkers import utils as bu


def copy(inroot: Path, outdir: Path) -> None:
    bu.mkdir_recursive(outdir)

    for subsesd in (inroot / "postgift").glob("*"):
        for subdir in ["amplitude", "biomarkers", "connectivity"]:
            utils.mergetree_overwrite(subsesd / subdir, outdir / subdir)
