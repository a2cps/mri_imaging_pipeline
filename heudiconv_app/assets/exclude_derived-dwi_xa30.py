import argparse
import logging
from pathlib import Path

import pydicom

TOEXCLUDE = ["DWI_ColFA", "DWI_ADC", "DWI_TRACEW", "DWI_FA", "DWI_TENSOR_B0"]


def main(root: Path) -> None:
    for dcm in root.rglob("*"):
        if not dcm.is_file() or dcm.name == "DICOMDIR":
            continue
        header = pydicom.dcmread(dcm, specific_tags=["SeriesDescription"])
        if (SeriesDescription := header.SeriesDescription) in TOEXCLUDE:
            logging.warning(
                f"excluding file {dcm} with SeriesDescription {SeriesDescription}"
            )
            dcm.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)

    args = parser.parse_args()
    main(root=args.root)
