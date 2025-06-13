import shutil
from pathlib import Path

import utils
from biomarkers import utils as bu


def copy(inroot: Path, outdir: Path) -> None:
    bu.mkdir_recursive(outdir)

    for subsesd in (inroot / "gift").glob("*"):
        utils.mergetree_overwrite(
            subsesd / "gift",
            outdir,
            ignore=shutil.ignore_patterns(
                "*anat*", "gift_rank-*log", "dataset_description.json"
            ),
        )
    for f in outdir.rglob("*gz"):
        if "nii" not in f.name:
            f.rename(f.with_name(f.name.replace(".gz", ".nii.gz")))
