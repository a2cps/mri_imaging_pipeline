import argparse
import json
import logging
from pathlib import Path
import shutil
import typing

import nibabel as nb


CORRECT_BVAL = Path("correct_bval_GE")
CORRECT_BVEC = Path("correct_bvec_GE")


def get_length_of_dwi(f: Path) -> int:
    dwi: nb.Nifti1Image = nb.load(f)
    assert len(dwi.shape) == 4

    return dwi.shape[-1]


def replace_niigz(orig: Path, suffix: str) -> Path:
    # need double because files will have two suffixes (.nii.gz)
    return orig.with_suffix("").with_suffix(suffix)


def split_truncate_join_line(line: str, n: int) -> str:
    return " ".join(line.split()[:n])


def truncate_bvalbvec(outdir: Path) -> None:
    # DWI images can be truncated, but the number of bvals/bvecs must match the
    # number of volumes
    for dwi in outdir.glob("sub*/ses*/dwi/*nii.gz"):
        n_dwi_volumes = get_length_of_dwi(dwi)

        bval_f = replace_niigz(dwi, ".bval")
        bval_f.write_text(split_truncate_join_line(bval_f.read_text(), n_dwi_volumes))

        bvec_f = replace_niigz(dwi, ".bvec")
        with open(bvec_f) as f:
            bvec_lines = f.read().splitlines()

        bvecs = [split_truncate_join_line(v, n_dwi_volumes) for v in bvec_lines]
        bvec_f.write_text("\n".join(bvecs))


def write_expected(outdir: Path) -> None:
    for dwi in outdir.glob("sub*/ses*/dwi/*nii.gz"):
        shutil.copy(CORRECT_BVAL, replace_niigz(dwi, ".bval"))
        shutil.copy(CORRECT_BVEC, replace_niigz(dwi, ".bvec"))


def main(outdir: Path) -> None:
    for dwi in outdir.glob("sub*/ses*/dwi/*json"):
        with open(dwi) as f:
            sidecar: dict[str, typing.Any] = json.load(f)
        version = sidecar.get("SoftwareVersions")

        assert not (version is None)

        # Issues with bvals and bvecs in dicom header only fixed in 28
        # https://confluence.a2cps.org/display/DOC/GE+V26+%28UIC%29+DWI+Incorrect+DICOM+Headers
        if not (("28" in version) or ("29" in version)):
            logging.warning("Overwriting bval and bvec files produced by dcm2niix")
            write_expected(outdir=outdir)
        else:
            # if not those cases, leave bval/bvec untouched because
            # the one that dcm2niix produced shoudl be fine
            logging.warning("Leaving bval and bvec files produced by dcm2niix")

        logging.warning(
            "Truncating bval and bvec files to match number of volumes in DWI"
        )
        truncate_bvalbvec(outdir=outdir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("outdir", type=Path)
    args = parser.parse_args()
    main(outdir=args.outdir)
