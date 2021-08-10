import sys
from utils import add_session_to_json
try:
    json_file = sys.argv[1]
    ses = sys.argv[2]
    print("Using session %s ... "%ses)
    json_file = add_session_to_json(json_file,ses)
except:
    raise ValueError("Please specify the full path of the bids json")
