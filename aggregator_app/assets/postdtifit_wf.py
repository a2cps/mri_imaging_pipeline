from pathlib import Path

import utils
from biomarkers import utils as bu

RENAME_MAPPINGS = {
    "dtifit_regional": "diffusion_regional",
    "dtifit_regional_stats": "diffusion_regional_stats",
}


def copy(inroot: Path, outdir: Path) -> None:
    bu.mkdir_recursive(outdir)

    for subsesd in (inroot / "postdtifit").glob("*"):
        for old, new in RENAME_MAPPINGS.items():
            utils.mergetree_overwrite(subsesd / old, outdir / new)
