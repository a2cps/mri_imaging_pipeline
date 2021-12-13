import os, argparse, pathlib
from glob import glob
import bids
import numpy as np
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


def add_deepkeys(observed: dict) -> dict:
  if observed.__contains__('global'):
      observed['BitsStored'] = observed.get('global').get('const').get('BitsStored')
  return observed


def check_bvalsbvecs(bval_observed: np.ndarray, bvec_observed: np.ndarray, reference: pd.DataFrame) -> None:
  rb = np.array(pd.eval(reference['bval']), dtype=float).squeeze()
  rv = np.array(pd.eval(reference['bvec']), dtype=float).squeeze()
  if not (np.isclose(rb, bval_observed).all() and np.isclose(rv, bvec_observed).all()):
    raise AssertionError ("unexpected bvals and bvecs!")

  return


def compare(layout: bids.BIDSLayout, js_observed: str, reference: pd.DataFrame) -> DeepDiff:

  meta = layout.get_metadata(js_observed)
  meta = add_deepkeys(meta)

  if reference.scanner.unique()[0] == "NS":
    if check_receivecoil(meta, reference):
      reference.drop(['ReceiveCoilActiveElements'], axis=1, inplace=True)      
    else:
      msg = f"{js_observed} has invalid ReceiveCoilActiveElements!"
      raise AssertionError (msg)

  reference.drop(['task', 'suffix', 'source', 'scanner', 'bval', 'bvec'], axis=1, inplace=True)
  js_goal = reference.dropna(axis=1).copy()

  for n in ['dcmmeta_affine', 'dcmmeta_reorient_transform', 'dcmmeta_shape','SliceTiming']:
    if n in js_goal.columns.values.tolist():
      js_goal[n] = pd.eval(js_goal[n])

  js_goal = js_goal.to_dict(orient="records")[0]
  observed = {key:meta[key] for key in js_goal.keys()}
  observed = remove_translation(observed)

  dd = DeepDiff(
    observed, js_goal, 
    math_epsilon=0.01,
    ignore_numeric_type_changes=True)
  
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


def main(root: str, site: str) -> None:

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
    check_bvalsbvecs(
      np.genfromtxt(glob(os.path.join(root, "**", "*bval"), recursive=True)[0]),
      np.genfromtxt(glob(os.path.join(root, "**", "*bvec"), recursive=True)[0]),
      reference.query("suffix == 'dwi'"))   
    compare(layout, scan, reference.query("suffix == 'dwi'"))

  compare(
    layout, 
    layout.get(suffix='T1w', extension="nii.gz", return_type="file")[0],
    reference.query("suffix == 'T1w'"))

  for task in ["rest", "cuff"]:
    for scan in layout.get(task=task, extension="nii.gz", return_type="file"):
      compare(layout, scan, reference.query("suffix == 'bold' & task == @task"))

  for acq in ["dwib0", "fmrib0"]:
    for dir in ["AP", "PA"]:
      for scan in layout.get(acq=acq,dir=dir, extension="nii.gz", return_type="file"):
        compare(layout, scan, reference.query("suffix == 'epi' & acq == @aqc & dir == @dir"))    

  compare_withinsub(layout, site=site)

  return


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Check bids.json files')
  parser.add_argument('root', type=pathlib.Path)
  parser.add_argument(
    'site', 
    choices=['NS', 'SH', 'UC', 'UI', 'UM', 'WS'])  
  args = parser.parse_args()

  main(root=args.root, site=args.site)
