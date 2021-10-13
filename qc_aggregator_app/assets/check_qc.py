import os
import re
import argparse
import requests
from typing import Union, Optional

import pandas as pd
import numpy as np

from atlassian import Confluence

def _zscore(scores: np.array) -> np.array:
  return (scores - scores.mean()) / scores.std()


def post_notification(notification: str, confluence: Optional[Confluence] = None) -> None:
  if confluence is not None:
    confluence.update_page(
      page_id="25755998", 
      title="MRIQC Aggregation", 
      body=notification, 
      parent_id=None, 
      type='page', 
      representation='storage', 
      minor_edit=True)
  else:
    print(notification)
  return 


def build_notification(outliers: pd.DataFrame, notification: list[str]) -> str:
  for idx, row in outliers.sort_index().iterrows():
    notification.append(f'<p>{idx}: {row.dropna().to_dict()}</p>')

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
    indices = ['site', 'sub', 'task', 'ses', 'bids_name']
    dind['task'] = [re.findall('task-(\w+)_', x)[0] for x in dind['bids_name']]
  else:
    indices = ['site', 'sub', 'ses', 'bids_name']

  dind = dind.merge(sites, on='sub', how='left')

  outliers = (
    d
    .merge(dind, on=['bids_name'])
    .set_index(indices)
    .groupby(groups)
    .transform(lambda x: np.where(np.abs(_zscore(x))>3, x, np.nan))
    .dropna(how="all")
    .round(1)
    )

  return outliers


def main(t1w_fname, bold_fname, token: Optional[str] = None) -> None:

  # anat_outliers = get_outliers(fname=t1w_fname, params=['cnr', 'snrd_csf', 'snrd_wm', 'snrd_gm'])
  # func_outliers = get_outliers(fname=bold_fname, params=['tSNR', 'FD_mean'])
  anat_outliers = get_outliers(fname=t1w_fname, groups=['site'])
  func_outliers = get_outliers(fname=bold_fname, groups=['site', 'task'])

  func_outliers.to_csv('outliers_bold.csv')
  anat_outliers.to_csv('outliers_T1w.csv')

  anat_notification = build_notification(anat_outliers, ['<h2>current list of outliers for T1w within each site:</h2>'])
  func_notification = build_notification(func_outliers, ['<h2>current list of outliers for bold within each site:</h2>'])

  notification = ''.join([anat_notification, func_notification])

  if token is not None:
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}"})
    s.verify="/home/psadil/Documents/git/a2cps/mri_imaging_pipeline/qc_aggregator_app/assets/confluence-a2cps-org-chain.pem"   
    post_notification(
      notification, 
      Confluence(
        url='https://confluence.a2cps.org',
        cloud=True,
        session=s))
  else:
    post_notification(notification)

  return


if __name__ == '__main__':

  """
  python check_qc.py MRIQC_A2CPS_group_T1w.tsv MRIQC_A2CPS_group_bold.tsv --token "$(<.token)"
  """

  parser = argparse.ArgumentParser(description='check mriqc-group output for outliers')
  parser.add_argument(
    't1w_fname', 
    default='group_T1w.tsv',
    help="group level tsv for T1w images")
  parser.add_argument(
    'bold_fname', 
    default='group_bold.tsv',
    help="group level tsv for bold images")
  parser.add_argument(
    '--token', 
    type=str)

  args = parser.parse_args()
  main(args.t1w_fname, args.bold_fname, args.token)
