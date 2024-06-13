from pathlib import Path
import shutil

import utils
from biomarkers import utils as bu


def copy(inroot: Path, outdir: Path) -> None:
    bu.mkdir_recursive(outdir)

    utils.mergetree_overwrite(
        inroot / "gift_rest",
        outdir,
        ignore=shutil.ignore_patterns(
            "*anat*", "gift_rank-*log", "dataset_description.json"
        ),
    )
