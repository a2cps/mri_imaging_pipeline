import argparse
import pathlib
import re
import shutil
import json

SITE_LONG = {
    "NS": "NS_northshore",
    "UI": "UI_uic",
    "UC": "UC_uchicago",
    "UM": "UM_umichigan",
    "SH": "SH_spectrum_health",
    "WS": "WS_wayne_state"
}

BIDS_IGNORE = """
*.err\n
*.out\n
__pycache__*\n
"""

DESCRIPTION = {
    "Acknowledgements": "TODO: more",
    "Authors": [
        "TODO:"
    ],
    "BIDSVersion": "1.9.3",
    "DatasetDOI": "TODO: eventually a DOI for the dataset",
    "Funding": [
        "TODO"
    ],
    "HowToAcknowledge": "TODO: describe how to acknowledge -- either cite a corresponding paper, or just in acknowledgement section",
    "License": "TODO: choose a license, e.g. PDDL (http://opendatacommons.org/licenses/pddl/)",
    "Name": "TODO: name of the dataset",
    "ReferencesAndLinks": [
        "TODO"
    ]
}

README = "phantom dataset"


def get_valid(inroot = pathlib.Path) -> list[pathlib.Path]:
    passed = []
    for site in SITE_LONG.values():
        # append only if the *out file is present in the folder
        passed += [ d for d in inroot.glob(f"{site}/bids_validation/*QC*") if len([x for x in d.glob('*out')]) > 0 ]

    return passed


def main(
    outdir: pathlib.Path, 
    inroot: pathlib.Path = pathlib.Path("/corral-secure/projects/A2CPS/products/mris")
    ) -> None:

    if not outdir.exists():
        outdir.mkdir(parents=True, exist_ok=True)

    for d in get_valid(inroot=inroot):
        bids = pathlib.Path(re.sub(r"_validation", "", str(d.absolute())))
        for phantom_id in bids.glob("sub-*"):
            for ses in phantom_id.glob("ses*"):
                target = outdir / phantom_id.name / ses.name
                if not target.exists() or ses.stat().st_mtime > target.stat().st_mtime:
                    print(f"copying {phantom_id.absolute()} -> {target.absolute()}")
                    shutil.copytree(ses.absolute(), target.absolute(), dirs_exist_ok=True)
                else:
                    print(f"skipping {phantom_id.absolute()}")

    readme = outdir / "README"
    readme.touch()
    readme.write_text(README)

    description = outdir / "dataset_description.json"
    description.write_text(json.dumps(DESCRIPTION, indent=2))

    bids_ignore = outdir / ".bidsignore"
    bids_ignore.write_text(BIDS_IGNORE)


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('outdir', type=pathlib.Path)
    parser.add_argument(
        '--inroot', 
        type=pathlib.Path, 
        default=pathlib.Path("/corral-secure/projects/A2CPS/products/mris"))

    args = parser.parse_args()
    main(
        inroot=args.inroot,
        outdir=args.outdir
    )


