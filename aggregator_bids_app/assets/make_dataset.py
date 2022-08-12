import argparse
import json
import os
import pathlib
import re
from typing import List

SITE_LONG = {
    "NS": "NS_northshore",
    "UI": "UI_uic",
    "UC": "UC_uchicago",
    "UM": "UM_umichigan",
    "SH": "SH_spectrum_health",
    "WS": "WS_wayne_state",
}

BIDS_IGNORE = """
*.err
*.out
__pycache__*
sub-*/ses-*/fmap/*.bval
sub-*/ses-*/fmap/*.bvec
"""

DESCRIPTION = {
    "Acknowledgements": "TODO: more",
    "Authors": ["TODO:"],
    "BIDSVersion": "1.4.1",
    "DatasetDOI": "TODO: eventually a DOI for the dataset",
    "Funding": ["TODO"],
    "HowToAcknowledge": "TODO: describe how to acknowledge -- either cite a corresponding paper, or just in acknowledgement section",
    "License": "TODO: choose a license, e.g. PDDL (http://opendatacommons.org/licenses/pddl/)",
    "Name": "TODO: name of the dataset",
    "ReferencesAndLinks": ["TODO"],
}

README = "symlink dataset"


def get_valid(inroot=pathlib.Path) -> List[pathlib.Path]:
    passed = []
    for site in SITE_LONG.values():
        # append only if the *out file is present in the folder
        passed += [
            d
            for d in inroot.glob(f"{site}/bids_validation/*")
            if (not "QC" in d.name) and (len([x for x in d.glob("*out")]) > 0)
        ]

    return passed


def main(
    outdir: pathlib.Path,
    inroot: pathlib.Path = pathlib.Path("/corral-secure/projects/A2CPS/products/mris"),
) -> None:

    if not outdir.exists():
        outdir.mkdir(parents=True)

    for d in get_valid(inroot=inroot):
        bids = pathlib.Path(re.sub(r"_validation", "", str(d.absolute())))
        for src_id in bids.glob("sub-*"):
            # bids validator is confused by symlinked folders, so need to create real folders and
            # symlink to individual files
            for src in os.walk(src_id):
                src_dir = pathlib.Path(src[0]).relative_to(src_id.parent)
                target_dir = outdir / src_dir
                target_dir.mkdir(exist_ok=True)
                print(f"linking contents of {src_id.parent / src_dir} -> {target_dir}")
                for f in src[2]:
                    if not (target := target_dir / f).exists():
                        target.symlink_to(src_id.parent / src_dir / f)

    # delete broken symlinks (e.g., files created by previous run of heudiconv that no longer exist)
    for target in os.walk(outdir):
        tar_dir = pathlib.Path(target[0])
        for f in target[2]:
            if not (broken := tar_dir / f).exists():
                print(f"deleting broken symlink: {broken}")
                broken.unlink()

    # delete empty directories
    for target in os.walk(outdir, topdown=False):
        if len(target[1] + target[2]) == 0:
            to_del = pathlib.Path(target[0])
            print(f"deleting empty directory: {to_del}")
            os.removedirs(to_del)

    readme = outdir / "README"
    readme.touch()
    readme.write_text(README)

    description = outdir / "dataset_description.json"
    description.write_text(json.dumps(DESCRIPTION, indent=2))

    bids_ignore = outdir / ".bidsignore"
    bids_ignore.write_text(BIDS_IGNORE)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("outdir", type=pathlib.Path)
    parser.add_argument(
        "--inroot",
        type=pathlib.Path,
        default=pathlib.Path("/corral-secure/projects/A2CPS/products/mris"),
    )

    args = parser.parse_args()
    main(inroot=args.inroot, outdir=args.outdir)
