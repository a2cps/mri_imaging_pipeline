import argparse
import pathlib
import shutil
import json

SITE_LONG = {
    "NS": "NS_northshore",
    "UI": "UI_uic",
    "UC": "UC_uchicago",
    "UM": "UM_umichigan",
    "SH": "SH_spectrum_health",
    "WS": "WS_wayne_state",
}

BIDS_IGNORE = """
*.err\n
*.out\n
__pycache__*\n
"""

DESCRIPTION = {"BIDSVersion": "1.9.3", "Name": "A2CPS Phantom Dataset"}

README = "phantom dataset"


def main(
    outdir: pathlib.Path,
    inroot: pathlib.Path = pathlib.Path(
        "/corral-secure/projects/A2CPS/products/mris"
    ),
) -> None:
    if not outdir.exists():
        outdir.mkdir(parents=True, exist_ok=True)

    for site in SITE_LONG.values():
        for bids in inroot.glob(f"{site}/bids/*QC*"):
            for phantom_id in bids.glob("sub-*"):
                for ses in phantom_id.glob("ses*"):
                    target = outdir / phantom_id.name / ses.name
                    if (
                        not target.exists()
                        or ses.stat().st_mtime > target.stat().st_mtime
                    ):
                        print(
                            f"copying {phantom_id.absolute()} -> {target.absolute()}"
                        )
                        shutil.copytree(
                            ses.absolute(),
                            target.absolute(),
                            dirs_exist_ok=True,
                        )
                    else:
                        print(f"skipping {phantom_id.absolute()}")

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
