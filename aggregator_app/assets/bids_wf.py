import json
from pathlib import Path

import utils

BIDS_IGNORE = """
sub-*/ses-*/fmap/*.bval
sub-*/ses-*/fmap/*.bvec
"""

DESCRIPTION = {"BIDSVersion": "1.8.0", "Name": "A2CPS"}

README = "A2CPS dataset"


def copy(outdir: Path, inroot: Path) -> None:
    if not outdir.exists():
        outdir.mkdir(parents=True)

    # copy files over
    for bids in inroot.glob("bids/*"):
        for src_id in bids.glob("sub-*"):
            utils.mergetree_overwrite(src_id, outdir / src_id.name)


def make_toplevel(outdir: Path) -> None:
    # create top-level files
    readme = outdir / "README"
    readme.touch()
    readme.write_text(README)

    description = outdir / "dataset_description.json"
    description.write_text(json.dumps(DESCRIPTION, indent=2))

    bids_ignore = outdir / ".bidsignore"
    bids_ignore.write_text(BIDS_IGNORE)
