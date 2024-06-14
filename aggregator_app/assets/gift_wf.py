from pathlib import Path
import shutil

import utils
from biomarkers import utils as bu


def copy(inroot: Path, outdir: Path) -> None:
    bu.mkdir_recursive(outdir)

    for subsesd in (inroot / "gift_rest").glob("*"):
        utils.mergetree_overwrite(
            subsesd / "gift",
            outdir,
            ignore=shutil.ignore_patterns(
                "*anat*", "gift_rank-*log", "dataset_description.json"
            ),
        )
