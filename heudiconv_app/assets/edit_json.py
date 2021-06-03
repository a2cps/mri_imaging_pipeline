import sys,json,ast
from utils import edit_json
"""
python3 edit_json.py /scratch/07798/tnath/data/products/development/mris/NS_northshore/bids/NS043021PVP_new_heuristics/
"""
try:
    fname = sys.argv[1]
    edit_json(fname)
except:
    raise ValueError("Please specify the path to the subject directory.")
