import argparse
import pathlib
from utils import create_fieldmaps

"""
python3 create_fieldmaps_GE '/home/tanmay/hacking/AC2PC/data/uic/development/UI_uic/UI_travhuman'
"""
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("fname", type=pathlib.Path)

    args = parser.parse_args()
    create_fieldmaps(args.fname)
