import sys,json,ast
from utils import edit_json
"""
python3 edit_json.py '/scratch/07798/tnath/data/products/development/mris/NS_northshore/bids/NS043021PVP_new_heuristics/sub-043021/ses-PVP/fmap/sub-043021_ses-PVP_acq-dwib0_dir-AP_epi.json' IntendedFor '["ses-PVP/dwi/sub-043021_ses-PVP_dwi.nii.gz"]'
"""
try:
    fname = sys.argv[1]
    key_to_add = sys.argv[2]
    value_to_add =sys.argv[3]
    value_to_add = ast.literal_eval(value_to_add)
    if len(sys.argv)==5:
         reference_key = sys.argv[4]
    else:
         reference_key = 'InstitutionAddress' #Set a default value
    print("Adding key %s with value %s to file %s "%(key_to_add,value_to_add,fname))
    new_dict = edit_json(fname, key_to_add,reference_key, value_to_add)
except:
    raise ValueError("Please specify all the input arguments.")

