from pathlib import Path

import utils
from biomarkers import utils as bu


def copy(outdir: Path, inroot: Path) -> None:
    bu.mkdir_recursive(outdir)
    for src in (inroot / "bedpostx").glob("*/*"):
        if src.is_dir():
            utils.mergetree_overwrite(src, outdir)
