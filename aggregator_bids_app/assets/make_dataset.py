import argparse
import pathlib
import re
import json
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
            target_sub = outdir / src_id.name
            if not target_sub.exists():
                target_sub.mkdir()
            for src_ses in src_id.glob("ses-*"):
                if (target := target_sub / src_ses.name).exists():
                    print(f"skipping {src_ses.absolute()}")
                else:
                    print(f"copying {src_ses.absolute()} -> {target.absolute()}")
                    target.symlink_to(src_ses, target_is_directory=True)

    readme = outdir / "README"
    readme.touch()
    readme.write_text(README)

    description = outdir / "dataset_description.json"
    description.write_text(json.dumps(DESCRIPTION, indent=2))

    bids_ignore = outdir / ".bidsignore"
    bids_ignore.write_text(BIDS_IGNORE)

    # delete broken symlinks (e.g., files created by previous run of heudiconv that no longer exist)
    for target_sub in outdir.glob("sub-*"):
        for target_ses in target_sub.glob("ses-*"):
            if not target_ses.exists():
                print(f"deleting broken {target_ses.absolute()}")
                target_ses.unlink()
        if not [x for x in target_sub.glob("*")]:
            print(f"deleting empty {target_sub.absolute()}")
            target_sub.unlink()


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
