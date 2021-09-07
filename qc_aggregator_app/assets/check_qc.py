import os
# import requests
from typing import Union
from pathlib import Path

import pandas as pd
import numpy as np
from scipy import stats
from boxsdk import DevelopmentClient
from boxsdk.exception import BoxAPIException

mriqc_folder = '144878701459'

def post_notification(notification: str) -> None:
  # endpoint = r"https://api.a2cps.org/actors/v2/slackbot.prod/messages?x-nonce=A2CPS_NPzA41LpZw6x5"
  # content = requests.post(url = endpoint, json = {"text": notification})
  # data = content.json()
  print(notification)
  return 


def build_notification(outliers: pd.DataFrame) -> str:
  notification = ['current list of outliers:']
  for idx, row in outliers.iterrows():
    notification.append(f'{idx}: {row.dropna().to_dict()}')

  return '\n'.join(notification)


def get_outliers(fname: Union[str, bytes, os.PathLike], params: list[str]) -> pd.DataFrame:
  '''
  get_outliers(fname='group_T1w.tsv', params=['cnr', 'snrd_csf', 'snrd_wm', 'snrd_gm'])
  '''
  
  outliers = (
    pd.read_csv(fname, delimiter="\t", index_col='bids_name', usecols=['bids_name']+params)
    .where(lambda x: np.abs(stats.zscore(x)) > 3, np.nan)
    .dropna(how="all")
    .round(1)
    )

  urls = get_urls(outliers.index.tolist())
  
  return outliers.join(urls)


def get_urls(bids_name: list) -> pd.DataFrame:
  client = DevelopmentClient()
  mriqc_reports_folder = client.folder(mriqc_folder)
  key = []
  for file in mriqc_reports_folder.get_items():
    fname = os.path.splitext(file.name)[0]
    if fname in bids_name:
      key.append(pd.DataFrame({
        "bids_name": [fname], 
        "url": [file.get_shared_link(access="open", allow_download=True, allow_preview=True)] 
        }))

  return pd.concat(key, ignore_index=True).set_index('bids_name')


def upload() -> None:
  """
  upload each html report. Note that this leverages error 409
  https://developer.box.com/reference/post-files-id-copy/
  i.e., box api refuses post request when the file name already exists. This
  is a sort of hacky way to cache results. 
  -> if the file needs to be updated, then it must first be deleted in box!
  """
  mriqc_root = Path(os.path.join(
    'corral-secure', 'projects', 'A2CPS', 'products', 'mris', 'sites_all',
    'mriqc', 'a2cps'))
  client = DevelopmentClient()
  mriqc_reports_folder = client.folder(mriqc_folder)  

  for html in mriqc_root.glob('*html'):
    target = html.resolve()
    try:
      mriqc_reports_folder.upload(
        target, 
        file_name=None, 
        file_description=None,
        preflight_check=False, 
        preflight_expected_size=0) 
    except BoxAPIException:
      print('file already uploaded! not bothering')

  return

def main() -> None:

  upload()

  anat_outliers = get_outliers(fname='group_T1w.tsv', params=['cnr', 'snrd_csf', 'snrd_wm', 'snrd_gm'])
  func_outliers = get_outliers(fname='group_bold.tsv', params=['tSNR', 'FD_mean'])

  anat_notification = build_notification(anat_outliers)
  func_notification = build_notification(func_outliers)
  post_notification(''.join([anat_notification, func_notification]))

  return


if __name__ == '__main__':
    main()
