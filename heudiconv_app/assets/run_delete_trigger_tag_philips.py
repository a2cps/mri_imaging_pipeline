import sys
import argparse
from utils import edit_dicom_file_philips
try:
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", help="increase output verbosity")
    args = parser.parse_args()
    inputfile = args.files
    print("Deleting Trigger tag for %s "%inputfile)
    edit_dicom_file_philips(inputfile)
except:
    raise ValueError("Please specify the full path of the raw subject data directory")
