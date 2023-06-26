import json
import shutil
from pathlib import Path

import utils

BIDS_IGNORE = """
sub-*/ses-*/fmap/*.bval
sub-*/ses-*/fmap/*.bvec
"""

DESCRIPTION = {"BIDSVersion": "1.8.0", "Name": "A2CPS"}

README = "A2CPS dataset"


def main(outdir: Path, inroot: Path) -> None:
    if not outdir.exists():
        outdir.mkdir(parents=True)

    # copy files over
    for bids in inroot.glob("bids/*"):
        for src_id in bids.glob("sub-*"):
            shutil.copytree(
                src_id,
                outdir / src_id.name,
                dirs_exist_ok=True,
                copy_function=utils._copy_if_needed,
            )

    # create top-level files
    readme = outdir / "README"
    readme.touch()
    readme.write_text(README)

    description = outdir / "dataset_description.json"
    description.write_text(json.dumps(DESCRIPTION, indent=2))

    bids_ignore = outdir / ".bidsignore"
    bids_ignore.write_text(BIDS_IGNORE)
