import os
import re
# import requests
from typing import Union, Optional
# from pathlib import Path

import pandas as pd
import numpy as np
# from boxsdk import DevelopmentClient
# from boxsdk.exception import BoxAPIException

import argparse

# mriqc_folder = '144878701459'

def _zscore(scores: np.array) -> np.array:
  return (scores - scores.mean()) / scores.std()


def post_notification(notification: str) -> None:
  # endpoint = r"https://api.a2cps.org/actors/v2/slackbot.prod/messages?x-nonce=A2CPS_NPzA41LpZw6x5"
  # content = requests.post(url = endpoint, json = {"text": notification})
  # data = content.json()
  print(notification)
  return 


def build_notification(outliers: pd.DataFrame, notification: list[str]) -> str:
  for idx, row in outliers.iterrows():
    notification.append(f'{idx}: {row.dropna().to_dict()}')

  return '\n'.join(notification)


def get_outliers(
  fname: Union[str, bytes, os.PathLike], 
  groups: list[str], 
  params: Optional[list] = None) -> pd.DataFrame:
  '''
  get_outliers(fname='group_T1w.tsv', params=['cnr', 'snrd_csf', 'snrd_wm', 'snrd_gm'])
  get_outliers(fname='group_T1w.tsv', ['site'])
  '''

  if not params is None:
    d = pd.read_csv(fname, delimiter="\t", usecols=['bids_name']+params)
  else:
    d = pd.read_csv(fname, delimiter="\t")
  
  
  sites = pd.read_csv('imaging-log.csv')
  dind = d[['bids_name']].copy()
  dind['sub'] = [int(re.findall('sub-(\d+)', x)[0]) for x in dind['bids_name']]
  dind['ses'] = [re.findall('ses-(V\d)', x)[0] for x in dind['bids_name']]

  if 'task' in groups:
    dind['task'] = [re.findall('task-(\w+)_', x)[0] for x in dind['bids_name']]

  dind = dind.merge(sites, on='sub', how='left')

  outliers = (
    d
    .merge(dind, on=['bids_name'])
    .set_index(groups + ['ses', 'sub', 'bids_name'])
    .groupby(groups)
    .transform(lambda x: np.where(np.abs(_zscore(x))>3, x, np.nan))
    .dropna(how="all")
    .round(1)
    )

  # urls = get_urls(outliers.index.tolist())
  # return outliers.join(urls)
  return outliers


# def get_urls(bids_name: list) -> pd.DataFrame:
#   client = DevelopmentClient()
#   mriqc_reports_folder = client.folder(mriqc_folder)
#   key = []
#   for file in mriqc_reports_folder.get_items():
#     fname = os.path.splitext(file.name)[0]
#     if fname in bids_name:
#       key.append(pd.DataFrame({
#         "bids_name": [fname], 
#         "url": [file.get_shared_link(access="open", allow_download=True, allow_preview=True)] 
#         }))

#   return pd.concat(key, ignore_index=True).set_index('bids_name')


# def upload() -> None:
#   """
#   upload each html report. Note that this leverages error 409
#   https://developer.box.com/reference/post-files-id-copy/
#   i.e., box api refuses post request when the file name already exists. This
#   is a sort of hacky way to cache results. 
#   -> if the file needs to be updated, then it must first be deleted in box!
#   """
#   mriqc_root = Path(os.path.join(
#     'corral-secure', 'projects', 'A2CPS', 'products', 'mris', 'sites_all',
#     'mriqc', 'a2cps'))
#   client = DevelopmentClient()
#   mriqc_reports_folder = client.folder(mriqc_folder)  

#   for html in mriqc_root.glob('*html'):
#     target = html.resolve()
#     try:
#       mriqc_reports_folder.upload(
#         target, 
#         file_name=None, 
#         file_description=None,
#         preflight_check=False, 
#         preflight_expected_size=0) 
#     except BoxAPIException:
#       print('file already uploaded!')

#   return


def main(t1w_fname, bold_fname) -> None:

  # upload()

  # anat_outliers = get_outliers(fname=t1w_fname, params=['cnr', 'snrd_csf', 'snrd_wm', 'snrd_gm'])
  # func_outliers = get_outliers(fname=bold_fname, params=['tSNR', 'FD_mean'])
  anat_outliers = get_outliers(fname=t1w_fname, groups=['site'])
  func_outliers = get_outliers(fname=bold_fname, groups=['site', 'task'])

  func_outliers.to_csv('outliers_bold.csv')
  anat_outliers.to_csv('outliers_T1w.csv')

  anat_notification = build_notification(anat_outliers, ['\n===\ncurrent list of outliers for T1w within each site:\n'])
  func_notification = build_notification(func_outliers, ['\n===\ncurrent list of outliers for bold within each site:\n'])
  post_notification(''.join([anat_notification, func_notification]))

  return


if __name__ == '__main__':

  parser = argparse.ArgumentParser(description='check mriqc-group output for outliers')
  parser.add_argument(
    't1w_fname', 
    default='group_T1w.tsv',
    help="group level tsv for T1w images")
  parser.add_argument(
    'bold_fname', 
    default='group_bold.tsv',
    help="group level tsv for bold images")

  args = parser.parse_args()
  main(args.t1w_fname, args.bold_fname)
