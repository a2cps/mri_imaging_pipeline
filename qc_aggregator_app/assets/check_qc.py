import os
import re
# import requests
from typing import Union, Optional

import pandas as pd
import numpy as np
import argparse

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
  params: Optional[list] = None,
  # imaging_log: Union[str, bytes, os.PathLike] = os.path.join('corral-secure', 'projects', 'A2CPS', 'shared', 'urrutia', 'imaging_report', 'imaging_log.csv')
  imaging_log: Union[str, bytes, os.PathLike] = os.path.join('/home', 'psadil', 'Documents', 'git', 'a2cps', 'mri_imaging_pipeline', 'qc_aggregator_app', 'tests', 'imaging_log.csv')
  ) -> pd.DataFrame:
  '''
  get_outliers(fname='group_T1w.tsv', params=['cnr', 'snrd_csf', 'snrd_wm', 'snrd_gm'])
  get_outliers(fname='group_T1w.tsv', ['site'])
  '''

  if not params is None:
    d = pd.read_csv(fname, delimiter="\t", usecols=['bids_name']+params)
  else:
    d = pd.read_csv(fname, delimiter="\t")
  
  sites = (
    pd.read_csv(
      imaging_log,
      usecols=['subject_id', 'site'])
    .rename(columns={'subject_id':'sub'})
    .drop_duplicates())
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

  return outliers


def main(t1w_fname, bold_fname) -> None:

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
