import os
import argparse
import requests
import json
import re

from tempfile import NamedTemporaryFile
from typing import Union, Optional

import pandas as pd

from atlassian import Confluence

def df_from_json(file: Union[str, bytes, os.PathLike]) -> pd.DataFrame:
  with open('/home/psadil/Documents/git/a2cps/mri_imaging_pipeline/qc_aggregator_app/tests/unknown_sub-10008_ses-T1w.json') as f:
    x=json.load(file)

  d = pd.DataFrame(
    {
      'sub':re.findall(r'(?:sub-)(\d+)', x['subject'])[0],
      'ses':re.findall(r'(?:ses-)(\w+)_', x['subject']),
      "review":x['rating'],
      "notes": str(x.get('artifacts'))
      }, 
    index=[0])    
  return d


def load_local_log(imaging_log: Union[str, bytes, os.PathLike]) -> pd.DataFrame:
  d = (
    pd.read_csv(imaging_log)
    .query("`T1 Received` == 1")
    .rename(columns={
      "subject_id": "sub",
      "visit": "ses",
      "T1 Received": "t1w",
      "DWI Received": "dwi",
      "fMRI Individualized Pressure Received": "cuff1",
      "fMRI Standard Pressure Received": "cuff2",
      "1st Resting State Received": "rest1",
      "2nd Resting State Received": "rest2"})
    [["site", "sub","ses", "t1w","dwi","cuff1", "cuff2","rest1", "rest2"]]
    .melt(id_vars=["site","sub","ses"], var_name = "scan", value_name = "received")
    .query("received == 1")
    .drop(columns="received")
  )

  return d


def get_all_attachments(confluence: Confluence, size=2000, step=200) -> str:
  """
  pull all stored jsons used for qc
  """

  responses = ""
  for start,limit in zip(range(0,size-step-1,step), range(step-1,size,step)):
    responses += confluence.get_attachments_from_content(
      page_id="29065229",
      start=start,
      limit=limit)

  return responses


def get_jsons(confluence: Confluence) -> list:
  """
  pull all stored jsons used for qc
  """

  attachments = get_all_attachments(confluence)

  jsons = []
  for attachment in attachments:
    jsons.append(confluence.get_attachments_from_content(
      filename=attachment,
      page_id="29065229",
      expand="body"))

  return jsons


def main(
  imaging_log: Union[str, bytes, os.PathLike],
  token: Optional[str] = None, 
  pem: Optional[Union[str, bytes, os.PathLike]] = None) -> None:

  """
  1. get remote log
  2. get all uploaded jsons
  3. update log with new jsons
  4. put updated log
  """

  s = requests.Session()
  s.headers.update({"Authorization": f"Bearer {token}"})
  s.verify = pem
  r = s.get('https://confluence.a2cps.org/download/attachments/29065229/qc_log.xlsx')
  remote_log = pd.read_excel(r.content)

  # local_log = load_local_log(imaging_log)

  tf = NamedTemporaryFile(suffix=".xlsx")
  remote_log.merge(local_log, on=["site","sub","ses","scan"], how="left").to_excel(tf.name, index=False)

  confluence = Confluence(
    url='https://confluence.a2cps.org',
    cloud=True,
    session=s)

  confluence.attach_file(
    filename=tf.name,
    page_id="29065229", 
    name="qc_log.xlsx", 
    title="QC Log")
    
  return


if __name__ == '__main__':

  """
  python check_qc.py MRIQC_A2CPS_group_T1w.tsv MRIQC_A2CPS_group_bold.tsv --token "$(<.token)"
  """

  parser = argparse.ArgumentParser(description='check mriqc-group output for outliers')
  parser.add_argument(
    'imaging_log', 
    default=os.path.join('/home', 'psadil', 'Documents', 'git', 'a2cps', 'mri_imaging_pipeline', 'qc_aggregator_app', 'tests', 'imaging_log.csv'),
    help="log of received scans")

  args = parser.parse_args()
  main(args.imaging_log)

