from pathlib import Path

import utils
from biomarkers import utils as bu


def copy(outdir: Path, inroot: Path) -> None:
    for product in ["qsirecon-fsl", "split_shells", "dtifit"]:
        bu.mkdir_recursive(outdir / product)
        for src in inroot.glob(f"{product}/*"):
            if src.is_dir():
                utils.mergetree_overwrite(src, outdir / product)
