import os, argparse, pathlib

import bids
import pandas as pd
from deepdiff import DeepDiff
from pprint import pprint


def remove_translation(meta):
  if meta.__contains__('dcmmeta_affine'):
    affine = meta.get('dcmmeta_affine')
    for i,row in enumerate(affine):
      meta['dcmmeta_affine'][i] = row[0:-1]

  return meta


def is_constant(json_list: list, key: str) -> bool:
  values = [x.get(key) for x in json_list]
  return set(len(values)) == 1


def compare_withinsub(layout: bids.BIDSLayout, site: str) -> None:
  '''
  Some parameters won't be consistant from participant to participant, even while
  they should have a single value within a session. This function checks for
  that consistency, raising AssertionErrors if there is variability
  
  '''
  json_list = layout.get(suffix='T1w', extension="nii.gz", return_type="file") \
    + layout.get(task='cuff', extension="nii.gz", return_type="file") \
    + layout.get(task='rest', extension="nii.gz", return_type="file") \
    + layout.get(suffix='dwi', extension="nii.gz", return_type="file") \
    + layout.get(suffix='dwi', extension="nii.gz", return_type="file")

  if site == "NS":
    if not is_constant(json_list, "ReceiveCoilActiveElements"):
      raise AssertionError ("ReceiveCoilActiveElements not constant across session!")

  if not is_constant(json_list, "ShimSettings"):
    raise AssertionError ("ShimSettings not constant across session!")

  return


def check_receivecoil(observed: dict, reference: pd.DataFrame) -> bool:
  okay_values =  reference.ReceiveCoilActiveElements.unique()
  if not len(okay_values) == 1:
    raise AssertionError ("Incorrect options for ReceiveCoilActiveElements in reference")

  return observed.get('ReceiveCoilActiveElements') in okay_values[0]


def compare(layout: bids.BIDSLayout, js_observed: str, reference: pd.DataFrame) -> DeepDiff:

  meta = layout.get_metadata(js_observed)

  if reference.scanner.unique()[0] == "NS":
    if check_receivecoil(meta, reference):
      reference.drop(['ReceiveCoilActiveElements'], axis=1, inplace=True)
      js_goal = reference.to_dict()
    else:
      msg = f"{js_observed} has invalid ReceiveCoilActiveElements!"
      raise AssertionError (msg)

  observed = {key:meta.get(key) for key in reference.keys()}
  observed = remove_translation(observed)

  dd = DeepDiff(
    observed, js_goal, 
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

  reference = (
    pd.read_csv("acq-params.tsv", delimiter="\t")
    .query("scanner == @site"))

  layout = bids.layout.BIDSLayout(root, validate=False)

  if site == "UM":
    site = getUM(
      layout.get_metadata(
        layout.get(suffix='T1w', extension="nii.gz", return_type="file")[0]))

  compare(
    layout, 
    layout.get(suffix='T1w', extension="nii.gz", return_type="file")[0],
    reference.query("suffix == 'T1w'"))

  compare(
    layout, 
    layout.get(suffix='dwi', extension="nii.gz", return_type="file")[0], 
    os.path.join(json_dir, f"site-{site}_dwi.json"),
    reference.query("suffix == 'dwi'"))

  for sample in layout.get(task='cuff', extension="nii.gz", return_type="file"):
    compare(layout, sample, reference.query("suffix == 'bold' & task == 'cuff'"))

  for sample in layout.get(task='rest', extension="nii.gz", return_type="file"):
    compare(layout, sample, reference.query("suffix == 'bold' & task == 'rest'"))    

  for sample in layout.get(acq='fmrib0', extension="nii.gz", return_type="file"):
    compare(layout, sample, reference.query("suffix == 'epi' & acq == 'fmrib0'"))    

  for sample in layout.get(acq='dwib0', extension="nii.gz", return_type="file"):
    compare(layout, sample, reference.query("suffix == 'epi' & acq == 'dwib0'"))    

  compare_withinsub(layout, site=site)

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
