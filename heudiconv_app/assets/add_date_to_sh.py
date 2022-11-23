import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

import pydicom


def main(dicomdir: Path, bidsdir: Path) -> None:
    for dcm in dicomdir.glob("**/*dcm"):
        header = pydicom.dcmread(dcm, specific_tags=["SeriesDate", "SeriesTime"])
        AcquisitionDateTime = datetime.strptime(
            header.SeriesDate + header.SeriesTime, "%Y%m%d%H%M%S.%f"
        ).isoformat()
        for scans_tsv in bidsdir.glob("**/sub*scans.tsv"):
            scans = pd.read_csv(scans_tsv, delim_whitespace=True)
            scans.acq_time = AcquisitionDateTime
            scans.to_csv(scans_tsv, sep="\t", na_rep="n/a", index=False)
        break


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dicomdir", type=Path)
    parser.add_argument("bidsdir", type=Path)

    args = parser.parse_args()
    main(dicomdir=args.dicomdir, bidsdir=args.bidsdir)
