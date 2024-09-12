import argparse
import json
import logging
import shutil
import typing
from pathlib import Path

CORRECT_BVAL = Path("/tapis/assets/correct_bval_GE")
CORRECT_BVEC = Path("/tapis/assets/correct_bvec_GE")


def replace_niigz(orig: Path, suffix: str) -> Path:
    """Replace .nii.gz with other suffix

    Args:
        orig (Path): filename with ending .nii.gz
        suffix (str): suffix to use instead of .nii.gz

    Returns:
        Path: filename with .nii.gz replaced by suffix

    Example:
        replace_niigz(Path("dwi.nii.gz"), ".bval") -> dwi.bval
    """

    # need double because files will have two suffixes (.nii.gz)
    return orig.with_suffix("").with_suffix(suffix)


def write_expected(outdir: Path) -> None:
    for dwi in outdir.glob("sub*/ses*/dwi/*nii.gz"):
        shutil.copy(CORRECT_BVAL, replace_niigz(dwi, ".bval"))
        shutil.copy(CORRECT_BVEC, replace_niigz(dwi, ".bvec"))


def main(outdir: Path) -> None:
    for dwi in outdir.glob("sub*/ses*/dwi/*json"):
        with open(dwi) as f:
            sidecar: dict[str, typing.Any] = json.load(f)
        version = sidecar.get("SoftwareVersions")

        assert version is not None

        version_prefix = int(version[:2])

        # Issues with bvals and bvecs in dicom header only fixed in version >=28
        # At least, have only seen that up to 29 is correct
        # https://a2cps.atlassian.net/wiki/spaces/DOC/pages/5406753/GE+V26+UIC+DWI+Incorrect+DICOM+Headers
        if version_prefix < 28:
            logging.warning(
                "Overwriting bval and bvec files produced by dcm2niix"
            )
            write_expected(outdir=outdir)
        else:
            # if not those cases, leave bval/bvec untouched because
            # the one that dcm2niix produced shoudl be fine
            logging.warning("Leaving bval and bvec files produced by dcm2niix")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("outdir", type=Path)
    args = parser.parse_args()
    main(outdir=args.outdir)
