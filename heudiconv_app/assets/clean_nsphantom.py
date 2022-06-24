import argparse
import json
import pathlib
import re

import pandas as pd

def check_is_orig(path) -> bool:
    with open(path) as f:
        data = json.load(f)
        imagetype = data.get("ImageType")

    return "ORIGINAL" in imagetype


def main(bids_path: pathlib.Path) -> None:
    originals = []
    to_del = []
    for j in bids_path.glob("**/dwi/*json"):
        if check_is_orig(j):
            originals.append(j.stem)
        else:
            to_del.append(j.stem)

    for stem in to_del:
        print(f"looking at stem: {stem}")
        for f in bids_path.glob(f"**/dwi/{stem}.*"):
            print(f"deleting: {f.name}")
            f.unlink()

    pattern = r'__dup-0[0-9]'
    for stem in originals:
        print(f"looking at stem: {stem}")
        for f in bids_path.glob(f"**/dwi/{stem}.*"):
            target = re.sub(pattern, '', f"{f.parent}/{f.name}")
            print(f"renaming: {f.name} -> {target}")
            f.rename(target)
            
    # repeat removal and renaming for the scans.tsv
    for scans in bids_path.glob("*/ses*/*scans.tsv"):
        d = pd.read_csv(scans, delimiter="\t")
        d.drop([index for index, row in d.iterrows() if pathlib.Path(row.filename).with_suffix('').stem in to_del], inplace=True)
        out = d.assign(filename = d.filename.str.replace(pattern,  "", regex=True))
        out.to_csv(scans, index=False, sep="\t", na_rep="n/a")

if __name__ == '__main__':
    '''
    Example:
        python clean_shphantom.py bids
    '''
    parser = argparse.ArgumentParser(
        description='''Derived (DWI) scans get stored by heudiconv as duplicates, 
        and the original DWI also ends up as a "duplicate". This parses the associated jsons, 
        to delete all but the original dwi and then strip the "dup" part of the filename for the originals.

        Files that are deleted in this manner are also removed from the scans.tsv
        ''')
    parser.add_argument('bids_dir', type=pathlib.Path)
 
    args = parser.parse_args()
    main(bids_path=args.bids_dir)
