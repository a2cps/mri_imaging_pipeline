import argparse
import pathlib
import re

import pandas as pd

def main(bids_path: pathlib.Path) -> None:
    pattern = r"_run-\d+"
    for f in bids_path.glob("**/func/*run-*"):
        print(f"looking at file: {f.name}")
        target = re.sub(pattern, '', f"{f.parent}/{f.name}")
        print(f"renaming: {f.name} -> {target}")
        f.rename(target)
            
    # repeat renaming for files in the scans.tsv
    for scans in bids_path.glob("*/ses*/*scans.tsv"):
        d = pd.read_csv(scans, delimiter="\t")
        out = d.assign(filename = d.filename.str.replace(pattern,  "", regex=True))
        out.to_csv(scans, index=False, sep="\t", na_rep="n/a")

if __name__ == '__main__':
    '''
    Example:
        python clean_phantom.py bids
    '''
    parser = argparse.ArgumentParser(
        description='''Initial scans from WS had a protocolname that matched the patient scans and 
        so ended up with a run-1 tag, unlike all other sites. This removes that tag from the scans and 
        scans.tsv files.
        ''')
    parser.add_argument('bids_dir', type=pathlib.Path)
 
    args = parser.parse_args()
    main(bids_path=args.bids_dir)
