import sys
from utils import edit_dicom_file_philips
try:
    inputfile = sys.argv[1]
    print("Deleting Trigger tag for %s "%inputfile)
    edit_dicom_file_philips(inputfile)
except:
    raise ValueError("Please specify the full path of the raw subject data directory")
