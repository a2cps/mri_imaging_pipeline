import os
# import requests
from typing import Union

import pandas as pd
import numpy as np
from scipy import stats

def post_notification(notification: str) -> None:
  # endpoint = r"https://api.a2cps.org/actors/v2/slackbot.prod/messages?x-nonce=A2CPS_NPzA41LpZw6x5"
  # content = requests.post(url = endpoint, json = {"text": notification})
  # data = content.json()
  print(notification)
  return 


def build_notification(outliers: pd.DataFrame) -> str:
  notification = ['current list of outliers:']
  for idx, row in outliers.iterrows():
    url = '<placeholder for link>'
    notification.append(f'{idx}: {row.dropna().round(1).to_dict()}; {url}')

  return '\n'.join(notification)


def get_outliers(fname: Union[str, bytes, os.PathLike], params: list[str]) -> pd.DataFrame:
  '''
  get_outliers(fname='group_T1w.tsv', params=['cnr', 'snrd_csf', 'snrd_wm', 'snrd_gm'])
  '''
  
  outliers = (
    pd.read_csv(fname, delimiter="\t", index_col='bids_name', usecols=['bids_name']+params)
    .where(lambda x: np.abs(stats.zscore(x)) > 3, np.nan)
    .dropna(how="all")
    )
  
  return outliers


def main() -> None:

  anat_outliers = get_outliers(fname='group_T1w.tsv', params=['cnr', 'snrd_csf', 'snrd_wm', 'snrd_gm'])
  func_outliers = get_outliers(fname='group_bold.tsv', params=['tSNR', 'FD_mean'])

  anat_notification = build_notification(anat_outliers)
  func_notification = build_notification(func_outliers)
  post_notification(''.join([anat_notification, func_notification]))

  return


if __name__ == '__main__':
    main()
