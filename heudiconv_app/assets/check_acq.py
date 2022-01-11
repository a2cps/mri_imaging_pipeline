import os, argparse, pathlib, requests
from glob import glob
from itertools import chain
import bids
import numpy as np
import pandas as pd
from deepdiff import DeepDiff
from pprint import pprint


# parameters to check for numerical equivalence
FLOATING_PARAMS = {
  0.001: ["dcmmeta_affine","EffectiveEchoSpacing","RepetitionTime"],
  0.01: ["ImagingFrequency","WaterFatShift"],
  0.1: ["SliceTiming","EchoTime"]}


def post_notification(notification: str, post: bool = False):
  if post:
    endpoint = r"https://api.a2cps.org/actors/v2/imaging-slackbot.prod/messages?x-nonce=A2CPS_w1r4M51bYemAQ"
    content = requests.post(url = endpoint, json = {"text": notification})
    data = content.json()
  else:
    data = None    
  return data


def remove_translation(meta: dict) -> dict:
  if meta.__contains__('dcmmeta_affine'):
    affine = meta.get('dcmmeta_affine')
    for i,row in enumerate(affine):
      meta['dcmmeta_affine'][i] = row[0:-1]

  return meta


def assert_constant(jsons: list, meta:list, key: str, post: bool = False) -> bool:
  tocheck = pd.DataFrame({
      'json': [os.path.basename(x) for x in jsons],
      key: [x.get(key) for x in meta]
    })
  
  if len(tocheck.drop_duplicates(subset=key)) > 1:
    print(f"Visit has multiple values for {key}")
    pprint(tocheck) 
    post_notification(tocheck.to_string(), post=post)   
    ok = False
  else:
    ok  = True

  return ok


def compare_withinsub(layout: bids.BIDSLayout, site: str, post: bool = False) -> None:
  '''
  Some parameters won't be consistant from participant to participant, even while
  they should have a single value within a session. This function checks for
  that consistency, raising AssertionErrors if there is variability
  
  '''
  json_list = layout.get(suffix='T1w', extension="nii.gz", return_type="file") \
    + layout.get(task='cuff', extension="nii.gz", return_type="file") \
    + layout.get(task='rest', extension="nii.gz", return_type="file") \
    + layout.get(suffix='dwi', extension="nii.gz", return_type="file") \
    + layout.get(suffix='epi', extension="nii.gz", return_type="file")
  meta_list = [layout.get_metadata(x) for x in json_list]
  
  if site == "NS":
    ok = assert_constant(json_list, meta_list, "ReceiveCoilActiveElements", post=post)
    ok *= assert_constant(json_list, meta_list, "ShimSettings", post=post)
  else:
    ok = True

  return ok


def check_receivecoil(observed: dict, reference: pd.DataFrame) -> bool:
  okay_values = reference.ReceiveCoilActiveElements.unique()
  if not len(okay_values) == 1:
    raise AssertionError ("Incorrect options for ReceiveCoilActiveElements in reference")

  return observed.get('ReceiveCoilActiveElements') in okay_values[0]


def add_deepkeys(observed: dict) -> dict:
  if observed.__contains__('global'):
      observed['BitsStored'] = observed.get('global').get('const').get('BitsStored')
  return observed


def check_bvalsbvecs(bval_observed: np.ndarray, bvec_observed: np.ndarray, reference: pd.DataFrame) -> bool:
  rb = np.array(pd.eval(reference['bval']), dtype=float).squeeze()
  rv = np.array(pd.eval(reference['bvec']), dtype=float).squeeze()
  if not (np.isclose(rb, bval_observed).all() and np.isclose(rv, bvec_observed).all()):
    print("unexpected bvals or bvecs!")
    print(f"bvals: {bval_observed}")
    print(f"bvecs: {bvec_observed}")
    ok = False
  else:
    ok = True

  return ok


def print_if_not_none(dd, post: bool = False) -> None:
  if dd is not None: 
    print(dd.pretty())
    post_notification(dd.pretty(), post=post)


def compare(layout: bids.BIDSLayout, js_observed: str, reference: pd.DataFrame, post: bool = False) -> bool:
  ok = True

  meta = layout.get_metadata(js_observed)
  meta = add_deepkeys(meta)

  if reference.scanner.unique()[0] == "NS":
    if check_receivecoil(meta, reference):
      reference.drop(['ReceiveCoilActiveElements'], axis=1, inplace=True)      
    else:
      print(f"{js_observed} has invalid ReceiveCoilActiveElements: {meta.get('ReceiveCoilActiveElements')}")
      post_notification(
        f"{js_observed} has invalid ReceiveCoilActiveElements: {meta.get('ReceiveCoilActiveElements')}",
        post=post)
      ok = False

  reference.drop(['task', 'suffix', 'source', 'scanner', 'bval', 'bvec'], axis=1, inplace=True)
  js_goal = reference.dropna(axis=1).copy()

  for n in ['dcmmeta_affine', 'dcmmeta_reorient_transform', 'dcmmeta_shape','SliceTiming']:
    if n in js_goal.columns.values.tolist():
      js_goal[n] = pd.eval(js_goal.loc[:,n])

  js_goal = js_goal.to_dict(orient="records")[0]
  observed = {key:meta[key] for key in js_goal.keys()}
  observed = remove_translation(observed)

  # These are the parameters 
  for epsilon, params in FLOATING_PARAMS.items():    
    if any(observed.__contains__(x) for x in params):
      dd1 = DeepDiff(
        {key:js_goal[key] for key in params if js_goal.__contains__(key)}, 
        {key:observed[key] for key in params if js_goal.__contains__(key)}, 
        math_epsilon=epsilon,
        ignore_numeric_type_changes=True)
      if dd1:
        ok = False
        print(f"json for {js_observed} has unexpected values at epsilon: {epsilon}!")
        print_if_not_none(dd1, post=post)

  dd2 = DeepDiff(
    {key:js_goal[key] for key in js_goal.keys() if key not in list(chain(*FLOATING_PARAMS.values()))}, 
    {key:observed[key] for key in observed.keys() if key not in list(chain(*FLOATING_PARAMS.values()))}, 
    ignore_numeric_type_changes=True)

  if dd2:
    print(f"json for {js_observed} has unexpected values at epsilon: 0!")
    print_if_not_none(dd2, post=post)
    ok = False
  else:
    print(f"json for {js_observed} looks okay")
    ok *= True

  return ok


def getUM(t1w_meta: dict) -> str:
  if t1w_meta.get("DeviceSerialNumber") == "000000000UM750MR":
    site = "UM1"
  elif t1w_meta.get("DeviceSerialNumber") == "0007347633TMRFIX":
    site = "UM2"
  else:
    raise AssertionError ("Unsure which UM bids to compare against!")

  return site


def main(root: str, site: str, post: bool = False) -> None:
  ok = 1

  layout = bids.layout.BIDSLayout(root, validate=False)

  if site == "UM":
    site = getUM(
      layout.get_metadata(
        layout.get(suffix='T1w', extension="nii.gz", return_type="file")[0]))

  reference = (
    pd.read_csv(
      "acq-params.tsv", 
      delimiter="\t",
      converters={
        'ImageOrientationPatientDICOM': pd.eval,
        'ImageType': pd.eval})
    .query("scanner == @site"))

  for scan in layout.get(suffix='dwi', extension="nii.gz", return_type="file"):
    ok *= check_bvalsbvecs(
      np.genfromtxt(glob(os.path.join(root, "**","dwi", "*bval"), recursive=True)[0]),
      np.genfromtxt(glob(os.path.join(root, "**","dwi", "*bvec"), recursive=True)[0]),
      reference.query("suffix == 'dwi'").copy())   
    ok *= compare(layout, scan, reference.query("suffix == 'dwi'").copy(), post=post)

  ok *= compare(
    layout, 
    layout.get(suffix='T1w', extension="nii.gz", return_type="file")[0],
    reference.query("suffix == 'T1w'").copy(),
    post=post)

  for task in ["rest", "cuff"]:
    for scan in layout.get(task=task, extension="nii.gz", return_type="file"):
      ok *= compare(layout, scan, reference.query("suffix == 'bold' & task == @task").copy(), post=post)

  for acq in ["dwib0", "fmrib0"]:
    for dir in ["AP", "PA"]:
      for scan in layout.get(acq=acq,dir=dir, extension="nii.gz", return_type="file", invalid_filters='allow'):
        ok *= compare(layout, scan, reference.query("suffix == 'epi' & acq == @aqc & dir == @dir").copy(), post=post)   

  ok *= compare_withinsub(layout, site=site, post=post)
  if not ok:
    raise AssertionError ("Unexpected parameters! See logs")

  return


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Check bids.json files')
  parser.add_argument('root', type=pathlib.Path)
  parser.add_argument('site', choices=['NS', 'SH', 'UC', 'UI', 'UM', 'WS'])  
  parser.add_argument(
    '--post', 
    action=argparse.BooleanOptionalAction,
    default=False)  

  args = parser.parse_args()  
  main(root=args.root, site=args.site, post=args.post)
