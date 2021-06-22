import sys,json,ast
from utils import create_fieldmaps
"""
python3 create_fieldmaps_GE '/home/tanmay/hacking/AC2PC/data/uic/development/UI_uic/UI_travhuman'
"""
try:
    fname = sys.argv[1]
    create_fieldmaps(fname)
except:
    raise ValueError("Please specify the path to the subject directory.")
