import argparse
import json
import logging
import pathlib
import re
import shutil
import typing

import nibabel as nb
import pandas as pd
from nibabel import orientations

DIR: typing.TypeAlias = typing.Literal["RL", "LR", "AP", "PA", "IS", "SI"]
PED: typing.TypeAlias = typing.Literal["i", "i-", "j", "j-", "k", "k-"]
RAS_DIR_PED: dict[DIR, PED] = {
    k: v for k, v in zip(typing.get_args(DIR), typing.get_args(PED))
}
RAS_PED_DIR: dict[PED, DIR] = {v: k for k, v in RAS_DIR_PED.items()}


def get_expected_dir(ped: PED, nii: nb.nifti1.Nifti1Image) -> DIR:
    axcodes = orientations.aff2axcodes(nii.affine)
    expected = None
    pos: dict[str, DIR] = {
        "R": "LR",
        "L": "RL",
        "A": "PA",
        "P": "AP",
        "S": "IS",
        "I": "SI",
    }
    neg: dict[str, DIR] = {
        "R": "RL",
        "L": "LR",
        "A": "AP",
        "P": "PA",
        "S": "IS",
        "I": "SI",
    }
    match ped:
        case "i":
            expected = pos.get(axcodes[0])
        case "i-":
            expected = neg.get(axcodes[0])
        case "j":
            expected = pos.get(axcodes[1])
        case "j-":
            expected = neg.get(axcodes[1])
        case "k":
            expected = pos.get(axcodes[2])
        case "k-":
            expected = neg.get(axcodes[2])

    if not expected:
        msg = f"Unsure how to handle {ped=}"
        raise RuntimeError(msg)

    return expected


def main(bids_path: pathlib.Path) -> None:
    for f in bids_path.glob("**/fmap/*dir-*.json"):
        print(f"Checking for dir/PED match in: {f.name}")
        n = f.with_suffix(".nii.gz")
        nii = nb.nifti1.load(n)
        if not isinstance(nii, nb.nifti1.Nifti1Image):
            msg = f"unexpected nifti {type(nii)=}"
            raise RuntimeError(msg)

        sidecar: dict[str, typing.Any] = json.loads(f.read_text())
        ped: PED | None = sidecar.get("PhaseEncodingDirection")
        if (not ped) or (ped not in typing.get_args(PED)):
            msg = f"Could not find PhaseEncodingDirection in {f}."
            raise RuntimeError(msg)

        existing_dirs = re.findall(r"(?<=dir-)\w{2}", f.name)
        if len(existing_dirs) != 1:
            msg = f"Unexpected count of dir in {f}?"
            raise RuntimeError(msg)
        existing_dir: DIR = existing_dirs[0]

        if not ((expected_dir := get_expected_dir(ped, nii)) == existing_dir):
            logging.warning(
                f"""
                Mismatch of {existing_dir=} and {ped=}.
                Axis Codes are {orientations.aff2axcodes(nii.affine)}.                 
                Updating filename with {expected_dir=}."""
            )

            shutil.move(
                f, f.with_name(f.name.replace(existing_dir, expected_dir))
            )
            new_n = n.with_name(n.name.replace(existing_dir, expected_dir))
            shutil.move(n, new_n)

            # repeat renaming for files in the scans.tsv
            for scans in bids_path.glob("*/ses*/*scans.tsv"):
                d = pd.read_csv(scans, delimiter="\t")
                out = d.assign(
                    filename=d.filename.str.replace(
                        n.name, new_n.name, regex=False
                    )
                )
                print(out)
                out.to_csv(scans, index=False, sep="\t", na_rep="n/a")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="""Update dir-[value] entities to ensure that it matches
        the relevant PhaseEncodingDirection.
        """
    )
    parser.add_argument("bids_dir", type=pathlib.Path)

    args = parser.parse_args()
    main(bids_path=args.bids_dir)
