import os, json, argparse, pathlib

import bids
from deepdiff import DeepDiff
from pprint import pprint

def compare(layout: bids.BIDSLayout, js_observed: str, reference: str) -> DeepDiff:

  meta = layout.get_metadata(js_observed)

  with open(reference) as f:
    js_goal = json.load(f)
  
  observed = {key:meta.get(key) for key in js_goal.keys()}

  dd = DeepDiff(
    sorted(observed), sorted(js_goal), 
    math_epsilon=0.01)
  
  if dd:
    pprint(dd)
    msg = f"{js_observed} has differences!"
    raise AssertionError (msg)
  else:
    print(f"{js_observed} looks okay")

  return dd


def getUM(t1w_meta: dict) -> str:
  if t1w_meta.get("DeviceSerialNumber") == "000000000UM750MR":
    site = "UM1"
  elif t1w_meta.get("DeviceSerialNumber") == "0007347633TMRFIX":
    site = "UM2"
  else:
    raise AssertionError ("Unsure which UM bids to compare against!")

  return site


def main(root: str, site: str, json_dir: str) -> None:

  layout = bids.layout.BIDSLayout(root, validate=False)

  if site == "UM":
    site = getUM(
      layout.get_metadata(layout.get(suffix='T1w', extension="nii.gz", return_type="file")[0]))

  compare(
    layout, 
    layout.get(suffix='T1w', extension="nii.gz", return_type="file")[0], 
    os.path.join(json_dir, f"site-{site}_T1w.json"))

  for sample in layout.get(task='cuff', extension="nii.gz", return_type="file"):
    compare(layout, sample, os.path.join(json_dir, f"site-{site}_task-cuff_bold.json"))

  for sample in layout.get(task='rest', extension="nii.gz", return_type="file"):
    compare(layout, sample, os.path.join(json_dir, f"site-{site}_task-rest_bold.json"))    

  compare(
    layout, 
    layout.get(suffix='dwi', extension="nii.gz", return_type="file")[0], 
    os.path.join(json_dir, f"site-{site}_dwi.json"))

  return


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Check bids.json files')
  parser.add_argument('root', type=pathlib.Path)
  parser.add_argument(
    'site', 
    choices=['NS', 'SH', 'UC', 'UI', 'UM', 'WS'])  
  parser.add_argument('json_dir', type=pathlib.Path)  
  args = parser.parse_args()

  main(root=args.root, site=args.site, json_dir=args.json_dir)
