import argparse
import json
import logging
import os
from pathlib import Path

SITE_LONG = {
    "NS": "NS_northshore",
    "UI": "UI_uic",
    "UC": "UC_uchicago",
    "UM": "UM_umichigan",
    "SH": "SH_spectrum_health",
    "WS": "WS_wayne_state",
    "RU": "RU_rush",
}

BIDS_IGNORE = """
*.err\n
*.out\n
__pycache__*\n
"""

DESCRIPTION = {"BIDSVersion": "1.9.3", "Name": "A2CPS Phantom Dataset"}

README = "phantom dataset"


def _prep_staged_dir(outroot: Path) -> None:
    # delete broken symlinks (e.g., files created by previous run of heudiconv that no
    # longer exist)
    for target in os.walk(outroot):
        tar_dir = Path(target[0])
        for f in target[2]:
            if not (broken := tar_dir / f).exists():
                logging.warning(f"deleting broken symlink: {broken}")
                broken.unlink()

    # delete empty directories
    for target in os.walk(outroot, topdown=False):
        if len(target[1] + target[2]) == 0:
            logging.warning(f"deleting empty directory: {target[0]}")
            Path(target[0]).rmdir()


def main(
    outdir: Path,
    inroot: Path = Path("/corral-secure/projects/A2CPS/products/mris"),
) -> None:
    if not outdir.exists():
        outdir.mkdir(parents=True, exist_ok=True)
    else:
        _prep_staged_dir(outroot=outdir)

    for site in SITE_LONG.values():
        for bids in inroot.glob(f"{site}/bids/*QC*"):
            for phantom_id in bids.glob("sub-*"):
                target_sub_dir = outdir / phantom_id.name
                if not target_sub_dir.exists():
                    target_sub_dir.mkdir(parents=True)
                for ses in phantom_id.glob("ses*"):
                    target = target_sub_dir / ses.name
                    if not target.exists():
                        logging.warning(
                            f"linking {phantom_id.absolute()} -> {target.absolute()}"
                        )
                        target.absolute().symlink_to(
                            ses.absolute(), target_is_directory=True
                        )
                    else:
                        logging.warning(
                            f"skipping {target.absolute()} (already exists)"
                        )

    (outdir / "README").write_text(README)

    (outdir / "dataset_description.json").write_text(json.dumps(DESCRIPTION, indent=2))

    (outdir / ".bidsignore").write_text(BIDS_IGNORE)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("outdir", type=Path)
    parser.add_argument(
        "--inroot",
        type=Path,
        default=Path("/corral-secure/projects/A2CPS/products/mris"),
    )

    args = parser.parse_args()
    main(inroot=args.inroot, outdir=args.outdir)
