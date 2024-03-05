import argparse
from pathlib import Path

import pandas as pd


def main(bidsdir: Path) -> None:
    for scans_tsv in bidsdir.rglob("*scans.tsv"):
        scans = pd.read_csv(scans_tsv, sep=r"\s+")
        scans.drop(columns=["operator", "randstr"], inplace=True)
        scans.to_csv(scans_tsv, sep="\t", na_rep="n/a", index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("bidsdir", type=Path)

    args = parser.parse_args()
    main(bidsdir=args.bidsdir)
